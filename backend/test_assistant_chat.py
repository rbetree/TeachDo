from __future__ import annotations

from typing import Any, Dict

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


@pytest.fixture()
def main_api_client():
    from backend.main_api.main import app

    return TestClient(app)


@pytest.fixture()
def personaldb_stub() -> Dict[str, Any]:
    """
    personaldb stub：仅提供 /healthz 与 /search，供 main_api 的助教 RAG 单测使用。
    """
    app = FastAPI()
    state: Dict[str, Any] = {"search_payload": None}

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.post("/search")
    async def search(request: Request):
        payload = await request.json()
        state["search_payload"] = payload
        return {
            "documents": [["KB chunk 1", "KB chunk 2"]],
            "metadatas": [
                [
                    {
                        "file_id": "upload:test:fid0",
                        "file_name": "a.txt",
                        "folder_id": 0,
                    },
                    {
                        "file_id": "gen:test:fid1",
                        "file_name": "b.md",
                        "folder_id": 1,
                    },
                ]
            ],
            "distances": [[0.1, 0.2]],
        }

    return {"app": app, "state": state}


def test_assistant_chat_enriches_with_kb_and_material(
    main_api_client, personaldb_stub, monkeypatch
):
    monkeypatch.setenv("PERSONAL_DB", "http://personaldb.test")

    # 助教默认复用 OUTLINE_* 配置（本用例仅验证配置读取不报错；真实 LLM 调用会被 mock）
    monkeypatch.setenv("OUTLINE_TYPE", "openai")
    monkeypatch.setenv("OUTLINE_MODEL", "mock-model")
    monkeypatch.setenv("OUTLINE_API_KEY", "sk-test")
    monkeypatch.setenv("OUTLINE_BASE_URL", "http://llm.test/v1")

    import backend.main_api.main as main_api

    stub_app = personaldb_stub["app"]
    stub_state = personaldb_stub["state"]

    real_async_client = httpx.AsyncClient

    def _async_client_factory(*_args, **kwargs):
        timeout = kwargs.get("timeout")
        return real_async_client(
            transport=httpx.ASGITransport(app=stub_app),
            base_url="http://personaldb.test",
            timeout=timeout,
            trust_env=False,
        )

    monkeypatch.setattr(main_api.httpx, "AsyncClient", _async_client_factory)

    seen: Dict[str, Any] = {}

    async def _fake_iter_assistant_text_chunks(*, model, api_key, base_url, messages, temperature=0.6):
        seen["model"] = model
        seen["api_key"] = api_key
        seen["base_url"] = base_url
        seen["messages"] = messages
        yield "Hello"

    monkeypatch.setattr(main_api, "iter_assistant_text_chunks", _fake_iter_assistant_text_chunks)

    payload = {
        "messages": [{"role": "user", "content": "请根据知识库解释三角形内角和定理"}],
        "user_id": "default_user",
        "kb_file_ids": ["upload:test:fid0", "gen:test:fid1"],
        "material": {
            "title": "三角形的基本性质",
            "subject": "数学",
            "description": "八年级上册",
            "objectives": "掌握三角形内角和定理并能解决基础题。",
        },
        "language": "zh",
    }

    with main_api_client.stream("POST", "/tools/assistant_chat", json=payload) as resp:
        assert resp.status_code == 200
        body = b"".join(resp.iter_bytes()).decode("utf-8", errors="ignore")

    assert "[DONE]" in body
    assert "Hello" in body

    assert stub_state["search_payload"]["userId"] == "default_user"
    assert stub_state["search_payload"]["query"] == "请根据知识库解释三角形内角和定理"
    assert stub_state["search_payload"]["fileIds"] == ["upload:test:fid0", "gen:test:fid1"]

    system_prompt = (seen["messages"][0] or {}).get("content", "")
    assert "当前教学资料" in system_prompt
    assert "三角形的基本性质" in system_prompt
    assert "知识库检索片段" in system_prompt
    assert "KB chunk 1" in system_prompt

