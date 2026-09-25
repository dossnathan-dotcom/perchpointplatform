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


def test_supported_entrypoints_import_without_legacy_packages():
    import sys

    sys.modules.pop("emergentintegrations", None)
    sys.modules.pop("litellm", None)
    import perchpoint.routes
    import perchpoint.seed
    import perchpoint.worker

    perchpoint.routes.create_app()
    assert "emergentintegrations" not in sys.modules
    assert "litellm" not in sys.modules


def test_database_urls_use_psycopg3(monkeypatch):
    monkeypatch.setenv("PHASE3_ENVIRONMENT", "local")
    monkeypatch.setenv("PHASE2_LOCAL_AUTH", "development")
    monkeypatch.setenv("PHASE2_ADMIN_URL", "postgresql://postgres:pw@127.0.0.1:5432/postgres")
    monkeypatch.setenv("PHASE2_MIGRATOR_URL", "postgresql://perchpoint_migrator:pw@127.0.0.1:5432/perchpoint_phase2")
    monkeypatch.setenv("PHASE2_RUNTIME_URL", "postgresql://perchpoint_runtime:pw@127.0.0.1:5432/perchpoint_phase2")
    monkeypatch.setenv("PHASE2_JWT_SECRET", "local-test-secret-value")
    monkeypatch.setenv("PHASE2_DEV_PASSWORD", "local-test-password")
    monkeypatch.setenv("PHASE2_WEBHOOK_SECRET", "local-test-webhook")
    loaded = Settings.load()
    assert loaded.admin_url.startswith("postgresql+psycopg://")
    assert loaded.migrator_url.startswith("postgresql+psycopg://")
    assert loaded.runtime_url.startswith("postgresql+psycopg://")


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
