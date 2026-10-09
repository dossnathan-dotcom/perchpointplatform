"""Staff screening commands and applicant authorization. No live provider is called."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .commands import CommandError
from .phase13_screening import (
    apply_result,
    create_handoff,
    criminal_safeguard,
    grant_authorization,
    open_case,
    open_dispute,
    place_order,
    record_decision,
)
from .routes import actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class OpenCaseRequest(BaseModel):
    application_reference: str
    idempotency_key: str


class CapabilityRequest(BaseModel):
    capability: str


class OrderRequest(BaseModel):
    capability: str
    product: str
    idempotency_key: str


class DecisionRequest(BaseModel):
    reference: str
    outcome: str
    human_confirmed: bool = False


class ReferenceRequest(BaseModel):
    reference: str


class DisputeRequest(BaseModel):
    reference: str
    dispute_kind: str


class SafeguardRequest(BaseModel):
    record_kind: str


def _call(action):
    try:
        return action()
    except CommandError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


@router.post("/leasing/screening/cases")
def staff_open(body: OpenCaseRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: open_case(current, current_actor["id"], current_actor["organization_id"], body.application_reference, body.idempotency_key))


@router.post("/public/screening/authorization")
def public_authorization(body: CapabilityRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: grant_authorization(current, body.capability))


@router.post("/public/screening/orders")
def public_order(body: OrderRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: place_order(current, body.capability, body.product, body.idempotency_key))


@router.post("/public/screening/results")
async def public_result(request: Request, current: Settings = Depends(settings)) -> dict:
    body = await request.body()
    capability = request.headers.get("x-perchpoint-capability", "")
    coverage = request.headers.get("x-perchpoint-coverage", "")
    signature = request.headers.get("x-perchpoint-signature", "")
    return _call(lambda: apply_result(current, capability, body, signature, coverage))


@router.post("/leasing/screening/decisions")
def staff_decision(body: DecisionRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: record_decision(current, current_actor["id"], current_actor["organization_id"], body.reference, body.outcome, body.human_confirmed))


@router.post("/leasing/screening/disputes")
def staff_dispute(body: DisputeRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: open_dispute(current, current_actor["id"], current_actor["organization_id"], body.reference, body.dispute_kind))


@router.post("/leasing/screening/handoff")
def staff_handoff(body: ReferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: create_handoff(current, current_actor["id"], current_actor["organization_id"], body.reference))


@router.post("/leasing/screening/criminal-safeguard")
def staff_safeguard(body: SafeguardRequest, current_actor=Depends(actor)) -> dict:
    del current_actor
    result = criminal_safeguard(body.record_kind)
    if not result["accepted"] and result.get("code") == "disabled" and body.record_kind != "test_only_individualized":
        raise HTTPException(status_code=400, detail={"code": "rejected", "message": "The screening request could not be accepted.", "retryable": False})
    return result
