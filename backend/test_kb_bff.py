from __future__ import annotations

from typing import Any, Dict

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient


def _assert_kb_error(resp, *, status_code: int, code: str) -> None:
    assert resp.status_code == status_code
    body = resp.json()
    assert body["ok"] is False
    assert body["error"]["code"] == code


@pytest.fixture()
def main_api_client():
    from backend.main_api.main import app

    return TestClient(app)


@pytest.fixture()
def personaldb_stub() -> Dict[str, Any]:
    """
    personaldb stub：仅提供 main_api KB BFF 所需的最小接口集合。
    - 不做真实向量化/落盘，避免单测依赖外部模型与耗时计算。
    """
    app = FastAPI()
    state: Dict[str, Any] = {
        "vectorize_payload": None,
        "upload_called": 0,
        "deleted": [],
    }

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.post("/upload/")
    async def upload(_request: Request):
        state["upload_called"] += 1
        return {"ok": True, "fileType": "txt"}

    @app.get("/files/{user_id}")
    async def files(user_id: str):
        return [
            {
                "user_id": user_id,
                "file_id": "upload:test:fid0",
                "file_name": "a.txt",
                "file_type": "txt",
                "file_size": 5,
                "folder_id": 0,
                "created_at": 1700000000000,
                "source_type": "upload",
            },
            # 兼容 camelCase 字段
            {
                "userId": user_id,
                "fileId": "gen:test:fid1",
                "fileName": "b.md",
                "fileType": "md",
                "fileSize": 12,
                "folderId": 1,
                "createdAt": 1700000001000,
                "sourceType": "material",
                "sourceMaterialId": "mat-1",
                "sourceMaterialTitle": "示例教学资料",
            },
            # 无效项应被 main_api 侧跳过
            "invalid",
        ]

    @app.get("/files/{user_id}/{file_id}/content")
    async def file_content(user_id: str, file_id: str):
        # 这里的 content 用于 main_api 的 /kb/.../export 下载
        return {
            "user_id": user_id,
            "file_id": file_id,
            "file_name": "导出示例.md",
            "file_type": "md",
            "file_size": 12,
            "content": "# Hello\n\nworld",
        }

    @app.post("/vectorize/text")
    async def vectorize_text(request: Request):
        payload = await request.json()
        state["vectorize_payload"] = payload
        if not isinstance(payload.get("userId"), str) or not isinstance(payload.get("fileId"), str):
            raise HTTPException(status_code=400, detail="userId/fileId 必须为 string")
        return {"ok": True}

    @app.delete("/files/{user_id}/{file_id}")
    async def delete_file(user_id: str, file_id: str):
        state["deleted"].append((user_id, file_id))
        return {"ok": True}

    return {"app": app, "state": state}


