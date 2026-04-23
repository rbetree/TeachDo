import logging
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

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
from backend.main_api.utils.proxy import _aclose_httpx_stream, _open_validated_proxy_stream

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/proxy")
async def proxy(request: Request, url: str = Query(..., description="Target absolute URL")):
    """
    透明代理上游资源，转发部分请求头，透传关键响应头，并允许前端同源访问。
    适合图片/音视频等二进制内容。
    """
    HEADERS_TO_FORWARD = {"Range", "User-Agent"}  # 需要时可扩展
    HEADERS_TO_COPY = {
        "Content-Type",
        "Content-Length",
        "Content-Disposition",
        "Accept-Ranges",
        "ETag",
        "Last-Modified",
        "Cache-Control",
        "Expires",
    }
    forward_headers = {}
    for h in HEADERS_TO_FORWARD:
        v = request.headers.get(h)
        if v:
            forward_headers[h] = v

    try:
        client, upstream = await _open_validated_proxy_stream(url, headers=forward_headers)
    except UrlAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream fetch error: {exc!s}") from exc

    if upstream.status_code >= 400:
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(status_code=upstream.status_code, detail="Upstream error")

    max_bytes = get_proxy_max_bytes()
    upstream_content_length = upstream.headers.get("Content-Length")
    if upstream_content_length:
        try:
            if int(upstream_content_length) > max_bytes:
                await upstream.aclose()
                await client.aclose()
                raise HTTPException(status_code=413, detail="上游资源过大")
        except ValueError:
            # 非法 Content-Length 不阻断，交给流式计数兜底
            pass

    headers = {}
    for h in HEADERS_TO_COPY:
        if h in upstream.headers:
            headers[h] = upstream.headers[h]

    # 给静态资源加简单缓存（按需调整）
    headers.setdefault("Cache-Control", "public, max-age=86400")

    async def _limited_iter_bytes():
        total = 0
        async for chunk in upstream.aiter_bytes():
            if not chunk:
                continue
            next_total = total + len(chunk)
            if next_total > max_bytes:
                logger.warning(
                    "proxy 响应超过上限，已中断：url=%s total=%s max=%s",
                    url,
                    next_total,
                    max_bytes,
                )
                break
            total = next_total
            yield chunk

    return StreamingResponse(
        _limited_iter_bytes(),
        status_code=upstream.status_code,
        headers=headers,
        media_type=upstream.headers.get("Content-Type"),
        background=BackgroundTask(_aclose_httpx_stream, upstream, client),
    )
