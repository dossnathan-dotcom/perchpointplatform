"""The payment worker is a separate process. The test does not call the worker function."""
import os
import subprocess
import sys
import time
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from perchpoint.db import application_admin_connection
from perchpoint.settings import Settings
from tests.phase17.test_callbacks import _count, _deliver, _event_state, _organization
from tests.phase17.test_payments import _account, _key, _pay, _publish, create_app


def _spawn(clock: str, scenario: str = "", fault: str = ""):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PHASE17_CLOCK"] = clock
    if scenario:
        env["PHASE17_AUTOPAY_SCENARIO"] = scenario
    else:
        env.pop("PHASE17_AUTOPAY_SCENARIO", None)
    if fault:
        env["PHASE17_FAULT"] = fault
    else:
        env.pop("PHASE17_FAULT", None)
    return subprocess.Popen(
        [sys.executable, "-m", "perchpoint.phase17_worker"],
        cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _stop(process):
    if process.poll() is None:
        process.kill()
        process.wait(timeout=10)


def _wait_until(client, headers, tenancy, predicate, timeout=20):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        summary = client.get("/api/v2/payments/summary", headers=headers, params={"tenancy_code": tenancy})
        assert summary.status_code == 200, summary.text
        last = summary.json()
        if predicate(last):
            return last
        time.sleep(0.25)
    raise AssertionError(f"worker did not reach the expected state: {last}")


def _orders(tenancy: str, key: str) -> int:
    with application_admin_connection(Settings.load()) as connection:
        return int(
            connection.execute(
                text("SELECT count(*) FROM payment_orders WHERE tenancy_code = :tenancy AND idempotency_key = :key"),
                {"tenancy": tenancy, "key": key},
            ).scalar_one()
        )


def _occurrence(tenancy: str):
    with application_admin_connection(Settings.load()) as connection:
        return connection.execute(
            text(
                "SELECT o.state, o.reason, o.amount_minor FROM autopay_occurrences o "
                "JOIN autopay_enrollments e ON e.id = o.enrollment_id WHERE e.tenancy_code = :tenancy"
            ),
            {"tenancy": tenancy},
        ).mappings().first()


def test_worker_process_collects_one_due_autopay_occurrence():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    assert _pay(client, headers, obligation, 40000).json()["due_minor"] == 60000
    enrolled = client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": tenancy, "cap_minor": 100000, "day_of_month": 11},
    )
    assert enrolled.status_code == 200, enrolled.text
    scheduled = client.get("/api/v2/payments/summary", headers=headers, params={"tenancy_code": tenancy})
    assert scheduled.status_code == 200, scheduled.text
    assert scheduled.json()["autopay"]["cap_minor"] == 100000
    assert scheduled.json()["autopay"]["included_categories"] == ["rent"]
    assert scheduled.json()["autopay"]["next_on"]
    assert scheduled.json()["autopay"]["latest"] is None
    process = _spawn("2026-10-11T16:00:00-04:00")
    try:
        collected = _wait_until(
            client,
            headers,
            tenancy,
            lambda body: body["ledger"]["due_minor"] == 0 and body["ledger"]["settlement_count"] == 2,
        )
        assert collected["obligations"][0]["remaining_minor"] == 0
        assert collected["autopay"]["latest"]["state"] == "collected"
        assert collected["autopay"]["latest"]["period_code"] == "2026-10"
        assert _orders(tenancy, f"autopay-{tenancy}-2026-10") == 1
    finally:
        _stop(process)


def test_worker_delay_posts_once_after_callback_and_restart():
    client = TestClient(create_app())
    headers, account = _account(client)
    organization = _organization(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    assert _pay(client, headers, obligation, 40000).json()["due_minor"] == 60000
    assert client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": tenancy, "cap_minor": 100000, "day_of_month": 11},
    ).status_code == 200
    first = _spawn("2026-10-11T16:00:00-04:00", "callback")
    try:
        waiting = _wait_until(
            client,
            headers,
            tenancy,
            lambda body: any(row["state"] == "processing" and row["amount_minor"] == 60000 for row in body["payments"]),
        )
        assert waiting["ledger"]["settlement_count"] == 1
        assert waiting["ledger"]["due_minor"] == 60000
    finally:
        _stop(first)
    second = _spawn("2026-10-11T16:00:00-04:00", "callback")
    try:
        time.sleep(1.5)
        still = client.get("/api/v2/payments/summary", headers=headers, params={"tenancy_code": tenancy}).json()
        assert still["ledger"]["settlement_count"] == 1
        assert _orders(tenancy, f"autopay-{tenancy}-2026-10") == 1
        payment = next(row for row in still["payments"] if row["amount_minor"] == 60000)
        payload = {
            "id": f"evt-{payment['public_reference']}",
            "organization_id": organization,
            "type": "payment.succeeded",
            "effect_key": payment["public_reference"],
            "amount_minor": 60000,
            "environment": "local_fake",
        }
        assert _deliver(client, payload).status_code == 200
        posted = _wait_until(
            client,
            headers,
            tenancy,
            lambda body: body["ledger"]["settlement_count"] == 2 and body["ledger"]["due_minor"] == 0,
        )
        assert posted["ledger"]["settlement_count"] == 2
        assert posted["autopay"]["latest"]["state"] == "collected"
        assert posted["autopay"]["latest"]["reason"] == "provider_confirmed"
        assert _deliver(client, payload).json()["duplicate"] is True
        time.sleep(1)
        assert _count(tenancy, "settlement") == 2
    finally:
        _stop(second)


