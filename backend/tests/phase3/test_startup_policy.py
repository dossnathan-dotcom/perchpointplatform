import os

import pytest

from perchpoint.settings import Phase2ConfigurationError, Settings


def test_production_refuses_local_auth(monkeypatch):
    monkeypatch.setenv("PHASE3_ENVIRONMENT", "production")
    monkeypatch.setenv("PHASE2_LOCAL_AUTH", "development")
    with pytest.raises(Phase2ConfigurationError, match="local-development auth"):
        Settings.load()


def test_production_refuses_placeholder_secrets(monkeypatch):
    monkeypatch.setenv("PHASE3_ENVIRONMENT", "production")
    monkeypatch.setenv("PHASE2_LOCAL_AUTH", "disabled")
    for name in ("PHASE2_ADMIN_URL", "PHASE2_MIGRATOR_URL", "PHASE2_RUNTIME_URL", "PHASE2_JWT_SECRET", "PHASE2_DEV_PASSWORD", "PHASE2_WEBHOOK_SECRET"):
        monkeypatch.setenv(name, "replace-me")
    with pytest.raises(Phase2ConfigurationError, match="Production startup refused"):
        Settings.load()


def test_liveness_does_not_require_a_database():
    from fastapi.testclient import TestClient
    from perchpoint.routes import create_app

    client = TestClient(create_app())
    response = client.get("/api/v2/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"
    assert response.headers["x-request-id"]


def test_local_mode_still_requires_development_auth(monkeypatch):
    monkeypatch.setenv("PHASE3_ENVIRONMENT", "local")
    monkeypatch.delenv("PHASE2_LOCAL_AUTH", raising=False)
    os.environ["PHASE2_LOCAL_AUTH"] = "production"
    try:
        with pytest.raises(Phase2ConfigurationError):
            Settings.load()
    finally:
        os.environ["PHASE2_LOCAL_AUTH"] = "development"
