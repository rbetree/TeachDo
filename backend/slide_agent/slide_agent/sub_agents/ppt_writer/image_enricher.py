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

    # 数学/几何类：优先返回更贴近“图形/公式/图表”的英文关键词，避免一律落到 abstract。
    # 说明：Pexels 更偏英文检索，中文关键词命中不稳定，因此这里做一次轻量级映射。
    if any(k in s for k in ["三角形", "triangle"]):
        return "triangle geometry"
    if any(k in s for k in ["几何", "geometry"]):
        return "geometry"
    if any(k in s for k in ["数学", "math", "代数", "algebra", "函数", "function", "概率", "probability", "统计", "statistics"]):
        return "math"

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


def extract_english_hints(text: str) -> str:
    """
    从中文/混合文本中提取少量“可用于图片检索”的英文提示词。

    目标：
    - 在中文主题下提高 Pexels 命中率
    - 只做有限映射，避免引入大规模翻译依赖
    """
    raw = str(text or "").strip()
    if not raw:
        return ""

    hints: list[str] = []

    # 常见数学/几何关键词（可按需扩展）
    if "三角形" in raw or "triangle" in raw.lower():
        hints += ["triangle", "geometry"]
    if "四边形" in raw or "quadrilateral" in raw.lower():
        hints += ["quadrilateral", "geometry"]
    if "圆" in raw or "circle" in raw.lower():
        hints.append("circle")
    if any(k in raw for k in ["几何", "角", "边", "相似", "全等", "勾股"]):
        hints.append("geometry")
    if any(k in raw for k in ["函数", "坐标", "图像", "曲线"]):
        hints += ["graph", "math"]
    if any(k in raw for k in ["概率", "统计"]):
        hints += ["statistics", "math"]

    # 去重并保持顺序
    uniq: list[str] = []
    seen = set()
    for h in hints:
        k = h.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        uniq.append(h)

    return " ".join(uniq)


def _dedupe_keywords(query: str) -> str:
    parts = [p.strip() for p in str(query or "").split() if p and p.strip()]
    if not parts:
        return ""
    uniq: list[str] = []
    seen = set()
    for p in parts:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return " ".join(uniq)


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

    raw_text = " ".join([title, items_text]).strip()
    theme = detect_image_theme(raw_text)
    hints = extract_english_hints(raw_text)

    # Pexels 对中文关键词命中率不稳定：若已提取到英文提示词，则避免把中文标题直接拼进 query。
    title_for_query = title
    if hints:
        title_for_query = ""
    elif re.search(r"[\u4e00-\u9fff]", title_for_query or "") and not re.search(r"[a-zA-Z]", title_for_query or ""):
        title_for_query = ""

    keywords = _dedupe_keywords(" ".join([hints, theme, title_for_query]))
    keywords = re.sub(r"\s+", " ", keywords).strip()

    is_math = any(k in (keywords or "").lower() for k in ["triangle", "geometry", "math", "algebra", "statistics", "graph"])

    # 针对不同页型的检索偏好：尽量命中“背景/插图”类素材
    if slide_type == "cover":
        suffix = "diagram illustration background" if is_math else "abstract background"
    elif slide_type == "contents":
        suffix = "minimal geometry background" if is_math else "minimal abstract background"
    elif slide_type == "transition":
        suffix = "geometry background" if is_math else "abstract background"
    elif slide_type == "content":
        suffix = "diagram illustration" if is_math else "illustration"
    elif slide_type == "end":
        # 结束页优先简洁背景，不依赖标题
        title = ""
        keywords = _dedupe_keywords(" ".join([hints, theme]))
        keywords = re.sub(r"\s+", " ", keywords).strip()
        suffix = "minimal geometry background" if is_math else "minimal abstract background"
    else:
        suffix = "geometry background" if is_math else "abstract background"

    query = " ".join([keywords, suffix]).strip()
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

    # 兼容：部分模型会把 images 放进 data.images（而不是 JSON 顶层）。
    # 前端只读取顶层 slide.images 来替换模板图片，因此这里优先“提升”到顶层，
    # 避免重复调用 SearchImage 以及出现“日志里搜了图但 PPT 仍用模板图”的错觉。
    data = slide.get("data")
    if isinstance(data, dict):
        nested = data.get("images")
        if isinstance(nested, list) and nested:
            cleaned_nested: list[dict[str, Any]] = []
            for img in nested:
                if not isinstance(img, dict):
                    continue
                src = img.get("src")
                if not isinstance(src, str) or not src.strip():
                    continue
                cleaned_nested.append(img)

            if cleaned_nested:
                return {**slide, "images": cleaned_nested}

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
