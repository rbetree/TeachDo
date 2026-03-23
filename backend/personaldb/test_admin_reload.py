from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def personaldb_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """
    为 personaldb 提供一个可控的 settings.json，并返回 TestClient。

    注意：
    - personaldb/main.py 在 import 时会 load_env_files(... overwrite=False)；
      因此这里预先写入 settings.json，并同时在 os.environ 里塞入“旧值”，以验证 /admin/reload 会覆盖。
    """
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "EMBEDDING_TYPE": "openai",
                "EMBEDDING_BASE_URL": "https://example.com/v1",
                "EMBEDDING_MODEL": "bge-m3",
                "EMBEDDING_API_KEY": "sk-emb",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TEACHDO_SETTINGS_FILE", str(settings_file))

    # 模拟“已有旧值”，确保 /admin/reload 是覆盖写入
    monkeypatch.setenv("EMBEDDING_TYPE", "openai")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://old.example.com/v1")
    monkeypatch.setenv("EMBEDDING_MODEL", "old-model")
    monkeypatch.setenv("EMBEDDING_API_KEY", "sk-old")

    from backend.personaldb.main import app

    return TestClient(app)


def test_admin_reload_applies_embedding_env(personaldb_client: TestClient):
    resp = personaldb_client.post("/admin/reload", json={"clearSecrets": False})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True

    assert os.environ.get("EMBEDDING_BASE_URL") == "https://example.com/v1"
    assert os.environ.get("EMBEDDING_MODEL") == "bge-m3"
    assert os.environ.get("EMBEDDING_API_KEY") == "sk-emb"


def test_admin_reload_clear_secrets(personaldb_client: TestClient):
    resp = personaldb_client.post("/admin/reload", json={"clearSecrets": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True

    assert os.environ.get("EMBEDDING_API_KEY") in {None, ""}

