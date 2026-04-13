from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from backend.common.url_security import UrlAccessError, validate_public_http_url


def test_validate_public_http_url_rejects_local_private_targets():
    with pytest.raises(UrlAccessError) as exc_info:
        validate_public_http_url("http://127.0.0.1:8000/demo.png")
    assert exc_info.value.status_code == 403

    with pytest.raises(UrlAccessError) as exc_info:
        validate_public_http_url("https://localhost/demo.png")
    assert exc_info.value.status_code == 403


def test_internal_agent_urls_use_access_host(monkeypatch: pytest.MonkeyPatch):
    import backend.main_api.main as main_api

    monkeypatch.delenv("OUTLINE_API", raising=False)
    monkeypatch.delenv("CONTENT_API", raising=False)
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("OUTLINE_API_PORT", "10001")
    monkeypatch.setenv("CONTENT_API_PORT", "10011")

    assert main_api._get_outline_api() == "http://127.0.0.1:10001"
    assert main_api._get_content_api() == "http://127.0.0.1:10011"


def test_proxy_rejects_private_target():
    from backend.main_api.main import app

    client = TestClient(app)
    resp = client.get("/proxy", params={"url": "http://127.0.0.1:8000/demo.png"})
    assert resp.status_code == 403
    assert "内网" in resp.json()["detail"]


def test_proxy_streams_public_resource(monkeypatch: pytest.MonkeyPatch):
    import backend.main_api.main as main_api

    stub_app = FastAPI()

    @stub_app.get("/asset")
    async def asset():
        return Response(
            content=b"proxy-ok",
            media_type="image/png",
            headers={"ETag": "proxy-etag"},
        )

    real_async_client = httpx.AsyncClient

    def _async_client_factory(*_args, **kwargs):
        return real_async_client(
            transport=httpx.ASGITransport(app=stub_app),
            base_url="http://assets.example",
            timeout=kwargs.get("timeout"),
            follow_redirects=kwargs.get("follow_redirects", False),
        )

    monkeypatch.setattr(main_api.httpx, "AsyncClient", _async_client_factory)
    monkeypatch.setattr(main_api, "validate_public_http_url", lambda url: url)

    client = TestClient(main_api.app)
    resp = client.get("/proxy", params={"url": "http://assets.example/asset"})
    assert resp.status_code == 200
    assert resp.content == b"proxy-ok"
    assert resp.headers["content-type"].startswith("image/png")
    assert resp.headers["etag"] == "proxy-etag"


def test_outline_unified_accepts_file_without_content(monkeypatch: pytest.MonkeyPatch):
    import backend.main_api.main as main_api

    monkeypatch.setenv("PERSONAL_DB", "http://personaldb.test")

    stub_app = FastAPI()

    @stub_app.post("/upload/")
    async def upload():
        return {"markdown_content": "# 文件解析结果\n- 要点"}

    real_async_client = httpx.AsyncClient

    def _async_client_factory(*_args, **kwargs):
        return real_async_client(
            transport=httpx.ASGITransport(app=stub_app),
            base_url="http://personaldb.test",
            timeout=kwargs.get("timeout"),
            follow_redirects=kwargs.get("follow_redirects", False),
        )

    captured: Dict[str, Any] = {}

    async def _fake_stream_outline_sse(prompt: str, language: str = "chinese", **_kwargs):
        captured["prompt"] = prompt
        captured["language"] = language
        yield b"data: [DONE]\n\n"

    monkeypatch.setattr(main_api.httpx, "AsyncClient", _async_client_factory)
    monkeypatch.setattr(main_api, "stream_outline_sse", _fake_stream_outline_sse)

    client = TestClient(main_api.app)
    with client.stream(
        "POST",
        "/tools/aippt_outline_unified",
        data={"language": "chinese", "user_id": "u-test"},
        files={"file": ("outline.md", b"hello", "text/plain")},
    ) as resp:
        assert resp.status_code == 200
        _ = b"".join(resp.iter_bytes())

    assert "参考文档内容（来自你上传的文件）" in captured["prompt"]
    assert "# 文件解析结果" in captured["prompt"]
    assert captured["language"] == "chinese"


def test_personaldb_upload_rejects_private_url():
    from backend.personaldb.main import app

    client = TestClient(app)
    resp = client.post(
        "/upload/",
        data={
            "userId": "u-test",
            "fileId": "f-test",
            "url": "http://127.0.0.1:8000/demo.txt",
        },
    )
    assert resp.status_code == 403
    assert "内网" in resp.json()["detail"]


def test_personaldb_upload_cleans_temp_file(monkeypatch: pytest.MonkeyPatch):
    import backend.personaldb.main as personaldb_main

    seen: Dict[str, Any] = {}

    def _fake_process_and_vectorize_local_file(*, file_name: str, temp_file_path: str, **_kwargs):
        seen["file_name"] = file_name
        seen["temp_file_path"] = temp_file_path
        seen["exists_during_call"] = os.path.exists(temp_file_path)
        return {"ok": True, "markdown_content": "# ok"}

    monkeypatch.setattr(personaldb_main, "process_and_vectorize_local_file", _fake_process_and_vectorize_local_file)

    client = TestClient(personaldb_main.app)
    resp = client.post(
        "/upload/",
        data={"userId": "u-test", "fileId": "f-test"},
        files={"file": ("../dangerous.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 200
    assert seen["file_name"] == "dangerous.txt"
    assert seen["exists_during_call"] is True
    assert Path(seen["temp_file_path"]).parent == Path(personaldb_main.TEMP_DIR)
    assert ".." not in Path(seen["temp_file_path"]).name
    assert not os.path.exists(seen["temp_file_path"])
