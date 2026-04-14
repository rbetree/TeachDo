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
    import backend.main_api.settings_api as settings_api

    # settings API 会尝试调用子服务 /admin/reload；测试环境下统一 mock 掉，避免真实网络请求与超时。
    def _fake_post_reload(_base_url: str, *, clear_secrets: bool):  # noqa: ANN001 - signature compat
        return settings_api._ReloadResult(ok=True, status=200)

    monkeypatch.setattr(settings_api, "_post_reload", _fake_post_reload)

    return TestClient(app)


def test_settings_get_returns_config_and_secret_flags(client: TestClient):
    resp = client.get("/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "data" in body
    assert "config" in body["data"]
    assert "secrets" in body["data"]
    assert "outlineApi" not in body["data"]["config"]
    assert "contentApi" not in body["data"]["config"]
    assert "personalDb" not in body["data"]["config"]
    assert "httpProxy" not in body["data"]["config"]
    assert "httpsProxy" not in body["data"]["config"]
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
        "personalDbPort": "9100",
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
    assert body["data"]["restartRequired"] is True
    assert isinstance(body["data"]["restartKeys"], list)
    assert body["data"]["reload"] is not None

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
            "personalDbPort": "9100",
            "useChart": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["config"]["outlineApiKey"] == ""
    assert body["data"]["secrets"]["outlineApiKey"] is True
    assert body["data"]["reload"] is not None

    stored = json.loads(settings_file.read_text(encoding="utf-8"))
    assert stored["OUTLINE_API_KEY"] == "sk-test"


def test_settings_put_only_llm_triggers_reload_without_restart_required(client: TestClient):
    resp = client.put(
        "/settings",
        json={
            "outlineType": "openai",
            "outlineBaseUrl": "https://example.com/v1",
            "outlineModel": "foo",
            "outlineApiKey": "sk-test",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["restartRequired"] is False
    assert body["data"]["reload"] is not None
    assert body["data"]["reload"]["outline"]["ok"] is True
    assert body["data"]["reload"]["content"]["ok"] is True


def test_settings_put_lesson_fields_persist_and_secret_flag(client: TestClient, settings_file: Path):
    resp = client.put(
        "/settings",
        json={
            "lessonType": "openai",
            "lessonBaseUrl": "https://example.com/v1",
            "lessonModel": "lesson-model",
            "lessonApiKey": "sk-lesson",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["config"]["lessonType"] == "openai"
    assert body["data"]["config"]["lessonBaseUrl"] == "https://example.com/v1"
    assert body["data"]["config"]["lessonModel"] == "lesson-model"
    assert body["data"]["config"]["lessonApiKey"] == ""
    assert body["data"]["secrets"]["lessonApiKey"] is True
    # lesson 只影响 main_api，本次不需要触发 Outline/Content/PersonalDB reload
    assert body["data"]["reload"] is None
    assert body["data"]["restartRequired"] is False

    stored = json.loads(settings_file.read_text(encoding="utf-8"))
    assert stored["LESSON_TYPE"] == "openai"
    assert stored["LESSON_BASE_URL"] == "https://example.com/v1"
    assert stored["LESSON_MODEL"] == "lesson-model"
    assert stored["LESSON_API_KEY"] == "sk-lesson"


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
            "personalDbPort": "9101",
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
    assert body["data"]["reload"] is not None
    assert body["data"]["restartRequired"] is True

    stored = json.loads(settings_file.read_text(encoding="utf-8"))
    assert stored["HOST"] == "0.0.0.0"
    assert stored["MAIN_API_PORT"] == 6801
    assert stored["OUTLINE_API_PORT"] == 10002
    assert stored["CONTENT_API_PORT"] == 10012
    assert stored["PERSONAL_DB_PORT"] == 9101
    assert stored["FRONTEND_PORT"] == 5175
    # 端口联动：当 URL 仍为本地基址且未显式修改时，会自动同步到新的端口
    assert stored["OUTLINE_API"] == "http://127.0.0.1:10002"
    assert stored["CONTENT_API"] == "http://127.0.0.1:10012"
    assert stored["PERSONAL_DB"] == "http://127.0.0.1:9101"
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


def test_settings_reset_clears_secrets_in_file_and_response(client: TestClient, settings_file: Path, monkeypatch: pytest.MonkeyPatch):
    import backend.main_api.settings_api as settings_api

    calls: list[bool] = []

    def _spy_post_reload(_base_url: str, *, clear_secrets: bool):  # noqa: ANN001 - signature compat
        calls.append(bool(clear_secrets))
        return settings_api._ReloadResult(ok=True, status=200)

    monkeypatch.setattr(settings_api, "_post_reload", _spy_post_reload)

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
            "useChart": True,
        },
    )

    resp = client.post("/settings/reset")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["secrets"]["outlineApiKey"] is False
    assert body["data"]["reload"] is not None
    assert body["data"]["restartRequired"] is True
    # 期间会先触发一次保存（clearSecrets=False），再触发 reset（clearSecrets=True）
    assert calls[:3] == [False, False, False]
    assert calls[-3:] == [True, True, True]

    stored = json.loads(settings_file.read_text(encoding="utf-8"))
    assert "OUTLINE_API_KEY" not in stored
