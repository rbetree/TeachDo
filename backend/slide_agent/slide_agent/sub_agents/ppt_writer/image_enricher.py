from __future__ import annotations

import hashlib
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


_PRESET_IMAGE_POOLS: dict[str, list[str]] = {
    "technology": [
        "https://images.pexels.com/photos/3861969/pexels-photo-3861969.jpeg",
        "https://images.pexels.com/photos/3861967/pexels-photo-3861967.jpeg",
        "https://images.pexels.com/photos/3861966/pexels-photo-3861966.jpeg",
        "https://images.pexels.com/photos/3861965/pexels-photo-3861965.jpeg",
        "https://images.pexels.com/photos/3861964/pexels-photo-3861964.jpeg",
    ],
    "business": [
        "https://images.pexels.com/photos/3183150/pexels-photo-3183150.jpeg",
        "https://images.pexels.com/photos/3183153/pexels-photo-3183153.jpeg",
        "https://images.pexels.com/photos/3183154/pexels-photo-3183154.jpeg",
        "https://images.pexels.com/photos/3183155/pexels-photo-3183155.jpeg",
        "https://images.pexels.com/photos/3183156/pexels-photo-3183156.jpeg",
    ],
    "nature": [
        "https://images.pexels.com/photos/3225517/pexels-photo-3225517.jpeg",
        "https://images.pexels.com/photos/3225518/pexels-photo-3225518.jpeg",
        "https://images.pexels.com/photos/3225519/pexels-photo-3225519.jpeg",
        "https://images.pexels.com/photos/3225520/pexels-photo-3225520.jpeg",
        "https://images.pexels.com/photos/3225521/pexels-photo-3225521.jpeg",
    ],
    "abstract": [
        "https://images.pexels.com/photos/3255761/pexels-photo-3255761.jpeg",
        "https://images.pexels.com/photos/3255762/pexels-photo-3255762.jpeg",
        "https://images.pexels.com/photos/3255763/pexels-photo-3255763.jpeg",
        "https://images.pexels.com/photos/3255764/pexels-photo-3255764.jpeg",
        "https://images.pexels.com/photos/3255765/pexels-photo-3255765.jpeg",
    ],
}


def resolve_image_source(metadata: dict) -> str:
    """
    决定配图来源：
    - network：联网检索（Pexels）
    - preset：使用内置预设图片池（不发起检索）
    """
    raw = metadata.get("image_source")
    if isinstance(raw, str):
        v = raw.strip().lower()
        if v in {"network", "preset"}:
            return v

    # 兼容旧字段：generate_with_images 之前表示“启用自动配图”
    # 现在将其解释为：是否启用“联网配图”。
    return "network" if is_truthy_value(metadata.get("generate_with_images")) else "preset"


def preset_images(query: str, count: int) -> List[Dict[str, Any]]:
    """
    从内置图片池生成候选图片列表（确定性输出，便于缓存与测试）。
    """
    q = (query or "").strip()
    q_lower = q.lower()

    selected_pool = "abstract"
    for key in ("technology", "business", "nature", "abstract"):
        if key in q_lower:
            selected_pool = key
            break

    pool = _PRESET_IMAGE_POOLS.get(selected_pool) or _PRESET_IMAGE_POOLS["abstract"]
    if not pool:
        return []

    safe_count = max(1, int(count or 1))
    safe_count = min(safe_count, 12)

    digest = hashlib.md5(q_lower.encode("utf-8"), usedforsecurity=False).hexdigest()
    start = int(digest, 16) % len(pool)

    picked: list[str] = []
    for i in range(safe_count):
        picked.append(pool[(start + i) % len(pool)])

    images: list[dict[str, Any]] = []
    for idx, src in enumerate(picked):
        images.append(
            {
                "id": f"preset:{selected_pool}:{start + idx}",
                "src": src,
                "width": 1920,
                "height": 1080,
                "alt": q or selected_pool,
                "photographer": "Pexels",
                "url": src,
                "source": "preset",
            }
        )
    return images


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

    配图策略：
    - 开启“联网配图”（metadata.image_source=network 或 metadata.generate_with_images=true）：调用 SearchImage 联网检索。
    - 关闭“联网配图”（preset）：使用内置预设图片池配图，不发起联网检索。
    """
    if not isinstance(slide, dict):
        return slide

    metadata = state.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

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
    source = resolve_image_source(metadata)

    cache = state.get("image_search_cache")
    if not isinstance(cache, dict):
        cache = {}
        state["image_search_cache"] = cache
    cache_key = f"{source}|{query}|{count}"

    images = cache.get(cache_key)
    if not isinstance(images, list):
        if source == "network":
            images = await search_image(query=query, count=count, tool_context=None)
        else:
            images = preset_images(query=query, count=count)
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
