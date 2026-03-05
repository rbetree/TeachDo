from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.common.settings_store import (
    DEFAULT_SETTINGS_ENV,
    SECRET_ENV_KEYS,
    apply_settings_to_environ,
    merged_effective_env,
    read_settings_env,
    settings_file_path,
    write_settings_env,
    is_truthy_env,
)


_router = APIRouter(tags=["settings"])


class UiSettingsPayload(BaseModel):
    # LLM
    outlineType: str | None = None
    outlineBaseUrl: str | None = None
    outlineModel: str | None = None
    outlineApiKey: str | None = Field(default=None, description="留空表示不修改")

    pptWriterType: str | None = None
    pptWriterBaseUrl: str | None = None
    pptWriterModel: str | None = None
    pptWriterApiKey: str | None = Field(default=None, description="留空表示不修改")

    pptCheckerType: str | None = None
    pptCheckerBaseUrl: str | None = None
    pptCheckerModel: str | None = None
    pptCheckerApiKey: str | None = Field(default=None, description="留空表示不修改")

    embeddingType: str | None = None
    embeddingBaseUrl: str | None = None
    embeddingModel: str | None = None
    embeddingApiKey: str | None = Field(default=None, description="留空表示不修改")
    embeddingTimeoutS: str | None = None
    embeddingMaxRetries: str | None = None
    embeddingDim: str | None = None

    # Service endpoints + proxy
    outlineApi: str | None = None
    contentApi: str | None = None
    personalDb: str | None = None
    httpProxy: str | None = None
    httpsProxy: str | None = None
    pexelsApiKey: str | None = Field(default=None, description="留空表示不修改")

    # runtime behavior
    useChart: bool | None = None
    outlineStreaming: bool | None = None
    contentStreaming: bool | None = None
    useMineru: bool | None = None

    # runtime paths
    teachdoCacheDir: str | None = None
    teachdoTmpDir: str | None = None
    teachdoLogDir: str | None = None

    # bind host & ports (used by start.py)
    host: str | None = None
    mainApiPort: str | None = None
    outlineApiPort: str | None = None
    contentApiPort: str | None = None
    frontendPort: str | None = None


_UI_TO_ENV: dict[str, str] = {
    "outlineType": "OUTLINE_TYPE",
    "outlineBaseUrl": "OUTLINE_BASE_URL",
    "outlineModel": "OUTLINE_MODEL",
    "outlineApiKey": "OUTLINE_API_KEY",
    "pptWriterType": "PPT_WRITER_TYPE",
    "pptWriterBaseUrl": "PPT_WRITER_BASE_URL",
    "pptWriterModel": "PPT_WRITER_MODEL",
    "pptWriterApiKey": "PPT_WRITER_API_KEY",
    "pptCheckerType": "PPT_CHECKER_TYPE",
    "pptCheckerBaseUrl": "PPT_CHECKER_BASE_URL",
    "pptCheckerModel": "PPT_CHECKER_MODEL",
    "pptCheckerApiKey": "PPT_CHECKER_API_KEY",
    "embeddingType": "EMBEDDING_TYPE",
    "embeddingBaseUrl": "EMBEDDING_BASE_URL",
    "embeddingModel": "EMBEDDING_MODEL",
    "embeddingApiKey": "EMBEDDING_API_KEY",
    "embeddingTimeoutS": "EMBEDDING_TIMEOUT_S",
    "embeddingMaxRetries": "EMBEDDING_MAX_RETRIES",
    "embeddingDim": "EMBEDDING_DIM",
    "outlineApi": "OUTLINE_API",
    "contentApi": "CONTENT_API",
    "personalDb": "PERSONAL_DB",
    "httpProxy": "HTTP_PROXY",
    "httpsProxy": "HTTPS_PROXY",
    "pexelsApiKey": "PEXELS_API_KEY",
    "useChart": "USE_CHART",
    "outlineStreaming": "OUTLINE_STREAMING",
    "contentStreaming": "CONTENT_STREAMING",
    "useMineru": "USE_MINERU",
    "teachdoCacheDir": "TEACHDO_CACHE_DIR",
    "teachdoTmpDir": "TEACHDO_TMP_DIR",
    "teachdoLogDir": "TEACHDO_LOG_DIR",
    "host": "HOST",
    "mainApiPort": "MAIN_API_PORT",
    "outlineApiPort": "OUTLINE_API_PORT",
    "contentApiPort": "CONTENT_API_PORT",
    "frontendPort": "FRONTEND_PORT",
}


def _mask_secrets_flags(effective_env: dict[str, str]) -> dict[str, bool]:
    return {
        "outlineApiKey": bool((effective_env.get("OUTLINE_API_KEY") or "").strip()),
        "pptWriterApiKey": bool((effective_env.get("PPT_WRITER_API_KEY") or "").strip()),
        "pptCheckerApiKey": bool((effective_env.get("PPT_CHECKER_API_KEY") or "").strip()),
        "embeddingApiKey": bool((effective_env.get("EMBEDDING_API_KEY") or "").strip()),
        "pexelsApiKey": bool((effective_env.get("PEXELS_API_KEY") or "").strip()),
    }


