#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TeachDo/后端接口冒烟验证脚本（无第三方依赖）。

用途：
- 验证后端直连（例如 http://127.0.0.1:6800）
- 验证前端 dev server 的 /api 代理是否正确（例如 http://127.0.0.1:3000 + prefix=/api）

说明：
- 默认会验证 outline/ppt 两个 SSE；如果你当前环境没有配置模型/外网，允许用 --skip-* 跳过。
- KB 校验默认不启用；阶段 C0 完成后用 --require-kb 强制校验。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener, install_opener, urlopen


def _join_url(base_url: str, prefix: str, path: str) -> str:
    base = (base_url or "").rstrip("/")
    pre = (prefix or "").strip()
    if pre and not pre.startswith("/"):
        pre = "/" + pre
    pre = pre.rstrip("/")
    p = path if path.startswith("/") else "/" + path
    return f"{base}{pre}{p}"


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: bytes
    headers: Dict[str, str]


def _http_request(
    url: str,
    *,
    method: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[bytes] = None,
    timeout_s: float = 30.0,
) -> HttpResult:
    req = Request(url, data=body, method=method.upper())
    for k, v in (headers or {}).items():
        req.add_header(k, v)

    try:
        with urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return HttpResult(status=int(resp.status), body=raw, headers=hdrs)
    except HTTPError as e:
        # 读取错误响应体，便于定位
        try:
            raw = e.read() or b""
        except Exception:
            raw = b""
        hdrs = {k.lower(): v for k, v in getattr(e, "headers", {}).items()}
        return HttpResult(status=int(e.code), body=raw, headers=hdrs)
    except URLError as e:
        # 例如 Connection refused / timeout / DNS 失败等
        msg = str(getattr(e, "reason", e))
        return HttpResult(status=0, body=msg.encode("utf-8", errors="replace"), headers={})


def _print_ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _print_fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)


def _as_json(res: HttpResult) -> Tuple[bool, Optional[object], str]:
    if not res.body:
        return False, None, "empty body"
    try:
        return True, json.loads(res.body.decode("utf-8")), ""
    except Exception as e:
        snippet = res.body[:200].decode("utf-8", errors="replace")
        return False, None, f"json parse failed: {e}; body[:200]={snippet!r}"


def _strip_code_fence(payload: str) -> str:
    s = (payload or "").strip()
    if not s.startswith("```"):
        return s
    lines = s.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _iter_sse_events(resp, *, max_seconds: float) -> Iterable[str]:
    """
    解析 SSE 响应流，按“空行分隔事件”，把同一事件内的多行 data: 拼成完整 payload。
    """
    started = time.monotonic()
    data_lines: List[str] = []
    while True:
        if time.monotonic() - started > max_seconds:
            raise TimeoutError(f"SSE read timeout after {max_seconds}s")

        line = resp.readline()
        if not line:
            # EOF
            if data_lines:
                yield "\n".join(data_lines)
            return

        # 统一处理 \r\n
        if line in (b"\n", b"\r\n"):
            if data_lines:
                yield "\n".join(data_lines)
                data_lines = []
            continue

        if line.startswith(b":"):
            # comment / keep-alive
            continue

        if not line.startswith(b"data:"):
            # event/id/retry 等字段不处理
            continue

        part = line[len(b"data:") :]
        if part.startswith(b" "):
            part = part[1:]
        # readline() 带换行，去掉行尾 \r?\n
        data_lines.append(part.decode("utf-8", errors="replace").rstrip("\r\n"))


def _sse_post_form(
    url: str,
    form_fields: Dict[str, str],
    *,
    timeout_s: float,
    max_seconds: float,
) -> List[str]:
    body = urlencode(form_fields).encode("utf-8")
    req = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "close",
        },
    )

    try:
        with urlopen(req, timeout=timeout_s) as resp:
            return list(_iter_sse_events(resp, max_seconds=max_seconds))
    except HTTPError as e:
        raw = b""
        try:
            raw = e.read() or b""
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {raw[:500].decode('utf-8', errors='replace')}")
    except URLError as e:
        raise RuntimeError(f"request failed: {e}")