def test_two_workers_collect_one_occurrence():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    assert _pay(client, headers, obligation, 40000).json()["due_minor"] == 60000
    assert client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": tenancy, "cap_minor": 100000, "day_of_month": 11},
    ).status_code == 200
    workers = [_spawn("2026-10-11T16:00:00-04:00"), _spawn("2026-10-11T16:00:00-04:00")]
    try:
        posted = _wait_until(
            client,
            headers,
            tenancy,
            lambda body: body["ledger"]["due_minor"] == 0 and body["ledger"]["settlement_count"] == 2,
        )
        assert _orders(tenancy, f"autopay-{tenancy}-2026-10") == 1
    finally:
        for process in workers:
            _stop(process)


def test_pause_and_blocked_instrument_do_not_debit():
    client = TestClient(create_app())
    headers, account = _account(client)
    paused = f"tenancy-{uuid4().hex[:8]}"
    blocked = f"tenancy-{uuid4().hex[:8]}"
    for tenancy in (paused, blocked):
        obligation = _publish(client, headers, account, tenancy, 100000, 100000)
        paid = _pay(client, headers, obligation, 40000)
        assert paid.status_code == 200 and paid.json()["state"] == "succeeded"
        assert client.post(
            "/api/v2/payments/autopay",
            headers=headers,
            json={"tenancy_code": tenancy, "cap_minor": 100000, "day_of_month": 11},
        ).status_code == 200
    assert client.post(
        "/api/v2/payments/autopay/state",
        headers=headers,
        json={"tenancy_code": paused, "state": "paused"},
    ).status_code == 200
    with application_admin_connection(Settings.load()) as connection:
        connection.execute(
            text(
                "UPDATE payment_instruments SET state = 'revoked' WHERE id = ("
                "SELECT instrument_id FROM autopay_enrollments WHERE tenancy_code = :tenancy)"
            ),
            {"tenancy": blocked},
        )
    process = _spawn("2026-10-11T16:00:00-04:00")
    try:
        deadline = time.time() + 45
        occurrence = None
        while time.time() < deadline:
            occurrence = _occurrence(blocked)
            if occurrence is not None:
                break
            time.sleep(0.25)
        assert _orders(paused, f"autopay-{paused}-2026-10") == 0
        assert _orders(blocked, f"autopay-{blocked}-2026-10") == 0
        assert _count(paused, "settlement") == 1
        assert occurrence is not None, "worker did not record the blocked instrument"
        assert occurrence["state"] == "action_required" and occurrence["reason"] == "blocked_instrument"
    finally:
        _stop(process)


def test_missed_day_is_not_collected_as_a_historical_batch():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    assert _pay(client, headers, obligation, 40000).json()["due_minor"] == 60000
    assert client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": tenancy, "cap_minor": 100000, "day_of_month": 1},
    ).status_code == 200
    process = _spawn("2026-10-11T16:00:00-04:00")
    try:
        time.sleep(2)
        assert _orders(tenancy, f"autopay-{tenancy}-2026-10") == 0
        assert _count(tenancy, "settlement") == 1
        assert _occurrence(tenancy) is None
    finally:
        _stop(process)


def test_pause_after_submission_still_posts_the_one_accepted_payment():
    client = TestClient(create_app())
    headers, account = _account(client)
    organization = _organization(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    assert _pay(client, headers, obligation, 40000).json()["state"] == "succeeded"
    assert client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": tenancy, "cap_minor": 100000, "day_of_month": 11},
    ).status_code == 200
    worker = _spawn("2026-10-11T16:00:00-04:00", "callback")
    try:
        waiting = _wait_until(
            client,
            headers,
            tenancy,
            lambda body: any(row["state"] == "processing" and row["amount_minor"] == 60000 for row in body["payments"]),
        )
        assert waiting["ledger"]["settlement_count"] == 1
        paused = client.post(
            "/api/v2/payments/autopay/state",
            headers=headers,
            json={"tenancy_code": tenancy, "state": "paused"},
        )
        assert paused.status_code == 200, paused.text
        payment = next(row for row in waiting["payments"] if row["amount_minor"] == 60000)
        payload = {
            "id": f"evt-pause-{payment['public_reference']}",
            "organization_id": organization,
            "type": "payment.succeeded",
            "effect_key": payment["public_reference"],
            "amount_minor": 60000,
            "environment": "local_fake",
        }
        assert _deliver(client, payload).status_code == 200
        posted = _wait_until(
            client,
            headers,
            tenancy,
            lambda body: body["ledger"]["settlement_count"] == 2 and body["ledger"]["due_minor"] == 0,
        )
        assert _orders(tenancy, f"autopay-{tenancy}-2026-10") == 1
        assert posted["ledger"]["charge_count"] == 1
        occurrence = _occurrence(tenancy)
        assert occurrence["state"] == "collected" and occurrence["reason"] == "provider_confirmed"
    finally:
        _stop(worker)


