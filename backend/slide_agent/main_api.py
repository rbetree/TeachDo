import logging
import os
import sys
from pathlib import Path
from dotenv import dotenv_values

from slide_agent.runtime_paths import find_repo_root


def _load_env_files() -> None:
    """
    统一环境变量加载优先级（不覆盖系统环境变量）：
    0) var/settings.json（由“设置”页写入，可覆盖 .env）
    1) 项目根目录 `.env`
    2) 当前服务目录 `.env`（可选覆盖）
    """
    merged: dict[str, str] = {}

    repo_root = find_repo_root(Path(__file__).resolve())
    # 允许在 `backend/slide_agent` 目录下直接运行：确保可导入 backend.*
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # 先加载 settings.json，再加载 .env；从而实现 settings 覆盖 .env
    try:
        from backend.common.settings_store import load_and_apply_settings

        load_and_apply_settings(overwrite=False, repo_root=repo_root)
    except Exception:
        pass

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

# 允许在任意工作目录运行：确保可以导入 `backend.common.*`
_repo_root = find_repo_root(Path(__file__).resolve())
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# 加速 google-adk 冷启动：必须在任何 `google.adk.*` import 之前调用
try:
    from backend.common.adk_fast_import import patch_google_adk_imports

    patch_google_adk_imports()
except Exception:  # pragma: no cover - 极端场景下不影响服务启动
    pass

try:
    from backend.common.logging_utils import build_uvicorn_log_config, apply_logging_config
except Exception:  # pragma: no cover - 单服务打包场景可能不存在 common 模块
    build_uvicorn_log_config = None
    apply_logging_config = None

logger = logging.getLogger(__name__)

import click
import uvicorn
from adk_agent_executor import ADKAgentExecutor
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from starlette.routing import Route
from google.adk.agents.run_config import RunConfig,StreamingMode
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from starlette.middleware.cors import CORSMiddleware
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from starlette.responses import JSONResponse
from slide_agent.agent import root_agent

@click.command()
@click.option(
    "--host",
    "host",
    default=None,
    envvar="HOST",
    show_default="HOST 或 0.0.0.0",
    help="服务器绑定的主机名（命令行优先，其次读取环境变量 HOST）",
)
@click.option(
    "--port",
    "port",
    default=None,
    type=int,
    envvar="CONTENT_API_PORT",
    show_default="CONTENT_API_PORT 或 10011",
    help="服务器监听的端口号（命令行优先，其次读取环境变量 CONTENT_API_PORT）",
)
@click.option("--agent_url", "agent_url", default="", help="Agent Card 中对外展示和访问的地址")
def main(host, port, agent_url=""):
    log_config = None
    if build_uvicorn_log_config and apply_logging_config:
        log_config = build_uvicorn_log_config()
        apply_logging_config(log_config)
    else:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # 从环境变量读取配置，命令行参数优先
    if host is None:
        host = os.environ.get("HOST", "0.0.0.0")
    if port is None:
        port = int(os.environ.get("CONTENT_API_PORT", "10011"))

    # 每个小的Agent都流式的输出结果
    streaming = os.environ.get("CONTENT_STREAMING", "false").lower() == "true"
    show_agent = ["ControllerAgent"]  #哪个Agent会作为最后的ppt的Agent的输出（对应前端显示）
    agent_card_name = "Writter PPT Agent"
    agent_name = "writter_agent"
    agent_description = "An agent that can help writer ppt"
    skill = AgentSkill(
        id=agent_name,
        name=agent_name,
        description=agent_description,
        tags=["writter", "ppt"],
        examples=["writter ppt agent"],
    )
    # 注意⚠️：这里Agent使用流式的输出，但是LLM模型不使用流式的输出，因为LLM使用流式的输出，在split topic时Json解析出问题
    if not agent_url:
        agent_url = f"http://{host}:{port}/"
    agent_card = AgentCard(
        name=agent_card_name,
        description=agent_description,
        url=agent_url,
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )
    # mcptools = load_mcp_tools(mcp_config_path=mcp_config_path)
    runner = Runner(
        app_name=agent_card.name,
        agent=root_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )

    # 根据环境变量决定是否启用流式输出
    if streaming:
        logger.info("使用 SSE 流式输出模式")
        run_config = RunConfig(
            streaming_mode=StreamingMode.SSE,
            max_llm_calls=500
        )
    else:
        logger.info("使用普通输出模式")
        run_config = RunConfig(
            streaming_mode=StreamingMode.NONE,
            max_llm_calls=500
        )
    agent_executor = ADKAgentExecutor(runner, agent_card, run_config, show_agent)

    # 初始化请求处理器
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    # 构建A2A应用
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    app = a2a_app.build()

    # 健康检查：供 start.py 等启动器做 readiness 探针
    def healthz(request):  # noqa: ANN001 - Starlette handler
        return JSONResponse({"ok": True})

    app.add_route("/healthz", healthz, methods=["GET"])

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"服务启动中，监听地址: http://{host}:{port}")
    # 启动 uvicorn 服务器
    uvicorn.run(app, host=host, port=port, log_config=log_config)

if __name__ == "__main__":
    main()
