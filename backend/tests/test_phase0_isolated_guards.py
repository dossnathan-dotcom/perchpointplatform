"""Isolated FastAPI/TestClient checks for Phase 0 route guards and synthetic fixture enforcement."""

import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, "/app/backend")

from foundation.routes import router as foundation_router
from server import api_router


@pytest.fixture
def phase0_client(monkeypatch):
    monkeypatch.setenv("PHASE0_ENABLED", "true")
    app = FastAPI()
    app.include_router(api_router)
    app.include_router(foundation_router)
    return TestClient(app)


# phase0 flag behavior and method/path error handling
def test_rentals_disabled_or_invalid_flag_returns_empty_units(monkeypatch):
    app = FastAPI()
    app.include_router(api_router)
    app.include_router(foundation_router)

    monkeypatch.setenv("PHASE0_ENABLED", "false")
    client = TestClient(app)
    off = client.get("/api/rentals")
    assert off.status_code == 200
    assert off.json()["units"] == []
    assert off.json()["data_status"] == "demonstration_phase_0"

    monkeypatch.setenv("PHASE0_ENABLED", "invalid")
    invalid = client.get("/api/rentals")
    assert invalid.status_code == 200
    assert invalid.json()["units"] == []

    monkeypatch.delenv("PHASE0_ENABLED", raising=False)
    missing = client.get("/api/rentals")
    assert missing.status_code == 200
    assert missing.json()["units"] == []


@pytest.mark.parametrize("flag", ["false", "invalid", None])
def test_foundation_routes_404_when_phase0_not_enabled(monkeypatch, flag):
    app = FastAPI()
    app.include_router(api_router)
    app.include_router(foundation_router)
    if flag is None:
        monkeypatch.delenv("PHASE0_ENABLED", raising=False)
    else:
        monkeypatch.setenv("PHASE0_ENABLED", flag)

    client = TestClient(app)
    for endpoint in ("/api/foundation", "/api/foundation/portfolio", "/api/foundation/contracts"):
        response = client.get(endpoint)
        assert response.status_code == 404
        assert response.json()["detail"] == "Seeded contract previews disabled"


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/rentals"),
        ("post", "/api/foundation"),
        ("post", "/api/foundation/contracts"),
        ("put", "/api/foundation/portfolio"),
    ],
)
def test_unsupported_methods_return_405_json(phase0_client, method, path):
    response = getattr(phase0_client, method)(path, json={"role": "owner", "permissions": ["all"]})
    assert response.status_code == 405
    assert "detail" in response.json()


@pytest.mark.parametrize("path", ["/api/foundation/nope", "/api/rentals/nope", "/api/unknown"])
def test_unknown_subpaths_return_404_json(phase0_client, path):
    response = phase0_client.get(path)
    assert response.status_code == 404
    assert "detail" in response.json()


def test_query_params_do_not_change_dataset_or_permissions(phase0_client):
    baseline = phase0_client.get("/api/foundation/contracts")
    injected = phase0_client.get(
        "/api/foundation/contracts",
        params={"role": "owner", "org": "prod", "permissions": "admin", "provider": "live"},
    )
    assert baseline.status_code == 200
    assert injected.status_code == 200
    assert baseline.json() == injected.json()


def test_cannot_supply_live_policy_via_post_body(phase0_client):
    response = phase0_client.post(
        "/api/foundation/contracts",
        json={
            "production_authentication": True,
            "provider_execution": True,
            "canonical_persistence": True,
            "credential_reference": "secret",
        },
    )
    assert response.status_code == 405
    assert "detail" in response.json()


# checked_fixture fail-closed guard behavior with malicious deterministic injections
def test_guard_rejects_non_synthetic_versioned_record(monkeypatch):
    from foundation import routes

    monkeypatch.setenv("PHASE0_ENABLED", "true")
    app = FastAPI()
    app.include_router(foundation_router)
    client = TestClient(app)

    malicious = {
        "version": "0.1.0",
        "data_status": "synthetic_contracts_only",
        "portfolio": {"schema_version": "0.1.0", "id": "x1", "synthetic": False},
        "people": {},
        "permissions": {},
        "delegation": {},
        "integrations": [],
        "identity": [],
        "retention": {},
        "scenarios": [],
        "migration": {},
    }
    monkeypatch.setattr(routes, "foundation_bundle", lambda: malicious)

    response = client.get("/api/foundation/contracts")
    assert response.status_code == 503
    assert response.json()["detail"] == "Synthetic preview unavailable"


def test_guard_rejects_non_null_credential_reference(monkeypatch):
    from foundation import routes

    monkeypatch.setenv("PHASE0_ENABLED", "true")
    app = FastAPI()
    app.include_router(foundation_router)
    client = TestClient(app)

    monkeypatch.setattr(
        routes,
        "foundation_bundle",
        lambda: {
            "version": "0.1.0",
            "data_status": "synthetic_contracts_only",
            "portfolio": {},
            "people": {},
            "permissions": {},
            "delegation": {},
            "integrations": [
                {
                    "id": "provider-1",
                    "provider_type": "screening",
                    "provider_name": "Fake",
                    "environment": "synthetic",
                    "connection_status": "disconnected",
                    "credential_reference": "vault://secret",
                }
            ],
            "identity": [],
            "retention": {},
            "scenarios": [],
            "migration": {},
        },
    )
    response = client.get("/api/foundation/contracts")
    assert response.status_code == 503
    assert response.json()["detail"] == "Synthetic preview unavailable"


def test_guard_rejects_forbidden_raw_credential_keys_without_secret_echo(monkeypatch):
    from foundation import routes

    monkeypatch.setenv("PHASE0_ENABLED", "true")
    app = FastAPI()
    app.include_router(foundation_router)
    client = TestClient(app)

    secret_value = "SHOULD_NOT_LEAK"
    monkeypatch.setattr(
        routes,
        "foundation_bundle",
        lambda: {
            "version": "0.1.0",
            "data_status": "synthetic_contracts_only",
            "portfolio": {},
            "people": {},
            "permissions": {"api_key": secret_value},
            "delegation": {},
            "integrations": [],
            "identity": [],
            "retention": {},
            "scenarios": [],
            "migration": {},
        },
    )
    response = client.get("/api/foundation/contracts")
    assert response.status_code == 503
    assert response.json()["detail"] == "Synthetic preview unavailable"
    assert secret_value not in response.text


def test_guard_rejects_provider_connected_or_non_synthetic(monkeypatch):
    from foundation import routes

    monkeypatch.setenv("PHASE0_ENABLED", "true")
    app = FastAPI()
    app.include_router(foundation_router)
    client = TestClient(app)

    monkeypatch.setattr(
        routes,
        "foundation_bundle",
        lambda: {
            "version": "0.1.0",
            "data_status": "synthetic_contracts_only",
            "portfolio": {},
            "people": {},
            "permissions": {},
            "delegation": {},
            "integrations": [
                {
                    "id": "provider-live",
                    "provider_type": "payments",
                    "provider_name": "Live Pay",
                    "environment": "production",
                    "connection_status": "connected",
                    "credential_reference": None,
                }
            ],
            "identity": [],
            "retention": {},
            "scenarios": [],
            "migration": {},
        },
    )
    response = client.get("/api/foundation/contracts")
    assert response.status_code == 503
    assert response.json()["detail"] == "Synthetic preview unavailable"


def test_guard_rejects_runtime_enforcement_or_execution_flags(monkeypatch):
    from foundation import routes

    monkeypatch.setenv("PHASE0_ENABLED", "true")
    app = FastAPI()
    app.include_router(foundation_router)
    client = TestClient(app)

    monkeypatch.setattr(
        routes,
        "foundation_bundle",
        lambda: {
            "version": "0.1.0",
            "data_status": "synthetic_contracts_only",
            "production_authentication": True,
            "provider_execution": True,
            "canonical_persistence": False,
            "runtime_enforcement": "enabled",
            "portfolio": {},
            "people": {},
            "permissions": {},
            "delegation": {},
            "integrations": [],
            "identity": [],
            "retention": {},
            "scenarios": [],
            "migration": {},
        },
    )
    response = client.get("/api/foundation/contracts")
    assert response.status_code == 503
    assert response.json()["detail"] == "Synthetic preview unavailable"
