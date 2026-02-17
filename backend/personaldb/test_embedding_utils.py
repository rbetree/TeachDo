from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _DummyCollectionInfo:
    name: str


class _DummyCollection:
    def __init__(self, *, ids, metadatas, documents):
        self._ids = ids
        self._metadatas = metadatas
        self._documents = documents

    def get(self, *, where=None):
        if not where:
            return {"ids": self._ids, "metadatas": self._metadatas, "documents": self._documents}

        file_id = where.get("file_id") if isinstance(where, dict) else None
        if file_id is None:
            return {"ids": [], "metadatas": [], "documents": []}

        picked = []
        for idx, meta in enumerate(self._metadatas):
            if isinstance(meta, dict) and meta.get("file_id") == file_id:
                picked.append(idx)
        return {
            "ids": [self._ids[i] for i in picked],
            "metadatas": [self._metadatas[i] for i in picked],
            "documents": [self._documents[i] for i in picked],
        }


class _DummyClient:
    def __init__(self, *, collection_name: str, ids, metadatas, documents):
        self._collection_name = collection_name
        self._collection = _DummyCollection(ids=ids, metadatas=metadatas, documents=documents)

    def list_collections(self):
        return [_DummyCollectionInfo(name=self._collection_name)]

    def get_collection(self, name: str):
        assert name == self._collection_name
        return self._collection


def _build_chroma_for_test(*, user_id: str, ids=None, metadatas, documents):
    """
    构造一个绕过真实 Chroma 初始化的 ChromaDB 实例：
    - 仅用于单测 list_files_by_user 的聚合逻辑
    - 不触发向量化/落盘/外部依赖
    """
    from backend.personaldb.embedding_utils import ChromaDB

    inst = ChromaDB.__new__(ChromaDB)  # 绕过 __init__
    resolved_ids = ids if ids is not None else [str(i) for i in range(len(documents))]
    inst.client = _DummyClient(
        collection_name=f"user_{user_id}",
        ids=resolved_ids,
        metadatas=metadatas,
        documents=documents,
    )
    return inst


def test_list_files_by_user_returns_file_size_when_present():
    chroma = _build_chroma_for_test(
        user_id="course-1",
        ids=["f1_0", "f1_1"],
        metadatas=[
            {"file_id": "f1", "user_id": "course-1", "file_name": "a.txt", "file_type": "txt", "folder_id": 0, "url": "", "file_size": 10},
            # 同一个文件的多个 chunk，file_size 应保持一致/取最大
            {"file_id": "f1", "user_id": "course-1", "file_name": "a.txt", "file_type": "txt", "folder_id": 0, "url": "", "file_size": 10},
        ],
        documents=["hello", "world"],
    )

    files = chroma.list_files_by_user("course-1")
    assert len(files) == 1
    assert files[0]["file_id"] == "f1"
    assert files[0]["file_size"] == 10


def test_list_files_by_user_falls_back_to_document_bytes_when_missing_file_size():
    chroma = _build_chroma_for_test(
        user_id="course-1",
        ids=["f2_0", "f2_1", "f3_0"],
        metadatas=[
            {"file_id": "f2", "user_id": "course-1", "file_name": "b.md", "file_type": "md", "folder_id": 1, "url": ""},
            {"file_id": "f2", "user_id": "course-1", "file_name": "b.md", "file_type": "md", "folder_id": 1, "url": ""},
            # 其他用户的数据应被忽略
            {"file_id": "f3", "user_id": "course-2", "file_name": "c.md", "file_type": "md", "folder_id": 1, "url": ""},
        ],
        documents=["abc", "你好", "should-not-count"],
    )

    files = {it["file_id"]: it for it in chroma.list_files_by_user("course-1")}
    assert "f2" in files
    assert "f3" not in files

    # "abc" -> 3 bytes, "你好" -> 6 bytes (UTF-8)
    assert files["f2"]["file_size"] == 9


def test_get_file_content_sorts_chunks_and_dedups_overlap():
    chroma = _build_chroma_for_test(
        user_id="course-1",
        # 模拟 Chroma get(where=...) 返回顺序不稳定
        ids=["f1_1", "f1_0"],
        metadatas=[
            {"file_id": "f1", "user_id": "course-1", "file_name": "a.md", "file_type": "md", "folder_id": 0, "url": "", "file_size": 123},
            {"file_id": "f1", "user_id": "course-1", "file_name": "a.md", "file_type": "md", "folder_id": 0, "url": "", "file_size": 123},
        ],
        documents=[
            "world!!!",
            "hello world",
        ],
    )

    result = chroma.get_file_content(user_id="course-1", file_id="f1")
    assert result is not None
    assert result["file_id"] == "f1"
    assert result["file_name"] == "a.md"
    assert result["file_type"] == "md"
    assert result["file_size"] == 123
    assert result["content"] == "hello world!!!"


def test_get_file_content_falls_back_to_utf8_length_when_missing_file_size():
    chroma = _build_chroma_for_test(
        user_id="course-1",
        ids=["f2_0", "f2_1"],
        metadatas=[
            {"file_id": "f2", "user_id": "course-1", "file_name": "b.md", "file_type": "md", "folder_id": 1, "url": ""},
            {"file_id": "f2", "user_id": "course-1", "file_name": "b.md", "file_type": "md", "folder_id": 1, "url": ""},
        ],
        documents=["你好", "世界"],
    )

    result = chroma.get_file_content(user_id="course-1", file_id="f2")
    assert result is not None
    assert result["file_size"] == len("你好世界".encode("utf-8"))
