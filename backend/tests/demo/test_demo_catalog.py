from pathlib import Path

from fastapi.testclient import TestClient

from perchpoint.demo_catalog import FEATURES, HOUSEHOLDS, LISTINGS, PAGE_SIZE, search_demo
from perchpoint.demo_center import demo_enabled
from perchpoint.routes import create_app


def test_account_lines_reconcile_to_the_cohort():
    from perchpoint.demo_catalog import account_statement, cohort_summary

    summary = cohort_summary()
    past_due = 0
    for row in HOUSEHOLDS:
        statement = account_statement(row)
        explained = sum(line["amount_minor"] for line in statement["lines"] if line["kind"] != "dispute")
        assert explained == statement["due_minor"]
        assert statement["money_moved"] is False
        past_due += statement["past_due_minor"]
    assert summary["past_due_accounts"] == 2
    assert summary["past_due_minor"] == past_due == 427500


def test_default_catalog_is_twenty_homes_on_two_pages():
    assert len(LISTINGS) == 20
    assert PAGE_SIZE == 10
    first = search_demo({})
    second = search_demo({"page": "2"})
    third = search_demo({"page": "3"})
    assert [len(first["records"]), len(second["records"]), len(third["records"])] == [10, 10, 0]
    seen = [row["slug"] for page in (1, 2) for row in search_demo({"page": page})["records"]]
    assert len(seen) == len(set(seen)) == 20
    assert "Avery" not in str(first["records"])
    assert all(row["occupancy"] == "leased" for row in LISTINGS)
    assert all(
        ("apartment-exterior" in row["hero"]) if row["home_type"] == "apartment" else ("house-exterior" in row["hero"])
        for row in LISTINGS
    )


def test_filters_compose_and_reject_invalid_values():
    houses = search_demo({"home_type": "house", "bedrooms": "3", "min_sqft": "1000"})
    assert houses["total"] > 0
    assert all(row["home_type"] == "house" and row["bedrooms"] == 3 and row["sqft"] >= 1000 for row in houses["records"])
    try:
        search_demo({"home_type": "duplex"})
    except ValueError:
        return
    raise AssertionError("invalid home type was accepted")


def test_feature_inventory_matches_registered_routes():
    source = (Path(__file__).resolve().parents[3] / "frontend" / "src" / "App.js").read_text(encoding="utf-8")
    assert FEATURES
    for feature in FEATURES:
        if feature["executable"]:
            assert feature["route"]
            assert feature["route"] == "/" or f'path="{feature["route"]}"' in source
        else:
            assert feature["state"] == "intentionally_disabled"
            assert feature["route"] is None


