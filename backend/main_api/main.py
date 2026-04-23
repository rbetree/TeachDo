import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


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


_repo_root = _find_repo_root(Path(__file__).resolve())
# 允许在 `backend/main_api` 目录下直接运行（例如 `python main.py`）：确保可导入 backend.*
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.common.env_loader import load_env_files
from backend.common.cors import get_cors_middleware_kwargs
from backend.common.settings_store import access_host_for_bind_host

load_env_files(repo_root=_repo_root, service_dir=Path(__file__).resolve().parent)

TEMPLATE_DIR = Path(__file__).resolve().parent / "template"


def _get_outline_api() -> str:
    return os.environ.get(
        "OUTLINE_API",
        f"http://{access_host_for_bind_host(os.environ.get('HOST', '127.0.0.1'))}:{os.environ.get('OUTLINE_API_PORT', '10001')}",
    )


def _get_content_api() -> str:
    return os.environ.get(
        "CONTENT_API",
        f"http://{access_host_for_bind_host(os.environ.get('HOST', '127.0.0.1'))}:{os.environ.get('CONTENT_API_PORT', '10011')}",
    )


app = FastAPI()

# settings API（允许在前端“设置”页写入 var/settings.json）
try:
    from backend.main_api.settings_api import register_settings_routes

    register_settings_routes(app)
except Exception:  # pragma: no cover - 单服务打包/裁剪场景允许缺失
    pass

# Allow CORS for the frontend development server
app.add_middleware(
    CORSMiddleware,
    **get_cors_middleware_kwargs(allow_credentials=True),
)

# Register routers
from backend.main_api.routes.outline import router as outline_router
from backend.main_api.routes.content import router as content_router
from backend.main_api.routes.assistant import router as assistant_router
from backend.main_api.routes.lesson import router as lesson_router
from backend.main_api.routes.kb import router as kb_router
from backend.main_api.routes.artifacts import router as artifacts_router
from backend.main_api.routes.proxy import router as proxy_router
from backend.main_api.routes.files import router as files_router
from backend.main_api.routes.health import router as health_router

app.include_router(outline_router)
app.include_router(content_router)
app.include_router(assistant_router)
app.include_router(lesson_router)
app.include_router(kb_router)
app.include_router(artifacts_router)
app.include_router(proxy_router)
app.include_router(files_router)
app.include_router(health_router)


if __name__ == "__main__":
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
