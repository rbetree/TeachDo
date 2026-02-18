#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2023/7/5 10:44
# @File  : embedding_api.py
# @Author:
# @Desc  : 对于给定的内容进行Embedding

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import time
import copy
import json
import logging
import requests
import numpy as np
import pickle
import hashlib
from functools import wraps
import string
import chromadb  #pip install chromadb
from chromadb.config import Settings
from openai import OpenAI
from dotenv import dotenv_values

try:
    # 兼容在 `backend/personaldb` 目录下直接运行
    from runtime_paths import find_repo_root, get_cache_dir
except ImportError:  # pragma: no cover - 兼容以包方式导入（用于单元测试等）
    from backend.personaldb.runtime_paths import find_repo_root, get_cache_dir


def _load_env_files() -> None:
    """
    统一环境变量加载优先级（不覆盖系统环境变量）：
    1) 项目根目录 `.env`
    2) 当前服务目录 `.env`（可选覆盖）
    """
    merged: dict[str, str] = {}

    repo_root = find_repo_root(Path(__file__).resolve())
    root_env = repo_root / ".env"
    if root_env.exists():
        merged.update({k: v for k, v in dotenv_values(root_env).items() if v is not None})

    service_env = Path(__file__).resolve().parent / ".env"
    if service_env.exists():
        merged.update({k: v for k, v in dotenv_values(service_env).items() if v is not None})

    for k, v in merged.items():
        if k not in os.environ:
            os.environ[k] = v


_load_env_files()


logger = logging.getLogger(__name__)

def cal_md5(content):
    """
    计算content字符串的md5
    :param content:
    :return:
    """
    # 使用encode
    content = str(content)
    result = hashlib.md5(content.encode())
    # 打印hash
    md5 = result.hexdigest()
    return md5


def cache_decorator(func):
    """
    cache从文件中读取, 当func中存在usecache时，并且为False时，不使用缓存
    Args:
        func ():
    Returns:
    """
    cache_path = str(get_cache_dir("personaldb"))  # cache目录

    @wraps(func)
    def wrapper(*args, **kwargs):
        # 将args和kwargs转换为哈希键， 当装饰类中的函数的时候，args的第一个参数是实例化的类，这会通常导致改变，我们不想检测它是否改变，那么就忽略它
        usecache = kwargs.get("usecache", True)
        if "usecache" in kwargs:
            del kwargs["usecache"]
        if len(args)> 0:
            if isinstance(args[0],(int, float, str, list, tuple, dict)):
                key = str(args) + str(kwargs)
            else:
                # 第1个参数以后的内容
                key = str(args[1:]) + str(kwargs)
        else:
            key = str(args) + str(kwargs)
        # 变成md5字符串
        key_file = os.path.join(cache_path, cal_md5(key) + "_cache.pkl")
        # 如果结果已缓存，则返回缓存的结果
        if os.path.exists(key_file) and usecache:
            # 去掉kwargs中的usecache
            print(f"函数{func.__name__}被调用，缓存被命中，使用已缓存结果，对于参数{key}")
            try:
                with open(key_file, 'rb') as f:
                    result = pickle.load(f)
                    return result
            except Exception as e:
                print(f"函数{func.__name__}被调用，缓存被命中，读取文件:{key_file}失败，错误信息:{e}")
        result = func(*args, **kwargs)
        # 将结果缓存到文件中
        # 如果返回的数据是一个元祖，并且第1个参数是False,说明这个函数报错了，那么就不缓存了，这是我们自己的一个设定
        if isinstance(result, tuple) and result[0] == False:
            print(f"函数{func.__name__}被调用，返回结果为False，对于参数{key}, 不缓存")
        else:
            with open(key_file, 'wb') as f:
                pickle.dump(result, f)
            print(f"函数{func.__name__}被调用，缓存未命中，结果被缓存，对于参数{key}, 写入文件:{key_file}")
        return result

    return wrapper


class ChromaDB(object):
    def __init__(self, embedder, db_dir: str | Path | None = None):
        """
        Args:
            embedder: 实例化后的embedding
            chromadb的相关操作
        """
        # 目前支持的模型,
        self.embedder = embedder
        if db_dir is None:
            db_dir = get_cache_dir("personaldb") / "chromadb"
        db_dir_path = Path(db_dir)
        db_dir_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(db_dir_path), settings=Settings(anonymized_telemetry=False))

    @staticmethod
    def _normalize_timestamp_ms(value: Any) -> int | None:
        """
        归一化时间戳为「毫秒」级整数。

        - 支持 int/float/str
        - 若为秒级（< 1e12），自动乘以 1000
        """
        if value is None:
            return None
        try:
            ts = int(float(value))
        except Exception:
            return None
        if ts <= 0:
            return None
        # 秒级时间戳通常为 10 位；毫秒为 13 位
        if ts < 1_000_000_000_000:
            ts *= 1000
        return ts

    @staticmethod
    def _normalize_source_type(value: Any) -> str | None:
        """
        归一化来源类型。
        - 目前仅支持：upload/material
        """
        if value is None:
            return None
        s = str(value).strip().lower()
        if s in {"upload", "material"}:
            return s
        return None

    @staticmethod
    def _try_parse_material_id_from_gen_file_id(file_id: Any) -> str | None:
        """
        从 file_id 解析 materialId（约定：gen:{user}:{materialId}:{kind}）。
        """
        if not isinstance(file_id, str):
            return None
        if not file_id.startswith("gen:"):
            return None
        parts = file_id.split(":")
        if len(parts) < 4:
            return None
        material_id = parts[2].strip()
        return material_id or None

    def delete_one_collection(self, collection):
        """
        删除1个collection
        Args:
            collection ():
        Returns:
        """
        try:
            self.client.delete_collection(name=collection)
        except Exception as e:
            print(f"删除collection:{collection}失败，错误信息:{e}")
            return "fail"
        return "success"

    def delete_one_document(self, collection, doc_id):
        """
        删除指定集合中的一条数据（根据 ID），并验证是否删除成功。
        Args:
            collection (str): 集合名称。
            doc_id (str): 要删除的文档 ID。
        Returns:
            str: "success" 表示删除成功，"fail" 表示失败。
        """
        try:
            col = self.client.get_or_create_collection(collection)
            # 删除指定 ID 的文档
            col.delete(ids=[doc_id])
            print(f"尝试删除集合 '{collection}' 中的文档 ID '{doc_id}'。")

            # 验证是否删除成功：查询该 ID，如果结果为空，则成功
            check_result = col.get(ids=[doc_id])
            if not check_result['ids']:  # 如果 IDs 列表为空，说明已删除
                print(f"验证成功：集合 '{collection}' 中的文档 ID '{doc_id}' 已删除。")
                return "success"
            else:
                print(f"验证失败：集合 '{collection}' 中的文档 ID '{doc_id}' 仍存在。")
                return "fail"
        except Exception as e:
            print(f"删除集合 '{collection}' 中的文档 ID '{doc_id}' 失败，错误信息: {e}")
            return "fail"



    def insert2collection(self, collection, documents, meta=None):
        """
        Args:
            collection ():
            documents: list[str]
            meta: 插入collection的meta信息, list[]
        Returns:
        """
        col = self.client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})
        vectors_result = self.embedder.do_embedding(documents)
        vectors = vectors_result["data"]
        embeddings = [one["embedding"] for one in vectors]
        col.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=meta,
            ids=[str(i) for i in range(len(documents))]
        )
        return "success"

    def query2collection(self, collection, query_documents, keyword="", topk=3, file_ids: List[str] | None = None):
        """
        查询向量，混合搜索
        Args:
            collection ():
            query_documents (): list[str]
            keyword: 是否同时对documents执行关键字搜索
            file_ids: 限定检索范围，仅从这些 file_id 的向量中检索
        Returns:
        """
        col = self.client.get_or_create_collection(collection)
        vectors_result = self.embedder.do_embedding(texts=query_documents)
        vectors = vectors_result["data"]
        embeddings = [one["embedding"] for one in vectors]

        try:
            resolved_topk = int(topk) if topk is not None else 3
        except Exception:
            resolved_topk = 3
        if resolved_topk <= 0:
            resolved_topk = 3

        resolved_file_ids: list[str] = []
        if isinstance(file_ids, list) and file_ids:
            for x in file_ids:
                s = str(x).strip()
                if s:
                    resolved_file_ids.append(s)

        def _query(*, where: dict | None):
            kwargs = {
                "query_embeddings": embeddings,
                "n_results": resolved_topk,
                "include": ["metadatas", "documents", "distances"],
            }
            if keyword:
                kwargs["where_document"] = {"$contains": keyword}
            if where is not None:
                kwargs["where"] = where
            return col.query(**kwargs)

        if not resolved_file_ids:
            return _query(where=None)

        if len(resolved_file_ids) == 1:
            return _query(where={"file_id": resolved_file_ids[0]})

        # 优先走服务端 where 过滤（更精准）。若 Chroma 不支持 $in，则回退为逐个 file_id 查询并按距离合并。
        try:
            return _query(where={"file_id": {"$in": resolved_file_ids}})
        except Exception:
            results = []
            for fid in resolved_file_ids:
                results.append(_query(where={"file_id": fid}))

            if not results:
                return _query(where=None)

            # 合并：对每个 query（通常只有 1 个）按距离升序取前 topk
            first = results[0] or {}
            row_count = 0
            docs_any = first.get("documents")
            if isinstance(docs_any, list):
                row_count = len(docs_any)

            merged = {"documents": [], "metadatas": [], "distances": []}
            has_ids = any(isinstance(r.get("ids"), list) for r in results)
            if has_ids:
                merged["ids"] = []

            for row_idx in range(row_count):
                candidates = []
                for r in results:
                    docs = r.get("documents") if isinstance(r, dict) else None
                    metas = r.get("metadatas") if isinstance(r, dict) else None
                    dists = r.get("distances") if isinstance(r, dict) else None
                    ids = r.get("ids") if isinstance(r, dict) else None

                    docs_row = docs[row_idx] if isinstance(docs, list) and row_idx < len(docs) and isinstance(docs[row_idx], list) else []
                    metas_row = metas[row_idx] if isinstance(metas, list) and row_idx < len(metas) and isinstance(metas[row_idx], list) else []
                    dists_row = dists[row_idx] if isinstance(dists, list) and row_idx < len(dists) and isinstance(dists[row_idx], list) else []
                    ids_row = ids[row_idx] if isinstance(ids, list) and row_idx < len(ids) and isinstance(ids[row_idx], list) else []

                    for i in range(len(docs_row)):
                        doc = docs_row[i]
                        meta = metas_row[i] if i < len(metas_row) else None
                        dist = dists_row[i] if i < len(dists_row) else None
                        doc_id = ids_row[i] if i < len(ids_row) else None
                        candidates.append((dist, doc_id, doc, meta))

                candidates.sort(key=lambda x: float(x[0]) if x[0] is not None else float("inf"))
                chosen = candidates[:resolved_topk]

                merged["documents"].append([c[2] for c in chosen])
                merged["metadatas"].append([c[3] for c in chosen])
                merged["distances"].append([c[0] for c in chosen])
                if has_ids:
                    merged["ids"].append([c[1] for c in chosen])

            return merged


    def delete_file_vectors(self, user_id: int | str, file_id: int | str):
        """
        根据用户ID和文件ID删除对应的向量
        Args:
            user_id (int | str): 用户ID
            file_id (int | str): 文件ID
        Returns:
            str: "success" 表示删除成功，"fail" 表示失败
        """
        try:
            user_id_str = str(user_id)
            file_id_str = str(file_id)
            collection_name = f"user_{user_id_str}"
            col = self.client.get_or_create_collection(collection_name)
            col.delete(where={"file_id": file_id_str})
            # 兼容旧数据：曾以 int 形式写入 file_id
            try:
                if file_id_str.isdigit():
                    col.delete(where={"file_id": int(file_id_str)})
            except Exception:
                pass

            logger.info(f"成功删除用户 {user_id_str} 的文件 {file_id_str} 对应的向量")
            return "success"
        except Exception as e:
            logger.error(f"删除用户 {user_id} 的文件 {file_id} 向量失败: {str(e)}", exc_info=True)
            return "fail"

    def insert_file_vectors(
        self,
        file_name: str,
        user_id: int | str,
        file_id: int | str,
        file_type: str,
        url: str,
        folder_id: int,
        documents: List[str],
        file_size: int | None = None,
        created_at: int | None = None,
        source_type: str | None = None,
        source_material_id: str | None = None,
        source_material_title: str | None = None,
    ):
        """
        将文件内容插入到ChromaDB中，生成并存储embedding向量
        Args:
            file_name: file_name, 文件名称
            user_id (int | str): 用户ID
            file_id (int | str): 文件ID
            file_type (str): 文件类型
            url (str): 文件URL
            folder_id (int): 文件夹ID
            file_size (int | None): 文件大小（字节）。用于前端展示与溯源，不参与向量检索。
            created_at (int | None): 创建时间（毫秒时间戳）。若不传则使用当前时间。
            source_type (str | None): 来源类型（upload/material）。若不传则按 file_id/folder_id 推断。
            source_material_id (str | None): 来源教学资料 ID（source_type=material 时可用）。
            source_material_title (str | None): 来源教学资料标题（可选，用于前端展示）。
            documents (List[str]): 文件内容列表
        Returns:
            dict: 包含embedding结果
        """
        # 首先删除已有存在的相同文件
        del_status = self.delete_file_vectors(user_id, file_id)
        # 然后插入新的向量
        try:
            user_id_str = str(user_id)
            file_id_str = str(file_id)
            collection_name = f"user_{user_id_str}"
            vectors_result = self.embedder.do_embedding(texts=documents)
            vectors = vectors_result["data"]
            embeddings = [one["embedding"] for one in vectors]
            # 统一存储 file_size（字节），便于前端展示；旧数据无该字段时会在 list_files_by_user 中做兜底估算
            resolved_file_size = None
            if file_size is not None:
                try:
                    resolved_file_size = int(file_size)
                    if resolved_file_size < 0:
                        resolved_file_size = 0
                except Exception:
                    resolved_file_size = None

            resolved_created_at = self._normalize_timestamp_ms(created_at) or int(time.time() * 1000)

            resolved_source_type = self._normalize_source_type(source_type)
            if resolved_source_type is None:
                try:
                    folder_id_int = int(folder_id) if folder_id is not None else 0
                except Exception:
                    folder_id_int = 0
                if file_id_str.startswith("upload:") or folder_id_int == 0:
                    resolved_source_type = "upload"
                elif file_id_str.startswith("gen:") or folder_id_int == 1:
                    resolved_source_type = "material"

            resolved_source_material_id = (str(source_material_id).strip() if source_material_id is not None else "") or None
            if resolved_source_material_id is None and resolved_source_type == "material":
                resolved_source_material_id = self._try_parse_material_id_from_gen_file_id(file_id_str)

            resolved_source_material_title = (
                (str(source_material_title).strip() if source_material_title is not None else "") or None
            )

            base_meta: Dict[str, Any] = {
                "file_name": file_name,
                "file_id": file_id_str,
                "user_id": user_id_str,
                "folder_id": int(folder_id or 0),
                "url": url,
                "file_type": file_type,
                "created_at": resolved_created_at,
            }
            if resolved_file_size is not None:
                base_meta["file_size"] = resolved_file_size
            if resolved_source_type is not None:
                base_meta["source_type"] = resolved_source_type
            if resolved_source_material_id is not None:
                base_meta["source_material_id"] = resolved_source_material_id
            if resolved_source_material_title is not None:
                base_meta["source_material_title"] = resolved_source_material_title

            meta = [base_meta.copy() for _ in documents]
            ids = [f"{file_id_str}_{i}" for i in range(len(documents))]
            col = self.client.get_or_create_collection(collection_name, metadata={"hnsw:space": "cosine"})
            col.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=meta,
                ids=ids
            )
            logger.info(f"成功插入文件 {file_id} 的向量到集合 {collection_name}")
            return vectors_result
        except Exception as e:
            logger.error(f"插入用户 {user_id} 的文件 {file_id} 向量失败: {str(e)}", exc_info=True)
            raise ValueError(f"插入向量失败: {str(e)}")



    def list_collection(self, collection, number=100):
        """
        列出某个集后的内容
        Returns:
        """
        col = self.client.get_or_create_collection(collection)
        data = col.peek(number)
        total = col.count()
        result = {
            "data": data,
            "number": number,
            "total": total
        }
        return result

    def list_files_by_user(self, user_id: int | str) -> List[Dict[str, Any]]:
        """
        根据用户ID列出该用户的所有文件信息
        Args:
            user_id (int | str): 用户ID
        Returns:
            List[Dict[str, Any]]: 文件信息列表
        """
        try:
            user_id_str = str(user_id)
            collection_name = f"user_{user_id_str}"
            # 确认集合存在
            collections = self.list_exist_collections()
            if collection_name not in collections:
                logger.warning(f"集合 {collection_name} 不存在，用户 {user_id} 没有任何文件。")
                return []

            col = self.client.get_collection(collection_name)

            # 获取所有与该用户ID相关的文档元数据
            # 注意：get()方法在没有where条件时返回所有文档，数据量可能很大
            # 但由于我们是按用户集合来操作的，所以这里获取的是该用户的所有数据
            results = col.get()

            metadatas = results.get("metadatas") or []
            documents = results.get("documents") or []

            # 文件信息可能重复，需要去重
            unique_files: Dict[str, Dict[str, Any]] = {}
            # 旧数据可能没有 file_size，这里做一次兜底：用 documents 的字节长度粗略估算
            approx_sizes: Dict[str, int] = {}
            for idx, meta in enumerate(metadatas):
                # 确保meta是字典且包含file_id
                if isinstance(meta, dict) and 'file_id' in meta:
                    file_id = meta.get('file_id')
                    # 过滤掉无效的file_id
                    if file_id is None:
                        continue

                    # 检查用户ID是否匹配
                    if str(meta.get('user_id')) == user_id_str:
                        file_id_key = str(file_id)
                        if file_id_key not in unique_files:
                            unique_files[file_id_key] = {
                                "file_id": file_id_key,
                                "file_name": meta.get('file_name'),
                                "file_type": meta.get('file_type'),
                                "url": meta.get('url'),
                                "folder_id": meta.get('folder_id'),
                                "user_id": meta.get('user_id'),
                            }

                        raw_created_at = (
                            meta.get("created_at") if meta.get("created_at") is not None else meta.get("createdAt")
                        )
                        created_at_ms = self._normalize_timestamp_ms(raw_created_at)
                        if created_at_ms is not None:
                            prev = unique_files[file_id_key].get("created_at")
                            if prev is None or int(created_at_ms) > int(prev):
                                unique_files[file_id_key]["created_at"] = int(created_at_ms)

                        source_type_norm = self._normalize_source_type(meta.get("source_type") or meta.get("sourceType"))
                        if source_type_norm:
                            unique_files[file_id_key]["source_type"] = source_type_norm

                        raw_source_material_id = (
                            meta.get("source_material_id")
                            if meta.get("source_material_id") is not None
                            else meta.get("sourceMaterialId")
                        )
                        if raw_source_material_id is not None:
                            sid = str(raw_source_material_id).strip()
                            if sid:
                                unique_files[file_id_key]["source_material_id"] = sid

                        raw_source_material_title = (
                            meta.get("source_material_title")
                            if meta.get("source_material_title") is not None
                            else meta.get("sourceMaterialTitle")
                        )
                        if raw_source_material_title is not None:
                            title = str(raw_source_material_title).strip()
                            if title:
                                unique_files[file_id_key]["source_material_title"] = title

                        # 优先使用显式存储的 file_size（更准确）
                        raw_size = meta.get("file_size") if meta.get("file_size") is not None else meta.get("fileSize")
                        if raw_size is not None:
                            try:
                                size_int = int(raw_size)
                                if size_int < 0:
                                    size_int = 0
                                prev = unique_files[file_id_key].get("file_size")
                                if prev is None or size_int > int(prev):
                                    unique_files[file_id_key]["file_size"] = size_int
                            except Exception:
                                # 忽略非法值，继续走兜底估算
                                pass
                        else:
                            doc = documents[idx] if idx < len(documents) else None
                            if isinstance(doc, str) and doc:
                                approx_sizes[file_id_key] = approx_sizes.get(file_id_key, 0) + len(doc.encode("utf-8"))

            # 补齐缺失的 source 信息（仅对旧数据兜底）
            for fid, info in unique_files.items():
                if not info.get("source_type"):
                    try:
                        folder_id_int = int(info.get("folder_id")) if info.get("folder_id") is not None else 0
                    except Exception:
                        folder_id_int = 0
                    if fid.startswith("upload:") or folder_id_int == 0:
                        info["source_type"] = "upload"
                    elif fid.startswith("gen:") or folder_id_int == 1:
                        info["source_type"] = "material"

                if info.get("source_type") == "material" and not info.get("source_material_id"):
                    parsed = self._try_parse_material_id_from_gen_file_id(fid)
                    if parsed:
                        info["source_material_id"] = parsed

            # 补齐缺失的 file_size（仅对旧数据生效）
            for fid, size in approx_sizes.items():
                if fid in unique_files and unique_files[fid].get("file_size") is None:
                    unique_files[fid]["file_size"] = int(size)

            return list(unique_files.values())
        except Exception as e:
            # 如果collection不存在或其他异常
            logger.error(f"为用户 {user_id} 列出文件失败: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def _merge_overlapping_chunks(chunks: List[str], *, max_overlap_chars: int = 8192) -> str:
        """
        将按顺序排列的文本块拼接为完整内容，并尝试去除相邻块的重叠部分。

        说明：当前 personaldb 的分块策略会产生 overlap（重复片段），直接 join 会导致内容重复；
        此处通过检测「已拼接内容的后缀」与「下一块的前缀」的最长匹配来去重。
        """
        merged = ""
        for chunk in chunks:
            if not chunk:
                continue
            if not merged:
                merged = chunk
                continue

            max_k = min(len(chunk), len(merged), max_overlap_chars)
            overlap = 0
            for k in range(max_k, 0, -1):
                if merged.endswith(chunk[:k]):
                    overlap = k
                    break
            merged += chunk[overlap:]
        return merged

    @staticmethod
    def _extract_chunk_index(doc_id: Any) -> int:
        if not isinstance(doc_id, str):
            return 0
        tail = doc_id.rsplit("_", 1)[-1]
        return int(tail) if tail.isdigit() else 0

    def get_file_content(self, *, user_id: int | str, file_id: int | str) -> Optional[Dict[str, Any]]:
        """
        根据 user_id + file_id 取回该文件的聚合内容（Markdown/纯文本）。

        返回字段：
        - user_id, file_id, file_name, file_type, file_size, content
        """
        user_id_str = str(user_id)
        file_id_str = str(file_id)
        collection_name = f"user_{user_id_str}"

        collections = self.list_exist_collections()
        if collection_name not in collections:
            return None

        col = self.client.get_collection(collection_name)

        try:
            result = col.get(where={"file_id": file_id_str})
        except Exception:
            # 兼容旧数据：曾以 int 形式写入 file_id
            if file_id_str.isdigit():
                result = col.get(where={"file_id": int(file_id_str)})
            else:
                raise

        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []

        if not ids or not documents:
            return None

        ordered_docs: List[tuple[int, str]] = []
        first_meta: Dict[str, Any] | None = None

        for idx, doc_id in enumerate(ids):
            doc = documents[idx] if idx < len(documents) else None
            meta = metadatas[idx] if idx < len(metadatas) else None

            if first_meta is None and isinstance(meta, dict):
                first_meta = meta

            if not isinstance(doc, str):
                continue

            ordered_docs.append((self._extract_chunk_index(doc_id), doc))

        if not ordered_docs:
            return None

        ordered_docs.sort(key=lambda it: it[0])
        content = self._merge_overlapping_chunks([doc for _, doc in ordered_docs])

        meta0 = first_meta or {}
        file_name = str(meta0.get("file_name") or meta0.get("fileName") or "").strip()
        file_type = str(meta0.get("file_type") or meta0.get("fileType") or "").strip()

        created_at_ms = self._normalize_timestamp_ms(
            meta0.get("created_at") if meta0.get("created_at") is not None else meta0.get("createdAt")
        )

        source_type_norm = self._normalize_source_type(meta0.get("source_type") or meta0.get("sourceType"))
        if source_type_norm is None:
            if file_id_str.startswith("upload:"):
                source_type_norm = "upload"
            elif file_id_str.startswith("gen:"):
                source_type_norm = "material"

        source_material_id = (
            str(meta0.get("source_material_id") or meta0.get("sourceMaterialId") or "").strip() or None
        )
        if source_material_id is None and source_type_norm == "material":
            source_material_id = self._try_parse_material_id_from_gen_file_id(file_id_str)

        source_material_title = (
            str(meta0.get("source_material_title") or meta0.get("sourceMaterialTitle") or "").strip() or None
        )

        raw_size = meta0.get("file_size") if meta0.get("file_size") is not None else meta0.get("fileSize")
        if raw_size is None:
            try:
                file_size = len(content.encode("utf-8"))
            except Exception:
                file_size = 0
        else:
            try:
                file_size = int(raw_size)
                if file_size < 0:
                    file_size = 0
            except Exception:
                file_size = 0

        return {
            "user_id": user_id_str,
            "file_id": file_id_str,
            "file_name": file_name,
            "file_type": file_type,
            "file_size": file_size,
            "content": content,
            **({"created_at": int(created_at_ms)} if created_at_ms is not None else {}),
            **({"source_type": source_type_norm} if source_type_norm is not None else {}),
            **({"source_material_id": source_material_id} if source_material_id is not None else {}),
            **({"source_material_title": source_material_title} if source_material_title is not None else {}),
        }

    def list_exist_collections(self):
        """
        列出所有已有的collections
        Returns:
        """
        collections_info = self.client.list_collections()
        collections = [i.name for i in collections_info]
        return collections

class EmbeddingModel(object):
    def __init__(self):
        """
        环境变量：
        - EMBEDDING_TYPE: openai | ollama
        - EMBEDDING_MODEL:    各提供方的模型名
        - 通用：EMBEDDING_DIM (可选，部分提供方不支持自定义维度)
        - 通用：EMBEDDING_API_KEY / EMBEDDING_BASE_URL
          * openai: base_url 可指向 OpenAI / DeepSeek / 阿里 DashScope / 豆包 / vLLM / Xinference 等 OpenAI 兼容服务
          * ollama: EMBEDDING_BASE_URL 或 OLLAMA_BASE_URL(默认 http://127.0.0.1:11434)
        """
        self.model = os.environ["EMBEDDING_MODEL"]
        provider = os.getenv("EMBEDDING_TYPE")
        if not provider:
            raise Exception("必须设置 EMBEDDING_TYPE")
        self.provider = provider.lower()
        self.dimensions = int(os.getenv("EMBEDDING_DIM", "0")) or None

        if self.provider == "openai":
            api_key = os.getenv("EMBEDDING_API_KEY")
            assert api_key, "未配置嵌入模型 API Key，请设置 EMBEDDING_API_KEY"
            base_url = (os.getenv("EMBEDDING_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
            # 可调超时与重试：某些 OpenAI 兼容网关在 TLS 握手/高峰期可能偶发超时
            # - EMBEDDING_TIMEOUT_S：请求超时（秒），默认 60
            # - EMBEDDING_MAX_RETRIES：失败重试次数，默认 2（与 OpenAI SDK 默认一致）
            try:
                timeout_s = float(os.getenv("EMBEDDING_TIMEOUT_S", "60"))
            except Exception:
                timeout_s = 60.0
            try:
                max_retries = int(os.getenv("EMBEDDING_MAX_RETRIES", "2"))
            except Exception:
                max_retries = 2
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout_s,
                max_retries=max_retries,
            )
            self._impl = self._impl_openai_compatible
        elif self.provider == "ollama":
            # 使用Ollama原生 /api/embeddings，兼容性最稳妥
            self.ollama_base = (
                os.getenv("EMBEDDING_BASE_URL")
                or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
            ).rstrip("/")
            self.session = requests.Session()
            self._impl = self._impl_ollama_native
        else:
            raise Exception(f"不支持的 EMBEDDING_TYPE: {self.provider}，当前仅支持 openai 或 ollama")

    def do_embedding(self, texts: List[str]):
        """
        对数据进行embedding。返回：{"data":[{"embedding":[...]}, ...]}

        缓存策略：
        - 缓存 key 显式包含 EMBEDDING_TYPE / EMBEDDING_MODEL 和输入 texts
        - 只有在 result["data"] 非空时才写入缓存
        - 失败或 result["data"] 为空一律不缓存
        """
        assert isinstance(texts, list) and all(isinstance(t, str) for t in texts), "texts必须为字符串列表"
        # 空输入直接返回空结果，避免无意义的下游调用
        if not texts:
            logger.info("do_embedding 收到空文本列表，直接返回空结果")
            return {"data": []}

        # --- 缓存查找阶段 ---
        cache_dir = str(get_cache_dir("personaldb") / "embeddings")
        os.makedirs(cache_dir, exist_ok=True)

        cache_payload = {
            "provider": self.provider,
            "model": self.model,
            "texts": texts,
        }
        cache_key = cal_md5(json.dumps(cache_payload, ensure_ascii=False, sort_keys=True))
        cache_file = os.path.join(cache_dir, f"{cache_key}_cache.pkl")

        if os.path.exists(cache_file):
            try:
                with open(cache_file, "rb") as f:
                    cached = pickle.load(f)
                if isinstance(cached, dict) and isinstance(cached.get("data"), list) and cached["data"]:
                    logger.info(
                        "Embedding do_embedding 缓存命中，provider=%s, model=%s, 文本数=%d",
                        self.provider,
                        self.model,
                        len(texts),
                    )
                    return cached
                else:
                    logger.warning("Embedding 缓存文件 %s 内容为空或格式不合法，忽略缓存", cache_file)
            except Exception as e:
                logger.warning("读取 Embedding 缓存文件 %s 失败，将重新计算: %s", cache_file, e)

        # --- 实际嵌入计算阶段 ---
        max_batch_size = 10  # 可根据不同后端调整
        result: Dict[str, List[Dict[str, Any]]] = {"data": []}
        for i in range(0, len(texts), max_batch_size):
            batch = texts[i:i + max_batch_size]
            try:
                batch_out = self._impl(batch)
                # 规范化为 {"data":[{"embedding":[...]}...]}
                if isinstance(batch_out, dict) and "data" in batch_out:
                    result["data"].extend(batch_out["data"])
                else:
                    # 兜底：如果只是返回了向量列表
                    result["data"].extend([{"embedding": emb} for emb in batch_out])
                logger.info("成功嵌入批次 %d，包含 %d 个文本", i // max_batch_size + 1, len(batch))
            except Exception as e:
                # 关键修复：任何一批失败都直接抛异常，而不是静默返回空 data，避免错误结果被上游缓存
                logger.error("嵌入批次 %d 失败: %s", i // max_batch_size + 1, e, exc_info=True)
                raise RuntimeError(f"嵌入批次 {i // max_batch_size + 1} 失败: {e}") from e

        # 所有批次都成功但结果仍为空（例如上游返回了空 data），视为配置/鉴权等错误
        if not result["data"]:
            logger.error(
                "嵌入结果为空，provider=%s, model=%s，可能是上游模型或鉴权配置错误，请检查相关配置",
                self.provider,
                self.model,
            )
            # 不写缓存，直接抛错
            raise RuntimeError(
                "嵌入结果为空，可能是上游模型或鉴权配置错误，请检查 EMBEDDING_TYPE / EMBEDDING_MODEL 及对应 API Key 配置"
            )

        logger.info("所有 %d 个文本嵌入完成，准备写入缓存", len(texts))

        # --- 写入缓存（仅在非空结果时） ---
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(result, f)
            logger.info(
                "Embedding 缓存写入成功，文件=%s, provider=%s, model=%s, 文本数=%d",
                cache_file,
                self.provider,
                self.model,
                len(texts),
            )
        except Exception as e:
            logger.warning("写入 Embedding 缓存文件 %s 失败（忽略，不影响主流程）: %s", cache_file, e)

        return result

    # ---------- 各提供方实现 ----------
    def _impl_openai_compatible(self, texts: List[str]):
        """
        适用于：阿里云(百炼兼容)、vLLM、Xinference等OpenAI兼容服务
        注意：有些后端不支持dimensions；不支持时自动忽略
        """
        kwargs = {"model": self.model, "input": texts}
        # 尝试传维度；如后端不支持则自动降级
        if self.dimensions:
            kwargs["dimensions"] = self.dimensions
        try:
            resp = self.client.embeddings.create(**kwargs)
        except Exception as e:
            # 如果是因不支持dimensions导致，去掉维度再试一次
            if self.dimensions:
                logger.warning(f"后端可能不支持自定义维度，去掉dimensions重试。错误：{e}")
                kwargs.pop("dimensions", None)
                resp = self.client.embeddings.create(**kwargs)
            else:
                raise
        # 统一输出格式
        out = resp.dict()
        # 有些实现不会返回encoding_format/等字段，不影响
        return {"data": [{"embedding": item["embedding"]} for item in out["data"]]}

    def _impl_ollama_native(self, texts: List[str]):
        """
        适用于Ollama原生接口：POST {OLLAMA_BASE_URL}/api/embeddings
        body: {"model": "...", "prompt": "..."}
        不支持批量输入 => 逐条请求
        """
        url = f"{self.ollama_base}/api/embeddings"
        data = []
        for t in texts:
            payload = {"model": self.model, "prompt": t}
            r = self.session.post(url, json=payload, timeout=120)
            if r.status_code != 200:
                raise RuntimeError(f"Ollama embeddings失败: {r.status_code} {r.text}")
            j = r.json()
            # 返回形如 {"embedding":[...]}
            data.append({"embedding": j.get("embedding")})
        return {"data": data}


if __name__ == '__main__':
    embedder = EmbeddingModel()
    chromadb_instance = ChromaDB(embedder=embedder)
    # 列出所有已有的collections
    print(chromadb_instance.list_exist_collections())
    # 列出collection的内容
    collection="test"
    number = 3
    print(chromadb_instance.list_collection(collection, number))
    query_documents = ["hello", "world"]
    keyword = "yes"
    result = chromadb_instance.query2collection(collection, query_documents, keyword=keyword,topk=3)
    documents = ["hello", "world"]
    result = chromadb_instance.insert2collection(collection, documents, meta=[])

    result = chromadb_instance.delete_one_collection(collection)

    # doc_id = "0"  # 假设您要删除 ID 为 "0" 的文档
    # result = chromadb_instance.delete_one_document(collection, doc_id)
    # print(f"删除结果: {result}")

