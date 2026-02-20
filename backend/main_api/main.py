import asyncio
import json
import io
import random
import re
import os
from pathlib import Path
from dotenv import dotenv_values
from fastapi import FastAPI, UploadFile, File
import time
import logging
from pydantic import BaseModel
import uuid
import httpx
from urllib.parse import quote
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import UploadFile, File, HTTPException, Form
from fastapi import FastAPI, HTTPException, Query, Request, Response
from typing import AsyncGenerator, Literal, Any
try:
    # 兼容在 `backend/main_api` 目录下直接运行（例如 `uvicorn main:app`）
    from outline_client import A2AOutlineClientWrapper
    from content_client import A2AContentClientWrapper
except ImportError:  # pragma: no cover - 兼容以包方式导入（用于单元测试等）
    from backend.main_api.outline_client import A2AOutlineClientWrapper
    from backend.main_api.content_client import A2AContentClientWrapper

logger = logging.getLogger(__name__)

def _find_repo_root(start: Path) -> Path:
    """
    向上查找项目根目录：
    - 优先命中 `.git/` 或 `env_template.txt`
    - 若不存在（例如 docker 镜像只拷贝了单服务目录），退化为包含 `main.py` 的目录
    """
    start_dir = start if start.is_dir() else start.parent
    fallback_service_root: Path | None = None

    current = start_dir
    while True:
        if (current / ".git").exists() or (current / "env_template.txt").exists():
            return current
        if fallback_service_root is None and (current / "main.py").exists():
            fallback_service_root = current

        parent = current.parent
        if parent == current:
            break
        current = parent

    return fallback_service_root or Path.cwd()


def _load_env_files() -> None:
    """
    统一环境变量加载优先级（不覆盖系统环境变量）：
    1) 项目根目录 `.env`
    2) 当前服务目录 `.env`（可选覆盖）
    """
    merged: dict[str, str] = {}

    repo_root = _find_repo_root(Path(__file__).resolve())
    root_env = repo_root / ".env"
    if root_env.exists():
        merged.update({k: v for k, v in dotenv_values(root_env).items() if v is not None})

    service_env = Path(__file__).resolve().parent / ".env"
    if service_env.exists():
        merged.update({k: v for k, v in dotenv_values(service_env).items() if v is not None})

    for k, v in merged.items():
        if k not in os.environ:
            os.environ[k] = v


_load_env_files()

OUTLINE_API = os.environ.get("OUTLINE_API", f"http://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('OUTLINE_API_PORT', '10001')}")
CONTENT_API = os.environ.get("CONTENT_API", f"http://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('CONTENT_API_PORT', '10011')}")
app = FastAPI()

# Allow CORS for the frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AipptRequest(BaseModel):
    content: str
    language: str
    model: str
    stream: bool


class AssistantChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AssistantMaterialContext(BaseModel):
    title: str
    subject: str | None = None
    description: str | None = None
    objectives: str | None = None


class AssistantChatRequest(BaseModel):
    """
    助教对话请求（全局单会话，历史由前端维护并在每次请求时透传）。
    """

    messages: list[AssistantChatMessage]
    user_id: str = "default_user"
    kb_file_ids: list[str] | None = None
    material: AssistantMaterialContext | None = None
    language: str = "zh"


class LessonPlanProcedureStep(BaseModel):
    step: str
    duration: str
    activity: str


class LessonPlan(BaseModel):
    """
    LessonPlan（与 teachdo-frontend/types.ts 对齐）
    """

    title: str
    targetAudience: str
    duration: str
    objectives: list[str]
    materials: list[str]
    procedure: list[LessonPlanProcedureStep]
    homework: str


class LessonPlanRequest(BaseModel):
    title: str
    subject: str | None = None
    description: str | None = None
    objectives: str | None = None
    outlineContent: str
    language: str = "zh"
    sessionId: str | None = None
    user_id: str | None = None
    kb_file_ids: list[str] | None = None


class LessonStyle(BaseModel):
    """
    Lesson 导出样式（V1）
    - 作为“展示/导出层”参数，不参与 LessonPlan 内容生成
    """

    fontZh: str = "微软雅黑"
    titleSizePt: int = 20
    h1SizePt: int = 16
    h2SizePt: int = 14
    bodySizePt: int = 12
    lineSpacing: float = 1.5

    # 页边距（cm）
    marginTopCm: float = 2.54
    marginBottomCm: float = 2.54
    marginLeftCm: float = 2.54
    marginRightCm: float = 2.54


class LessonExportDocxRequest(BaseModel):
    lessonPlan: LessonPlan
    style: LessonStyle | None = None
    language: str | None = None


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

    title = (req.title or "").strip() or ("Lesson Plan" if want_english else "教案")
    objectives = _split_objectives_text(req.objectives or "")
    if not objectives:
        objectives = [
            "理解本节课核心概念与关键结论" if not want_english else "Understand the key concepts and core conclusions",
            "能完成基础例题/练习并进行简单迁移" if not want_english else "Solve basic exercises and apply the concept",
        ]

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
    if llm_type != "openai":
        raise RuntimeError(f"当前 Lesson 仅支持 openai 协议，检测到 LESSON_TYPE/OUTLINE_TYPE={llm_type}")
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


def _build_lesson_system_prompt(*, req: LessonPlanRequest, kb_context: str) -> str:
    """
    Lesson 生成 system prompt（用于 LLM 路径）。
    """
    lang = (req.language or "zh").strip().lower()
    want_english = lang in {"en", "english"}

    if want_english:
        base = (
            "You are TeachDo's lesson plan generator.\n"
            "Generate a structured lesson plan based on the provided outline.\n"
            "Rules:\n"
            "- Follow the outline structure and do NOT invent topics that are unrelated.\n"
            "- Output must be STRICT JSON only (no markdown, no code fences).\n"
            "- Keep it practical for classroom use.\n"
        )
    else:
        base = (
            "你是 TeachDo 的教案生成器。\n"
            "请基于给定的大纲生成结构化教案。\n"
            "规则：\n"
            "- 必须参考大纲结构，不要引入无关主题。\n"
            "- 输出必须是严格 JSON（不要 markdown、不要代码块围栏）。\n"
            "- 内容要可落地、可直接用于课堂。\n"
        )

    context_bits: list[str] = []
    title = (req.title or "").strip()
    if title:
        context_bits.append(("Title: " if want_english else "标题：") + title)
    if req.subject:
        context_bits.append(("Subject: " if want_english else "学科：") + str(req.subject).strip())
    if req.description:
        context_bits.append(("Background: " if want_english else "背景：") + str(req.description).strip())
    if req.objectives:
        context_bits.append(("User objectives: " if want_english else "用户提供的教学目标：") + str(req.objectives).strip())

    outline = (req.outlineContent or "").strip()
    context_bits.append(("Outline (Markdown):\n" if want_english else "课程大纲（Markdown）：\n") + outline)

    if kb_context and kb_context.strip():
        context_bits.append(("KB snippets:\n" if want_english else "知识库检索片段：\n") + kb_context.strip())

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


