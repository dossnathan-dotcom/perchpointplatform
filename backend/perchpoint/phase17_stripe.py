"""Stripe-shaped adapter. The default transport is local and does not open a network connection.

Mocked transport results are not a Stripe sandbox transaction and do not move money.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from uuid import uuid4

LOCAL_WEBHOOK_KEY = os.environ.get("PHASE17_WEBHOOK_SECRET", "local-only-not-production-phase17-webhook")


class ProviderTimeout(Exception):
    def __init__(self, provider_reference: str):
        self.provider_reference = provider_reference


class FakeTransport:
    """Remembers an accepted result so a timeout can be reconciled without a second charge."""

    def __init__(self) -> None:
        self.results: dict[str, dict] = {}

    def charge(self, *, idempotency_key: str, amount_minor: int, method: str, scenario: str) -> dict:
        existing = self.results.get(idempotency_key)
        if existing is not None:
            return existing
        reference = f"py_local_{uuid4().hex[:12]}"
        if scenario == "decline":
            result = {"status": "failed", "id": reference, "amount": amount_minor, "method": method, "safe_message": "The synthetic payment was declined."}
        elif scenario == "pending":
            result = {"status": "processing", "id": reference, "amount": amount_minor, "method": method, "safe_message": "The synthetic bank debit is processing."}
        elif scenario == "timeout_after_accept":
            result = {"status": "succeeded", "id": reference, "amount": amount_minor, "method": method, "safe_message": "The synthetic payment was accepted."}
            self.results[idempotency_key] = result
            raise ProviderTimeout(reference)
        elif scenario == "outage":
            raise ConnectionError("The local payment adapter is unavailable.")
        else:
            result = {"status": "succeeded", "id": reference, "amount": amount_minor, "method": method, "safe_message": "The synthetic payment was accepted."}
        self.results[idempotency_key] = result
        return result

    def refund(self, *, idempotency_key: str, amount_minor: int, scenario: str) -> dict:
        existing = self.results.get(idempotency_key)
        if existing is not None:
            return existing
        reference = f"re_local_{uuid4().hex[:12]}"
        if scenario == "timeout_after_accept":
            result = {"status": "succeeded", "id": reference, "amount": amount_minor}
            self.results[idempotency_key] = result
            raise ProviderTimeout(reference)
        if scenario == "fail":
            result = {"status": "failed", "id": reference, "amount": amount_minor}
        else:
            result = {"status": "succeeded", "id": reference, "amount": amount_minor}
        self.results[idempotency_key] = result
        return result

    def retrieve(self, idempotency_key: str) -> dict | None:
        return self.results.get(idempotency_key)


TRANSPORT = FakeTransport()

PINNED_STRIPE_VERSION = "2026-02-25.clover"


class StripeAdapter:
    """Real Stripe SDK calls. Tests inject the HTTP client. This class does not run in local fake checkout."""

    def __init__(self, *, api_key: str, http_client, stripe_account: str | None = None):
        import stripe

        self._stripe = stripe
        self.client = stripe.StripeClient(
            api_key,
            stripe_version=PINNED_STRIPE_VERSION,
            stripe_account=stripe_account,
            http_client=http_client,
            max_network_retries=0,
        )

    def create_payment(self, *, idempotency_key: str, amount_minor: int, currency: str = "usd", payment_method: str, off_session: bool = False) -> dict:
        try:
            intent = self.client.v1.payment_intents.create(
                params={
                    "amount": amount_minor,
                    "currency": currency,
                    "payment_method": payment_method,
                    "confirm": True,
                    "off_session": off_session,
                },
                options={"idempotency_key": idempotency_key},
            )
        except self._stripe.CardError as exc:
            return {"status": "failed", "id": None, "amount": amount_minor, "currency": currency, "failure_code": exc.code}
        except self._stripe.APIConnectionError as exc:
            raise ProviderTimeout(idempotency_key) from exc
        return _normalize_intent(intent)

    def create_cash_app_payment(self, *, idempotency_key: str, amount_minor: int, currency: str = "usd") -> dict:
        """Cash App Pay is a Stripe method type. It is not an off-session card confirm."""
        from .phase18_assistance import cash_app_payment_intent_params

        shape = cash_app_payment_intent_params(amount_minor)
        intent = self.client.v1.payment_intents.create(
            params={
                "amount": shape["amount"],
                "currency": currency,
                "payment_method_types": ["cashapp"],
                "confirm": False,
            },
            options={"idempotency_key": idempotency_key},
        )
        normalized = _normalize_intent(intent)
        if intent.status == "requires_payment_method":
            normalized["status"] = "action_required"
        return normalized

    def refund_payment(self, *, idempotency_key: str, payment_intent: str, amount_minor: int) -> dict:
        try:
            refund = self.client.v1.refunds.create(
                params={"payment_intent": payment_intent, "amount": amount_minor},
                options={"idempotency_key": idempotency_key},
            )
        except self._stripe.APIConnectionError as exc:
            raise ProviderTimeout(idempotency_key) from exc
        return {"status": refund.status, "id": refund.id, "amount": refund.amount, "payment_intent": refund.payment_intent}

    def retrieve_payment(self, payment_intent: str) -> dict:
        intent = self.client.v1.payment_intents.retrieve(payment_intent)
        return _normalize_intent(intent)


def _normalize_intent(intent) -> dict:
    status = {
        "succeeded": "succeeded",
        "processing": "processing",
        "requires_action": "action_required",
        "requires_payment_method": "failed",
        "canceled": "failed",
    }.get(intent.status, "unknown")
    return {
        "status": status,
        "id": intent.id,
        "amount": intent.amount,
        "currency": intent.currency,
        "provider_status": intent.status,
    }


def sign_payload(body: bytes, secret: str = LOCAL_WEBHOOK_KEY) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def signature_ok(body: bytes, presented: str, secret: str = LOCAL_WEBHOOK_KEY) -> bool:
    if not presented:
        return False
    if secret == "local-only-not-production-phase17-webhook" and os.environ.get("PHASE3_ENVIRONMENT", "local") not in {"local", "test"}:
        return False
    expected = sign_payload(body, secret)
    return hmac.compare_digest(expected, presented)
