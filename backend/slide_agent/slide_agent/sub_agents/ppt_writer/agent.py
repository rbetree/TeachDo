import json
import logging
from typing import Dict, List, Any, AsyncGenerator, Optional
from google.genai import types
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents import LoopAgent, BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from .tools import SearchImage, DocumentSearch,KnowledgeBaseSearch
from .image_enricher import maybe_attach_images_to_slide
from ...config import get_ppt_writer_agent_config
from ...create_model import create_model
from . import prompt
from .utils import (
    advance_or_retry_after_validation,
    apply_checker_outcome_to_state,
    ensure_loop_state_initialized,
    evaluate_checker_result,
)

logger = logging.getLogger(__name__)

# ========== 课程产出（全文注入）参考上下文处理 ==========
def _want_english(language: str) -> bool:
    lang = (language or "").strip().lower().replace("_", "-")
    return lang in {"en", "english", "en-us", "en-gb"} or lang.startswith("en-")


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        s = (it or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _extract_keywords_from_slide_schema(slide_schema: dict) -> list[str]:
    keywords: list[str] = []
    if not isinstance(slide_schema, dict):
        return []
    data = slide_schema.get("data")
    if isinstance(data, dict):
        title = data.get("title")
        if isinstance(title, str) and title.strip():
            keywords.append(title.strip())
        items = data.get("items")
        if isinstance(items, list):
            for it in items[:12]:
                if isinstance(it, str) and it.strip():
                    keywords.append(it.strip())
                elif isinstance(it, dict):
                    t = it.get("title")
                    if isinstance(t, str) and t.strip():
                        keywords.append(t.strip())
    # 过滤过短关键词（避免误命中导致截取片段无意义）
    keywords = [k for k in keywords if len(k) >= 2]
    return _dedupe_keep_order(keywords)


def _build_reference_excerpt(text: str, *, keywords: list[str], max_chars: int = 6000) -> str:
    src = (text or "").strip()
    if not src:
        return ""
    if len(src) <= max_chars:
        return src

    # 尝试围绕关键词截取更相关的片段
    for kw in keywords or []:
        if not kw:
            continue
        pos = src.find(kw)
        if pos == -1:
            continue
        start = max(0, pos - max_chars // 3)
        end = min(len(src), start + max_chars)
        chunk = src[start:end].strip()
        if start > 0:
            chunk = "…" + chunk
        if end < len(src):
            chunk = chunk + "…"
        return chunk

    # 兜底：取开头片段
    return src[:max_chars].rstrip() + "…"


def _build_reference_rules(language: str) -> str:
    if _want_english(language):
        return (
            "\n# IMPORTANT: Reference-only context (course outputs)\n"
            "- Use it only to align terminology, facts, and examples.\n"
            "- Do NOT copy sentences/paragraphs verbatim.\n"
            "- Do NOT treat the reference document structure as the PPT structure.\n"
            "- The current slide JSON is the single source of truth for structure.\n"
        )
    return (
        "\n# 重要：参考资料使用规则（课程产出全文）\n"
        "- 仅用于术语一致性、事实核对与例子提炼。\n"
        "- 严禁原文照抄句子/段落，必须改写与重组。\n"
        "- 严禁把参考资料的目录结构当作本次 PPT 的结构。\n"
        "- 页面结构以“输入的 slide JSON”为唯一准绳。\n"
    )

# ========== 通用回调（与原文件一致） ==========
def my_before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    agent_name = callback_context.agent_name
    history_length = len(llm_request.contents)
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型前的callback, 现在Agent共有{history_length}条历史记录,metadata数据为：{metadata}")
    logger.info(f"调用了{agent_name}模型前的callback, 现在Agent共有{history_length}条历史记录,metadata数据为：{metadata}")
    #清空contents,不需要上一步的拆分topic的记录, 不能在这里清理，否则，每次调用工具都会清除记忆，白操作了
    # llm_request.contents.clear()
    # 返回 None，继续调用 LLM
    return None

def my_after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    # 1. 检查用户输入，注意如果是llm的stream模式，那么response_data的结果是一个token的结果，还有可能是工具的调用
    agent_name = callback_context.agent_name
    response_parts = llm_response.content.parts
    part_texts = []
    for one_part in response_parts:
        part_text = one_part.text
        if part_text is not None:
            part_texts.append(part_text)
    part_text_content = "\n".join(part_texts)
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型后的callback, 这次模型回复{response_parts}条信息,metadata数据为：{metadata},回复内容是: {part_text_content}")
    logger.info(f"调用了{agent_name}模型后的callback, 这次模型回复{response_parts}条信息,metadata数据为：{metadata},回复内容是: {part_text_content}")
    return None

# ========== 生成前/后回调 ==========
def my_writer_before_agent_callback(callback_context: CallbackContext) -> None:
    # 这里可根据需要读取 state 做前置处理
    current_slide_index: int = callback_context.state.get("current_slide_index", 0)  # Default to 0
    slides_plan_num = callback_context.state.get("slides_plan_num")
    # 返回 None，继续调用 LLM
    return None

def my_after_agent_callback(callback_context: CallbackContext) -> None:
    """
    在LLM生成内容后，将其原始文本缓存到 state['last_written_raw']，
    供 CheckerAgent 进行 JSON 校验；不在此处推进页码。
    """
    model_last_output_content = callback_context._invocation_context.session.events[-1]
    response_parts = model_last_output_content.content.parts
    part_texts = []
    for one_part in response_parts:
        part_text = one_part.text
        if part_text is not None:
            part_texts.append(part_text)
    part_text_content = "\n".join(part_texts)

    # 保存本轮生成的原始文本，等待校验
    callback_context.state["last_written_raw"] = part_text_content
    print(f"--- 本页生成的原始内容已写入 state['last_written_raw'] ---")

# ========== Writer（生成） ==========
class PPTWriterSubAgent(LlmAgent):
    def __init__(self, **kwargs):
        writer_config = get_ppt_writer_agent_config()
        writer_provider = writer_config["provider"]
        writer_model = writer_config["model"]
        writer_api_key = writer_config.get("api_key")
        writer_base_url = writer_config.get("base_url")

        super().__init__(
            name="PPTWriterSubAgent",
            model=create_model(
                model=writer_model,
                provider=writer_provider,
                api_key=writer_api_key,
                base_url=writer_base_url,
            ),
            description="根据每一页的幻灯片slide的json结构，丰富幻灯片的slide的内容",
            instruction=self._get_dynamic_instruction,
            before_agent_callback=my_writer_before_agent_callback,
            after_agent_callback=my_after_agent_callback,
            before_model_callback=my_before_model_callback,
            after_model_callback=my_after_model_callback,
            tools=[DocumentSearch,KnowledgeBaseSearch,SearchImage],
            **kwargs
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        current_slide_index: int = ctx.session.state.get("current_slide_index", 0)

        # 根据上一次Checker校验结果决定是否清空 / 追加内消息 == =
        st = ctx.session.state
        ensure_loop_state_initialized(st)
        last_passed = st.get("last_validation_passed")  # 可能为 None / True / False
        feedback_text = st.get("last_validation_feedback")
        should_clear = bool(st.get("writer_should_clear_history", False))

        # 首轮默认清空；若上次失败，则保留必要上下文并注入反馈帮助重写。
        if current_slide_index == 0 and last_passed is None:
            should_clear = True

        if should_clear:
            ctx.session.events = []
            st["writer_should_clear_history"] = False
        else:
            logger.info(f"=====>>>6. 当前正在进行对: 第{current_slide_index}个块重新生成")
            if len(ctx.session.events) >= 2:
                del_history = ctx.session.events.pop()
                logger.info(f"=============>>>删除了最后1个内容块：\n{del_history}")
                del_history = ctx.session.events.pop()
                logger.info(f"=============>>>删除了倒数第2个内容块：\n{del_history}")
                logger.info(f"=============>>>删除后的历史记录为：\n{ctx.session.events}")
            if feedback_text:
                ctx.session.events.append(
                    Event(
                        author="CheckerAgent",
                        content=types.Content(parts=[types.Part(text=feedback_text)])
                    )
                )
        if current_slide_index == 0:
            print(f"正在生成第{current_slide_index}页幻灯片...")

        async for event in super()._run_async_impl(ctx):
            print(f"{self.name} 收到事件：{event}")
            logger.info(f"{self.name} 收到事件：{event}")
            yield event

    def _get_dynamic_instruction(self, ctx: InvocationContext) -> str:
        """动态整合所有研究发现并生成指令"""
        # 当前正在生成第几页的ppt
        current_slide_index: int = ctx.state.get("current_slide_index", 0)
        # 获取大纲
        outline_json: list = ctx.state.get("outline_json")
        # 获取要生成的ppt的这一页的schema大纲
        current_slide_schema = outline_json[current_slide_index]
        metadata = ctx.state.get("metadata", {})
        # 默认支持所有的搜索工具
        search_engine = metadata.get("search_engine", [])
        # 若启用“联网配图”，确保 SearchImage 出现在工具列表中（让模型自己决定 query 并调用工具）
        try:
            want_images = bool(metadata.get("generate_with_images"))
        except Exception:
            want_images = False
        if want_images and isinstance(search_engine, list) and "SearchImage" not in search_engine:
            search_engine = [*search_engine, "SearchImage"]
        # 如果是None，那么没问题，走默认PREFIX_PAGE_PROMPT，如果是空列表，那么使用所有工具
        if search_engine == []:
            search_engine = ["KnowledgeBaseSearch","DocumentSearch","SearchImage"]
        user_id = metadata.get("user_id", "")
        language = metadata.get("language", "chinese")  # 默认中文
        if not user_id and search_engine and "KnowledgeBaseSearch" in search_engine:
            print("当前用户未指定知识库的用户id，无法使用KnowledgeBaseSearch进行搜索，必须去除知识库搜索工具")
            search_engine.remove("KnowledgeBaseSearch")
        # 根据不同的搜索工具，使用不同的prefix的prompt, search_engine为False的时候
        if not search_engine:
            prefix_prompt = prompt.PREFIX_PAGE_PROMPT.format(language=language)
        elif search_engine == ["SearchImage"]:
            prefix_prompt = prompt.PREFIX_PAGE_PROMPT_WITH_IMAGE.format(language=language)
        else:
            tool_names = ", ".join([str(x) for x in search_engine]) if isinstance(search_engine, list) else str(search_engine)
            prefix_prompt = prompt.PREFIX_PAGE_PROMPT_WITH_SEARCH.format(tool_names=tool_names,language=language)
        # 这页ppt的类型
        current_slide_type = current_slide_schema.get("type")
        print(f"当前要生成第{current_slide_index}页的ppt， 类型为：{current_slide_type}， 具体内容为：{current_slide_schema}")
        # 根据不同的类型，形成不同的prompt
        slide_prompt = prompt.prompt_mapper[current_slide_type]
        current_slide_schema_json = json.dumps(current_slide_schema, ensure_ascii=False)

        # 若存在“课程产出全文注入”（来自 main_api 注入区块剥离），则仅作为参考上下文使用
        course_outputs_fulltext = ctx.state.get("course_outputs_fulltext")
        reference_block = ""
        if isinstance(course_outputs_fulltext, str) and course_outputs_fulltext.strip():
            keywords = _extract_keywords_from_slide_schema(current_slide_schema)
            excerpt = _build_reference_excerpt(course_outputs_fulltext, keywords=keywords, max_chars=6000)
            if excerpt:
                header = "# Reference context (course outputs, excerpt)" if _want_english(language) else "# 参考资料（课程产出全文，节选）"
                reference_block = (
                    _build_reference_rules(language)
                    + f"\n{header}\n"
                    + excerpt.strip()
                    + "\n"
                )

        prompt_instruction = (
            prefix_prompt
            + reference_block
            + slide_prompt.format(input_slide_data=current_slide_schema_json, language=language)
        )
        print(f"第{current_slide_index}页的prompt是：{prompt_instruction}")
        return prompt_instruction

# ========== Checker（规则 + 质量双阶段校验，不调用大模型） ==========
class CheckerAgent(BaseAgent):
    """
    规则：
    - 先解析 JSON
    - 再做 schema / 结构校验
    - 最后做内容质量校验
    """
    def __init__(self, **kwargs):
        super().__init__(
            name="CheckerAgent",
            description="规则校验 Writer 输出是否为 JSON（不调用大模型）",
            **kwargs
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        raw = ctx.session.state.get("last_written_raw")
        current_slide_index: int = ctx.session.state.get("current_slide_index", 0)
        outline_json: list = ctx.session.state.get("outline_json")
        current_slide_schema = outline_json[current_slide_index]
        outcome = evaluate_checker_result(raw, current_slide_schema)
        apply_checker_outcome_to_state(ctx.session.state, outcome)
        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text=outcome.summary_text)])
        )
        return

