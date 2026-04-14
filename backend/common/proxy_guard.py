from __future__ import annotations

import os

DEFAULT_PROXY_MAX_BYTES = 25 * 1024 * 1024  # 25MB


def _split_csv(value: str) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


def get_proxy_allowed_hosts() -> list[str]:
    """
    读取代理域名白名单（逗号分隔）。
    - 空列表：不启用白名单（兼容现有行为）
    """
    return _split_csv(os.environ.get("TEACHDO_PROXY_ALLOWED_HOSTS") or "")


def is_proxy_host_allowed(hostname: str, allowed_hosts: list[str]) -> bool:
    """
    判断 hostname 是否命中 allowlist。
    - host == allowed
    - host.endswith("." + allowed)
    """
    host = str(hostname or "").strip().lower().rstrip(".")
    if not host:
        return False
    for item in allowed_hosts:
        allowed = str(item or "").strip().lower().rstrip(".")
        if not allowed:
            continue
        if host == allowed:
            return True
        if host.endswith("." + allowed):
            return True
    return False


def get_proxy_max_bytes() -> int:
    """
    读取代理响应体最大字节数。
    - 未设置或非法：使用默认值
    - <= 0：使用默认值（避免误配置导致“无限制”）
    """
    raw = (os.environ.get("TEACHDO_PROXY_MAX_BYTES") or "").strip()
    if not raw:
        return DEFAULT_PROXY_MAX_BYTES
    try:
        value = int(raw)
    except Exception:
        return DEFAULT_PROXY_MAX_BYTES
    if value <= 0:
        return DEFAULT_PROXY_MAX_BYTES
    return value

