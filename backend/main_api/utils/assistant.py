import asyncio
import json
import logging
import os
from typing import AsyncGenerator

from backend.main_api.models.schemas import AssistantChatMessage
from backend.main_api.utils.common import iter_assistant_text_chunks
from backend.main_api.utils.common import _encode_sse_data

logger = logging.getLogger(__name__)


def _pick_last_user_message(messages: list[AssistantChatMessage]) -> str:
    """
    从历史消息中找到最后一条 user 消息，作为 RAG 检索 query。
    """
    for msg in reversed(messages or []):
        if msg.role == "user" and (msg.content or "").strip():
            return msg.content.strip()
    return ""


def _build_assistant_system_prompt(
    *,
    material: object,
    full_context: str,
    kb_context: str,
    language: str,
) -> str:
    """
    构建助教的 system prompt：
    - 教学资料上下文（标题/学科/简介/目标）
    - KB 检索片段（若有）
    """
    lang = (language or "zh").strip().lower()
    want_english = lang in {"en", "english"}

    if want_english:
        base = (
            "You are TeachDo's AI teaching assistant.\n"
            "Your goal is to help teachers design lessons, explain concepts, generate exercises, and answer questions.\n"
            "Rules:\n"
            "- Be accurate and practical.\n"
            "- If the user question is ambiguous, ask 1-2 clarifying questions.\n"
            "- When course outputs (full text) are provided, prioritize them as context.\n"
            "- When KB snippets (RAG) are provided, use them as grounding; if insufficient, say so.\n"
            "- Use concise bullets/steps when helpful.\n"
        )
    else:
        base = (
            "你是 TeachDo 的 AI 教学助教。\n"
            "你的目标是帮助教师进行教学设计、知识点讲解、题目生成与答疑。\n"
            "规则：\n"
            "- 回答要准确、可操作。\n"
            "- 问题不清晰时，先问 1~2 个澄清问题。\n"
            "- 若提供了课程产出全文（不经检索），应优先基于全文作答。\n"
            "- 若提供了参考资料检索片段（RAG），应优先基于片段作答；片段不足时要明确说明。\n"
            "- 需要时用条目/步骤输出。\n"
        )

    context_bits: list[str] = []
    if material and (material.title or "").strip():
        title = material.title.strip()
        if want_english:
            context_bits.append(f"Current teaching material: {title}")
        else:
            context_bits.append(f"当前教学资料：{title}")
        if material.subject:
            context_bits.append(("Subject: " if want_english else "学科：") + str(material.subject).strip())
        if material.description:
            context_bits.append(("Description: " if want_english else "简介：") + str(material.description).strip())
        if material.objectives:
            context_bits.append(("Objectives: " if want_english else "教学目标：") + str(material.objectives).strip())

    if full_context and full_context.strip():
        if want_english:
            context_bits.append("Course outputs (full text, not retrieved):\n" + full_context.strip())
        else:
            context_bits.append("课程产出（全文，不经检索）：\n" + full_context.strip())

    if kb_context and kb_context.strip():
        if want_english:
            context_bits.append("Reference snippets (RAG):\n" + kb_context.strip())
        else:
            context_bits.append("参考资料检索片段（RAG）：\n" + kb_context.strip())

    if not context_bits:
        return base

    return base + "\n\n" + "\n".join(context_bits).strip()


def _get_assistant_llm_settings() -> dict[str, str]:
    """
    助教模型配置：
    - 优先读取 ASSISTANT_*，若未配置则回退到 OUTLINE_*（保持与计划一致，减少新增配置成本）。
    - 当前仅支持 openai 协议（OpenAI 兼容 base_url）。
    """
    llm_type = (os.getenv("ASSISTANT_TYPE") or os.getenv("OUTLINE_TYPE") or "").strip().lower()
    llm_model = (os.getenv("ASSISTANT_MODEL") or os.getenv("OUTLINE_MODEL") or "").strip()
    llm_api_key = (os.getenv("ASSISTANT_API_KEY") or os.getenv("OUTLINE_API_KEY") or "").strip()
    llm_base_url = (os.getenv("ASSISTANT_BASE_URL") or os.getenv("OUTLINE_BASE_URL") or "https://api.openai.com/v1").strip()

    if not llm_type or not llm_model:
        raise RuntimeError("助教模型未配置，请设置 ASSISTANT_TYPE/ASSISTANT_MODEL（或复用 OUTLINE_* 配置）")
    openai_compatible = {"openai", "ollama", "vllm", "local_openai", "xinference"}
    if llm_type not in openai_compatible:
        raise RuntimeError(f"当前助教仅支持 openai 兼容协议，检测到 ASSISTANT_TYPE/OUTLINE_TYPE={llm_type}")
    if not llm_api_key:
        raise RuntimeError("缺少助教模型 API Key，请设置 ASSISTANT_API_KEY（或复用 OUTLINE_API_KEY）")

    return {"type": llm_type, "model": llm_model, "api_key": llm_api_key, "base_url": llm_base_url}


async def stream_assistant_sse(
    *,
    llm_settings: dict[str, str],
    messages: list[dict[str, str]],
) -> AsyncGenerator[bytes, None]:
    """
    将助教回答以 SSE 向前端流式输出（data: 增量文本，结束 data: [DONE]）。
    若发生异常，发送一条 type=error 的 JSON 事件后结束。
    """
    try:
        async for delta in iter_assistant_text_chunks(
            model=llm_settings["model"],
            api_key=llm_settings["api_key"],
            base_url=llm_settings["base_url"],
            messages=messages,
        ):
            yield _encode_sse_data(delta)
    except asyncio.CancelledError:
        logger.info("客户端已断开 /tools/assistant_chat SSE 连接，提前结束流")
        raise
    except Exception as exc:
        logger.error("助教对话流异常: %s", exc, exc_info=True)
        payload = json.dumps(
            {
                "type": "error",
                "text": f"助教服务异常：{exc}",
            },
            ensure_ascii=False,
        )
        yield _encode_sse_data(payload)
    finally:
        yield b"data: [DONE]\n\n"