def test_worker_skips_over_cap_paid_fee_reserved_and_revoked_grant():
    client = TestClient(create_app())
    headers, account = _account(client)
    over = f"tenancy-{uuid4().hex[:8]}"
    paid = f"tenancy-{uuid4().hex[:8]}"
    fee = f"tenancy-{uuid4().hex[:8]}"
    reserved = f"tenancy-{uuid4().hex[:8]}"
    revoked = f"tenancy-{uuid4().hex[:8]}"
    _publish(client, headers, account, over, 100000, 100000)
    paid_obligation = _publish(client, headers, account, paid, 100000, 100000)
    assert _pay(client, headers, paid_obligation, 100000).json()["state"] == "succeeded"
    fee_charge = client.post(
        "/api/v2/payments/charges",
        headers=headers,
        json={
            "tenancy_code": fee,
            "amount_minor": 25000,
            "category": "fee",
            "description": "A fee that autopay must not collect",
            "account_reference": account,
            "rent_basis_minor": 0,
            "idempotency_key": _key("fee"),
        },
    )
    assert fee_charge.status_code == 200, fee_charge.text
    reserved_obligation = _publish(client, headers, account, reserved, 100000, 100000)
    assert _pay(client, headers, reserved_obligation, 40000).json()["state"] == "succeeded"
    holding = _pay(client, headers, reserved_obligation, 60000, scenario="callback")
    assert holding.json()["state"] == "processing"
    revoked_obligation = _publish(client, headers, account, revoked, 100000, 100000)
    assert _pay(client, headers, revoked_obligation, 40000).json()["state"] == "succeeded"
    for tenancy, cap in ((over, 50000), (paid, 100000), (fee, 100000), (reserved, 100000), (revoked, 100000)):
        assert client.post(
            "/api/v2/payments/autopay",
            headers=headers,
            json={"tenancy_code": tenancy, "cap_minor": cap, "day_of_month": 11},
        ).status_code == 200
    with application_admin_connection(Settings.load()) as connection:
        payer = connection.execute(
            text("SELECT organization_id, payer_account_id FROM autopay_enrollments WHERE tenancy_code = :tenancy"),
            {"tenancy": revoked},
        ).one()
        connection.execute(
            text(
                "INSERT INTO payer_grants "
                "(organization_id, id, tenancy_code, payer_account_id, grantor_account_id, email, state) "
                "VALUES (:org, gen_random_uuid(), :tenancy, :payer, :payer, 'revoked-payer@example.com', 'revoked')"
            ),
            {"org": payer.organization_id, "tenancy": revoked, "payer": payer.payer_account_id},
        )
    worker = _spawn("2026-10-11T16:00:00-04:00")
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            if _occurrence(over) is not None and _occurrence(revoked) is not None and _occurrence(paid) is not None:
                break
            time.sleep(0.25)
        assert _orders(over, f"autopay-{over}-2026-10") == 0
        assert _occurrence(over)["state"] == "action_required" and _occurrence(over)["reason"] == "over_cap"
        assert _count(over, "settlement") == 0
        assert _orders(paid, f"autopay-{paid}-2026-10") == 0
        assert _occurrence(paid)["state"] == "skipped" and _occurrence(paid)["reason"] == "nothing_due"
        assert _orders(fee, f"autopay-{fee}-2026-10") == 0
        assert _occurrence(fee)["reason"] == "nothing_due"
        assert _orders(reserved, f"autopay-{reserved}-2026-10") == 0
        assert _occurrence(reserved)["reason"] == "nothing_due"
        assert _count(reserved, "settlement") == 1
        assert _orders(revoked, f"autopay-{revoked}-2026-10") == 0
        assert _occurrence(revoked)["state"] == "action_required" and _occurrence(revoked)["reason"] == "revoked_grant"
        assert _count(revoked, "settlement") == 1
    finally:
        _stop(worker)


