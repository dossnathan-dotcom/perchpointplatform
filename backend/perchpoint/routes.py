"""Phase 2 HTTP routes. Client role headers are ignored."""
from __future__ import annotations

import os
from uuid import UUID, uuid4

import bcrypt
import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

from .commands import (
    CommandError,
    accept_inbox,
    claim_and_deliver,
    add_inquiry_note,
    create_building,
    create_listing,
    set_listing_publication,
    create_property,
    create_space,
    set_space_dimension,
    submit_public_inquiry,
    triage_inquiry,
    update_property,
)
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


class BuildingBody(BaseModel):
    property_id: UUID
    name: str = Field(min_length=1, max_length=80)
    allowed_uses: list[str] = Field(min_length=1)
    idempotency_key: str = Field(min_length=8, max_length=128)


class SpaceBody(BaseModel):
    property_id: UUID
    building_id: UUID
    label: str = Field(min_length=1, max_length=80)
    use: str
    square_feet: int = Field(gt=0)
    idempotency_key: str = Field(min_length=8, max_length=128)


class PropertyEdit(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    expected_version: int
    idempotency_key: str = Field(min_length=8, max_length=128)


class ListingBody(BaseModel):
    space_id: UUID
    property_name: str
    label: str
    use: str
    municipality: str
    state: str = Field(min_length=2, max_length=2)
    amount_minor: int = Field(ge=0)
    currency: str = "USD"
    idempotency_key: str = Field(min_length=8, max_length=128)


class PublicationBody(BaseModel):
    publication: str
    expected_version: int
    idempotency_key: str = Field(min_length=8, max_length=128)


class NoteBody(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class SpaceTransition(BaseModel):
    dimension: str
    value: str
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


def _public_listing(row: dict) -> dict:
    return {
        "listing_id": row["listing_id"],
        "property_name": row["property_name"],
        "label": row["label"],
        "use": row["use"],
        "municipality": row["municipality"],
        "state": row["state"],
        "publication": row["publication"],
        "availability": row["availability"],
        "amount_minor": row["amount_minor"],
        "currency": row["currency"],
        "synthetic": True,
    }


@router.get("/listings")
def listings(settings: Settings = Depends(settings)):
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        rows = connection.execute(text("SELECT * FROM perchpoint.published_listings()")).mappings().all()
    return {"listings": [_public_listing(dict(row)) for row in rows], "synthetic": True}


@router.get("/listings/{listing_id}")
def listing_detail(listing_id: UUID, settings: Settings = Depends(settings)):
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        rows = connection.execute(text("SELECT * FROM perchpoint.published_listings()")).mappings().all()
    match = next((dict(row) for row in rows if row["listing_id"] == listing_id), None)
    if not match:
        raise HTTPException(404, "That listing is not public")
    return _public_listing(match)


@router.post("/properties", status_code=201)
def post_property(body: PropertyBody, current=Depends(actor), settings: Settings = Depends(settings)):
    return _run(lambda: create_property(settings, current["id"], current["organization_id"], body.model_dump(), body.idempotency_key, uuid4()))


@router.post("/inquiries", status_code=201)
def post_inquiry(body: InquiryBody, settings: Settings = Depends(settings)):
    return _run(lambda: submit_public_inquiry(settings, body.model_dump(mode="json"), uuid4()))


@router.post("/listings", status_code=201)
def post_listing(body: ListingBody, current=Depends(actor), settings: Settings = Depends(settings)):
    return _run(lambda: create_listing(settings, current["id"], current["organization_id"], body.model_dump(mode="json"), body.idempotency_key, uuid4()))


@router.post("/listings/{listing_id}/publication")
def post_publication(listing_id: UUID, body: PublicationBody, current=Depends(actor), settings: Settings = Depends(settings)):
    return _run(lambda: set_listing_publication(settings, current["id"], current["organization_id"], listing_id, body.model_dump(), body.idempotency_key, uuid4()))


@router.get("/inquiries/{inquiry_id}")
def get_inquiry(inquiry_id: UUID, current=Depends(actor), settings: Settings = Depends(settings)):
    with runtime_transaction(settings, current["id"], current["organization_id"], uuid4()) as connection:
        inquiry = connection.execute(
            text("SELECT id, listing_id, name, email, intent, message, status, assigned_account_id, version FROM inquiries WHERE id = :id"),
            {"id": inquiry_id},
        ).mappings().first()
        if not inquiry:
            raise HTTPException(404, "Inquiry was not found")
        notes = connection.execute(
            text("SELECT id, body, actor_id, created_at FROM inquiry_notes WHERE inquiry_id = :id ORDER BY created_at"),
            {"id": inquiry_id},
        ).mappings().all()
    return {"inquiry": dict(inquiry), "notes": [dict(note) for note in notes]}


@router.get("/inquiries")
def get_inquiries(current=Depends(actor), settings: Settings = Depends(settings)):
    with runtime_transaction(settings, current["id"], current["organization_id"], uuid4()) as connection:
        rows = connection.execute(text("SELECT id, listing_id, name, status, assigned_account_id, version FROM inquiries ORDER BY received_at DESC")).mappings().all()
    return {"inquiries": [dict(row) for row in rows]}


@router.post("/inquiries/{inquiry_id}/notes", status_code=201)
def post_note(inquiry_id: UUID, body: NoteBody, current=Depends(actor), settings: Settings = Depends(settings)):
    return _run(lambda: add_inquiry_note(settings, current["id"], current["organization_id"], inquiry_id, body.model_dump(), body.idempotency_key, uuid4()))


@router.post("/inquiries/{inquiry_id}/triage")
def post_triage(inquiry_id: UUID, body: TriageBody, current=Depends(actor), settings: Settings = Depends(settings)):
    return _run(lambda: triage_inquiry(settings, current["id"], current["organization_id"], inquiry_id, body.model_dump(), body.idempotency_key, uuid4()))


@router.post("/buildings", status_code=201)
def post_building(body: BuildingBody, current=Depends(actor), settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    return _run(lambda: create_building(settings, current["id"], current["organization_id"], payload, body.idempotency_key, uuid4()))


@router.post("/spaces", status_code=201)
def post_space(body: SpaceBody, current=Depends(actor), settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    return _run(lambda: create_space(settings, current["id"], current["organization_id"], payload, body.idempotency_key, uuid4()))


@router.post("/properties/{property_id}")
def edit_property(property_id: UUID, body: PropertyEdit, current=Depends(actor), settings: Settings = Depends(settings)):
    return _run(lambda: update_property(settings, current["id"], current["organization_id"], property_id, body.model_dump(), body.idempotency_key, uuid4()))


@router.post("/spaces/{space_id}/transition")
def transition_space(space_id: UUID, body: SpaceTransition, current=Depends(actor), settings: Settings = Depends(settings)):
    return _run(lambda: set_space_dimension(settings, current["id"], current["organization_id"], space_id, body.model_dump(), body.idempotency_key, uuid4()))


@router.get("/properties")
def get_properties(limit: int = 50, cursor: str | None = None, current=Depends(actor), settings: Settings = Depends(settings)):
    limit = min(max(limit, 1), 100)
    with runtime_transaction(settings, current["id"], current["organization_id"], uuid4()) as connection:
        total = connection.execute(text("SELECT count(*) FROM properties")).scalar()
        rows = connection.execute(
            text("SELECT id, name, property_type, version FROM properties WHERE (:cursor)::uuid IS NULL OR id > (:cursor)::uuid ORDER BY id LIMIT :limit"),
            {"cursor": cursor, "limit": limit},
        ).mappings().all()
    return {"properties": [dict(row) for row in rows], "total_count": total, "limit": limit}


@router.get("/buildings")
def get_buildings(property_id: UUID, current=Depends(actor), settings: Settings = Depends(settings)):
    with runtime_transaction(settings, current["id"], current["organization_id"], uuid4()) as connection:
        rows = connection.execute(text("SELECT id, name, property_id FROM buildings WHERE property_id = :property ORDER BY name"), {"property": property_id}).mappings().all()
    return {"buildings": [dict(row) for row in rows]}


@router.get("/spaces")
def get_spaces(building_id: UUID, current=Depends(actor), settings: Settings = Depends(settings)):
    with runtime_transaction(settings, current["id"], current["organization_id"], uuid4()) as connection:
        rows = connection.execute(
            text(
                """
                SELECT s.id, s.label, s.use, s.square_feet, st.version, st.availability, st.publication
                FROM spaces s JOIN space_states st ON st.space_id = s.id AND st.current
                WHERE s.building_id = :building ORDER BY s.label
                """
            ),
            {"building": building_id},
        ).mappings().all()
    return {"spaces": [dict(row) for row in rows]}


@router.get("/activity")
def activity(resource_id: UUID, current=Depends(actor), settings: Settings = Depends(settings)):
    with runtime_transaction(settings, current["id"], current["organization_id"], uuid4()) as connection:
        rows = connection.execute(
            text("SELECT id, summary, occurred_at, actor_id FROM activity WHERE resource_id = :resource ORDER BY occurred_at"),
            {"resource": resource_id},
        ).mappings().all()
    return {"activity": [dict(row) for row in rows]}


@router.post("/inbox/synthetic")
async def inbox(request: Request, settings: Settings = Depends(settings)):
    raw = await request.body()
    signature = request.headers.get("x-perchpoint-signature", "")
    import json
    from uuid import UUID as UUIDType

    try:
        organization = UUIDType(json.loads(raw)["organization_id"])
    except Exception as exc:
        raise HTTPException(422, "Webhook payload is invalid") from exc
    return _run(lambda: accept_inbox(settings, raw, signature, organization))


@router.post("/worker/once")
def worker_once(current=Depends(actor), settings: Settings = Depends(settings)):
    if current is None:
        raise HTTPException(401, "Authentication required")
    return claim_and_deliver(settings, "api-dev-worker")


@router.get("/health/live")
def health_live():
    return {"status": "live"}


@router.get("/version")
def version():
    from foundation.reference import REFERENCE_VERSION

    return {
        "application": "perchpoint",
        "contract_version": REFERENCE_VERSION,
        "commit": os.environ.get("PHASE3_COMMIT", "unknown"),
        "environment": os.environ.get("PHASE3_ENVIRONMENT", "local"),
    }


@router.get("/health/ready")
def health_ready(settings: Settings = Depends(settings)):
    from sqlalchemy import text

    from .db import engine_for

    try:
        engine = engine_for(settings.runtime_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
    except Exception:
        raise HTTPException(503, {"status": "not_ready"}) from None
    return {"status": "ready"}


def create_app():
    import json
    import logging
    from uuid import uuid4

    from fastapi import FastAPI

    from .telemetry import init_sentry

    init_sentry()
    app = FastAPI(title="PerchPoint Phase 2 reference")
    log = logging.getLogger("perchpoint")

    @app.middleware("http")
    async def correlation(request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        log.info(json.dumps({"event": "request", "request_id": request_id, "method": request.method, "path": request.url.path, "status": response.status_code}))
        return response

    app.include_router(router)
    return app


def _run(operation):
    try:
        return operation()
    except CommandError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc
