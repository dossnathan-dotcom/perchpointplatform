"""Contract tests for the real Stripe SDK adapter. No sandbox call is made."""
import json
from urllib.parse import parse_qs

import stripe

from perchpoint.phase17_stripe import PINNED_STRIPE_VERSION, ProviderTimeout, StripeAdapter


class ScriptedHttp(stripe.HTTPClient):
    name = "scripted"

    def __init__(self, responses):
        super().__init__()
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, headers, post_data=None, *, _usage=None):
        self.calls.append({"method": method, "url": url, "headers": dict(headers or {}), "body": post_data})
        scripted = self.responses.pop(0)
        if isinstance(scripted, Exception):
            raise scripted
        body, status = scripted
        return json.dumps(body), status, {"request-id": "req_test"}

    def request_stream(self, method, url, headers, post_data=None, *, _usage=None):
        raise NotImplementedError

    def close(self):
        return None


def _adapter(responses, account="acct_test"):
    return StripeAdapter(api_key="sk_test_contract_not_a_live_key", http_client=ScriptedHttp(responses), stripe_account=account), responses


def _body(call):
    return parse_qs(call["body"] or "")


def test_payment_intent_contract_maps_success_pending_and_action():
    client = ScriptedHttp([
        ({"id": "pi_ok", "object": "payment_intent", "amount": 40000, "currency": "usd", "status": "succeeded"}, 200),
    ])
    adapter = StripeAdapter(api_key="sk_test_contract_not_a_live_key", http_client=client, stripe_account="acct_test")
    result = adapter.create_payment(idempotency_key="pay-400", amount_minor=40000, payment_method="pm_card")
    assert result["status"] == "succeeded"
    call = client.calls[0]
    assert call["method"] == "post"
    assert call["url"].endswith("/v1/payment_intents")
    assert call["headers"]["Stripe-Version"] == PINNED_STRIPE_VERSION
    assert call["headers"]["Stripe-Account"] == "acct_test"
    assert call["headers"]["Idempotency-Key"] == "pay-400"
    body = _body(call)
    assert body["amount"] == ["40000"]
    assert body["currency"] == ["usd"]
    assert body["confirm"] == ["true"]

    pending = ScriptedHttp([({"id": "pi_pending", "object": "payment_intent", "amount": 60000, "currency": "usd", "status": "processing"}, 200)])
    assert StripeAdapter(api_key="sk_test_contract_not_a_live_key", http_client=pending).create_payment(
        idempotency_key="pay-600", amount_minor=60000, payment_method="pm_bank"
    )["status"] == "processing"
    action = ScriptedHttp([({"id": "pi_action", "object": "payment_intent", "amount": 1000, "currency": "usd", "status": "requires_action"}, 200)])
    assert StripeAdapter(api_key="sk_test_contract_not_a_live_key", http_client=action).create_payment(
        idempotency_key="pay-action", amount_minor=1000, payment_method="pm_card"
    )["status"] == "action_required"


def test_decline_timeout_refund_and_retrieve_keep_one_idempotency_key():
    declined = ScriptedHttp([
        ({"error": {"type": "card_error", "code": "card_declined", "message": "declined"}}, 402),
    ])
    adapter = StripeAdapter(api_key="sk_test_contract_not_a_live_key", http_client=declined)
    failed = adapter.create_payment(idempotency_key="pay-decline", amount_minor=40000, payment_method="pm_card")
    assert failed["status"] == "failed" and failed["failure_code"] == "card_declined"
    assert len(declined.calls) == 1

    timed_out = ScriptedHttp([stripe.APIConnectionError("timeout after the request was accepted")])
    adapter = StripeAdapter(api_key="sk_test_contract_not_a_live_key", http_client=timed_out)
    try:
        adapter.create_payment(idempotency_key="pay-timeout", amount_minor=40000, payment_method="pm_card")
        raise AssertionError("timeout should stay unknown")
    except ProviderTimeout as exc:
        assert exc.provider_reference == "pay-timeout"
    assert len(timed_out.calls) == 1
    assert timed_out.calls[0]["headers"]["Idempotency-Key"] == "pay-timeout"

    refund_http = ScriptedHttp([
        ({"id": "re_400", "object": "refund", "amount": 40000, "currency": "usd", "status": "succeeded", "payment_intent": "pi_ok"}, 200),
    ])
    refund = StripeAdapter(api_key="sk_test_contract_not_a_live_key", http_client=refund_http).refund_payment(
        idempotency_key="refund-400", payment_intent="pi_ok", amount_minor=40000
    )
    assert refund["amount"] == 40000 and refund["payment_intent"] == "pi_ok"
    refund_call = refund_http.calls[0]
    assert refund_call["url"].endswith("/v1/refunds")
    assert _body(refund_call)["amount"] == ["40000"]
    assert _body(refund_call)["payment_intent"] == ["pi_ok"]
    assert refund_call["headers"]["Idempotency-Key"] == "refund-400"

    retrieved = ScriptedHttp([
        ({"id": "pi_ok", "object": "payment_intent", "amount": 40000, "currency": "usd", "status": "succeeded"}, 200),
    ])
    assert StripeAdapter(api_key="sk_test_contract_not_a_live_key", http_client=retrieved).retrieve_payment("pi_ok")["id"] == "pi_ok"
    assert retrieved.calls[0]["method"] == "get"
    assert retrieved.calls[0]["url"].endswith("/v1/payment_intents/pi_ok")
