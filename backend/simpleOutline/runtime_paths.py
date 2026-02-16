from __future__ import annotations

import os
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    """
    向上查找项目根目录：
    - 优先命中 `.git/` 或 `env_template.txt`（单仓库/monorepo 场景）
    - 若不存在（例如 docker 镜像只拷贝了单服务目录），退化为包含 `main_api.py` 的目录
    - 最后兜底为当前工作目录
    """
    start_dir = start if start.is_dir() else start.parent

    fallback_service_root: Path | None = None
    current = start_dir
    while True:
        if (current / ".git").exists() or (current / "env_template.txt").exists():
            return current
        if fallback_service_root is None and (current / "main_api.py").exists():
            fallback_service_root = current

        parent = current.parent
        if parent == current:
            break
        current = parent

    return fallback_service_root or Path.cwd()


def resolve_root_relative(path_str: str) -> Path:
    """
    将路径字符串解析为绝对路径：
    - 绝对路径：原样返回
    - 相对路径：以 repo root（或 service root）为基准
    """
    if not path_str:
        raise ValueError("path_str 不能为空")

    p = Path(path_str).expanduser()
    if p.is_absolute():
        return p

    root = find_repo_root(Path(__file__).resolve())
    return (root / p).resolve()


def get_cache_dir(service: str) -> Path:
    base = os.getenv("TEACHDO_CACHE_DIR", "var/cache")
    cache_dir = resolve_root_relative(base) / service
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_tmp_dir(service: str) -> Path:
    base = os.getenv("TEACHDO_TMP_DIR", "var/tmp")
    tmp_dir = resolve_root_relative(base) / service
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir


def get_log_file(service: str, filename: str) -> Path:
    base = os.getenv("TEACHDO_LOG_DIR", "logs")
    log_dir = resolve_root_relative(base)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 为了让 `logs/*.log` 能直接被 tail/采集，默认不使用子目录
    safe_name = filename.lstrip("/\\")
    return log_dir / f"{service}_{safe_name}"

