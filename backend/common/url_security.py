from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit

IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class UrlAccessError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = int(status_code)


REDIRECT_STATUS_CODES: set[int] = {301, 302, 303, 307, 308}


def _truthy_env(name: str) -> bool:
    value = os.environ.get(name)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def allow_private_network_urls() -> bool:
    """
    仅用于本地调试时临时放开私网 URL 访问。
    生产环境默认必须关闭。
    """
    return _truthy_env("TEACHDO_ALLOW_PRIVATE_NETWORK_URLS")


def _is_disallowed_ip(ip: IpAddress) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_host_ips(hostname: str, port: int) -> set[IpAddress]:
    try:
        infos = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as exc:  # pragma: no cover - 依赖运行环境 DNS
        raise UrlAccessError(f"无法解析目标地址：{hostname}") from exc

    resolved: set[IpAddress] = set()
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        host = sockaddr[0]
        try:
            resolved.add(ipaddress.ip_address(host))
        except ValueError:
            continue

    if not resolved:
        raise UrlAccessError(f"无法解析目标地址：{hostname}")
    return resolved


def validate_public_http_url(
    url: str,
    *,
    allow_private_network: bool | None = None,
) -> str:
    """
    校验用户提供的 URL 仅指向公网 http/https 资源。
    - 禁止 file:// 等非 http(s) 协议
    - 禁止带账号口令的 URL
    - 默认拒绝本机/内网/保留地址（可通过环境变量临时放开）
    """
    raw = (url or "").strip()
    if not raw:
        raise UrlAccessError("url 不能为空")

    try:
        parts = urlsplit(raw)
    except Exception as exc:
        raise UrlAccessError("url 格式非法") from exc

    scheme = (parts.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise UrlAccessError("url 必须以 http:// 或 https:// 开头")
    if not parts.hostname:
        raise UrlAccessError("url 缺少主机名")
    if parts.username or parts.password:
        raise UrlAccessError("url 不允许包含账号信息")

    normalized = urlunsplit((scheme, parts.netloc, parts.path or "", parts.query, parts.fragment))

    if allow_private_network is None:
        allow_private_network = allow_private_network_urls()
    if allow_private_network:
        return normalized

    hostname = parts.hostname.strip()
    if hostname.lower() == "localhost":
        raise UrlAccessError("禁止访问本机或内网地址", status_code=403)

    port = int(parts.port or (443 if scheme == "https" else 80))

    try:
        resolved_ips = {ipaddress.ip_address(hostname)}
    except ValueError:
        resolved_ips = _resolve_host_ips(hostname, port)

    for resolved_ip in resolved_ips:
        if _is_disallowed_ip(resolved_ip):
            raise UrlAccessError(f"禁止访问本机或内网地址：{resolved_ip.compressed}", status_code=403)

    return normalized


def resolve_and_validate_redirect_url(
    current_url: str,
    location: str,
    *,
    allow_private_network: bool | None = None,
) -> str:
    target = urljoin(current_url, (location or "").strip())
    if not target:
        raise UrlAccessError("上游重定向缺少有效的 Location")
    return validate_public_http_url(target, allow_private_network=allow_private_network)
