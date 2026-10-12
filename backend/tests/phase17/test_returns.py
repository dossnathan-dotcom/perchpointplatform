"""Returns, failed refunds, and closed-period corrections keep one economic effect."""
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from perchpoint.db import application_admin_connection
from perchpoint.routes import create_app
from perchpoint.settings import Settings
from tests.phase17.test_callbacks import _count
from tests.phase17.test_payments import _account, _key, _pay, _publish


def test_failed_refund_releases_once_and_a_replay_does_not_restore_again():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    paid = _pay(client, headers, obligation, 100000)
    body = {
        "payment_reference": paid.json()["reference"],
        "amount_minor": 40000,
        "description": "This refund failed before the payer was credited.",
        "resident_explanation": "The failed refund does not reduce what can still be refunded.",
        "scenario": "fail",
        "idempotency_key": _key("refund-fail"),
    }
    failed = client.post("/api/v2/payments/refunds", headers=headers, json=body)
    assert failed.status_code == 200 and failed.json()["state"] == "failed", failed.text
    replay = client.post("/api/v2/payments/refunds", headers=headers, json=body)
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    assert _count(tenancy, "refund") == 0
    restored = client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 40000,
            "description": "A later refund can use the restored source value.",
            "resident_explanation": "The earlier failure released the reservation once.",
            "idempotency_key": _key("refund-after-fail"),
        },
    )
    assert restored.status_code == 200 and restored.json()["state"] == "succeeded", restored.text
    assert _count(tenancy, "refund") == 1


def test_unknown_refund_reconciles_once_on_retry():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    paid = _pay(client, headers, obligation, 100000)
    body = {
        "payment_reference": paid.json()["reference"],
        "amount_minor": 40000,
        "description": "The provider accepted this refund and the response was lost.",
        "resident_explanation": "Retry the same refund instead of creating another one.",
        "scenario": "timeout_after_accept",
        "idempotency_key": _key("refund-unknown"),
    }
    unknown = client.post("/api/v2/payments/refunds", headers=headers, json=body)
    assert unknown.status_code == 200 and unknown.json()["state"] == "unknown", unknown.text
    assert _count(tenancy, "refund") == 0
    reconciled = client.post("/api/v2/payments/refunds", headers=headers, json=body)
    assert reconciled.status_code == 200 and reconciled.json()["state"] == "succeeded", reconciled.text
    assert _count(tenancy, "refund") == 1
    again = client.post("/api/v2/payments/refunds", headers=headers, json=body)
    assert again.status_code == 200 and again.json()["replayed"] is True
    assert _count(tenancy, "refund") == 1


def test_return_after_period_close_posts_a_correction_without_editing_history():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    paid = _pay(client, headers, obligation, 100000)
    settlement = paid.json()["ledger_reference"]
    before = _line_count(settlement)
    closed = client.post("/api/v2/leasing/ledger/periods/close", headers=headers, json={"reference": account})
    assert closed.status_code == 200 and closed.json()["state"] == "closed", closed.text
    complaint = client.post(
        "/api/v2/leasing/ledger/disputes",
        headers=headers,
        json={"reference": account, "reason_code": "amount_question"},
    )
    assert complaint.status_code == 200 and complaint.json()["journal_lines_unchanged"] is True
    returned = client.post(
        "/api/v2/payments/returns",
        headers=headers,
        json={"payment_reference": paid.json()["reference"], "amount_minor": 40000},
    )
    assert returned.status_code == 200 and returned.json()["due_minor"] == 40000, returned.text
    assert _line_count(settlement) == before
    assert _count(tenancy, "return") == 1
    assert _count(tenancy, "settlement") == 1


def test_ach_return_revokes_the_saved_instrument():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    enrolled = client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": tenancy, "cap_minor": 100000, "day_of_month": 1},
    )
    assert enrolled.status_code == 200, enrolled.text
    paid = _pay(client, headers, obligation, 100000)
    returned = client.post(
        "/api/v2/payments/returns",
        headers=headers,
        json={"payment_reference": paid.json()["reference"], "amount_minor": 100000},
    )
    assert returned.status_code == 200, returned.text
    assert _instrument_state(tenancy) == "revoked"


def _line_count(reference: str) -> int:
    with application_admin_connection(Settings.load()) as connection:
        return int(
            connection.execute(
                text(
                    "SELECT count(*) FROM journal_lines l "
                    "JOIN journal_transactions t ON t.id = l.transaction_id "
                    "WHERE t.public_reference = :reference"
                ),
                {"reference": reference},
            ).scalar_one()
        )


def _instrument_state(tenancy: str) -> str | None:
    with application_admin_connection(Settings.load()) as connection:
        return connection.execute(
            text(
                "SELECT i.state FROM payment_instruments i "
                "JOIN autopay_enrollments e ON e.instrument_id = i.id "
                "WHERE e.tenancy_code = :tenancy"
            ),
            {"tenancy": tenancy},
        ).scalar()
