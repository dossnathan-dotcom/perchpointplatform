"""Public application collection and staff review commands."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .commands import CommandError
from .phase12_applications import (
    add_minor,
    finalize_document,
    handoff,
    invite,
    place_hold,
    request_item,
    save_answer,
    start,
    submit,
    withdraw,
)
from .routes import actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class StartRequest(BaseModel):
    receipt: str
    disclosure: bool = False
    application_type: str = "residential"
    preferred_name: str = ""
    legal_name: str = ""
    email: str = ""
    showing_reference: str = ""
    idempotency_key: str
    ssn: str = ""
    credit_score: str = ""
    criminal_history: str = ""


class AnswerRequest(BaseModel):
    capability: str
    field_code: str
    field_value: str
    expected_version: int


class DocumentRequest(BaseModel):
    capability: str
    document_class: str
    display_name: str
    content: str
    magic: str


class SubmitRequest(BaseModel):
    capability: str
    idempotency_key: str
    expected_version: int
    attestation: bool = False


class CapabilityRequest(BaseModel):
    capability: str


class InviteRequest(BaseModel):
    capability: str
    role_name: str
    destination_email: str


class ReferenceRequest(BaseModel):
    reference: str
    field_code: str = ""
    preferred_name: str = ""
    reason: str = ""


def _call(action):
    try:
        return action()
    except CommandError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


@router.post("/public/applications")
def public_start(body: StartRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: start(current, body.model_dump(), body.idempotency_key))


@router.post("/public/applications/answers")
def public_answer(body: AnswerRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: save_answer(current, body.capability, body.field_code, body.field_value, body.expected_version))


@router.post("/public/applications/documents")
def public_document(body: DocumentRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: finalize_document(current, body.capability, body.document_class, body.display_name, body.content, body.magic))


@router.post("/public/applications/submit")
def public_submit(body: SubmitRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: submit(current, body.capability, body.idempotency_key, body.expected_version, body.attestation))


@router.post("/public/applications/withdraw")
def public_withdraw(body: CapabilityRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: withdraw(current, body.capability))


@router.post("/public/applications/invitations")
def public_invite(body: InviteRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: invite(current, body.capability, body.role_name, body.destination_email))


@router.post("/leasing/applications/minors")
def staff_minor(body: ReferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: add_minor(current, current_actor["id"], current_actor["organization_id"], body.reference, body.preferred_name))


@router.post("/leasing/applications/requests")
def staff_request(body: ReferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: request_item(current, current_actor["id"], current_actor["organization_id"], body.reference, body.field_code))


@router.post("/leasing/applications/handoff")
def staff_handoff(body: ReferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: handoff(current, current_actor["id"], current_actor["organization_id"], body.reference))


@router.post("/leasing/applications/holds")
def staff_hold(body: ReferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: place_hold(current, current_actor["id"], current_actor["organization_id"], body.reference, body.reason or "preservation"))