def test_kb_bff_returns_not_configured_when_env_missing(main_api_client, monkeypatch):
    monkeypatch.delenv("PERSONAL_DB", raising=False)

    resp = main_api_client.get("/kb/files/course-1")
    _assert_kb_error(resp, status_code=500, code="KB_NOT_CONFIGURED")

    resp = main_api_client.post(
        "/kb/upload",
        data={"user_id": "course-1", "folder_id": "0"},
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    _assert_kb_error(resp, status_code=500, code="KB_NOT_CONFIGURED")

    resp = main_api_client.post(
        "/kb/vectorize/text",
        json={
            "user_id": "course-1",
            "file_id": "gen:course-1:unit-1:outline",
            "file_name": "outline.md",
            "content": "# outline",
            "file_type": "md",
            "folder_id": 1,
        },
    )
    _assert_kb_error(resp, status_code=500, code="KB_NOT_CONFIGURED")

    resp = main_api_client.delete("/kb/files/course-1/upload:test:fid0")
    _assert_kb_error(resp, status_code=500, code="KB_NOT_CONFIGURED")


def test_kb_bff_happy_path_with_personaldb_stub(main_api_client, personaldb_stub, monkeypatch):
    monkeypatch.setenv("PERSONAL_DB", "http://personaldb.test")
    stub_app = personaldb_stub["app"]
    stub_state = personaldb_stub["state"]

    import backend.main_api.main as main_api

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

    # 1) upload
    resp = main_api_client.post(
        "/kb/upload",
        data={
            "user_id": "course-1",
            "folder_id": "0",
            "file_id": "upload:course-1:fixed:001",
            "file_type": "txt",
        },
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["user_id"] == "course-1"
    assert body["data"]["file_id"] == "upload:course-1:fixed:001"
    assert body["data"]["folder_id"] == 0
    assert body["data"]["file_size"] == 5
    assert stub_state["upload_called"] == 1

    # 2) list（含 folder_id 过滤 + 字段归一化）
    resp = main_api_client.get("/kb/files/course-1")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert {it["file_id"] for it in items} == {"upload:test:fid0", "gen:test:fid1"}
    by_id = {it["file_id"]: it for it in items}
    assert by_id["upload:test:fid0"]["file_size"] == 5
    assert by_id["gen:test:fid1"]["file_size"] == 12
    assert by_id["upload:test:fid0"]["created_at"] == 1700000000000
    assert by_id["upload:test:fid0"]["source_type"] == "upload"
    assert by_id["gen:test:fid1"]["created_at"] == 1700000001000
    assert by_id["gen:test:fid1"]["source_type"] == "material"
    assert by_id["gen:test:fid1"]["source_material_id"] == "mat-1"
    assert by_id["gen:test:fid1"]["source_material_title"] == "示例教学资料"

    resp = main_api_client.get("/kb/files/course-1?folder_id=0")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert [it["file_id"] for it in items] == ["upload:test:fid0"]
    assert items[0]["file_size"] == 5
    assert items[0]["source_type"] == "upload"

    resp = main_api_client.get("/kb/files/course-1?folder_id=1")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert [it["file_id"] for it in items] == ["gen:test:fid1"]
    assert items[0]["file_size"] == 12
    assert items[0]["source_type"] == "material"

    # 3) vectorize/text
    resp = main_api_client.post(
        "/kb/vectorize/text",
        json={
            "user_id": "course-1",
            "file_id": "gen:course-1:unit-1:outline",
            "file_name": "outline.md",
            "content": "# outline",
            "file_type": "md",
            "folder_id": 1,
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "data": True}
    assert stub_state["vectorize_payload"]["userId"] == "course-1"
    assert stub_state["vectorize_payload"]["fileId"] == "gen:course-1:unit-1:outline"

    resp = main_api_client.post(
        "/kb/vectorize/text",
        json={
            "user_id": "course-1",
            "file_id": "gen:empty",
            "file_name": "outline.md",
            "content": "   ",
            "file_type": "md",
            "folder_id": 1,
        },
    )
    _assert_kb_error(resp, status_code=400, code="KB_CONTENT_REQUIRED")

    # 4) delete
    resp = main_api_client.delete("/kb/files/course-1/upload:test:fid0")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "data": True}
    assert ("course-1", "upload:test:fid0") in stub_state["deleted"]

    # 5) export（附件下载）
    resp = main_api_client.get("/kb/files/course-1/upload:test:fid0/export")
    assert resp.status_code == 200
    assert resp.text == "# Hello\n\nworld"
    disposition = resp.headers.get("content-disposition") or ""
    assert "attachment" in disposition.lower()
    assert "utf-8" in disposition.lower()


def test_tools_aippt_disables_kb_when_personaldb_not_configured(main_api_client, monkeypatch):
    monkeypatch.delenv("PERSONAL_DB", raising=False)

    import backend.main_api.main as main_api

    seen: Dict[str, Any] = {}

    async def _fake_stream_content_response(
        markdown_content: str,
        language: str,
        generateFromUploadedFile: bool,
        generateFromWebSearch: bool,
        user_id: str,
        kb_folder_ids=None,
        kb_file_ids=None,
    ):
        seen["generateFromUploadedFile"] = generateFromUploadedFile
        seen["kb_folder_ids"] = kb_folder_ids
        seen["kb_file_ids"] = kb_file_ids
        yield b"data: [DONE]\n\n"

    monkeypatch.setattr(main_api, "stream_content_response", _fake_stream_content_response)

    payload = {
        "content": "# TeachDo\n\n## Outline\n- A\n",
        "language": "zh",
        "sessionId": "course-1",
        "generateFromUploadedFile": True,
        "generateFromWebSearch": False,
        "kb_folder_ids": [0, 1],
        "kb_file_ids": ["upload:test:fid0"],
    }
    with main_api_client.stream("POST", "/tools/aippt", json=payload) as resp:
        assert resp.status_code == 200
        _ = b"".join(resp.iter_bytes())

    assert seen["generateFromUploadedFile"] is False
    assert seen["kb_folder_ids"] is None
    assert seen["kb_file_ids"] is None


def test_tools_aippt_disables_kb_when_personaldb_not_ready(main_api_client, monkeypatch):
    monkeypatch.setenv("PERSONAL_DB", "http://personaldb.test")

    import backend.main_api.main as main_api

    async def _fake_is_ready(_url: str) -> bool:
        return False

    seen: Dict[str, Any] = {}

    async def _fake_stream_content_response(
        markdown_content: str,
        language: str,
        generateFromUploadedFile: bool,
        generateFromWebSearch: bool,
        user_id: str,
        kb_folder_ids=None,
        kb_file_ids=None,
    ):
        seen["generateFromUploadedFile"] = generateFromUploadedFile
        seen["kb_folder_ids"] = kb_folder_ids
        seen["kb_file_ids"] = kb_file_ids
        yield b"data: [DONE]\n\n"

    monkeypatch.setattr(main_api, "_is_personaldb_ready", _fake_is_ready)
    monkeypatch.setattr(main_api, "stream_content_response", _fake_stream_content_response)

    payload = {
        "content": "# TeachDo\n\n## Outline\n- A\n",
        "language": "zh",
        "sessionId": "course-1",
        "generateFromUploadedFile": True,
        "generateFromWebSearch": False,
        "kb_folder_ids": [0],
        "kb_file_ids": ["upload:test:fid0"],
    }
    with main_api_client.stream("POST", "/tools/aippt", json=payload) as resp:
        assert resp.status_code == 200
        _ = b"".join(resp.iter_bytes())

    assert seen["generateFromUploadedFile"] is False
    assert seen["kb_folder_ids"] is None
    assert seen["kb_file_ids"] is None


def test_tools_aippt_keeps_kb_when_personaldb_ready(main_api_client, monkeypatch):
    monkeypatch.setenv("PERSONAL_DB", "http://personaldb.test")

    import backend.main_api.main as main_api

    async def _fake_is_ready(_url: str) -> bool:
        return True

    seen: Dict[str, Any] = {}

    async def _fake_stream_content_response(
        markdown_content: str,
        language: str,
        generateFromUploadedFile: bool,
        generateFromWebSearch: bool,
        user_id: str,
        kb_folder_ids=None,
        kb_file_ids=None,
    ):
        seen["generateFromUploadedFile"] = generateFromUploadedFile
        seen["kb_folder_ids"] = kb_folder_ids
        seen["kb_file_ids"] = kb_file_ids
        yield b"data: [DONE]\n\n"

    monkeypatch.setattr(main_api, "_is_personaldb_ready", _fake_is_ready)
    monkeypatch.setattr(main_api, "stream_content_response", _fake_stream_content_response)

    payload = {
        "content": "# TeachDo\n\n## Outline\n- A\n",
        "language": "zh",
        "sessionId": "course-1",
        "generateFromUploadedFile": True,
        "generateFromWebSearch": False,
        "kb_folder_ids": [0, 1],
        "kb_file_ids": ["upload:test:fid0", "gen:test:slides"],
    }
    with main_api_client.stream("POST", "/tools/aippt", json=payload) as resp:
        assert resp.status_code == 200
        _ = b"".join(resp.iter_bytes())

    assert seen["generateFromUploadedFile"] is True
    assert seen["kb_folder_ids"] == [0, 1]
    assert seen["kb_file_ids"] == ["upload:test:fid0", "gen:test:slides"]
