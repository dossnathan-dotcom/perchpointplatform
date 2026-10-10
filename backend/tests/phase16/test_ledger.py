"""Phase 16 derives a resident subledger from an active household and does not move money."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from perchpoint.db import runtime_transaction
from perchpoint.routes import create_app
from perchpoint.settings import Settings
from tests.phase15.test_portal import _activate, _key, _login


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def _household(client, headers):
    lease_reference = _activate(client, headers)
    opened = client.post(
        "/api/v2/leasing/portal/memberships",
        headers=headers,
        json={"reference": lease_reference, "idempotency_key": _key("portal")},
    )
    assert opened.status_code == 200, opened.text
    return lease_reference, opened.json()["reference"], opened.json()["capability"]


def test_ledger_posts_exact_minor_units_without_moving_money(client):
    headers = _login(client, "ann.synthetic@example.com")
    lease_reference, portal_reference, capability = _household(client, headers)
    early = client.post(
        "/api/v2/leasing/ledger/accounts",
        headers=headers,
        json={"reference": portal_reference, "idempotency_key": _key("early")},
    )
    assert early.status_code == 409
    assert client.post("/api/v2/public/portal/invitations", json={"capability": capability, "idempotency_key": _key("accept")}).status_code == 200
    account_key = _key("account")
    opened = client.post(
        "/api/v2/leasing/ledger/accounts",
        headers=headers,
        json={"reference": portal_reference, "idempotency_key": account_key},
    )
    assert opened.status_code == 200, opened.text
    assert opened.json()["state"] == "open" and opened.json()["currency_code"] == "USD"
    account = opened.json()["reference"]
    assert client.post("/api/v2/leasing/ledger/accounts", headers=headers, json={"reference": portal_reference, "idempotency_key": account_key}).json()["replayed"] is True
    assert client.post("/api/v2/leasing/ledger/accounts", headers=headers, json={"reference": portal_reference, "idempotency_key": _key("other")}).status_code == 409
    charged = client.post(
        "/api/v2/leasing/ledger/charges",
        headers=headers,
        json={"reference": account, "amount_minor": 140000, "occurrence_code": f"rent-{uuid4().hex[:8]}", "idempotency_key": _key("rent")},
    )
    assert charged.status_code == 200, charged.text
    assert charged.json()["due_minor"] == 140000 and charged.json()["money_moved"] is False
    occurrence = f"rent-{uuid4().hex[:8]}"
    rent_key = _key("rent-once")
    once = client.post(
        "/api/v2/leasing/ledger/charges",
        headers=headers,
        json={"reference": account, "amount_minor": 1000, "occurrence_code": occurrence, "idempotency_key": rent_key},
    )
    assert once.status_code == 200 and once.json()["due_minor"] == 141000
    assert client.post(
        "/api/v2/leasing/ledger/charges",
        headers=headers,
        json={"reference": account, "amount_minor": 1000, "occurrence_code": occurrence, "idempotency_key": rent_key},
    ).json()["replayed"] is True
    assert client.post(
        "/api/v2/leasing/ledger/charges",
        headers=headers,
        json={"reference": account, "amount_minor": 1000, "occurrence_code": occurrence, "idempotency_key": _key("rent-again")},
    ).status_code == 409
    subsidy = client.post(
        "/api/v2/leasing/ledger/subsidies",
        headers=headers,
        json={"reference": account, "amount_minor": 20000, "idempotency_key": _key("subsidy")},
    )
    assert subsidy.status_code == 200, subsidy.text
    assert subsidy.json()["resident_debt_created"] is False and subsidy.json()["due_minor"] == 141000 and subsidy.json()["subsidy_minor"] == 20000
    deposit = client.post(
        "/api/v2/leasing/ledger/deposits",
        headers=headers,
        json={"reference": account, "amount_minor": 140000, "idempotency_key": _key("deposit")},
    )
    assert deposit.json()["applied_to_rent"] is False and deposit.json()["due_minor"] == 141000 and deposit.json()["deposit_minor"] == 140000
    partial = client.post(
        "/api/v2/leasing/ledger/settlements",
        headers=headers,
        json={"reference": account, "amount_minor": 100000, "idempotency_key": _key("pay")},
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["applied_minor"] == 100000 and partial.json()["unapplied_minor"] == 0
    assert partial.json()["applied_minor"] + partial.json()["unapplied_minor"] == 100000
    assert partial.json()["due_minor"] == 41000 and partial.json()["processor_called"] is False
    statement = client.post("/api/v2/leasing/ledger/statements", headers=headers, json={"reference": account})
    assert statement.status_code == 200, statement.text
    assert statement.json()["due_minor"] == 41000 and statement.json()["delivered"] is False
    assert "SYNTHETIC OPERATIONAL STATEMENT" in statement.json()["body"]
    over = client.post(
        "/api/v2/leasing/ledger/settlements",
        headers=headers,
        json={"reference": account, "amount_minor": 50000, "idempotency_key": _key("over")},
    )
    assert over.json()["applied_minor"] == 41000 and over.json()["unapplied_minor"] == 9000
    assert over.json()["due_minor"] == 0 and over.json()["prepayment_minor"] == 9000
    assert client.post("/api/v2/leasing/ledger/charges", headers=headers, json={"reference": account, "amount_minor": 0, "occurrence_code": "zero", "idempotency_key": _key("zero")}).status_code == 400
    assert client.post("/api/v2/leasing/ledger/charges", headers=headers, json={"reference": account, "amount_minor": 10.5, "occurrence_code": "float", "idempotency_key": _key("float")}).status_code == 422
    reversed_charge = client.post(
        "/api/v2/leasing/ledger/reversals",
        headers=headers,
        json={"reference": charged.json()["reference"], "idempotency_key": _key("reverse")},
    )
    assert reversed_charge.status_code == 200, reversed_charge.text
    assert reversed_charge.json()["original_lines_unchanged"] is True and reversed_charge.json()["money_moved"] is False
    assert client.post(
        "/api/v2/leasing/ledger/reversals",
        headers=headers,
        json={"reference": charged.json()["reference"], "idempotency_key": _key("reverse-again")},
    ).status_code == 409
    dispute = client.post("/api/v2/leasing/ledger/disputes", headers=headers, json={"reference": account, "reason_code": "amount_question"})
    assert dispute.status_code == 200 and dispute.json()["legal_conclusion"] is False and dispute.json()["journal_lines_unchanged"] is True
    closed = client.post("/api/v2/leasing/ledger/periods/close", headers=headers, json={"reference": account})
    assert closed.status_code == 200 and closed.json()["state"] == "closed"
    assert client.post(
        "/api/v2/leasing/ledger/charges",
        headers=headers,
        json={"reference": account, "amount_minor": 100, "occurrence_code": "after-close", "idempotency_key": _key("closed")},
    ).status_code == 409
    assert client.post("/api/v2/leasing/ledger/manifest", headers=headers, json={"display_name": "Example Homes", "extra": {"secret": "not-stored"}}).status_code == 400
    manifest = client.post("/api/v2/leasing/ledger/manifest", headers=headers, json={"display_name": "Example Homes"})
    assert manifest.status_code == 200 and manifest.json()["real_values_activated"] is False
    assert client.post("/api/v2/leasing/ledger/payments", headers=headers).status_code == 400
    assert client.post("/api/v2/leasing/ledger/balances", headers=headers).status_code == 400
    assert client.post("/api/v2/leasing/portal/payments", headers=headers).status_code == 400
    home = client.post("/api/v2/leasing/portal/home", headers=headers, json={"reference": portal_reference})
    assert home.status_code == 200 and home.json()["ledger_posted"] is False
    assert client.post("/api/v2/leasing/ledger/accounts", headers=_login(client, "resident.synthetic@example.com"), json={"reference": portal_reference, "idempotency_key": _key("resident")}).status_code == 403
    assert client.post("/api/v2/leasing/ledger/accounts", headers=_login(client, "isolation.synthetic@example.com"), json={"reference": portal_reference, "idempotency_key": _key("isolation")}).status_code == 403
    with runtime_transaction(Settings.load(), None, None, uuid4()) as connection:
        assert connection.execute(text("SELECT count(*) FROM journal_transactions")).scalar_one() == 0
        assert connection.execute(text("SELECT to_regclass('public.ledger_postings')")).scalar_one() is None
        assert os.environ["PHASE2_DEV_PASSWORD"]
