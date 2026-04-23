import uuid
import logging
from typing import Any

try:
    from outline_client import A2AOutlineClientWrapper
except ImportError:  # pragma: no cover - 兼容以包方式导入（用于单元测试等）
    from backend.main_api.outline_client import A2AOutlineClientWrapper

from backend.main_api.utils.common import _get_outline_api

logger = logging.getLogger(__name__)


async def iter_outline_text_chunks(
    prompt: str,
    language: str = "chinese",
    *,
    user_id: str = "default_user",
    metadata: dict[str, Any] | None = None,
):
    """
    抽象出大纲 Agent 的文本增量迭代器：
    - 只关心 chunk_data["type"] == "text" 的部分
    - 统一日志与空文本过滤
    """
    outline_wrapper = A2AOutlineClientWrapper(session_id=uuid.uuid4().hex, agent_url=_get_outline_api())
    async for chunk_data in outline_wrapper.generate(prompt, language=language, user_id=user_id, metadata=metadata):
        logger.info(f"生成大纲输出的chunk_data: {chunk_data}")
        chunk_type = chunk_data.get("type")

        if chunk_type == "text":
            text = chunk_data.get("text") or ""
            if not text:
                continue
            yield text


async def stream_outline_sse(
    prompt: str,
    language: str = "chinese",
    *,
    user_id: str = "default_user",
    metadata: dict[str, Any] | None = None,
):
    """
    将大纲 Agent 的响应以 SSE 形式向前端流式输出。
    - media_type: text/event-stream
    - 每个 chunk_data["text"] 作为一条 SSE 事件发送
    - 如 text 内部包含换行，按 SSE 规范拆成多行 data:
    - 结束时发送 data: [DONE]
    """
    async for text in iter_outline_text_chunks(prompt, language, user_id=user_id, metadata=metadata):
        # 按行拆分，遵守 SSE 规范：一条事件内多行 data:
        lines = text.splitlines()
        # 如果 text 以换行结尾，splitlines() 会吞掉末尾空行，这里记录一下
        has_trailing_newline = text.endswith("\n")

        if not lines:
            # 纯换行的情况，例如 text == "\n" 或 "\n\n"
            # 用一个空 data 行表示，然后前端按照事件边界追加换行
            yield b"data:\n\n"
        else:
            for line in lines:
                # 每一行作为一条 data: 行
                yield f"data: {line}\n".encode("utf-8")
            if has_trailing_newline:
                # 保留结尾换行：再补一个空 data 行
                yield b"data:\n"
        # 事件结束
        yield b"\n"

    # 目前前端不依赖 artifact/metadata/final 这几类事件，这里仅记录日志即可
    # 如果后续需要，可以在此扩展不同类型的 SSE 事件

    # 显式结束信号，前端据此收尾
    yield b"data: [DONE]\n\n"
