"""Phase 5 closeout paths: processing, access, export, search, import, and replay."""
from uuid import uuid4

import fitz
from fastapi.testclient import TestClient

from perchpoint.phase5_closeout import _safe_csv, sanitize_text
from perchpoint.routes import create_app
from tests.phase5.test_canonical import _auth, _login


def _property(client, token):
    response = client.post(
        "/api/v2/properties",
        headers=_auth(token),
        json={"name": "Closeout Court", "property_type": "single_family", "idempotency_key": "prop-" + uuid4().hex},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _upload(client, token, property_id, filename, content, media, title="Closeout note"):
    return client.post(
        "/api/v2/documents",
        headers=_auth(token),
        data={
            "title": title,
            "document_class": "internal-administration",
            "classification": "internal",
            "primary_resource_type": "property",
            "primary_resource_id": property_id,
            "idempotency_key": "doc-" + uuid4().hex,
        },
        files={"upload": (filename, content, media)},
    )


def test_text_is_sanitized_and_formula_cells_are_neutralized():
    assert "<script>" not in sanitize_text("Boiler <script>alert(1)</script> note")
    rendered = _safe_csv([{"document_id": "=cmd", "sha256": "abc"}])
    assert "'=cmd" in rendered


def test_extraction_preview_access_and_disposition(tmp_path, monkeypatch):
    monkeypatch.setenv("PHASE5_OBJECT_ROOT", str(tmp_path))
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Elm Court boiler certificate")
    payload = document.tobytes()
    document.close()
    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    property_id = _property(client, token)
    uploaded = _upload(client, token, property_id, "note.pdf", payload, "application/pdf", "Boiler certificate")
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["lifecycle"] == "available"
    document_id = uploaded.json()["id"]
    processed = client.post("/api/v2/phase5/jobs/process", headers=_auth(token))
    assert processed.status_code == 200, processed.text
    found = client.get("/api/v2/search", headers=_auth(token), params={"q": "boiler"})
    assert found.status_code == 200
    assert any(item["resource_id"] == document_id for item in found.json()["results"])
    access = client.post(f"/api/v2/documents/{document_id}/access", headers=_auth(token))
    assert access.status_code == 200, access.text
    assert "token" in access.json()
    body = client.get(
        f"/api/v2/documents/{document_id}/content",
        headers={**_auth(token), "X-PerchPoint-Document-Token": access.json()["token"], "Range": "bytes=0-3"},
    )
    assert body.status_code == 200
    assert "no-store" in body.headers["cache-control"]
    assert body.content == payload[:4]
    monkeypatch.setenv("PHASE5_ACCESS_SECONDS", "0")
    expired = client.post(f"/api/v2/documents/{document_id}/access", headers=_auth(token))
    denied = client.get(
        f"/api/v2/documents/{document_id}/content",
        headers={**_auth(token), "X-PerchPoint-Document-Token": expired.json()["token"]},
    )
    assert denied.status_code == 410
    missing = client.get(f"/api/v2/documents/{uuid4()}/content", headers=_auth(token))
    assert missing.status_code == 404
    disposed = client.post(
        f"/api/v2/documents/{document_id}/disposition",
        headers=_auth(token),
        json={"expected_version": 1, "confirmation": "destroy", "confirm_again": "destroy", "idempotency_key": "disp-" + uuid4().hex},
    )
    assert disposed.status_code == 200, disposed.text
    hidden = client.get("/api/v2/search", headers=_auth(token), params={"q": "Boiler certificate"})
    assert all(item["resource_id"] != document_id for item in hidden.json()["results"])


def test_scanner_unavailable_is_not_clean(tmp_path, monkeypatch):
    monkeypatch.setenv("PHASE5_OBJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("PHASE5_SCANNER_MODE", "live")
    monkeypatch.delenv("PHASE5_CLAMAV_HOST", raising=False)
    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    property_id = _property(client, token)
    uploaded = _upload(client, token, property_id, "note.txt", b"Synthetic operating note", "text/plain")
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["lifecycle"] == "scanning"
    assert uploaded.json()["reason"] == "scanner_unavailable"


def test_saved_search_stays_private_until_shared():
    client = TestClient(create_app())
    ann = _login(client, "ann.synthetic@example.com")
    nathan = _login(client, "nathan.synthetic@example.com")
    other = _login(client, "isolation.synthetic@example.com")
    created = client.post(
        "/api/v2/search/saved",
        headers=_auth(ann),
        json={"name": "Boiler queue", "query": "boiler", "idempotency_key": "save-" + uuid4().hex},
    )
    assert created.status_code == 201, created.text
    search_id = created.json()["id"]
    nathan_saved = client.get("/api/v2/search/saved", headers=_auth(nathan)).json()["saved"]
    assert all(item["id"] != search_id for item in nathan_saved)
    assert client.get("/api/v2/search/saved", headers=_auth(other)).status_code == 200
    assert all(item["id"] != search_id for item in client.get("/api/v2/search/saved", headers=_auth(other)).json()["saved"])
    shared = client.post(
        f"/api/v2/search/saved/{search_id}/share",
        headers=_auth(ann),
        json={"visibility": "organization", "idempotency_key": "share-" + uuid4().hex},
    )
    assert shared.status_code == 200, shared.text
    visible = client.get("/api/v2/search/saved", headers=_auth(nathan)).json()["saved"]
    assert any(item["id"] == search_id for item in visible)
    renamed = client.post(
        f"/api/v2/search/saved/{search_id}",
        headers=_auth(ann),
        json={"name": "Boiler queue renamed", "query": "boiler", "idempotency_key": "rename-" + uuid4().hex},
    )
    assert renamed.status_code == 200, renamed.text
    copied = client.post(
        f"/api/v2/search/saved/{search_id}/duplicate",
        headers=_auth(ann),
        json={"idempotency_key": "copy-" + uuid4().hex},
    )
    assert copied.status_code == 201, copied.text
    assert copied.json()["visibility"] == "private"
    assert all(item["id"] != search_id for item in client.get("/api/v2/search/saved", headers=_auth(other)).json()["saved"])


def test_import_approval_apply_and_rollback():
    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    name = "Import " + uuid4().hex[:8]
    staged = client.post(
        "/api/v2/imports",
        headers=_auth(token),
        json={"content": f"name\n{name}\n", "idempotency_key": "imp-" + uuid4().hex},
    )
    assert staged.status_code == 201, staged.text
    batch_id = staged.json()["id"]
    blocked = client.post(f"/api/v2/imports/{batch_id}/apply", headers=_auth(token), json={"idempotency_key": "apply-" + uuid4().hex})
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "approval_required"
    dry = client.post(f"/api/v2/imports/{batch_id}/dry-run", headers=_auth(token))
    assert dry.status_code == 200
    approved = client.post(f"/api/v2/imports/{batch_id}/approve", headers=_auth(token), json={"idempotency_key": "approve-" + uuid4().hex})
    assert approved.status_code == 200, approved.text
    applied = client.post(f"/api/v2/imports/{batch_id}/apply", headers=_auth(token), json={"idempotency_key": "apply2-" + uuid4().hex})
    assert applied.status_code == 200, applied.text
    assert applied.json()["created"] == 1
    rolled = client.post(f"/api/v2/imports/{batch_id}/rollback", headers=_auth(token), json={"idempotency_key": "roll-" + uuid4().hex})
    assert rolled.status_code == 200, rolled.text
    assert rolled.json()["removed"] == 1


def test_replay_reconciles_and_diagnostics_are_admin_only():
    client = TestClient(create_app())
    ann = _login(client, "ann.synthetic@example.com")
    nathan = _login(client, "nathan.synthetic@example.com")
    denied = client.get("/api/v2/phase5/diagnostics", headers=_auth(ann))
    assert denied.status_code == 404
    allowed = client.get("/api/v2/phase5/diagnostics", headers=_auth(nathan))
    assert allowed.status_code == 200
    assert "scanner_mode" in allowed.json()
    replay = client.post("/api/v2/replay", headers=_auth(nathan))
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "reconciled"
    again = client.post("/api/v2/replay", headers=_auth(nathan))
    assert again.json()["actual"] == again.json()["expected"]


def test_owner_quality_queue_is_material_only():
    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    staged = client.post(
        "/api/v2/imports",
        headers=_auth(token),
        json={"content": "name\n=cmd|danger\n", "idempotency_key": "imp-" + uuid4().hex},
    )
    assert staged.json()["blockers"] == 1
    findings = client.get("/api/v2/quality", headers=_auth(token))
    assert findings.status_code == 200
    assert any(item["severity"] == "blocker" for item in findings.json()["findings"])
    finding_id = findings.json()["findings"][0]["id"]
    resolved = client.post(
        f"/api/v2/quality/{finding_id}/resolve",
        headers=_auth(token),
        json={"reason": "Synthetic review", "idempotency_key": "resolve-" + uuid4().hex},
    )
    assert resolved.status_code == 200, resolved.text
    events = client.get("/api/v2/audit/events", headers=_auth(token))
    assert events.status_code == 200
    assert all("password" not in item["action"] for item in events.json()["events"])
