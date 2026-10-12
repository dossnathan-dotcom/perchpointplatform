"""Phase 18 keeps resident rent separate from agency assistance and posts a receipt once."""
import os
import subprocess
import sys
import threading
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.phase15.test_portal import _key, _login
from tests.phase16.test_ledger import _household


@pytest.fixture(scope="module")
def client():
    from perchpoint.routes import create_app

    return TestClient(create_app())


def _books(client, headers):
    _lease, portal_reference, capability = _household(client, headers)
    assert client.post("/api/v2/public/portal/invitations", json={"capability": capability, "idempotency_key": _key("accept")}).status_code == 200
    opened = client.post(
        "/api/v2/leasing/ledger/accounts",
        headers=headers,
        json={"reference": portal_reference, "idempotency_key": _key("account")},
    )
    assert opened.status_code == 200, opened.text
    return opened.json()["reference"]


def _determination(client, headers, account, *, resident, agency, period="2026-11", tenancy=None):
    tenancy = tenancy or f"tenancy-{uuid4().hex[:8]}"
    response = client.post(
        "/api/v2/payments/assistance/determinations",
        headers=headers,
        json={
            "tenancy_code": tenancy,
            "account_reference": account,
            "program_kind": "hcv",
            "agency_name": "Synthetic housing agency",
            "service_period": period,
            "rent_to_owner_minor": resident + agency,
            "resident_minor": resident,
            "agency_minor": agency,
            "idempotency_key": _key("determination"),
        },
    )
    assert response.status_code == 200, response.text
    return tenancy, response.json()


def test_split_charges_the_resident_portion_once(client):
    headers = _login(client, "ann.synthetic@example.com")
    before = client.get("/api/v2/payments/assistance/measures", headers=headers)
    assert before.status_code == 200, before.text
    account = _books(client, headers)
    tenancy, body = _determination(client, headers, account, resident=40000, agency=110000)
    assert body["resident_obligation"]
    view = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy})
    assert view.status_code == 200, view.text
    shown = view.json()
    assert shown["rent_to_owner_minor"] == 150000
    assert shown["resident_responsibility_minor"] == 40000
    assert shown["agency_responsibility_minor"] == 110000
    assert shown["due_minor"] == 40000
    assert shown["subsidy_minor"] == 0
    assert shown["agency_outstanding_minor"] == 110000
    assert shown["payment_default_includes_agency"] is False
    assert shown["money_moved"] is False
    after = client.get("/api/v2/payments/assistance/measures", headers=headers).json()
    assert after["assistance_expected_minor"] - before.json()["assistance_expected_minor"] == 110000
    assert after["confirmed_cash_minor"] == before.json()["confirmed_cash_minor"]
    assert "definitions" in after


def test_a_resident_cannot_open_another_household_by_code(client):
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, _body = _determination(client, headers, account, resident=40000, agency=110000)
    listed = client.get("/api/v2/payments/assistance/households", headers=headers, params={"q": "Synthetic housing"})
    assert listed.status_code == 200, listed.text
    match = [row for row in listed.json()["households"] if row["tenancy_code"] == tenancy]
    assert match and match[0]["resident_minor"] == 40000 and match[0]["agency_minor"] == 110000
    assert "Synthetic housing" in match[0]["label"]
    resident = _login(client, "resident.synthetic@example.com")
    denied = client.get("/api/v2/payments/assistance/household", headers=resident, params={"tenancy_code": tenancy})
    assert denied.status_code == 403
    hidden = client.get("/api/v2/payments/assistance/households", headers=resident, params={"q": "Synthetic housing"})
    assert hidden.status_code == 200
    assert all(row["tenancy_code"] != tenancy for row in hidden.json()["households"])
    measures = client.get("/api/v2/payments/assistance/measures", headers=resident)
    assert measures.status_code == 403
    report = client.post(
        "/api/v2/payments/assistance/reports",
        headers=resident,
        json={
            "tenancy_code": tenancy,
            "amount_minor": 40000,
            "reference_text": "not-my-transfer",
            "explanation": "This household is not mine",
            "idempotency_key": _key("cross-report"),
        },
    )
    assert report.status_code == 403


