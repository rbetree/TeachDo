from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Mapping

# =========================
# TeachDo 运行期设置持久化
# =========================
#
# 目标：
# - 允许通过前端“设置”页写入本地配置，而不是必须手改 `.env`
# - 以 `var/settings.json` 作为持久化载体（默认 gitignore）
# - 对外仍以环境变量作为“最终读取接口”，尽量减少对现有代码侵入
#
# 优先级（同一进程内）：
# 1) 系统环境变量（os.environ 已存在的值）
# 2) var/settings.json（仅补齐或按需覆盖）
# 3) .env（若服务仍加载；但在我们“先应用 settings，再 load .env”时，settings 可覆盖 .env）


_FILE_LOCK = threading.Lock()


ALLOWED_SETTINGS_ENV_KEYS: set[str] = {
    # Outline
    "OUTLINE_TYPE",
    "OUTLINE_BASE_URL",
    "OUTLINE_API_KEY",
    "OUTLINE_MODEL",
    # PPT writer / checker
    "PPT_WRITER_TYPE",
    "PPT_WRITER_BASE_URL",
    "PPT_WRITER_API_KEY",
    "PPT_WRITER_MODEL",
    "PPT_CHECKER_TYPE",
    "PPT_CHECKER_BASE_URL",
    "PPT_CHECKER_API_KEY",
    "PPT_CHECKER_MODEL",
    # Embedding
    "EMBEDDING_TYPE",
    "EMBEDDING_BASE_URL",
    "EMBEDDING_API_KEY",
    "EMBEDDING_MODEL",
    "EMBEDDING_TIMEOUT_S",
    "EMBEDDING_MAX_RETRIES",
    "EMBEDDING_DIM",
    # Runtime behavior
    "USE_MINERU",
    "USE_CHART",
    "OUTLINE_STREAMING",
    "CONTENT_STREAMING",
    # Runtime paths
    "TEACHDO_CACHE_DIR",
    "TEACHDO_TMP_DIR",
    "TEACHDO_LOG_DIR",
    # Optional integrations
    "PEXELS_API_KEY",
    # Service endpoints
    "OUTLINE_API",
    "CONTENT_API",
    "PERSONAL_DB",
    # Bind host & ports (used by start.py)
    "HOST",
    "MAIN_API_PORT",
    "OUTLINE_API_PORT",
    "CONTENT_API_PORT",
    "FRONTEND_PORT",
    # Proxy
    "HTTP_PROXY",
    "HTTPS_PROXY",
}


SECRET_ENV_KEYS: set[str] = {
    "OUTLINE_API_KEY",
    "PPT_WRITER_API_KEY",
    "PPT_CHECKER_API_KEY",
    "EMBEDDING_API_KEY",
    "PEXELS_API_KEY",
}


DEFAULT_SETTINGS_ENV: dict[str, Any] = {
    # 与根目录 env_template.txt 的默认值保持一致（Key 默认留空更安全）
    "OUTLINE_TYPE": "openai",
    "OUTLINE_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "OUTLINE_API_KEY": "",
    "OUTLINE_MODEL": "qwen-turbo-latest",
    "PPT_WRITER_TYPE": "openai",
    "PPT_WRITER_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "PPT_WRITER_API_KEY": "",
    "PPT_WRITER_MODEL": "qwen-turbo-latest",
    "PPT_CHECKER_TYPE": "openai",
    "PPT_CHECKER_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "PPT_CHECKER_API_KEY": "",
    "PPT_CHECKER_MODEL": "qwen-turbo-latest",
    "EMBEDDING_TYPE": "openai",
    "EMBEDDING_BASE_URL": "https://ark.cn-beijing.volces.com/api/v3",
    "EMBEDDING_API_KEY": "",
    "EMBEDDING_MODEL": "doubao-embedding-text-240715",
    "EMBEDDING_TIMEOUT_S": None,
    "EMBEDDING_MAX_RETRIES": None,
    "EMBEDDING_DIM": None,
    # internal endpoints（本地默认）
    "OUTLINE_API": "http://127.0.0.1:10001",
    "CONTENT_API": "http://127.0.0.1:10011",
    "PERSONAL_DB": "http://127.0.0.1:9100",
    # 服务绑定地址与端口（start.py 使用）
    "HOST": "127.0.0.1",
    "MAIN_API_PORT": 6800,
    "OUTLINE_API_PORT": 10001,
    "CONTENT_API_PORT": 10011,
    "FRONTEND_PORT": 5174,
    # 代理默认关闭
    "HTTP_PROXY": "",
    "HTTPS_PROXY": "",
    # 运行行为
    "USE_MINERU": False,
    "USE_CHART": True,
    "OUTLINE_STREAMING": True,
    "CONTENT_STREAMING": False,
    # 运行目录（默认不提交到 git）
    "TEACHDO_CACHE_DIR": "var/cache",
    "TEACHDO_TMP_DIR": "var/tmp",
    "TEACHDO_LOG_DIR": "logs",
    # 可选：图片素材搜索（Pexels）
    "PEXELS_API_KEY": "",
}


