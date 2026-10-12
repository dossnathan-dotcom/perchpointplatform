"""Default checkout settles a local card payment. Explicit callback waits for a signed fact."""
import os
from uuid import uuid4

from fastapi.testclient import TestClient

from perchpoint.phase17_payments import process_provider_inbox
from perchpoint.routes import create_app
from perchpoint.settings import Settings
from tests.phase17.test_callbacks import _count, _deliver, _organization
from tests.phase17.test_payments import _account, _key, _publish


def test_omitted_card_posts_once_and_a_later_callback_does_not_duplicate():
    client = TestClient(create_app())
    headers, account = _account(client)
    organization = _organization(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    paid = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={"obligation_reference": obligation, "amount_minor": 40000, "method": "card", "idempotency_key": _key("plain")},
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["state"] == "succeeded" and paid.json()["ledger_status"] == "posted"
    assert _count(tenancy, "settlement") == 1
    payload = {
        "id": f"evt-{uuid4().hex[:8]}",
        "organization_id": organization,
        "type": "payment.succeeded",
        "effect_key": paid.json()["reference"],
        "amount_minor": 40000,
        "environment": "local_fake",
    }
    assert _deliver(client, payload).status_code == 200
    process_provider_inbox(Settings.load())
    assert _count(tenancy, "settlement") == 1


def test_explicit_callback_waits_and_replay_cannot_switch_to_success():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    key = _key("callback")
    pending = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={"obligation_reference": obligation, "amount_minor": 40000, "method": "card", "scenario": "callback", "idempotency_key": key},
    )
    assert pending.status_code == 200, pending.text
    assert pending.json()["state"] == "processing" and pending.json()["due_minor"] is None
    assert _count(tenancy, "settlement") == 0
    switched = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={"obligation_reference": obligation, "amount_minor": 40000, "method": "card", "scenario": "succeeded", "idempotency_key": key},
    )
    assert switched.status_code == 200 and switched.json()["replayed"] is True
    assert _count(tenancy, "settlement") == 0
    unknown = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={"obligation_reference": obligation, "amount_minor": 100, "method": "card", "scenario": "force-success", "idempotency_key": _key("unknown")},
    )
    assert unknown.status_code == 400


def test_omitted_bank_debit_does_not_post_and_live_mode_refuses_simulation():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    bank = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={"obligation_reference": obligation, "amount_minor": 40000, "method": "ach", "idempotency_key": _key("ach")},
    )
    assert bank.status_code == 200, bank.text
    assert bank.json()["state"] == "processing"
    assert _count(tenancy, "settlement") == 0
    previous = os.environ.get("PHASE3_ENVIRONMENT")
    os.environ["PHASE3_ENVIRONMENT"] = "production"
    try:
        from perchpoint.commands import CommandError
        from perchpoint.phase17_payments import _resolve_checkout_scenario

        try:
            _resolve_checkout_scenario("card", "succeeded", True)
        except CommandError as exc:
            assert exc.status == 400
        else:
            raise AssertionError("a production scenario was accepted")
        try:
            _resolve_checkout_scenario("card", None, True)
        except CommandError as exc:
            assert exc.status == 409
        else:
            raise AssertionError("omitted production collection was accepted")
    finally:
        if previous is None:
            os.environ.pop("PHASE3_ENVIRONMENT", None)
        else:
            os.environ["PHASE3_ENVIRONMENT"] = previous
    assert _count(tenancy, "settlement") == 0
