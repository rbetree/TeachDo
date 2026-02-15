import asyncio
import json
import re
import os
from pathlib import Path
from dotenv import dotenv_values
from fastapi import FastAPI, UploadFile, File
import time
import logging
from pydantic import BaseModel
import uuid
import httpx
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import UploadFile, File, HTTPException, Form
from fastapi import FastAPI, HTTPException, Query, Request, Response
try:
    # 兼容在 `backend/main_api` 目录下直接运行（例如 `uvicorn main:app`）
    from outline_client import A2AOutlineClientWrapper
    from content_client import A2AContentClientWrapper
except ImportError:  # pragma: no cover - 兼容以包方式导入（用于单元测试等）
    from backend.main_api.outline_client import A2AOutlineClientWrapper
    from backend.main_api.content_client import A2AContentClientWrapper

logger = logging.getLogger(__name__)

def _find_repo_root(start: Path) -> Path:
    """
    向上查找项目根目录：
    - 优先命中 `.git/` 或 `env_template.txt`
    - 若不存在（例如 docker 镜像只拷贝了单服务目录），退化为包含 `main.py` 的目录
    """
    start_dir = start if start.is_dir() else start.parent
    fallback_service_root: Path | None = None

    current = start_dir
    while True:
        if (current / ".git").exists() or (current / "env_template.txt").exists():
            return current
        if fallback_service_root is None and (current / "main.py").exists():
            fallback_service_root = current

        parent = current.parent
        if parent == current:
            break
        current = parent

    return fallback_service_root or Path.cwd()


def _load_env_files() -> None:
    """
    统一环境变量加载优先级（不覆盖系统环境变量）：
    1) 项目根目录 `.env`
    2) 当前服务目录 `.env`（可选覆盖）
    """
    merged: dict[str, str] = {}

    repo_root = _find_repo_root(Path(__file__).resolve())
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

OUTLINE_API = os.environ.get("OUTLINE_API", f"http://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('OUTLINE_API_PORT', '10001')}")
CONTENT_API = os.environ.get("CONTENT_API", f"http://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('CONTENT_API_PORT', '10011')}")
app = FastAPI()

# Allow CORS for the frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AipptRequest(BaseModel):
    content: str
    language: str
    model: str
    stream: bool

async def iter_outline_text_chunks(prompt: str, language: str = "chinese"):
    """
    抽象出大纲 Agent 的文本增量迭代器：
    - 只关心 chunk_data["type"] == "text" 的部分
    - 统一日志与空文本过滤
    """
    outline_wrapper = A2AOutlineClientWrapper(session_id=uuid.uuid4().hex, agent_url=OUTLINE_API)
    async for chunk_data in outline_wrapper.generate(prompt, language=language):
        logger.info(f"生成大纲输出的chunk_data: {chunk_data}")
        chunk_type = chunk_data.get("type")

        if chunk_type == "text":
            text = chunk_data.get("text") or ""
            if not text:
                continue
            yield text


async def stream_agent_response(prompt: str, language: str = "chinese"):
    """
    兼容旧用法：返回纯文本增量（非 SSE）。
    目前仅用于 /tools/aippt_by_id 这类内部串联场景。
    """
    async for text in iter_outline_text_chunks(prompt, language):
        yield text


async def stream_outline_sse(prompt: str, language: str = "chinese"):
    """
    将大纲 Agent 的响应以 SSE 形式向前端流式输出。
    - media_type: text/event-stream
    - 每个 chunk_data["text"] 作为一条 SSE 事件发送
    - 如 text 内部包含换行，按 SSE 规范拆成多行 data:
    - 结束时发送 data: [DONE]
    """
    async for text in iter_outline_text_chunks(prompt, language):
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


def _encode_sse_data(payload: str) -> bytes:
    """
    将任意文本安全编码为 SSE data 事件，兼容多行内容。
    """
    if payload is None:
        payload = ""

    lines = payload.splitlines()
    has_trailing_newline = payload.endswith("\n")

    if not lines:
        return b"data:\n\n"

    chunks: list[bytes] = []
    for line in lines:
        chunks.append(f"data: {line}\n".encode("utf-8"))
    if has_trailing_newline:
        chunks.append(b"data:\n")
    chunks.append(b"\n")
    return b"".join(chunks)


@app.post("/tools/aippt_outline")
async def aippt_outline(request: AipptRequest):
    assert request.stream, "只支持流式的返回大纲"
    logger.info(f"前端*outline***=====>用户输入：{request.language}")
    async def event_generator():
        async for chunk in stream_outline_sse(request.content, request.language):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/tools/aippt_outline_unified")
