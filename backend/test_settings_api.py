from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def settings_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    将 settings.json 重定向到临时目录，避免污染开发者本地 var/。
    """
    path = tmp_path / "settings.json"
    monkeypatch.setenv("TEACHDO_SETTINGS_FILE", str(path))
    return path


@pytest.fixture()
def client(settings_file: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # 避免其它测试/环境变量影响本用例断言
    from backend.common.settings_store import ALLOWED_SETTINGS_ENV_KEYS

    for k in ALLOWED_SETTINGS_ENV_KEYS:
        monkeypatch.delenv(k, raising=False)

    from backend.main_api.main import app

    return TestClient(app)


def test_settings_get_returns_config_and_secret_flags(client: TestClient):
    resp = client.get("/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "data" in body
    assert "config" in body["data"]
    assert "secrets" in body["data"]
    assert isinstance(body["data"]["secrets"]["outlineApiKey"], bool)


def test_settings_put_updates_file_without_writing_empty_secrets(client: TestClient, settings_file: Path):
    payload = {
        "outlineType": "openai",
        "outlineBaseUrl": "https://example.com/v1",
        "outlineModel": "foo",
        "outlineApiKey": "",  # 留空：不写入 settings.json
        "pptWriterType": "openai",
        "pptWriterBaseUrl": "https://example.com/v1",
        "pptWriterModel": "bar",
        "pptWriterApiKey": "",
        "pptCheckerType": "openai",
        "pptCheckerBaseUrl": "https://example.com/v1",
        "pptCheckerModel": "baz",
        "pptCheckerApiKey": "",
        "embeddingType": "openai",
        "embeddingBaseUrl": "https://example.com/v1",
        "embeddingModel": "emb",
        "embeddingApiKey": "",
        "outlineApi": "http://127.0.0.1:10001",
        "contentApi": "http://127.0.0.1:10011",
        "personalDb": "http://127.0.0.1:9100",
        "httpProxy": "",
        "httpsProxy": "",
        "useChart": False,
    }

    resp = client.put("/settings", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["config"]["outlineBaseUrl"] == "https://example.com/v1"
    assert body["data"]["config"]["useChart"] is False
    assert body["data"]["config"]["outlineApiKey"] == ""
    assert body["data"]["secrets"]["outlineApiKey"] is False

    assert settings_file.exists()
    stored = json.loads(settings_file.read_text(encoding="utf-8"))
    assert stored["OUTLINE_BASE_URL"] == "https://example.com/v1"
    assert stored["USE_CHART"] is False
    assert "OUTLINE_API_KEY" not in stored


def test_settings_put_writes_secret_when_provided(client: TestClient, settings_file: Path):
    resp = client.put(
        "/settings",
        json={
            "outlineType": "openai",
            "outlineBaseUrl": "https://example.com/v1",
            "outlineModel": "foo",
            "outlineApiKey": "sk-test",
            "pptWriterType": "openai",
            "pptWriterBaseUrl": "https://example.com/v1",
            "pptWriterModel": "bar",
            "pptWriterApiKey": "",
            "pptCheckerType": "openai",
            "pptCheckerBaseUrl": "https://example.com/v1",
            "pptCheckerModel": "baz",
            "pptCheckerApiKey": "",
            "embeddingType": "openai",
            "embeddingBaseUrl": "https://example.com/v1",
            "embeddingModel": "emb",
            "embeddingApiKey": "",
            "outlineApi": "http://127.0.0.1:10001",
            "contentApi": "http://127.0.0.1:10011",
            "personalDb": "http://127.0.0.1:9100",
            "httpProxy": "",
            "httpsProxy": "",
            "useChart": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["config"]["outlineApiKey"] == ""
    assert body["data"]["secrets"]["outlineApiKey"] is True

    stored = json.loads(settings_file.read_text(encoding="utf-8"))
    assert stored["OUTLINE_API_KEY"] == "sk-test"


def test_settings_put_full_coverage_fields_persist(client: TestClient, settings_file: Path):
    resp = client.put(
        "/settings",
        json={
            # LLM
            "outlineType": "vllm",
            "outlineBaseUrl": "http://127.0.0.1:8000/v1",
            "outlineModel": "qwen2.5",
            "outlineApiKey": "",
            "pptWriterType": "openai",
            "pptWriterBaseUrl": "https://example.com/v1",
            "pptWriterModel": "bar",
            "pptWriterApiKey": "",
            "pptCheckerType": "openai",
            "pptCheckerBaseUrl": "https://example.com/v1",
            "pptCheckerModel": "baz",
            "pptCheckerApiKey": "",
            "embeddingType": "xinference",
            "embeddingBaseUrl": "http://127.0.0.1:9999/v1",
            "embeddingModel": "bge-m3",
            "embeddingApiKey": "",
            "embeddingTimeoutS": "30",
            "embeddingMaxRetries": "0",
            "embeddingDim": "0",
            # endpoints + proxy
            "outlineApi": "http://127.0.0.1:10001",
            "contentApi": "http://127.0.0.1:10011",
            "personalDb": "http://127.0.0.1:9100",
            "httpProxy": "",
            "httpsProxy": "",
            "pexelsApiKey": "pexels-xxx",
            # behavior
            "useChart": False,
            "outlineStreaming": False,
            "contentStreaming": True,
            "useMineru": True,
            # runtime paths
            "teachdoCacheDir": "var/cache2",
            "teachdoTmpDir": "var/tmp2",
            "teachdoLogDir": "logs2",
            # bind host & ports
            "host": "0.0.0.0",
            "mainApiPort": "6801",
            "outlineApiPort": "10002",
            "contentApiPort": "10012",
            "frontendPort": "5175",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["config"]["outlineType"] == "vllm"
    assert body["data"]["config"]["embeddingType"] == "xinference"
    assert body["data"]["config"]["useChart"] is False
    assert body["data"]["config"]["outlineStreaming"] is False
    assert body["data"]["config"]["contentStreaming"] is True
    assert body["data"]["config"]["useMineru"] is True
    assert body["data"]["config"]["mainApiPort"] == "6801"
    assert body["data"]["config"]["frontendPort"] == "5175"
    assert body["data"]["config"]["pexelsApiKey"] == ""
    assert body["data"]["secrets"]["pexelsApiKey"] is True

    stored = json.loads(settings_file.read_text(encoding="utf-8"))
    assert stored["HOST"] == "0.0.0.0"
    assert stored["MAIN_API_PORT"] == 6801
    assert stored["OUTLINE_API_PORT"] == 10002
    assert stored["CONTENT_API_PORT"] == 10012
    assert stored["FRONTEND_PORT"] == 5175
    assert stored["TEACHDO_CACHE_DIR"] == "var/cache2"
    assert stored["TEACHDO_TMP_DIR"] == "var/tmp2"
    assert stored["TEACHDO_LOG_DIR"] == "logs2"
    assert stored["OUTLINE_STREAMING"] is False
    assert stored["CONTENT_STREAMING"] is True
    assert stored["USE_MINERU"] is True
    assert stored["USE_CHART"] is False
    assert stored["PEXELS_API_KEY"] == "pexels-xxx"
    assert stored["EMBEDDING_MAX_RETRIES"] == 0
    assert stored["EMBEDDING_DIM"] == 0


def test_settings_reset_clears_secrets_in_file_and_response(client: TestClient, settings_file: Path):
    # 先写入一个 secret
    client.put(
        "/settings",
        json={
            "outlineType": "openai",
            "outlineBaseUrl": "https://example.com/v1",
            "outlineModel": "foo",
            "outlineApiKey": "sk-test",
            "pptWriterType": "openai",
            "pptWriterBaseUrl": "https://example.com/v1",
            "pptWriterModel": "bar",
            "pptWriterApiKey": "",
            "pptCheckerType": "openai",
            "pptCheckerBaseUrl": "https://example.com/v1",
            "pptCheckerModel": "baz",
            "pptCheckerApiKey": "",
            "embeddingType": "openai",
            "embeddingBaseUrl": "https://example.com/v1",
            "embeddingModel": "emb",
            "embeddingApiKey": "",
            "outlineApi": "http://127.0.0.1:10001",
            "contentApi": "http://127.0.0.1:10011",
            "personalDb": "http://127.0.0.1:9100",
            "httpProxy": "",
            "httpsProxy": "",
            "useChart": True,
        },
    )

    resp = client.post("/settings/reset")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["secrets"]["outlineApiKey"] is False

    stored = json.loads(settings_file.read_text(encoding="utf-8"))
    assert "OUTLINE_API_KEY" not in stored
