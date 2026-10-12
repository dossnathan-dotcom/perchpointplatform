"""Two database sessions compete for one refund allowance. The barrier is before the request."""
import os
import threading
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from perchpoint.db import application_admin_connection
from perchpoint.settings import Settings
from tests.phase15.test_portal import _login
from tests.phase17.test_payments import _account, _key, _pay, _publish, create_app


def test_two_simultaneous_refunds_stay_inside_the_remaining_allowance():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 200000, 100000)
    paid = _pay(client, headers, obligation, 200000)
    assert paid.json()["state"] == "succeeded"
    first = client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 70000,
            "description": "Ordinary refund that leaves three hundred dollars.",
            "resident_explanation": "Seven hundred dollars is inside the monthly rent.",
            "idempotency_key": _key("refund-700"),
        },
    )
    assert first.status_code == 200 and first.json()["state"] == "succeeded", first.text
    barrier = threading.Barrier(2)
    results = []

    def request(key):
        local = TestClient(create_app())
        barrier.wait(timeout=15)
        response = local.post(
            "/api/v2/payments/refunds",
            headers=headers,
            json={
                "payment_reference": paid.json()["reference"],
                "amount_minor": 20000,
                "description": "Simultaneous refund against the remaining allowance.",
                "resident_explanation": "This request competes with the other approval.",
                "idempotency_key": key,
            },
        )
        results.append((response.status_code, response.json().get("state") if response.status_code == 200 else response.text))

    threads = [threading.Thread(target=request, args=(_key("race"),)) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert sorted(state for _status, state in results) == ["owner_decision_required", "succeeded"], results


def test_two_staff_identities_share_one_refund_allowance():
    client = TestClient(create_app())
    ann = _login(client, "ann.synthetic@example.com")
    faruk = _login(client, "faruk.synthetic@example.com")
    _headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, ann, account, tenancy, 200000, 100000)
    paid = _pay(client, ann, obligation, 200000)
    assert paid.json()["state"] == "succeeded"
    first = client.post(
        "/api/v2/payments/refunds",
        headers=ann,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 70000,
            "description": "Ordinary refund that leaves three hundred dollars.",
            "resident_explanation": "Seven hundred dollars is inside the monthly rent.",
            "idempotency_key": _key("refund-700"),
        },
    )
    assert first.status_code == 200 and first.json()["state"] == "succeeded", first.text
    barrier = threading.Barrier(2)
    results = []

    def request(headers, key):
        local = TestClient(create_app())
        barrier.wait(timeout=15)
        response = local.post(
            "/api/v2/payments/refunds",
            headers=headers,
            json={
                "payment_reference": paid.json()["reference"],
                "amount_minor": 20000,
                "description": "Simultaneous refund from a different staff identity.",
                "resident_explanation": "This request uses the same tenancy allowance.",
                "idempotency_key": key,
            },
        )
        results.append((response.status_code, response.json().get("state") if response.status_code == 200 else response.text))

    threads = [
        threading.Thread(target=request, args=(ann, _key("ann-race"))),
        threading.Thread(target=request, args=(faruk, _key("faruk-race"))),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert sorted(state for _status, state in results) == ["owner_decision_required", "succeeded"], results


def test_first_budget_row_is_created_once():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    barrier = threading.Barrier(2)
    results = []

    def publish(key):
        local = TestClient(create_app())
        barrier.wait(timeout=15)
        response = local.post(
            "/api/v2/payments/charges",
            headers=headers,
            json={
                "tenancy_code": tenancy,
                "amount_minor": 100000,
                "category": "rent",
                "description": "Synthetic rent obligation for a payment scenario",
                "account_reference": account,
                "rent_basis_minor": 100000,
                "idempotency_key": key,
            },
        )
        results.append(response.status_code)

    threads = [threading.Thread(target=publish, args=(_key("budget"),)) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert results == [200, 200], results
    with application_admin_connection(Settings.load()) as connection:
        count = connection.execute(
            text("SELECT count(*) FROM tenancy_refund_budgets WHERE tenancy_code = :tenancy"),
            {"tenancy": tenancy},
        ).scalar_one()
    assert int(count) == 1


def test_reserved_refund_dispatches_once_and_blocks_a_competing_request():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 200000, 100000)
    paid = _pay(client, headers, obligation, 200000)
    key = _key("refund-800")
    body = {
        "payment_reference": paid.json()["reference"],
        "amount_minor": 80000,
        "description": "Reserved refund that must dispatch only once.",
        "resident_explanation": "Eight hundred dollars stays inside the rent allowance.",
        "idempotency_key": key,
    }
    os.environ["PHASE17_FAULT"] = "before_refund_dispatch"
    try:
        with pytest.raises(RuntimeError, match="injected fault"):
            client.post("/api/v2/payments/refunds", headers=headers, json=body)
    finally:
        os.environ.pop("PHASE17_FAULT", None)
    competing = client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 30000,
            "description": "This competing refund must not use the reserved allowance twice.",
            "resident_explanation": "Three hundred dollars does not fit beside the reservation.",
            "idempotency_key": _key("refund-300"),
        },
    )
    assert competing.status_code == 200 and competing.json()["state"] == "owner_decision_required", competing.text
    dispatched = client.post("/api/v2/payments/refunds", headers=headers, json=body)
    assert dispatched.status_code == 200 and dispatched.json()["state"] == "succeeded", dispatched.text
    replay = client.post("/api/v2/payments/refunds", headers=headers, json=body)
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    from tests.phase17.test_callbacks import _count

    assert _count(tenancy, "refund") == 1