def test_agency_delay_does_not_increase_resident_due(client):
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, _body = _determination(client, headers, account, resident=40000, agency=110000)
    view = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert view["due_minor"] == 40000
    assert view["agency_outstanding_minor"] == 110000


def test_remittance_without_cash_does_not_settle(client):
    headers = _login(client, "ann.synthetic@example.com")
    created = client.post(
        "/api/v2/payments/assistance/batches",
        headers=headers,
        json={
            "external_id": f"advice-{uuid4().hex[:8]}",
            "gross_minor": 110000,
            "recoupment_minor": 0,
            "net_minor": 110000,
            "rows": [{"tenancy_code": "pending-household", "service_period": "2026-11", "gross_minor": 110000}],
            "idempotency_key": _key("advice"),
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["posted"] is False
    assert created.json()["receipt_reference"] is None


def test_one_receipt_posts_once_and_a_different_payment_remains(client):
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, _body = _determination(client, headers, account, resident=40000, agency=110000)
    external = f"bank-{uuid4().hex[:8]}"
    first = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "business_bank",
            "external_id": external,
            "method": "bank_transfer",
            "amount_minor": 110000,
            "tenancy_code": tenancy,
            "service_period": "2026-11",
            "idempotency_key": _key("receipt"),
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["application_state"] == "queued"
    again = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "business_bank",
            "external_id": external,
            "method": "bank_transfer",
            "amount_minor": 110000,
            "tenancy_code": tenancy,
            "service_period": "2026-11",
            "idempotency_key": _key("receipt-again"),
        },
    )
    assert again.json()["replayed"] is True
    applied = client.post(
        "/api/v2/payments/assistance/receipts/apply",
        headers=headers,
        json={"receipt_reference": first.json()["reference"], "idempotency_key": _key("apply")},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["posted"] is True
    second_apply = client.post(
        "/api/v2/payments/assistance/receipts/apply",
        headers=headers,
        json={"receipt_reference": first.json()["reference"], "idempotency_key": _key("apply-2")},
    )
    assert second_apply.json()["replayed"] is True
    other = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "business_bank",
            "external_id": f"bank-{uuid4().hex[:8]}",
            "method": "bank_transfer",
            "amount_minor": 110000,
            "tenancy_code": tenancy,
            "service_period": "2026-11",
            "idempotency_key": _key("other-payment"),
        },
    )
    assert other.status_code == 200, other.text
    assert other.json()["replayed"] is False
    reviewed = client.post(
        "/api/v2/payments/assistance/receipts/apply",
        headers=headers,
        json={"receipt_reference": other.json()["reference"], "idempotency_key": _key("other-apply")},
    )
    assert reviewed.json()["posted"] is False
    assert reviewed.json()["application_state"] == "review"
    view = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert view["due_minor"] == 40000
    assert view["subsidy_minor"] == 110000
    assert view["agency_outstanding_minor"] == 0