async def aippt_outline_unified(
    content: str = Form(None),           # 主题文本（可选）
    file: UploadFile = File(None),       # 上传文件（可选）
    language: str = Form("chinese"),
    user_id: str = Form("default_user"),
    folder_id: int | str = Form(0),
    file_type: str | None = Form(None),
):
    """
    统一的大纲生成 API，支持两种模式：
    - 主题模式：只传 content，根据主题生成大纲
    - 文档模式：传 file，解析文档后生成大纲
    - 混合模式：同时传 content 和 file，以文档为主，主题作为补充上下文
    """
    has_content = content and content.strip()
    has_file = file is not None

    # 主题是必填的
    if not has_content:
        raise HTTPException(status_code=400, detail="请提供主题")

    prompt = ""
    file_content = ""

    # 如果有文件，先解析文件内容
    if has_file:
        personaldb_api_url = os.getenv("PERSONAL_DB")
        if not personaldb_api_url:
            raise HTTPException(status_code=500, detail="PERSONAL_DB 未配置")

        # 生成 fileId
        file_id = str(int(time.time() * 1000))

        # 推断 fileType
        actual_file_type = file_type
        if not actual_file_type and file.filename and "." in file.filename:
            actual_file_type = file.filename.rsplit(".", 1)[-1]

        # 组装请求数据
        data = {
            "userId": str(user_id),
            "fileId": file_id,
            "folderId": str(folder_id),
        }
        if actual_file_type:
            data["fileType"] = actual_file_type

        # 读取文件内容
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="文件内容为空")

        files_payload = {
            "file": (
                file.filename or "uploaded_file",
                file_bytes,
                file.content_type or "application/octet-stream",
            )
        }

        upload_url = f"{personaldb_api_url.rstrip('/')}/upload/"

        # 内部服务调用（personaldb）不应受系统代理环境变量影响
        async with httpx.AsyncClient(trust_env=False) as client:
            try:
                resp = await client.post(
                    upload_url,
                    data=data,
                    files=files_payload,
                    timeout=360.0,
                )
                if resp.status_code >= 400:
                    logger.info(f"[personaldb {resp.status_code}] {resp.text}")
                    resp.raise_for_status()

                try:
                    result = resp.json()
                except ValueError:
                    raise HTTPException(status_code=502, detail=f"personaldb 返回的不是 JSON：{resp.text}")

                markdown_content = result.get("markdown_content")
                if markdown_content is None:
                    raise HTTPException(status_code=500, detail="personaldb 响应缺少 'markdown_content'")

                file_content = markdown_content

            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="Request to personaldb timed out.")
            except httpx.HTTPStatusError as exc:
                raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
            except httpx.RequestError as exc:
                raise HTTPException(status_code=500, detail=f"Error connecting to personaldb: {exc}")

    # 构建最终的 prompt
    if file_content:
        # 有文件时，结合主题和文件内容
        prompt = f"主题：{content.strip()}\n\n参考文档内容：\n{file_content}"
    else:
        # 纯主题模式
        prompt = content.strip()

    logger.info(f"统一大纲API*outline***=====>：language={language}, has_file={has_file}, has_content={has_content}")

    async def event_generator():
        async for chunk in stream_outline_sse(prompt, language):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/tools/aippt_outline_from_file")
