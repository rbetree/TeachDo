import asyncio
import logging
import re
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.common.course_outputs_injection import (
    COURSE_OUTPUTS_START_MARKER,
    build_course_outputs_injection_markdown,
)
from backend.main_api.utils.common import _encode_sse_data
from backend.main_api.utils.content import stream_content_response, _inject_markdown_after_first_h1
from backend.main_api.utils.kb import (
    _get_personaldb_url,
    _is_personaldb_ready,
    _load_personaldb_full_text_context,
    _normalize_kb_file_ids,
    _split_kb_file_ids,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class AipptContentRequest(BaseModel):
    content: str
    language: str = "zh"  # 默认中文
    sessionId: str = ""  # 当使用知识库时，需要根据用户的user_id查询对应的知识库
    generateFromUploadedFile: bool = False  # 是否从上传的文件中生成PPT内容
    generateFromWebSearch: bool = True  # 是否从网络搜索中生成PPT内容
    generateWithImages: bool = False  # 是否启用“联网配图”（开启：检索网络图片；关闭：使用预设图片池）
    kb_folder_ids: list[int] | None = None  # 仅当启用知识库检索时生效，用于过滤可检索的 folder_id
    kb_file_ids: list[str] | None = None  # 仅当启用知识库检索时生效，用于过滤可检索的 file_id（更精确）


@router.post("/tools/ppt")
@router.post("/tools/aippt")
async def aippt_content(request: AipptContentRequest):
    personaldb_url = _get_personaldb_url()
    personaldb_ready = bool(personaldb_url and await _is_personaldb_ready(personaldb_url))

    markdown_content = request.content
    # 兼容旧字段名：如果 user_id 为空就用 sessionId
    user_id = str(getattr(request, "user_id", None) or getattr(request, "sessionId", None) or "").strip() or "default_user"

    resolved_kb_file_ids = _normalize_kb_file_ids(request.kb_file_ids)
    full_ids, rag_ids = _split_kb_file_ids(resolved_kb_file_ids)

    # gen: 产物全文注入（不依赖 generateFromUploadedFile 开关）
    if full_ids and personaldb_ready and COURSE_OUTPUTS_START_MARKER not in (markdown_content or ""):
        full_context = await _load_personaldb_full_text_context(
            personaldb_url,
            user_id=user_id,
            file_ids=full_ids,
        )
        injection = build_course_outputs_injection_markdown(full_context, language=request.language)
        if injection:
            markdown_content = _inject_markdown_after_first_h1(markdown_content, injection)

    generate_from_uploaded_file = bool(request.generateFromUploadedFile) and personaldb_ready
    if bool(request.generateFromUploadedFile) and not generate_from_uploaded_file:
        logger.info("personaldb 不可用或未配置，强制禁用 generateFromUploadedFile: %s", personaldb_url)

    async def event_generator():
        async for chunk in stream_content_response(
            markdown_content,
            language=request.language,
            generateFromUploadedFile=generate_from_uploaded_file,
            generateFromWebSearch=request.generateFromWebSearch,
            generateWithImages=request.generateWithImages,
            user_id=user_id,
            kb_folder_ids=request.kb_folder_ids if generate_from_uploaded_file else None,
            kb_file_ids=rag_ids if generate_from_uploaded_file else None,
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