async def stream_lesson_plan_sse(req: LessonPlanRequest) -> AsyncGenerator[bytes, None]:
    """
    LessonPlan SSE：
    - data: {"type":"section",...}
    - data: {"type":"final","data":{LessonPlan}}
    - data: {"type":"error","text":"..."}
    - data: [DONE]
    """
    outline = (req.outlineContent or "").strip()
    if not outline:
        payload = json.dumps({"type": "error", "text": "outlineContent 不能为空"}, ensure_ascii=False, separators=(",", ":"))
        yield _encode_sse_data(payload)
        yield b"data: [DONE]\n\n"
        return

    user_id = str(req.user_id or "default_user")
    resolved_kb_file_ids = _normalize_kb_file_ids(req.kb_file_ids)
    personaldb_url = _get_personaldb_url()

    kb_context = ""
    if resolved_kb_file_ids and personaldb_url and await _is_personaldb_ready(personaldb_url):
        # query 选用 “标题 + 大纲” 的组合，尽量贴近教案生成语义
        query = f"{(req.title or '').strip()}\n{outline}".strip()
        kb_context = await _search_personaldb_kb_context(
            personaldb_url,
            user_id=user_id,
            query=query,
            kb_file_ids=resolved_kb_file_ids,
            topk=5,
        )

    llm_settings: dict[str, str] | None = None
    try:
        llm_settings = _try_get_lesson_llm_settings()
    except Exception as exc:
        # 配置异常：作为错误事件返回，但仍保证 [DONE] 收尾
        payload = json.dumps({"type": "error", "text": f"Lesson 模型配置错误：{exc}"}, ensure_ascii=False, separators=(",", ":"))
        yield _encode_sse_data(payload)
        yield b"data: [DONE]\n\n"
        return

    # 兜底：无 LLM 配置时，直接按 outline 生成一个可用版本
    if not llm_settings:
        plan = _fallback_generate_lesson_plan(req)
        yield _encode_sse_data(json.dumps({"type": "section", "section": "objectives", "data": plan.objectives}, ensure_ascii=False, separators=(",", ":")))
        yield _encode_sse_data(json.dumps({"type": "section", "section": "materials", "data": plan.materials}, ensure_ascii=False, separators=(",", ":")))
        yield _encode_sse_data(json.dumps({"type": "section", "section": "procedure", "data": [p.model_dump() for p in plan.procedure]}, ensure_ascii=False, separators=(",", ":")))
        yield _encode_sse_data(json.dumps({"type": "section", "section": "homework", "data": plan.homework}, ensure_ascii=False, separators=(",", ":")))
        yield _encode_sse_data(json.dumps({"type": "final", "data": plan.model_dump()}, ensure_ascii=False, separators=(",", ":")))
        yield b"data: [DONE]\n\n"
        return

    system_prompt = _build_lesson_system_prompt(req=req, kb_context=kb_context)
    lang = (req.language or "zh").strip().lower()
    want_english = lang in {"en", "english"}

    last_flush = asyncio.get_event_loop().time()

    try:
        # meta
        meta_prompt = (
            'Return STRICT JSON only: {"targetAudience":"...","duration":"..."}.\n'
            'duration should be like "45分钟" (zh) or "45 min" (en).'
            if want_english
            else '仅输出严格 JSON：{"targetAudience":"...","duration":"..."}。\n'
                 'duration 形如 "45分钟"。'
        )
        meta = await _generate_lesson_section_with_llm(
            llm_settings=llm_settings,
            system_prompt=system_prompt,
            user_prompt=meta_prompt,
            temperature=0.3,
        )
        target_audience = str(meta.get("targetAudience") or ("Students" if want_english else "中学学生")).strip() or ("Students" if want_english else "中学学生")
        duration = str(meta.get("duration") or ("45 min" if want_english else "45分钟")).strip() or ("45 min" if want_english else "45分钟")

        # objectives
        obj_prompt = (
            'Return STRICT JSON only: {"objectives":["..."]}.\n'
            "Write 3-6 concise objectives."
            if want_english
            else '仅输出严格 JSON：{"objectives":["..."]}。\n'
                 "写 3~6 条可执行的教学目标。"
        )
        obj = await _generate_lesson_section_with_llm(
            llm_settings=llm_settings,
            system_prompt=system_prompt,
            user_prompt=obj_prompt,
            temperature=0.4,
        )
        objectives = obj.get("objectives")
        if not isinstance(objectives, list):
            objectives = []
        objectives = [str(x).strip() for x in objectives if str(x).strip()]
        if not objectives:
            objectives = _fallback_generate_lesson_plan(req).objectives

        # 心跳：每10秒发一次注释，避免某些代理断连接
        now = asyncio.get_event_loop().time()
        if now - last_flush > 10:
            yield b": keep-alive\n\n"
            last_flush = now

        yield _encode_sse_data(json.dumps({"type": "section", "section": "objectives", "data": objectives}, ensure_ascii=False, separators=(",", ":")))

        # materials
        mat_prompt = (
            'Return STRICT JSON only: {"materials":["..."]}.\n'
            "List 3-8 materials/tools needed."
            if want_english
            else '仅输出严格 JSON：{"materials":["..."]}。\n'
                 "列出 3~8 项教学材料/工具。"
        )
        mat = await _generate_lesson_section_with_llm(
            llm_settings=llm_settings,
            system_prompt=system_prompt,
            user_prompt=mat_prompt,
            temperature=0.4,
        )
        materials = mat.get("materials")
        if not isinstance(materials, list):
            materials = []
        materials = [str(x).strip() for x in materials if str(x).strip()]
        if not materials:
            materials = _fallback_generate_lesson_plan(req).materials

        now = asyncio.get_event_loop().time()
        if now - last_flush > 10:
            yield b": keep-alive\n\n"
            last_flush = now

        yield _encode_sse_data(json.dumps({"type": "section", "section": "materials", "data": materials}, ensure_ascii=False, separators=(",", ":")))

        # procedure
        proc_prompt = (
            'Return STRICT JSON only: {"procedure":[{"step":"...","duration":"...","activity":"..."}]}.\n'
            "Write 4-8 steps; duration like '5 min'."
            if want_english
            else '仅输出严格 JSON：{"procedure":[{"step":"...","duration":"...","activity":"..."}]}。\n'
                 "写 4~8 步教学流程；duration 形如 '5分钟'。"
        )
        proc = await _generate_lesson_section_with_llm(
            llm_settings=llm_settings,
            system_prompt=system_prompt,
            user_prompt=proc_prompt,
            temperature=0.5,
        )
        procedure_raw = proc.get("procedure")
        procedure: list[LessonPlanProcedureStep] = []
        if isinstance(procedure_raw, list):
            for item in procedure_raw:
                if not isinstance(item, dict):
                    continue
                step = str(item.get("step") or "").strip()
                dur = str(item.get("duration") or "").strip()
                act = str(item.get("activity") or "").strip()
                if not step or not act:
                    continue
                if not dur:
                    dur = "5 min" if want_english else "5分钟"
                procedure.append(LessonPlanProcedureStep(step=step, duration=dur, activity=act))
        if not procedure:
            procedure = _fallback_generate_lesson_plan(req).procedure

        now = asyncio.get_event_loop().time()
        if now - last_flush > 10:
            yield b": keep-alive\n\n"
            last_flush = now

        yield _encode_sse_data(json.dumps({"type": "section", "section": "procedure", "data": [p.model_dump() for p in procedure]}, ensure_ascii=False, separators=(",", ":")))

        # homework
        hw_prompt = (
            'Return STRICT JSON only: {"homework":"..."}.\n'
            "Keep it concise."
            if want_english
            else '仅输出严格 JSON：{"homework":"..."}。\n'
                 "内容简洁可执行。"
        )
        hw = await _generate_lesson_section_with_llm(
            llm_settings=llm_settings,
            system_prompt=system_prompt,
            user_prompt=hw_prompt,
            temperature=0.4,
        )
        homework = str(hw.get("homework") or "").strip()
        if not homework:
            homework = _fallback_generate_lesson_plan(req).homework

        now = asyncio.get_event_loop().time()
        if now - last_flush > 10:
            yield b": keep-alive\n\n"
            last_flush = now

        yield _encode_sse_data(json.dumps({"type": "section", "section": "homework", "data": homework}, ensure_ascii=False, separators=(",", ":")))

        plan = LessonPlan(
            title=(req.title or "").strip() or ("Lesson Plan" if want_english else "教案"),
            targetAudience=target_audience,
            duration=duration,
            objectives=objectives,
            materials=materials,
            procedure=procedure,
            homework=homework,
        )
        yield _encode_sse_data(json.dumps({"type": "final", "data": plan.model_dump()}, ensure_ascii=False, separators=(",", ":")))
    except asyncio.CancelledError:
        logger.info("客户端已断开 /tools/lesson_plan SSE 连接，提前结束流")
        raise
    except Exception as exc:
        logger.error("LessonPlan 生成流异常: %s", exc, exc_info=True)
        payload = json.dumps({"type": "error", "text": f"教案生成异常：{exc}"}, ensure_ascii=False, separators=(",", ":"))
        yield _encode_sse_data(payload)
    finally:
        yield b"data: [DONE]\n\n"

