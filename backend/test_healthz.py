from __future__ import annotations

from fastapi.testclient import TestClient


def test_main_api_healthz():
    from backend.main_api.main import app

    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True


def test_personaldb_healthz():
    from backend.personaldb.main import app

    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
