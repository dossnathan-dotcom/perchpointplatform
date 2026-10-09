"""Staff lease commands and a fake signature ceremony. No live provider is called."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .commands import CommandError
from .phase14_lease import (
    activate_resident,
    apply_signature,
    approve_package,
    open_deal,
    place_signature,
    reject_payment,
    satisfy_deposit,
)
from .routes import actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class OpenDealRequest(BaseModel):
    screening_reference: str
    idempotency_key: str


class ApproveRequest(BaseModel):
    reference: str
    human_confirmed: bool = False


class CapabilityRequest(BaseModel):
    capability: str
    idempotency_key: str


class ReferenceRequest(BaseModel):
    reference: str


class ActivateRequest(BaseModel):
    reference: str
    idempotency_key: str


def _call(action):
    try:
        return action()
    except CommandError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


@router.post("/leasing/leases/deals")
def staff_open(body: OpenDealRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: open_deal(current, current_actor["id"], current_actor["organization_id"], body.screening_reference, body.idempotency_key))


@router.post("/leasing/leases/approvals")
def staff_approve(body: ApproveRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: approve_package(current, current_actor["id"], current_actor["organization_id"], body.reference, body.human_confirmed))


@router.post("/public/leases/signatures")
def public_signature(body: CapabilityRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: place_signature(current, body.capability, body.idempotency_key))


@router.post("/public/leases/signatures/events")
async def public_signature_event(request: Request, current: Settings = Depends(settings)) -> dict:
    body = await request.body()
    capability = request.headers.get("x-perchpoint-capability", "")
    signature = request.headers.get("x-perchpoint-signature", "")
    return _call(lambda: apply_signature(current, capability, body, signature))


@router.post("/leasing/leases/deposits")
def staff_deposit(body: ReferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: satisfy_deposit(current, current_actor["id"], current_actor["organization_id"], body.reference))


@router.post("/leasing/leases/activations")
def staff_activate(body: ActivateRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: activate_resident(current, current_actor["id"], current_actor["organization_id"], body.reference, body.idempotency_key))


@router.post("/leasing/leases/payments")
def staff_payment(current_actor=Depends(actor)) -> dict:
    del current_actor
    return _call(reject_payment)