def test_month_change_collects_the_new_period_without_a_historical_batch():
    client = TestClient(create_app())
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    assert _pay(client, headers, obligation, 40000).json()["state"] == "succeeded"
    assert client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": tenancy, "cap_minor": 100000, "day_of_month": 1},
    ).status_code == 200
    october = _spawn("2026-10-31T23:30:00-04:00")
    try:
        time.sleep(2)
        assert _orders(tenancy, f"autopay-{tenancy}-2026-10") == 0
        assert _count(tenancy, "settlement") == 1
    finally:
        _stop(october)
    november = _spawn("2026-11-01T01:30:00-05:00")
    try:
        posted = _wait_until(
            client,
            headers,
            tenancy,
            lambda body: body["ledger"]["due_minor"] == 0 and body["ledger"]["settlement_count"] == 2,
        )
        assert _orders(tenancy, f"autopay-{tenancy}-2026-10") == 0
        assert _orders(tenancy, f"autopay-{tenancy}-2026-11") == 1
        assert posted["ledger"]["charge_count"] == 1
    finally:
        _stop(november)


def test_worker_crash_before_posting_retries_the_same_callback_once():
    client = TestClient(create_app())
    headers, account = _account(client)
    organization = _organization(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    assert _pay(client, headers, obligation, 40000).json()["state"] == "succeeded"
    assert client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": tenancy, "cap_minor": 100000, "day_of_month": 11},
    ).status_code == 200
    started = _spawn("2026-10-11T16:00:00-04:00", "callback")
    try:
        waiting = _wait_until(
            client,
            headers,
            tenancy,
            lambda body: any(row["state"] == "processing" and row["amount_minor"] == 60000 for row in body["payments"]),
        )
    finally:
        _stop(started)
    assert client.post(
        "/api/v2/payments/autopay/state",
        headers=headers,
        json={"tenancy_code": tenancy, "state": "paused"},
    ).status_code == 200
    payment = next(row for row in waiting["payments"] if row["amount_minor"] == 60000)
    event_id = f"evt-crash-{payment['public_reference']}"
    payload = {
        "id": event_id,
        "organization_id": organization,
        "type": "payment.succeeded",
        "effect_key": payment["public_reference"],
        "amount_minor": 60000,
        "environment": "local_fake",
    }
    assert _deliver(client, payload).status_code == 200
    crashed = _spawn("2026-10-11T16:00:00-04:00", fault="before_provider_commit")
    try:
        crashed.wait(timeout=15)
    finally:
        _stop(crashed)
    assert _count(tenancy, "settlement") == 1
    assert _event_state(event_id) == "received"
    recovered = _spawn("2026-10-11T16:00:00-04:00")
    try:
        posted = _wait_until(
            client,
            headers,
            tenancy,
            lambda body: body["ledger"]["settlement_count"] == 2 and body["ledger"]["due_minor"] == 0,
        )
        assert _orders(tenancy, f"autopay-{tenancy}-2026-10") == 1
        assert posted["ledger"]["settlement_count"] == 2
        assert _event_state(event_id) == "applied"
    finally:
        _stop(recovered)


def test_worker_process_lost_ack_does_not_post_again():
    client = TestClient(create_app())
    headers, account = _account(client)
    organization = _organization(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    assert _pay(client, headers, obligation, 40000).json()["state"] == "succeeded"
    assert client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": tenancy, "cap_minor": 100000, "day_of_month": 11},
    ).status_code == 200
    started = _spawn("2026-10-11T16:00:00-04:00", "callback")
    try:
        waiting = _wait_until(
            client,
            headers,
            tenancy,
            lambda body: any(row["state"] == "processing" and row["amount_minor"] == 60000 for row in body["payments"]),
        )
    finally:
        _stop(started)
    payment = next(row for row in waiting["payments"] if row["amount_minor"] == 60000)
    event_id = f"evt-ack-{payment['public_reference']}"
    assert _deliver(
        client,
        {
            "id": event_id,
            "organization_id": organization,
            "type": "payment.succeeded",
            "effect_key": payment["public_reference"],
            "amount_minor": 60000,
            "environment": "local_fake",
        },
    ).status_code == 200
    crashed = _spawn("2026-10-11T16:00:00-04:00", fault="before_ack")
    try:
        crashed.wait(timeout=15)
    finally:
        _stop(crashed)
    assert _count(tenancy, "settlement") == 2
    assert _event_state(event_id) == "received"
    recovered = _spawn("2026-10-11T16:00:00-04:00")
    try:
        posted = _wait_until(client, headers, tenancy, lambda body: body["ledger"]["due_minor"] == 0)
        assert posted["ledger"]["settlement_count"] == 2
        assert _orders(tenancy, f"autopay-{tenancy}-2026-10") == 1
        assert _event_state(event_id) == "applied"
    finally:
        _stop(recovered)
