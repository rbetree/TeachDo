import logging
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.main_api.utils.artifacts import (
    _artifact_media_type,
    _get_artifact_material_dir,
    _load_artifact_index,
    _normalize_artifact_kind,
    _save_artifact_bytes,
    _write_artifact_index,
    _artifact_public_meta,
)
from backend.main_api.utils.kb import _kb_error, _kb_ok, _kb_safe_filename

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/artifacts/{user_id}/{material_id}")
async def list_artifacts(user_id: str, material_id: str):
    """
    列出指定课程的导出产物（PPTX/DOCX 等）。
    """
    material_dir = _get_artifact_material_dir(user_id=str(user_id), material_id=str(material_id))
    items = _load_artifact_index(material_dir)

    def _created_at(it: dict[str, Any]) -> int:
        raw = it.get("created_at")
        try:
            return int(raw)
        except Exception:
            logger.debug("忽略非法 artifact created_at: %r", raw, exc_info=True)
            return 0

    items_sorted = sorted(items, key=_created_at, reverse=True)
    return _kb_ok([_artifact_public_meta(it) for it in items_sorted])


@router.post("/artifacts/{user_id}/{material_id}")
async def upload_artifact(
    user_id: str,
    material_id: str,
    kind: str = Form(...),
    file: UploadFile = File(...),
):
    """
    上传一个导出产物文件（multipart/form-data）。
    fields:
    - kind: pptx | docx
    - file: 二进制文件
    """
    normalized_kind = _normalize_artifact_kind(kind)
    if not normalized_kind:
        return _kb_error("ARTIFACT_KIND_INVALID", "kind 必须是 pptx 或 docx", status_code=400)

    file_bytes = await file.read()
    if not file_bytes:
        return _kb_error("ARTIFACT_FILE_EMPTY", "文件内容为空", status_code=400)

    original_name = file.filename or f"{normalized_kind}.{normalized_kind}"
    try:
        meta = _save_artifact_bytes(
            user_id=str(user_id),
            material_id=str(material_id),
            kind=normalized_kind,
            file_bytes=file_bytes,
            file_name=original_name,
        )
    except Exception as exc:
        logger.error("upload_artifact 保存失败: %s", exc, exc_info=True)
        return _kb_error("ARTIFACT_UPLOAD_FAILED", str(exc), status_code=500)

    return _kb_ok(meta)


@router.get("/artifacts/{user_id}/{material_id}/{artifact_id}")
async def download_artifact(user_id: str, material_id: str, artifact_id: str):
    """
    下载一个导出产物文件（attachment）。
    """
    material_dir = _get_artifact_material_dir(user_id=str(user_id), material_id=str(material_id))
    items = _load_artifact_index(material_dir)

    target: dict[str, Any] | None = None
    for it in items:
        if str(it.get("artifact_id") or "") == str(artifact_id):
            target = it
            break
    if not target:
        raise HTTPException(status_code=404, detail="artifact 不存在")

    stored_name = str(target.get("stored_name") or "").strip()
    if not stored_name:
        raise HTTPException(status_code=404, detail="artifact 索引损坏（缺少 stored_name）")
    file_path = material_dir / stored_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="artifact 文件不存在")

    file_name = str(target.get("file_name") or f"{artifact_id}").strip() or f"{artifact_id}"
    encoded = quote(_kb_safe_filename(file_name))
    media_type = _artifact_media_type(str(target.get("kind") or ""))
    return FileResponse(
        file_path,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
            "Cache-Control": "no-store",
        },
    )


@router.delete("/artifacts/{user_id}/{material_id}/{artifact_id}")
async def delete_artifact(user_id: str, material_id: str, artifact_id: str):
    """
    删除一个导出产物文件。
    """
    material_dir = _get_artifact_material_dir(user_id=str(user_id), material_id=str(material_id))
    items = _load_artifact_index(material_dir)

    kept: list[dict[str, Any]] = []
    target: dict[str, Any] | None = None
    for it in items:
        if str(it.get("artifact_id") or "") == str(artifact_id) and target is None:
            target = it
            continue
        kept.append(it)

    if not target:
        raise HTTPException(status_code=404, detail="artifact 不存在")

    stored_name = str(target.get("stored_name") or "").strip()
    if stored_name:
        try:
            (material_dir / stored_name).unlink()
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.info("delete_artifact 删除文件失败：%s", exc)

    _write_artifact_index(material_dir, kept)
    return _kb_ok({"artifact_id": str(artifact_id), "deleted": True})
