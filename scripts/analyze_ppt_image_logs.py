#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析 logs/content.log（或 docker logs 导出的文本），定位“自动配图为何不贴主题”。

该脚本不会修改任何代码，只做日志抽取，适合用于排查：
- 每一页（slide index/type/title）对应的 SearchImage query 是什么？
- 是否出现大量过于泛化的 query（仅 technology/abstract/minimal/background 等）？

用法：
  python3 scripts/analyze_ppt_image_logs.py --log logs/content.log

若你在 Docker 中运行，可先导出日志：
  docker compose logs --no-color content > /tmp/content.log
  python3 scripts/analyze_ppt_image_logs.py --log /tmp/content.log
"""

from __future__ import annotations

import argparse
import ast
import logging

logger = logging.getLogger(__name__)
import re
import sys
import textwrap
from dataclasses import dataclass, field
from typing import Dict, List, Optional


def _short(text: str, width: int = 40) -> str:
    return textwrap.shorten(str(text or ""), width=width, placeholder="…")


_RE_SLIDE_CTX = re.compile(r"当前要生成第(?P<idx>\d+)页的ppt，\s*类型为：(?P<type>[^，]+)，\s*具体内容为：(?P<schema>\{.*)$")
_RE_SEARCH = re.compile(
    r"正在搜索图片，关键词:\s*(?P<query>.+?)(?:\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+\[|$)"
)
_RE_SEARCH_OK = re.compile(r"成功搜索到\s*(?P<n>\d+)\s*张图片")


def _extract_title(schema: dict) -> str:
    if not isinstance(schema, dict):
        return ""
    data = schema.get("data")
    if isinstance(data, dict):
        title = data.get("title") or data.get("text") or ""
        if isinstance(title, str):
            return title.strip()
    return ""


@dataclass
class SlideLog:
    idx: int
    slide_type: str = ""
    title: str = ""
    queries: List[str] = field(default_factory=list)
    ok_counts: List[int] = field(default_factory=list)


def main() -> int:
    parser = argparse.ArgumentParser(description="TeachDo 自动配图日志分析（content.log）")
    parser.add_argument("--log", required=True, help="content.log 路径（或 docker logs 导出文件）")
    args = parser.parse_args()

    slides: Dict[int, SlideLog] = {}
    current_idx: Optional[int] = None

    with open(args.log, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = _RE_SLIDE_CTX.search(line)
            if m:
                idx = int(m.group("idx"))
                slide_type = (m.group("type") or "").strip()
                schema_raw = (m.group("schema") or "").strip()

                title = ""
                try:
                    schema = ast.literal_eval(schema_raw)
                    title = _extract_title(schema)
                except Exception:
                    # schema 解析失败时不阻断，只记录 idx/type
                    logger.debug(f"解析 schema 失败: {schema_raw[:200]!r}", exc_info=True)
                    title = ""

                slides.setdefault(idx, SlideLog(idx=idx))
                slides[idx].slide_type = slide_type
                if title:
                    slides[idx].title = title
                current_idx = idx
                continue

            m = _RE_SEARCH.search(line)
            if m and current_idx is not None:
                q = (m.group("query") or "").strip()
                if q:
                    slides.setdefault(current_idx, SlideLog(idx=current_idx)).queries.append(q)
                continue

            m = _RE_SEARCH_OK.search(line)
            if m and current_idx is not None:
                try:
                    n = int(m.group("n"))
                except Exception:
                    logger.debug(f"解析搜索结果数量失败: {m.group('n')!r}", exc_info=True)
                    n = -1
                slides.setdefault(current_idx, SlideLog(idx=current_idx)).ok_counts.append(n)
                continue

    if not slides:
        print("未从日志中解析到 slide 或 SearchImage 记录。请确认使用的是 content.log（内容生成服务）。")
        return 1

    for idx in sorted(slides):
        s = slides[idx]
        queries = s.queries or []
        q_show = " | ".join(_short(q, 60) for q in queries[:3]) + (" | …" if len(queries) > 3 else "")
        ok = ""
        if s.ok_counts:
            ok = f" ok={s.ok_counts[-1]}"

        print(
            f"[{idx:02d}] {s.slide_type:10s} title={_short(s.title, 24):24s} "
            f"queries={q_show or '-'}{ok}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