def _find_repo_root(start: Path) -> Path:
    """
    向上查找项目根目录：
    - 优先命中 `.git/` 或 `env_template.txt`
    - 若不存在（例如仅拷贝了单服务目录），退化为包含当前文件的目录
    """
    start_dir = start if start.is_dir() else start.parent
    fallback_root: Path | None = None

    current = start_dir
    while True:
        if (current / ".git").exists() or (current / "env_template.txt").exists():
            return current
        if fallback_root is None and (current / "backend").exists():
            fallback_root = current

        parent = current.parent
        if parent == current:
            break
        current = parent

    return fallback_root or start_dir


def settings_file_path(repo_root: Path | None = None) -> Path:
    overridden = (os.environ.get("TEACHDO_SETTINGS_FILE") or "").strip()
    if overridden:
        return Path(overridden).expanduser()
    root = repo_root or _find_repo_root(Path(__file__).resolve())
    return root / "var" / "settings.json"


def _normalize_env_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def read_settings_env(path: Path | None = None) -> dict[str, Any]:
    """
    读取 settings.json（仅保留白名单键）。
    - 文件不存在：返回空 dict
    - 文件损坏或结构不合法：返回空 dict（避免影响服务启动）
    """
    file_path = path or settings_file_path()
    if not file_path.exists():
        return {}

    try:
        raw = file_path.read_text(encoding="utf-8")
        data = json.loads(raw or "{}")
        if not isinstance(data, dict):
            return {}
        cleaned: dict[str, Any] = {}
        for k, v in data.items():
            key = str(k)
            if key not in ALLOWED_SETTINGS_ENV_KEYS:
                continue
            cleaned[key] = v
        return cleaned
    except Exception:
        return {}


def write_settings_env(env: Mapping[str, Any], path: Path | None = None) -> None:
    """
    原子写入 settings.json（仅写入白名单键）。
    """
    file_path = path or settings_file_path()
    file_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {}
    for k, v in env.items():
        if k not in ALLOWED_SETTINGS_ENV_KEYS:
            continue
        # 避免把“空的 secret”写入文件导致覆盖 .env
        if k in SECRET_ENV_KEYS and not str(v or "").strip():
            continue
        payload[str(k)] = v

    tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)

    with _FILE_LOCK:
        tmp_path.write_text(content + "\n", encoding="utf-8")
        tmp_path.replace(file_path)


def apply_settings_to_environ(
    env: Mapping[str, Any],
    *,
    overwrite: bool = False,
) -> None:
    """
    将 settings.json 的内容应用到 os.environ。

    - overwrite=False：不覆盖既有环境变量（系统环境变量优先）
    - overwrite=True ：覆盖同名环境变量（用于“设置页保存后立即生效”场景）
    """
    for key, raw_value in env.items():
        if key not in ALLOWED_SETTINGS_ENV_KEYS:
            continue
        # 避免“空的 secret”覆盖后续 .env / 系统环境变量
        if key in SECRET_ENV_KEYS and not str(raw_value or "").strip():
            continue
        if not overwrite and key in os.environ:
            continue
        os.environ[key] = _normalize_env_value(raw_value)


def load_and_apply_settings(*, overwrite: bool = False, repo_root: Path | None = None) -> dict[str, Any]:
    """
    读取 settings.json 并应用到 os.environ，返回读取到的配置。
    """
    env = read_settings_env(settings_file_path(repo_root))
    apply_settings_to_environ(env, overwrite=overwrite)
    return env


def merged_effective_env(*, defaults: Mapping[str, Any] | None = None) -> dict[str, str]:
    """
    获取“用于展示/编辑”的有效配置：
    - defaults（建议传 DEFAULT_SETTINGS_ENV）作为兜底
    - 再叠加当前 os.environ
    """
    base: dict[str, str] = {}
    if defaults:
        for k, v in defaults.items():
            if k not in ALLOWED_SETTINGS_ENV_KEYS:
                continue
            base[k] = _normalize_env_value(v)

    for k in ALLOWED_SETTINGS_ENV_KEYS:
        if k in os.environ:
            base[k] = os.environ[k]
    return base


def is_truthy_env(value: str | None) -> bool:
    v = (value or "").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}
