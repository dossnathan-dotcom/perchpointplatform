import os

import pytest
from fastapi.testclient import TestClient

from perchpoint.abuse import assess_inquiry, client_digest
from perchpoint.http_security import CSP, security_headers
from perchpoint.routes import create_app
from perchpoint.settings import Phase2ConfigurationError, Settings


def test_honeypot_and_timing_reject_without_storing_raw_ip():
    assert assess_inquiry({"company_website": "https://spam.example", "message": "hi"}, "203.0.113.10") == "rejected"
    assert "203.0.113.10" not in client_digest("203.0.113.10")
    os.environ["PHASE4_ABUSE_MIN_MS"] = "1500"
    try:
        assert assess_inquiry({"message": "hi", "started_at_ms": 1_000}, "203.0.113.11", now=1.2) == "rejected"
    finally:
        os.environ["PHASE4_ABUSE_MIN_MS"] = "0"


def test_security_headers_enforce_csp_without_unsafe_eval():
    headers = security_headers("text/html", "/")
    assert "unsafe-eval" not in headers["content-security-policy"]
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert headers["cache-control"] == "no-store"
    assert headers["x-frame-options"] == "DENY"
    asset = security_headers("text/javascript", "/static/js/main.abc123.js")
    assert asset["cache-control"].startswith("public")
    assert CSP == headers["content-security-policy"]


def test_live_response_carries_security_headers():
    response = TestClient(create_app()).get("/api/v2/health/live")
    assert response.status_code == 200
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"


def test_production_requires_distributed_abuse_protection(monkeypatch):
    monkeypatch.setenv("PHASE3_ENVIRONMENT", "production")
    monkeypatch.setenv("PHASE2_LOCAL_AUTH", "disabled")
    monkeypatch.setenv("PHASE2_ADMIN_URL", "postgresql://postgres:operational@db.internal:5432/postgres")
    monkeypatch.setenv("PHASE2_MIGRATOR_URL", "postgresql://migrator:operational@db.internal:5432/perchpoint")
    monkeypatch.setenv("PHASE2_RUNTIME_URL", "postgresql://runtime:operational@db.internal:5432/perchpoint")
    monkeypatch.setenv("PHASE2_JWT_SECRET", "operational-jwt-value-2026")
    monkeypatch.setenv("PHASE2_DEV_PASSWORD", "operational-dev-value-2026")
    monkeypatch.setenv("PHASE2_WEBHOOK_SECRET", "operational-webhook-value-2026")
    monkeypatch.delenv("PHASE4_ABUSE_PROVIDER", raising=False)
    with pytest.raises(Phase2ConfigurationError, match="distributed abuse protection"):
        Settings.load()
