#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/19 11:16
# @File  : config.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :  项目的基本配置
import os


# =========================
# LLM 配置读取（支持复用 Outline）
# =========================
#
# 说明：
# - settings.json/设置页允许将 PPT_* 配置留空，以“复用 OUTLINE_*”
# - 环境变量在被显式写成空字符串时，os.getenv 会返回 ''（不会触发默认值）
#   因此这里需要统一把空字符串当作“未配置”处理。


def _get_env_str(key: str) -> str:
    return (os.getenv(key) or "").strip()


def _pick(primary_key: str, fallback_key: str, *, default: str) -> str:
    return _get_env_str(primary_key) or _get_env_str(fallback_key) or default


def _pick_optional(primary_key: str, fallback_key: str) -> str | None:
    value = _get_env_str(primary_key) or _get_env_str(fallback_key)
    return value or None


# 对所有的上面的研究员Agent的研究结果写PPT
PPT_WRITER_AGENT_CONFIG = {
    # "provider": "openai",
    # "provider": "local_openai",
    # "model": "gpt-4.1",
    # "provider": "google",
    # "model": "gemini-2.0-flash",
    # "provider": "claude",
    # "model": "claude-sonnet-4-20250514",
    # "provider": "deepseek",
    # "model": "deepseek-chat",
    # "model": "gpt-4o-2024-08-06",
    # 使用新的环境变量命名：PPT_WRITER_TYPE / PPT_WRITER_BASE_URL / PPT_WRITER_API_KEY
    # 默认为 openai 协议（通过 BASE_URL + API_KEY 区分厂商）
    # 允许 PPT_* 留空（settings 页选择“复用 Outline”） -> 回退到 OUTLINE_*
    "provider": _pick("PPT_WRITER_TYPE", "OUTLINE_TYPE", default="openai"),
    "model": _pick("PPT_WRITER_MODEL", "OUTLINE_MODEL", default="qwen-turbo-latest"),
    "api_key": _pick_optional("PPT_WRITER_API_KEY", "OUTLINE_API_KEY"),
    "base_url": _pick_optional("PPT_WRITER_BASE_URL", "OUTLINE_BASE_URL"),
}

# 检查每一页的PPT是否符合要求，不符合要求的会被重写
PPT_CHECKER_AGENT_CONFIG = {
    # "provider": "openai",
    # "provider": "local_openai",
    # "model": "gpt-4.1",
    # "provider": "google",
    # "model": "gemini-2.0-flash",
    # "provider": "claude",
    # "model": "claude-sonnet-4-20250514",
    # "provider": "local_deepseek",
    # "model": "deepseek-chat",
    # "model": "gpt-4o-2024-08-06",
    # 允许 PPT_* 留空（settings 页选择“复用 Outline”） -> 回退到 OUTLINE_*
    "provider": _pick("PPT_CHECKER_TYPE", "OUTLINE_TYPE", default="openai"),
    "model": _pick("PPT_CHECKER_MODEL", "OUTLINE_MODEL", default="qwen-turbo-latest"),
    "api_key": _pick_optional("PPT_CHECKER_API_KEY", "OUTLINE_API_KEY"),
    "base_url": _pick_optional("PPT_CHECKER_BASE_URL", "OUTLINE_BASE_URL"),
    # "provider": "deepseek",
    # "model": "deepseek-chat",
}

