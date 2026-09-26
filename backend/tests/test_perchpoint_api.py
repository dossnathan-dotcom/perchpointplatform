"""PerchPoint API smoke and integration tests for Phase 0 demo flows."""


# health and catalog endpoints
def test_health_endpoint(phase0_http_client, phase0_base_url):
    response = phase0_http_client.get(f"{phase0_base_url}/api/health", timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "perchpoint"


# public properties feed returns canonical property records
def test_properties_endpoint(phase0_http_client, phase0_base_url):
    response = phase0_http_client.get(f"{phase0_base_url}/api/properties", timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["data_status"] == "demonstration_phase_0"
    assert isinstance(data["properties"], list)
    assert len(data["properties"]) >= 4
    first = data["properties"][0]
    assert "id" in first and isinstance(first["id"], str)
    assert "ownership_entity_id" in first
    assert "property_type" in first


# showing/application lead capture endpoint
def test_create_showing_lead(phase0_http_client, phase0_base_url):
    payload = {
        "name": "TEST_QA User",
        "email": "qa.tester+showing@example.com",
        "intent": "showing",
        "message": "Please schedule an afternoon showing.",
        "property_id": "412-elm-unit-a",
        "preferred_date": "2026-03-10",
    }
    response = phase0_http_client.post(f"{phase0_base_url}/api/leads", json=payload, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["message"] == "Synthetic request recorded. No showing, application, or notification was created."
    assert isinstance(data["id"], str) and len(data["id"]) > 10


# application interest route shares same lead endpoint
def test_create_application_interest_lead(phase0_http_client, phase0_base_url):
    payload = {
        "name": "TEST_QA Applicant",
        "email": "qa.tester+apply@example.com",
        "intent": "application",
        "message": "Interested in next application steps.",
        "property_id": "clifton-duplex-unit-b",
        "preferred_date": "2026-03-14",
    }
    response = phase0_http_client.post(f"{phase0_base_url}/api/leads", json=payload, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["message"] == "Synthetic request recorded. No showing, application, or notification was created."
    assert isinstance(data["id"], str) and len(data["id"]) > 10


# non-emergency maintenance submission flow
def test_create_maintenance_request(phase0_http_client, phase0_base_url):
    payload = {
        "name": "TEST_QA Resident",
        "email": "qa.tester+maintenance@example.com",
        "property_address": "412 Elm Street, Cincinnati, OH 45202",
        "unit": "412-A",
        "category": "Plumbing",
        "description": "Kitchen sink leaking steadily below the trap.",
        "permission_to_enter": True,
    }
    response = phase0_http_client.post(
        f"{phase0_base_url}/api/maintenance-requests", json=payload, timeout=20
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "submitted"
    assert data["message"] == "Synthetic maintenance request recorded. No dispatch or notification was sent."
    assert isinstance(data["id"], str) and data["id"].startswith("PP-")


# canonical unit/property mismatch should be rejected
def test_create_lead_rejects_unit_property_mismatch(phase0_http_client, phase0_base_url):
    rentals = phase0_http_client.get(f"{phase0_base_url}/api/rentals", timeout=20)
    assert rentals.status_code == 200
    units = rentals.json()["units"]
    target_unit = next((u for u in units if u.get("property_id") and u.get("id")), None)
    wrong_property = next((u["property_id"] for u in units if u["property_id"] != target_unit["property_id"]), None)
    assert target_unit is not None and wrong_property is not None

    payload = {
        "name": "TEST_QA Mismatch",
        "email": "qa.tester+mismatch@example.com",
        "intent": "showing",
        "message": "Testing canonical mismatch guard",
        "property_id": wrong_property,
        "unit_id": target_unit["id"],
    }
    response = phase0_http_client.post(f"{phase0_base_url}/api/leads", json=payload, timeout=20)
    assert response.status_code == 422
    assert "Unit must belong to the referenced canonical property" in response.json()["detail"]


# synthetic-only domain validation for public forms
def test_lead_rejects_non_example_domain(phase0_http_client, phase0_base_url):
    payload = {
        "name": "TEST_QA Domain Guard",
        "email": "qa.real@gmail.com",
        "intent": "application",
        "message": "Should fail synthetic domain rule",
        "property_id": "412-elm-unit-a",
    }
    response = phase0_http_client.post(f"{phase0_base_url}/api/leads", json=payload, timeout=20)
    assert response.status_code == 422
    assert "Synthetic requests only" in response.json()["detail"]


# auth endpoint is intentionally absent in phase 0
def test_auth_endpoint_absent_by_design(phase0_http_client, phase0_base_url):
    response = phase0_http_client.post(
        f"{phase0_base_url}/api/auth/login",
        json={"email": "any@example.com", "password": "unused"},
        timeout=20,
    )
    assert response.status_code == 404


# validation handling for incomplete maintenance payload
def test_maintenance_validation_error(phase0_http_client, phase0_base_url):
    payload = {
        "name": "A",
        "email": "invalid-email",
        "property_address": "12",
        "unit": "",
        "category": "X",
        "description": "short",
        "permission_to_enter": False,
    }
    response = phase0_http_client.post(
        f"{phase0_base_url}/api/maintenance-requests", json=payload, timeout=20
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
