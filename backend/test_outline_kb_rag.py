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
    personaldb stub：提供 /healthz、/search、/files/{user_id}/{file_id}/content，供 main_api 的大纲 KB 增强单测使用。
    """
    app = FastAPI()
    state: Dict[str, Any] = {"search_payload": None, "content_calls": []}

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.post("/search")
    async def search(request: Request):
        payload = await request.json()
        state["search_payload"] = payload
        return {
            "documents": [["KB chunk 1"]],
            "metadatas": [
                [
                    {
                        "file_id": "upload:test:fid0",
                        "file_name": "a.txt",
                        "folder_id": 0,
                    },
                ]
            ],
            "distances": [[0.1]],
        }

    @app.get("/files/{user_id}/{file_id}/content")
    async def file_content(user_id: str, file_id: str):
        state["content_calls"].append({"user_id": user_id, "file_id": file_id})
        return {
            "user_id": user_id,
            "file_id": file_id,
            "file_name": "outline.md",
            "file_type": "md",
            "file_size": 10,
            "content": "FULL TEXT FROM gen: OUTPUT",
        }

    return {"app": app, "state": state}


def test_outline_unified_enriches_prompt_with_kb_search_results(
    main_api_client, personaldb_stub, monkeypatch
):
    monkeypatch.setenv("PERSONAL_DB", "http://personaldb.test")

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

    async def _fake_stream_outline_sse(prompt: str, language: str = "chinese"):
        seen["prompt"] = prompt
        seen["language"] = language
        yield b"data: [DONE]\n\n"

    monkeypatch.setattr(main_api, "stream_outline_sse", _fake_stream_outline_sse)

    data = {
        "content": "主题：细胞结构与功能",
        "language": "chinese",
        "user_id": "default_user",
        "kb_file_ids": ["upload:test:fid0", "gen:test:fid1"],
    }

    with main_api_client.stream("POST", "/tools/aippt_outline_unified", data=data) as resp:
        assert resp.status_code == 200
        _ = b"".join(resp.iter_bytes())

    assert stub_state["search_payload"]["userId"] == "default_user"
    assert stub_state["search_payload"]["query"] == "主题：细胞结构与功能"
    assert stub_state["search_payload"]["fileIds"] == ["upload:test:fid0"]

    assert stub_state["content_calls"] == [{"user_id": "default_user", "file_id": "gen:test:fid1"}]

    prompt = seen["prompt"]
    assert "主题：细胞结构与功能" in prompt
    assert "课程产出（全文，不经检索）" in prompt
    assert "FULL TEXT FROM gen: OUTPUT" in prompt
    assert "参考资料检索片段（RAG）" in prompt
    assert "KB chunk 1" in prompt
    assert "file_id=upload:test:fid0" in prompt


def test_outline_unified_skips_kb_when_personaldb_missing(main_api_client, monkeypatch):
    monkeypatch.delenv("PERSONAL_DB", raising=False)

    import backend.main_api.main as main_api

    seen: Dict[str, Any] = {}

    async def _fake_stream_outline_sse(prompt: str, language: str = "chinese"):
        seen["prompt"] = prompt
        yield b"data: [DONE]\n\n"

    monkeypatch.setattr(main_api, "stream_outline_sse", _fake_stream_outline_sse)

    data = {
        "content": "主题：电动汽车发展",
        "language": "chinese",
        "user_id": "default_user",
        "kb_file_ids": ["upload:test:fid0"],
    }

    with main_api_client.stream("POST", "/tools/aippt_outline_unified", data=data) as resp:
        assert resp.status_code == 200
        _ = b"".join(resp.iter_bytes())

    prompt = seen["prompt"]
    assert "主题：电动汽车发展" in prompt
    assert "参考资料检索片段（RAG）" not in prompt
    assert "课程产出（全文，不经检索）" not in prompt
