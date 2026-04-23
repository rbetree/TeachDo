import logging
import os
import time

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.main_api.models.schemas import AipptRequest
from backend.main_api.utils.kb import (
    _build_personaldb_kb_contexts,
    _get_personaldb_url,
    _is_personaldb_ready,
    _normalize_kb_file_ids,
)
from backend.main_api.utils.outline import iter_outline_text_chunks, stream_outline_sse

try:
    from outline_client import A2AOutlineClientWrapper
except ImportError:  # pragma: no cover - 兼容以包方式导入（用于单元测试等）
    from backend.main_api.outline_client import A2AOutlineClientWrapper

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tools/aippt_outline")
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


@router.post("/tools/outline")
@router.post("/tools/aippt_outline_unified")
async def aippt_outline_unified(
    content: str = Form(None),           # 主题文本（可选）
    file: UploadFile = File(None),       # 上传文件（可选）
    language: str = Form("chinese"),
    user_id: str = Form("default_user"),
    folder_id: int | str = Form(0),
    file_type: str | None = Form(None),
    kb_file_ids: list[str] | None = Form(None),  # 可选：限定从哪些 KB 文件检索参考片段
    outline_length: str = Form("standard"),  # short | standard | long
    use_web_search: bool = Form(True),
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

    if not has_content and not has_file:
        raise HTTPException(status_code=400, detail="请提供主题或文件")

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

    full_context = ""
    kb_context = ""
    resolved_kb_file_ids = _normalize_kb_file_ids(kb_file_ids)
    if resolved_kb_file_ids:
        if personaldb_url and await _is_personaldb_ready(personaldb_url):
            full_context, kb_context = await _build_personaldb_kb_contexts(
                personaldb_url,
                user_id=str(user_id),
                query=content_text,
                kb_file_ids=resolved_kb_file_ids,
                rag_topk=5,
            )
        else:
            logger.info("personaldb 不可用，跳过 kb_file_ids 检索增强：%s", personaldb_url)

    prompt_parts: list[str] = []
    if content_text:
        prompt_parts.append(content_text)
    if file_content:
        prompt_parts.append(f"参考文档内容（来自你上传的文件）：\n{file_content}")
    if full_context:
        prompt_parts.append(
            "课程产出（全文，不经检索）：\n"
            "（说明：仅供参考用于一致性对齐，不要原文照抄，也不要把其目录/结构当作本次大纲结构。）\n"
            f"{full_context}"
        )
    if kb_context:
        prompt_parts.append(f"参考资料检索片段（RAG）：\n{kb_context}")
    prompt = "\n\n".join(prompt_parts)

    outline_length_norm = (outline_length or "").strip().lower() or "standard"
    if outline_length_norm not in {"short", "standard", "long"}:
        logger.info("outline_length 非法，回落为 standard: %s", outline_length)
        outline_length_norm = "standard"

    outline_metadata = {
        "outline_length": outline_length_norm,
        "use_web_search": bool(use_web_search),
        "user_id": str(user_id),
    }

    logger.info(
        "统一大纲API*outline***=====>：language=%s, has_file=%s, has_content=%s, outline_length=%s, use_web_search=%s",
        language,
        has_file,
        has_content,
        outline_length_norm,
        bool(use_web_search),
    )

    async def event_generator():
        async for chunk in stream_outline_sse(
            prompt,
            language,
            user_id=str(user_id),
            metadata=outline_metadata,
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


@router.post("/tools/outline_from_file")
@router.post("/tools/aippt_outline_from_file")
async def aippt_outline_from_file(
    user_id: int | str = Form(...),
    file: UploadFile = File(None),  # 允许缺省，这样我们可以决定走 file 或 url
    url: str | None = Form(None),
    folder_id: int | str = Form(0),
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
