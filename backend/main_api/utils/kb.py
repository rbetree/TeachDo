import os
import json
import logging
from pathlib import Path
from typing import Any

import httpx
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def _get_personaldb_url() -> str | None:
    url = os.environ.get("PERSONAL_DB")
    return url.rstrip("/") if url else None


async def _is_personaldb_ready(personaldb_url: str) -> bool:
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(2.0)) as client:
            resp = await client.get(f"{personaldb_url}/healthz")
            return resp.status_code == 200
    except Exception:
        logger.debug("检查 personaldb 健康状态失败", exc_info=True)
        return False


def _normalize_kb_file_ids(kb_file_ids: list[str] | None) -> list[str]:
    """
    归一化 kb_file_ids：
    - 去空白
    - 去重（保持稳定顺序）
    """
    if not isinstance(kb_file_ids, list) or not kb_file_ids:
        return []
    seen: set[str] = set()
    resolved: list[str] = []
    for raw in kb_file_ids:
        sid = str(raw).strip()
        if not sid or sid in seen:
            continue
        seen.add(sid)
        resolved.append(sid)
    return resolved


def _split_kb_file_ids(kb_file_ids: list[str]) -> tuple[list[str], list[str]]:
    """
    按约定将 KB 文件拆分为两类：
    - full_ids：全文注入（gen:/full: 前缀）→ 拉取全文加入上下文（不经检索）
    - rag_ids：RAG 检索（非 gen:/full:）→ 仅用于 personaldb /search（只注入相关片段）
    """
    full_ids: list[str] = []
    rag_ids: list[str] = []
    for fid in kb_file_ids or []:
        if str(fid).startswith("gen:") or str(fid).startswith("full:"):
            full_ids.append(str(fid))
        else:
            rag_ids.append(str(fid))
    return full_ids, rag_ids


def _format_personaldb_search_context(
    result: object,
    *,
    max_chunks: int = 5,
    max_total_chars: int = 4000,
    max_chunk_chars: int = 800,
) -> str:
    """
    将 personaldb /search 的返回格式化为可拼进 prompt 的参考内容。
    约束：
    - 限制总长度，避免 prompt 过大导致模型效果变差或超限
    - 每个 chunk 截断
    """
    if not isinstance(result, dict):
        return ""

    documents = result.get("documents")
    metadatas = result.get("metadatas")
    distances = result.get("distances")

    docs_row: list[object] = []
    metas_row: list[object] = []
    dists_row: list[object] = []

    if isinstance(documents, list) and documents and isinstance(documents[0], list):
        docs_row = documents[0]
    if isinstance(metadatas, list) and metadatas and isinstance(metadatas[0], list):
        metas_row = metadatas[0]
    if isinstance(distances, list) and distances and isinstance(distances[0], list):
        dists_row = distances[0]

    blocks: list[str] = []
    total = 0
    for idx, doc in enumerate(docs_row):
        if not isinstance(doc, str):
            continue
        text = doc.strip()
        if not text:
            continue

        meta = metas_row[idx] if idx < len(metas_row) else None
        file_id = ""
        file_name = ""
        folder_id = None
        if isinstance(meta, dict):
            file_id = str(meta.get("file_id") or meta.get("fileId") or "").strip()
            file_name = str(meta.get("file_name") or meta.get("fileName") or "").strip()
            folder_id = meta.get("folder_id") if meta.get("folder_id") is not None else meta.get("folderId")

        dist = dists_row[idx] if idx < len(dists_row) else None
        dist_str = ""
        if dist is not None:
            try:
                dist_str = f"{float(dist):.4f}"
            except Exception:
                dist_str = ""

        if len(text) > max_chunk_chars:
            text = text[:max_chunk_chars].rstrip() + "…"

        meta_bits: list[str] = []
        if file_name:
            meta_bits.append(file_name)
        if file_id:
            meta_bits.append(f"file_id={file_id}")
        if folder_id is not None:
            try:
                meta_bits.append(f"folder_id={int(folder_id)}")
            except Exception:
                logger.debug("忽略非法 folder_id: %r", folder_id, exc_info=True)
                pass
        if dist_str:
            meta_bits.append(f"distance={dist_str}")
        meta_line = " / ".join(meta_bits).strip() or "KB chunk"

        block = f"[{len(blocks) + 1}] {meta_line}\n{text}"
        if total + len(block) > max_total_chars:
            break
        blocks.append(block)
        total += len(block) + 2
        if len(blocks) >= max_chunks:
            break

    return "\n\n".join(blocks).strip()


async def _search_personaldb_kb_context(
    personaldb_url: str,
    *,
    user_id: str,
    query: str,
    kb_file_ids: list[str],
    topk: int = 5,
) -> str:
    """
    从 personaldb 检索知识库片段，作为大纲生成的参考上下文。
    注意：检索失败时不应阻断主流程（仍可用主题生成大纲）。
    """
    if not query.strip():
        return ""
    if not kb_file_ids:
        return ""

    payload = {
        "userId": str(user_id),
        "query": str(query),
        "keyword": "",
        "topk": int(topk),
        "fileIds": list(kb_file_ids),
    }

    url = f"{personaldb_url}/search"
    async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(20.0)) as client:
        try:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                logger.info("[personaldb %s] %s", resp.status_code, resp.text)
                return ""
            try:
                result = resp.json()
            except ValueError:
                logger.info("personaldb /search 返回非 JSON：%s", resp.text)
                return ""
        except Exception as exc:
            logger.info("personaldb /search 调用失败：%s", exc)
            return ""

    return _format_personaldb_search_context(result)


