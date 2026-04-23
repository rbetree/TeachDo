from __future__ import annotations

import logging
import os
import hmac
from typing import Any
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request
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

logger = logging.getLogger(__name__)

_OUTLINE_LLM_ENV_KEYS: set[str] = {"OUTLINE_TYPE", "OUTLINE_BASE_URL", "OUTLINE_MODEL", "OUTLINE_API_KEY"}
_LESSON_LLM_ENV_KEYS: set[str] = {"LESSON_TYPE", "LESSON_BASE_URL", "LESSON_MODEL", "LESSON_API_KEY"}
_PPT_LLM_ENV_KEYS: set[str] = {
    "PPT_WRITER_TYPE",
    "PPT_WRITER_BASE_URL",
    "PPT_WRITER_MODEL",
    "PPT_WRITER_API_KEY",
    "PPT_CHECKER_TYPE",
    "PPT_CHECKER_BASE_URL",
    "PPT_CHECKER_MODEL",
    "PPT_CHECKER_API_KEY",
}
_EMBEDDING_LLM_ENV_KEYS: set[str] = {
    "EMBEDDING_TYPE",
    "EMBEDDING_BASE_URL",
    "EMBEDDING_MODEL",
    "EMBEDDING_API_KEY",
    "EMBEDDING_TIMEOUT_S",
    "EMBEDDING_MAX_RETRIES",
    "EMBEDDING_DIM",
}
_LLM_ENV_KEYS: set[str] = set().union(
    _OUTLINE_LLM_ENV_KEYS,
    _LESSON_LLM_ENV_KEYS,
    _PPT_LLM_ENV_KEYS,
    _EMBEDDING_LLM_ENV_KEYS,
)


def _is_loopback_client(host: str) -> bool:
    return str(host or "").strip() in {"127.0.0.1", "::1"}


def _has_valid_admin_token(request: Request) -> bool:
    """
    可选的管理口令：
    - 当设置了 TEACHDO_ADMIN_TOKEN 时，允许非本机访问 settings API；
    - 调用方需在请求头里带上 x-teachdo-admin-token。
    """
    expected = (os.environ.get("TEACHDO_ADMIN_TOKEN") or "").strip()
    if not expected:
        return False
    got = (request.headers.get("x-teachdo-admin-token") or "").strip()
    if not got:
        return False
    return hmac.compare_digest(got, expected)


def _ensure_settings_access(request: Request) -> None:
    """
    settings API 属于“本机管理接口”：
    - 默认仅允许本机回环访问；
    - 如需远程管理，请设置 TEACHDO_ADMIN_TOKEN 并在请求头携带 x-teachdo-admin-token。
    """
    client_host = request.client.host if request.client else ""
    is_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
    if is_pytest and client_host == "testclient":
        return
    if _is_loopback_client(client_host):
        return
    if _has_valid_admin_token(request):
        return
    raise HTTPException(status_code=403, detail="forbidden")


def _join_url(base_url: str, path: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return path
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


def _resolve_service_base_url(*, url_key: str, port_key: str) -> str:
    raw = (os.environ.get(url_key) or "").strip()
    if raw:
        return raw.rstrip("/")
    bind_host = (os.environ.get("HOST") or str(DEFAULT_SETTINGS_ENV.get("HOST") or "127.0.0.1")).strip() or "127.0.0.1"
    try:
        port = int(str(os.environ.get(port_key) or DEFAULT_SETTINGS_ENV.get(port_key) or "").strip())
    except Exception:
        logger.debug("解析 %s 端口失败，使用默认端口", port_key, exc_info=True)
        port = int(DEFAULT_SETTINGS_ENV.get(port_key) or 0) or 0
    if port <= 0:
        # 最后的兜底：避免拼出非法 URL
        port = 80
    return f"http://{access_host_for_bind_host(bind_host)}:{port}"


@dataclass(frozen=True)
class _ReloadResult:
    ok: bool
    status: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"ok": bool(self.ok)}
        if self.status is not None:
            data["status"] = int(self.status)
        if self.error:
            data["error"] = str(self.error)
        return data


def _safe_extract_httpx_error_message(response) -> str:  # noqa: ANN001 - httpx.Response
    try:
        payload = response.json()
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict) and isinstance(err.get("message"), str) and err["message"].strip():
                return err["message"].strip()
            detail = payload.get("detail")
            if isinstance(detail, str) and detail.strip():
                return detail.strip()
            msg = payload.get("message")
            if isinstance(msg, str) and msg.strip():
                return msg.strip()
    except Exception:
        logger.debug("解析响应 JSON 失败", exc_info=True)
        pass
    try:
        text = (response.text or "").strip()
        if text:
            return text[:500]
    except Exception:
        logger.debug("读取响应文本失败", exc_info=True)
        pass
    return f"HTTP {getattr(response, 'status_code', 'unknown')}"


def _post_reload(base_url: str, *, clear_secrets: bool) -> _ReloadResult:
    """
    触发子服务 /admin/reload（失败不抛错，返回结构化结果）。
    """
    import httpx  # 延迟导入：避免在无 httpx 环境下影响其它路由加载

    url = _join_url(base_url, "/admin/reload")
    try:
        timeout = httpx.Timeout(3.0, connect=0.5)
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            resp = client.post(url, json={"clearSecrets": bool(clear_secrets)})
        if 200 <= int(resp.status_code) < 300:
            return _ReloadResult(ok=True, status=int(resp.status_code))
        return _ReloadResult(ok=False, status=int(resp.status_code), error=_safe_extract_httpx_error_message(resp))
    except Exception as exc:
        return _ReloadResult(ok=False, error=str(exc))


