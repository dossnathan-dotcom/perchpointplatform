"""Phase 2 HTTP routes. Client role headers are ignored."""
from __future__ import annotations

from uuid import UUID, uuid4

import bcrypt
import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from .commands import CommandError, claim_and_deliver, create_property, submit_public_inquiry, triage_inquiry
from .db import runtime_transaction
from .settings import Phase2ConfigurationError, Settings

router = APIRouter(prefix="/api/v2")


class LoginBody(BaseModel):
    email: str
    password: str


class PropertyBody(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    property_type: str
    idempotency_key: str = Field(min_length=8, max_length=128)


class InquiryBody(BaseModel):
    listing_id: UUID
    name: str
    email: str
    intent: str
    message: str = ""
    idempotency_key: str = Field(min_length=8, max_length=128)


class TriageBody(BaseModel):
    decision: str
    expected_version: int
    idempotency_key: str = Field(min_length=8, max_length=128)


def settings() -> Settings:
    try:
        return Settings.load()
    except Phase2ConfigurationError as exc:
        raise HTTPException(503, str(exc)) from exc


def actor(authorization: str | None = Header(default=None), settings: Settings = Depends(settings)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(authorization.removeprefix("Bearer "), settings.jwt_secret, algorithms=["HS256"])
        return {"id": UUID(payload["sub"]), "organization_id": UUID(payload["org"])}
    except Exception as exc:
        raise HTTPException(401, "Authentication required") from exc


@router.post("/session")
def login(body: LoginBody, settings: Settings = Depends(settings)):
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = connection.execute(text("SELECT * FROM perchpoint.login_material(:email)"), {"email": body.email}).mappings().first()
    if not row or not bcrypt.checkpw(body.password.encode(), row["password_hash"].encode()):
        raise HTTPException(401, "Authentication required")
    with runtime_transaction(settings, row["id"], None, uuid4()) as connection:
        membership = connection.execute(text("SELECT * FROM perchpoint.current_membership(:account)"), {"account": row["id"]}).mappings().first()
    if not membership:
        raise HTTPException(403, "No current organization membership")
    token = jwt.encode({"sub": str(row["id"]), "org": str(membership["organization_id"])}, settings.jwt_secret, algorithm="HS256")
    return {"token": token, "organization_id": str(membership["organization_id"]), "role_name": membership["role_name"], "synthetic": True}


@router.get("/listings")
def listings(settings: Settings = Depends(settings)):
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        rows = connection.execute(text("SELECT * FROM perchpoint.published_listings()")).mappings().all()
    return {"listings": [dict(row) for row in rows], "synthetic": True}


@router.post("/properties", status_code=201)
def post_property(body: PropertyBody, current=Depends(actor), settings: Settings = Depends(settings)):
    return _run(lambda: create_property(settings, current["id"], current["organization_id"], body.model_dump(), body.idempotency_key, uuid4()))


@router.post("/inquiries", status_code=201)
def post_inquiry(body: InquiryBody, settings: Settings = Depends(settings)):
    return _run(lambda: submit_public_inquiry(settings, body.model_dump(mode="json"), uuid4()))


@router.post("/inquiries/{inquiry_id}/triage")
def post_triage(inquiry_id: UUID, body: TriageBody, current=Depends(actor), settings: Settings = Depends(settings)):
    return _run(lambda: triage_inquiry(settings, current["id"], current["organization_id"], inquiry_id, body.model_dump(), body.idempotency_key, uuid4()))


@router.get("/properties")
def get_properties(current=Depends(actor), settings: Settings = Depends(settings)):
    with runtime_transaction(settings, current["id"], current["organization_id"], uuid4()) as connection:
        rows = connection.execute(text("SELECT id, name, property_type, version FROM properties ORDER BY name")).mappings().all()
    return {"properties": [dict(row) for row in rows]}


@router.post("/worker/once")
def worker_once(current=Depends(actor), settings: Settings = Depends(settings)):
    if current is None:
        raise HTTPException(401, "Authentication required")
    return claim_and_deliver(settings, "api-dev-worker")


def create_app():
    from fastapi import FastAPI

    app = FastAPI(title="PerchPoint Phase 2 reference")
    app.include_router(router)
    return app


def _run(operation):
    try:
        return operation()
    except CommandError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc
