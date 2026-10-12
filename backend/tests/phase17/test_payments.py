"""Phase 17 posts one synthetic collection into the Phase 16 ledger and enforces the refund cap."""
import json
import os
import re
import time
import urllib.request
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.phase15.test_portal import _key, _login
from tests.phase16.test_ledger import _household


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def create_app():
    from perchpoint.routes import create_app as build
    return build()


def test_preactivation_obligation_is_payable_without_opening_the_active_ledger(client):
    headers = _login(client, "ann.synthetic@example.com")
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    blocked = client.post(
        "/api/v2/payments/charges",
        headers=headers,
        json={
            "tenancy_code": tenancy,
            "amount_minor": 25000,
            "category": "preactivation",
            "description": "Holding fee before activation",
            "account_reference": "account-not-opened",
            "idempotency_key": _key("pre-blocked"),
        },
    )
    assert blocked.status_code == 409, blocked.text
    published = client.post(
        "/api/v2/payments/charges",
        headers=headers,
        json={
            "tenancy_code": tenancy,
            "amount_minor": 25000,
            "category": "preactivation",
            "description": "Holding fee before activation",
            "idempotency_key": _key("pre-publish"),
        },
    )
    assert published.status_code == 200, published.text
    body = published.json()
    assert body["payable"] is True and body["journal_reference"] is None and body["money_moved"] is False
    paid = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={
            "obligation_reference": body["reference"],
            "amount_minor": 25000,
            "method": "card",
            "scenario": "succeeded",
            "idempotency_key": _key("pre-pay"),
        },
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["state"] == "succeeded"
    assert paid.json()["ledger_status"] == "not_linked"
    assert paid.json()["ledger_reference"] is None
    assert paid.json()["due_minor"] is None


def test_published_charge_is_payable_once_and_refunds_share_one_cap(client):
    headers = _login(client, "ann.synthetic@example.com")
    _lease, portal_reference, capability = _household(client, headers)
    assert client.post("/api/v2/public/portal/invitations", json={"capability": capability, "idempotency_key": _key("accept")}).status_code == 200
    opened = client.post("/api/v2/leasing/ledger/accounts", headers=headers, json={"reference": portal_reference, "idempotency_key": _key("account")})
    assert opened.status_code == 200, opened.text
    account = opened.json()["reference"]
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    published = client.post(
        "/api/v2/payments/charges",
        headers=headers,
        json={
            "tenancy_code": tenancy,
            "amount_minor": 100000,
            "category": "rent",
            "description": "October rent for the synthetic payment test",
            "account_reference": account,
            "rent_basis_minor": 100000,
            "idempotency_key": _key("publish"),
        },
    )
    assert published.status_code == 200, published.text
    assert published.json()["payable"] is True and published.json()["money_moved"] is False
    obligation = published.json()["reference"]
    paid = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={"obligation_reference": obligation, "amount_minor": 100000, "method": "card", "scenario": "succeeded", "idempotency_key": _key("pay")},
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["state"] == "succeeded"
    assert paid.json()["ledger_status"] == "posted"
    assert paid.json()["due_minor"] == 0
    assert paid.json()["money_moved"] is False
    replay = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={"obligation_reference": obligation, "amount_minor": 100000, "method": "card", "scenario": "succeeded", "idempotency_key": paid.json() and _key("pay-other")},
    )
    assert replay.status_code == 409
    refund_key = _key("refund-a")
    refund_body = {
        "payment_reference": paid.json()["reference"],
        "amount_minor": 40000,
        "description": "Partial rent refund for a duplicate fee.",
        "resident_explanation": "We are returning the duplicate portion of October rent.",
        "idempotency_key": refund_key,
    }
    first = client.post("/api/v2/payments/refunds", headers=headers, json=refund_body)
    assert first.status_code == 200, first.text
    assert first.json()["state"] == "succeeded" and first.json()["money_moved"] is False
    assert client.post("/api/v2/payments/refunds", headers=headers, json=refund_body).json()["replayed"] is True
    changed = dict(refund_body)
    changed["amount_minor"] = 100
    assert client.post("/api/v2/payments/refunds", headers=headers, json=changed).status_code == 409
    overrun = client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 70000,
            "description": "This second refund would exceed one month of rent.",
            "resident_explanation": "The remaining request is above the ordinary cap.",
            "idempotency_key": _key("refund-b"),
        },
    )
    assert overrun.status_code == 200, overrun.text
    assert overrun.json()["state"] == "owner_decision_required"
    assert overrun.json()["ordinary_max_minor"] == 60000
    assert client.post("/api/v2/leasing/ledger/payments", headers=headers).status_code == 400
    assert client.post("/api/v2/payments/provider-events", content=b"{}", headers={"content-type": "application/json"}).status_code == 401
    resident = _login(client, "resident.synthetic@example.com")
    assert client.post(
        "/api/v2/payments/refunds",
        headers=resident,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 100,
            "description": "A resident cannot approve a refund.",
            "resident_explanation": "This request must be refused.",
            "idempotency_key": _key("resident-refund"),
        },
    ).status_code == 403
    assert os.environ["PHASE2_DEV_PASSWORD"]


