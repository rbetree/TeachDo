#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/18 14:44
# @File  : create_model.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :
import os
from typing import Optional

import litellm
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv

litellm._turn_on_debug()

load_dotenv()


def _ensure_openai_prefix(model: str) -> str:
    """统一为 OpenAI 兼容协议增加 openai/ 前缀，保持与原实现一致。"""
    if not model.startswith("openai/"):
        return "openai/" + model
    return model


def create_model(model: str, provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
    """
    创建模型，返回字符串或者 LiteLlm。

    仅保留“协议级别”的 provider：
    - google  : Gemini 协议（依赖 GOOGLE_API_KEY）
    - claude  : Anthropic 协议（依赖 CLAUDE_API_KEY）
    - openai  : OpenAI 兼容协议（依赖 OPENAI_API_KEY 或调用方传入的 api_key），
                base_url 可指向 OpenAI / DeepSeek / 阿里 DashScope / 豆包 / vLLM / Xinference 等兼容服务。
    其他厂商一律通过 base_url + api_key 表达，不再作为 provider 值出现。
    """
    provider = (provider or "").strip().lower()
    print(f"创建模型, provider: {provider}, 模型是: {model}")

    if provider == "google":
        # google 的模型在 ADK 里直接用名称；底层 SDK 仍然依赖 GOOGLE_API_KEY。
        key = api_key or os.environ.get("GOOGLE_API_KEY")
        assert key, "GOOGLE_API_KEY is not set，或未通过 OUTLINE_API_KEY 提供"
        if api_key and not os.environ.get("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = api_key
        return model

    if provider == "claude":
        key = api_key or os.environ.get("CLAUDE_API_KEY")
        assert key, "CLAUDE_API_KEY is not set，或未通过 OUTLINE_API_KEY / PPT_WRITER_API_KEY 提供"
        if not model.startswith("anthropic/"):
            model = "anthropic/" + model
        return LiteLlm(
            model=model,
            api_key=key,
            num_tries=3,
        )

    if provider == "openai":
        key = api_key or os.environ.get("OPENAI_API_KEY")
        assert key, "OPENAI_API_KEY is not set，或未通过统一 API_KEY 提供"
        model = _ensure_openai_prefix(model)
        api_base = base_url or os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
        return LiteLlm(model=model, api_key=key, api_base=api_base, num_retries=3)

    raise ValueError(f"Unsupported provider: {provider}")