def test_batch_offset_reconciles_without_charging_a_resident(client):
    headers = _login(client, "ann.synthetic@example.com")
    households = []
    for agency in (110000, 90000, 80000):
        account = _books(client, headers)
        tenancy, _body = _determination(client, headers, account, resident=10000, agency=agency)
        households.append((tenancy, account))
    economic = f"hap-{uuid4().hex[:8]}"
    cash = f"cash-{uuid4().hex[:8]}"
    created = client.post(
        "/api/v2/payments/assistance/batches",
        headers=headers,
        json={
            "external_id": economic,
            "gross_minor": 280000,
            "recoupment_minor": 20000,
            "adjustment_minor": 0,
            "net_minor": 260000,
            "cash_external_id": cash,
            "rows": [
                {"tenancy_code": households[0][0], "service_period": "2026-11", "gross_minor": 110000},
                {"tenancy_code": households[1][0], "service_period": "2026-11", "gross_minor": 90000},
                {"tenancy_code": households[2][0], "service_period": "2026-11", "gross_minor": 80000},
            ],
            "idempotency_key": _key("batch"),
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["posted"] is False
    assert created.json()["net_minor"] == 260000
    applied = client.post(
        "/api/v2/payments/assistance/batches/apply",
        headers=headers,
        json={"batch_reference": created.json()["reference"], "idempotency_key": _key("batch-apply")},
    )
    assert applied.status_code == 200, applied.text
    body = applied.json()
    assert body["gross_minor"] - body["recoupment_minor"] == body["net_minor"] == body["confirmed_cash_minor"]
    assert body["unexplained_minor"] == 0
    assert body["open_rows"] == 0
    assert body["money_moved"] is False
    for tenancy, _account in households:
        view = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
        assert view["due_minor"] == 10000
        assert view["agency_outstanding_minor"] == 0
        assert view["agency_received_minor"] == {households[0][0]: 110000, households[1][0]: 90000, households[2][0]: 80000}[tenancy]
    replayed = client.post(
        "/api/v2/payments/assistance/batches",
        headers=headers,
        json={
            "external_id": economic,
            "gross_minor": 280000,
            "recoupment_minor": 20000,
            "adjustment_minor": 0,
            "net_minor": 260000,
            "cash_external_id": cash,
            "rows": [
                {"tenancy_code": households[0][0], "service_period": "2026-11", "gross_minor": 110000},
                {"tenancy_code": households[1][0], "service_period": "2026-11", "gross_minor": 90000},
                {"tenancy_code": households[2][0], "service_period": "2026-11", "gross_minor": 80000},
            ],
            "idempotency_key": _key("batch-replay"),
        },
    )
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["replayed"] is True
    assert replayed.json()["reference"] == created.json()["reference"]
    reapplied = client.post(
        "/api/v2/payments/assistance/batches/apply",
        headers=headers,
        json={"batch_reference": created.json()["reference"], "idempotency_key": _key("batch-apply-again")},
    )
    assert reapplied.status_code == 200, reapplied.text
    assert reapplied.json()["replayed"] is True
    distinct = client.post(
        "/api/v2/payments/assistance/batches",
        headers=headers,
        json={
            "external_id": f"hap-{uuid4().hex[:8]}",
            "gross_minor": 280000,
            "recoupment_minor": 20000,
            "adjustment_minor": 0,
            "net_minor": 260000,
            "cash_external_id": f"cash-{uuid4().hex[:8]}",
            "rows": [
                {"tenancy_code": households[0][0], "service_period": "2026-11", "gross_minor": 110000},
                {"tenancy_code": households[1][0], "service_period": "2026-11", "gross_minor": 90000},
                {"tenancy_code": households[2][0], "service_period": "2026-11", "gross_minor": 80000},
            ],
            "idempotency_key": _key("batch-distinct"),
        },
    )
    assert distinct.status_code == 200, distinct.text
    assert distinct.json()["replayed"] is False
    assert distinct.json()["reference"] != created.json()["reference"]
    blocked = client.post(
        "/api/v2/payments/assistance/batches/apply",
        headers=headers,
        json={"batch_reference": distinct.json()["reference"], "idempotency_key": _key("batch-distinct-apply")},
    )
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["open_rows"] == 3
    assert blocked.json()["unexplained_minor"] == 260000
    for tenancy, _account in households:
        view = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
        assert view["agency_received_minor"] == {households[0][0]: 110000, households[1][0]: 90000, households[2][0]: 80000}[tenancy]
        assert view["due_minor"] == 10000


def test_revision_opens_an_overpayment_without_an_agency_receipt(client):
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, created = _determination(client, headers, account, resident=40000, agency=110000)
    paid = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={
            "obligation_reference": created["resident_obligation"],
            "amount_minor": 40000,
            "method": "card",
            "scenario": "succeeded",
            "idempotency_key": _key("pay"),
        },
    )
    assert paid.status_code == 200, paid.text
    revised = client.post(
        "/api/v2/payments/assistance/determinations",
        headers=headers,
        json={
            "tenancy_code": tenancy,
            "account_reference": account,
            "service_period": "2026-11",
            "rent_to_owner_minor": 150000,
            "resident_minor": 30000,
            "agency_minor": 120000,
            "idempotency_key": _key("revision"),
        },
    )
    assert revised.status_code == 200, revised.text
    assert revised.json()["version"] == 2
    view = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert view["resident_responsibility_minor"] == 30000
    assert view["agency_responsibility_minor"] == 120000
    assert view["agency_received_minor"] == 0
    assert view["exceptions"][0]["kind"] == "resident_overpayment"
    assert view["exceptions"][0]["amount_minor"] == 10000
    assert view["due_minor"] == 0


def test_required_return_stays_unpaid_and_cannot_be_sent_to_the_agency(client):
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, created = _determination(client, headers, account, resident=40000, agency=110000)
    paid = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={
            "obligation_reference": created["resident_obligation"],
            "amount_minor": 40000,
            "method": "card",
            "scenario": "succeeded",
            "idempotency_key": _key("return-pay"),
        },
    )
    assert paid.status_code == 200, paid.text
    revised = client.post(
        "/api/v2/payments/assistance/determinations",
        headers=headers,
        json={
            "tenancy_code": tenancy,
            "account_reference": account,
            "service_period": "2026-11",
            "rent_to_owner_minor": 150000,
            "resident_minor": 30000,
            "agency_minor": 120000,
            "idempotency_key": _key("return-revision"),
        },
    )
    assert revised.status_code == 200, revised.text
    view = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    overpayment = view["exceptions"][0]
    assert overpayment["kind"] == "resident_overpayment" and overpayment["amount_minor"] == 10000
    blocked = client.post(
        "/api/v2/payments/assistance/returns",
        headers=headers,
        json={
            "exception_reference": overpayment["public_reference"],
            "recipient": "resident",
            "paid": True,
            "idempotency_key": _key("return-paid"),
        },
    )
    assert blocked.status_code == 400
    wrong = client.post(
        "/api/v2/payments/assistance/returns",
        headers=headers,
        json={
            "exception_reference": overpayment["public_reference"],
            "recipient": "agency",
            "idempotency_key": _key("return-agency"),
        },
    )
    assert wrong.status_code == 409
    opened = client.post(
        "/api/v2/payments/assistance/returns",
        headers=headers,
        json={
            "exception_reference": overpayment["public_reference"],
            "recipient": "resident",
            "idempotency_key": _key("return-open"),
        },
    )
    assert opened.status_code == 200, opened.text
    assert opened.json()["paid"] is False and opened.json()["state"] == "open"
    assert opened.json()["amount_minor"] == 10000
    after = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert after["due_minor"] == 0 and after["agency_received_minor"] == 0
    opened_return = next(row for row in after["exceptions"] if row["kind"] == "required_return")
    assert opened_return["amount_minor"] == 10000
    evidence = f"bank-return-{uuid4().hex[:12]}"
    noted = client.post(
        "/api/v2/payments/assistance/returns/complete",
        headers=headers,
        json={
            "return_reference": opened.json()["reference"],
            "evidence_key": "please refund this",
            "idempotency_key": _key("return-note"),
        },
    )
    assert noted.status_code == 400
    flagged = client.post(
        "/api/v2/payments/assistance/returns/complete",
        headers=headers,
        json={
            "return_reference": opened.json()["reference"],
            "evidence_key": evidence,
            "mandatory": True,
            "idempotency_key": _key("return-flag"),
        },
    )
    assert flagged.status_code == 400
    completed = client.post(
        "/api/v2/payments/assistance/returns/complete",
        headers=headers,
        json={
            "return_reference": opened.json()["reference"],
            "evidence_key": evidence,
            "idempotency_key": _key("return-complete"),
        },
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["state"] == "resolved" and completed.json()["paid"] is False
    assert completed.json()["amount_minor"] == 10000 and completed.json()["journal_reference"]
    replayed = client.post(
        "/api/v2/payments/assistance/returns/complete",
        headers=headers,
        json={
            "return_reference": opened.json()["reference"],
            "evidence_key": evidence,
            "idempotency_key": _key("return-again"),
        },
    )
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["replayed"] is True
    assert replayed.json()["journal_reference"] == completed.json()["journal_reference"]
    finished = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert finished["due_minor"] == 0
    assert finished["resident_received_minor"] == 40000
    assert finished["resident_returned_minor"] == 10000
    assert finished["resident_net_minor"] == 30000
    assert finished["resident_responsibility_minor"] == 30000
    assert finished["agency_outstanding_minor"] == 120000
    assert all(row["kind"] not in {"required_return", "resident_overpayment"} for row in finished["exceptions"])
    repeated = client.post(
        "/api/v2/payments/assistance/returns",
        headers=headers,
        json={
            "exception_reference": overpayment["public_reference"],
            "recipient": "resident",
            "idempotency_key": _key("return-second"),
        },
    )
    assert repeated.status_code == 404


def test_a_later_overpayment_remains_returnable(client):
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, created = _determination(client, headers, account, resident=40000, agency=110000)
    paid = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={
            "obligation_reference": created["resident_obligation"],
            "amount_minor": 40000,
            "method": "card",
            "scenario": "succeeded",
            "idempotency_key": _key("later-pay"),
        },
    )
    assert paid.status_code == 200, paid.text
    revised = client.post(
        "/api/v2/payments/assistance/determinations",
        headers=headers,
        json={
            "tenancy_code": tenancy,
            "account_reference": account,
            "service_period": "2026-11",
            "rent_to_owner_minor": 150000,
            "resident_minor": 30000,
            "agency_minor": 120000,
            "idempotency_key": _key("later-first"),
        },
    )
    assert revised.status_code == 200, revised.text
    first = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    overpayment = next(row for row in first["exceptions"] if row["kind"] == "resident_overpayment")
    opened = client.post(
        "/api/v2/payments/assistance/returns",
        headers=headers,
        json={"exception_reference": overpayment["public_reference"], "recipient": "resident", "idempotency_key": _key("later-open")},
    )
    assert opened.status_code == 200, opened.text
    evidence = f"bank-return-{uuid4().hex[:12]}"
    completed = client.post(
        "/api/v2/payments/assistance/returns/complete",
        headers=headers,
        json={"return_reference": opened.json()["reference"], "evidence_key": evidence, "idempotency_key": _key("later-complete")},
    )
    assert completed.status_code == 200, completed.text
    again = client.post(
        "/api/v2/payments/assistance/determinations",
        headers=headers,
        json={
            "tenancy_code": tenancy,
            "account_reference": account,
            "service_period": "2026-11",
            "rent_to_owner_minor": 150000,
            "resident_minor": 20000,
            "agency_minor": 130000,
            "idempotency_key": _key("later-second"),
        },
    )
    assert again.status_code == 200, again.text
    fresh = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert fresh["resident_returned_minor"] == 10000
    assert fresh["resident_responsibility_minor"] == 20000
    opened_again = [row for row in fresh["exceptions"] if row["kind"] == "resident_overpayment"]
    assert len(opened_again) == 1
    assert opened_again[0]["amount_minor"] == 10000
    assert opened_again[0]["public_reference"] != overpayment["public_reference"]
    stale = client.post(
        "/api/v2/payments/assistance/returns",
        headers=headers,
        json={"exception_reference": overpayment["public_reference"], "recipient": "resident", "idempotency_key": _key("later-stale")},
    )
    assert stale.status_code == 404
    second = client.post(
        "/api/v2/payments/assistance/returns",
        headers=headers,
        json={"exception_reference": opened_again[0]["public_reference"], "recipient": "resident", "idempotency_key": _key("later-new")},
    )
    assert second.status_code == 200, second.text
    assert second.json()["amount_minor"] == 10000 and second.json()["state"] == "open" and second.json()["paid"] is False