async def iter_outline_text_chunks(prompt: str, language: str = "chinese"):
    """
    抽象出大纲 Agent 的文本增量迭代器：
    - 只关心 chunk_data["type"] == "text" 的部分
    - 统一日志与空文本过滤
    """
    outline_wrapper = A2AOutlineClientWrapper(session_id=uuid.uuid4().hex, agent_url=OUTLINE_API)
    async for chunk_data in outline_wrapper.generate(prompt, language=language):
        logger.info(f"生成大纲输出的chunk_data: {chunk_data}")
        chunk_type = chunk_data.get("type")

        if chunk_type == "text":
            text = chunk_data.get("text") or ""
            if not text:
                continue
            yield text


async def stream_outline_sse(prompt: str, language: str = "chinese"):
    """
    将大纲 Agent 的响应以 SSE 形式向前端流式输出。
    - media_type: text/event-stream
    - 每个 chunk_data["text"] 作为一条 SSE 事件发送
    - 如 text 内部包含换行，按 SSE 规范拆成多行 data:
    - 结束时发送 data: [DONE]
    """
    async for text in iter_outline_text_chunks(prompt, language):
            # 按行拆分，遵守 SSE 规范：一条事件内多行 data:
            lines = text.splitlines()
            # 如果 text 以换行结尾，splitlines() 会吞掉末尾空行，这里记录一下
            has_trailing_newline = text.endswith("\n")

            if not lines:
                # 纯换行的情况，例如 text == "\n" 或 "\n\n"
                # 用一个空 data 行表示，然后前端按照事件边界追加换行
                yield b"data:\n\n"
            else:
                for line in lines:
                    # 每一行作为一条 data: 行
                    yield f"data: {line}\n".encode("utf-8")
                if has_trailing_newline:
                    # 保留结尾换行：再补一个空 data 行
                    yield b"data:\n"
            # 事件结束
            yield b"\n"

    # 目前前端不依赖 artifact/metadata/final 这几类事件，这里仅记录日志即可
    # 如果后续需要，可以在此扩展不同类型的 SSE 事件

    # 显式结束信号，前端据此收尾
    yield b"data: [DONE]\n\n"


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


@app.post("/tools/aippt_outline")
async def aippt_outline(request: AipptRequest):
    assert request.stream, "只支持流式的返回大纲"
    logger.info(f"前端*outline***=====>用户输入：{request.language}")
    async def event_generator():
        async for chunk in stream_outline_sse(request.content, request.language):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/tools/aippt_outline_unified")
async def aippt_outline_unified(
    content: str = Form(None),           # 主题文本（可选）
    file: UploadFile = File(None),       # 上传文件（可选）
    language: str = Form("chinese"),
    user_id: str = Form("default_user"),
    folder_id: int | str = Form(0),
    file_type: str | None = Form(None),
    kb_file_ids: list[str] | None = Form(None),  # 可选：限定从哪些 KB 文件检索参考片段
):
    """
    统一的大纲生成 API，支持两种模式：
    - 主题模式：只传 content，根据主题生成大纲
    - 文档模式：传 file，解析文档后生成大纲
    - 混合模式：同时传 content 和 file，以文档为主，主题作为补充上下文
    """
    content_text = (content or "").strip()
    has_content = bool(content_text)
    has_file = file is not None

    # 主题是必填的
    if not has_content:
        raise HTTPException(status_code=400, detail="请提供主题")

    file_content = ""
    personaldb_url = _get_personaldb_url()

    # 如果有文件，先解析文件内容
    if has_file:
        if not personaldb_url:
            raise HTTPException(status_code=500, detail="PERSONAL_DB 未配置")

        # 生成 fileId
        file_id = str(int(time.time() * 1000))

        # 推断 fileType
        actual_file_type = file_type
        if not actual_file_type and file.filename and "." in file.filename:
            actual_file_type = file.filename.rsplit(".", 1)[-1]

        # 组装请求数据
        data = {
            "userId": str(user_id),
            "fileId": file_id,
            "folderId": str(folder_id),
        }
        if actual_file_type:
            data["fileType"] = actual_file_type

        # 读取文件内容
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="文件内容为空")

        files_payload = {
            "file": (
                file.filename or "uploaded_file",
                file_bytes,
                file.content_type or "application/octet-stream",
            )
        }

        upload_url = f"{personaldb_url}/upload/"

        # 内部服务调用（personaldb）不应受系统代理环境变量影响
        async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(360.0)) as client:
            try:
                resp = await client.post(
                    upload_url,
                    data=data,
                    files=files_payload,
                )
                if resp.status_code >= 400:
                    logger.info(f"[personaldb {resp.status_code}] {resp.text}")
                    resp.raise_for_status()

                try:
                    result = resp.json()
                except ValueError:
                    raise HTTPException(status_code=502, detail=f"personaldb 返回的不是 JSON：{resp.text}")

                markdown_content = result.get("markdown_content")
                if markdown_content is None:
                    raise HTTPException(status_code=500, detail="personaldb 响应缺少 'markdown_content'")

                file_content = markdown_content

            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="Request to personaldb timed out.")
            except httpx.HTTPStatusError as exc:
                raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
            except httpx.RequestError as exc:
                raise HTTPException(status_code=500, detail=f"Error connecting to personaldb: {exc}")

    kb_context = ""
    resolved_kb_file_ids = _normalize_kb_file_ids(kb_file_ids)
    if resolved_kb_file_ids:
        if personaldb_url and await _is_personaldb_ready(personaldb_url):
            kb_context = await _search_personaldb_kb_context(
                personaldb_url,
                user_id=str(user_id),
                query=content_text,
                kb_file_ids=resolved_kb_file_ids,
            )
        else:
            logger.info("personaldb 不可用，跳过 kb_file_ids 检索增强：%s", personaldb_url)

    prompt_parts: list[str] = [content_text]
    if file_content:
        prompt_parts.append(f"参考文档内容（来自你上传的文件）：\n{file_content}")
    if kb_context:
        prompt_parts.append(f"知识库检索结果（从你选择的知识库文件中检索，仅供参考）：\n{kb_context}")
    prompt = "\n\n".join(prompt_parts)

    logger.info(f"统一大纲API*outline***=====>：language={language}, has_file={has_file}, has_content={has_content}")

    async def event_generator():
        async for chunk in stream_outline_sse(prompt, language):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/tools/aippt_outline_from_file")