def test_persona_enter_rotates_the_server_session(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.setenv("PHASE2_LOCAL_AUTH", "development")
    monkeypatch.setenv("PHASE3_ENVIRONMENT", "local")
    monkeypatch.setenv("PHASE6_ALLOWED_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000,http://testserver")
    client = TestClient(create_app())
    owner = client.post("/api/v2/demo/enter", json={"persona": "owner"})
    assert owner.status_code == 200
    assert owner.json()["role"] == "owner"
    assert owner.json()["email"] == "dossnathan@gmail.com"
    assert owner.json()["workspace"] == "/owner"
    owner_token = owner.cookies.get("pp_session")
    resident = client.post(
        "/api/v2/demo/enter",
        json={"persona": "resident"},
        headers={
            "x-perchpoint-csrf": client.cookies.get("pp_csrf") or "",
            "origin": "http://testserver",
            "referer": "http://testserver/demo",
        },
    )
    assert resident.status_code == 200, resident.text
    current = client.get("/api/v2/auth/me")
    assert current.status_code == 200
    assert current.json()["role_name"] == "resident"
    stale = TestClient(create_app())
    stale.cookies.set("pp_session", owner_token)
    assert stale.get("/api/v2/auth/me").status_code in {401, 403}


def test_owner_workspace_rejects_other_personas(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.setenv("PHASE2_LOCAL_AUTH", "development")
    monkeypatch.setenv("PHASE3_ENVIRONMENT", "local")
    monkeypatch.setenv("PHASE6_ALLOWED_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000,http://testserver")
    client = TestClient(create_app())
    resident = client.post("/api/v2/demo/enter", json={"persona": "resident"})
    assert resident.status_code == 200
    assert resident.json()["email"] == "dossnathan2@gmail.com"
    assert client.get("/api/v2/demo/owner").status_code == 403
    owner = client.post(
        "/api/v2/demo/enter",
        json={"persona": "owner"},
        headers={"x-perchpoint-csrf": client.cookies.get("pp_csrf") or "", "origin": "http://testserver", "referer": "http://testserver/demo"},
    )
    assert owner.status_code == 200
    workspace = client.get("/api/v2/demo/owner")
    assert workspace.status_code == 200, workspace.text
    assert workspace.json()["email"] == "dossnathan@gmail.com"
    assert workspace.json()["cards"]


def test_demo_routes_fail_closed_without_the_flag(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert demo_enabled() is False
    client = TestClient(create_app())
    assert client.get("/api/v2/demo/status").status_code == 404
    assert client.get("/api/v2/demo/personas").status_code == 404
    assert client.get("/api/v2/public/demo/listings").status_code == 404
    assert client.post("/api/v2/demo/enter", json={"persona": "owner"}).status_code == 404
    assert client.get("/api/v2/demo/household").status_code == 404


def test_resident_session_sees_one_household_and_not_the_staff_portal(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.setenv("PHASE2_LOCAL_AUTH", "development")
    monkeypatch.setenv("PHASE3_ENVIRONMENT", "local")
    monkeypatch.setenv("PHASE6_ALLOWED_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000,http://testserver")
    client = TestClient(create_app())
    assert client.get("/api/v2/demo/household").status_code == 401
    entered = client.post("/api/v2/demo/enter", json={"persona": "resident"})
    assert entered.status_code == 200
    household = client.get("/api/v2/demo/household")
    assert household.status_code == 200, household.text
    body = household.json()
    assert body["person_label"]
    assert "SAMPLE" in body["sample_marker"]
    assert "reference" not in body
    assert body["payments_open"] is False
    staff = client.post(
        "/api/v2/leasing/portal/home",
        json={"reference": "portal-163b9e3d72784c98"},
        headers={"x-perchpoint-csrf": client.cookies.get("pp_csrf") or "", "origin": "http://testserver"},
    )
    assert staff.status_code == 403
    lease = client.get("/api/v2/demo/documents/demo-01/lease")
    assert lease.status_code == 200
    assert "Avery Morgan" in lease.text
    assert "SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION" in lease.text
    other = client.get("/api/v2/demo/documents/demo-02/statement")
    assert other.status_code == 403


def test_resident_request_reaches_the_staff_queue(monkeypatch, tmp_path):
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.setenv("PHASE2_LOCAL_AUTH", "development")
    monkeypatch.setenv("PHASE3_ENVIRONMENT", "local")
    monkeypatch.setenv("PHASE6_ALLOWED_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000,http://testserver")
    monkeypatch.setattr("perchpoint.demo_center.REQUEST_FILE", tmp_path / "requests.json")
    client = TestClient(create_app())
    entered = client.post("/api/v2/demo/enter", json={"persona": "resident"})
    assert entered.status_code == 200
    headers = {"x-perchpoint-csrf": client.cookies.get("pp_csrf") or "", "origin": "http://testserver", "referer": "http://testserver/portal"}
    saved = client.post("/api/v2/demo/requests", json={"kind": "contact", "note": "Please update the phone on file.", "idempotency_key": "contact-once-0001"}, headers=headers)
    assert saved.status_code == 200, saved.text
    again = client.post("/api/v2/demo/requests", json={"kind": "contact", "note": "Please update the phone on file.", "idempotency_key": "contact-once-0001"}, headers=headers)
    assert again.json()["id"] == saved.json()["id"]
    household = client.get("/api/v2/demo/household")
    assert household.json()["requests"][0]["state"] == "submitted"
    denied = client.post(f"/api/v2/demo/requests/{saved.json()['id']}/review", headers=headers)
    assert denied.status_code == 403
    owner = client.post("/api/v2/demo/enter", json={"persona": "owner"}, headers=headers)
    assert owner.status_code == 200
    owner_headers = {"x-perchpoint-csrf": client.cookies.get("pp_csrf") or "", "origin": "http://testserver", "referer": "http://testserver/owner"}
    queue = client.get("/api/v2/demo/work")
    assert any(item["workflow"] == "Request" and "Avery Morgan" in item["subject"] for item in queue.json()["items"])
    reviewed = client.post(f"/api/v2/demo/requests/{saved.json()['id']}/review", headers=owner_headers)
    assert reviewed.status_code == 200
    assert reviewed.json()["state"] == "reviewed"