def test_zero_resident_portion_publishes_no_charge(client):
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, body = _determination(client, headers, account, resident=0, agency=150000)
    assert body["resident_obligation"] is None
    view = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert view["resident_responsibility_minor"] == 0
    assert view["due_minor"] == 0
    assert view["agency_outstanding_minor"] == 150000


def test_transfer_report_and_physical_methods_do_not_post(client):
    headers = _login(client, "ann.synthetic@example.com")
    reported = client.post(
        "/api/v2/payments/assistance/reports",
        headers=headers,
        json={
            "tenancy_code": f"tenancy-{uuid4().hex[:8]}",
            "amount_minor": 40000,
            "reference_text": "bank-ref-1844",
            "explanation": "I sent the November transfer yesterday.",
            "idempotency_key": _key("report"),
        },
    )
    assert reported.status_code == 200, reported.text
    assert reported.json()["state"] == "reported"
    assert reported.json()["payment_posted"] is False
    for method in ("cash", "check", "money_order"):
        refused = client.post(
            "/api/v2/payments/assistance/receipts",
            headers=headers,
            json={
                "source": "business_bank",
                "external_id": f"bad-{uuid4().hex[:8]}",
                "method": method,
                "amount_minor": 1000,
                "idempotency_key": _key(method),
            },
        )
        assert refused.status_code == 400, refused.text
    checkout = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={"obligation_reference": "obligation-missing", "amount_minor": 1000, "method": "cash", "idempotency_key": _key("cash")},
    )
    assert checkout.status_code == 400
    historical = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "historical_import",
            "external_id": f"old-{uuid4().hex[:8]}",
            "method": "check",
            "amount_minor": 197500,
            "idempotency_key": _key("historical"),
        },
    )
    assert historical.status_code == 200, historical.text
    assert historical.json()["state"] == "staged"
    applied = client.post(
        "/api/v2/payments/assistance/receipts/apply",
        headers=headers,
        json={"receipt_reference": historical.json()["reference"], "idempotency_key": _key("historical-apply")},
    )
    assert applied.status_code == 409