# ========== Controller（推进/终止） ==========
class ControllerAgent(BaseAgent):
    """
    决策：
    - 若校验通过：把 JSON 存入 accumulated 列表，推进 current_slide_index
    - 若校验失败：针对当前页重试，重试次数超过阈值则跳过此页并推进
    - 若已到最后一页：汇总输出并 escalate 终止
    """
    def __init__(self, **kwargs):
        super().__init__(
            name="ControllerAgent",
            description="根据校验结果推进或终止",
            **kwargs
        )

    def _get_retry_map(self, st: Dict[str, Any]) -> Dict[int, int]:
        # 避免 setdefault：若不存在则赋空 dict
        m = st.get("retry_count_map")
        if m is None:
            m = {}
            st["retry_count_map"] = m
        return m

    def _append_accumulated(self, st: Dict[str, Any], item: dict) -> None:
        acc = st.get("generated_slides_content")
        if acc is None:
            acc = []
            st["generated_slides_content"] = acc
        acc.append(item)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        st = ctx.session.state
        ensure_loop_state_initialized(st)
        current_slide_index: int = int(st.get("current_slide_index", 0))

        if bool(st.get("last_validation_passed")):
            data = st.get("last_slide_json")
            if isinstance(data, dict):
                try:
                    data = await maybe_attach_images_to_slide(data, state=st, search_image=SearchImage)
                    st["last_slide_json"] = data
                except Exception as exc:
                    logger.warning("自动配图失败，将跳过 images 注入：%s", exc, exc_info=True)

        decision = advance_or_retry_after_validation(st, max_retries=3)

        if decision.action == "retry":
            print(
                f"第 {current_slide_index} 页{decision.failure_stage or '校验'}失败，准备第 {decision.retry_count} 次重试。"
            )
            return

        if decision.output_text is not None:
            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text=decision.output_text)])
            )

        if decision.action == "advance":
            print(f"第 {current_slide_index} 页已通过校验，进入下一页。")
        elif decision.action == "degrade":
            print(
                f"第 {current_slide_index} 页在 {decision.failure_stage or 'unknown'} 阶段重试超过 3 次，降级跳过并进入下一页。"
            )

        if decision.should_escalate:
            accumulated = st.get("generated_slides_content") or []
            try:
                pretty = json.dumps(accumulated, ensure_ascii=False, indent=2)
            except Exception:
                pretty = str(accumulated)
            print(f"全部页处理完成。汇总如下：\n\n{pretty}")
            yield Event(author=self.name, actions=EventActions(escalate=True))

        return

# ========== Loop 入口 ==========
def my_super_before_agent_callback(callback_context: CallbackContext):
    """
    Loop 启动前的初始化（仅一次）
    """
    st = callback_context.state
    ensure_loop_state_initialized(st)
    return None


def build_ppt_generator_loop_agent() -> LoopAgent:
    """
    构建 PPT 生成 LoopAgent（动态读取环境变量）。

    说明：
    - PPTWriterSubAgent 在初始化时会读取当前环境变量并创建模型；
    - 因此热加载时需要重新 build 整棵 Agent 树，避免 import-time 常量导致配置不生效。
    """
    return LoopAgent(
        name="PPTGeneratorLoopAgent",
        max_iterations=200,  # 给足够大，依赖 Controller 决定终止
        sub_agents=[
            PPTWriterSubAgent(),  # 1) 生成
            CheckerAgent(),  # 2) 规则校验 JSON（不调用大模型）
            ControllerAgent(),  # 3) 控制推进 / 终止
        ],
        before_agent_callback=my_super_before_agent_callback,
    )