async def aippt_outline_from_file(
    user_id: int|str = Form(...),
    file: UploadFile = File(None),  # 允许缺省，这样我们可以决定走 file 或 url
    url: str | None = Form(None),
    folder_id: int|str = Form(0),
    file_type: str | None = Form(None),
    language: str = Form("chinese"),  # 添加language参数，默认为chinese
):
    """
    对齐 personaldb 的 /upload/：
    - 必填: userId, fileId
    - 可选: folderId (默认0), fileType
    - file 与 url 互斥，至少一个
    """
    personaldb_api_url = os.getenv("PERSONAL_DB")
    if not personaldb_api_url:
        raise HTTPException(status_code=500, detail="PERSONAL_DB 未配置")

    # 互斥校验（与 personaldb 完全一致）
    has_file = file is not None
    has_url = bool(url and url.strip())

    # 生成 fileId（字符串更稳；personaldb 会 int()）
    file_id = str(int(time.time() * 1000))

    # 推断 fileType（当上传文件时且未显式传入）
    if has_file and not file_type:
        if file.filename and "." in file.filename:
            file_type = file.filename.rsplit(".", 1)[-1]
        else:
            file_type = "unknown"

    # 组装 multipart/form-data
    # 注意：即使是 url 分支，也仍用 multipart，personaldb 也能解析 form
    data = {
        "userId": str(user_id),
        "fileId": file_id,
        "folderId": str(folder_id),
    }
    if file_type:
        data["fileType"] = file_type
    if has_url:
        data["url"] = url.strip()

    files_payload = None
    if has_file:
        # 读取一次到内存，httpx 需要 (filename, bytes/obj, content_type)
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="文件内容为空")
        files_payload = {
            "file": (
                file.filename or "uploaded_file",
                file_bytes,
                file.content_type or "application/octet-stream",
            )
        }

    upload_url = f"{personaldb_api_url.rstrip('/')}/upload/"

    # 内部服务调用（personaldb）不应受系统代理环境变量影响
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            resp = await client.post(
                upload_url,
                data=data,
                files=files_payload,
                timeout=360.0,
            )
            # 不直接 raise，先打日志方便定位
            if resp.status_code >= 400:
                # 打印下游返回体，personaldb 对错误信息写得很清楚
                logger.info(f"[personaldb {resp.status_code}] {resp.text}")
                resp.raise_for_status()

            # personaldb 的处理函数最终会返回一个 JSON（你上游期望里要有 markdown_content）
            try:
                result = resp.json()
            except ValueError:
                raise HTTPException(status_code=502, detail=f"personaldb 返回的不是 JSON：{resp.text}")

            markdown_content = result.get("markdown_content")
            if markdown_content is None:
                raise HTTPException(status_code=500, detail="personaldb 响应缺少 'markdown_content'")
            logger.info(f"本地上传文件*outline***=====>：{ {'language': language} }")

            async def event_generator():
                async for chunk in stream_outline_sse(markdown_content, language):
                    yield chunk

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache, no-transform",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request to personaldb timed out.")
        except httpx.HTTPStatusError as exc:
            # 透传 personaldb 的错误详情，便于你在日志里看到具体字段问题
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Error connecting to personaldb: {exc}")

class AipptContentRequest(BaseModel):
    content: str
    language: str = "zh"  #默认中文
    sessionId: str = ""  # 当使用知识库时，需要根据用户的user_id查询对应的知识库
    generateFromUploadedFile: bool = False  # 是否从上传的文件中生成PPT内容
    generateFromWebSearch: bool = True  # 是否从网络搜索中生成PPT内容
    kb_folder_ids: list[int] | None = None  # 仅当启用知识库检索时生效，用于过滤可检索的 folder_id
    kb_file_ids: list[str] | None = None  # 仅当启用知识库检索时生效，用于过滤可检索的 file_id（更精确）

def _kb_ok(data):
    return {"ok": True, "data": data}


def _kb_error(code: str, message: str, status_code: int = 500):
    return JSONResponse(
        status_code=status_code,
        content={"ok": False, "error": {"code": code, "message": message}},
    )


def _kb_safe_filename(name: str) -> str:
    # 避免 header 注入与路径穿越
    safe = (name or "").strip().replace("\\", "_").replace("/", "_")
    safe = safe.replace("\r", "_").replace("\n", "_").replace("\t", "_")
    return safe


def _kb_build_export_filename(file_name: str, file_type: str, file_id: str) -> str:
    base = _kb_safe_filename(file_name) or _kb_safe_filename(file_id) or "export"
    base = base or "export"

    lower = base.lower()
    if "." in Path(base).name:
        # 已带后缀：若不是可读文本后缀，则追加 .md
        if lower.endswith((".md", ".txt")):
            return base
        return f"{base}.md"

    ext = (file_type or "").strip().lower().lstrip(".")
    if ext in {"md", "markdown"}:
        return f"{base}.md"
    if ext in {"txt", "text"}:
        return f"{base}.txt"
    if ext and ext not in {"unknown"}:
        return f"{base}.{ext}.md"
    return f"{base}.md"


def _get_personaldb_url() -> str | None:
    url = os.environ.get("PERSONAL_DB")
    return url.rstrip("/") if url else None


async def _is_personaldb_ready(personaldb_url: str) -> bool:
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(2.0)) as client:
            resp = await client.get(f"{personaldb_url}/healthz")
            return resp.status_code == 200
    except Exception:
        return False


def _normalize_kb_file_ids(kb_file_ids: list[str] | None) -> list[str]:
    """
    归一化 kb_file_ids：
    - 去空白
    - 去重（保持稳定顺序）
    """
    if not isinstance(kb_file_ids, list) or not kb_file_ids:
        return []
    seen: set[str] = set()
    resolved: list[str] = []
    for raw in kb_file_ids:
        sid = str(raw).strip()
        if not sid or sid in seen:
            continue
        seen.add(sid)
        resolved.append(sid)
    return resolved


def _format_personaldb_search_context(
    result: object,
    *,
    max_chunks: int = 5,
    max_total_chars: int = 4000,
    max_chunk_chars: int = 800,
) -> str:
    """
    将 personaldb /search 的返回格式化为可拼进 prompt 的参考内容。
    约束：
    - 限制总长度，避免 prompt 过大导致模型效果变差或超限
    - 每个 chunk 截断
    """
    if not isinstance(result, dict):
        return ""

    documents = result.get("documents")
    metadatas = result.get("metadatas")
    distances = result.get("distances")

    docs_row: list[object] = []
    metas_row: list[object] = []
    dists_row: list[object] = []

    if isinstance(documents, list) and documents and isinstance(documents[0], list):
        docs_row = documents[0]
    if isinstance(metadatas, list) and metadatas and isinstance(metadatas[0], list):
        metas_row = metadatas[0]
    if isinstance(distances, list) and distances and isinstance(distances[0], list):
        dists_row = distances[0]

    blocks: list[str] = []
    total = 0
    for idx, doc in enumerate(docs_row):
        if not isinstance(doc, str):
            continue
        text = doc.strip()
        if not text:
            continue

        meta = metas_row[idx] if idx < len(metas_row) else None
        file_id = ""
        file_name = ""
        folder_id = None
        if isinstance(meta, dict):
            file_id = str(meta.get("file_id") or meta.get("fileId") or "").strip()
            file_name = str(meta.get("file_name") or meta.get("fileName") or "").strip()
            folder_id = meta.get("folder_id") if meta.get("folder_id") is not None else meta.get("folderId")

        dist = dists_row[idx] if idx < len(dists_row) else None
        dist_str = ""
        if dist is not None:
            try:
                dist_str = f"{float(dist):.4f}"
            except Exception:
                dist_str = ""

        if len(text) > max_chunk_chars:
            text = text[:max_chunk_chars].rstrip() + "…"

        meta_bits: list[str] = []
        if file_name:
            meta_bits.append(file_name)
        if file_id:
            meta_bits.append(f"file_id={file_id}")
        if folder_id is not None:
            try:
                meta_bits.append(f"folder_id={int(folder_id)}")
            except Exception:
                pass
        if dist_str:
            meta_bits.append(f"distance={dist_str}")
        meta_line = " / ".join(meta_bits).strip() or "KB chunk"

        block = f"[{len(blocks) + 1}] {meta_line}\n{text}"
        if total + len(block) > max_total_chars:
            break
        blocks.append(block)
        total += len(block) + 2
        if len(blocks) >= max_chunks:
            break

    return "\n\n".join(blocks).strip()