async def aippt_outline_from_file(
    user_id: int|str = Form(...),
    file: UploadFile = File(None),  # 允许缺省，这样我们可以决定走 file 或 url
    url: str | None = Form(None),
    folder_id: int|str = Form(0),
    file_type: str | None = Form(None),
    language: str = Form("chinese"),  # 添加language参数，默认为chinese
):
    """
    对齐 personaldb 的 /upload/：
    - 必填: userId, fileId
    - 可选: folderId (默认0), fileType
    - file 与 url 互斥，至少一个
    """
    personaldb_api_url = os.getenv("PERSONAL_DB")
    if not personaldb_api_url:
        raise HTTPException(status_code=500, detail="PERSONAL_DB 未配置")

    # 互斥校验（与 personaldb 完全一致）
    has_file = file is not None
    has_url = bool(url and url.strip())

    # 生成 fileId（字符串更稳；personaldb 会 int()）
    file_id = str(int(time.time() * 1000))

    # 推断 fileType（当上传文件时且未显式传入）
    if has_file and not file_type:
        if file.filename and "." in file.filename:
            file_type = file.filename.rsplit(".", 1)[-1]
        else:
            file_type = "unknown"

    # 组装 multipart/form-data
    # 注意：即使是 url 分支，也仍用 multipart，personaldb 也能解析 form
    data = {
        "userId": str(user_id),
        "fileId": file_id,
        "folderId": str(folder_id),
    }
    if file_type:
        data["fileType"] = file_type
    if has_url:
        data["url"] = url.strip()

    files_payload = None
    if has_file:
        # 读取一次到内存，httpx 需要 (filename, bytes/obj, content_type)
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="文件内容为空")
        files_payload = {
            "file": (
                file.filename or "uploaded_file",
                file_bytes,
                file.content_type or "application/octet-stream",
            )
        }

    upload_url = f"{personaldb_api_url.rstrip('/')}/upload/"

    # 内部服务调用（personaldb）不应受系统代理环境变量影响
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            resp = await client.post(
                upload_url,
                data=data,
                files=files_payload,
                timeout=360.0,
            )
            # 不直接 raise，先打日志方便定位
            if resp.status_code >= 400:
                # 打印下游返回体，personaldb 对错误信息写得很清楚
                logger.info(f"[personaldb {resp.status_code}] {resp.text}")
                resp.raise_for_status()

            # personaldb 的处理函数最终会返回一个 JSON（你上游期望里要有 markdown_content）
            try:
                result = resp.json()
            except ValueError:
                raise HTTPException(status_code=502, detail=f"personaldb 返回的不是 JSON：{resp.text}")

            markdown_content = result.get("markdown_content")
            if markdown_content is None:
                raise HTTPException(status_code=500, detail="personaldb 响应缺少 'markdown_content'")
            logger.info(f"本地上传文件*outline***=====>：{ {'language': language} }")

            async def event_generator():
                async for chunk in stream_outline_sse(markdown_content, language):
                    yield chunk

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache, no-transform",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request to personaldb timed out.")
        except httpx.HTTPStatusError as exc:
            # 透传 personaldb 的错误详情，便于你在日志里看到具体字段问题
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Error connecting to personaldb: {exc}")

class AipptContentRequest(BaseModel):
    content: str
    language: str = "zh"  #默认中文
    sessionId: str = ""  # 当使用知识库时，需要根据用户的user_id查询对应的知识库
    generateFromUploadedFile: bool = False  # 是否从上传的文件中生成PPT内容
    generateFromWebSearch: bool = True  # 是否从网络搜索中生成PPT内容

async def stream_content_response(markdown_content: str, language, generateFromUploadedFile, generateFromWebSearch, user_id):
    match = re.search(r"(# .*)", markdown_content, flags=re.DOTALL)
    result = markdown_content[match.start():] if match else markdown_content
    logger.info(f"用户输入的markdown大纲是：{result}")

    content_wrapper = A2AContentClientWrapper(session_id=uuid.uuid4().hex, agent_url=CONTENT_API)

    search_engine = []
    if generateFromUploadedFile:
        search_engine.append("KnowledgeBaseSearch")
    if generateFromWebSearch:
        search_engine.append("DocumentSearch")

    metadata = {"user_id": user_id, "search_engine": search_engine, "language": language}
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
        logger.info("客户端已断开 /tools/aippt SSE 连接，提前结束流")
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

@app.post("/tools/aippt")
async def aippt_content(request: AipptContentRequest):
    markdown_content = request.content
    # 兼容旧字段名：如果 user_id 为空就用 sessionId
    user_id = getattr(request, "user_id", None) or getattr(request, "sessionId", None)

    async def event_generator():
        async for chunk in stream_content_response(
            markdown_content,
            language=request.language,
            generateFromUploadedFile=request.generateFromUploadedFile,
            generateFromWebSearch=request.generateFromWebSearch,
            user_id=user_id
        ):
            yield chunk

    # 关键：SSE 推荐这些头
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.get("/data/{filename}")
async def get_data(filename: str):
    file_path = os.path.join("./template", filename)
    return FileResponse(file_path)

@app.get("/templates")
async def get_templates():
    templates = [
        { "name": "红色通用", "id": "template_1", "cover": "/api/data/template_1.jpg" },
        { "name": "蓝色通用", "id": "template_2", "cover": "/api/data/template_2.jpg" },
        { "name": "紫色通用", "id": "template_3", "cover": "/api/data/template_3.jpg" },
        { "name": "莫兰迪配色", "id": "template_4", "cover": "/api/data/template_4.jpg" },
        # { "name": "图表", "id": "template_6", "cover": "/api/data/template_6.jpg" },
    ]

    return {"data": templates}

class AipptByIDRequest(BaseModel):
    id: str
    language: str = "chinese"  # 添加language字段，默认为chinese

