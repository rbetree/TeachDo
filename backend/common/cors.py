from __future__ import annotations

import os
from typing import Iterable

from backend.common.settings_store import DEFAULT_SETTINGS_ENV, access_host_for_bind_host


def _split_csv(value: str) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def get_cors_allow_origins() -> list[str]:
    """
    获取 CORS allow_origins：
    - 显式设置 TEACHDO_CORS_ALLOW_ALL=1 时，返回 ["*"]（仅建议开发环境使用）
    - 显式设置 TEACHDO_CORS_ORIGINS=... 时，按逗号分隔解析
    - 否则默认允许本地前端端口（127.0.0.1 / localhost / ::1 + FRONTEND_PORT）
    """
    if _is_truthy(os.environ.get("TEACHDO_CORS_ALLOW_ALL")):
        return ["*"]

    explicit = _split_csv(os.environ.get("TEACHDO_CORS_ORIGINS") or os.environ.get("CORS_ORIGINS") or "")
    if explicit:
        return explicit

    bind_host = (os.environ.get("HOST") or str(DEFAULT_SETTINGS_ENV.get("HOST") or "127.0.0.1")).strip() or "127.0.0.1"
    access_host = access_host_for_bind_host(bind_host)
    try:
        port = int(str(os.environ.get("FRONTEND_PORT") or DEFAULT_SETTINGS_ENV.get("FRONTEND_PORT") or 5174).strip())
    except Exception:
        port = int(DEFAULT_SETTINGS_ENV.get("FRONTEND_PORT") or 5174)

    origins: set[str] = {
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
        f"http://[::1]:{port}",
        f"http://{access_host}:{port}",
    }
    return sorted(origins)


def get_cors_middleware_kwargs(*, allow_credentials: bool = False) -> dict:
    """
    生成 CORSMiddleware 的关键参数。
    - allow_methods/allow_headers 通常保持为 ["*"] 以减少开发摩擦
    - allow_credentials：默认 False；若确有跨域 cookie 需求再开启
    """
    origins = get_cors_allow_origins()
    return {
        "allow_origins": origins,
        "allow_credentials": bool(allow_credentials),
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }

