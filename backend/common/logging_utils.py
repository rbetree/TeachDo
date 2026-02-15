from __future__ import annotations

import copy
import logging
import logging.config
import os
from typing import Any


DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"
DEFAULT_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
ACCESS_FMT = (
    '%(asctime)s [%(levelname)s] %(name)s: %(client_addr)s - "%(request_line)s" %(status_code)s'
)


def _set_formatter_fields(formatter_cfg: dict[str, Any], *, fmt: str, datefmt: str) -> None:
    """
    uvicorn 的默认 LOGGING_CONFIG 在不同版本中可能使用 `fmt` 或 `format` 字段。
    这里做一层兼容处理，避免因为版本差异导致日志格式无法生效。
    """
    if "fmt" in formatter_cfg:
        formatter_cfg["fmt"] = fmt
    else:
        formatter_cfg["format"] = fmt

    # datefmt 在 uvicorn 默认配置里不一定存在，补齐即可
    formatter_cfg["datefmt"] = datefmt


def build_uvicorn_log_config(
    *,
    level: str | None = None,
    datefmt: str = DEFAULT_DATEFMT,
    default_fmt: str = DEFAULT_FMT,
    access_fmt: str = ACCESS_FMT,
) -> dict[str, Any]:
    """
    构建“统一风格”的 uvicorn logging dictConfig。

    目标：
    - uvicorn 的 error/access 日志都有时间戳、level、logger 名称
    - 应用自身 logging 也走同一套 root handler（便于 start.py 重定向到文件时保持一致）
    """
    import uvicorn.config

    cfg: dict[str, Any] = copy.deepcopy(uvicorn.config.LOGGING_CONFIG)

    # 统一格式
    formatters = cfg.setdefault("formatters", {})
    if "default" in formatters:
        _set_formatter_fields(formatters["default"], fmt=default_fmt, datefmt=datefmt)
    if "access" in formatters:
        _set_formatter_fields(formatters["access"], fmt=access_fmt, datefmt=datefmt)

    # 统一 root（确保应用 logger 也有输出）
    resolved_level = (level or os.environ.get("LOG_LEVEL") or "INFO").upper()
    cfg["root"] = {"handlers": ["default"], "level": resolved_level}

    # 确保 uvicorn.* 继承/匹配 root level
    loggers = cfg.setdefault("loggers", {})
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        if logger_name in loggers and "level" in loggers[logger_name]:
            loggers[logger_name]["level"] = resolved_level

    return cfg


def apply_logging_config(cfg: dict[str, Any]) -> None:
    """应用 dictConfig，并把 warnings 也汇入 logging。"""
    logging.config.dictConfig(cfg)
    logging.captureWarnings(True)

