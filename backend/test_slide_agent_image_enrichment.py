import asyncio


def test_slide_agent_images_network_mode_uses_search_tool_and_injects_images():
    """
    单测目标：
    - 开启“联网配图”（metadata.generate_with_images=True）时：服务端会补齐 slide.images，并触发 search_image
    - 不依赖真实 Pexels 网络请求（注入 search_image stub）
    """

    from backend.slide_agent.slide_agent.sub_agents.ppt_writer.image_enricher import maybe_attach_images_to_slide

    calls = {"n": 0, "query": "", "count": 0}

    async def _fake_search_image(*, query: str, count: int = 1, tool_context=None):
        calls["n"] += 1
        calls["query"] = query
        calls["count"] = count
        return [
            {
                "id": f"img-{i}",
                "src": f"https://example.com/{i}.jpg",
                "width": 1200,
                "height": 800,
                "alt": query,
            }
            for i in range(count)
        ]

    slide = {
        "type": "content",
        "data": {
            "title": "AI 与商业应用",
            "items": [{"title": "自动化", "text": "提升效率"}],
        },
    }
    state = {"metadata": {"generate_with_images": True, "image_count": 3}}

    enriched = asyncio.run(maybe_attach_images_to_slide(slide, state=state, search_image=_fake_search_image))

    assert calls["n"] == 1
    assert calls["count"] == 3
    assert "technology" in (calls["query"] or "")
    assert isinstance(enriched.get("images"), list)
    assert len(enriched["images"]) == 3
    assert all(isinstance(it, dict) and it.get("src") for it in enriched["images"])

    # 已有 images 时不应再次触发检索
    enriched2 = asyncio.run(maybe_attach_images_to_slide(enriched, state=state, search_image=_fake_search_image))
    assert calls["n"] == 1
    assert enriched2.get("images") == enriched.get("images")


def test_slide_agent_images_preset_mode_injects_images_without_network():
    """
    单测目标：
    - 关闭“联网配图”（metadata.generate_with_images=False）时：仍会补齐 slide.images
    - 且不会触发 search_image（使用内置预设图片池）
    """

    from backend.slide_agent.slide_agent.sub_agents.ppt_writer.image_enricher import maybe_attach_images_to_slide

    calls = {"n": 0}

    async def _fake_search_image(*, query: str, count: int = 1, tool_context=None):
        calls["n"] += 1
        return [{"id": "net-1", "src": "https://example.com/1.jpg"}]

    slide = {"type": "cover", "data": {"title": "三角形的基本性质"}}
    state = {"metadata": {"generate_with_images": False, "image_count": 2}}

    enriched = asyncio.run(maybe_attach_images_to_slide(slide, state=state, search_image=_fake_search_image))

    assert calls["n"] == 0
    assert isinstance(enriched.get("images"), list)
    assert len(enriched["images"]) == 2
    assert all(isinstance(it, dict) and it.get("src") for it in enriched["images"])


def test_slide_agent_promotes_nested_images_to_top_level_without_search():
    """
    单测目标：
    - 若模型把 images 写进 data.images（而不是 JSON 顶层），服务端应将其“提升”到顶层 slide.images
    - 且不应触发 search_image（避免重复检索 & 前端读不到导致仍用模板图）
    """

    from backend.slide_agent.slide_agent.sub_agents.ppt_writer.image_enricher import maybe_attach_images_to_slide

    calls = {"n": 0}

    async def _fake_search_image(*, query: str, count: int = 1, tool_context=None):
        calls["n"] += 1
        return [{"id": "net-1", "src": "https://example.com/1.jpg"}]

    slide = {
        "type": "content",
        "data": {
            "title": "任意主题",
            "items": [{"title": "点 1", "text": "..."}, {"title": "点 2", "text": "..."}],
            "images": [
                {"id": "nested-1", "src": "https://images.pexels.com/photos/1/pexels-photo-1.jpeg", "alt": "x"},
                {"id": "nested-2", "src": "https://images.pexels.com/photos/2/pexels-photo-2.jpeg", "alt": "y"},
            ],
        },
    }
    state = {"metadata": {"generate_with_images": True, "image_count": 3}}

    enriched = asyncio.run(maybe_attach_images_to_slide(slide, state=state, search_image=_fake_search_image))

    assert calls["n"] == 0
    assert isinstance(enriched.get("images"), list)
    assert len(enriched["images"]) == 2
    assert enriched["images"][0]["src"].startswith("https://")
