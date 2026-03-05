from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from urllib.parse import urlsplit

from backend.common.settings_store import (
    DEFAULT_SETTINGS_ENV,
    SECRET_ENV_KEYS,
    access_host_for_bind_host,
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

    # Lesson（可选：覆盖 OUTLINE_*；留空表示复用 Outline）
    lessonType: str | None = None
    lessonBaseUrl: str | None = None
    lessonModel: str | None = None
    lessonApiKey: str | None = Field(default=None, description="留空表示不修改")

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
    personalDbPort: str | None = None
    frontendPort: str | None = None


_UI_TO_ENV: dict[str, str] = {
    "outlineType": "OUTLINE_TYPE",
    "outlineBaseUrl": "OUTLINE_BASE_URL",
    "outlineModel": "OUTLINE_MODEL",
    "outlineApiKey": "OUTLINE_API_KEY",
    "lessonType": "LESSON_TYPE",
    "lessonBaseUrl": "LESSON_BASE_URL",
    "lessonModel": "LESSON_MODEL",
    "lessonApiKey": "LESSON_API_KEY",
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
    "personalDbPort": "PERSONAL_DB_PORT",
    "frontendPort": "FRONTEND_PORT",
}


def _coerce_int(value: Any, *, default: int) -> int:
    try:
        v = int(str(value).strip())
        return v
    except Exception:
        return int(default)


def _normalize_loopback(host: str) -> str:
    """
    将 localhost / 0.0.0.0 / 127.0.0.1 等视为同一类，便于做“本地联动”判断。
    """
    h = (host or "").strip().lower()
    if h in {"localhost", "127.0.0.1", "0.0.0.0", "::1", "::"}:
        return "127.0.0.1"
    return h


def _is_simple_base_url(url: str) -> bool:
    """
    仅当 URL 形如 http(s)://host[:port][/]
    - 不包含额外 path/query/fragment
    - 用于判断“是否是本地服务基址”，避免把用户自定义路径误判为可自动联动
    """
    raw = (url or "").strip()
    if not raw:
        return False
    parts = urlsplit(raw)
    if not parts.scheme or not parts.hostname:
        return False
    if parts.scheme.lower() not in {"http", "https"}:
        return False
    if (parts.path or "") not in {"", "/"}:
        return False
    if parts.query or parts.fragment:
        return False
    return True


def _normalize_base_url_for_compare(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
        if not parts.scheme or not parts.hostname:
            return raw.rstrip("/")
        scheme = parts.scheme.lower()
        host = parts.hostname
        port = parts.port
        if port:
            return f"{scheme}://{host}:{port}"
        return f"{scheme}://{host}"
    except Exception:
        return raw.rstrip("/")


def _build_local_service_url(bind_host: str, port: int) -> str:
    access_host = access_host_for_bind_host(bind_host)
    return f"http://{access_host}:{int(port)}"


def _apply_ports_link_service_urls(
    existing_effective: dict[str, Any],
    updates: dict[str, Any],
) -> None:
    """
    端口与服务 URL 联动，尽量消除“端口改了但 URL 没改”的漂移。

    策略（偏保守）：
    - 仅对“看起来是本地基址”的 URL（http(s)://host:port[/]）做自动联动
    - 仅当用户本次请求未显式修改对应 URL 时，才会用 host/port 派生的 URL 覆盖
    """
    old_host = str(existing_effective.get("HOST", DEFAULT_SETTINGS_ENV["HOST"]))
    old_outline_port = _coerce_int(existing_effective.get("OUTLINE_API_PORT"), default=int(DEFAULT_SETTINGS_ENV["OUTLINE_API_PORT"]))
    old_content_port = _coerce_int(existing_effective.get("CONTENT_API_PORT"), default=int(DEFAULT_SETTINGS_ENV["CONTENT_API_PORT"]))
    old_personal_port = _coerce_int(existing_effective.get("PERSONAL_DB_PORT"), default=int(DEFAULT_SETTINGS_ENV.get("PERSONAL_DB_PORT", 9100)))

    new_host = str(updates.get("HOST", old_host))
    new_outline_port = _coerce_int(updates.get("OUTLINE_API_PORT", old_outline_port), default=old_outline_port)
    new_content_port = _coerce_int(updates.get("CONTENT_API_PORT", old_content_port), default=old_content_port)
    new_personal_port = _coerce_int(updates.get("PERSONAL_DB_PORT", old_personal_port), default=old_personal_port)

    # 仅对 host 归一化后的“本地环回”做联动判断（避免把远端 URL 误同步）
    old_access_host_norm = _normalize_loopback(access_host_for_bind_host(old_host))
    new_outline_url = _build_local_service_url(new_host, new_outline_port)
    new_content_url = _build_local_service_url(new_host, new_content_port)
    new_personal_url = _build_local_service_url(new_host, new_personal_port)

    def should_autosync_url(env_url_key: str) -> bool:
        existing_url = str(existing_effective.get(env_url_key, "") or "")
        if not _is_simple_base_url(existing_url):
            return False
        existing_host = urlsplit(existing_url).hostname or ""
        existing_host_norm = _normalize_loopback(existing_host)
        # 允许“旧配置仍是 127.0.0.1/localhost”被视为本地基址，从而在用户切换 HOST 时自动纠偏。
        if existing_host_norm not in {old_access_host_norm, "127.0.0.1"}:
            return False

        # 若用户本次显式修改了该 URL，则不覆盖（允许手动 override）
        if env_url_key in updates:
            incoming = str(updates.get(env_url_key, "") or "")
            if _normalize_base_url_for_compare(incoming) != _normalize_base_url_for_compare(existing_url):
                return False
        return True

    if should_autosync_url("OUTLINE_API"):
        updates["OUTLINE_API"] = new_outline_url
    if should_autosync_url("CONTENT_API"):
        updates["CONTENT_API"] = new_content_url
    if should_autosync_url("PERSONAL_DB"):
        updates["PERSONAL_DB"] = new_personal_url


def _mask_secrets_flags(effective_env: dict[str, str]) -> dict[str, bool]:
    return {
        "outlineApiKey": bool((effective_env.get("OUTLINE_API_KEY") or "").strip()),
        "lessonApiKey": bool((effective_env.get("LESSON_API_KEY") or "").strip()),
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
        "lessonType": effective_env.get("LESSON_TYPE", DEFAULT_SETTINGS_ENV["LESSON_TYPE"]),
        "lessonBaseUrl": effective_env.get("LESSON_BASE_URL", DEFAULT_SETTINGS_ENV["LESSON_BASE_URL"]),
        "lessonModel": effective_env.get("LESSON_MODEL", DEFAULT_SETTINGS_ENV["LESSON_MODEL"]),
        "lessonApiKey": "",
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
        "personalDbPort": effective_env.get("PERSONAL_DB_PORT", str(DEFAULT_SETTINGS_ENV.get("PERSONAL_DB_PORT", 9100))),
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
    int_keys: set[str] = {"MAIN_API_PORT", "OUTLINE_API_PORT", "CONTENT_API_PORT", "PERSONAL_DB_PORT", "FRONTEND_PORT"}
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

    # 端口 <-> URL 联动（只在用户未显式改 URL 时自动同步）
    existing_effective: dict[str, Any] = dict(DEFAULT_SETTINGS_ENV)
    existing_effective.update(existing)
    _apply_ports_link_service_urls(existing_effective, updates)

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