def test_restricted_and_stripe_observations_do_not_settle_a_resident(client):
    headers = _login(client, "ann.synthetic@example.com")
    utility = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "business_bank",
            "external_id": f"util-{uuid4().hex[:8]}",
            "method": "bank_transfer",
            "amount_minor": 5000,
            "purpose": "utility_reimbursement",
            "tenancy_code": "household-a",
            "service_period": "2026-11",
            "idempotency_key": _key("utility"),
        },
    )
    assert utility.status_code == 200, utility.text
    refused = client.post(
        "/api/v2/payments/assistance/receipts/apply",
        headers=headers,
        json={"receipt_reference": utility.json()["reference"], "idempotency_key": _key("utility-apply")},
    )
    assert refused.status_code == 409
    for kind in ("cash_balance.funded", "payout.paid"):
        observed = client.post(
            "/api/v2/payments/assistance/receipts",
            headers=headers,
            json={
                "source": "stripe",
                "external_id": f"stripe-{kind}-{uuid4().hex[:6]}",
                "method": "bank_transfer",
                "amount_minor": 110000,
                "stripe_kind": kind,
                "idempotency_key": _key(kind),
            },
        )
        assert observed.status_code == 200, observed.text
        assert observed.json()["effect_class"] == "no_resident_settlement"
        assert observed.json()["application_state"] == "excluded"
    config = client.get("/api/v2/payments/assistance/configuration", headers=headers)
    assert config.status_code == 200
    assert config.json()["zelle"]["available"] is False
    assert config.json()["physical_intake"] is False
    assert config.json()["real_values_activated"] is False
    zelle = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={"obligation_reference": "obligation-missing", "amount_minor": 1000, "method": "zelle", "idempotency_key": _key("zelle")},
    )
    assert zelle.status_code == 409


