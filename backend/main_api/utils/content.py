import re
import json
import asyncio
import logging
import uuid
from typing import Any

try:
    from content_client import A2AContentClientWrapper
except ImportError:  # pragma: no cover - 兼容以包方式导入（用于单元测试等）
    from backend.main_api.content_client import A2AContentClientWrapper

from backend.main_api.utils.common import _get_content_api
from backend.main_api.utils.common import _encode_sse_data
from backend.common.course_outputs_injection import (
    COURSE_OUTPUTS_START_MARKER,
    build_course_outputs_injection_markdown,
)

logger = logging.getLogger(__name__)


async def stream_content_response(
    markdown_content: str,
    language,
    generateFromUploadedFile,
    generateFromWebSearch,
    user_id,
    generateWithImages: bool = False,
    kb_folder_ids: list[int] | None = None,
    kb_file_ids: list[str] | None = None,
):
    match = re.search(r"(# .*)", markdown_content, flags=re.DOTALL)
    result = markdown_content[match.start():] if match else markdown_content
    logger.info(f"用户输入的markdown大纲是：{result}")

    content_wrapper = A2AContentClientWrapper(session_id=uuid.uuid4().hex, agent_url=_get_content_api())

    search_engine = []
    if generateFromUploadedFile:
        search_engine.append("KnowledgeBaseSearch")
    if generateFromWebSearch:
        search_engine.append("DocumentSearch")
    # 联网配图：由 Writer 直接调用 SearchImage 决定 query（失败时服务端再做兜底注入）
    if bool(generateWithImages) and "SearchImage" not in search_engine:
        search_engine.append("SearchImage")

    image_source = "network" if bool(generateWithImages) else "preset"
    metadata = {
        "user_id": user_id,
        "search_engine": search_engine,
        "language": language,
        "generate_with_images": bool(generateWithImages),
        "image_source": image_source,
    }
    if kb_folder_ids:
        metadata["kb_folder_ids"] = kb_folder_ids
    if kb_file_ids:
        metadata["kb_file_ids"] = kb_file_ids
    logger.info(f"前端*内容**=====>metadata数据为：{metadata}")

    last_flush = asyncio.get_event_loop().time()

    try:
        async for chunk_data in content_wrapper.generate(user_question=result, metadata=metadata):
            logger.info(f"生成正文输出的chunk_data: {chunk_data}")

            # 心跳：每10秒发一次注释，避免某些代理断连接
            now = asyncio.get_event_loop().time()
            if now - last_flush > 10:
                yield b": keep-alive\n\n"
                last_flush = now

            chunk_type = chunk_data.get("type")
            if chunk_type == "text":
                # 注意：每条 SSE 事件以空行结束
                payload = chunk_data.get("text", "")
                yield _encode_sse_data(payload)
            elif chunk_type in {"error", "final"}:
                # 返回结构化事件，便于前端/日志诊断
                payload = json.dumps(chunk_data, ensure_ascii=False)
                yield _encode_sse_data(payload)
    except asyncio.CancelledError:
        logger.info("客户端已断开 PPT 内容 SSE 连接，提前结束流")
        raise
    except Exception as e:
        logger.error("内容生成流异常: %s", e, exc_info=True)
        payload = json.dumps(
            {
                "type": "error",
                "text": f"内容生成中断：{e}",
                "author": "system",
            },
            ensure_ascii=False,
        )
        yield _encode_sse_data(payload)
    finally:
        # 显式结束信号（前端可据此收尾）
        yield b"data: [DONE]\n\n"


def _inject_markdown_after_first_h1(markdown_content: str, injection_markdown: str) -> str:
    """
    将 injection_markdown 注入到 markdown_content 的首个 H1（# ）之后。
    目的：避免 stream_content_response 内部对首个 `#` 的截取逻辑把注入内容裁掉。
    """
    src = str(markdown_content or "")
    inj = (injection_markdown or "").strip()
    if not inj:
        return src
    if inj in src:
        return src

    lines = src.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith("# "):
            injection_lines = ["", *inj.splitlines(), ""]
            return "\n".join(lines[: idx + 1] + injection_lines + lines[idx + 1 :])
    return inj + "\n\n" + src
