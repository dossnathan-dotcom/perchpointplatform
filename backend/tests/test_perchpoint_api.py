"""PerchPoint API smoke and integration tests for Phase 0 demo flows."""

import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv


load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="session")
def api_base_url():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# health and catalog endpoints
def test_health_endpoint(api_client, api_base_url):
    response = api_client.get(f"{api_base_url}/api/health", timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "perchpoint"


# public properties feed returns seeded rental demonstration data
def test_properties_endpoint(api_client, api_base_url):
    response = api_client.get(f"{api_base_url}/api/properties", timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["data_status"] == "demonstration_phase_0"
    assert isinstance(data["properties"], list)
    assert len(data["properties"]) >= 4
    first = data["properties"][0]
    assert "id" in first and isinstance(first["id"], str)
    assert isinstance(first["rent"], int)
    assert isinstance(first["deposit"], int)


# showing/application lead capture endpoint
def test_create_showing_lead(api_client, api_base_url):
    payload = {
        "name": "TEST_QA User",
        "email": "qa.tester+showing@example.com",
        "intent": "showing",
        "message": "Please schedule an afternoon showing.",
        "property_id": "412-elm-unit-a",
        "preferred_date": "2026-03-10",
    }
    response = api_client.post(f"{api_base_url}/api/leads", json=payload, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["message"] == "Your request is in. HawkVision will follow up with the next step."
    assert isinstance(data["id"], str) and len(data["id"]) > 10


# application interest route shares same lead endpoint
def test_create_application_interest_lead(api_client, api_base_url):
    payload = {
        "name": "TEST_QA Applicant",
        "email": "qa.tester+apply@example.com",
        "intent": "application",
        "message": "Interested in next application steps.",
        "property_id": "clifton-duplex-unit-b",
        "preferred_date": "2026-03-14",
    }
    response = api_client.post(f"{api_base_url}/api/leads", json=payload, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert isinstance(data["id"], str) and len(data["id"]) > 10


# non-emergency maintenance submission flow
def test_create_maintenance_request(api_client, api_base_url):
    payload = {
        "name": "TEST_QA Resident",
        "email": "qa.tester+maintenance@example.com",
        "property_address": "412 Elm Street, Cincinnati, OH 45202",
        "unit": "412-A",
        "category": "Plumbing",
        "description": "Kitchen sink leaking steadily below the trap.",
        "permission_to_enter": True,
    }
    response = api_client.post(f"{api_base_url}/api/maintenance-requests", json=payload, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "submitted"
    assert data["message"] == "Your maintenance request has been recorded for review."
    assert isinstance(data["id"], str) and data["id"].startswith("PP-")


# validation handling for incomplete maintenance payload
def test_maintenance_validation_error(api_client, api_base_url):
    payload = {
        "name": "A",
        "email": "invalid-email",
        "property_address": "12",
        "unit": "",
        "category": "X",
        "description": "short",
        "permission_to_enter": False,
    }
    response = api_client.post(f"{api_base_url}/api/maintenance-requests", json=payload, timeout=20)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