def _build_ui_config(effective_env: dict[str, str]) -> dict[str, Any]:
    # 统一从 effective_env 读取（已经包含 defaults + os.environ）
    return {
        "outlineType": effective_env.get("OUTLINE_TYPE", DEFAULT_SETTINGS_ENV["OUTLINE_TYPE"]),
        "outlineBaseUrl": effective_env.get("OUTLINE_BASE_URL", DEFAULT_SETTINGS_ENV["OUTLINE_BASE_URL"]),
        "outlineModel": effective_env.get("OUTLINE_MODEL", DEFAULT_SETTINGS_ENV["OUTLINE_MODEL"]),
        "outlineApiKey": "",  # 不回传 secret
        "pptWriterType": effective_env.get("PPT_WRITER_TYPE", DEFAULT_SETTINGS_ENV["PPT_WRITER_TYPE"]),
        "pptWriterBaseUrl": effective_env.get("PPT_WRITER_BASE_URL", DEFAULT_SETTINGS_ENV["PPT_WRITER_BASE_URL"]),
        "pptWriterModel": effective_env.get("PPT_WRITER_MODEL", DEFAULT_SETTINGS_ENV["PPT_WRITER_MODEL"]),
        "pptWriterApiKey": "",
        "pptCheckerType": effective_env.get("PPT_CHECKER_TYPE", DEFAULT_SETTINGS_ENV["PPT_CHECKER_TYPE"]),
        "pptCheckerBaseUrl": effective_env.get("PPT_CHECKER_BASE_URL", DEFAULT_SETTINGS_ENV["PPT_CHECKER_BASE_URL"]),
        "pptCheckerModel": effective_env.get("PPT_CHECKER_MODEL", DEFAULT_SETTINGS_ENV["PPT_CHECKER_MODEL"]),
        "pptCheckerApiKey": "",
        "embeddingType": effective_env.get("EMBEDDING_TYPE", DEFAULT_SETTINGS_ENV["EMBEDDING_TYPE"]),
        "embeddingBaseUrl": effective_env.get("EMBEDDING_BASE_URL", DEFAULT_SETTINGS_ENV["EMBEDDING_BASE_URL"]),
        "embeddingModel": effective_env.get("EMBEDDING_MODEL", DEFAULT_SETTINGS_ENV["EMBEDDING_MODEL"]),
        "embeddingApiKey": "",
        "embeddingTimeoutS": effective_env.get("EMBEDDING_TIMEOUT_S", ""),
        "embeddingMaxRetries": effective_env.get("EMBEDDING_MAX_RETRIES", ""),
        "embeddingDim": effective_env.get("EMBEDDING_DIM", ""),
        "outlineApi": effective_env.get("OUTLINE_API", DEFAULT_SETTINGS_ENV["OUTLINE_API"]),
        "contentApi": effective_env.get("CONTENT_API", DEFAULT_SETTINGS_ENV["CONTENT_API"]),
        "personalDb": effective_env.get("PERSONAL_DB", DEFAULT_SETTINGS_ENV["PERSONAL_DB"]),
        "httpProxy": effective_env.get("HTTP_PROXY", ""),
        "httpsProxy": effective_env.get("HTTPS_PROXY", ""),
        "pexelsApiKey": "",
        "useChart": is_truthy_env(effective_env.get("USE_CHART")),
        "outlineStreaming": is_truthy_env(effective_env.get("OUTLINE_STREAMING")),
        "contentStreaming": is_truthy_env(effective_env.get("CONTENT_STREAMING")),
        "useMineru": is_truthy_env(effective_env.get("USE_MINERU")),
        "teachdoCacheDir": effective_env.get("TEACHDO_CACHE_DIR", DEFAULT_SETTINGS_ENV["TEACHDO_CACHE_DIR"]),
        "teachdoTmpDir": effective_env.get("TEACHDO_TMP_DIR", DEFAULT_SETTINGS_ENV["TEACHDO_TMP_DIR"]),
        "teachdoLogDir": effective_env.get("TEACHDO_LOG_DIR", DEFAULT_SETTINGS_ENV["TEACHDO_LOG_DIR"]),
        "host": effective_env.get("HOST", DEFAULT_SETTINGS_ENV["HOST"]),
        "mainApiPort": effective_env.get("MAIN_API_PORT", str(DEFAULT_SETTINGS_ENV["MAIN_API_PORT"])),
        "outlineApiPort": effective_env.get("OUTLINE_API_PORT", str(DEFAULT_SETTINGS_ENV["OUTLINE_API_PORT"])),
        "contentApiPort": effective_env.get("CONTENT_API_PORT", str(DEFAULT_SETTINGS_ENV["CONTENT_API_PORT"])),
        "frontendPort": effective_env.get("FRONTEND_PORT", str(DEFAULT_SETTINGS_ENV["FRONTEND_PORT"])),
    }


def _load_effective_env_for_ui() -> dict[str, str]:
    return merged_effective_env(defaults=DEFAULT_SETTINGS_ENV)