def test_unmatched_legacy_receipt_resolves_once(client):
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, _body = _determination(client, headers, account, resident=0, agency=197500)
    external = f"legacy-{uuid4().hex[:8]}"
    created = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "business_bank",
            "external_id": external,
            "method": "bank_transfer",
            "amount_minor": 197500,
            "idempotency_key": _key("legacy"),
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["application_state"] == "unmatched"
    resolved = client.post(
        "/api/v2/payments/assistance/receipts/resolve",
        headers=headers,
        json={
            "receipt_reference": created.json()["reference"],
            "tenancy_code": tenancy,
            "service_period": "2026-11",
            "idempotency_key": _key("legacy-resolve"),
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["posted"] is False
    assert resolved.json()["application_state"] == "queued"
    applied = client.post(
        "/api/v2/payments/assistance/receipts/apply",
        headers=headers,
        json={"receipt_reference": created.json()["reference"], "idempotency_key": _key("legacy-apply")},
    )
    assert applied.json()["posted"] is True
    repeated = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "business_bank",
            "external_id": external,
            "method": "bank_transfer",
            "amount_minor": 197500,
            "idempotency_key": _key("legacy-repeat"),
        },
    )
    assert repeated.json()["replayed"] is True
    view = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert view["due_minor"] == 0
    assert view["subsidy_minor"] == 197500
    assert view["agency_outstanding_minor"] == 0


