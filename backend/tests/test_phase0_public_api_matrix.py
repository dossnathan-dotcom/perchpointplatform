"""Public Phase 0 API matrix checks against external preview endpoints."""

import os

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="module")
def base_url():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="module")
def client():
    return requests.Session()


# phase0 public endpoint matrix for contracts and synthetic-only boundaries
@pytest.mark.parametrize(
    "endpoint,required_keys",
    [
        ("/api/rentals", {"units", "data_status"}),
        (
            "/api/foundation",
            {
                "version",
                "data_status",
                "production_authentication",
                "provider_execution",
                "canonical_persistence",
            },
        ),
        (
            "/api/foundation/portfolio",
            {
                "organizations",
                "ownership_entities",
                "properties",
                "buildings",
                "units",
                "shared_spaces",
                "assets",
            },
        ),
        (
            "/api/foundation/contracts",
            {
                "version",
                "data_status",
                "portfolio",
                "people",
                "permissions",
                "delegation",
                "integrations",
                "identity",
                "retention",
                "scenarios",
                "migration",
            },
        ),
    ],
)
def test_public_endpoints_status_content_type_and_shape(client, base_url, endpoint, required_keys):
    response = client.get(f"{base_url}{endpoint}", timeout=20)
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    assert "no-store" in response.headers.get("Cache-Control", "")
    assert response.headers.get("X-PerchPoint-Data") == "synthetic-phase-0"

    payload = response.json()
    assert required_keys.issubset(set(payload.keys()))


def test_rentals_units_and_status(client, base_url):
    response = client.get(f"{base_url}/api/rentals", timeout=20)
    body = response.json()
    assert body["data_status"] == "demonstration_phase_0"
    assert isinstance(body["units"], list)
    assert len(body["units"]) == 15
    assert all(unit.get("synthetic") is True for unit in body["units"])


def test_foundation_summary_synthetic_contract_flags(client, base_url):
    response = client.get(f"{base_url}/api/foundation", timeout=20)
    body = response.json()
    assert body["data_status"] == "synthetic_contracts_only"
    assert body["production_authentication"] is False
    assert body["provider_execution"] is False
    assert body["canonical_persistence"] is False


def test_contracts_contains_disconnected_and_no_credential_references(client, base_url):
    response = client.get(f"{base_url}/api/foundation/contracts", timeout=20)
    body = response.json()
    integrations = body["integrations"]

    assert all(item.get("environment") == "synthetic" for item in integrations)
    assert all(item.get("connection_status") == "disconnected" for item in integrations)
    assert all(item.get("credential_reference") is None for item in integrations)


def test_public_endpoints_do_not_require_cookie_or_token(client, base_url):
    headers = {"Authorization": "Bearer fake-token", "Cookie": "session=fake"}
    with_auth = client.get(f"{base_url}/api/foundation/contracts", headers=headers, timeout=20)
    without_auth = client.get(f"{base_url}/api/foundation/contracts", timeout=20)

    assert with_auth.status_code == 200
    assert without_auth.status_code == 200
    assert with_auth.json()["version"] == without_auth.json()["version"]