def _sse_post_json(
    url: str,
    payload_obj: object,
    *,
    timeout_s: float,
    max_seconds: float,
) -> List[str]:
    body = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")
    req = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "close",
        },
    )

    try:
        with urlopen(req, timeout=timeout_s) as resp:
            return list(_iter_sse_events(resp, max_seconds=max_seconds))
    except HTTPError as e:
        raw = b""
        try:
            raw = e.read() or b""
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {raw[:500].decode('utf-8', errors='replace')}")
    except URLError as e:
        raise RuntimeError(f"request failed: {e}")


def _encode_multipart_form(fields: Dict[str, str], file_field: str, file_name: str, file_bytes: bytes) -> Tuple[bytes, str]:
    boundary = f"----teachdo-boundary-{uuid.uuid4().hex}"
    crlf = b"\r\n"

    def _part_header(name: str, filename: Optional[str] = None, content_type: Optional[str] = None) -> bytes:
        disp = f'Content-Disposition: form-data; name="{name}"'
        if filename is not None:
            disp += f'; filename="{filename}"'
        headers = [disp]
        if content_type:
            headers.append(f"Content-Type: {content_type}")
        return ("\r\n".join(headers)).encode("utf-8")

    chunks: List[bytes] = []
    for k, v in fields.items():
        chunks.append(f"--{boundary}".encode("utf-8"))
        chunks.append(_part_header(k))
        chunks.append(b"")
        chunks.append((v or "").encode("utf-8"))

    chunks.append(f"--{boundary}".encode("utf-8"))
    chunks.append(_part_header(file_field, filename=file_name, content_type="application/octet-stream"))
    chunks.append(b"")
    chunks.append(file_bytes)

    chunks.append(f"--{boundary}--".encode("utf-8"))
    chunks.append(b"")
    body = crlf.join(chunks)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def _kb_upload(
    url: str,
    *,
    user_id: str,
    folder_id: int,
    timeout_s: float,
) -> Tuple[str, Dict[str, object]]:
    file_name = "teachdo_smoke.txt"
    file_bytes = b"TeachDo smoke upload\n"
    fields = {
        "user_id": user_id,
        "folder_id": str(folder_id),
        "file_type": "txt",
    }
    body, content_type = _encode_multipart_form(fields, "file", file_name, file_bytes)
    res = _http_request(
        url,
        method="POST",
        headers={"Content-Type": content_type, "Accept": "application/json"},
        body=body,
        timeout_s=timeout_s,
    )
    ok, data, err = _as_json(res)
    if res.status >= 400 or not ok or not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"kb upload failed: status={res.status}; err={err}; body={res.body[:200]!r}")
    payload = data.get("data") or {}
    if not isinstance(payload, dict) or not payload.get("file_id"):
        raise RuntimeError(f"kb upload response missing data.file_id: {payload!r}")
    return str(payload["file_id"]), payload


def _kb_vectorize_text(
    url: str,
    *,
    user_id: str,
    file_id: str,
    timeout_s: float,
) -> None:
    payload = {
        "user_id": user_id,
        "file_id": file_id,
        "file_name": "TeachDo 冒烟文档.md",
        "file_type": "md",
        "folder_id": 1,
        "content": "# TeachDo 冒烟\n\n这是一段用于知识库向量化的测试文本。\n",
    }
    res = _http_request(
        url,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout_s=timeout_s,
    )
    ok, data, err = _as_json(res)
    if res.status >= 400 or not ok or not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"kb vectorize failed: status={res.status}; err={err}; body={res.body[:200]!r}")


def _kb_list_files(url: str, *, timeout_s: float) -> List[Dict[str, object]]:
    res = _http_request(url, method="GET", headers={"Accept": "application/json"}, timeout_s=timeout_s)
    ok, data, err = _as_json(res)
    if res.status >= 400 or not ok or not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"kb list failed: status={res.status}; err={err}; body={res.body[:200]!r}")
    items = data.get("data")
    if not isinstance(items, list):
        raise RuntimeError(f"kb list data is not list: {items!r}")
    out: List[Dict[str, object]] = []
    for it in items:
        if isinstance(it, dict):
            out.append(it)
    return out


