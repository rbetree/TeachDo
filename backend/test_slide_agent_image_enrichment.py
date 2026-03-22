import asyncio


def test_slide_agent_auto_images_injects_images_when_enabled():
    """
    单测目标：
    - metadata.generate_with_images=True 时，服务端会补齐 slide.images
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
