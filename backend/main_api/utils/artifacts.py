import os
import json
import time
import uuid
import logging
from pathlib import Path
from typing import Any

from backend.main_api.utils.repo import _find_repo_root

logger = logging.getLogger(__name__)


def _artifact_safe_filename(name: str) -> str:
    """
    artifacts 落盘用的文件名净化：
    - 兼容 Windows/WSL 的 NTFS（例如 ':' 在文件名中不合法）
    - 避免路径穿越
    """
    from backend.main_api.utils.kb import _kb_safe_filename

    safe = _kb_safe_filename(name)
    for ch in [":", "<", ">", '"', "|", "?", "*"]:
        safe = safe.replace(ch, "_")
    safe = safe.strip()
    if safe in {"", ".", ".."}:
        return ""
    return safe


def _artifact_safe_segment(value: str) -> str:
    safe = _artifact_safe_filename(str(value or ""))
    safe = safe.replace("..", "_").strip("._")
    return safe or "unknown"


def _get_artifact_root_dir() -> Path:
    """
    Artifacts 根目录：
    - env: TEACHDO_ARTIFACT_DIR（默认 var/artifacts）
    - 相对路径按 repo root 解析（复用 _find_repo_root）
    """
    configured = (os.environ.get("TEACHDO_ARTIFACT_DIR") or "").strip()
    repo_root = _find_repo_root(Path(__file__).resolve())
    root = (Path(configured) if configured else Path("var/artifacts"))
    if not root.is_absolute():
        root = repo_root / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def _normalize_artifact_kind(kind: str) -> str | None:
    k = (kind or "").strip().lower()
    return k if k in {"pptx", "docx"} else None


def _artifact_media_type(kind: str) -> str:
    k = (kind or "").strip().lower()
    if k == "pptx":
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    if k == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"


def _get_artifact_material_dir(*, user_id: str, material_id: str) -> Path:
    root = _get_artifact_root_dir()
    u = _artifact_safe_segment(user_id)
    m = _artifact_safe_segment(material_id)
    path = root / u / m
    path.mkdir(parents=True, exist_ok=True)
    return path


def _artifact_index_path(material_dir: Path) -> Path:
    return material_dir / "index.json"


def _load_artifact_index(material_dir: Path) -> list[dict[str, Any]]:
    path = _artifact_index_path(material_dir)
    if not path.exists():
        return []
    try:
        raw = path.read_text("utf-8")
        obj = json.loads(raw)
    except Exception:
        logger.warning("读取 artifact 索引失败: %s", path, exc_info=True)
        return []

    items: Any = None
    if isinstance(obj, dict):
        items = obj.get("artifacts")
    elif isinstance(obj, list):
        items = obj
    if not isinstance(items, list):
        return []
    return [it for it in items if isinstance(it, dict)]


def _write_artifact_index(material_dir: Path, items: list[dict[str, Any]]) -> None:
    path = _artifact_index_path(material_dir)
    tmp = path.with_suffix(".json.tmp")
    payload = {"artifacts": items}
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), "utf-8")
    os.replace(tmp, path)


def _artifact_public_meta(item: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "artifact_id": str(item.get("artifact_id") or ""),
        "kind": str(item.get("kind") or ""),
        "file_name": str(item.get("file_name") or ""),
    }
    created_at = item.get("created_at")
    if created_at is not None:
        try:
            meta["created_at"] = int(created_at)
        except Exception:
            logger.debug("忽略非法 created_at: %r", created_at, exc_info=True)
            pass
    size = item.get("size")
    if size is not None:
        try:
            meta["size"] = int(size)
        except Exception:
            logger.debug("忽略非法 size: %r", size, exc_info=True)
            pass
    return meta


def _save_artifact_bytes(
    *,
    user_id: str,
    material_id: str,
    kind: str,
    file_bytes: bytes,
    file_name: str,
) -> dict[str, Any]:
    normalized_kind = _normalize_artifact_kind(kind)
    if not normalized_kind:
        raise ValueError(f"非法 kind：{kind}")

    material_dir = _get_artifact_material_dir(user_id=str(user_id), material_id=str(material_id))

    artifact_id = uuid.uuid4().hex
    safe_name = _artifact_safe_filename(file_name) or f"{normalized_kind}.{normalized_kind}"
    if not safe_name.lower().endswith(f".{normalized_kind}"):
        safe_name = safe_name + f".{normalized_kind}"

    stored_name = f"{artifact_id}__{safe_name}"
    stored_path = material_dir / stored_name
    stored_path.write_bytes(file_bytes)

    created_at = int(time.time() * 1000)
    size = len(file_bytes) if isinstance(file_bytes, (bytes, bytearray)) else 0

    items = _load_artifact_index(material_dir)
    items.append(
        {
            "artifact_id": artifact_id,
            "kind": normalized_kind,
            "file_name": safe_name,
            "stored_name": stored_name,
            "created_at": created_at,
            "size": size,
        }
    )
    _write_artifact_index(material_dir, items)
    return _artifact_public_meta(items[-1])
