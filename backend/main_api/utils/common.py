import asyncio
import json
import logging
import os
import re
from typing import Any, AsyncGenerator

import httpx

from backend.common.settings_store import access_host_for_bind_host
from backend.main_api.models.schemas import (
    LessonPlan,
    LessonPlanProcedureStep,
    LessonPlanRequest,
)

logger = logging.getLogger(__name__)


def _get_outline_api() -> str:
    return os.environ.get(
        "OUTLINE_API",
        f"http://{access_host_for_bind_host(os.environ.get('HOST', '127.0.0.1'))}:{os.environ.get('OUTLINE_API_PORT', '10001')}",
    )


def _get_content_api() -> str:
    return os.environ.get(
        "CONTENT_API",
        f"http://{access_host_for_bind_host(os.environ.get('HOST', '127.0.0.1'))}:{os.environ.get('CONTENT_API_PORT', '10011')}",
    )


def _encode_sse_data(payload: str) -> bytes:
    """
    将任意文本安全编码为 SSE data 事件，兼容多行内容。
    """
    if payload is None:
        payload = ""

    lines = payload.splitlines()
    has_trailing_newline = payload.endswith("\n")

    if not lines:
        return b"data:\n\n"

    chunks: list[bytes] = []
    for line in lines:
        chunks.append(f"data: {line}\n".encode("utf-8"))
    if has_trailing_newline:
        chunks.append(b"data:\n")
    chunks.append(b"\n")
    return b"".join(chunks)

def _normalize_lesson_template_id(value: str | None) -> str:
    """
    统一归一化教案模板 ID（生成/预览/导出共用）。
    - 未指定：默认 lesson_simple
    - 兼容常见别名：simple/table/form/jnu 等
    """
    tpl = (value or "").strip() or "lesson_simple"
    if tpl in {"default", "simple"}:
        return "lesson_simple"
    if tpl in {"table"}:
        return "lesson_table"
    if tpl in {"form", "jnu", "jnu_form", "lesson_form"}:
        return "lesson_jnu_form"
    return tpl


def _split_objectives_text(text: str) -> list[str]:
    """
    将自由文本教学目标拆成条目列表（用于无 LLM 的兜底生成）。
    """
    raw = (text or "").strip()
    if not raw:
        return []
    bits = re.split(r"[；;。\n]+", raw)
    cleaned: list[str] = []
    for b in bits:
        item = (b or "").strip()
        if not item:
            continue
        if item in cleaned:
            continue
        cleaned.append(item)
    return cleaned


def _guess_procedure_steps_from_outline(outline_md: str, *, max_steps: int = 6) -> list[str]:
    """
    从 Markdown 大纲里猜测教学流程步骤（用于无 LLM 的兜底生成）。
    """
    steps: list[str] = []
    for raw_line in (outline_md or "").splitlines():
        line = (raw_line or "").strip()
        if not line:
            continue
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            if title and title not in steps:
                steps.append(title)
        elif line.startswith(("-", "*", "+")):
            title = line.lstrip("-*+").strip()
            if title and title not in steps:
                steps.append(title)
        if len(steps) >= max_steps:
            break
    return steps


