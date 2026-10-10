"""Resident portal commands. Later financial, maintenance, and message writes stay closed."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from .commands import CommandError
from .phase15_portal import (
    accept_invitation,
    download_document,
    dry_run_manifest,
    open_portal,
    publish_config,
    read_home,
    reject_later_domain,
    revoke_membership,
    set_preference,
    submit_request,
)
from .routes import actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class OpenPortalRequest(BaseModel):
    reference: str
    idempotency_key: str


class AcceptInvitationRequest(BaseModel):
    capability: str
    idempotency_key: str


class ReferenceRequest(BaseModel):
    reference: str


class PreferenceRequest(BaseModel):
    reference: str
    channel: str
    quiet_hours: bool = False


class ProfileRequest(BaseModel):
    reference: str
    request_kind: str
    requested_delta: str


class ConfigRequest(BaseModel):
    family_code: str
    clause_code: str
    human_confirmed: bool = False


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


@router.post("/leasing/portal/memberships")
def staff_open(body: OpenPortalRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(
        lambda: open_portal(
            current,
            current_actor["id"],
            current_actor["organization_id"],
            body.reference,
            body.idempotency_key,
        )
    )


@router.post("/public/portal/invitations")
def public_accept(body: AcceptInvitationRequest, current: Settings = Depends(settings)) -> dict:
    return _call(lambda: accept_invitation(current, body.capability, body.idempotency_key))


@router.post("/leasing/portal/home")
def staff_home(body: ReferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: read_home(current, current_actor["id"], current_actor["organization_id"], body.reference))


@router.post("/leasing/portal/documents")
def staff_document(
    body: ReferenceRequest,
    response: Response,
    current: Settings = Depends(settings),
    current_actor=Depends(actor),
) -> dict:
    payload = _call(lambda: download_document(current, current_actor["id"], current_actor["organization_id"], body.reference))
    response.headers["cache-control"] = "no-store"
    return payload


@router.post("/leasing/portal/preferences")
def staff_preference(body: PreferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(
        lambda: set_preference(
            current,
            current_actor["id"],
            current_actor["organization_id"],
            body.reference,
            body.channel,
            body.quiet_hours,
        )
    )


@router.post("/leasing/portal/requests")
def staff_request(body: ProfileRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(
        lambda: submit_request(
            current,
            current_actor["id"],
            current_actor["organization_id"],
            body.reference,
            body.request_kind,
            body.requested_delta,
        )
    )


@router.post("/leasing/portal/revocations")
def staff_revoke(body: ReferenceRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: revoke_membership(current, current_actor["id"], current_actor["organization_id"], body.reference))


@router.post("/leasing/portal/configuration")
def staff_config(body: ConfigRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(
        lambda: publish_config(
            current,
            current_actor["id"],
            current_actor["organization_id"],
            body.family_code,
            body.clause_code,
            body.human_confirmed,
        )
    )


@router.post("/leasing/portal/manifest")
def staff_manifest(body: ManifestRequest, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    payload = {"display_name": body.display_name, **body.extra}
    return _call(lambda: dry_run_manifest(current, current_actor["id"], current_actor["organization_id"], payload))


@router.post("/leasing/portal/payments")
def staff_payment(current_actor=Depends(actor)) -> dict:
    del current_actor
    return _call(reject_later_domain)


@router.post("/leasing/portal/maintenance")
def staff_maintenance(current_actor=Depends(actor)) -> dict:
    del current_actor
    return _call(reject_later_domain)


@router.post("/leasing/portal/messages")
def staff_messages(current_actor=Depends(actor)) -> dict:
    del current_actor
    return _call(reject_later_domain)
