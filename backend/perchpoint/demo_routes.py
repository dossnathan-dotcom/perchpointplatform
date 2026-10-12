"""HTTP surface for the local demo. Closed unless demo_enabled() is true."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .demo_catalog import demo_listing, search_demo
from .demo_center import (
    PERSONAS,
    account_detail,
    document_view,
    accounts_view,
    demo_enabled,
    enter,
    feature_inventory,
    household_view,
    owner_view,
    review_resident_request,
    submit_resident_request,
    work_view,
)
from .phase6_identity import resolve
from .routes import COOKIE, _require_csrf, _session_cookie
from .settings import Settings

router = APIRouter()


class EnterBody(BaseModel):
    persona: str


class ResidentRequestBody(BaseModel):
    kind: str
    note: str
    idempotency_key: str


def _closed() -> None:
    if not demo_enabled():
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Not found"})


@router.get("/api/v2/demo/status")
def demo_status():
    _closed()
    return {"enabled": True, "synthetic": True, "real_values_activated": False, "money_moved": False}


@router.get("/api/v2/demo/personas")
def demo_personas():
    _closed()
    return {"personas": [dict(row) for row in PERSONAS], "synthetic": True}


@router.get("/api/v2/demo/features")
def demo_features():
    _closed()
    return {"features": feature_inventory(), "synthetic": True}


@router.post("/api/v2/demo/enter")
def demo_enter(body: EnterBody, request: Request):
    _closed()
    try:
        opened = enter(Settings.load(), body.persona, request.cookies.get(COOKIE))
    except KeyError:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "That demo persona is not available"}) from None
    except LookupError:
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "The local synthetic organization is not ready"}) from None
    except PermissionError:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Not found"}) from None
    token = opened.pop("token")
    csrf = opened.pop("csrf")
    response = JSONResponse(opened)
    _session_cookie(response, token, csrf)
    return response


@router.get("/api/v2/demo/owner")
def demo_owner(request: Request):
    _closed()
    try:
        return owner_view(Settings.load(), request.cookies.get(COOKIE))
    except LookupError:
        raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "Enter the owner persona before opening the owner workspace."}) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail={"code": "denied", "message": "This session is not the owner. Return to the demo control center and choose Owner."}) from None


@router.get("/api/v2/demo/household")
def demo_household(request: Request):
    _closed()
    try:
        return household_view(Settings.load(), request.cookies.get(COOKIE))
    except LookupError as exc:
        if str(exc) == "signed out":
            raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "Enter a demo persona before opening a household."}) from None
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "No active synthetic household is ready."}) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail={"code": "denied", "message": "This session cannot open that household. Return to the demo control center and choose Resident."}) from None


@router.get("/api/v2/demo/accounts")
def demo_accounts(request: Request):
    _closed()
    try:
        return accounts_view(Settings.load(), request.cookies.get(COOKIE))
    except LookupError:
        raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "Sign in to view resident accounts."}) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail={"code": "denied", "message": "This session cannot view resident accounts."}) from None


@router.get("/api/v2/demo/accounts/{slug}")
def demo_account(slug: str, request: Request):
    _closed()
    try:
        return account_detail(Settings.load(), request.cookies.get(COOKIE), slug)
    except LookupError as exc:
        if str(exc) == "signed out":
            raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "Sign in to view this account."}) from None
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "That account is not in the demonstration cohort."}) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail={"code": "denied", "message": "This session cannot view that account."}) from None


@router.get("/api/v2/demo/documents/{slug}/{kind}")
def demo_document(slug: str, kind: str, request: Request):
    _closed()
    try:
        body = document_view(Settings.load(), request.cookies.get(COOKIE), slug, kind)
    except LookupError as exc:
        if str(exc) == "signed out":
            raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "Sign in to open this document."}) from None
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "That document is not available."}) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail={"code": "denied", "message": "This session cannot open that document."}) from None
    response = HTMLResponse(body)
    response.headers["content-disposition"] = f'inline; filename="{kind}-{slug}.html"'
    return response


def _mutate(request: Request):
    session = resolve(Settings.load(), request.cookies.get(COOKIE))
    if session is None:
        raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "Sign in to continue."})
    _require_csrf(request, session)


@router.post("/api/v2/demo/requests")
def demo_submit_request(body: ResidentRequestBody, request: Request):
    _closed()
    _mutate(request)
    try:
        return submit_resident_request(Settings.load(), request.cookies.get(COOKIE), body.kind, body.note, body.idempotency_key)
    except LookupError:
        raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "Sign in to submit a request."}) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail={"code": "denied", "message": "Only the resident can submit a household request."}) from None
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "rejected", "message": "Describe the requested change in at least 8 characters."}) from None


@router.post("/api/v2/demo/requests/{request_id}/review")
def demo_review_request(request_id: str, request: Request):
    _closed()
    _mutate(request)
    try:
        return review_resident_request(Settings.load(), request.cookies.get(COOKIE), request_id)
    except LookupError:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "That request is not waiting for review."}) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail={"code": "denied", "message": "This session cannot review household requests."}) from None


@router.get("/api/v2/demo/work")
def demo_work(request: Request):
    _closed()
    try:
        return work_view(Settings.load(), request.cookies.get(COOKIE))
    except LookupError:
        raise HTTPException(status_code=401, detail={"code": "unauthenticated", "message": "Sign in to view the work queue."}) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail={"code": "denied", "message": "This session does not have a work queue. An owner, operations manager, or leasing account can open it."}) from None


@router.get("/api/v2/public/demo/listings")
def public_demo_listings(request: Request):
    _closed()
    try:
        return search_demo(dict(request.query_params))
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "rejected", "message": "Those filters are not valid"}) from None


@router.get("/api/v2/public/demo/listings/{slug}")
def public_demo_listing(slug: str):
    _closed()
    row = demo_listing(slug)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "That listing is not in the local catalog"})
    return row