def _account(client):
    headers = _login(client, "ann.synthetic@example.com")
    _lease, portal_reference, capability = _household(client, headers)
    assert client.post("/api/v2/public/portal/invitations", json={"capability": capability, "idempotency_key": _key("accept")}).status_code == 200
    opened = client.post(
        "/api/v2/leasing/ledger/accounts",
        headers=headers,
        json={"reference": portal_reference, "idempotency_key": _key("account")},
    )
    assert opened.status_code == 200, opened.text
    return headers, opened.json()["reference"]


def _publish(client, headers, account, tenancy, amount, rent):
    published = client.post(
        "/api/v2/payments/charges",
        headers=headers,
        json={
            "tenancy_code": tenancy,
            "amount_minor": amount,
            "category": "rent",
            "description": "Synthetic rent obligation for a payment scenario",
            "account_reference": account,
            "rent_basis_minor": rent,
            "idempotency_key": _key("publish"),
        },
    )
    assert published.status_code == 200, published.text
    return published.json()["reference"]


def _pay(client, headers, obligation, amount, scenario="succeeded", key=None):
    pay_key = key or _key("pay")
    paid = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={
            "obligation_reference": obligation,
            "amount_minor": amount,
            "method": "card",
            "scenario": scenario,
            "idempotency_key": pay_key,
        },
    )
    assert paid.status_code == 200, paid.text
    paid.pay_key = pay_key
    return paid


def test_two_partial_payments_settle_once_each(client):
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    first = _pay(client, headers, obligation, 40000)
    assert first.json()["due_minor"] == 60000
    second = _pay(client, headers, obligation, 60000)
    assert second.json()["due_minor"] == 0 and second.json()["ledger_status"] == "posted"
    replay = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={
            "obligation_reference": obligation,
            "amount_minor": 40000,
            "method": "card",
            "scenario": "succeeded",
            "idempotency_key": first.pay_key,
        },
    )
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    changed = client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={
            "obligation_reference": obligation,
            "amount_minor": 100,
            "method": "card",
            "scenario": "succeeded",
            "idempotency_key": first.pay_key,
        },
    )
    assert changed.status_code == 409
    assert client.post(
        "/api/v2/payments/checkout",
        headers=headers,
        json={"obligation_reference": obligation, "amount_minor": 100, "method": "card", "scenario": "succeeded", "idempotency_key": _key("extra")},
    ).status_code == 409
    summary = client.get("/api/v2/payments/summary", headers=headers, params={"tenancy_code": tenancy})
    assert summary.status_code == 200
    succeeded = [row for row in summary.json()["payments"] if row["state"] == "succeeded"]
    assert len(succeeded) == 2
    assert sum(row["amount_minor"] for row in succeeded) == 100000
    assert summary.json()["ledger"]["account_reference"] == account
    journals = summary.json()["ledger"]["journals"]
    assert sum(row["amount_minor"] for row in journals if row["kind"] == "charge") == 100000
    assert sum(row["amount_minor"] for row in journals if row["kind"] == "settlement") == 100000


