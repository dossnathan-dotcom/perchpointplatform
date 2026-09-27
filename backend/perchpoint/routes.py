"""Phase 2 HTTP routes. Client role headers are ignored."""
from __future__ import annotations

import os
from uuid import UUID, uuid4

import bcrypt
import jwt
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from .abuse import assess_inquiry
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
from .http_security import security_headers
from .phase6_identity import (
    COOKIE,
    CSRF_HEADER,
    accept_invitation,
    confirm_totp,
    create_invitation,
    csrf_ok,
    enroll_totp,
    issue_recovery_codes,
    open_session,
    resolve,
    revoke,
)
from .phase6_policy import approval_authority, authorize
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
    company_website: str = ""
    started_at_ms: int | None = None


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
    if os.environ.get("PHASE6_ALLOW_DEV_JWT") != "1":
        raise HTTPException(404, {"code": "development_jwt_retired", "message": "Use the unified sign-in.", "retryable": False})
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
def post_inquiry(body: InquiryBody, request: Request, settings: Settings = Depends(settings)):
    host = request.client.host if request.client else ""
    verdict = assess_inquiry(body.model_dump(mode="json"), host)
    if verdict == "rate_limited":
        raise HTTPException(429, {"code": "rate_limited", "message": "The inquiry was not accepted.", "retryable": True})
    if verdict:
        raise HTTPException(400, {"code": "rejected", "message": "The inquiry was not accepted.", "retryable": False})
    payload = body.model_dump(mode="json")
    payload.pop("company_website", None)
    payload.pop("started_at_ms", None)
    return _run(lambda: submit_public_inquiry(settings, payload, uuid4()))


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


class PartyBody(BaseModel):
    party_kind: str
    display_name: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=8, max_length=128)


class HoldBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=128)


class DisposeBody(BaseModel):
    expected_version: int
    confirmation: str
    confirm_again: str
    idempotency_key: str = Field(min_length=8, max_length=128)


class ImportBody(BaseModel):
    content: str = Field(min_length=1)
    source_format: str = "csv"
    idempotency_key: str = Field(min_length=8, max_length=128)


class ApplyBody(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)


