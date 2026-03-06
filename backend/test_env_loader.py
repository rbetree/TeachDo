from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from backend.common.env_loader import load_env_files
from backend.common.settings_store import load_and_apply_settings


def _write_env(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def test_load_env_files_settings_json_overrides_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    repo_root = tmp_path
    service_dir = repo_root / "service"
    service_dir.mkdir(parents=True, exist_ok=True)

    settings_path = repo_root / "var" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"OUTLINE_BASE_URL": "https://from-settings"}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("TEACHDO_SETTINGS_FILE", str(settings_path))

    _write_env(repo_root / ".env", "OUTLINE_BASE_URL=https://from-root")
    _write_env(service_dir / ".env", "OUTLINE_BASE_URL=https://from-service")

    monkeypatch.delenv("OUTLINE_BASE_URL", raising=False)

    other_cwd = repo_root / "somewhere"
    other_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(other_cwd)

    original_sys_path = list(sys.path)
    try:
        load_env_files(repo_root=repo_root, service_dir=service_dir)
    finally:
        sys.path[:] = original_sys_path

    assert os.environ.get("OUTLINE_BASE_URL") == "https://from-settings"


def test_load_env_files_service_env_overrides_root_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    repo_root = tmp_path
    service_dir = repo_root / "service"
    service_dir.mkdir(parents=True, exist_ok=True)

    _write_env(repo_root / ".env", "OUTLINE_BASE_URL=https://from-root")
    _write_env(service_dir / ".env", "OUTLINE_BASE_URL=https://from-service")

    monkeypatch.delenv("OUTLINE_BASE_URL", raising=False)

    other_cwd = repo_root / "somewhere"
    other_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(other_cwd)

    original_sys_path = list(sys.path)
    try:
        load_env_files(repo_root=repo_root, service_dir=service_dir, apply_settings_json=False)
    finally:
        sys.path[:] = original_sys_path

    assert os.environ.get("OUTLINE_BASE_URL") == "https://from-service"


def test_load_env_files_does_not_override_existing_environ(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    repo_root = tmp_path
    service_dir = repo_root / "service"
    service_dir.mkdir(parents=True, exist_ok=True)

    settings_path = repo_root / "var" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"OUTLINE_BASE_URL": "https://from-settings"}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("TEACHDO_SETTINGS_FILE", str(settings_path))

    _write_env(repo_root / ".env", "OUTLINE_BASE_URL=https://from-root")
    _write_env(service_dir / ".env", "OUTLINE_BASE_URL=https://from-service")

    monkeypatch.setenv("OUTLINE_BASE_URL", "https://from-system")

    other_cwd = repo_root / "somewhere"
    other_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(other_cwd)

    original_sys_path = list(sys.path)
    try:
        load_env_files(repo_root=repo_root, service_dir=service_dir)
    finally:
        sys.path[:] = original_sys_path

    assert os.environ.get("OUTLINE_BASE_URL") == "https://from-system"


def test_load_and_apply_settings_pytest_guard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    # 明确打开 pytest guard（即便该文件被独立运行，也能覆盖该逻辑）
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_guard")

    repo_root = tmp_path
    default_settings = repo_root / "var" / "settings.json"
    default_settings.parent.mkdir(parents=True, exist_ok=True)
    default_settings.write_text(json.dumps({"OUTLINE_BASE_URL": "https://from-default"}, ensure_ascii=False), encoding="utf-8")

    monkeypatch.delenv("OUTLINE_BASE_URL", raising=False)
    monkeypatch.delenv("TEACHDO_SETTINGS_FILE", raising=False)

    applied = load_and_apply_settings(overwrite=False, repo_root=repo_root)
    assert applied == {}
    assert os.environ.get("OUTLINE_BASE_URL") is None

    monkeypatch.setenv("TEACHDO_SETTINGS_FILE", str(default_settings))
    applied = load_and_apply_settings(overwrite=False, repo_root=repo_root)
    assert applied.get("OUTLINE_BASE_URL") == "https://from-default"
    assert os.environ.get("OUTLINE_BASE_URL") == "https://from-default"

