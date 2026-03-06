#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/12
# @Desc  : 使用FastAPI实现API，接收JSON或RabbitMQ消息，下载七牛云文件，读取内容并生成embedding向量

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, ValidationError

try:
    # 兼容在 `backend/personaldb` 目录下直接运行（例如 `python main.py`）
    from runtime_paths import find_repo_root, get_tmp_dir
except ImportError:  # pragma: no cover - 兼容以包方式导入（用于单元测试等）
    from backend.personaldb.runtime_paths import find_repo_root, get_tmp_dir

_repo_root = find_repo_root(Path(__file__).resolve())
# 允许在 `backend/personaldb` 目录下直接运行：确保可导入 backend.*
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.common.env_loader import load_env_files

# 注意：必须在 import embedding_utils 之前调用；
# embedding_utils 里存在模块级缓存目录计算（依赖 TEACHDO_CACHE_DIR 等配置）。
load_env_files(repo_root=_repo_root, service_dir=Path(__file__).resolve().parent)

try:
    import embedding_utils
    from embedding_utils import cache_decorator
except ImportError:  # pragma: no cover - 兼容以包方式导入（用于单元测试等）
    from backend.personaldb import embedding_utils
    from backend.personaldb.embedding_utils import cache_decorator

try:
    from core.magic_pdf_converter import MagicPDFConverter
    from core.markitdown_converter import MarkItDownConverter
    from core.chunkers.fast_chunker import FastChunker
    from core.chunkers.semantic_chunker import SemanticChunker
except ImportError:  # pragma: no cover - 兼容以包方式导入（用于单元测试等）
    from backend.personaldb.core.magic_pdf_converter import MagicPDFConverter
    from backend.personaldb.core.markitdown_converter import MarkItDownConverter
    from backend.personaldb.core.chunkers.fast_chunker import FastChunker
    from backend.personaldb.core.chunkers.semantic_chunker import SemanticChunker

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/healthz")
def healthz():
    return {"ok": True}


# 创建临时下载目录（集中到 var/tmp）
TEMP_DIR = str(get_tmp_dir("personaldb"))

# RabbitMQ消息处理类

class SearchQuery(BaseModel):
    userId: int | str
    query: str
    keyword: Optional[str] = ""
    topk: Optional[int] = 3
    fileIds: Optional[List[str]] = None

@app.post("/search")
def search_personal_knowledge_base(query: SearchQuery):
    """
    搜索个人知识库
    """
    try:
        logger.info(f"收到搜索请求: {query}")
        embedder = embedding_utils.EmbeddingModel()
        chroma = embedding_utils.ChromaDB(embedder)
        collection_name = f"user_{query.userId}"

        result = chroma.query2collection(
            collection=collection_name,
            query_documents=[query.query],
            keyword=query.keyword,
            topk=query.topk,
            file_ids=query.fileIds,
        )
        logger.info(f"搜索成功: {result}")
        return result
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@cache_decorator
def _get_markdown_content(file_path: str, file_name: str) -> str:
    """
    根据文件类型选择合适的转换器，将文件内容转换为Markdown格式。
    PDF文件使用MagicPDFConverter（MinerU），其他文件使用MarkitdownConverter。
    """
    # 获取文件扩展名, 是否可以使用MinerU，如果不用显卡速度太慢
    USE_MINERU = os.environ.get("USE_MINERU", "false")
    if USE_MINERU.lower() == "true":
        CAN_USE_MINERU = True
    else:
        CAN_USE_MINERU = False
    file_extension = os.path.splitext(file_name)[1].lower() if file_name else ""

    # 根据文件类型选择转换器
    if CAN_USE_MINERU and file_extension == '.pdf':
        # 使用 MinerU (MagicPDFConverter) 处理PDF
        logger.info(f"使用PDF转换器(MinerU)处理文件: {file_path}")
        converter = MagicPDFConverter(output_dir="./output_pdf")
        content, _ = converter.convert_pdf_file(file_path)
        return True, content
    else:
        # 使用 markitdown 处理其他文件
        logger.info(f"使用Markitdown转换器处理文件: {file_path}")
        converter = MarkItDownConverter(use_magic_pdf=False)  #use_magic_pdf设定是否使用MinerU
        content, _ = converter.convert_file(file_path)
        return True, content


def process_and_vectorize_local_file(
    file_name: str,
    temp_file_path: str,
    id: int | str,
    user_id: int | str,
    file_type: str,
    url: str,
    folder_id: int,
    created_at: int | None = None,
    source_type: str | None = None,
    source_material_id: str | None = None,
    source_material_title: str | None = None,
):
    """
    从本地文件路径处理文件、进行向量化并存储
    """
    # 步骤2: 使用适当的转换器读取文件内容
    logger.info(f"开始读取文件内容: {temp_file_path}")
    
    status, markdown_content = _get_markdown_content(temp_file_path, file_name)

    if not markdown_content or not markdown_content.strip():
        logger.error(f"文件内容为空或无效: {temp_file_path}")
        raise ValueError("文件内容为空或无效")
    logger.info(f"文件内容读取成功，准备进行分块。")

    # 对Markdown格式进行Trunk(分块)
    documents = _chunk_text(markdown_content)
    if not documents:
        raise ValueError("分块后内容为空")
    logger.info(f"内容分块成功，共 {len(documents)} 块。")

    # 原始文件大小（字节），用于前端知识库列表展示
    try:
        file_size = os.path.getsize(temp_file_path)
    except OSError:
        file_size = 0

    # 步骤3: 使用embedding_utils生成embedding向量并插入向量（内部会校验 EMBEDDING_* 配置）
    logger.info("初始化embedding模型")
    embedder = embedding_utils.EmbeddingModel()
    chroma = embedding_utils.ChromaDB(embedder)
    logger.info(f"开始插入文件 {id} 的向量")
    embedding_result = chroma.insert_file_vectors(
        file_name=file_name,
        user_id=user_id,
        file_id=id,
        file_type=file_type or "unknown",
        url=url or "",
        folder_id=folder_id or 0,
        documents=documents,
        file_size=file_size,
        created_at=created_at,
        source_type=source_type,
        source_material_id=source_material_id,
        source_material_title=source_material_title,
    )
    logger.info("向量插入成功")

    result = {
        "id": id,
        "file_name": file_name,
        "userId": user_id,
        "fileType": file_type,
        "url": url,
        "folderId": folder_id,
        **({"created_at": created_at} if created_at is not None else {}),
        **({"source_type": source_type} if source_type is not None else {}),
        **({"source_material_id": source_material_id} if source_material_id is not None else {}),
        **({"source_material_title": source_material_title} if source_material_title is not None else {}),
        "embedding_result": embedding_result,
        "markdown_content": markdown_content
    }
    logger.info(f"处理OK。。。")
    return result