@router.get("/search")
def search(q: str = "", current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5 import search_records

    return search_records(settings, current["id"], current["organization_id"], q)


@router.get("/search/public")
def search_public(q: str = "", settings: Settings = Depends(settings)):
    from .phase5 import public_search

    return public_search(settings, q)


@router.post("/parties", status_code=201)
def post_party(body: PartyBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5 import create_party

    return _run(lambda: create_party(settings, current["id"], current["organization_id"], body.model_dump(), body.idempotency_key, uuid4()))


@router.post("/documents", status_code=201)
async def post_document(
    title: str = Form(),
    document_class: str = Form(),
    classification: str = Form(),
    primary_resource_type: str = Form(),
    primary_resource_id: UUID = Form(),
    idempotency_key: str = Form(min_length=8, max_length=128),
    upload: UploadFile = File(),
    current=Depends(actor),
    settings: Settings = Depends(settings),
):
    from .phase5 import store_document

    data = await upload.read()
    meta = {
        "title": title,
        "document_class": document_class,
        "classification": classification,
        "primary_resource_type": primary_resource_type,
        "primary_resource_id": primary_resource_id,
    }
    return _run(
        lambda: store_document(
            settings,
            current["id"],
            current["organization_id"],
            upload.filename or "upload.bin",
            upload.content_type or "",
            data,
            meta,
            idempotency_key,
            uuid4(),
        )
    )


@router.post("/documents/{document_id}/hold")
def post_hold(document_id: UUID, body: HoldBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5 import place_hold

    return _run(lambda: place_hold(settings, current["id"], current["organization_id"], document_id, body.model_dump(), body.idempotency_key, uuid4()))


@router.post("/documents/{document_id}/disposition")
def post_disposition(document_id: UUID, body: DisposeBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5 import dispose_document

    return _run(lambda: dispose_document(settings, current["id"], current["organization_id"], document_id, body.model_dump(), body.idempotency_key, uuid4()))


@router.get("/imports")
def get_imports(current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import list_imports

    return _run(lambda: list_imports(settings, current["id"], current["organization_id"]))


@router.post("/imports", status_code=201)
def post_import(body: ImportBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5 import stage_import

    return _run(lambda: stage_import(settings, current["id"], current["organization_id"], body.content, body.source_format, body.idempotency_key, uuid4()))


@router.post("/imports/{batch_id}/apply")
def post_apply(batch_id: UUID, body: ApplyBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5 import apply_import

    return _run(lambda: apply_import(settings, current["id"], current["organization_id"], batch_id, body.idempotency_key, uuid4()))


class SaveSearchBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    query: str = Field(min_length=2, max_length=200)
    idempotency_key: str = Field(min_length=8, max_length=128)


class UpdateSearchBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    query: str = Field(min_length=2, max_length=200)
    idempotency_key: str = Field(min_length=8, max_length=128)


class ShareSearchBody(BaseModel):
    visibility: str
    idempotency_key: str = Field(min_length=8, max_length=128)


class ExportBody(BaseModel):
    document_ids: list[UUID]
    idempotency_key: str = Field(min_length=8, max_length=128)


class ResolveBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=128)


@router.get("/documents")
def get_documents(current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import list_documents

    return _run(lambda: list_documents(settings, current["id"], current["organization_id"]))


@router.post("/documents/{document_id}/access")
def post_access(document_id: UUID, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import mint_access

    return _run(lambda: mint_access(settings, current["id"], current["organization_id"], document_id, "download"))


@router.get("/documents/{document_id}/content")
def get_content(
    document_id: UUID,
    range_header: str | None = Header(default=None, alias="range"),
    x_perchpoint_document_token: str | None = Header(default=None),
    current=Depends(actor),
    settings: Settings = Depends(settings),
):
    from fastapi.responses import Response

    from .phase5_closeout import read_granted

    if not x_perchpoint_document_token:
        raise HTTPException(404, {"code": "not_found", "message": "Document was not found", "retryable": False})
    data, media = _run(
        lambda: read_granted(
            settings,
            current["id"],
            current["organization_id"],
            document_id,
            x_perchpoint_document_token,
            range_header,
        )
    )
    return Response(content=data, media_type=media, headers={"Cache-Control": "private, no-store", "Accept-Ranges": "bytes"})


@router.post("/exports", status_code=201)
def post_export(body: ExportBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import create_export

    return _run(lambda: create_export(settings, current["id"], current["organization_id"], body.document_ids, body.idempotency_key, uuid4()))


@router.get("/exports/{export_id}/content")
def get_export_content(export_id: UUID, current=Depends(actor), settings: Settings = Depends(settings)):
    from fastapi.responses import Response

    from .phase5_closeout import read_export

    data, _manifest = _run(lambda: read_export(settings, current["id"], current["organization_id"], export_id))
    return Response(content=data, media_type="application/zip", headers={"Cache-Control": "private, no-store"})


@router.post("/search/saved", status_code=201)
def post_saved(body: SaveSearchBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import save_search

    return _run(lambda: save_search(settings, current["id"], current["organization_id"], body.name, body.query, body.idempotency_key, uuid4()))


@router.get("/search/saved")
def get_saved(current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import list_saved

    return _run(lambda: list_saved(settings, current["id"], current["organization_id"]))


@router.post("/search/saved/{search_id}/share")
def post_share(search_id: UUID, body: ShareSearchBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import share_search

    return _run(lambda: share_search(settings, current["id"], current["organization_id"], search_id, body.visibility, body.idempotency_key, uuid4()))


@router.delete("/search/saved/{search_id}")
def delete_saved_search(search_id: UUID, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import delete_saved

    return _run(lambda: delete_saved(settings, current["id"], current["organization_id"], search_id))


@router.post("/search/saved/{search_id}")
def post_saved_update(search_id: UUID, body: UpdateSearchBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import update_saved

    return _run(lambda: update_saved(settings, current["id"], current["organization_id"], search_id, body.name, body.query, body.idempotency_key, uuid4()))


@router.post("/search/saved/{search_id}/duplicate", status_code=201)
def post_saved_duplicate(search_id: UUID, body: ApplyBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import duplicate_saved

    return _run(lambda: duplicate_saved(settings, current["id"], current["organization_id"], search_id, body.idempotency_key, uuid4()))


@router.post("/imports/{batch_id}/approve")
def post_approve(batch_id: UUID, body: ApplyBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import approve_import

    return _run(lambda: approve_import(settings, current["id"], current["organization_id"], batch_id, body.idempotency_key, uuid4()))


@router.post("/imports/{batch_id}/dry-run")
def post_dry_run(batch_id: UUID, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import dry_run_import

    return _run(lambda: dry_run_import(settings, current["id"], current["organization_id"], batch_id))


@router.post("/imports/{batch_id}/rollback")
def post_rollback(batch_id: UUID, body: ApplyBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import rollback_import

    return _run(lambda: rollback_import(settings, current["id"], current["organization_id"], batch_id, body.idempotency_key, uuid4()))


@router.get("/imports/{batch_id}")
def get_import(batch_id: UUID, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import import_report

    return _run(lambda: import_report(settings, current["id"], current["organization_id"], batch_id))


@router.get("/quality")
def get_quality(current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import list_quality

    return _run(lambda: list_quality(settings, current["id"], current["organization_id"]))


@router.post("/quality/{finding_id}/resolve")
def post_resolve(finding_id: UUID, body: ResolveBody, current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import resolve_quality

    return _run(lambda: resolve_quality(settings, current["id"], current["organization_id"], finding_id, body.reason, body.idempotency_key, uuid4()))


@router.get("/audit/events")
def get_audit(current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import list_audit

    return _run(lambda: list_audit(settings, current["id"], current["organization_id"]))


@router.post("/replay")
def post_replay(current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import replay_projection

    return _run(lambda: replay_projection(settings, current["id"], current["organization_id"]))


@router.get("/phase5/diagnostics")
def get_diagnostics(current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import diagnostics

    return _run(lambda: diagnostics(settings, current["id"], current["organization_id"]))


@router.post("/phase5/jobs/process")
def post_jobs(current=Depends(actor), settings: Settings = Depends(settings)):
    from .phase5_closeout import process_document_jobs

    return process_document_jobs(settings)


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


class InvitationBody(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    role_name: str = Field(min_length=2, max_length=80)
    purpose: str = Field(min_length=3, max_length=500)
    staff: bool = True


class InvitationAccept(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class TotpConfirm(BaseModel):
    factor_id: UUID
    code: str = Field(min_length=6, max_length=6)


class PurchaseBody(BaseModel):
    amount_minor: int = Field(ge=0)
    monthly_rent_minor: int | None = None
    capital: bool = False
    emergency: bool = False


def _session_actor(request: Request, settings: Settings) -> dict:
    session = resolve(settings, request.cookies.get(COOKIE))
    if not session:
        raise HTTPException(401, {"code": "authentication_required", "message": "Sign in to continue.", "retryable": True})
    return session


@router.post("/auth/sign-in")
def sign_in(body: LoginBody, settings: Settings = Depends(settings)):
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = connection.execute(text("SELECT * FROM perchpoint.login_material(:email)"), {"email": body.email}).mappings().first()
    if not row or not bcrypt.checkpw(body.password.encode(), row["password_hash"].encode()):
        raise HTTPException(401, {"code": "authentication_failed", "message": "The email or password is incorrect.", "retryable": True})
    with runtime_transaction(settings, row["id"], None, uuid4()) as connection:
        membership = connection.execute(text("SELECT * FROM perchpoint.current_membership(:account)"), {"account": row["id"]}).mappings().first()
    if not membership:
        raise HTTPException(403, {"code": "membership_expired", "message": "This account has no current membership.", "retryable": False})
    opened = open_session(settings, row["id"], membership["organization_id"], membership["role_name"], f"local:{row['id']}")
    response = JSONResponse(
        {
            "organization_id": str(membership["organization_id"]),
            "role_name": membership["role_name"],
            "csrf": opened["csrf"],
            "assurance": opened["assurance"],
            "synthetic": True,
        }
    )
    response.set_cookie(COOKIE, opened["token"], httponly=True, samesite="lax", secure=os.environ.get("PHASE3_ENVIRONMENT") in {"staging", "production"}, path="/")
    return response


@router.get("/auth/me")
def current_session(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    return {"account_id": str(session["id"]), "organization_id": str(session["organization_id"]), "assurance": session["assurance"], "synthetic": True}


@router.post("/auth/sign-out")
def sign_out(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    if not csrf_ok(session, request.headers.get(CSRF_HEADER)):
        raise HTTPException(403, {"code": "csrf_rejected", "message": "The security token did not match this session.", "retryable": True})
    revoke(settings, session["id"], session["organization_id"], session["session_id"], "sign_out")
    response = JSONResponse({"signed_out": True, "synthetic": True})
    response.delete_cookie(COOKIE, path="/")
    return response


def _require_csrf(request: Request, session: dict) -> None:
    if not csrf_ok(session, request.headers.get(CSRF_HEADER)):
        raise HTTPException(403, {"code": "csrf_rejected", "message": "The security token did not match this session.", "retryable": True})


@router.post("/auth/invitations")
def invite(body: InvitationBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    created = create_invitation(settings, session["id"], session["organization_id"], body.email, body.role_name, body.purpose, staff=body.staff)
    return {**created, "synthetic": True}


@router.post("/auth/invitations/accept")
def accept_invite(body: InvitationAccept, settings: Settings = Depends(settings)):
    if not accept_invitation(settings, body.token):
        raise HTTPException(400, {"code": "invitation_invalid", "message": "This invitation is no longer valid.", "retryable": False})
    return {"accepted": True, "synthetic": True}


@router.post("/auth/mfa/enroll")
def mfa_enroll(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    return {**enroll_totp(settings, session["id"], session["organization_id"]), "synthetic": True}


@router.post("/auth/mfa/confirm")
def mfa_confirm(body: TotpConfirm, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    if not confirm_totp(settings, session["id"], session["organization_id"], body.factor_id, body.code):
        raise HTTPException(401, {"code": "mfa_invalid", "message": "The authentication code is incorrect.", "retryable": True})
    return {"assurance": "aal2", "synthetic": True}


@router.post("/auth/recovery-codes")
def recovery_codes(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    return {"codes": issue_recovery_codes(settings, session["id"], session["organization_id"]), "synthetic": True}


def _role_may_approve(role_name: str, authority: str) -> bool:
    if authority == "routine":
        return role_name in {"leasing", "owner", "maintenance"}
    if authority in {"operations", "operations_emergency"}:
        return role_name in {"leasing", "owner"}
    return role_name == "owner"


@router.post("/access/purchase-authority")
def purchase_authority(body: PurchaseBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        membership = connection.execute(text("SELECT * FROM perchpoint.current_membership(:account)"), {"account": session["id"]}).mappings().first()
    authority = approval_authority(body.amount_minor, body.monthly_rent_minor, capital=body.capital, emergency=body.emergency)
    role_name = membership["role_name"] if membership else ""
    decision = authorize(
        capability="expense.approve",
        role_name=role_name,
        actor_id=str(session["id"]),
        assurance=session["assurance"],
        privileged=authority == "owner",
    )
    return {
        "authority": authority,
        "allowed": decision.allowed and _role_may_approve(role_name, authority),
        "reason": decision.reason,
        "role_name": role_name,
        "policy_version": "phase6-1",
        "synthetic": True,
    }


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
        for name, value in security_headers(response.headers.get("content-type", "application/json"), request.url.path).items():
            response.headers[name] = value
        log.info(json.dumps({"event": "request", "request_id": request_id, "method": request.method, "path": request.url.path, "status": response.status_code}))
        return response

    app.include_router(router)
    return app


def _run(operation):
    try:
        return operation()
    except CommandError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc
