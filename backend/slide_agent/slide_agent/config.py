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
def get_ppt_writer_agent_config() -> dict[str, str | None]:
    """
    获取 PPT Writer 模型配置（动态读取环境变量）。

    为什么用函数而不是 import-time 常量：
    - 设置页保存后会通过 /admin/reload 热加载环境变量；
    - 旧的模块常量不会自动更新，导致模型仍使用旧配置；
    - 这里每次调用都从 os.environ 读取，确保新配置生效。
    """
    return {
        # 使用新的环境变量命名：PPT_WRITER_TYPE / PPT_WRITER_BASE_URL / PPT_WRITER_API_KEY
        # 默认为 openai 协议（通过 BASE_URL + API_KEY 区分厂商）
        # 允许 PPT_* 留空（settings 页选择“复用 Outline”） -> 回退到 OUTLINE_*
        "provider": _pick("PPT_WRITER_TYPE", "OUTLINE_TYPE", default="openai"),
        "model": _pick("PPT_WRITER_MODEL", "OUTLINE_MODEL", default="qwen-turbo-latest"),
        "api_key": _pick_optional("PPT_WRITER_API_KEY", "OUTLINE_API_KEY"),
        "base_url": _pick_optional("PPT_WRITER_BASE_URL", "OUTLINE_BASE_URL"),
    }

# 检查每一页的PPT是否符合要求，不符合要求的会被重写
def get_ppt_checker_agent_config() -> dict[str, str | None]:
    """
    获取 PPT Checker 模型配置（动态读取环境变量）。

    目前 CheckerAgent 不走大模型，但保留配置读取，方便未来扩展。
    """
    return {
        # 允许 PPT_* 留空（settings 页选择“复用 Outline”） -> 回退到 OUTLINE_*
        "provider": _pick("PPT_CHECKER_TYPE", "OUTLINE_TYPE", default="openai"),
        "model": _pick("PPT_CHECKER_MODEL", "OUTLINE_MODEL", default="qwen-turbo-latest"),
        "api_key": _pick_optional("PPT_CHECKER_API_KEY", "OUTLINE_API_KEY"),
        "base_url": _pick_optional("PPT_CHECKER_BASE_URL", "OUTLINE_BASE_URL"),
    }

