"""Phase 20 intake, materials, time, evidence, and escalation."""
import base64
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from perchpoint.db import application_admin_connection
from perchpoint.demo_catalog import cohort_summary
from perchpoint.settings import Settings
from tests.phase15.test_portal import _key, _login

JPEG = "ffd8ffe000104a4649460000010101000100010000ffd9"
PNG = "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c63000100000500010d0a2db40000000049454e44ae426082"


def _actor(headers) -> str:
    payload = headers["Authorization"].split(" ", 1)[1].split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))["sub"]


def _client():
    from perchpoint.routes import create_app

    return TestClient(create_app())


def _journals_for(reference: str) -> int:
    with application_admin_connection(Settings.load()) as connection:
        return int(connection.execute(
            text("SELECT count(*) FROM journal_transactions WHERE public_reference = :reference"),
            {"reference": reference},
        ).scalar_one())


def _report(client, headers, **extra):
    payload = {
        "description": "The kitchen faucet drips.",
        "place_label": "Maple Court 101",
        "place_kind": "unit",
        "source": "resident",
        "urgency": {"immediate_danger": False},
        "idempotency_key": _key("report"),
    }
    payload.update(extra)
    created = client.post("/api/v2/maintenance/intake", headers=headers, json=payload)
    assert created.status_code == 200, created.text
    return created.json()