def test_owner_exception_cannot_refund_more_than_the_source_payment(client):
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    paid = _pay(client, headers, obligation, 100000)
    refund_key = _key("refund-part")
    first = client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 40000,
            "description": "Ordinary refund within one month of rent.",
            "resident_explanation": "Returning four hundred dollars of the October rent.",
            "idempotency_key": refund_key,
        },
    )
    assert first.status_code == 200 and first.json()["state"] == "succeeded"
    waiting = client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 70000,
            "description": "This request is above both the remaining allowance and the source.",
            "resident_explanation": "The second request needs an owner decision.",
            "idempotency_key": _key("refund-over"),
        },
    )
    assert waiting.status_code == 200 and waiting.json()["state"] == "owner_decision_required"
    owner = _login(client, "faruk.synthetic@example.com")
    denied = client.post(
        "/api/v2/payments/refunds/exceptions",
        headers=owner,
        json={
            "reference": waiting.json()["reference"],
            "amount_minor": 70000,
            "reason": "The source payment only has six hundred dollars left.",
            "idempotency_key": _key("owner"),
        },
    )
    assert denied.status_code == 409, denied.text
    assert client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 70000,
            "description": "This request is above both the remaining allowance and the source.",
            "resident_explanation": "The second request needs an owner decision.",
            "idempotency_key": _key("refund-over-2"),
        },
    ).json()["state"] == "owner_decision_required"


def test_owner_exception_executes_once_when_the_source_can_fund_it(client):
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 200000, 100000)
    paid = _pay(client, headers, obligation, 200000)
    first = client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 40000,
            "description": "Ordinary refund within the monthly rent basis.",
            "resident_explanation": "Returning four hundred dollars of the collected rent.",
            "idempotency_key": _key("refund-400"),
        },
    )
    assert first.status_code == 200 and first.json()["state"] == "succeeded"
    waiting = client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 70000,
            "description": "This request is above the remaining ordinary rent allowance.",
            "resident_explanation": "The owner must approve this exact additional refund.",
            "idempotency_key": _key("refund-700"),
        },
    )
    assert waiting.status_code == 200 and waiting.json()["state"] == "owner_decision_required"
    owner = _login(client, "faruk.synthetic@example.com")
    owner_key = _key("owner-yes")
    approved = client.post(
        "/api/v2/payments/refunds/exceptions",
        headers=owner,
        json={
            "reference": waiting.json()["reference"],
            "amount_minor": 70000,
            "reason": "Approve this exact exception without resetting the ordinary cap.",
            "idempotency_key": owner_key,
        },
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["state"] == "succeeded" and approved.json()["ordinary_cap_reset"] is False
    replay = client.post(
        "/api/v2/payments/refunds/exceptions",
        headers=owner,
        json={
            "reference": waiting.json()["reference"],
            "amount_minor": 70000,
            "reason": "Approve this exact exception without resetting the ordinary cap.",
            "idempotency_key": owner_key,
        },
    )
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    later = client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 100,
            "description": "The ordinary allowance stays consumed after the exception.",
            "resident_explanation": "This further amount still needs an owner decision.",
            "idempotency_key": _key("refund-after"),
        },
    )
    assert later.status_code == 200 and later.json()["state"] == "owner_decision_required"


def test_autopay_collects_only_the_remainder_and_skips_over_the_cap(client):
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    assert _pay(client, headers, obligation, 40000).json()["due_minor"] == 60000
    enrolled = client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": tenancy, "cap_minor": 100000, "day_of_month": 1},
    )
    assert enrolled.status_code == 200, enrolled.text
    ran = client.post(
        "/api/v2/payments/autopay/run",
        headers=headers,
        json={"tenancy_code": tenancy, "period_code": "2026-10"},
    )
    assert ran.status_code == 200, ran.text
    assert ran.json()["state"] == "collected" and ran.json()["amount_minor"] == 60000
    assert ran.json()["payment"]["due_minor"] == 0
    again = client.post(
        "/api/v2/payments/autopay/run",
        headers=headers,
        json={"tenancy_code": tenancy, "period_code": "2026-10"},
    )
    assert again.json()["replayed"] is True
    capped = f"tenancy-{uuid4().hex[:8]}"
    _publish(client, headers, account, capped, 100000, 100000)
    assert client.post(
        "/api/v2/payments/autopay",
        headers=headers,
        json={"tenancy_code": capped, "cap_minor": 50000, "day_of_month": 1},
    ).status_code == 200
    skipped = client.post(
        "/api/v2/payments/autopay/run",
        headers=headers,
        json={"tenancy_code": capped, "period_code": "2026-10"},
    )
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["state"] == "action_required" and skipped.json()["reason"] == "over_cap"
    assert "payment" not in skipped.json()