async def _search_personaldb_kb_context(
    personaldb_url: str,
    *,
    user_id: str,
    query: str,
    kb_file_ids: list[str],
    topk: int = 5,
) -> str:
    """
    从 personaldb 检索知识库片段，作为大纲生成的参考上下文。
    注意：检索失败时不应阻断主流程（仍可用主题生成大纲）。
    """
    if not query.strip():
        return ""
    if not kb_file_ids:
        return ""

    payload = {
        "userId": str(user_id),
        "query": str(query),
        "keyword": "",
        "topk": int(topk),
        "fileIds": list(kb_file_ids),
    }

    url = f"{personaldb_url}/search"
    async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(20.0)) as client:
        try:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                logger.info("[personaldb %s] %s", resp.status_code, resp.text)
                return ""
            try:
                result = resp.json()
            except ValueError:
                logger.info("personaldb /search 返回非 JSON：%s", resp.text)
                return ""
        except Exception as exc:
            logger.info("personaldb /search 调用失败：%s", exc)
            return ""

    return _format_personaldb_search_context(result)


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
    material: AssistantMaterialContext | None,
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
            "- When KB snippets are provided, use them as grounding; if insufficient, say so.\n"
            "- Use concise bullets/steps when helpful.\n"
        )
    else:
        base = (
            "你是 TeachDo 的 AI 教学助教。\n"
            "你的目标是帮助教师进行教学设计、知识点讲解、题目生成与答疑。\n"
            "规则：\n"
            "- 回答要准确、可操作。\n"
            "- 问题不清晰时，先问 1~2 个澄清问题。\n"
            "- 若提供了知识库检索片段，应优先基于片段作答；片段不足时要明确说明。\n"
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

    if kb_context and kb_context.strip():
        if want_english:
            context_bits.append("KB snippets (for grounding):\n" + kb_context.strip())
        else:
            context_bits.append("知识库检索片段（用于事实依据/参考）：\n" + kb_context.strip())

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
    if llm_type != "openai":
        raise RuntimeError(f"当前助教仅支持 openai 协议，检测到 ASSISTANT_TYPE/OUTLINE_TYPE={llm_type}")
    if not llm_api_key:
        raise RuntimeError("缺少助教模型 API Key，请设置 ASSISTANT_API_KEY（或复用 OUTLINE_API_KEY）")

    return {"type": llm_type, "model": llm_model, "api_key": llm_api_key, "base_url": llm_base_url}


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
                    delta = None

                if isinstance(delta, str) and delta:
                    yield delta


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


async def stream_content_response(
    markdown_content: str,
    language,
    generateFromUploadedFile,
    generateFromWebSearch,
    user_id,
    kb_folder_ids: list[int] | None = None,
    kb_file_ids: list[str] | None = None,
):
    match = re.search(r"(# .*)", markdown_content, flags=re.DOTALL)
    result = markdown_content[match.start():] if match else markdown_content
    logger.info(f"用户输入的markdown大纲是：{result}")

    content_wrapper = A2AContentClientWrapper(session_id=uuid.uuid4().hex, agent_url=CONTENT_API)

    search_engine = []
    if generateFromUploadedFile:
        search_engine.append("KnowledgeBaseSearch")
    if generateFromWebSearch:
        search_engine.append("DocumentSearch")

    metadata = {"user_id": user_id, "search_engine": search_engine, "language": language}
    if kb_folder_ids:
        metadata["kb_folder_ids"] = kb_folder_ids
    if kb_file_ids:
        metadata["kb_file_ids"] = kb_file_ids
    logger.info(f"前端*内容**=====>metadata数据为：{metadata}")

    last_flush = asyncio.get_event_loop().time()

    try:
        async for chunk_data in content_wrapper.generate(user_question=result, metadata=metadata):
            logger.info(f"生成正文输出的chunk_data: {chunk_data}")

            # 心跳：每10秒发一次注释，避免某些代理断连接
            now = asyncio.get_event_loop().time()
            if now - last_flush > 10:
                yield b": keep-alive\n\n"
                last_flush = now

            chunk_type = chunk_data.get("type")
            if chunk_type == "text":
                # 注意：每条 SSE 事件以空行结束
                payload = chunk_data.get("text", "")
                yield _encode_sse_data(payload)
            elif chunk_type in {"error", "final"}:
                # 返回结构化事件，便于前端/日志诊断
                payload = json.dumps(chunk_data, ensure_ascii=False)
                yield _encode_sse_data(payload)
    except asyncio.CancelledError:
        logger.info("客户端已断开 /tools/aippt SSE 连接，提前结束流")
        raise
    except Exception as e:
        logger.error("内容生成流异常: %s", e, exc_info=True)
        payload = json.dumps(
            {
                "type": "error",
                "text": f"内容生成中断：{e}",
                "author": "system",
            },
            ensure_ascii=False,
        )
        yield _encode_sse_data(payload)
    finally:
        # 显式结束信号（前端可据此收尾）
        yield b"data: [DONE]\n\n"

@app.post("/tools/aippt")
async def aippt_content(request: AipptContentRequest):
    markdown_content = request.content
    # 兼容旧字段名：如果 user_id 为空就用 sessionId
    user_id = getattr(request, "user_id", None) or getattr(request, "sessionId", None)

    generate_from_uploaded_file = bool(request.generateFromUploadedFile)
    personaldb_url = _get_personaldb_url()
    if generate_from_uploaded_file:
        if not personaldb_url:
            logger.info("PERSONAL_DB 未配置，强制禁用 generateFromUploadedFile")
            generate_from_uploaded_file = False
        else:
            ready = await _is_personaldb_ready(personaldb_url)
            if not ready:
                logger.info("personaldb 不可用，强制禁用 generateFromUploadedFile: %s", personaldb_url)
                generate_from_uploaded_file = False

    async def event_generator():
        async for chunk in stream_content_response(
            markdown_content,
            language=request.language,
            generateFromUploadedFile=generate_from_uploaded_file,
            generateFromWebSearch=request.generateFromWebSearch,
            user_id=user_id,
            kb_folder_ids=request.kb_folder_ids if generate_from_uploaded_file else None,
            kb_file_ids=request.kb_file_ids if generate_from_uploaded_file else None,
        ):
            yield chunk

    # 关键：SSE 推荐这些头
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/tools/lesson_plan")
async def lesson_plan(request: LessonPlanRequest):
    """
    教案生成（SSE）：
    - 每个 section 输出一条 JSON 事件
    - 结束以 data: [DONE] 收尾
    """

    async def event_generator():
        async for chunk in stream_lesson_plan_sse(request):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _lesson_safe_export_filename(title: str) -> str:
    """
    构造可用于 Content-Disposition 的 docx 文件名。
    """
    base = _kb_safe_filename(title) or "lesson_plan"
    if base.lower().endswith(".docx"):
        return base
    return f"{base}.docx"


def _build_lesson_docx_bytes(*, plan: LessonPlan, style: LessonStyle, language: str) -> bytes:
    """
    生成 docx bytes（python-docx）。
    - 直接按 LessonPlan 写文档，减少模板渲染带来的运行时依赖和不确定性
    """
    try:
        from docx import Document
        from docx.oxml.ns import qn
        from docx.shared import Pt, Cm
    except Exception as exc:  # pragma: no cover - 依赖缺失时给出明确错误
        raise RuntimeError(f"缺少 python-docx 依赖：{exc}") from exc

    lang = (language or "zh").strip().lower()
    want_english = lang in {"en", "english"}

    def _safe_float(value: Any, fallback: float) -> float:
        try:
            return float(value)
        except Exception:
            return fallback

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(_safe_float(style.marginTopCm, 2.54))
    section.bottom_margin = Cm(_safe_float(style.marginBottomCm, 2.54))
    section.left_margin = Cm(_safe_float(style.marginLeftCm, 2.54))
    section.right_margin = Cm(_safe_float(style.marginRightCm, 2.54))

    def _set_style_font(style_name: str, *, size_pt: int):
        try:
            st = doc.styles[style_name]
        except Exception:
            return
        st.font.name = style.fontZh
        st.font.size = Pt(int(size_pt))
        try:
            st._element.rPr.rFonts.set(qn("w:eastAsia"), style.fontZh)
        except Exception:
            pass

    _set_style_font("Normal", size_pt=style.bodySizePt)
    _set_style_font("Title", size_pt=style.titleSizePt)
    _set_style_font("Heading 1", size_pt=style.h1SizePt)
    _set_style_font("Heading 2", size_pt=style.h2SizePt)
    _set_style_font("List Bullet", size_pt=style.bodySizePt)
    _set_style_font("List Number", size_pt=style.bodySizePt)

    def _set_run_font(run: Any, *, size_pt: int, bold: bool = False):
        run.font.name = style.fontZh
        run.font.size = Pt(int(size_pt))
        run.bold = bool(bold)
        try:
            run._element.rPr.rFonts.set(qn("w:eastAsia"), style.fontZh)
        except Exception:
            pass

    def _add_paragraph(text: str, *, size_pt: int, bold: bool = False, style_name: str | None = None):
        p = doc.add_paragraph()
        if style_name:
            try:
                p.style = style_name
            except Exception:
                pass
        run = p.add_run((text or "").strip() or ("N/A" if want_english else "—"))
        _set_run_font(run, size_pt=size_pt, bold=bold)
        try:
            p.paragraph_format.line_spacing = float(style.lineSpacing)
        except Exception:
            pass
        return p

    # Title
    _add_paragraph(
        (plan.title or "").strip() or ("Lesson Plan" if want_english else "教案"),
        size_pt=style.titleSizePt,
        bold=True,
        style_name="Title",
    )

    # Meta
    aud_label = "Audience" if want_english else "受众"
    dur_label = "Duration" if want_english else "时长"
    _add_paragraph(
        f"{aud_label}：{(plan.targetAudience or '').strip() or ('Students' if want_english else '中学学生')} | "
        f"{dur_label}：{(plan.duration or '').strip() or ('45 min' if want_english else '45分钟')}",
        size_pt=style.bodySizePt,
    )

    # Objectives
    _add_paragraph(
        "Objectives" if want_english else "教学目标",
        size_pt=style.h1SizePt,
        bold=True,
        style_name="Heading 1",
    )
    if plan.objectives:
        for item in plan.objectives:
            _add_paragraph(str(item), size_pt=style.bodySizePt, style_name="List Bullet")
    else:
        _add_paragraph("No objectives provided." if want_english else "未提供教学目标。", size_pt=style.bodySizePt, style_name="List Bullet")

    # Materials
    _add_paragraph(
        "Materials" if want_english else "教学材料",
        size_pt=style.h1SizePt,
        bold=True,
        style_name="Heading 1",
    )
    if plan.materials:
        for item in plan.materials:
            _add_paragraph(str(item), size_pt=style.bodySizePt, style_name="List Bullet")
    else:
        _add_paragraph("No materials provided." if want_english else "未提供教学材料。", size_pt=style.bodySizePt, style_name="List Bullet")

    # Procedure
    _add_paragraph(
        "Procedure" if want_english else "教学流程",
        size_pt=style.h1SizePt,
        bold=True,
        style_name="Heading 1",
    )
    if plan.procedure:
        for item in plan.procedure:
            step = (item.step or "").strip() or ("Untitled Step" if want_english else "未命名步骤")
            duration = (item.duration or "").strip() or ("N/A" if want_english else "未填写时长")
            activity = (item.activity or "").strip() or ("No activity details." if want_english else "未填写活动说明。")
            if want_english:
                _add_paragraph(f"{step} ({duration})", size_pt=style.bodySizePt, bold=True, style_name="List Number")
            else:
                _add_paragraph(f"{step}（{duration}）", size_pt=style.bodySizePt, bold=True, style_name="List Number")
            _add_paragraph(activity, size_pt=style.bodySizePt)
    else:
        _add_paragraph(
            "No procedure provided." if want_english else "未提供教学流程。",
            size_pt=style.bodySizePt,
            style_name="List Number",
        )

    # Homework
    _add_paragraph(
        "Homework" if want_english else "课后作业",
        size_pt=style.h1SizePt,
        bold=True,
        style_name="Heading 1",
    )
    _add_paragraph((plan.homework or "").strip() or ("No homework provided." if want_english else "未提供课后作业。"), size_pt=style.bodySizePt)

    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


@app.post("/lesson/export/docx")
async def lesson_export_docx(request: LessonExportDocxRequest):
    """
    导出教案为标准 .docx（附件下载）。
    """
    plan = request.lessonPlan
    style = request.style or LessonStyle()
    language = request.language or "zh"

    try:
        content = _build_lesson_docx_bytes(plan=plan, style=style, language=language)
    except Exception as exc:
        logger.error("lesson_export_docx 失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    filename = _lesson_safe_export_filename(plan.title)
    encoded = quote(filename)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
            "Cache-Control": "no-store",
        },
    )


