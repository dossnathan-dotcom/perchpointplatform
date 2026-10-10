"""Resident ledger commands. Live payment and formal general-ledger writes stay closed."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .commands import CommandError
from .phase16_ledger import (
    close_period,
    dry_run_manifest,
    issue_statement,
    open_account,
    post_charge,
    post_deposit,
    post_settlement,
    post_subsidy,
    reject_live_payment,
    reverse_transaction,
    submit_dispute,
)
from .routes import actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class OpenAccountRequest(BaseModel):
    reference: str
    idempotency_key: str


class ChargeRequest(BaseModel):
    reference: str
    amount_minor: int
    occurrence_code: str
    idempotency_key: str


class AmountRequest(BaseModel):
    reference: str
    amount_minor: int
    idempotency_key: str


class ReversalRequest(BaseModel):
    reference: str
    idempotency_key: str


class ReferenceRequest(BaseModel):
    reference: str


class DisputeRequest(BaseModel):
    reference: str
    reason_code: str


class ManifestRequest(BaseModel):
    display_name: str = "Example Homes"
    extra: dict = Field(default_factory=dict)


def _call(action):
    try:
        return action()
    except CommandError as exc:
        raise HTTPException(
            status_code=exc.status,
            detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable},
        ) from exc


@router.post("/leasing/ledger/accounts")
def staff_open(body: OpenAccountRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: open_account(current, current_actor["id"], current_actor["organization_id"], body.reference, body.idempotency_key))


@router.post("/leasing/ledger/charges")
def staff_charge(body: ChargeRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(
        lambda: post_charge(
            current,
            current_actor["id"],
            current_actor["organization_id"],
            body.reference,
            body.amount_minor,
            body.occurrence_code,
            body.idempotency_key,
        )
    )


@router.post("/leasing/ledger/subsidies")
def staff_subsidy(body: AmountRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: post_subsidy(current, current_actor["id"], current_actor["organization_id"], body.reference, body.amount_minor, body.idempotency_key))


@router.post("/leasing/ledger/deposits")
def staff_deposit(body: AmountRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: post_deposit(current, current_actor["id"], current_actor["organization_id"], body.reference, body.amount_minor, body.idempotency_key))


@router.post("/leasing/ledger/settlements")
def staff_settlement(body: AmountRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: post_settlement(current, current_actor["id"], current_actor["organization_id"], body.reference, body.amount_minor, body.idempotency_key))


@router.post("/leasing/ledger/reversals")
def staff_reversal(body: ReversalRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: reverse_transaction(current, current_actor["id"], current_actor["organization_id"], body.reference, body.idempotency_key))


@router.post("/leasing/ledger/disputes")
def staff_dispute(body: DisputeRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: submit_dispute(current, current_actor["id"], current_actor["organization_id"], body.reference, body.reason_code))


@router.post("/leasing/ledger/statements")
def staff_statement(body: ReferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: issue_statement(current, current_actor["id"], current_actor["organization_id"], body.reference))


@router.post("/leasing/ledger/periods/close")
def staff_close(body: ReferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: close_period(current, current_actor["id"], current_actor["organization_id"], body.reference))


@router.post("/leasing/ledger/manifest")
def staff_manifest(body: ManifestRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: dry_run_manifest(current, current_actor["id"], current_actor["organization_id"], {"display_name": body.display_name, **body.extra}))


@router.post("/leasing/ledger/payments")
def reject_payment(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: reject_live_payment(current, current_actor["id"], current_actor["organization_id"]))


@router.post("/leasing/ledger/balances")
def reject_balance(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: reject_live_payment(current, current_actor["id"], current_actor["organization_id"]))
