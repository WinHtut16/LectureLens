"""Smoke test: the app imports and the /health stub responds.

Keeps the suite (and CI) green on the empty skeleton. Replaced/augmented by
real feature tests later.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
