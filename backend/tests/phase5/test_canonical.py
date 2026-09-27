"""Phase 5 search isolation, documents, holds, and imports."""
import os
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from foundation.seeds import sid
from perchpoint.db import engine_for, runtime_transaction
from perchpoint.phase5 import verify_digest
from perchpoint.routes import create_app
from perchpoint.settings import Settings


def _settings() -> Settings:
    return Settings.load()


def _admin():
    return engine_for(_settings().admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")


def _login(client, email):
    import bcrypt

    password = os.environ["PHASE2_DEV_PASSWORD"]
    digest = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    admin = _admin()
    with admin.begin() as connection:
        connection.execute(text("UPDATE accounts SET password_hash = :password WHERE email = :email"), {"password": digest, "email": email})
    admin.dispose()
    response = client.post("/api/v2/session", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_runtime_still_cannot_update_audit():
    admin = _admin()
    with admin.connect() as connection:
        allowed = connection.execute(text("SELECT has_table_privilege('perchpoint_runtime', 'audit_events', 'UPDATE')")).scalar()
    admin.dispose()
    assert allowed is False


def test_search_does_not_leak_another_organization():
    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    marker = "Canary " + uuid4().hex[:8]
    created = client.post(
        "/api/v2/parties",
        headers=_auth(token),
        json={"party_kind": "person", "display_name": marker, "idempotency_key": "party-" + uuid4().hex},
    )
    assert created.status_code == 201, created.text
    hidden = "Hidden " + uuid4().hex[:8]
    admin = _admin()
    other = uuid4()
    with admin.connect() as connection:
        connection.execute(text("INSERT INTO organizations (id, name, synthetic) VALUES (:id, 'Other Synthetic Org', true)"), {"id": other})
        connection.execute(
            text(
                """
                INSERT INTO search_documents (
                  organization_id, id, resource_type, resource_id, title, body, classification
                ) VALUES (:org, :id, 'party', :resource, :title, '', 'internal')
                """
            ),
            {"org": other, "id": uuid4(), "resource": uuid4(), "title": hidden},
        )
        connection.commit()
    admin.dispose()
    visible = client.get("/api/v2/search", headers=_auth(token), params={"q": marker})
    assert visible.status_code == 200, visible.text
    assert sum(1 for item in visible.json()["results"] if item["title"] == marker) == 1
    leaked = client.get("/api/v2/search", headers=_auth(token), params={"q": hidden})
    assert all(item["title"] != hidden for item in leaked.json()["results"])


def test_public_search_omits_internal_parties():
    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    marker = "InternalOnly " + uuid4().hex[:8]
    client.post(
        "/api/v2/parties",
        headers=_auth(token),
        json={"party_kind": "vendor", "display_name": marker, "idempotency_key": "party-" + uuid4().hex},
    )
    public = client.get("/api/v2/search/public", params={"q": marker})
    assert public.status_code == 200
    assert public.json()["results"] == []


def test_eicar_upload_is_quarantined_and_hold_blocks_disposition(tmp_path, monkeypatch):
    monkeypatch.setenv("PHASE5_OBJECT_ROOT", str(tmp_path))
    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    property_id = client.post(
        "/api/v2/properties",
        headers=_auth(token),
        json={"name": "Document Court", "property_type": "single_family", "idempotency_key": "prop-" + uuid4().hex},
    ).json()["id"]
    from perchpoint.phase5_files import EICAR

    response = client.post(
        "/api/v2/documents",
        headers=_auth(token),
        data={
            "title": "Suspicious note",
            "document_class": "internal-administration",
            "classification": "confidential",
            "primary_resource_type": "property",
            "primary_resource_id": property_id,
            "idempotency_key": "doc-" + uuid4().hex,
        },
        files={"upload": ("note.txt", b"see " + EICAR, "text/plain")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["lifecycle"] == "quarantined"
    clean = client.post(
        "/api/v2/documents",
        headers=_auth(token),
        data={
            "title": "Clean note",
            "document_class": "internal-administration",
            "classification": "internal",
            "primary_resource_type": "property",
            "primary_resource_id": property_id,
            "idempotency_key": "doc-" + uuid4().hex,
        },
        files={"upload": ("note.txt", b"Synthetic operating note", "text/plain")},
    )
    assert clean.status_code == 201, clean.text
    assert clean.json()["lifecycle"] == "available"
    document_id = clean.json()["id"]
    held = client.post(
        f"/api/v2/documents/{document_id}/hold",
        headers=_auth(token),
        json={"reason": "Synthetic preservation", "idempotency_key": "hold-" + uuid4().hex},
    )
    assert held.status_code == 200, held.text
    blocked = client.post(
        f"/api/v2/documents/{document_id}/disposition",
        headers=_auth(token),
        json={
            "expected_version": 2,
            "confirmation": "destroy",
            "confirm_again": "destroy",
            "idempotency_key": "disp-" + uuid4().hex,
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "legal_hold"


def test_formula_import_stays_staged():
    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    content = "name\n=cmd|danger\nAda Synthetic\n"
    staged = client.post(
        "/api/v2/imports",
        headers=_auth(token),
        json={"content": content, "idempotency_key": "imp-" + uuid4().hex},
    )
    assert staged.status_code == 201, staged.text
    assert staged.json()["blockers"] == 1
    applied = client.post(
        f"/api/v2/imports/{staged.json()['id']}/apply",
        headers=_auth(token),
        json={"idempotency_key": "apply-" + uuid4().hex},
    )
    assert applied.status_code == 409


def test_exclusive_relationship_cannot_overlap():
    admin = _admin()
    org = sid("organization-demo")
    first = uuid4()
    second = uuid4()
    with admin.connect() as connection:
        connection.execute(text("INSERT INTO parties (organization_id, id, party_kind, display_name) VALUES (:org, :id, 'person', 'Overlap A')"), {"org": org, "id": first})
        connection.execute(text("INSERT INTO parties (organization_id, id, party_kind, display_name) VALUES (:org, :id, 'household', 'Overlap House')"), {"org": org, "id": second})
        connection.execute(
            text(
                """
                INSERT INTO party_relationships (
                  organization_id, id, subject_party_id, object_party_id, relationship_kind, exclusive, effective_at
                ) VALUES (:org, :id, :subject, :object, 'primary_occupancy', true, now())
                """
            ),
            {"org": org, "id": uuid4(), "subject": first, "object": second},
        )
        try:
            connection.execute(
                text(
                    """
                    INSERT INTO party_relationships (
                      organization_id, id, subject_party_id, object_party_id, relationship_kind, exclusive, effective_at
                    ) VALUES (:org, :id, :subject, :object, 'primary_occupancy', true, now())
                    """
                ),
                {"org": org, "id": uuid4(), "subject": first, "object": second},
            )
            connection.commit()
            raised = False
        except Exception:
            connection.rollback()
            raised = True
    admin.dispose()
    assert raised is True


def test_digest_mismatch_is_detected():
    assert verify_digest("abc", "abc")["matches"] is True
    assert verify_digest("abc", "tampered")["matches"] is False


def test_missing_context_hides_parties():
    with runtime_transaction(_settings(), None, None, uuid4()) as connection:
        count = connection.execute(text("SELECT count(*) FROM parties")).scalar()
    assert count == 0
