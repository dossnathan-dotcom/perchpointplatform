"""Signed provider deliveries reach the ledger once through the inbox worker."""
import json
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from perchpoint.db import application_admin_connection
from perchpoint.phase17_payments import process_provider_inbox
from perchpoint.phase17_stripe import sign_payload
from perchpoint.routes import create_app
from perchpoint.settings import Settings
from tests.phase17.test_payments import _account, _pay, _publish


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def _organization(client) -> str:
    signed = client.post(
        "/api/v2/session",
        json={"email": "ann.synthetic@example.com", "password": os.environ["PHASE2_DEV_PASSWORD"]},
    )
    assert signed.status_code == 200, signed.text
    return signed.json()["organization_id"]


def _deliver(client, payload: dict, signature: str | None = None):
    raw = json.dumps(payload).encode()
    return client.post(
        "/api/v2/payments/provider-events",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-perchpoint-provider-signature": signature if signature is not None else sign_payload(raw),
        },
    )


def _count(tenancy: str, kind: str) -> int:
    with application_admin_connection(Settings.load()) as connection:
        return int(
            connection.execute(
                text("SELECT count(*) FROM journal_transactions WHERE tenancy_code = :tenancy AND kind = :kind"),
                {"tenancy": tenancy, "kind": kind},
            ).scalar_one()
        )


def _event_state(event_id: str) -> str | None:
    with application_admin_connection(Settings.load()) as connection:
        return connection.execute(
            text("SELECT state FROM provider_events WHERE provider_event_id = :event"),
            {"event": event_id},
        ).scalar()


