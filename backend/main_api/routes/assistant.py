import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.main_api.models.schemas import AssistantChatRequest
from backend.main_api.utils.assistant import (
    _build_assistant_system_prompt,
    _get_assistant_llm_settings,
    _pick_last_user_message,
    stream_assistant_sse,
)
from backend.main_api.utils.kb import (
    _build_personaldb_kb_contexts,
    _get_personaldb_url,
    _is_personaldb_ready,
    _normalize_kb_file_ids,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tools/assistant_chat")
async def assistant_chat(request: AssistantChatRequest):
    """
    助教对话（SSE）：
    - 历史消息由前端维护，每次请求透传 messages
    - 可选透传 kb_file_ids，用 personaldb 检索片段增强回答（RAG）
    - 不做会话持久化，提供 "清除上下文" 由前端实现（清空 messages）
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")

    last_user_message = _pick_last_user_message(request.messages)
    if not last_user_message:
        raise HTTPException(status_code=400, detail="messages 中缺少 user 消息")

    personaldb_url = _get_personaldb_url()
    resolved_kb_file_ids = _normalize_kb_file_ids(request.kb_file_ids)
    full_context = ""
    kb_context = ""
    if resolved_kb_file_ids and personaldb_url and await _is_personaldb_ready(personaldb_url):
        full_context, kb_context = await _build_personaldb_kb_contexts(
            personaldb_url,
            user_id=str(request.user_id or "default_user"),
            query=last_user_message,
            kb_file_ids=resolved_kb_file_ids,
            rag_topk=5,
        )

    system_prompt = _build_assistant_system_prompt(
        material=request.material,
        full_context=full_context,
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
