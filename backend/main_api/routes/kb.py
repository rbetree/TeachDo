import logging
import random
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse, Response
import httpx
from pydantic import BaseModel

from backend.main_api.utils.kb import (
    _get_personaldb_url,
    _kb_build_export_filename,
    _kb_error,
    _kb_ok,
    _kb_safe_filename,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class KbVectorizeTextRequest(BaseModel):
    user_id: str
    file_id: str
    file_name: str
    content: str
    file_type: str = "md"
    folder_id: int = 1
    # KB 元数据（可选）：用于前端展示"时间 + 来源"，不参与检索
    created_at: int | None = None
    source_type: str | None = None
    source_material_id: str | None = None
    source_material_title: str | None = None


@router.post("/kb/upload")
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


@router.get("/kb/files/{user_id}")
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
                logger.debug("忽略非法 file_size: %r", one_file_size, exc_info=True)
                one_file_size_int = 0

            raw_created_at = item.get("created_at") if item.get("created_at") is not None else item.get("createdAt")
            created_at_ms: int | None = None
            if raw_created_at is not None:
                try:
                    created_at_ms = int(raw_created_at)
                    if created_at_ms > 0 and created_at_ms < 1_000_000_000_000:
                        created_at_ms *= 1000
                except Exception:
                    logger.debug("忽略非法 created_at: %r", raw_created_at, exc_info=True)
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
            logger.warning("解析 KB 文件项失败，跳过该项", exc_info=True)
            continue

    return _kb_ok(normalized)


@router.get("/kb/files/{user_id}/{file_id}/export")
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


@router.post("/kb/vectorize/text")
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
            logger.debug("忽略非法 created_at: %r", request.created_at, exc_info=True)
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


@router.delete("/kb/files/{user_id}/{file_id}")
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