async def _load_personaldb_full_text_context(
    personaldb_url: str,
    *,
    user_id: str,
    file_ids: list[str],
    max_file_chars: int = 40_000,
    max_total_chars: int = 120_000,
) -> str:
    """
    从 personaldb 拉取指定 file_ids 的全文内容（不经检索），并拼接为可注入 prompt 的上下文。

    约束（防止 prompt 过大）：
    - 单文件最多 max_file_chars 字符
    - 总计最多 max_total_chars 字符
    - 超限截断时在上下文中标注“已截断”
    """
    if not file_ids:
        return ""

    def _build_prefix(index: int, title: str, meta_line: str, notes: list[str]) -> str:
        lines = [f"[{index}] {title}"]
        if meta_line:
            lines.append(meta_line)
        if notes:
            lines.append("（" + "；".join([x for x in notes if x]) + "）")
        return "\n".join(lines).rstrip() + "\n"

    blocks: list[str] = []
    total_chars = 0  # 仅统计返回字符串长度（含分隔空行）

    async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(20.0)) as client:
        for fid in file_ids:
            if total_chars >= max_total_chars:
                break

            url = f"{personaldb_url}/files/{user_id}/{fid}/content"
            try:
                resp = await client.get(url)
            except Exception as exc:
                logger.info("personaldb /files/.../content 调用失败：%s", exc)
                continue

            if resp.status_code == 404:
                continue
            if resp.status_code >= 400:
                logger.info("[personaldb %s] %s", resp.status_code, resp.text)
                continue

            try:
                payload = resp.json()
            except ValueError:
                logger.info("personaldb /files/.../content 返回非 JSON：%s", resp.text)
                continue

            if not isinstance(payload, dict):
                continue

            content = payload.get("content")
            if not isinstance(content, str):
                continue
            text = content.strip()
            if not text:
                continue

            file_name = str(payload.get("file_name") or payload.get("fileName") or "").strip()
            file_type = str(payload.get("file_type") or payload.get("fileType") or "").strip()

            title = file_name or fid
            notes: list[str] = []

            if len(text) > max_file_chars:
                text = text[:max_file_chars].rstrip() + "…"
                notes.append(f"已按单文件上限截断（{max_file_chars} chars）")

            meta_bits = [f"file_id={fid}"]
            if file_type:
                meta_bits.append(f"type={file_type}")
            meta_line = " / ".join(meta_bits).strip()

            index = len(blocks) + 1

            # 预留分隔空行：除首块外，每块前面会有 "\n\n"
            remaining_total = max_total_chars - total_chars
            if blocks:
                remaining_total -= 2
            if remaining_total <= 0:
                break

            prefix = _build_prefix(index, title, meta_line, notes)
            remaining_for_content = remaining_total - len(prefix)
            if remaining_for_content <= 0:
                break

            if len(text) > remaining_for_content:
                if "已按总长度上限截断" not in notes:
                    notes.append("已按总长度上限截断")
                prefix = _build_prefix(index, title, meta_line, notes)
                remaining_for_content = remaining_total - len(prefix)
                if remaining_for_content <= 0:
                    break
                if len(text) > remaining_for_content:
                    # 至少留 1 个字符给省略号
                    cut = max(0, remaining_for_content - 1)
                    text = text[:cut].rstrip() + "…"

            block = (prefix + text).strip()
            if blocks:
                total_chars += 2
            blocks.append(block)
            total_chars += len(block)

    return "\n\n".join(blocks).strip()


async def _build_personaldb_kb_contexts(
    personaldb_url: str,
    *,
    user_id: str,
    query: str,
    kb_file_ids: list[str],
    rag_topk: int = 5,
) -> tuple[str, str]:
    """
    给定“用户当前选中的 kb_file_ids”，按约定构建两类上下文：
    - full_context：gen: 全文注入（不经检索）
    - rag_context：非 gen: 走 /search 的检索片段
    """
    full_ids, rag_ids = _split_kb_file_ids(kb_file_ids)
    full_context = ""
    rag_context = ""
    if rag_ids:
        rag_context = await _search_personaldb_kb_context(
            personaldb_url,
            user_id=str(user_id),
            query=str(query),
            kb_file_ids=rag_ids,
            topk=int(rag_topk),
        )
    if full_ids:
        full_context = await _load_personaldb_full_text_context(
            personaldb_url,
            user_id=str(user_id),
            file_ids=full_ids,
        )
    return full_context, rag_context


def _kb_ok(data):
    return {"ok": True, "data": data}


def _kb_error(code: str, message: str, status_code: int = 500):
    return JSONResponse(
        status_code=status_code,
        content={"ok": False, "error": {"code": code, "message": message}},
    )


def _kb_safe_filename(name: str) -> str:
    # 避免 header 注入与路径穿越
    safe = (name or "").strip().replace("\\", "_").replace("/", "_")
    safe = safe.replace("\r", "_").replace("\n", "_").replace("\t", "_")
    return safe


def _kb_build_export_filename(file_name: str, file_type: str, file_id: str) -> str:
    base = _kb_safe_filename(file_name) or _kb_safe_filename(file_id) or "export"
    base = base or "export"

    lower = base.lower()
    if "." in Path(base).name:
        # 已带后缀：若不是可读文本后缀，则追加 .md
        if lower.endswith((".md", ".txt")):
            return base
        return f"{base}.md"

    ext = (file_type or "").strip().lower().lstrip(".")
    if ext in {"md", "markdown"}:
        return f"{base}.md"
    if ext in {"txt", "text"}:
        return f"{base}.txt"
    if ext and ext not in {"unknown"}:
        return f"{base}.{ext}.md"
    return f"{base}.md"
