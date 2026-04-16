from __future__ import annotations

import pytest


def _get_writer_config():
    # 配置读取为函数式实现：每次调用都会读取当前环境变量
    from backend.slide_agent.slide_agent.config import get_ppt_writer_agent_config

    return get_ppt_writer_agent_config()


def _get_checker_config():
    from backend.slide_agent.slide_agent.config import get_ppt_checker_agent_config

    return get_ppt_checker_agent_config()


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

    cfg = _get_writer_config()
    assert cfg["provider"] == "openai"
    assert cfg["model"] == "gpt-4o-mini"
    assert cfg["api_key"] == "sk-outline"
    assert cfg["base_url"] == "https://example.com/v1"


def test_ppt_writer_overrides_outline_when_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OUTLINE_TYPE", "openai")
    monkeypatch.setenv("OUTLINE_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OUTLINE_API_KEY", "sk-outline")
    monkeypatch.setenv("OUTLINE_BASE_URL", "https://example.com/v1")

    monkeypatch.setenv("PPT_WRITER_TYPE", "claude")
    monkeypatch.setenv("PPT_WRITER_MODEL", "claude-sonnet-4-20250514")
    monkeypatch.setenv("PPT_WRITER_API_KEY", "sk-ppt")
    monkeypatch.setenv("PPT_WRITER_BASE_URL", "https://ppt.example.com")

    cfg = _get_writer_config()
    assert cfg["provider"] == "claude"
    assert cfg["model"] == "claude-sonnet-4-20250514"
    assert cfg["api_key"] == "sk-ppt"
    assert cfg["base_url"] == "https://ppt.example.com"


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

    cfg = _get_writer_config()
    assert cfg["provider"] == "openai"
    assert cfg["model"] == "qwen-turbo-latest"
    assert cfg["api_key"] is None
    assert cfg["base_url"] is None


def test_ppt_checker_inherits_outline_when_blank(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OUTLINE_TYPE", "openai")
    monkeypatch.setenv("OUTLINE_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OUTLINE_API_KEY", "sk-outline")
    monkeypatch.setenv("OUTLINE_BASE_URL", "https://example.com/v1")

    monkeypatch.setenv("PPT_CHECKER_TYPE", "")
    monkeypatch.setenv("PPT_CHECKER_MODEL", "")
    monkeypatch.setenv("PPT_CHECKER_BASE_URL", "")
    monkeypatch.delenv("PPT_CHECKER_API_KEY", raising=False)

    cfg = _get_checker_config()
    assert cfg["provider"] == "openai"
    assert cfg["model"] == "gpt-4o-mini"
    assert cfg["api_key"] == "sk-outline"
    assert cfg["base_url"] == "https://example.com/v1"


def test_ppt_checker_overrides_outline_when_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OUTLINE_TYPE", "openai")
    monkeypatch.setenv("OUTLINE_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OUTLINE_API_KEY", "sk-outline")
    monkeypatch.setenv("OUTLINE_BASE_URL", "https://example.com/v1")

    monkeypatch.setenv("PPT_CHECKER_TYPE", "claude")
    monkeypatch.setenv("PPT_CHECKER_MODEL", "claude-sonnet-4-20250514")
    monkeypatch.setenv("PPT_CHECKER_API_KEY", "sk-checker")
    monkeypatch.setenv("PPT_CHECKER_BASE_URL", "https://checker.example.com")

    cfg = _get_checker_config()
    assert cfg["provider"] == "claude"
    assert cfg["model"] == "claude-sonnet-4-20250514"
    assert cfg["api_key"] == "sk-checker"
    assert cfg["base_url"] == "https://checker.example.com"


def test_ppt_checker_defaults_when_all_missing(monkeypatch: pytest.MonkeyPatch):
    for k in [
        "OUTLINE_TYPE",
        "OUTLINE_MODEL",
        "OUTLINE_API_KEY",
        "OUTLINE_BASE_URL",
        "PPT_CHECKER_TYPE",
        "PPT_CHECKER_MODEL",
        "PPT_CHECKER_API_KEY",
        "PPT_CHECKER_BASE_URL",
    ]:
        monkeypatch.delenv(k, raising=False)

    cfg = _get_checker_config()
    assert cfg["provider"] == "openai"
    assert cfg["model"] == "qwen-turbo-latest"
    assert cfg["api_key"] is None
    assert cfg["base_url"] is None
