"""Public showing booking and staff calendar commands."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from .commands import CommandError
from .phase11_scheduling import (
    apply_callback,
    book,
    cancel,
    complete,
    create_resource,
    finish_connection,
    issue_capability,
    refresh_connection,
    slots_for,
    start_connection,
)
from .routes import actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class CapabilityRequest(BaseModel):
    receipt: str


class SlotRequest(BaseModel):
    capability: str
    day: str


class BookingRequest(BaseModel):
    capability: str
    wall_start: str
    zone_name: str
    offset_minutes: int
    mode: str = "individual"
    guest_count: int = 1
    host_resource_id: str = ""
    space_resource_id: str = ""
    idempotency_key: str


class ResourceRequest(BaseModel):
    kind: str
    label: str
    capacity: int = 1
    parent_id: str | None = None


class ReferenceRequest(BaseModel):
    reference: str


class ConnectFinish(BaseModel):
    connection_id: str
    code: str
    state: str
    verifier: str
    challenge: str


class RefreshRequest(BaseModel):
    connection_id: str
    token_version: int


def _call(action):
    try:
        return action()
    except CommandError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


@router.post("/public/showings/capabilities")
def public_capability(body: CapabilityRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: issue_capability(current, body.receipt))


@router.post("/public/showings/slots")
def public_slots(body: SlotRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: slots_for(current, body.capability, body.day))


@router.post("/public/showings")
def public_book(body: BookingRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: book(current, body.model_dump(), body.idempotency_key))


@router.post("/public/calendar/callbacks")
async def public_callback(request: Request, current: Settings = Depends(settings), x_perchpoint_signature: str = Header(default="")) -> dict:
    payload = await request.body()
    return _call(lambda: apply_callback(current, payload, x_perchpoint_signature))


@router.post("/leasing/showing-resources")
def staff_resource(body: ResourceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: create_resource(current, current_actor["id"], current_actor["organization_id"], body.kind, body.label, body.capacity, body.parent_id))


@router.post("/leasing/showings/cancel")
def staff_cancel(body: ReferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: cancel(current, current_actor["id"], current_actor["organization_id"], body.reference))


@router.post("/leasing/showings/complete")
def staff_complete(body: ReferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: complete(current, current_actor["id"], current_actor["organization_id"], body.reference))


@router.post("/leasing/calendar/start")
def staff_start(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: start_connection(current, current_actor["id"], current_actor["organization_id"]))


@router.post("/leasing/calendar/finish")
def staff_finish(body: ConnectFinish, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: finish_connection(current, current_actor["id"], current_actor["organization_id"], body.connection_id, body.code, body.state, body.verifier, body.challenge))


@router.post("/leasing/calendar/refresh")
def staff_refresh(body: RefreshRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: refresh_connection(current, current_actor["id"], current_actor["organization_id"], body.connection_id, body.token_version))
