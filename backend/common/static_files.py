from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

DEFAULT_ALLOWED_SUFFIXES: set[str] = {
    ".json",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".svg",
}


def resolve_safe_static_file(
    base_dir: Path,
    filename: str,
    *,
    allowed_suffixes: set[str] | None = None,
) -> Path | None:
    """
    安全解析「base_dir 下的静态文件」路径，避免路径穿越。

    设计目标：
    - 不依赖当前工作目录（CWD）
    - 仅允许安全的文件名字符集（不包含 /、\\、空白、中文等）
    - 仅允许白名单后缀（避免把任意文件当成静态文件暴露出去）

    返回：
    - 成功：返回绝对路径（已 resolve），且保证在 base_dir 内、且为文件
    - 失败：返回 None（调用方应统一返回 404，避免信息泄露）
    """

    base = Path(base_dir).resolve()
    name = str(filename or "").strip()
    if not name:
        return None

    if not _FILENAME_RE.fullmatch(name):
        return None

    # 防御性：即便 regex 已经限制，这里仍显式拒绝 ".."
    if ".." in name:
        return None

    suffixes = allowed_suffixes or DEFAULT_ALLOWED_SUFFIXES
    suffix = Path(name).suffix.lower()
    if suffix not in suffixes:
        return None

    candidate = (base / name).resolve()
    try:
        candidate.relative_to(base)
    except Exception:
        logger.debug("静态文件路径安全检查失败", exc_info=True)
        return None

    if not candidate.is_file():
        return None

    return candidate