def test_signed_callback_posts_once_and_replays_do_not(client):
    headers, account = _account(client)
    organization = _organization(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    pending = _pay(client, headers, obligation, 100000, scenario="pending")
    reference = pending.json()["reference"]
    assert pending.json()["state"] == "processing"
    assert _count(tenancy, "settlement") == 0
    payload = {
        "id": f"evt-{uuid4().hex[:8]}",
        "organization_id": organization,
        "type": "payment.succeeded",
        "effect_key": reference,
        "amount_minor": 100000,
        "environment": "local_fake",
    }
    stored = _deliver(client, payload)
    assert stored.status_code == 200, stored.text
    assert stored.json()["stored"] is True and stored.json()["applied"] is False
    process_provider_inbox(Settings.load())
    assert _event_state(payload["id"]) == "applied"
    assert _count(tenancy, "settlement") == 1
    replay = _deliver(client, payload)
    assert replay.json()["duplicate"] is True
    process_provider_inbox(Settings.load())
    assert _event_state(payload["id"]) == "applied"
    assert _count(tenancy, "settlement") == 1
    sibling = {**payload, "id": f"evt-{uuid4().hex[:8]}"}
    assert _deliver(client, sibling).json()["stored"] is True
    process_provider_inbox(Settings.load())
    assert _count(tenancy, "settlement") == 1
    other = f"tenancy-{uuid4().hex[:8]}"
    other_obligation = _publish(client, headers, account, other, 100000, 100000)
    other_payment = _pay(client, headers, other_obligation, 100000, scenario="pending")
    second = {
        "id": f"evt-{uuid4().hex[:8]}",
        "organization_id": organization,
        "type": "payment.succeeded",
        "effect_key": other_payment.json()["reference"],
        "amount_minor": 100000,
        "environment": "local_fake",
    }
    assert _deliver(client, second).status_code == 200
    process_provider_inbox(Settings.load())
    assert _count(other, "settlement") == 1
    assert _count(tenancy, "settlement") == 1


def test_bad_signature_and_wrong_mapping_do_not_settle(client):
    headers, account = _account(client)
    organization = _organization(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    pending = _pay(client, headers, obligation, 100000, scenario="pending")
    payload = {
        "id": f"evt-{uuid4().hex[:8]}",
        "organization_id": organization,
        "type": "payment.succeeded",
        "effect_key": pending.json()["reference"],
        "amount_minor": 100000,
        "environment": "local_fake",
    }
    raw = json.dumps(payload).encode()
    unsigned = _deliver(client, payload, signature="0" * 64)
    assert unsigned.status_code == 401
    changed = client.post(
        "/api/v2/payments/provider-events",
        content=raw.replace(b"100000", b"100001"),
        headers={"content-type": "application/json", "x-perchpoint-provider-signature": sign_payload(raw)},
    )
    assert changed.status_code == 401
    wrong = {**payload, "id": f"evt-{uuid4().hex[:8]}", "organization_id": str(uuid4()), "environment": "live"}
    assert _deliver(client, wrong).status_code == 200
    process_provider_inbox(Settings.load())
    assert _event_state(wrong["id"]) == "quarantined"
    assert _count(tenancy, "settlement") == 0


def test_worker_crash_and_lost_ack_post_once(client):
    headers, account = _account(client)
    organization = _organization(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    pending = _pay(client, headers, obligation, 100000, scenario="pending")
    event_id = f"evt-{uuid4().hex[:8]}"
    assert _deliver(
        client,
        {
            "id": event_id,
            "organization_id": organization,
            "type": "payment.succeeded",
            "effect_key": pending.json()["reference"],
            "amount_minor": 100000,
            "environment": "local_fake",
        },
    ).status_code == 200
    os.environ["PHASE17_FAULT"] = "before_provider_commit"
    with pytest.raises(RuntimeError):
        process_provider_inbox(Settings.load())
    assert _count(tenancy, "settlement") == 0
    assert _event_state(event_id) == "received"
    process_provider_inbox(Settings.load())
    assert _count(tenancy, "settlement") == 1

    tenancy_ack = f"tenancy-{uuid4().hex[:8]}"
    obligation_ack = _publish(client, headers, account, tenancy_ack, 100000, 100000)
    pending_ack = _pay(client, headers, obligation_ack, 100000, scenario="pending")
    ack_id = f"evt-{uuid4().hex[:8]}"
    assert _deliver(
        client,
        {
            "id": ack_id,
            "organization_id": organization,
            "type": "payment.succeeded",
            "effect_key": pending_ack.json()["reference"],
            "amount_minor": 100000,
            "environment": "local_fake",
        },
    ).status_code == 200
    os.environ["PHASE17_FAULT"] = "before_ack"
    with pytest.raises(RuntimeError):
        process_provider_inbox(Settings.load())
    assert _count(tenancy_ack, "settlement") == 1
    assert _event_state(ack_id) == "received"
    process_provider_inbox(Settings.load())
    assert _count(tenancy_ack, "settlement") == 1
    assert _event_state(ack_id) == "applied"


def test_oversized_return_is_quarantined(client):
    headers, account = _account(client)
    organization = _organization(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    paid = _pay(client, headers, obligation, 100000)
    reference = paid.json()["reference"]
    event_id = f"evt-{uuid4().hex[:8]}"
    assert _deliver(
        client,
        {
            "id": event_id,
            "organization_id": organization,
            "type": "payment.returned",
            "effect_key": f"return-{reference}",
            "payment_reference": reference,
            "amount_minor": 1000000,
            "environment": "local_fake",
        },
    ).status_code == 200
    process_provider_inbox(Settings.load())
    assert _event_state(event_id) == "quarantined"
    assert _count(tenancy, "return") == 0


def test_out_of_order_return_waits_for_success_then_corrects(client):
    headers, account = _account(client)
    organization = _organization(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    pending = _pay(client, headers, obligation, 100000, scenario="pending")
    reference = pending.json()["reference"]
    common = {"organization_id": organization, "environment": "local_fake", "amount_minor": 100000}
    assert _deliver(client, {"id": f"evt-{uuid4().hex[:8]}", "type": "payment.processing", "effect_key": reference, **common}).status_code == 200
    assert _deliver(
        client,
        {
            "id": f"evt-{uuid4().hex[:8]}",
            "type": "payment.returned",
            "effect_key": f"return-{reference}",
            "payment_reference": reference,
            "amount_minor": 40000,
            "organization_id": organization,
            "environment": "local_fake",
        },
    ).status_code == 200
    assert _deliver(client, {"id": f"evt-{uuid4().hex[:8]}", "type": "payment.succeeded", "effect_key": reference, **common}).status_code == 200
    process_provider_inbox(Settings.load())
    assert _count(tenancy, "settlement") == 1
    assert _count(tenancy, "return") == 1
    with application_admin_connection(Settings.load()) as connection:
        due = connection.execute(
            text(
                "SELECT coalesce(sum(CASE WHEN line.category = 'receivable' AND line.side = 'debit' THEN line.amount_minor "
                "WHEN line.category = 'receivable' AND line.side = 'credit' THEN -line.amount_minor ELSE 0 END), 0) "
                "FROM journal_lines line JOIN journal_transactions posted ON posted.id = line.transaction_id "
                "WHERE posted.tenancy_code = :tenancy"
            ),
            {"tenancy": tenancy},
        ).scalar_one()
    assert int(due) == 40000