def process_file_sync(
    file_name: str,
    id: int,
    user_id: int | str,
    file_type: str,
    url: str,
    folder_id: int,
    created_at: int | None = None,
    source_type: str | None = None,
    source_material_id: str | None = None,
    source_material_title: str | None = None,
):
    """
    处理文件下载、读取和生成embedding的同步版本
    """
    if not url:
        logger.error("url为空")
        raise ValueError("url不能为空")

    # 验证URL格式
    if not url.startswith(("http://", "https://")):
        logger.error(f"无效的URL格式: {url}")
        raise ValueError("url必须以http://或https://开头")

    parsed_url = urlparse(url)
    logger.info(f"解析后的URL: {parsed_url.geturl()}")
    temp_file_path = None
    try:
        # 步骤1: 下载文件
        # file_name = os.path.basename(parsed_url.path) or f"downloaded_file_{user_id}"
        temp_file_path = os.path.join(TEMP_DIR, file_name)
        logger.info(f"开始下载文件: {url}")
        response = requests.get(url, timeout=60, proxies=None)
        response.raise_for_status()
        with open(temp_file_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"文件下载成功: {temp_file_path}")

        return process_and_vectorize_local_file(
            file_name=file_name,
            temp_file_path=temp_file_path,
            id=id,
            user_id=user_id,
            file_type=file_type,
            url=url,
            folder_id=folder_id,
            created_at=created_at,
            source_type=source_type,
            source_material_id=source_material_id,
            source_material_title=source_material_title,
        )

    except requests.exceptions.Timeout as e:
        logger.error(f"下载文件超时: {str(e)}", exc_info=True)
        raise ValueError(f"下载文件超时: {str(e)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"下载文件失败: {str(e)}", exc_info=True)
        raise ValueError(f"下载文件失败: {str(e)}")
    except ValueError as e:
        logger.error(f"处理失败: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"未知错误: {str(e)}", exc_info=True)
        raise ValueError(f"未知错误: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"临时文件已删除: {temp_file_path}")


@app.post("/upload/")
async def upload_and_vectorize_endpoint(request: Request):
    """
    支持三种内容类型：
    - multipart/form-data（带或不带文件）
    - application/x-www-form-urlencoded
    - application/json

    字段：
    - userId: int | str
    - fileId: int | str
    - folderId: int (可选，默认0)
    - fileType: str (可选)
    - url: str (可选，与 file 互斥)
    - file: UploadFile (可选，与 url 互斥)
    """
    temp_file_path = None
    try:
        # 统一解析 body
        content_type = request.headers.get("content-type", "")
        data = {}
        upload_file: UploadFile | None = None

        if "application/json" in content_type:
            data = await request.json()
        else:
            # 对 multipart/form-data 与 x-www-form-urlencoded 都适用
            form = await request.form()
            data = dict(form)
            possible_file = form.get("file")
            if possible_file:
                upload_file = possible_file

        # 参数解析与校验
        userId = data.get("userId")
        fileId = data.get("fileId")

        if userId is None:
            raise HTTPException(status_code=422, detail="缺少或非法参数: userId")
        if fileId is None:
            raise HTTPException(status_code=422, detail="缺少或非法参数: fileId")

        userId = str(userId)
        fileId = str(fileId)

        folderId = int(data.get("folderId", 0))
        fileType = data.get("fileType")
        url = data.get("url")

        # --- 可观测性元数据（用于前端展示“时间 + 来源”）---
        # createdAt: 毫秒时间戳；若不传则使用当前时间
        raw_created_at = data.get("createdAt") if data.get("createdAt") is not None else data.get("created_at")
        created_at_ms = embedding_utils.ChromaDB._normalize_timestamp_ms(raw_created_at) or int(time.time() * 1000)

        raw_source_type = data.get("sourceType") if data.get("sourceType") is not None else data.get("source_type")
        source_type_norm = embedding_utils.ChromaDB._normalize_source_type(raw_source_type) or "upload"

        raw_source_material_id = (
            data.get("sourceMaterialId") if data.get("sourceMaterialId") is not None else data.get("source_material_id")
        )
        source_material_id = str(raw_source_material_id).strip() if raw_source_material_id is not None else None
        if source_material_id == "":
            source_material_id = None

        raw_source_material_title = (
            data.get("sourceMaterialTitle")
            if data.get("sourceMaterialTitle") is not None
            else data.get("source_material_title")
        )
        source_material_title = str(raw_source_material_title).strip() if raw_source_material_title is not None else None
        if source_material_title == "":
            source_material_title = None

        # 互斥校验
        has_url = bool(url and str(url).strip())
        has_file = upload_file is not None
        if not has_url and not has_file:
            raise HTTPException(status_code=400, detail="必须提供 'url' 或 'file'")
        if has_url and has_file:
            raise HTTPException(status_code=400, detail="只能提供 'url' 或 'file' 中的一个")

        # 分支：文件上传
        if has_file:
            # 推断 fileType
            if not fileType and upload_file and upload_file.filename:
                fileType = upload_file.filename.split(".")[-1] if "." in upload_file.filename else "unknown"

            temp_file_name = f"{uuid.uuid4()}_{upload_file.filename or 'uploaded_file'}"
            temp_file_path = os.path.join(TEMP_DIR, temp_file_name)
            # 保存上传内容
            content_bytes = await upload_file.read()
            with open(temp_file_path, "wb") as buffer:
                buffer.write(content_bytes)
            logger.info(f"文件上传成功: {temp_file_path}")

            return process_and_vectorize_local_file(
                file_name=upload_file.filename or "uploaded_file",
                temp_file_path=temp_file_path,
                id=fileId,
                user_id=userId,
                file_type=fileType,
                url="",  # 直接上传无 URL
                folder_id=folderId,
                created_at=created_at_ms,
                source_type=source_type_norm,
                source_material_id=source_material_id,
                source_material_title=source_material_title,
            )

        # 分支：URL 下载处理
        else:
            file_name = os.path.basename(urlparse(url).path) or f"downloaded_file_{userId}"
            return process_file_sync(
                file_name=file_name,
                id=fileId,
                user_id=userId,
                file_type=fileType,
                url=url,
                folder_id=folderId,
                created_at=created_at_ms,
                source_type=source_type_norm,
                source_material_id=source_material_id,
                source_material_title=source_material_title,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传和向量化失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pass
        # if temp_file_path and os.path.exists(temp_file_path):
        #     os.remove(temp_file_path)
        #     logger.info(f"临时文件已删除: {temp_file_path}")


class TextVectorizeBody(BaseModel):
    """
    纯文本向量化请求体。
    仅必需字段：content, fileId, fileName
    其余参数均为可选，默认空/0。
    """
    content: str
    fileId: str
    fileName: str
    userId: Optional[str] = "0"
    fileType: Optional[str] = None
    url: Optional[str] = ""
    folderId: Optional[int] = 0
    # --- KB 元数据（可选）---
    # 说明：这些字段用于前端展示“时间 + 来源”，不参与向量检索。
    # createdAt 约定为毫秒时间戳；若不传则由服务端在落库时填充当前时间。
    createdAt: Optional[int] = None
    sourceType: Optional[str] = None
    sourceMaterialId: Optional[str] = None
    sourceMaterialTitle: Optional[str] = None


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> List[str]:
    """
    使用 SemanticChunker 进行分块。
    """
    text = (text or "").strip()
    if not text:
        return []
    chunker = FastChunker(max_tokens=max_chars)
    chunks = chunker.chunk_text(text)
    return [chunk.content for chunk in chunks]


def process_text_content(
    file_name: str,
    text: str,
    id: str,
    user_id: str = "0",
    file_type: Optional[str] = None,
    folder_id: int = 0,
    url: str = "",
    created_at: int | None = None,
    source_type: str | None = None,
    source_material_id: str | None = None,
    source_material_title: str | None = None,
):
    """
    直接对纯文本进行向量化并落库（Chroma）。
    其余参数默认空/0，以满足“无需额外参数”的需求。
    """
    logger.info("开始处理纯文本向量化")
    if not text or not text.strip():
        raise ValueError("content 不能为空")

    documents = _chunk_text(text)
    if not documents:
        raise ValueError("content 无有效文本")

    logger.info("初始化 embedding 模型与 Chroma")
    embedder = embedding_utils.EmbeddingModel()
    chroma = embedding_utils.ChromaDB(embedder)

    logger.info(f"插入文本向量：fileId={id}, userId={user_id}")
    # 纯文本的“大小”用 UTF-8 字节数表示（用于前端展示）
    try:
        file_size = len((text or "").encode("utf-8"))
    except Exception:
        file_size = 0
    embedding_result = chroma.insert_file_vectors(
        file_name=file_name,
        user_id=user_id,
        file_id=id,
        file_type=file_type or "unknown",
        url=url or "",
        folder_id=folder_id or 0,
        documents=documents,
        file_size=file_size,
        created_at=created_at,
        source_type=source_type,
        source_material_id=source_material_id,
        source_material_title=source_material_title,
    )

    result = {
        "id": id,
        "file_name": file_name,
        "userId": user_id,
        "fileType": file_type or "unknown",
        "url": url or "",
        "folderId": folder_id or 0,
        **({"created_at": created_at} if created_at is not None else {}),
        **({"source_type": source_type} if source_type is not None else {}),
        **({"source_material_id": source_material_id} if source_material_id is not None else {}),
        **({"source_material_title": source_material_title} if source_material_title is not None else {}),
        "embedding_result": embedding_result
    }
    logger.info("纯文本向量化完成")
    return result


# ===== 纯文本向量化接口 =====
@app.post("/vectorize/text")
def vectorize_text_endpoint(body: TextVectorizeBody):
    """
    纯文本向量化：
    - 必填：content, fileId, fileName
    - 可选：userId(默认0), fileType(None), url(""), folderId(0)
    """
    try:
        logger.info(
            f"收到文本向量化请求: fileId={body.fileId}, fileName={body.fileName}, userId={body.userId}"
        )
        kwargs = {}
        if body.createdAt is not None:
            kwargs["created_at"] = body.createdAt
        if body.sourceType:
            kwargs["source_type"] = body.sourceType
        if body.sourceMaterialId:
            kwargs["source_material_id"] = body.sourceMaterialId
        if body.sourceMaterialTitle:
            kwargs["source_material_title"] = body.sourceMaterialTitle

        return process_text_content(
            file_name=body.fileName,
            text=body.content,
            id=body.fileId,
            user_id=body.userId or "0",
            file_type=body.fileType,
            folder_id=body.folderId or 0,
            url=body.url or "",
            **kwargs,
        )
    except Exception as e:
        logger.error(f"文本向量化失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文本向量化失败: {str(e)}")

@app.get("/files/{user_id}")
def list_user_files(user_id: str):
    """
    列出指定用户的所有文件信息
    """
    try:
        logger.info(f"收到列出用户 {user_id} 文件的请求")
        embedder = embedding_utils.EmbeddingModel()
        chroma = embedding_utils.ChromaDB(embedder)

        files = chroma.list_files_by_user(user_id=user_id)

        if not files:
            logger.info(f"用户 {user_id} 没有任何文件。")
            return []

        logger.info(f"成功为用户 {user_id} 找到 {len(files)} 个文件。")
        return files
    except Exception as e:
        logger.error(f"列出用户 {user_id} 的文件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"列出文件失败: {str(e)}")


@app.get("/files/{user_id}/{file_id}/content")
def get_user_file_content(user_id: str, file_id: str):
    """
    导出/下载用：按 file_id 聚合返回该文件的内容（Markdown/纯文本）。

    注意：
    - personaldb 内部存的是分块后的 documents（存在 overlap 重复）
    - 这里会按 chunk id 顺序拼接并去除相邻重叠
    """
    try:
        logger.info(f"收到导出文件内容请求: user_id={user_id}, file_id={file_id}")
        chroma = embedding_utils.ChromaDB(embedder=None)
        result = chroma.get_file_content(user_id=user_id, file_id=file_id)
        if not result:
            raise HTTPException(status_code=404, detail="文件不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出文件内容失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@app.delete("/files/{user_id}/{file_id}")
def delete_user_file(user_id: str, file_id: str):
    """
    删除指定用户的某个文件对应的向量数据。
    """
    try:
        logger.info(f"收到删除向量请求: user_id={user_id}, file_id={file_id}")
        embedder = embedding_utils.EmbeddingModel()
        chroma = embedding_utils.ChromaDB(embedder)

        status = chroma.delete_file_vectors(user_id=user_id, file_id=file_id)
        if status != "success":
            raise HTTPException(status_code=500, detail="删除失败")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除向量失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


if __name__ == "__main__":
    # 允许在任意工作目录运行：确保可以导入 `backend.common.*`
    repo_root = find_repo_root(Path(__file__).resolve())
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from backend.common.logging_utils import build_uvicorn_log_config, apply_logging_config

        log_config = build_uvicorn_log_config()
        apply_logging_config(log_config)
    except Exception:
        log_config = None
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PERSONALDB_PORT") or os.environ.get("PERSONAL_DB_PORT") or "9100")

    logger.info("启动 Personal DB FastAPI 服务...")
    uvicorn.run(app, host=host, port=port, log_config=log_config)
