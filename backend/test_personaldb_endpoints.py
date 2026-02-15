from __future__ import annotations

from typing import Any, Dict

from fastapi.testclient import TestClient


def test_personaldb_files_endpoints_accept_string_ids(monkeypatch):
    import backend.personaldb.main as personaldb

    class _DummyEmbedder:
        pass

    class _DummyChroma:
        def __init__(self, _embedder):
            pass

        def list_files_by_user(self, user_id: str):
            assert user_id == "course-1"
            return [
                {
                    "file_id": "upload:course-1:001",
                    "file_name": "a.txt",
                    "file_type": "txt",
                    "url": "",
                    "folder_id": 0,
                    "user_id": "course-1",
                }
            ]

        def delete_file_vectors(self, user_id: str, file_id: str):
            assert user_id == "course-1"
            assert file_id == "upload:course-1:001"
            return "success"

    monkeypatch.setattr(personaldb.embedding_utils, "EmbeddingModel", _DummyEmbedder)
    monkeypatch.setattr(personaldb.embedding_utils, "ChromaDB", _DummyChroma)

    client = TestClient(personaldb.app)

    resp = client.get("/files/course-1")
    assert resp.status_code == 200
    assert resp.json()[0]["user_id"] == "course-1"
    assert resp.json()[0]["file_id"] == "upload:course-1:001"

    resp = client.delete("/files/course-1/upload:course-1:001")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_personaldb_vectorize_text_endpoint_accepts_string_ids(monkeypatch):
    import backend.personaldb.main as personaldb

    called: Dict[str, Any] = {}

    def _fake_process_text_content(
        *,
        file_name: str,
        text: str,
        id: str,
        user_id: str = "0",
        file_type: str | None = None,
        folder_id: int = 0,
        url: str = "",
    ):
        called.update(
            {
                "file_name": file_name,
                "text": text,
                "id": id,
                "user_id": user_id,
                "file_type": file_type,
                "folder_id": folder_id,
                "url": url,
            }
        )
        return {"id": id, "file_name": file_name, "userId": user_id, "folderId": folder_id}

    monkeypatch.setattr(personaldb, "process_text_content", _fake_process_text_content)

    client = TestClient(personaldb.app)
    resp = client.post(
        "/vectorize/text",
        json={
            "content": "hello",
            "fileId": "gen:course-1:unit-1:outline",
            "fileName": "outline.md",
            "userId": "course-1",
            "fileType": "md",
            "folderId": 1,
            "url": "",
        },
    )
    assert resp.status_code == 200
    assert called["user_id"] == "course-1"
    assert called["id"] == "gen:course-1:unit-1:outline"
    assert called["folder_id"] == 1