async def aippt_file_id_streamer(id: str, language: str = "chinese"):
    """根据用户的已有的文件数据中的文件id来生成ppt
    id: 文件的id，例如论文的pmid
    """
    yield json.dumps({"type": "status", "message": "正在解析文件..."}, ensure_ascii=False) + '\n'
    paper_markdown = ""
    if not paper_markdown:
        yield json.dumps({"type": "status", "message": "没有找到该文章"}, ensure_ascii=False) + '\n'
        return
    personaldb_api_url = os.getenv("PERSONAL_DB")
    if not personaldb_api_url:
        raise HTTPException(status_code=500, detail="PERSONAL_DB 未配置")
    # 论文名称
    file_name = f"{id}.md"
    data = {
        "userId": id,
        "fileId": id,
        "folderId": 123,
        "fileType": "txt"
    }
    files = {"file": (file_name, paper_markdown, "text/plain")}
    upload_url = f"{personaldb_api_url.rstrip('/')}/upload/"
    response = httpx.post(upload_url, data=data, files=files, timeout=40.0)
    result = response.json()
    if not result.get("id"):
        yield json.dumps({"type": "status", "message": "论文向量化失败，请联系管理员"}, ensure_ascii=False) + '\n'
    yield json.dumps({"type": "status", "message": "正在生成大纲..."}, ensure_ascii=False) + '\n'
    outline = ""
    async for outline_trunk in stream_agent_response(paper_markdown, language):
        outline += outline_trunk
    yield json.dumps({"type": "status", "message": "大纲生成完毕，即将生成PPT..."}, ensure_ascii=False) + '\n'

    match = re.search(r"(# .*)", outline, flags=re.DOTALL)

    if match:
        result = outline[match.start():]
    else:
        result = outline
    logger.info(f"用户输入的markdown大纲是：{result}")
    content_wrapper = A2AContentClientWrapper(session_id=uuid.uuid4().hex, agent_url=CONTENT_API)
    # 传入不同的参数，使用不同的搜索,可以同时使用多个搜索
    search_engine = ["KnowledgeBaseSearch"]
    # 方便测试，这个已经在知识库中插入了对应的数据
    metadata = {"user_id": id, "search_engine": search_engine, "language": language}
    logger.info(f"aippt_by_id**=====>metadata数据为：{metadata}")
    async for chunk_data in content_wrapper.generate(user_question=result, metadata=metadata):
        logger.info(f"生成正文输出的chunk_data: {chunk_data}")
        if chunk_data["type"] == "text":
            slide = chunk_data["text"]
            yield slide + '\n'


@app.post("/tools/aippt_by_id")
async def aippt_by_id(request: AipptByIDRequest):
    return StreamingResponse(aippt_file_id_streamer(request.id, request.language), media_type="application/json; charset=utf-8")


@app.get("/files/{user_id}")
async def list_user_files(user_id: int):
    """
    列出指定用户的所有文件信息
    """
    personaldb_api_url = os.environ["PERSONAL_DB"]
    url = f"{personaldb_api_url}/files/{user_id}"

    # 内部服务调用（personaldb）不应受系统代理环境变量影响
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Error connecting to personaldb: {exc}")
        except httpx.HTTPStatusError as exc:
            # 转发下游服务的错误
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


@app.get("/proxy")
async def proxy(request: Request, url: str = Query(..., description="Target absolute URL")):
    """
    透明代理上游资源，转发部分请求头，透传关键响应头，并允许前端同源访问。
    适合图片/音视频等二进制内容。
    """
    HEADERS_TO_FORWARD = {"Range", "User-Agent"}  # 需要时可扩展
    HEADERS_TO_COPY = {
        "Content-Type",
        "Content-Length",
        "Content-Disposition",
        "Accept-Ranges",
        "ETag",
        "Last-Modified",
        "Cache-Control",
        "Expires",
    }
    forward_headers = {}
    for h in HEADERS_TO_FORWARD:
        v = request.headers.get(h)
        if v:
            forward_headers[h] = v

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            upstream = await client.get(url, headers=forward_headers)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream fetch error: {e!s}")

    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail="Upstream error")

    headers = {}
    for h in HEADERS_TO_COPY:
        if h in upstream.headers:
            headers[h] = upstream.headers[h]

    # 允许被前端同源读取
    headers["Access-Control-Allow-Origin"] = "*"
    # 给静态资源加简单缓存（按需调整）
    headers.setdefault("Cache-Control", "public, max-age=86400")

    return StreamingResponse(
        upstream.aiter_bytes(),
        status_code=upstream.status_code,
        headers=headers,
        media_type=upstream.headers.get("Content-Type"),
    )

@app.get("/healthz")
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    import sys
    import uvicorn

    # 允许在任意工作目录运行：确保可以导入 `backend.common.*`
    repo_root = _find_repo_root(Path(__file__).resolve())
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.common.logging_utils import build_uvicorn_log_config, apply_logging_config

    log_config = build_uvicorn_log_config()
    apply_logging_config(log_config)

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("MAIN_API_PORT", "6800"))
    uvicorn.run(app, host=host, port=port, log_config=log_config)