@_router.get("/settings")
def get_settings():
    effective_env = _load_effective_env_for_ui()
    return {
        "ok": True,
        "data": {
            "config": _build_ui_config(effective_env),
            "secrets": _mask_secrets_flags(effective_env),
            "persistPath": str(settings_file_path()),
            "note": "已保存到 settings.json 的配置会在服务重启后影响 Outline/Content 等子服务。",
        },
    }


@_router.put("/settings")
def update_settings(payload: UiSettingsPayload):
    existing = read_settings_env()
    updates: dict[str, Any] = {}

    bool_keys: set[str] = {"USE_CHART", "OUTLINE_STREAMING", "CONTENT_STREAMING", "USE_MINERU"}
    int_keys: set[str] = {"MAIN_API_PORT", "OUTLINE_API_PORT", "CONTENT_API_PORT", "FRONTEND_PORT"}
    embedding_int_keys: set[str] = {"EMBEDDING_MAX_RETRIES", "EMBEDDING_DIM"}
    embedding_float_keys: set[str] = {"EMBEDDING_TIMEOUT_S"}

    data = payload.model_dump(exclude_none=True)
    for ui_key, ui_value in data.items():
        env_key = _UI_TO_ENV.get(ui_key)
        if not env_key:
            continue

        # secret：留空不写入（避免覆盖 .env）
        if env_key in SECRET_ENV_KEYS:
            if not str(ui_value or "").strip():
                continue
            updates[env_key] = str(ui_value).strip()
            continue

        if env_key in bool_keys:
            updates[env_key] = bool(ui_value)
            continue

        if env_key in int_keys:
            raw = str(ui_value or "").strip()
            if not raw:
                # 端口不允许写入空值（会导致 start.py/int() 崩溃），留空则视为“不修改”
                continue
            try:
                port = int(raw)
            except Exception:
                raise HTTPException(status_code=422, detail=f"{env_key} 必须是整数")
            if not (1 <= port <= 65535):
                raise HTTPException(status_code=422, detail=f"{env_key} 必须在 1~65535 之间")
            updates[env_key] = port
            continue

        if env_key in embedding_int_keys:
            raw = str(ui_value or "").strip()
            if not raw:
                # 这些字段留空表示不修改
                continue
            try:
                value = int(raw)
            except Exception:
                raise HTTPException(status_code=422, detail=f"{env_key} 必须是整数")
            if env_key == "EMBEDDING_MAX_RETRIES" and value < 0:
                raise HTTPException(status_code=422, detail=f"{env_key} 不能为负数")
            if env_key == "EMBEDDING_DIM" and value < 0:
                raise HTTPException(status_code=422, detail=f"{env_key} 不能为负数")
            updates[env_key] = value
            continue

        if env_key in embedding_float_keys:
            raw = str(ui_value or "").strip()
            if not raw:
                continue
            try:
                value = float(raw)
            except Exception:
                raise HTTPException(status_code=422, detail=f"{env_key} 必须是数字")
            if value <= 0:
                continue
            updates[env_key] = value
            continue

        # 非 secret：允许空字符串（例如 base_url 置空以使用默认 openai）
        updates[env_key] = str(ui_value).strip() if ui_value is not None else ""

    merged = dict(existing)
    merged.update(updates)

    # 写入持久化文件（内部会自动过滤空 secret）
    write_settings_env(merged)

    # 让 main_api 进程内尽可能立即生效（覆盖同名 env）
    apply_settings_to_environ(updates, overwrite=True)

    # 若用户把某些 secret 留空，则不修改当前进程里的值；但在“下一次重启”时也不会写入 settings.json，
    # 因此不会覆盖 `.env` 的 secret（安全）。

    effective_env = _load_effective_env_for_ui()
    return {
        "ok": True,
        "data": {
            "config": _build_ui_config(effective_env),
            "secrets": _mask_secrets_flags(effective_env),
            "persistPath": str(settings_file_path()),
            "updatedKeys": sorted(list(updates.keys())),
        },
    }


@_router.post("/settings/reset")
def reset_settings():
    """
    恢复默认配置：
    - 覆盖写入默认值（但不写入空的 secret）
    - 仅对 main_api 进程做即时覆盖；Outline/Content 等子服务需重启生效
    """
    defaults = dict(DEFAULT_SETTINGS_ENV)
    # 关键：不写入空 secret（否则会覆盖 .env）
    for k in list(defaults.keys()):
        if k in SECRET_ENV_KEYS:
            defaults.pop(k, None)

    write_settings_env(defaults)
    apply_settings_to_environ(defaults, overwrite=True)
    # 同时清空进程内 secret，确保 UI 立即反映“已清空”（若需要恢复 .env 中的 secret，请重启服务）
    for k in SECRET_ENV_KEYS:
        os.environ.pop(k, None)

    effective_env = _load_effective_env_for_ui()
    return {
        "ok": True,
        "data": {
            "config": _build_ui_config(effective_env),
            "secrets": _mask_secrets_flags(effective_env),
            "persistPath": str(settings_file_path()),
        },
    }


def register_settings_routes(app) -> None:  # noqa: ANN001 - FastAPI app
    app.include_router(_router)