def _kb_delete(url: str, *, timeout_s: float) -> None:
    res = _http_request(url, method="DELETE", headers={"Accept": "application/json"}, timeout_s=timeout_s)
    ok, data, err = _as_json(res)
    if res.status >= 400 or not ok or not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"kb delete failed: status={res.status}; err={err}; body={res.body[:200]!r}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="TeachDo endpoint smoke verifier")
    parser.add_argument("--base-url", default="http://127.0.0.1:6800", help="目标服务地址，例如 http://127.0.0.1:6800")
    parser.add_argument("--prefix", default="", help="统一前缀，例如通过前端 /api 代理时传 /api")
    parser.add_argument("--timeout", type=float, default=30.0, help="单次 HTTP 请求超时（秒）")
    parser.add_argument("--sse-timeout", type=float, default=90.0, help="单个 SSE 流最大读取时长（秒）")
    parser.add_argument(
        "--trust-env-proxy",
        action="store_true",
        help="默认禁用环境代理变量（避免本机 127.0.0.1 误走代理导致 502）；如需使用代理再显式开启",
    )
    parser.add_argument("--skip-outline", action="store_true", help="跳过 /tools/outline SSE 校验")
    parser.add_argument("--skip-ppt", action="store_true", help="跳过 /tools/ppt SSE 校验")
    parser.add_argument("--require-kb", action="store_true", help="强制校验 /kb/*（阶段 C0 完成后启用）")
    parser.add_argument("--kb-user-id", default="course-smoke", help="KB user_id（建议用 course.id），默认 course-smoke")
    args = parser.parse_args(argv)

    # urllib 会读取环境代理变量（HTTP_PROXY/HTTPS_PROXY），在部分环境下会导致本机请求误走代理返回 502。
    # 冒烟验证默认只针对本机服务，因此默认禁用代理；需要时再用 --trust-env-proxy 显式开启。
    if not args.trust_env_proxy:
        install_opener(build_opener(ProxyHandler({})))

    base_url = args.base_url
    prefix = args.prefix
    timeout_s = float(args.timeout)
    sse_timeout_s = float(args.sse_timeout)

    failures: List[str] = []

    def _req_url(path: str) -> str:
        return _join_url(base_url, prefix, path)

    started = time.monotonic()

    # 1) healthz
    url = _req_url("/healthz")
    res = _http_request(url, method="GET", headers={"Accept": "application/json"}, timeout_s=timeout_s)
    if res.status != 200:
        msg = f"GET {url} -> {res.status}"
        _print_fail(msg)
        failures.append(msg)
    else:
        ok, data, err = _as_json(res)
        if not ok or not isinstance(data, dict) or not data.get("ok", False):
            msg = f"GET {url} -> unexpected json ({err})"
            _print_fail(msg)
            failures.append(msg)
        else:
            _print_ok(f"healthz ok ({url})")

    # 2) templates
    url = _req_url("/templates")
    res = _http_request(url, method="GET", headers={"Accept": "application/json"}, timeout_s=timeout_s)
    if res.status != 200:
        msg = f"GET {url} -> {res.status}"
        _print_fail(msg)
        failures.append(msg)
    else:
        ok, data, err = _as_json(res)
        if not ok or not isinstance(data, dict) or not isinstance(data.get("data"), list) or not data["data"]:
            msg = f"GET {url} -> unexpected json ({err})"
            _print_fail(msg)
            failures.append(msg)
        else:
            _print_ok(f"templates ok ({len(data['data'])} items)")

    # 3) outline sse
    if not args.skip_outline:
        url = _req_url("/tools/outline")
        try:
            events = _sse_post_form(
                url,
                {
                    "content": "冒烟测试：请生成一个简短的大纲（3-5条）。",
                    "language": "chinese",
                    "user_id": args.kb_user_id,
                    "folder_id": "0",
                },
                timeout_s=timeout_s,
                max_seconds=sse_timeout_s,
            )
            total_text = 0
            done = False
            for ev in events:
                if ev.strip() == "[DONE]":
                    done = True
                    break
                total_text += len(ev)
            if not done:
                raise RuntimeError("outline SSE missing [DONE]")
            if total_text < 10:
                raise RuntimeError(f"outline SSE too short: total_text={total_text}")
            _print_ok(f"outline SSE ok (total_text={total_text})")
        except Exception as e:
            msg = f"POST {url} (SSE) failed: {e}"
            _print_fail(msg)
            failures.append(msg)

    # 4) ppt sse
    if not args.skip_ppt:
        url = _req_url("/tools/ppt")
        payload = {
            "content": "# TeachDo 冒烟测试\n\n## 目录\n- 第一部分\n- 第二部分\n",
            "language": "zh",
            "sessionId": args.kb_user_id,
            "generateFromUploadedFile": False,
            # 冒烟测试默认关闭 web search，避免外网依赖；需要时可改为 True 再测。
            "generateFromWebSearch": False,
        }
        try:
            events = _sse_post_json(url, payload, timeout_s=timeout_s, max_seconds=sse_timeout_s)
            slide_count = 0
            done = False
            for ev in events:
                ev = ev.strip()
                if not ev:
                    continue
                if ev == "[DONE]":
                    done = True
                    break

                candidate = _strip_code_fence(ev)
                try:
                    obj = json.loads(candidate)
                except Exception:
                    continue

                if isinstance(obj, dict) and obj.get("type") == "error":
                    raise RuntimeError(f"ppt SSE error event: {obj.get('text') or obj}")

                if isinstance(obj, dict) and isinstance(obj.get("type"), str) and "data" in obj:
                    slide_count += 1
                    if slide_count >= 1:
                        # 冒烟测试只要求至少产出一页结构化 slide
                        pass

            if not done:
                raise RuntimeError("ppt SSE missing [DONE]")
            if slide_count < 1:
                raise RuntimeError("ppt SSE produced no JSON slides")
            _print_ok(f"ppt SSE ok (slides={slide_count})")
        except Exception as e:
            msg = f"POST {url} (SSE) failed: {e}"
            _print_fail(msg)
            failures.append(msg)

    # 5) kb
    kb_upload_file_id: Optional[str] = None
    kb_vector_file_id: Optional[str] = None
    if args.require_kb:
        user_id = args.kb_user_id
        try:
            upload_url = _req_url("/kb/upload")
            kb_upload_file_id, _meta = _kb_upload(upload_url, user_id=user_id, folder_id=0, timeout_s=timeout_s)
            _print_ok(f"kb upload ok (file_id={kb_upload_file_id})")

            list_url = _req_url(f"/kb/files/{user_id}?folder_id=0")
            items = _kb_list_files(list_url, timeout_s=timeout_s)
            if kb_upload_file_id not in {str(it.get('file_id')) for it in items}:
                raise RuntimeError("kb uploaded file not found in list")
            _print_ok(f"kb list ok (folder_id=0, items={len(items)})")

            kb_vector_file_id = f"gen:{user_id}:smoke:text"
            vector_url = _req_url("/kb/vectorize/text")
            _kb_vectorize_text(vector_url, user_id=user_id, file_id=kb_vector_file_id, timeout_s=timeout_s)
            _print_ok(f"kb vectorize ok (file_id={kb_vector_file_id})")

            list_url = _req_url(f"/kb/files/{user_id}?folder_id=1")
            items = _kb_list_files(list_url, timeout_s=timeout_s)
            if kb_vector_file_id not in {str(it.get('file_id')) for it in items}:
                raise RuntimeError("kb vectorized file not found in list")
            _print_ok(f"kb list ok (folder_id=1, items={len(items)})")
        except Exception as e:
            msg = f"KB verify failed: {e}"
            _print_fail(msg)
            failures.append(msg)
        finally:
            # 尽力清理测试数据，避免污染知识库
            for fid in [kb_upload_file_id, kb_vector_file_id]:
                if not fid:
                    continue
                try:
                    del_url = _req_url(f"/kb/files/{args.kb_user_id}/{fid}")
                    _kb_delete(del_url, timeout_s=timeout_s)
                    _print_ok(f"kb cleanup ok (file_id={fid})")
                except Exception as e:
                    _print_fail(f"kb cleanup failed (file_id={fid}): {e}")

    elapsed = time.monotonic() - started
    if failures:
        _print_fail(f"{len(failures)} checks failed in {elapsed:.1f}s")
        return 1
    _print_ok(f"all checks passed in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
