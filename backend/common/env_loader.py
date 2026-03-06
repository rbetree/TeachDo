from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import dotenv_values


def ensure_repo_root_on_sys_path(repo_root: Path) -> None:
    """
    确保项目根目录在 sys.path 中。

    典型场景：
    - 开发者在 `backend/<service>` 目录下直接运行入口（例如 `python main.py`）
    - 需要 `import backend.*` 正常工作
    """
    root = str(repo_root)
    if root not in sys.path:
        sys.path.insert(0, root)


def load_env_files(
    *,
    repo_root: Path,
    service_dir: Path | None,
    apply_settings_json: bool = True,
    load_root_env: bool = True,
    load_service_env: bool = True,
) -> None:
    """
    统一环境变量加载规则（不覆盖系统环境变量）。

    优先级（高 → 低）：
    1) 系统环境变量（os.environ 已存在的值）
    2) var/settings.json（设置页写入；默认只补齐，不覆盖系统 env）
    3) 项目根目录 `.env`
    4) 服务目录 `.env`

    说明：
    - 为实现「settings.json 覆盖 .env」：必须先 apply settings，再加载 .env；
      且对 `.env` 的应用遵循“只补齐不覆盖”，从而避免 .env 覆盖 settings。
    - 任何 settings.json 读取异常都不应阻塞服务启动。
    """
    ensure_repo_root_on_sys_path(repo_root)

    if apply_settings_json:
        try:
            from backend.common.settings_store import load_and_apply_settings

            load_and_apply_settings(overwrite=False, repo_root=repo_root)
        except Exception:
            # settings.json 读取失败不应影响服务启动
            pass

    merged: dict[str, str] = {}

    if load_root_env:
        root_env = repo_root / ".env"
        if root_env.exists():
            merged.update({k: v for k, v in dotenv_values(root_env).items() if v is not None})

    if load_service_env and service_dir is not None:
        service_env = service_dir / ".env"
        if service_env.exists():
            merged.update({k: v for k, v in dotenv_values(service_env).items() if v is not None})

    for k, v in merged.items():
        if k not in os.environ:
            os.environ[k] = v

