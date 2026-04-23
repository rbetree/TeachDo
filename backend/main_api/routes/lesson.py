import logging
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse

from backend.main_api.models.schemas import (
    LessonExportDocxRequest,
    LessonPlanRequest,
    LessonStyle,
)
from backend.main_api.services.docx_builder import (
    LESSON_DOCX_TEMPLATES,
    _build_lesson_docx_bytes,
    _lesson_safe_export_filename,
)
from backend.main_api.services.sse_streamer import stream_lesson_plan_sse
from backend.main_api.utils.artifacts import _save_artifact_bytes

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tools/lesson_plan")
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


@router.get("/lesson/templates")
async def get_lesson_templates():
    """
    返回教案 Word（docx）导出可选模板列表（供前端选择）。
    """
    return {"data": LESSON_DOCX_TEMPLATES}


@router.post("/lesson/export/docx")
async def lesson_export_docx(request: LessonExportDocxRequest):
    """
    导出教案为标准 .docx（附件下载）。
    """
    plan = request.lessonPlan
    style = request.style or LessonStyle()
    language = request.language or "zh"
    template_id = (request.templateId or "").strip() or None

    try:
        content = _build_lesson_docx_bytes(plan=plan, style=style, language=language, template_id=template_id)
    except ValueError as exc:
        # 模板不合法属于 4xx（调用方参数错误），不要吞成 500
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("lesson_export_docx 失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    filename = _lesson_safe_export_filename(plan.title)
    encoded = quote(filename)

    artifact_id: str | None = None
    if bool(request.persist):
        persist_user_id = str(request.userId or "").strip()
        persist_material_id = str(request.materialId or "").strip()
        if persist_user_id and persist_material_id:
            try:
                meta = _save_artifact_bytes(
                    user_id=persist_user_id,
                    material_id=persist_material_id,
                    kind="docx",
                    file_bytes=content,
                    file_name=filename,
                )
                artifact_id = str(meta.get("artifact_id") or "").strip() or None
            except Exception as exc:
                logger.error("lesson_export_docx 持久化 artifacts 失败: %s", exc, exc_info=True)
        else:
            logger.info("lesson_export_docx persist=true 但缺少 userId/materialId，跳过持久化")

    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
        "Cache-Control": "no-store",
    }
    if artifact_id:
        headers["X-TeachDo-Artifact-Id"] = artifact_id

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )
