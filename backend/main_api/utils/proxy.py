import httpx
from urllib.parse import urlsplit
from fastapi import HTTPException

from backend.common.proxy_guard import (
    get_proxy_allowed_hosts,
    get_proxy_max_bytes,
    is_proxy_host_allowed,
)
from backend.common.url_security import (
    REDIRECT_STATUS_CODES,
    UrlAccessError,
    resolve_and_validate_redirect_url,
    validate_public_http_url,
)


async def _aclose_httpx_stream(response: httpx.Response, client: httpx.AsyncClient) -> None:
    await response.aclose()
    await client.aclose()


async def _open_validated_proxy_stream(
    target_url: str,
    *,
    headers: dict[str, str],
    max_redirects: int = 3,
) -> tuple[httpx.AsyncClient, httpx.Response]:
    """
    以“每次跳转都校验目标地址”的方式打开上游流，避免 SSRF 通过重定向绕过。
    调用方负责在返回后关闭 response/client。
    """
    current_url = validate_public_http_url(target_url)
    allowed_hosts = get_proxy_allowed_hosts()

    def _ensure_allowed(url: str) -> None:
        if not allowed_hosts:
            return
        host = urlsplit(url).hostname or ""
        if not is_proxy_host_allowed(host, allowed_hosts):
            raise UrlAccessError("目标域名不在允许列表", status_code=403)

    _ensure_allowed(current_url)
    client = httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=False)

    try:
        for _ in range(max_redirects + 1):
            request = client.build_request("GET", current_url, headers=headers)
            response = await client.send(request, stream=True)
            if response.status_code in REDIRECT_STATUS_CODES and "location" in response.headers:
                next_url = resolve_and_validate_redirect_url(current_url, response.headers["location"])
                _ensure_allowed(next_url)
                await response.aclose()
                current_url = next_url
                continue
            return client, response
    except Exception:
        await client.aclose()
        raise

    await client.aclose()
    raise HTTPException(status_code=502, detail="上游重定向次数过多")
