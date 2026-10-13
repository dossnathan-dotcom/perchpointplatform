"""Phase 21 call metadata, routing, and the no-recording boundary."""
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import text
from twilio.request_validator import RequestValidator

from perchpoint.commands import CommandError
from perchpoint.db import application_admin_connection
from perchpoint.demo_catalog import cohort_summary
from perchpoint.settings import Settings
from tests.phase15.test_portal import _key, _login

URL = "https://calls.example.test/api/v2/calls/provider-events"
RUN = uuid4().hex[:8]


def _sid(name: str) -> str:
    return f"{name}-{RUN}"


def _client():
    from perchpoint.routes import create_app

    return TestClient(create_app())


def _signed(client, ann, **params):
    payload = {
        "AccountSid": "AC-local-synthetic",
        "CallSid": params.pop("CallSid", "CA-parent"),
        "CallStatus": params.pop("CallStatus", "completed"),
        "SequenceNumber": params.pop("SequenceNumber", "1"),
        "From": params.pop("From", "+15551212000"),
        "To": "ann-handset",
        "Timestamp": params.pop("Timestamp", "2026-10-13T19:00:00+00:00"),
    }
    payload.update(params)
    payload = {key: str(value) for key, value in payload.items()}
    signature = RequestValidator(os.environ.get("PHASE21_PROVIDER_TOKEN", "local-only-not-production-call-token")).compute_signature(URL, payload)
    response = client.post(
        "/api/v2/calls/provider-events",
        data=payload,
        headers={"x-twilio-signature": signature, "x-perchpoint-signature-url": URL},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _bind(client, ann):
    saved = client.post(
        "/api/v2/calls/routing",
        headers=ann,
        json={"account_sid": "AC-local-synthetic", "edges": [["inbound", "ann-handset"], ["emergency", "on-call"], ["on-call", "owner"]]},
    )
    assert saved.status_code == 200, saved.text


def test_ann_first_emergency_and_terminal_outcomes_stay_distinct():
    client = _client()
    ann = _login(client, "ann.synthetic@example.com")
    resident = _login(client, "resident.synthetic@example.com")
    denied = client.get("/api/v2/calls/desk", headers=resident)
    assert denied.status_code == 403
    _bind(client, ann)
    weekday = _signed(client, ann, CallSid=_sid("CA-weekday"), CallStatus="ringing", SequenceNumber="1")
    assert weekday["destination"] == "ann-handset"
    emergency = _signed(client, ann, CallSid=_sid("CA-emergency"), Digits="9", CallStatus="completed", SequenceNumber="2", Timestamp="2026-10-13T19:10:00+00:00")
    assert emergency["destination"] == "on-call"
    assert emergency["human_acknowledged"] is False
    for status, outcome, sid in (
        ("busy", "busy", _sid("CA-busy")),
        ("no-answer", "no-answer", _sid("CA-miss")),
        ("canceled", "cancelled", _sid("CA-cancel")),
        ("failed", "rejected", _sid("CA-reject")),
    ):
        result = _signed(client, ann, CallSid=sid, CallStatus=status, SequenceNumber="1", Timestamp="2026-10-13T20:00:00+00:00")
        assert result["outcome"] == outcome
        assert result["human_acknowledged"] is False
    loop = client.post(
        "/api/v2/calls/routing",
        headers=ann,
        json={"edges": [["ann-handset", "provider"], ["provider", "ann-handset"]]},
    )
    assert loop.status_code == 409
    manual = client.post(
        "/api/v2/calls/manual",
        headers=ann,
        json={"description": "The caller asked for a callback.", "duration_source": "unknown", "idempotency_key": _key("manual")},
    )
    assert manual.status_code == 200, manual.text
    assert manual.json()["connected_proof"] is False
    assert cohort_summary()["past_due_minor"] == 427500


def test_parent_legs_duration_order_and_ambiguity_do_not_double_count():
    client = _client()
    ann = _login(client, "ann.synthetic@example.com")
    _bind(client, ann)
    first = _signed(
        client, ann, CallSid=_sid("CA-root"), CallStatus="completed", SequenceNumber="2",
        DialCallDuration="40", CallDuration="55", Timestamp="2026-10-13T19:20:00+00:00",
    )
    child = _signed(
        client, ann, CallSid=_sid("CA-child"), ParentCallSid=_sid("CA-root"), CallStatus="completed",
        SequenceNumber="3", DialCallDuration="15",
    )
    assert child["reference"] == first["reference"]
    stale = _signed(client, ann, CallSid=_sid("CA-root"), CallStatus="busy", SequenceNumber="1", CallEventId=_sid("CA-root") + ":old")
    assert stale["outcome"] == "busy"
    desk = client.get("/api/v2/calls/desk", headers=ann)
    matches = [item for item in desk.json()["items"] if item["public_reference"] == first["reference"]]
    assert len(matches) == 1
    assert matches[0]["duration_kind"] == "connected"
    assert matches[0]["duration_seconds"] == 15
    replay = _signed(client, ann, CallSid=_sid("CA-root"), CallStatus="completed", SequenceNumber="2", CallEventId=f"{_sid('CA-root')}:2:completed")
    assert replay["replayed"] is True
    reviewed = client.post(
        "/api/v2/calls/caller",
        headers=ann,
        json={"reference": first["reference"], "caller_status": "ambiguous"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["household_disclosed"] is False


def test_callback_note_and_worker_escalation():
    client = _client()
    ann = _login(client, "ann.synthetic@example.com")
    _bind(client, ann)
    created = _signed(client, ann, CallSid=_sid("CA-callback"), CallStatus="no-answer", SequenceNumber="1", Timestamp="2026-10-10T15:00:00+00:00")
    noted = client.post(
        "/api/v2/calls/notes",
        headers=ann,
        json={"reference": created["reference"], "body": "The faucet is dripping."},
    )
    assert noted.status_code == 200, noted.text
    linked = client.post(
        "/api/v2/calls/links",
        headers=ann,
        json={"reference": created["reference"], "case_reference": "PP-M20-01"},
    )
    assert linked.status_code == 200
    due = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    scheduled = client.post(
        "/api/v2/calls/callbacks",
        headers=ann,
        json={"reference": created["reference"], "due_at": due, "reason": "Call back about the drip."},
    )
    assert scheduled.status_code == 200, scheduled.text
    env = os.environ.copy()
    env["PHASE21_WORKER_ONCE"] = "1"
    env["PYTHONPATH"] = str(__import__("pathlib").Path(__file__).resolve().parents[2])
    completed = subprocess.run(
        [sys.executable, "-m", "perchpoint.phase21_worker"],
        cwd=env["PYTHONPATH"],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "phase21-worker-once" in completed.stdout
    desk = client.get("/api/v2/calls/desk", headers=ann)
    assert any(item["state"] == "escalated" for item in desk.json()["callbacks"])


def test_recording_fields_are_dropped_and_voicemail_is_not_acceptance():
    client = _client()
    ann = _login(client, "ann.synthetic@example.com")
    _bind(client, ann)
    posture = client.get("/api/v2/calls/posture", headers=ann)
    assert posture.json()["recording"] is False
    missing = client.post("/api/v2/calls/recordings", headers=ann, json={})
    assert missing.status_code == 404
    payload = {
        "AccountSid": "AC-local-synthetic",
        "CallSid": _sid("CA-record"),
        "CallStatus": "completed",
        "SequenceNumber": "1",
        "From": "anonymous",
        "To": "ann-handset",
        "Timestamp": "2026-10-13T19:30:00+00:00",
        "RecordingUrl": "https://recordings.example.test/secret-audio",
        "TranscriptionText": "do not store",
    }
    signature = RequestValidator("local-only-not-production-call-token").compute_signature(URL, payload)
    stored = client.post(
        "/api/v2/calls/provider-events",
        data=payload,
        headers={"x-twilio-signature": signature, "x-perchpoint-signature-url": URL},
    )
    assert stored.status_code == 200, stored.text
    assert "RecordingUrl" in stored.json()["rejected_fields"]
    with application_admin_connection(Settings.load()) as connection:
        leaked = connection.execute(
            text("SELECT count(*) FROM call_rejections WHERE field_name = 'RecordingUrl'")
        ).scalar_one()
        audio = connection.execute(
            text("SELECT count(*) FROM information_schema.columns WHERE table_name LIKE 'call_%' AND column_name ILIKE '%record%'")
        ).scalar_one()
    assert int(leaked) >= 1
    assert int(audio) == 0
    voice = _signed(client, ann, CallSid=_sid("CA-machine"), CallStatus="completed", AnsweredBy="machine", SequenceNumber="1")
    refused = client.post("/api/v2/calls/acknowledge", headers=ann, json={"reference": voice["reference"]})
    assert refused.status_code == 409
    connected = _signed(client, ann, CallSid=_sid("CA-live"), CallStatus="completed", SequenceNumber="4", DialCallDuration="12")
    accepted = client.post("/api/v2/calls/acknowledge", headers=ann, json={"reference": connected["reference"]})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["case_accepted"] is False
    blocked = {
        "AccountSid": "AC-local-synthetic",
        "CallSid": _sid("CA-flag"),
        "CallStatus": "ringing",
        "SequenceNumber": "1",
        "From": "+15550001",
        "To": "ann",
        "record": "true",
    }
    signature = RequestValidator("local-only-not-production-call-token").compute_signature(URL, blocked)
    rejected = client.post(
        "/api/v2/calls/provider-events",
        data=blocked,
        headers={"x-twilio-signature": signature, "x-perchpoint-signature-url": URL},
    )
    assert rejected.status_code == 409


def test_worker_fault_before_commit_rolls_back():
    client = _client()
    ann = _login(client, "ann.synthetic@example.com")
    _bind(client, ann)
    created = _signed(client, ann, CallSid=_sid("CA-fault"), CallStatus="no-answer", SequenceNumber="1", Timestamp="2026-10-10T15:00:00+00:00")
    due = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    scheduled = client.post(
        "/api/v2/calls/callbacks",
        headers=ann,
        json={"reference": created["reference"], "due_at": due, "reason": "Fault practice callback."},
    )
    assert scheduled.status_code == 200, scheduled.text
    with application_admin_connection(Settings.load()) as connection:
        before = connection.execute(text("SELECT count(*) FROM call_callbacks WHERE state = 'escalated'")).scalar_one()
    env = os.environ.copy()
    env["PHASE21_WORKER_ONCE"] = "1"
    env["PHASE21_FAULT"] = "before_commit"
    env["PYTHONPATH"] = str(__import__("pathlib").Path(__file__).resolve().parents[2])
    completed = subprocess.run(
        [sys.executable, "-m", "perchpoint.phase21_worker"],
        cwd=env["PYTHONPATH"],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    with application_admin_connection(Settings.load()) as connection:
        after = connection.execute(text("SELECT count(*) FROM call_callbacks WHERE state = 'escalated'")).scalar_one()
    assert int(after) == int(before)


def test_another_organization_cannot_bind_a_taken_provider_account():
    client = _client()
    ann = _login(client, "ann.synthetic@example.com")
    _bind(client, ann)
    with application_admin_connection(Settings.load()) as connection:
        connection.execute(text("SET LOCAL ROLE perchpoint_definer"))
        connection.execute(
            text(
                "INSERT INTO role_bundle_capabilities (bundle_id, capability) "
                "SELECT id, 'calls.coordinate' FROM role_bundles WHERE name = 'platform_admin' "
                "ON CONFLICT DO NOTHING"
            )
        )
    try:
        isolation = _login(client, "isolation.synthetic@example.com")
        own = client.post(
            "/api/v2/calls/routing",
            headers=isolation,
            json={"account_sid": _sid("AC-isolation"), "edges": [["inbound", "ann-handset"]]},
        )
        assert own.status_code == 200, own.text
        taken = client.post(
            "/api/v2/calls/routing",
            headers=isolation,
            json={"account_sid": "AC-local-synthetic", "edges": [["inbound", "ann-handset"]]},
        )
        assert taken.status_code == 409
    finally:
        with application_admin_connection(Settings.load()) as connection:
            connection.execute(text("SET LOCAL ROLE perchpoint_definer"))
            connection.execute(
                text(
                    "DELETE FROM role_bundle_capabilities WHERE capability = 'calls.coordinate' "
                    "AND bundle_id IN (SELECT id FROM role_bundles WHERE name = 'platform_admin')"
                )
            )


def test_provider_token_is_required_outside_local(monkeypatch):
    from perchpoint.phase21_calls import provider_token

    monkeypatch.delenv("PHASE21_PROVIDER_TOKEN", raising=False)
    monkeypatch.setenv("PHASE3_ENVIRONMENT", "production")
    try:
        provider_token()
    except CommandError as error:
        assert error.status == 503
        return
    raise AssertionError("the local token was accepted outside local")