def test_revised_basis_tightens_the_ordinary_refund_cap(client):
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, created = _determination(client, headers, account, resident=40000, agency=110000)
    paid = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={
            "obligation_reference": created["resident_obligation"],
            "amount_minor": 40000,
            "method": "cash_app",
            "scenario": "succeeded",
            "idempotency_key": _key("cash-app"),
        },
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["state"] == "succeeded"
    revised = client.post(
        "/api/v2/payments/assistance/determinations",
        headers=headers,
        json={
            "tenancy_code": tenancy,
            "account_reference": account,
            "service_period": "2026-11",
            "rent_to_owner_minor": 150000,
            "resident_minor": 30000,
            "agency_minor": 120000,
            "idempotency_key": _key("basis"),
        },
    )
    assert revised.status_code == 200, revised.text
    refund = client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 35000,
            "description": "Resident requested more than the revised portion.",
            "resident_explanation": "The revised resident portion is the ordinary refund basis.",
            "idempotency_key": _key("refund-basis"),
        },
    )
    assert refund.status_code == 200, refund.text
    assert refund.json()["state"] == "owner_decision_required"
    assert refund.json()["ordinary_max_minor"] == 30000
    assert refund.json()["assistance_basis_minor"] == 30000


def test_resident_transfer_reduces_autopay_and_an_agency_receipt_does_not(client):
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, _created = _determination(client, headers, account, resident=40000, agency=110000)
    assert client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": tenancy, "cap_minor": 40000, "day_of_month": 1},
    ).status_code == 200
    confirmed = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "business_bank",
            "external_id": f"resident-{uuid4().hex[:8]}",
            "method": "bank_transfer",
            "purpose": "resident_rent",
            "amount_minor": 40000,
            "tenancy_code": tenancy,
            "service_period": "2026-11",
            "idempotency_key": _key("resident-receipt"),
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["application_state"] == "queued"
    skipped = client.post(
        "/api/v2/payments/autopay/run",
        headers=headers,
        json={"tenancy_code": tenancy, "period_code": "2026-11"},
    )
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["state"] == "skipped" and skipped.json()["reason"] == "nothing_due"
    assert "payment" not in skipped.json()
    held = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert held["due_minor"] == 40000 and held["agency_outstanding_minor"] == 110000
    applied = client.post(
        "/api/v2/payments/assistance/receipts/apply",
        headers=headers,
        json={"receipt_reference": confirmed.json()["reference"], "idempotency_key": _key("resident-apply")},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["posted"] is True
    settled = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert settled["due_minor"] == 0
    assert settled["subsidy_minor"] == 0
    assert settled["agency_outstanding_minor"] == 110000

    other_account = _books(client, headers)
    other, obligation = _determination(client, headers, other_account, resident=40000, agency=110000)
    assert client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": other, "cap_minor": 40000, "day_of_month": 1},
    ).status_code == 200
    agency = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "business_bank",
            "external_id": f"agency-{uuid4().hex[:8]}",
            "method": "bank_transfer",
            "amount_minor": 110000,
            "tenancy_code": other,
            "service_period": "2026-11",
            "idempotency_key": _key("agency-waiting"),
        },
    )
    assert agency.status_code == 200, agency.text
    collected = client.post(
        "/api/v2/payments/autopay/run",
        headers=headers,
        json={"tenancy_code": other, "period_code": "2026-11"},
    )
    assert collected.status_code == 200, collected.text
    assert collected.json()["state"] == "collected" and collected.json()["amount_minor"] == 40000
    after = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": other}).json()
    assert after["due_minor"] == 0 and after["agency_outstanding_minor"] == 110000
    assert obligation["resident_obligation"]