def _fallback_generate_lesson_plan(req: LessonPlanRequest) -> LessonPlan:
    """
    无 LLM 配置时的兜底教案生成：
    - 保证端到端链路可用（SSE 预览 + docx 导出）
    - 质量不追求最优，但内容结构完整、可读
    """
    lang = (req.language or "zh").strip().lower()
    want_english = lang in {"en", "english"}
    tpl = _normalize_lesson_template_id(req.templateId)
    if tpl not in {"lesson_simple", "lesson_table", "lesson_jnu_form"}:
        tpl = "lesson_simple"

    title = (req.title or "").strip() or ("Lesson Plan" if want_english else "教案")
    objectives = _split_objectives_text(req.objectives or "")
    if not objectives:
        objectives = [
            "理解本节课核心概念与关键结论" if not want_english else "Understand the key concepts and core conclusions",
            "能完成基础例题/练习并进行简单迁移" if not want_english else "Solve basic exercises and apply the concept",
        ]
    if tpl == "lesson_jnu_form":
        # 表单模板：目标用于“重点/难点”，确保最后一条为“难点：...”
        diff = None
        rest: list[str] = []
        for item in objectives:
            text = str(item or "").strip()
            if not text:
                continue
            is_diff = bool(re.match(r"^difficulty\s*[:：]", text, re.IGNORECASE)) if want_english else bool(re.match(r"^难点\s*[:：]", text))
            if is_diff and diff is None:
                diff = text
                continue
            rest.append(text)

        if diff is None:
            topic = (req.title or "").strip() or ("this lesson" if want_english else "本节课")
            diff = (
                f"Difficulty: Explain and apply the key reasoning of {topic} in new contexts."
                if want_english
                else f"难点：掌握{topic}的关键推导与应用，并能迁移解决典型问题。"
            )

        objectives = rest + [diff]

    steps = _guess_procedure_steps_from_outline(req.outlineContent or "", max_steps=6)
    if not steps:
        steps = [
            "导入与复习" if not want_english else "Warm-up & review",
            "新知讲解" if not want_english else "Concept introduction",
            "例题与练习" if not want_english else "Examples & practice",
            "总结提升" if not want_english else "Wrap-up",
        ]

    # 简单分配时长（总时长默认 45 分钟）
    total_minutes = 45
    minutes_each = max(5, int(round(total_minutes / max(1, len(steps)))))
    procedure: list[LessonPlanProcedureStep] = []
    for idx, name in enumerate(steps):
        m = minutes_each
        duration = f"{m}分钟" if not want_english else f"{m} min"
        activity = (
            f"围绕「{name}」组织讲解与互动，包含提问、板书要点与即时练习。"
            if not want_english
            else f"Teach and interact around “{name}”, including questions, key points, and quick practice."
        )
        procedure.append(
            LessonPlanProcedureStep(
                step=f"{idx + 1}. {name}",
                duration=duration,
                activity=activity,
            )
        )

    materials = [
        "课件/PPT",
        "板书/白板",
        "练习题/作业纸",
    ] if not want_english else ["Slides", "Whiteboard", "Practice sheets"]
    if tpl == "lesson_jnu_form":
        # 参考资料占位（便于表单模板直接落地填写）
        materials = list(materials) + (["教材/参考书：______"] if not want_english else ["Textbook/Reference: ______"])

    homework = (
        "完成课后练习 1~3 题，并用自己的话总结本课关键结论（不少于 100 字）。"
        if not want_english
        else "Finish exercises 1–3 and summarize the key takeaway in your own words (100+ words)."
    )

    return LessonPlan(
        title=title,
        targetAudience=("中学学生" if not want_english else "Students"),
        duration=("45分钟" if not want_english else "45 min"),
        objectives=objectives,
        materials=materials,
        procedure=procedure,
        homework=homework,
    )


def _try_get_lesson_llm_settings() -> dict[str, str] | None:
    """
    Lesson 生成的模型配置：
    - 优先读取 LESSON_*，未配置则回退到 OUTLINE_*（减少新增配置成本）
    - 仅支持 openai 兼容协议（base_url + /chat/completions）
    - 若缺少必要配置，返回 None（由兜底生成保证链路可用）
    """
    llm_type = (os.getenv("LESSON_TYPE") or os.getenv("OUTLINE_TYPE") or "").strip().lower()
    llm_model = (os.getenv("LESSON_MODEL") or os.getenv("OUTLINE_MODEL") or "").strip()
    llm_api_key = (os.getenv("LESSON_API_KEY") or os.getenv("OUTLINE_API_KEY") or "").strip()
    llm_base_url = (os.getenv("LESSON_BASE_URL") or os.getenv("OUTLINE_BASE_URL") or "https://api.openai.com/v1").strip()

    if not llm_type or not llm_model or not llm_api_key:
        return None
    openai_compatible = {"openai", "ollama", "vllm", "local_openai", "xinference"}
    if llm_type not in openai_compatible:
        raise RuntimeError(f"当前 Lesson 仅支持 openai 兼容协议，检测到 LESSON_TYPE/OUTLINE_TYPE={llm_type}")
    return {"type": llm_type, "model": llm_model, "api_key": llm_api_key, "base_url": llm_base_url}


def _strip_json_code_fence(text: str) -> str:
    """
    兼容模型把 JSON 包在 ```json ... ``` 围栏内的情况。
    """
    s = (text or "").strip()
    if not s.startswith("```"):
        return s
    lines = s.splitlines()
    if len(lines) < 2:
        return s
    if not lines[0].strip().startswith("```"):
        return s
    end_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == "```":
            end_idx = i
            break
    if end_idx <= 0:
        return s
    return "\n".join(lines[1:end_idx]).strip()


def _extract_first_json_object(text: str) -> dict[str, Any]:
    """
    从模型输出中提取第一个 JSON 对象。
    - 允许前后夹杂说明文字
    - 失败则抛出异常，由上层决定兜底策略
    """
    s = _strip_json_code_fence(text)
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("未找到 JSON 对象边界")
    candidate = s[start : end + 1].strip()
    obj = json.loads(candidate)
    if not isinstance(obj, dict):
        raise ValueError("JSON 顶层不是对象")
    return obj