def test_return_restores_the_obligation_and_an_open_dispute_blocks_refund(client):
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    paid = _pay(client, headers, obligation, 100000)
    returned = client.post(
        "/api/v2/payments/returns",
        headers=headers,
        json={"payment_reference": paid.json()["reference"], "amount_minor": 40000},
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["kind"] == "return" and returned.json()["due_minor"] == 40000 and returned.json()["money_moved"] is False
    dispute = client.post(
        "/api/v2/payments/disputes",
        headers=headers,
        json={"payment_reference": paid.json()["reference"], "amount_minor": 10000, "reason_code": "card_dispute"},
    )
    assert dispute.status_code == 200 and dispute.json()["journal_posted"] is False
    blocked = client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 10000,
            "description": "A refund cannot race an open processor dispute.",
            "resident_explanation": "Hold this refund until the dispute is resolved.",
            "idempotency_key": _key("blocked"),
        },
    )
    assert blocked.status_code == 409


def _mail_token(email: str) -> str:
    mailpit = os.environ.get("PHASE6_MAILPIT_URL", "http://127.0.0.1:8025")
    for _ in range(20):
        listing = json.load(urllib.request.urlopen(f"{mailpit}/api/v1/messages", timeout=3))
        match = next(
            (
                item
                for item in listing.get("messages", [])
                if any(recipient.get("Address", "").lower() == email.lower() for recipient in item.get("To", []))
            ),
            None,
        )
        if match:
            message = json.load(urllib.request.urlopen(f"{mailpit}/api/v1/message/{match['ID']}", timeout=3))
            text = (message.get("Text") or "").replace("=\r\n", "").replace("=\n", "")
            found = re.search(r"token=([A-Za-z0-9_\-]+)", text)
            if found:
                return found.group(1)
        time.sleep(0.1)
    raise AssertionError("Mailpit did not contain the invitation token")


