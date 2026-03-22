from __future__ import annotations

import re
from typing import Any, Awaitable, Callable, Dict, List


def is_truthy_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def detect_image_theme(text: str) -> str:
    """
    为了让 Pexels 搜索在中文输入下也有更稳定的命中率：
    - 从内容里粗略识别主题，再拼接稳定的英文关键词（technology/business/nature/abstract）。
    """
    s = (text or "").lower()
    theme_map = {
        "technology": ["ai", "a.i", "人工智能", "算法", "大模型", "机器学习", "深度学习", "科技", "技术", "数据", "数字化", "智能"],
        "business": ["商业", "市场", "营销", "企业", "管理", "战略", "品牌", "运营", "产品", "增长", "财务", "融资"],
        "nature": ["自然", "环境", "生态", "气候", "森林", "海洋", "动物", "植物", "水", "绿色", "可持续"],
        "education": ["教育", "学习", "课程", "教学", "课堂", "学生", "老师", "培训"],
    }
    for theme, keywords in theme_map.items():
        if any(k.lower() in s for k in keywords):
            # Pexels 搜索更偏英文；education 不一定有稳定素材池，降级到 abstract
            return "abstract" if theme == "education" else theme
    return "abstract"


def build_image_query(slide: dict) -> str:
    slide_type = str(slide.get("type") or "").strip().lower()
    data = slide.get("data") or {}
    if not isinstance(data, dict):
        data = {}

    title = str(data.get("title") or data.get("text") or "").strip()

    # 把 items 里的文本也纳入主题识别（content 页更准）
    items_text = ""
    items = data.get("items")
    if isinstance(items, list) and items:
        parts: list[str] = []
        for it in items[:8]:
            if not isinstance(it, dict):
                continue
            for key in ("title", "text"):
                v = it.get(key)
                if isinstance(v, str) and v.strip():
                    parts.append(v.strip())
        items_text = " ".join(parts)

    theme = detect_image_theme(" ".join([title, items_text]))

    # 针对不同页型的检索偏好：尽量命中“背景/插图”类素材
    if slide_type == "cover":
        suffix = "abstract background"
    elif slide_type == "contents":
        suffix = "minimal abstract background"
    elif slide_type == "transition":
        suffix = "abstract background"
    elif slide_type == "content":
        suffix = "illustration"
    elif slide_type == "end":
        # 结束页优先简洁背景，不依赖标题
        title = ""
        suffix = "minimal abstract background"
    else:
        suffix = "abstract background"

    query = " ".join([theme, title, suffix]).strip()
    query = re.sub(r"\s+", " ", query)
    return query or "abstract background"


async def maybe_attach_images_to_slide(
    slide: dict,
    *,
    state: Dict[str, Any],
    search_image: Callable[..., Awaitable[List[Dict[str, Any]]]],
) -> dict:
    """
    在不修改 LLM Prompt 约束的前提下，由服务端补齐 `slide.images`，供前端模板映射/导出嵌入使用。

    开关：metadata.generate_with_images 为真时启用。
    """
    if not isinstance(slide, dict):
        return slide

    metadata = state.get("metadata") or {}
    if not isinstance(metadata, dict) or not is_truthy_value(metadata.get("generate_with_images")):
        return slide

    existing = slide.get("images")
    if isinstance(existing, list) and existing:
        return slide

    # 每页默认给一组候选图片（覆盖常见模板的多图片槽位）；可通过 metadata.image_count 覆盖
    try:
        count = int(metadata.get("image_count") or 6)
    except Exception:
        count = 6
    count = max(1, min(count, 12))

    query = build_image_query(slide)

    cache = state.get("image_search_cache")
    if not isinstance(cache, dict):
        cache = {}
        state["image_search_cache"] = cache
    cache_key = f"{query}|{count}"

    images = cache.get(cache_key)
    if not isinstance(images, list):
        images = await search_image(query=query, count=count, tool_context=None)
        cache[cache_key] = images

    cleaned: list[dict[str, Any]] = []
    for img in images:
        if not isinstance(img, dict):
            continue
        src = img.get("src")
        if not isinstance(src, str) or not src.strip():
            continue
        cleaned.append(img)

    if not cleaned:
        return slide

    return {**slide, "images": cleaned}

