#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/20 10:02
# @File  : tools.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :

import logging
from typing import Any
try:
    # 兼容“脚本方式”运行（在 backend/simpleOutline 目录下直接启动）
    from weixin_search import sogou_weixin_search, get_real_url, get_article_content
except ImportError:  # pragma: no cover - 单测/包导入场景
    from .weixin_search import sogou_weixin_search, get_real_url, get_article_content
import time
from datetime import datetime
import random

logger = logging.getLogger(__name__)


def _coerce_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y", "on"}:
            return True
        if v in {"0", "false", "no", "n", "off"}:
            return False
    return bool(value)

async def DocumentSearch(
    keyword: str,
    tool_context: Any,
):
    """
    根据关键词搜索文档
    :param keyword: str, 搜索的相关文档的关键词
    :return: 返回每篇文档数据
    """
    number = 3 # 默认搜索数量改小一些，防止有些本地模型的上下文过长
    agent_name = tool_context.agent_name
    logger.info(f"Agent{agent_name}正在调用工具：DocumentSearch: " + keyword)
    metadata = tool_context.state.get("metadata", {})
    if metadata is None:
        metadata = {}
    logger.info(f"调用工具：DocumentSearch时传入的metadata: {metadata}")

    use_web_search = None
    if isinstance(metadata, dict) and "use_web_search" in metadata:
        use_web_search = _coerce_bool(metadata.get("use_web_search"))
    if use_web_search is False:
        logger.info("DocumentSearch 已关闭(use_web_search=false)，跳过检索：%s", keyword)
        return f"已关闭联网检索（use_web_search=false），跳过搜索：{keyword}"

    logger.info("文档检索: " + keyword)
    start_time = time.time()
    results = sogou_weixin_search(keyword)
    if not results:
        return f"没有搜索到{keyword}相关的文章"
    articles = []
    results = results[:number]
    for every_result in results:
        sougou_link = every_result["link"]
        real_url = get_real_url(sougou_link)
        # referer：请求来源
        content = get_article_content(real_url, referer=sougou_link)
        article = {
            "title": every_result["title"],
            "publish_time": every_result["publish_time"],
            "real_url": real_url,
            "content": content
        }
        articles.append(article)
    end_time = time.time()
    logger.info(f"关键词{keyword}相关的文章已经获取完毕，获取到{len(articles)}篇, 耗时{end_time - start_time}秒")
    metadata["tool_document_ids"] = articles
    tool_context.state["metadata"] = metadata
    return articles

if __name__ == '__main__':
    result = DocumentSearch(keyword="电动汽车")
    print(result)