def test_in_flight_debit_is_not_cancelled_by_a_later_transfer(client):
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, created = _determination(client, headers, account, resident=40000, agency=110000)
    pending = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={
            "obligation_reference": created["resident_obligation"],
            "amount_minor": 40000,
            "method": "ach",
            "scenario": "pending",
            "idempotency_key": _key("inflight"),
        },
    )
    assert pending.status_code == 200, pending.text
    assert pending.json()["state"] == "processing"
    transfer = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "business_bank",
            "external_id": f"late-{uuid4().hex[:8]}",
            "method": "bank_transfer",
            "purpose": "resident_rent",
            "amount_minor": 40000,
            "tenancy_code": tenancy,
            "service_period": "2026-11",
            "idempotency_key": _key("late-transfer"),
        },
    )
    assert transfer.status_code == 200, transfer.text
    reviewed = client.post(
        "/api/v2/payments/assistance/receipts/apply",
        headers=headers,
        json={"receipt_reference": transfer.json()["reference"], "idempotency_key": _key("late-apply")},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["posted"] is False
    assert reviewed.json()["application_state"] == "review"
    view = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert view["due_minor"] == 40000
    assert view["subsidy_minor"] == 0


def test_worker_rolls_back_a_crash_and_two_workers_post_once(client):
    from perchpoint.phase18_assistance import apply_queued_receipts
    from perchpoint.settings import Settings

    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, _created = _determination(client, headers, account, resident=10000, agency=50000)
    created = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "business_bank",
            "external_id": f"crash-{uuid4().hex[:8]}",
            "method": "bank_transfer",
            "amount_minor": 50000,
            "tenancy_code": tenancy,
            "service_period": "2026-11",
            "idempotency_key": _key("crash-receipt"),
        },
    )
    assert created.status_code == 200, created.text
    os.environ["PHASE18_FAULT"] = "before_commit"
    try:
        apply_queued_receipts(Settings.load())
        raise AssertionError("the worker should have stopped before commit")
    except RuntimeError:
        pass
    held = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert held["subsidy_minor"] == 0
    os.environ.pop("PHASE18_FAULT", None)
    recovered = apply_queued_receipts(Settings.load())
    assert recovered["applied"] >= 1
    once = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert once["subsidy_minor"] == 50000

    second_account = _books(client, headers)
    second, _body = _determination(client, headers, second_account, resident=10000, agency=60000)
    queued = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "business_bank",
            "external_id": f"race-{uuid4().hex[:8]}",
            "method": "bank_transfer",
            "amount_minor": 60000,
            "tenancy_code": second,
            "service_period": "2026-11",
            "idempotency_key": _key("race-receipt"),
        },
    )
    assert queued.status_code == 200, queued.text
    errors: list[BaseException] = []

    def _run() -> None:
        try:
            apply_queued_receipts(Settings.load())
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    first = threading.Thread(target=_run)
    other = threading.Thread(target=_run)
    first.start()
    other.start()
    first.join(timeout=30)
    other.join(timeout=30)
    assert not errors
    raced = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": second}).json()
    assert raced["subsidy_minor"] == 60000
    assert raced["due_minor"] == 10000


def test_worker_process_applies_a_queued_receipt_once(client):
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, _body = _determination(client, headers, account, resident=20000, agency=80000)
    created = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "business_bank",
            "external_id": f"worker-{uuid4().hex[:8]}",
            "method": "bank_transfer",
            "amount_minor": 80000,
            "tenancy_code": tenancy,
            "service_period": "2026-11",
            "idempotency_key": _key("worker-receipt"),
        },
    )
    assert created.status_code == 200, created.text
    env = os.environ.copy()
    env["PHASE18_WORKER_ONCE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-m", "perchpoint.phase17_worker"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "phase18-worker-once" in completed.stdout
    view = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert view["agency_outstanding_minor"] == 0
    assert view["subsidy_minor"] == 80000
    assert view["due_minor"] == 20000
    replay = client.post(
        "/api/v2/payments/assistance/receipts/apply",
        headers=headers,
        json={"receipt_reference": created.json()["reference"], "idempotency_key": _key("worker-replay")},
    )
    assert replay.json()["replayed"] is True
    confirmed = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert confirmed["subsidy_minor"] == 80000
