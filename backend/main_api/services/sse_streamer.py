import asyncio
import json
import logging
import re
from typing import AsyncGenerator

from backend.main_api.models.schemas import LessonPlan, LessonPlanProcedureStep, LessonPlanRequest
from backend.main_api.utils.common import _encode_sse_data
from backend.main_api.utils.kb import (
    _build_personaldb_kb_contexts,
    _get_personaldb_url,
    _is_personaldb_ready,
    _normalize_kb_file_ids,
)
from backend.main_api.utils.common import (
    _build_lesson_system_prompt,
    _fallback_generate_lesson_plan,
    _generate_lesson_section_with_llm,
    _normalize_lesson_template_id,
    _try_get_lesson_llm_settings,
)

logger = logging.getLogger(__name__)

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

    full_context = ""
    kb_context = ""
    if resolved_kb_file_ids and personaldb_url and await _is_personaldb_ready(personaldb_url):
        # query 选用 “标题 + 大纲” 的组合，尽量贴近教案生成语义
        query = f"{(req.title or '').strip()}\n{outline}".strip()
        full_context, kb_context = await _build_personaldb_kb_contexts(
            personaldb_url,
            user_id=user_id,
            query=query,
            kb_file_ids=resolved_kb_file_ids,
            rag_topk=5,
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

    lang = (req.language or "zh").strip().lower()
    want_english = lang in {"en", "english"}
    tpl = _normalize_lesson_template_id(req.templateId)
    if tpl not in {"lesson_simple", "lesson_table", "lesson_jnu_form"}:
        tpl = "lesson_simple"
    system_prompt = _build_lesson_system_prompt(req=req, full_context=full_context, kb_context=kb_context)

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
        if tpl == "lesson_jnu_form":
            obj_prompt = (
                'Return STRICT JSON only: {"objectives":["..."]}.\n'
                "Write 3-6 key points, then add ONE final item starting with 'Difficulty:'."
                if want_english
                else '仅输出严格 JSON：{"objectives":["..."]}.\n'
                     "先写 3~6 条“重点”，再额外补充 1 条以“难点：”开头的条目（作为最后一条）。"
            )
        else:
            obj_prompt = (
                'Return STRICT JSON only: {"objectives":["..."]}.\n'
                "Write 3-6 concise objectives."
                if want_english
                else '仅输出严格 JSON：{"objectives":["..."]}.\n'
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
        elif tpl == "lesson_jnu_form":
            # 兜底修正：确保最后一条是“难点：/Difficulty:”
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

        # 心跳：每10秒发一次注释，避免某些代理断连接
        now = asyncio.get_event_loop().time()
        if now - last_flush > 10:
            yield b": keep-alive\n\n"
            last_flush = now

        yield _encode_sse_data(json.dumps({"type": "section", "section": "objectives", "data": objectives}, ensure_ascii=False, separators=(",", ":")))

        # materials
        if tpl == "lesson_jnu_form":
            mat_prompt = (
                'Return STRICT JSON only: {"materials":["..."]}.\n'
                "List 4-10 items. Include at least one reference item (e.g., starts with 'Textbook:' or 'Reference:')."
                if want_english
                else '仅输出严格 JSON：{"materials":["..."]}.\n'
                     "列出 4~10 项教学材料/工具；并至少包含 1 条参考资料（例如以“教材：/参考书：/参考资料：”开头）。"
            )
        else:
            mat_prompt = (
                'Return STRICT JSON only: {"materials":["..."]}.\n'
                "List 3-8 materials/tools needed."
                if want_english
                else '仅输出严格 JSON：{"materials":["..."]}.\n'
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
        elif tpl == "lesson_jnu_form":
            ref_keywords = (
                ["textbook", "reference", "paper", "book", "isbn"]
                if want_english
                else ["教材", "课本", "参考", "文献", "论文", "书", "ISBN"]
            )
            has_ref = any(any(k.lower() in m.lower() for k in ref_keywords) for m in materials)
            if not has_ref:
                materials = materials + (["Textbook/Reference: ______"] if want_english else ["教材/参考书：______"])

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
        if tpl == "lesson_jnu_form":
            hw_prompt = (
                'Return STRICT JSON only: {"homework":"..."}.\n'
                "Write questions/discussion/homework, concise but actionable."
                if want_english
                else '仅输出严格 JSON：{"homework":"..."}.\n'
                     "以“思考题/讨论题或作业”的形式输出，内容简洁可执行。"
            )
        else:
            hw_prompt = (
                'Return STRICT JSON only: {"homework":"..."}.\n'
                "Keep it concise."
                if want_english
                else '仅输出严格 JSON：{"homework":"..."}.\n'
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