def test_j01_resident_report_is_idempotent_and_reaches_the_queue():
    client = _client()
    resident = _login(client, "resident.synthetic@example.com")
    ann = _login(client, "ann.synthetic@example.com")
    key = _key("report")
    created = _report(client, resident, idempotency_key=key)
    assert created["replayed"] is False
    assert created["summary"] == "received"
    replay = client.post(
        "/api/v2/maintenance/intake",
        headers=resident,
        json={
            "description": "The kitchen faucet drips.",
            "place_label": "Maple Court 101",
            "place_kind": "unit",
            "source": "resident",
            "urgency": {"immediate_danger": False},
            "idempotency_key": key,
        },
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["replayed"] is True
    assert replay.json()["reference"] == created["reference"]
    mine = client.get("/api/v2/maintenance/mine", headers=resident)
    assert mine.status_code == 200
    assert any(item["public_reference"] == created["reference"] for item in mine.json()["items"])
    queued = client.get("/api/v2/maintenance/desk/queue", headers=ann)
    assert queued.status_code == 200
    assert any(item["public_reference"] == created["reference"] for item in queued.json()["items"])
    assert created["money_moved"] is False
    assert _journals_for(created["reference"]) == 0


def test_a_resident_cannot_attach_a_report_to_someone_else():
    client = _client()
    resident = _login(client, "resident.synthetic@example.com")
    rejected = client.post(
        "/api/v2/maintenance/intake",
        headers=resident,
        json={
            "description": "This should not appear for another household.",
            "place_label": "Other household",
            "place_kind": "unit",
            "source": "phone",
            "resident_actor": str(uuid4()),
            "urgency": {"immediate_danger": False},
            "idempotency_key": _key("inject"),
        },
    )
    assert rejected.status_code == 403


def test_a_resident_cannot_file_an_internal_note():
    client = _client()
    resident = _login(client, "resident.synthetic@example.com")
    created = _report(client, resident, idempotency_key=_key("note"))
    noted = client.post(
        "/api/v2/maintenance/mine/notes",
        headers=resident,
        json={"reference": created["reference"], "body": "The drip is worse.", "visibility": "internal"},
    )
    assert noted.status_code == 200, noted.text
    ann = _login(client, "ann.synthetic@example.com")
    viewed = client.get(f"/api/v2/maintenance/desk/{created['reference']}", headers=ann)
    assert viewed.status_code == 200, viewed.text
    assert any(note["visibility"] == "resident" and "worse" in note["body"] for note in viewed.json()["notes"])


def test_j02_emergency_returns_safety_without_a_photo_or_balance_check():
    client = _client()
    resident = _login(client, "resident.synthetic@example.com")
    created = _report(
        client,
        resident,
        description="I smell gas near the stove.",
        urgency={"immediate_danger": True, "human_emergency": True},
        idempotency_key=_key("gas"),
    )
    assert created["severity"] == "emergency"
    assert "911" in created["safety_message"]
    assert created["money_moved"] is False


def test_j03_failed_delivery_escalates_without_calling_it_acceptance(monkeypatch):
    client = _client()
    resident = _login(client, "resident.synthetic@example.com")
    created = _report(
        client,
        resident,
        description="Water is pouring through the ceiling.",
        urgency={"immediate_danger": True},
        synthetic_fail_first_delivery=True,
        reported_at="2026-10-11T03:00:00+00:00",
        idempotency_key=_key("after"),
    )
    monkeypatch.setenv("PHASE20_FAULT", "before_commit")
    from perchpoint.phase20_maintenance import process_escalations
    from perchpoint.settings import Settings as Loaded

    try:
        process_escalations(Loaded.load())
        raise AssertionError("the fault should abort the claim")
    except RuntimeError:
        pass
    finally:
        monkeypatch.delenv("PHASE20_FAULT", raising=False)
    env = os.environ.copy()
    env["PHASE20_WORKER_ONCE"] = "1"
    env["PYTHONPATH"] = str(__import__("pathlib").Path(__file__).resolve().parents[2])
    first = subprocess.run([sys.executable, "-m", "perchpoint.phase20_worker"], cwd=env["PYTHONPATH"], env=env, text=True, capture_output=True, check=False)
    second = subprocess.run([sys.executable, "-m", "perchpoint.phase20_worker"], cwd=env["PYTHONPATH"], env=env, text=True, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    ann = _login(client, "ann.synthetic@example.com")
    viewed = client.get(f"/api/v2/maintenance/desk/{created['reference']}", headers=ann)
    assert viewed.status_code == 200
    assert viewed.json()["money_moved"] is False


def test_materials_time_evidence_and_authority_stay_distinct():
    client = _client()
    resident = _login(client, "resident.synthetic@example.com")
    ann = _login(client, "ann.synthetic@example.com")
    technician = _login(client, "technician.synthetic@example.com")
    faruk = _login(client, "faruk.synthetic@example.com")
    created = _report(client, resident, idempotency_key=_key("job"))
    reference = created["reference"]
    assigned = client.post(
        "/api/v2/maintenance/desk/assignments",
        headers=ann,
        json={"reference": reference, "assignee_actor": _actor(technician)},
    )
    assert assigned.status_code == 200, assigned.text
    accepted = client.post("/api/v2/maintenance/jobs/assignments", headers=technician, json={"reference": reference, "state": "accepted"})
    assert accepted.status_code == 200, accepted.text
    need = client.post(
        "/api/v2/maintenance/jobs/needs",
        headers=technician,
        json={"reference": reference, "specification": "Moen 7594 1/2 inch cartridge", "quantity": 1, "unit_name": "each", "dimensions": "1/2 inch", "model_number": "7594"},
    )
    assert need.status_code == 200, need.text
    decided = client.post(
        "/api/v2/maintenance/desk/decisions",
        headers=ann,
        json={"reference": reference, "needs_revision": need.json()["revision"], "selected_specification": "Generic cartridge", "reason": "The specified cartridge is unavailable.", "amount_minor": 4000, "authority": "routine"},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["original_specification"].startswith("Moen")
    stale = client.post(
        "/api/v2/maintenance/jobs/compatibility",
        headers=technician,
        json={"reference": reference, "needs_revision": need.json()["revision"] - 1, "result": "accepted"},
    )
    assert stale.status_code == 409
    arrived = client.post(
        "/api/v2/maintenance/desk/fulfillment",
        headers=ann,
        json={"reference": reference, "quantity_received": 1, "quantity_remaining": 0, "condition": "different cartridge"},
    )
    assert arrived.status_code == 200
    mismatch = client.post(
        "/api/v2/maintenance/jobs/compatibility",
        headers=technician,
        json={"reference": reference, "needs_revision": need.json()["revision"], "result": "rejected", "mismatch": "The delivered cartridge is the wrong diameter."},
    )
    assert mismatch.status_code == 200
    assert mismatch.json()["ready"] is False
    worker_purchase = client.post(
        "/api/v2/maintenance/desk/decisions",
        headers=technician,
        json={"reference": reference, "needs_revision": need.json()["revision"], "selected_specification": "Another", "reason": "I will buy it.", "amount_minor": 100, "authority": "routine"},
    )
    assert worker_purchase.status_code == 403
    over = client.post(
        "/api/v2/maintenance/desk/decisions",
        headers=ann,
        json={"reference": reference, "needs_revision": need.json()["revision"], "selected_specification": "Capital replacement", "reason": "Replace the stack.", "amount_minor": 200000, "authority": "routine"},
    )
    assert over.status_code == 403
    owner = client.post(
        "/api/v2/maintenance/desk/decisions",
        headers=faruk,
        json={"reference": reference, "needs_revision": need.json()["revision"], "selected_specification": "Capital replacement", "reason": "Owner-reserved replacement.", "amount_minor": 200000, "authority": "owner"},
    )
    assert owner.status_code == 200, owner.text
    started = client.post("/api/v2/maintenance/jobs/time/start", headers=technician, json={"reference": reference, "category": "waiting", "idempotency_key": _key("start")})
    assert started.status_code == 200, started.text
    again = client.post("/api/v2/maintenance/jobs/time/start", headers=technician, json={"reference": reference, "category": "on_site", "idempotency_key": _key("start-2")})
    assert again.status_code == 409
    stopped = client.post("/api/v2/maintenance/jobs/time/stop", headers=technician, json={"reference": reference, "idempotency_key": _key("stop")})
    assert stopped.status_code == 200
    assert stopped.json()["requires_photos"] is False
    denied = client.post("/api/v2/maintenance/jobs/location", headers=technician, json={"reference": reference, "outcome": "denied"})
    assert denied.status_code == 200
    assert denied.json()["proves_presence"] is False
    hidden = client.get(f"/api/v2/maintenance/jobs/location/{reference}", headers=ann)
    assert hidden.status_code == 200
    assert hidden.json()["items"] == []
    missing = client.post("/api/v2/maintenance/jobs/completion", headers=technician, json={"reference": reference})
    assert missing.status_code == 409
    before = client.post("/api/v2/maintenance/jobs/evidence", headers=technician, json={"reference": reference, "stage": "before", "caption": "Dripping faucet", "content_hex": JPEG})
    after = client.post("/api/v2/maintenance/jobs/evidence", headers=technician, json={"reference": reference, "stage": "after", "caption": "Cartridge replaced", "content_hex": PNG})
    assert before.status_code == 200 and before.json()["scan_state"] == "available"
    assert after.status_code == 200, after.text
    reused = client.post("/api/v2/maintenance/jobs/evidence", headers=technician, json={"reference": reference, "stage": "after", "caption": "Same as before", "content_hex": JPEG})
    assert reused.status_code == 409
    submitted = client.post("/api/v2/maintenance/jobs/completion", headers=technician, json={"reference": reference})
    assert submitted.status_code == 200, submitted.text
    own = client.post("/api/v2/maintenance/desk/reviews", headers=technician, json={"reference": reference, "outcome": "verified", "reason": "I checked my own work."})
    assert own.status_code == 403
    reviewed = client.post("/api/v2/maintenance/desk/reviews", headers=ann, json={"reference": reference, "outcome": "verified", "reason": "The after photo shows the new cartridge."})
    assert reviewed.status_code == 200, reviewed.text
    assert cohort_summary()["past_due_minor"] == 427500


def test_inspection_notice_does_not_move_money_and_briefing_matches_the_queue():
    client = _client()
    ann = _login(client, "ann.synthetic@example.com")
    faruk = _login(client, "faruk.synthetic@example.com")
    resident = _login(client, "resident.synthetic@example.com")
    created = _report(client, resident, place_kind="common_area", place_label="Sycamore House hallway", idempotency_key=_key("common"))
    deadline = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    notice = client.post(
        "/api/v2/maintenance/desk/notices",
        headers=ann,
        json={"reference": created["reference"], "program": "HCV", "source_label": "Synthetic notice 2026-10", "deficiency": "Missing handrail", "deadline_at": deadline, "deadline_version": 2},
    )
    assert notice.status_code == 200, notice.text
    assert notice.json()["money_moved"] is False
    assert _journals_for(created["reference"]) == 0
    briefing = client.get("/api/v2/maintenance/briefing", headers=faruk)
    queued = client.get("/api/v2/maintenance/desk/queue", headers=ann)
    assert briefing.status_code == 200
    assert briefing.json()["queue_count"] == queued.json()["count"]
    resident_view = client.get(f"/api/v2/maintenance/mine/{created['reference']}", headers=resident)
    assert resident_view.status_code == 200
    assert resident_view.json()["access_instructions"] is None
