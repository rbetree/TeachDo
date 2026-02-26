from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def main_api_client():
    from backend.main_api.main import app

    return TestClient(app)


def test_artifacts_upload_list_download_delete(main_api_client, monkeypatch, tmp_path):
    monkeypatch.setenv("TEACHDO_ARTIFACT_DIR", str(tmp_path))

    upload_bytes = b"PK\x03\x04test-docx"
    resp = main_api_client.post(
        "/artifacts/default_user/material-1",
        data={"kind": "docx"},
        files={
            "file": (
                "lesson.docx",
                upload_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("ok") is True
    meta = payload.get("data") or {}
    artifact_id = str(meta.get("artifact_id") or "").strip()
    assert artifact_id
    assert meta.get("kind") == "docx"
    assert str(meta.get("file_name") or "").lower().endswith(".docx")

    resp = main_api_client.get("/artifacts/default_user/material-1")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("ok") is True
    items = payload.get("data") or []
    assert any(str(it.get("artifact_id")) == artifact_id for it in items)

    resp = main_api_client.get(f"/artifacts/default_user/material-1/{artifact_id}")
    assert resp.status_code == 200
    assert "attachment" in (resp.headers.get("content-disposition") or "")
    assert resp.content == upload_bytes

    resp = main_api_client.delete(f"/artifacts/default_user/material-1/{artifact_id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("ok") is True

    resp = main_api_client.get("/artifacts/default_user/material-1")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("ok") is True
    assert payload.get("data") == []


def test_lesson_export_docx_persists_to_artifacts(main_api_client, monkeypatch, tmp_path):
    monkeypatch.setenv("TEACHDO_ARTIFACT_DIR", str(tmp_path))

    payload: Dict[str, Any] = {
        "lessonPlan": {
            "title": "三角形的基本性质",
            "targetAudience": "中学学生",
            "duration": "45分钟",
            "objectives": ["理解内角和定理", "完成基础练习"],
            "materials": ["课件/PPT", "白板"],
            "procedure": [
                {"step": "导入", "duration": "5分钟", "activity": "复习三角形概念并引出问题"},
                {"step": "讲解", "duration": "15分钟", "activity": "讲解内角和定理并示范推导"},
            ],
            "homework": "完成课后练习 1~3 题。",
        },
        "style": {
            "fontZh": "微软雅黑",
            "titleSizePt": 20,
            "h1SizePt": 16,
            "h2SizePt": 14,
            "bodySizePt": 12,
            "lineSpacing": 1.5,
        },
        "language": "zh",
        "persist": True,
        "userId": "default_user",
        "materialId": "material-1",
    }

    resp = main_api_client.post("/lesson/export/docx", json=payload)
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"
    artifact_id = (resp.headers.get("x-teachdo-artifact-id") or "").strip()
    assert artifact_id

    list_resp = main_api_client.get("/artifacts/default_user/material-1")
    assert list_resp.status_code == 200
    items = (list_resp.json().get("data") or [])
    assert any(str(it.get("artifact_id")) == artifact_id for it in items)

    dl_resp = main_api_client.get(f"/artifacts/default_user/material-1/{artifact_id}")
    assert dl_resp.status_code == 200
    assert dl_resp.content == resp.content

