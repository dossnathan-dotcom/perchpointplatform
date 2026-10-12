"""Phase 17 payment routes. Live collection stays closed. Callbacks use provider signatures, not browser CSRF."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from .commands import CommandError
from .phase17_payments import (
    accept_payer,
    approve_exception,
    checkout,
    exceptions,
    integration_health,
    invite_payer,
    publish_charge,
    reconcile,
    record_provider_event,
    revoke_payer,
    enroll_autopay,
    set_autopay_state,
    open_processor_dispute,
    record_return,
    request_refund,
    run_autopay,
    summary,
)
from .phase17_stripe import signature_ok
from .phase6_identity import resolve
from .routes import COOKIE, _require_csrf, actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class ChargeBody(BaseModel):
    tenancy_code: str
    amount_minor: int
    category: str = "rent"
    description: str
    account_reference: str | None = None
    rent_basis_minor: int | None = None
    idempotency_key: str = Field(min_length=8)


class CheckoutBody(BaseModel):
    obligation_reference: str
    amount_minor: int
    method: str = "card"
    scenario: str | None = None
    idempotency_key: str = Field(min_length=8)


class RefundBody(BaseModel):
    payment_reference: str
    amount_minor: int
    description: str
    resident_explanation: str
    reason_category: str = "resident_request"
    scenario: str | None = None
    idempotency_key: str = Field(min_length=8)


class ExceptionBody(BaseModel):
    reference: str
    amount_minor: int
    reason: str
    idempotency_key: str = Field(min_length=8)


class PayerBody(BaseModel):
    email: str
    tenancy_code: str | None = None


class AcceptBody(BaseModel):
    invitation_token: str


def _call(action):
    try:
        return action()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "A payment is already processing for that obligation.", "retryable": False}) from exc
    except CommandError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


def _browser(request: Request, current: Settings) -> None:
    session = resolve(current, request.cookies.get(COOKIE))
    if session and session.get("status") == "active":
        _require_csrf(request, session)


@router.get("/payments/summary")
def read_summary(tenancy_code: str | None = None, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: summary(current, current_actor["id"], current_actor["organization_id"], tenancy_code))


@router.post("/payments/charges")
def create_charge(body: ChargeBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: publish_charge(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/checkout")
def create_checkout(body: CheckoutBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: checkout(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/checkout/{reference}/reconcile")
def reconcile_checkout(reference: str, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: reconcile(current, current_actor["id"], current_actor["organization_id"], reference))


@router.post("/payments/refunds")
def create_refund(body: RefundBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: request_refund(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


class AutopayBody(BaseModel):
    tenancy_code: str
    cap_minor: int
    day_of_month: int = 1


class AutopayRunBody(BaseModel):
    tenancy_code: str
    period_code: str


class ReturnBody(BaseModel):
    payment_reference: str
    amount_minor: int


class DisputeBody(BaseModel):
    payment_reference: str
    amount_minor: int
    reason_code: str = "card_dispute"


@router.post("/payments/autopay")
def create_autopay(body: AutopayBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: enroll_autopay(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


class AutopayStateBody(BaseModel):
    tenancy_code: str
    state: str


@router.post("/payments/autopay/state")
def change_autopay(body: AutopayStateBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: set_autopay_state(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/autopay/run")
def execute_autopay(body: AutopayRunBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: run_autopay(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/returns")
def create_return(body: ReturnBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: record_return(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/disputes")
def create_dispute(body: DisputeBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: open_processor_dispute(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.get("/payments/refunds/exceptions")
def read_exceptions(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: exceptions(current, current_actor["id"], current_actor["organization_id"]))


@router.post("/payments/refunds/exceptions")
def decide_exception(body: ExceptionBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: approve_exception(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/payers")
def create_payer(body: PayerBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: invite_payer(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


class RevokePayerBody(BaseModel):
    tenancy_code: str


@router.post("/payments/payers/revoke")
def revoke_invitation(body: RevokePayerBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: revoke_payer(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/payers/accept")
def accept_invitation(body: AcceptBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: accept_payer(current, current_actor["id"], current_actor["organization_id"], body.invitation_token))


@router.get("/payments/integration")
def read_integration(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: integration_health(current, current_actor["id"], current_actor["organization_id"]))


@router.post("/payments/provider-events")
async def provider_event(request: Request, current: Settings = Depends(settings)) -> dict:
    body = await request.body()
    if len(body) > 200_000:
        raise HTTPException(413, {"code": "invalid", "message": "The provider event is too large.", "retryable": False})
    if not signature_ok(body, request.headers.get("x-perchpoint-provider-signature", "")):
        raise HTTPException(401, {"code": "denied", "message": "The provider signature was not accepted.", "retryable": False})
    try:
        payload = json.loads(body.decode())
    except json.JSONDecodeError as exc:
        raise HTTPException(400, {"code": "invalid", "message": "The provider event could not be read.", "retryable": False}) from exc
    try:
        return record_provider_event(current, payload)
    except Exception as exc:
        raise HTTPException(503, {"code": "unavailable", "message": "The provider event was not stored.", "retryable": True}) from exc