def _trigger_llm_reload(*, updated_env_keys: set[str], clear_secrets: bool) -> dict[str, Any]:
    """
    根据“本次更新的 env keys”，决定哪些子服务需要热加载 LLM 配置。

    - 仅保存/重置 LLM 配置时调用（其它配置仍需重启）
    - 失败不阻断 /settings 的保存：仅在响应里返回 warning 结果给前端提示
    """
    services: set[str] = set()
    if updated_env_keys & _OUTLINE_LLM_ENV_KEYS:
        services.update({"outline", "content"})
    if updated_env_keys & _PPT_LLM_ENV_KEYS:
        services.add("content")
    if updated_env_keys & _EMBEDDING_LLM_ENV_KEYS:
        services.add("personaldb")

    if not services:
        return {}

    results: dict[str, Any] = {}

    if "outline" in services:
        base = _resolve_service_base_url(url_key="OUTLINE_API", port_key="OUTLINE_API_PORT")
        results["outline"] = _post_reload(base, clear_secrets=clear_secrets).to_dict()

    if "content" in services:
        base = _resolve_service_base_url(url_key="CONTENT_API", port_key="CONTENT_API_PORT")
        results["content"] = _post_reload(base, clear_secrets=clear_secrets).to_dict()

    if "personaldb" in services:
        base = _resolve_service_base_url(url_key="PERSONAL_DB", port_key="PERSONAL_DB_PORT")
        results["personaldb"] = _post_reload(base, clear_secrets=clear_secrets).to_dict()

    return results


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

    # Service endpoints / proxy：不再通过设置页修改（避免误配；开发时改 var/settings.json 或环境变量）
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
        logger.debug("将 %r 转为 int 失败，使用默认值 %s", value, default, exc_info=True)
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
        logger.debug("URL 归一化失败: %r", raw, exc_info=True)
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
def get_settings(request: Request):  # noqa: ANN001 - FastAPI handler
    _ensure_settings_access(request)
    effective_env = _load_effective_env_for_ui()
    return {
        "ok": True,
        "data": {
            "config": _build_ui_config(effective_env),
            "secrets": _mask_secrets_flags(effective_env),
            "persistPath": str(settings_file_path()),
            "note": "LLM 配置可在保存后自动热加载；端口/地址/目录等运行参数仍需重启服务生效。",
        },
    }


@_router.put("/settings")
def update_settings(payload: UiSettingsPayload, request: Request):  # noqa: ANN001 - FastAPI handler
    _ensure_settings_access(request)
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

    # 记录：用户本次请求显式更新的 env keys（用于判断 restartRequired / 是否触发 LLM reload）。
    # 注意：后续 _apply_ports_link_service_urls 可能会“自动补齐” OUTLINE_API/CONTENT_API 等 URL keys，
    # 这些不应影响前端的“是否需要重启”提示。
    requested_update_keys = set(updates.keys())

    # 端口 <-> URL 联动：
    # - 设置页不再直接暴露 OUTLINE_API/CONTENT_API/PERSONAL_DB 的编辑能力；
    # - 仅当用户本次确实修改了 host/port 时，才做“派生 URL 自动同步”，避免保存其它字段时意外覆盖 .env 中的自定义值。
    if {"HOST", "OUTLINE_API_PORT", "CONTENT_API_PORT", "PERSONAL_DB_PORT"} & set(updates.keys()):
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

    restart_keys = sorted([k for k in requested_update_keys if k not in _LLM_ENV_KEYS])
    reload_results = _trigger_llm_reload(updated_env_keys=requested_update_keys, clear_secrets=False)

    effective_env = _load_effective_env_for_ui()
    return {
        "ok": True,
        "data": {
            "config": _build_ui_config(effective_env),
            "secrets": _mask_secrets_flags(effective_env),
            "persistPath": str(settings_file_path()),
            "updatedKeys": sorted(list(updates.keys())),
            "reload": reload_results or None,
            "restartRequired": bool(restart_keys),
            "restartKeys": restart_keys,
        },
    }


@_router.post("/settings/reset")
def reset_settings(request: Request):  # noqa: ANN001 - FastAPI handler
    _ensure_settings_access(request)
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

    updated_env_keys = set(defaults.keys()).union(SECRET_ENV_KEYS)
    restart_keys = sorted([k for k in updated_env_keys if k not in _LLM_ENV_KEYS])
    # reset 场景：子服务需清空 secret（避免继续使用旧 key）
    reload_results = _trigger_llm_reload(updated_env_keys=updated_env_keys, clear_secrets=True)

    effective_env = _load_effective_env_for_ui()
    return {
        "ok": True,
        "data": {
            "config": _build_ui_config(effective_env),
            "secrets": _mask_secrets_flags(effective_env),
            "persistPath": str(settings_file_path()),
            "reload": reload_results or None,
            "restartRequired": bool(restart_keys),
            "restartKeys": restart_keys,
        },
    }


def register_settings_routes(app) -> None:  # noqa: ANN001 - FastAPI app
    app.include_router(_router)
