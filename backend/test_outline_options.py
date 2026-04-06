from __future__ import annotations

import asyncio

import pytest


def test_build_outline_instruction_presets():
    from backend.simpleOutline import prompt

    short_text = prompt.build_outline_instruction(language="chinese", outline_length="short", use_web_search=True)
    assert "一级部分数量：3个；每个一级部分下含2–3个二级小节" in short_text
    assert "每个二级小节列出2–3个要点" in short_text
    assert "DocumentSearch" in short_text

    standard_text = prompt.build_outline_instruction(language="chinese", outline_length="standard", use_web_search=True)
    assert "一级部分数量：5个；每个一级部分下含3–4个二级小节" in standard_text
    assert "每个二级小节列出3–5个要点" in standard_text

    long_text = prompt.build_outline_instruction(language="chinese", outline_length="long", use_web_search=False)
    assert "一级部分数量：6个；每个一级部分下含4–5个二级小节" in long_text
    assert "每个二级小节列出4–6个要点" in long_text
    assert "禁止调用DocumentSearch" in long_text


def test_document_search_skips_network_when_disabled(monkeypatch: pytest.MonkeyPatch):
    import backend.simpleOutline.tools as tools

    def _boom(*_args, **_kwargs):  # noqa: ANN001 - 测试用
        raise AssertionError("sogou_weixin_search should not be called when use_web_search=false")

    monkeypatch.setattr(tools, "sogou_weixin_search", _boom)

    class DummyToolContext:
        agent_name = "test_agent"
        state = {"metadata": {"use_web_search": False}}

    result = asyncio.run(tools.DocumentSearch("电动汽车", DummyToolContext()))
    assert "已关闭联网检索" in str(result)


def test_outline_endpoint_passes_options_via_metadata(monkeypatch: pytest.MonkeyPatch):
    import backend.main_api.main as main_api
    from fastapi.testclient import TestClient

    captured: dict[str, object] = {}

    class DummyOutlineClientWrapper:
        def __init__(self, session_id: str, agent_url: str):  # noqa: ARG002
            self.session_id = session_id
            self.agent_url = agent_url

        async def generate(self, user_question: str, language: str = "chinese", user_id: str = "", metadata=None):
            captured["prompt"] = user_question
            captured["language"] = language
            captured["user_id"] = user_id
            captured["metadata"] = metadata
            yield {"type": "text", "text": "ok"}

    monkeypatch.setattr(main_api, "A2AOutlineClientWrapper", DummyOutlineClientWrapper)

    client = TestClient(main_api.app)
    with client.stream(
        "POST",
        "/tools/outline",
        data={
            "content": "主题：冒烟测试",
            "language": "chinese",
            "user_id": "u-test",
            "outline_length": "short",
            "use_web_search": "false",
        },
        headers={"Accept": "text/event-stream"},
    ) as resp:
        assert resp.status_code == 200
        # 触发消费，确保内部 async generator 真正跑起来
        for line in resp.iter_lines():
            text_line = line.decode("utf-8", errors="replace") if isinstance(line, (bytes, bytearray)) else str(line)
            if text_line and "[DONE]" in text_line:
                break

    assert captured.get("user_id") == "u-test"
    md = captured.get("metadata")
    assert isinstance(md, dict)
    assert md.get("outline_length") == "short"
    assert md.get("use_web_search") is False