@app.post("/tools/assistant_chat")
async def assistant_chat(request: AssistantChatRequest):
    """
    助教对话（SSE）：
    - 历史消息由前端维护，每次请求透传 messages
    - 可选透传 kb_file_ids，用 personaldb 检索片段增强回答（RAG）
    - 不做会话持久化，提供 “清除上下文” 由前端实现（清空 messages）
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")

    last_user_message = _pick_last_user_message(request.messages)
    if not last_user_message:
        raise HTTPException(status_code=400, detail="messages 中缺少 user 消息")

    personaldb_url = _get_personaldb_url()
    resolved_kb_file_ids = _normalize_kb_file_ids(request.kb_file_ids)
    kb_context = ""
    if resolved_kb_file_ids and personaldb_url and await _is_personaldb_ready(personaldb_url):
        kb_context = await _search_personaldb_kb_context(
            personaldb_url,
            user_id=str(request.user_id or "default_user"),
            query=last_user_message,
            kb_file_ids=resolved_kb_file_ids,
        )

    system_prompt = _build_assistant_system_prompt(
        material=request.material,
        kb_context=kb_context,
        language=request.language,
    )

    llm_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for msg in request.messages:
        content = (msg.content or "").strip()
        if not content:
            continue
        llm_messages.append({"role": msg.role, "content": content})

    try:
        llm_settings = _get_assistant_llm_settings()
    except Exception as exc:
        logger.error("助教模型配置错误: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    async def event_generator():
        async for chunk in stream_assistant_sse(
            llm_settings=llm_settings,
            messages=llm_messages,
        ):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/kb/upload")
async def kb_upload(
    user_id: str = Form(...),
    folder_id: int = Form(0),
    file_id: str | None = Form(None),
    file_type: str | None = Form(None),
    file: UploadFile = File(...),
):
    """
    KB BFF：上传素材并向量化（转发到 personaldb /upload/）。
    - 前端统一访问 /api/kb/upload（Vite proxy 去掉 /api）
    """
    personaldb_url = _get_personaldb_url()
    if not personaldb_url:
        return _kb_error("KB_NOT_CONFIGURED", "PERSONAL_DB 未配置", status_code=500)

    if not file:
        return _kb_error("KB_FILE_REQUIRED", "缺少文件", status_code=400)

    resolved_file_type = (file_type or "").strip() or None
    if not resolved_file_type and file.filename and "." in file.filename:
        resolved_file_type = file.filename.rsplit(".", 1)[-1]

    resolved_file_id = (file_id or "").strip() or None
    if not resolved_file_id:
        epoch_ms = int(time.time() * 1000)
        resolved_file_id = f"upload:{user_id}:{epoch_ms}:{random.randint(0, 999):03d}"

    file_bytes = await file.read()
    if not file_bytes:
        return _kb_error("KB_EMPTY_FILE", "文件内容为空", status_code=400)
    file_size = len(file_bytes)

    data = {
        "userId": str(user_id),
        "fileId": str(resolved_file_id),
        "folderId": str(folder_id),
    }
    if resolved_file_type:
        data["fileType"] = str(resolved_file_type)

    files_payload = {
        "file": (
            file.filename or "uploaded_file",
            file_bytes,
            file.content_type or "application/octet-stream",
        )
    }

    upload_url = f"{personaldb_url}/upload/"

    async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(360.0)) as client:
        try:
            resp = await client.post(upload_url, data=data, files=files_payload)
            if resp.status_code >= 400:
                logger.info("[personaldb %s] %s", resp.status_code, resp.text)
                return _kb_error("KB_UPLOAD_FAILED", resp.text, status_code=resp.status_code)
            result = resp.json()
        except Exception as exc:
            logger.error("kb_upload 调用 personaldb 失败: %s", exc, exc_info=True)
            return _kb_error("KB_UPLOAD_FAILED", f"personaldb 调用失败: {exc}", status_code=502)

    # 不向前端返回 markdown_content（可能很大）
    return _kb_ok(
        {
            "user_id": str(user_id),
            "file_id": str(resolved_file_id),
            "file_name": file.filename or result.get("file_name") or "uploaded_file",
            "file_type": resolved_file_type or result.get("fileType") or "unknown",
            "file_size": int(file_size),
            "folder_id": int(folder_id),
            "status": "ready",
        }
    )


@app.get("/kb/files/{user_id}")
async def kb_list_files(user_id: str, folder_id: int | None = Query(None)):
    """
    KB BFF：列出知识库文件（转发 personaldb GET /files/{user_id}）。
    """
    personaldb_url = _get_personaldb_url()
    if not personaldb_url:
        return _kb_error("KB_NOT_CONFIGURED", "PERSONAL_DB 未配置", status_code=500)

    url = f"{personaldb_url}/files/{user_id}"
    async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(10.0)) as client:
        try:
            resp = await client.get(url)
            if resp.status_code >= 400:
                logger.info("[personaldb %s] %s", resp.status_code, resp.text)
                return _kb_error("KB_LIST_FAILED", resp.text, status_code=resp.status_code)
            files = resp.json()
        except Exception as exc:
            logger.error("kb_list_files 调用 personaldb 失败: %s", exc, exc_info=True)
            return _kb_error("KB_LIST_FAILED", f"personaldb 调用失败: {exc}", status_code=502)

    if not isinstance(files, list):
        return _kb_error("KB_LIST_FAILED", "personaldb 返回格式非法（期望 list）", status_code=502)

    normalized = []
    for item in files:
        if not isinstance(item, dict):
            continue
        try:
            fid = str(item.get("file_id") or item.get("fileId") or "")
            if not fid:
                continue
            one_folder_id = item.get("folder_id") if item.get("folder_id") is not None else item.get("folderId")
            one_folder_id_int = int(one_folder_id) if one_folder_id is not None else 0
            one_file_size = item.get("file_size") if item.get("file_size") is not None else item.get("fileSize")
            try:
                one_file_size_int = int(one_file_size) if one_file_size is not None else 0
                if one_file_size_int < 0:
                    one_file_size_int = 0
            except Exception:
                one_file_size_int = 0

            raw_created_at = item.get("created_at") if item.get("created_at") is not None else item.get("createdAt")
            created_at_ms: int | None = None
            if raw_created_at is not None:
                try:
                    created_at_ms = int(raw_created_at)
                    if created_at_ms > 0 and created_at_ms < 1_000_000_000_000:
                        created_at_ms *= 1000
                except Exception:
                    created_at_ms = None

            raw_source_type = item.get("source_type") if item.get("source_type") is not None else item.get("sourceType")
            source_type = str(raw_source_type).strip().lower() if raw_source_type is not None else ""
            if source_type not in {"upload", "material"}:
                source_type = ""

            source_material_id = (
                str(
                    item.get("source_material_id")
                    if item.get("source_material_id") is not None
                    else item.get("sourceMaterialId")
                    or ""
                ).strip()
            )
            source_material_title = (
                str(
                    item.get("source_material_title")
                    if item.get("source_material_title") is not None
                    else item.get("sourceMaterialTitle")
                    or ""
                ).strip()
            )
            if folder_id is not None and int(folder_id) != one_folder_id_int:
                continue
            normalized.append(
                {
                    "user_id": str(user_id),
                    "file_id": fid,
                    "file_name": item.get("file_name") or item.get("fileName") or "",
                    "file_type": item.get("file_type") or item.get("fileType") or "",
                    "file_size": one_file_size_int,
                    "folder_id": one_folder_id_int,
                    **({"created_at": created_at_ms} if created_at_ms is not None else {}),
                    **({"source_type": source_type} if source_type else {}),
                    **({"source_material_id": source_material_id} if source_material_id else {}),
                    **({"source_material_title": source_material_title} if source_material_title else {}),
                }
            )
        except Exception:
            continue

    return _kb_ok(normalized)


@app.get("/kb/files/{user_id}/{file_id}/export")
async def kb_export_file(user_id: str, file_id: str):
    """
    KB BFF：导出知识库文件内容（Markdown/纯文本）。

    - 转发 personaldb GET /files/{user_id}/{file_id}/content
    - 以 attachment 形式返回，便于前端下载保存
    """
    personaldb_url = _get_personaldb_url()
    if not personaldb_url:
        return _kb_error("KB_NOT_CONFIGURED", "PERSONAL_DB 未配置", status_code=500)

    url = f"{personaldb_url}/files/{user_id}/{file_id}/content"
    async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(20.0)) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 404:
                return _kb_error("KB_FILE_NOT_FOUND", "文件不存在", status_code=404)
            if resp.status_code >= 400:
                logger.info("[personaldb %s] %s", resp.status_code, resp.text)
                return _kb_error("KB_EXPORT_FAILED", resp.text, status_code=resp.status_code)
            payload = resp.json()
        except Exception as exc:
            logger.error("kb_export_file 调用 personaldb 失败: %s", exc, exc_info=True)
            return _kb_error("KB_EXPORT_FAILED", f"personaldb 调用失败: {exc}", status_code=502)

    content = payload.get("content") if isinstance(payload, dict) else None
    if not isinstance(content, str):
        return _kb_error("KB_EXPORT_FAILED", "personaldb 返回格式非法（缺少 content）", status_code=502)

    file_name = payload.get("file_name") if isinstance(payload, dict) else ""
    file_type = payload.get("file_type") if isinstance(payload, dict) else ""
    export_name = _kb_build_export_filename(str(file_name or ""), str(file_type or ""), file_id)
    encoded = quote(export_name)

    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
            "Cache-Control": "no-store",
        },
    )


class KbVectorizeTextRequest(BaseModel):
    user_id: str
    file_id: str
    file_name: str
    content: str
    file_type: str = "md"
    folder_id: int = 1
    # KB 元数据（可选）：用于前端展示“时间 + 来源”，不参与检索
    created_at: int | None = None
    source_type: str | None = None
    source_material_id: str | None = None
    source_material_title: str | None = None


@app.post("/kb/vectorize/text")
async def kb_vectorize_text(request: KbVectorizeTextRequest):
    """
    KB BFF：把文本写入 KB 索引（转发 personaldb POST /vectorize/text）。
    """
    personaldb_url = _get_personaldb_url()
    if not personaldb_url:
        return _kb_error("KB_NOT_CONFIGURED", "PERSONAL_DB 未配置", status_code=500)

    if not request.content.strip():
        return _kb_error("KB_CONTENT_REQUIRED", "content 不能为空", status_code=400)

    payload = {
        "userId": request.user_id,
        "fileId": request.file_id,
        "fileName": request.file_name,
        "fileType": request.file_type,
        "folderId": request.folder_id,
        "content": request.content,
        "url": "",
    }
    if request.created_at is not None:
        try:
            payload["createdAt"] = int(request.created_at)
        except Exception:
            pass
    if request.source_type:
        payload["sourceType"] = str(request.source_type)
    if request.source_material_id:
        payload["sourceMaterialId"] = str(request.source_material_id)
    if request.source_material_title:
        payload["sourceMaterialTitle"] = str(request.source_material_title)

    url = f"{personaldb_url}/vectorize/text"
    async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(60.0)) as client:
        try:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                logger.info("[personaldb %s] %s", resp.status_code, resp.text)
                return _kb_error("KB_VECTORIZE_FAILED", resp.text, status_code=resp.status_code)
        except Exception as exc:
            logger.error("kb_vectorize_text 调用 personaldb 失败: %s", exc, exc_info=True)
            return _kb_error("KB_VECTORIZE_FAILED", f"personaldb 调用失败: {exc}", status_code=502)

    return _kb_ok(True)


@app.delete("/kb/files/{user_id}/{file_id}")
async def kb_delete_file(user_id: str, file_id: str):
    """
    KB BFF：删除知识库文件向量（转发 personaldb DELETE /files/{user_id}/{file_id}）。
    """
    personaldb_url = _get_personaldb_url()
    if not personaldb_url:
        return _kb_error("KB_NOT_CONFIGURED", "PERSONAL_DB 未配置", status_code=500)

    url = f"{personaldb_url}/files/{user_id}/{file_id}"
    async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(10.0)) as client:
        try:
            resp = await client.delete(url)
            if resp.status_code >= 400:
                logger.info("[personaldb %s] %s", resp.status_code, resp.text)
                return _kb_error("KB_DELETE_FAILED", resp.text, status_code=resp.status_code)
        except Exception as exc:
            logger.error("kb_delete_file 调用 personaldb 失败: %s", exc, exc_info=True)
            return _kb_error("KB_DELETE_FAILED", f"personaldb 调用失败: {exc}", status_code=502)

    return _kb_ok(True)

@app.get("/data/{filename}")
async def get_data(filename: str):
    file_path = os.path.join("./template", filename)
    return FileResponse(file_path)

@app.get("/templates")
async def get_templates():
    templates = [
        { "name": "红色通用", "id": "template_1", "cover": "/api/data/template_1.jpg" },
        { "name": "蓝色通用", "id": "template_2", "cover": "/api/data/template_2.jpg" },
        { "name": "紫色通用", "id": "template_3", "cover": "/api/data/template_3.jpg" },
        { "name": "莫兰迪配色", "id": "template_4", "cover": "/api/data/template_4.jpg" },
        # { "name": "图表", "id": "template_6", "cover": "/api/data/template_6.jpg" },
    ]

    return {"data": templates}


@app.get("/files/{user_id}")
async def list_user_files(user_id: int):
    """
    列出指定用户的所有文件信息
    """
    personaldb_api_url = os.environ["PERSONAL_DB"]
    url = f"{personaldb_api_url}/files/{user_id}"

    # 内部服务调用（personaldb）不应受系统代理环境变量影响
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Error connecting to personaldb: {exc}")
        except httpx.HTTPStatusError as exc:
            # 转发下游服务的错误
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


@app.get("/proxy")
async def proxy(request: Request, url: str = Query(..., description="Target absolute URL")):
    """
    透明代理上游资源，转发部分请求头，透传关键响应头，并允许前端同源访问。
    适合图片/音视频等二进制内容。
    """
    HEADERS_TO_FORWARD = {"Range", "User-Agent"}  # 需要时可扩展
    HEADERS_TO_COPY = {
        "Content-Type",
        "Content-Length",
        "Content-Disposition",
        "Accept-Ranges",
        "ETag",
        "Last-Modified",
        "Cache-Control",
        "Expires",
    }
    forward_headers = {}
    for h in HEADERS_TO_FORWARD:
        v = request.headers.get(h)
        if v:
            forward_headers[h] = v

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            upstream = await client.get(url, headers=forward_headers)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream fetch error: {e!s}")

    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail="Upstream error")

    headers = {}
    for h in HEADERS_TO_COPY:
        if h in upstream.headers:
            headers[h] = upstream.headers[h]

    # 允许被前端同源读取
    headers["Access-Control-Allow-Origin"] = "*"
    # 给静态资源加简单缓存（按需调整）
    headers.setdefault("Cache-Control", "public, max-age=86400")

    return StreamingResponse(
        upstream.aiter_bytes(),
        status_code=upstream.status_code,
        headers=headers,
        media_type=upstream.headers.get("Content-Type"),
    )

@app.get("/healthz")
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    import sys
    import uvicorn

    # 允许在任意工作目录运行：确保可以导入 `backend.common.*`
    repo_root = _find_repo_root(Path(__file__).resolve())
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.common.logging_utils import build_uvicorn_log_config, apply_logging_config

    log_config = build_uvicorn_log_config()
    apply_logging_config(log_config)

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("MAIN_API_PORT", "6800"))
    uvicorn.run(app, host=host, port=port, log_config=log_config)