def _build_lesson_system_prompt(*, req: LessonPlanRequest, full_context: str, kb_context: str) -> str:
    """
    Lesson 生成 system prompt（用于 LLM 路径）。
    """
    lang = (req.language or "zh").strip().lower()
    want_english = lang in {"en", "english"}
    tpl = _normalize_lesson_template_id(req.templateId)
    if tpl not in {"lesson_simple", "lesson_table", "lesson_jnu_form"}:
        tpl = "lesson_simple"

    if want_english:
        base = (
            "You are TeachDo's lesson plan generator.\n"
            "Generate a structured lesson plan based on the provided outline.\n"
            "Rules:\n"
            "- Follow the outline structure and do NOT invent topics that are unrelated.\n"
            "- If course outputs (full text, not retrieved) are provided, treat them as reference-only for consistency; do NOT copy verbatim and do NOT reuse its structure.\n"
            "- Output must be STRICT JSON only (no markdown, no code fences).\n"
            "- Keep it practical for classroom use.\n"
        )
    else:
        base = (
            "你是 TeachDo 的教案生成器。\n"
            "请基于给定的大纲生成结构化教案。\n"
            "规则：\n"
            "- 必须参考大纲结构，不要引入无关主题。\n"
            "- 若提供“课程产出（全文，不经检索）”，仅作参考用于术语/事实对齐：不要原文照抄、不要套用其目录/结构，仍以本次大纲为准。\n"
            "- 输出必须是严格 JSON（不要 markdown、不要代码块围栏）。\n"
            "- 内容要可落地、可直接用于课堂。\n"
        )

    if tpl == "lesson_jnu_form":
        if want_english:
            base += (
                "\nTemplate: form-style (fields).\n"
                "- Objectives will be used as Key Points and Difficulty.\n"
                "- Ensure the final objective starts with 'Difficulty:'.\n"
            )
        else:
            base += (
                "\n当前模板：教案表单（字段）。\n"
                "- objectives 将用于“重点/难点”。请确保最后一条以“难点：”开头。\n"
            )

    context_bits: list[str] = []
    title = (req.title or "").strip()
    if title:
        context_bits.append(("Topic: " if want_english else "主题：") + title)
    if req.subject:
        context_bits.append(("Subject: " if want_english else "学科：") + str(req.subject).strip())
    if req.description:
        context_bits.append(("Background: " if want_english else "背景：") + str(req.description).strip())
    if req.objectives:
        context_bits.append(("User objectives: " if want_english else "用户提供的教学目标：") + str(req.objectives).strip())

    outline = (req.outlineContent or "").strip()
    context_bits.append(("Outline (Markdown):\n" if want_english else "课程大纲（Markdown）：\n") + outline)

    if full_context and full_context.strip():
        context_bits.append(
            (
                "Course outputs (full text, not retrieved):\n(Note: reference-only; do NOT copy verbatim; do NOT reuse its structure.)\n"
                if want_english
                else "课程产出（全文，不经检索）：\n（说明：仅供参考，不要原文照抄，不要套用其目录/结构。）\n"
            )
            + full_context.strip()
        )

    if kb_context and kb_context.strip():
        context_bits.append(("Reference snippets (RAG):\n" if want_english else "参考资料检索片段（RAG）：\n") + kb_context.strip())

    return base + "\n\n" + "\n".join(context_bits).strip()


async def _generate_lesson_section_with_llm(
    *,
    llm_settings: dict[str, str],
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.4,
    max_output_chars: int = 20_000,
) -> dict[str, Any]:
    """
    调用 OpenAI 兼容协议生成一个 JSON 片段（section/meta）。
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    text = ""
    async for delta in iter_assistant_text_chunks(
        model=llm_settings["model"],
        api_key=llm_settings["api_key"],
        base_url=llm_settings["base_url"],
        messages=messages,
        temperature=temperature,
    ):
        text += delta
        if len(text) > max_output_chars:
            break

    return _extract_first_json_object(text)



async def iter_assistant_text_chunks(
    *,
    model: str,
    api_key: str,
    base_url: str,
    messages: list[dict[str, str]],
    temperature: float = 0.6,
) -> AsyncGenerator[str, None]:
    """
    通过 OpenAI 兼容协议调用 Chat Completions，并将增量 token 作为文本片段 yield。
    注意：这里不直接向客户端暴露上游 SSE，避免不同兼容网关的格式差异影响前端解析。
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }

    timeout = httpx.Timeout(connect=60.0, write=60.0, pool=60.0, read=None)
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code >= 400:
                text = await resp.aread()
                raise RuntimeError(f"LLM 请求失败：{resp.status_code} {text.decode('utf-8', errors='ignore')}")

            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if not data:
                    continue
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except Exception:
                    # 某些网关可能夹杂非 JSON 行，忽略
                    logger.debug("忽略非 JSON SSE 数据行: %r", data, exc_info=True)
                    continue

                # OpenAI 标准：choices[0].delta.content
                delta = None
                try:
                    choices = obj.get("choices") if isinstance(obj, dict) else None
                    if isinstance(choices, list) and choices:
                        choice0 = choices[0] if isinstance(choices[0], dict) else {}
                        delta_obj = choice0.get("delta") if isinstance(choice0.get("delta"), dict) else {}
                        delta = delta_obj.get("content")
                        if not delta:
                            # 兼容少数实现：message.content 直接返回完整段落
                            msg_obj = choice0.get("message") if isinstance(choice0.get("message"), dict) else {}
                            delta = msg_obj.get("content")
                except Exception:
                    logger.debug("提取 SSE delta 失败", exc_info=True)
                    delta = None

                if isinstance(delta, str) and delta:
                    yield delta


