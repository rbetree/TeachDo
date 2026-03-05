from __future__ import annotations

import importlib

import pytest


def _reload_slide_config():
    # config.py 在 import 时读取环境变量，因此测试里需要 reload
    import backend.slide_agent.slide_agent.config as slide_config

    return importlib.reload(slide_config)


def test_ppt_writer_inherits_outline_when_blank(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OUTLINE_TYPE", "openai")
    monkeypatch.setenv("OUTLINE_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OUTLINE_API_KEY", "sk-outline")
    monkeypatch.setenv("OUTLINE_BASE_URL", "https://example.com/v1")

    # settings 页选择“复用 Outline”会写入空字符串（非 secret）到 settings.json
    monkeypatch.setenv("PPT_WRITER_TYPE", "")
    monkeypatch.setenv("PPT_WRITER_MODEL", "")
    monkeypatch.setenv("PPT_WRITER_BASE_URL", "")
    # secret 留空通常不会写入 settings.json，这里显式模拟为“未设置”
    monkeypatch.delenv("PPT_WRITER_API_KEY", raising=False)

    slide_config = _reload_slide_config()
    assert slide_config.PPT_WRITER_AGENT_CONFIG["provider"] == "openai"
    assert slide_config.PPT_WRITER_AGENT_CONFIG["model"] == "gpt-4o-mini"
    assert slide_config.PPT_WRITER_AGENT_CONFIG["api_key"] == "sk-outline"
    assert slide_config.PPT_WRITER_AGENT_CONFIG["base_url"] == "https://example.com/v1"


def test_ppt_writer_overrides_outline_when_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OUTLINE_TYPE", "openai")
    monkeypatch.setenv("OUTLINE_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OUTLINE_API_KEY", "sk-outline")
    monkeypatch.setenv("OUTLINE_BASE_URL", "https://example.com/v1")

    monkeypatch.setenv("PPT_WRITER_TYPE", "claude")
    monkeypatch.setenv("PPT_WRITER_MODEL", "claude-sonnet-4-20250514")
    monkeypatch.setenv("PPT_WRITER_API_KEY", "sk-ppt")
    monkeypatch.setenv("PPT_WRITER_BASE_URL", "https://ppt.example.com")

    slide_config = _reload_slide_config()
    assert slide_config.PPT_WRITER_AGENT_CONFIG["provider"] == "claude"
    assert slide_config.PPT_WRITER_AGENT_CONFIG["model"] == "claude-sonnet-4-20250514"
    assert slide_config.PPT_WRITER_AGENT_CONFIG["api_key"] == "sk-ppt"
    assert slide_config.PPT_WRITER_AGENT_CONFIG["base_url"] == "https://ppt.example.com"


def test_ppt_writer_defaults_when_all_missing(monkeypatch: pytest.MonkeyPatch):
    # 先清空相关环境变量，确保用例不受外部影响
    for k in [
        "OUTLINE_TYPE",
        "OUTLINE_MODEL",
        "OUTLINE_API_KEY",
        "OUTLINE_BASE_URL",
        "PPT_WRITER_TYPE",
        "PPT_WRITER_MODEL",
        "PPT_WRITER_API_KEY",
        "PPT_WRITER_BASE_URL",
    ]:
        monkeypatch.delenv(k, raising=False)

    slide_config = _reload_slide_config()
    assert slide_config.PPT_WRITER_AGENT_CONFIG["provider"] == "openai"
    assert slide_config.PPT_WRITER_AGENT_CONFIG["model"] == "qwen-turbo-latest"
    assert slide_config.PPT_WRITER_AGENT_CONFIG["api_key"] is None
    assert slide_config.PPT_WRITER_AGENT_CONFIG["base_url"] is None

