#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPT 自动配图链路诊断脚本（避免“盲改”）

用途：
1) 直接调用后端 `/tools/ppt`（SSE）拿到每页 slide JSON；
2) 输出每页是否包含 images（顶层 / data.images），以及图片 URL 的来源（Pexels / 本地模板）；
3) 可把完整 slide JSON 保存成 jsonl，便于复现与对照。

典型用法：
  - 从文件读取大纲并启用联网配图：
      python3 scripts/diagnose_ppt_images.py --content-file /path/to/outline.md --with-images
  - 只做数据链路检查（不依赖 web search）：
      python3 scripts/diagnose_ppt_images.py --content-file outline.md --with-images --no-web-search
"""

from __future__ import annotations

import argparse
import json
import os
import logging
import sys
import textwrap
from dataclasses import dataclass

logger = logging.getLogger(__name__)
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse


def _strip_json_code_fence(raw: str) -> str:
    s = (raw or "").strip()
    if s.startswith("```json"):
        s = s[len("```json") :].strip()
    if s.startswith("```"):
        s = s[len("```") :].strip()
    if s.endswith("```"):
        s = s[: -len("```")].strip()
    return s


def _short(text: str, width: int = 60) -> str:
    return textwrap.shorten(str(text or ""), width=width, placeholder="…")


def _read_content(args: argparse.Namespace) -> str:
    if args.content is not None:
        return str(args.content)
    if args.content_file:
        with open(args.content_file, "r", encoding="utf-8") as f:
            return f.read()

    # 支持管道输入
    if not sys.stdin.isatty():
        return sys.stdin.read()

    raise SystemExit("ERROR: 需要提供 --content 或 --content-file，或通过 stdin 传入。")


def _classify_src(src: str) -> str:
    s = (src or "").strip()
    if not s:
        return "empty"
    if s.startswith(("/api/data/", "/data/", "api/data/")):
        return "template"
    if s.startswith(("http://", "https://")):
        host = (urlparse(s).hostname or "").lower()
        if host.endswith("pexels.com") or host == "images.pexels.com":
            return "pexels"
        return "http"
    return "other"


def _extract_title(slide: dict) -> str:
    slide_type = str(slide.get("type") or "").strip()
    data = slide.get("data")
    if not isinstance(data, dict):
        data = {}

    if slide_type == "contents":
        items = data.get("items")
        if isinstance(items, list) and items:
            items = [str(x) for x in items if str(x).strip()]
            return " / ".join(items[:3]) + (" …" if len(items) > 3 else "")
        return ""

    title = data.get("title") or data.get("text") or ""
    return str(title).strip()


def _extract_images(slide: dict) -> Tuple[List[dict], List[dict]]:
    top = slide.get("images")
    top_list = top if isinstance(top, list) else []

    data = slide.get("data")
    if not isinstance(data, dict):
        return top_list, []
    nested = data.get("images")
    nested_list = nested if isinstance(nested, list) else []
    return top_list, nested_list


@dataclass
class SlideImageSummary:
    index: int
    slide_type: str
    title: str
    top_images: int
    nested_images: int
    src_kind_counts: Dict[str, int]
    first_src: str
    first_alt: str


def _summarize_slide(slide: dict, index: int) -> SlideImageSummary:
    slide_type = str(slide.get("type") or "").strip()
    title = _extract_title(slide)
    top_list, nested_list = _extract_images(slide)

    counts: Dict[str, int] = {}
    first_src = ""
    first_alt = ""
    for img in top_list:
        if not isinstance(img, dict):
            continue
        src = img.get("src")
        if isinstance(src, str) and src.strip():
            kind = _classify_src(src)
            counts[kind] = counts.get(kind, 0) + 1
            if not first_src:
                first_src = src.strip()
                alt = img.get("alt")
                if isinstance(alt, str):
                    first_alt = alt.strip()

    return SlideImageSummary(
        index=index,
        slide_type=slide_type,
        title=title,
        top_images=len(top_list),
        nested_images=len(nested_list),
        src_kind_counts=counts,
        first_src=first_src,
        first_alt=first_alt,
    )


def _iter_sse_events(lines: Iterable[str]) -> Iterable[str]:
    """
    将 `iter_lines()` 的文本流解析为 SSE 事件 data（多行 data: 合并为一个字符串）。
    """
    buf: List[str] = []
    for raw_line in lines:
        line = raw_line.rstrip("\n")
        if not line:
            # event boundary
            yield "\n".join(buf)
            buf = []
            continue
        if line.startswith(":"):
            # comment / keep-alive
            continue
        if line.startswith("data:"):
            val = line[len("data:") :]
            if val.startswith(" "):
                val = val[1:]
            buf.append(val)
            continue
        # ignore other SSE fields like id/event/retry
    if buf:
        yield "\n".join(buf)


def _post_sse(
    *,
    server: str,
    payload: dict,
    timeout_s: float,
) -> Iterable[str]:
    """
    使用标准库发起 POST 并按行读取 SSE 响应，避免依赖第三方包（例如 httpx）。
    """
    import urllib.error
    import urllib.request

    url = server.rstrip("/") + "/tools/ppt"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=float(timeout_s)) as resp:
            status = getattr(resp, "status", None) or 200
            if int(status) >= 400:
                body = resp.read(4000).decode("utf-8", errors="ignore")
                raise SystemExit(f"ERROR: HTTP {status}: {body}")

            def _lines():
                while True:
                    b = resp.readline()
                    if not b:
                        break
                    yield b.decode("utf-8", errors="ignore")

            yield from _iter_sse_events(_lines())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read(4000).decode("utf-8", errors="ignore")
        except Exception:
            logger.debug("读取 HTTP 错误响应体失败", exc_info=True)
            body = ""
        raise SystemExit(f"ERROR: HTTP {e.code}: {body or e.reason}")
    except urllib.error.URLError as e:
        raise SystemExit(f"ERROR: 请求失败：{e}")


def main() -> int:
    parser = argparse.ArgumentParser(description="TeachDo PPT 自动配图诊断脚本")
    parser.add_argument("--server", default=os.environ.get("TEACHDO_MAIN_API", "http://127.0.0.1:6800"))
    parser.add_argument("--session-id", default="default_user")
    parser.add_argument("--language", default="zh")

    parser.add_argument("--with-images", action="store_true", help="启用 generateWithImages=true（联网配图）")
    parser.add_argument("--web-search", dest="web_search", action="store_true", default=True)
    parser.add_argument("--no-web-search", dest="web_search", action="store_false")

    parser.add_argument("--content", default=None, help="直接传入 Markdown 大纲内容（注意 shell 转义）")
    parser.add_argument("--content-file", default=None, help="从文件读取 Markdown 大纲内容")

    parser.add_argument("--dump-jsonl", default=None, help="将解析出的 slide JSON 逐行写入该文件（jsonl）")
    parser.add_argument("--max-slides", type=int, default=200, help="最多解析多少页 slide（防止异常无限流）")
    parser.add_argument("--timeout", type=float, default=600.0, help="请求超时（秒）")

    args = parser.parse_args()

    content = _read_content(args).strip()
    if not content:
        print("ERROR: content 为空")
        return 2

    payload = {
        "content": content,
        "language": args.language,
        "sessionId": args.session_id,
        "generateFromWebSearch": bool(args.web_search),
        "generateFromUploadedFile": False,
        "generateWithImages": bool(args.with_images),
        "kb_folder_ids": None,
        "kb_file_ids": None,
    }

    dump_f = None
    if args.dump_jsonl:
        dump_f = open(args.dump_jsonl, "w", encoding="utf-8")

    try:
        print(f"[diagnose] POST {args.server.rstrip('/')}/tools/ppt  withImages={payload['generateWithImages']} webSearch={payload['generateFromWebSearch']}")
        slide_count = 0
        for event_data in _post_sse(server=args.server, payload=payload, timeout_s=args.timeout):
            raw = (event_data or "").strip()
            if not raw:
                continue
            if raw == "[DONE]":
                break

            candidate = _strip_json_code_fence(raw).strip()
            try:
                obj = json.loads(candidate)
            except Exception:
                # 非 JSON 事件（可能是零散文本 token），忽略
                logger.debug(f"解析 SSE 事件 JSON 失败: {candidate[:200]!r}", exc_info=True)
                continue

            # 有些事件可能是 JSON 字符串/数组等（例如模型输出被包成字符串），与 slide 无关，直接忽略
            if not isinstance(obj, dict):
                continue

            t = obj.get("type")
            if t == "error":
                print(f"[error] {obj.get('text') or obj}")
                return 1

            if t in {"cover", "contents", "transition", "content", "reference", "end"}:
                if dump_f:
                    dump_f.write(json.dumps(obj, ensure_ascii=False) + "\n")

                summary = _summarize_slide(obj, slide_count)
                kind_desc = ", ".join(f"{k}={v}" for k, v in sorted(summary.src_kind_counts.items())) or "-"
                warn = ""
                if summary.top_images == 0 and summary.nested_images > 0:
                    warn = "  [WARN: images 在 data.images，前端默认不会读取]"
                elif summary.top_images == 0:
                    warn = "  [WARN: 无 images，PPT 将保留模板自带图片]"

                print(
                    f"[{summary.index:02d}] {summary.slide_type:10s}  "
                    f"title={_short(summary.title, 28):28s}  "
                    f"images(top/nested)={summary.top_images}/{summary.nested_images}  "
                    f"srcKinds={kind_desc:28s}  "
                    f"first={_short(summary.first_src, 48)}  "
                    f"alt={_short(summary.first_alt, 40)}"
                    f"{warn}"
                )

                slide_count += 1
                if slide_count >= int(args.max_slides or 0):
                    print("[diagnose] reached --max-slides, stop.")
                    break
    finally:
        if dump_f:
            dump_f.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
