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


def test_personaldb_file_content_endpoint_exports_merged_text(monkeypatch):
    import backend.personaldb.main as personaldb

    class _DummyChroma:
        def __init__(self, embedder=None, db_dir=None):  # noqa: ARG002
            pass

        def get_file_content(self, *, user_id: str, file_id: str):
            assert user_id == "course-1"
            assert file_id == "upload:course-1:001"
            return {
                "user_id": user_id,
                "file_id": file_id,
                "file_name": "a.md",
                "file_type": "md",
                "file_size": 12,
                "content": "# Hello\n\nworld",
            }

    monkeypatch.setattr(personaldb.embedding_utils, "ChromaDB", _DummyChroma)

    client = TestClient(personaldb.app)
    resp = client.get("/files/course-1/upload:course-1:001/content")
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_id"] == "upload:course-1:001"
    assert body["content"] == "# Hello\n\nworld"


def test_personaldb_search_endpoint_accepts_file_ids(monkeypatch):
    import backend.personaldb.main as personaldb

    class _DummyEmbedder:
        pass

    class _DummyChroma:
        def __init__(self, _embedder):
            pass

        def query2collection(self, collection, query_documents, keyword="", topk=3, file_ids=None):  # noqa: ARG002
            assert collection == "user_default_user"
            assert query_documents == ["hello"]
            assert keyword == ""
            assert topk == 3
            assert file_ids == ["upload:test:001", "gen:test:slides"]
            return {
                "documents": [["doc-a"]],
                "metadatas": [[{"file_id": "upload:test:001"}]],
                "distances": [[0.01]],
            }

    monkeypatch.setattr(personaldb.embedding_utils, "EmbeddingModel", _DummyEmbedder)
    monkeypatch.setattr(personaldb.embedding_utils, "ChromaDB", _DummyChroma)

    client = TestClient(personaldb.app)
    resp = client.post(
        "/search",
        json={
            "userId": "default_user",
            "query": "hello",
            "keyword": "",
            "topk": 3,
            "fileIds": ["upload:test:001", "gen:test:slides"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["documents"][0][0] == "doc-a"
    assert body["metadatas"][0][0]["file_id"] == "upload:test:001"


def test_personaldb_chromadb_query2collection_uses_where_in(monkeypatch, tmp_path):
    from backend.personaldb import embedding_utils

    class _DummyEmbedder:
        def do_embedding(self, texts):  # noqa: ARG002
            return {"data": [{"embedding": [0.0, 0.0, 0.0]}]}

    seen = {}

    class _DummyCollection:
        def query(self, **kwargs):
            seen["where"] = kwargs.get("where")
            seen["where_document"] = kwargs.get("where_document")
            return {"documents": [["doc"]], "metadatas": [[{"file_id": "f1"}]], "distances": [[0.1]]}

    class _DummyClient:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            pass

        def get_or_create_collection(self, _name, metadata=None):  # noqa: ARG002
            return _DummyCollection()

    monkeypatch.setattr(embedding_utils.chromadb, "PersistentClient", _DummyClient)

    chroma = embedding_utils.ChromaDB(_DummyEmbedder(), db_dir=tmp_path)
    _ = chroma.query2collection(
        collection="user_default_user",
        query_documents=["q"],
        keyword="",
        topk=3,
        file_ids=["f1", "f2"],
    )

    assert seen["where"] == {"file_id": {"$in": ["f1", "f2"]}}
    assert seen["where_document"] is None