def test_additional_payer_accepts_a_token_pays_and_cannot_continue_after_revocation(client):
    from tests.phase6.test_identity import _csrf, _mark_current_session_aal2, _provider_user

    os.environ["PHASE6_ALLOWED_ORIGINS"] = "http://testserver,http://127.0.0.1:3000,http://localhost:3000"
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    other = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    hidden_charge = client.post(
        "/api/v2/payments/charges",
        headers=headers,
        json={
            "tenancy_code": other,
            "amount_minor": 50000,
            "category": "rent",
            "description": "A charge the additional payer must not see",
            "rent_basis_minor": 50000,
            "idempotency_key": _key("hidden"),
        },
    )
    assert hidden_charge.status_code == 200, hidden_charge.text
    _provider_user("ann.synthetic@example.com")
    identity = TestClient(create_app())
    signed = identity.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": os.environ["PHASE2_DEV_PASSWORD"]},
    )
    assert signed.status_code == 200, signed.text
    _mark_current_session_aal2(identity, signed.json())
    payer_email = f"payer.{uuid4().hex[:8]}@example.com"
    payer_password = "Synthetic invitation password 2046!"
    invited = identity.post(
        "/api/v2/auth/invitations",
        headers=_csrf(signed.json()),
        json={"email": payer_email, "role_name": "additional_payer", "purpose": "Pay one granted tenancy", "staff": False},
    )
    assert invited.status_code == 200, invited.text
    assert "token" not in invited.json()
    identity_token = _mail_token(payer_email)
    activated = identity.post(
        "/api/v2/auth/invitations/accept",
        json={"token": identity_token, "email": payer_email, "password": payer_password},
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["role_name"] == "additional_payer"
    payer = TestClient(create_app())
    payer_signed = payer.post("/api/v2/auth/sign-in", json={"email": payer_email, "password": payer_password})
    assert payer_signed.status_code == 200, payer_signed.text
    assert payer_signed.json()["mfa_required"] is False
    grant = client.post(
        "/api/v2/payments/payers",
        headers=headers,
        json={"email": payer_email, "tenancy_code": tenancy},
    )
    assert grant.status_code == 200, grant.text
    payer_token = grant.json()["invitation_token"]
    resident = _login(client, "resident.synthetic@example.com")
    denied = client.post("/api/v2/payments/payers/accept", headers=resident, json={"invitation_token": payer_token})
    assert denied.status_code == 409
    accepted = payer.post(
        "/api/v2/payments/payers/accept",
        headers=_csrf(payer_signed.json()),
        json={"invitation_token": payer_token},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["state"] == "active"
    assert _pay(client, headers, obligation, 40000).json()["due_minor"] == 60000
    too_much = payer.post(
        "/api/v2/payments/checkout",
        headers=_csrf(payer_signed.json()),
        json={"obligation_reference": obligation, "amount_minor": 100000, "method": "card", "idempotency_key": _key("payer-too-much")},
    )
    assert too_much.status_code == 409, too_much.text
    paid = payer.post(
        "/api/v2/payments/checkout",
        headers=_csrf(payer_signed.json()),
        json={"obligation_reference": obligation, "amount_minor": 60000, "method": "card", "idempotency_key": _key("payer-rest")},
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["due_minor"] == 0 and paid.json()["money_moved"] is False
    own = payer.get("/api/v2/payments/summary", headers=_csrf(payer_signed.json()), params={"tenancy_code": tenancy})
    assert own.status_code == 200, own.text
    assert own.json()["obligations"][0]["remaining_minor"] == 0
    assert [row["amount_minor"] for row in own.json()["payments"]] == [60000]
    hidden = payer.get("/api/v2/payments/summary", headers=_csrf(payer_signed.json()), params={"tenancy_code": other})
    assert hidden.json()["obligations"] == []
    second = client.post("/api/v2/payments/payers", headers=headers, json={"email": payer_email, "tenancy_code": tenancy})
    assert second.status_code == 200, second.text
    repeat = payer.post(
        "/api/v2/payments/payers/accept",
        headers=_csrf(payer_signed.json()),
        json={"invitation_token": second.json()["invitation_token"]},
    )
    assert repeat.status_code == 409
    revoked = client.post("/api/v2/payments/payers/revoke", headers=headers, json={"tenancy_code": tenancy})
    assert revoked.status_code == 200, revoked.text
    blocked = payer.post(
        "/api/v2/payments/checkout",
        headers=_csrf(payer_signed.json()),
        json={"obligation_reference": obligation, "amount_minor": 100, "method": "card", "idempotency_key": _key("payer-after")},
    )
    assert blocked.status_code == 404
    hidden_refunds = payer.get("/api/v2/payments/summary", headers=_csrf(payer_signed.json()), params={"tenancy_code": other})
    assert hidden_refunds.json()["refunds"] == []


def test_resident_cannot_read_or_command_another_tenancy(client):
    headers, account = _account(client)
    tenancy = f"tenancy-{uuid4().hex[:8]}"
    obligation = _publish(client, headers, account, tenancy, 100000, 100000)
    paid = _pay(client, headers, obligation, 100000)
    refund = client.post(
        "/api/v2/payments/refunds",
        headers=headers,
        json={
            "payment_reference": paid.json()["reference"],
            "amount_minor": 10000,
            "description": "A refund the other resident must not see.",
            "resident_explanation": "This explanation stays with the tenancy.",
            "idempotency_key": _key("hidden-refund"),
        },
    )
    assert refund.status_code == 200, refund.text
    resident = _login(client, "resident.synthetic@example.com")
    summary = client.get("/api/v2/payments/summary", headers=resident, params={"tenancy_code": tenancy})
    assert summary.status_code == 200, summary.text
    assert summary.json()["obligations"] == []
    assert summary.json()["refunds"] == []
    invited = client.post(
        "/api/v2/payments/payers",
        headers=resident,
        json={"email": "payer.hidden@example.com", "tenancy_code": tenancy},
    )
    assert invited.status_code == 403, invited.text
    enrolled = client.post(
        "/api/v2/payments/autopay",
        headers=resident,
        json={"tenancy_code": tenancy, "cap_minor": 100000, "day_of_month": 11},
    )
    assert enrolled.status_code == 403, enrolled.text
