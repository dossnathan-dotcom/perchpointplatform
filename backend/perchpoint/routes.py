"""Phase 2 HTTP routes. Client role headers are ignored."""
from __future__ import annotations

import json
import os
from contextvars import ContextVar
from datetime import UTC, datetime
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
from .db import AuthorityContext, reset_authority_context, runtime_transaction, set_authority_context
from .http_security import security_headers
from .phase6_identity import (
    COOKIE,
    CSRF_HEADER,
    activate_invitation,
    authenticate_service_credential,
    approve_privileged_recovery,
    begin_email_change,
    cancel_email_change,
    create_access_request,
    create_delegation,
    create_invitation,
    complete_privileged_recovery,
    consume_recovery_code_id,
    csrf_ok,
    decide_access_request,
    expire_delegation,
    expire_invitation,
    issue_recovery_codes,
    issue_service_credential,
    list_factors,
    list_sessions,
    mark_factor_confirmed,
    mark_factor_removed,
    matching_recovery_code,
    open_privileged_recovery,
    open_session,
    record_provider_refresh_reuse,
    refresh_token_for,
    replace_provider_refresh,
    remember_factor,
    resend_invitation,
    resolve,
    revoke,
    revoke_delegation,
    revoke_invitation,
    revoke_others,
    revoke_session,
    select_context,
    send_local_notice,
)
from .phase6_policy import (
    BUNDLES,
    OWNER_RESERVED,
    approval_authority,
    invitation_role_allowed,
    password_problem,
    recovery_participants,
)
from .phase6_provider import (
    ProviderError,
    admin_remove_factor,
    complete_recovery,
    confirm_factor,
    create_user,
    delete_user,
    enroll_factor,
    list_user_factors,
    password_grant,
    refresh_grant,
    remove_factor,
    request_email_change as provider_request_email_change,
    request_recovery,
)
from .settings import Phase2ConfigurationError, Settings

router = APIRouter(prefix="/api/v2")
_request_context: ContextVar[UUID | None] = ContextVar("perchpoint_request_id", default=None)


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


def _route_capability(request: Request) -> str:
    path = request.url.path.removeprefix("/api/v2")
    if path.startswith("/worker"):
        return "outbox.deliver"
    if path == "/phase5/jobs/process":
        return "document.process"
    if path.startswith("/search"):
        return "search.read"
    if path.startswith("/exports"):
        return "export.create"
    if path.startswith("/documents"):
        return "document.read" if request.method == "GET" else "document.manage"
    if path.startswith("/inquiries"):
        return "inquiry.manage"
    if path.startswith(("/properties", "/buildings", "/spaces", "/activity")):
        return "property.read" if request.method == "GET" else "property.manage"
    if path.startswith(("/imports", "/quality", "/audit", "/replay", "/phase5", "/worker")):
        return "audit.read"
    if path.startswith("/parties"):
        return "resident.read" if request.method == "GET" else "party.create"
    if path.startswith("/listings"):
        return "property.manage"
    raise HTTPException(403, {"code": "route_unclassified", "message": "This protected route has no authority mapping.", "retryable": False})


def actor(request: Request, authorization: str | None = Header(default=None), settings: Settings = Depends(settings)) -> dict:
    session = resolve(settings, request.cookies.get(COOKIE))
    if session and session.get("status") == "active":
        session = _session_actor(request, settings)
        _authorize_session(settings, session, _route_capability(request))
        return {
            "id": session["id"],
            "organization_id": session["organization_id"],
            "principal_type": "interactive",
        }
    if authorization and authorization.startswith("Service "):
        worker_name = request.headers.get("x-perchpoint-worker", "")
        service = authenticate_service_credential(
            settings,
            authorization.removeprefix("Service "),
            audience=request.headers.get("x-perchpoint-audience", "perchpoint-worker"),
            worker_name=worker_name,
        )
        if service is None:
            raise HTTPException(401, "Authentication required")
        set_authority_context(
            AuthorityContext(
                actor_id=service["id"],
                identity_id=None,
                organization_id=service["organization_id"],
                membership_id=None,
                assurance="aal2",
            )
        )
        with runtime_transaction(
            settings, service["id"], service["organization_id"], uuid4(), assurance="aal2"
        ) as connection:
            allowed = connection.execute(
                text("SELECT perchpoint.has_capability(:capability)"),
                {"capability": _route_capability(request)},
            ).scalar()
        if not allowed:
            raise HTTPException(403, {"code": "denied", "message": "This credential is not authorized.", "retryable": False})
        return {
            "id": service["id"],
            "organization_id": service["organization_id"],
            "principal_type": "service",
        }
    if os.environ.get("PHASE6_ALLOW_DEV_JWT") == "1" and authorization and authorization.startswith("Bearer "):
        try:
            payload = jwt.decode(authorization.removeprefix("Bearer "), settings.jwt_secret, algorithms=["HS256"])
            account_id = UUID(payload["sub"])
            organization_id = UUID(payload["org"])
            with runtime_transaction(
                settings, account_id, organization_id, uuid4(), assurance="aal1"
            ) as connection:
                resolved = connection.execute(
                    text(
                        """
                        SELECT NULLIF(current_setting('app.identity_id', true), '')::uuid,
                               NULLIF(current_setting('app.membership_id', true), '')::uuid
                        """
                    )
                ).one()
            set_authority_context(
                AuthorityContext(
                    actor_id=account_id,
                    identity_id=resolved[0],
                    organization_id=organization_id,
                    membership_id=resolved[1],
                    assurance="aal1",
                )
            )
            return {
                "id": account_id,
                "organization_id": organization_id,
                "principal_type": "development_jwt",
            }
        except Exception as exc:
            raise HTTPException(401, "Authentication required") from exc
    raise HTTPException(401, "Authentication required")


@router.post("/session")
def login(body: LoginBody, settings: Settings = Depends(settings)):
    if os.environ.get("PHASE6_ALLOW_DEV_JWT") != "1":
        raise HTTPException(404, {"code": "development_jwt_retired", "message": "Use the unified sign-in.", "retryable": False})
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = connection.execute(text("SELECT * FROM perchpoint.login_material(:email)"), {"email": body.email}).mappings().first()
    if not row or not bcrypt.checkpw(body.password.encode(), row["password_hash"].encode()):
        raise HTTPException(401, "Authentication required")
    with runtime_transaction(settings, row["id"], None, uuid4()) as connection:
        membership = connection.execute(
            text("SELECT membership_id, organization_id, role_name FROM perchpoint.list_memberships(:account) LIMIT 1"),
            {"account": row["id"]},
        ).mappings().first()
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
def worker_once(
    request: Request,
    current=Depends(actor),
    settings: Settings = Depends(settings),
):
    if current["principal_type"] == "interactive":
        raise HTTPException(
            403,
            {
                "code": "service_principal_required",
                "message": "This operation requires a worker service credential.",
                "retryable": False,
            },
        )
    service_request = current["principal_type"] == "service"
    return claim_and_deliver(
        settings,
        request.headers.get("x-perchpoint-worker", "")
        if service_request
        else os.environ.get("PHASE6_WORKER_NAME", "synthetic-worker"),
        request.headers.get("authorization", "").removeprefix("Service ")
        if service_request
        else os.environ.get(
            "PHASE6_WORKER_CREDENTIAL",
            "local-only-not-production-worker-credential",
        ),
    )


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
def post_jobs(
    request: Request,
    current=Depends(actor),
    settings: Settings = Depends(settings),
):
    from .phase5_closeout import process_document_jobs

    if current["principal_type"] == "interactive":
        raise HTTPException(
            403,
            {
                "code": "service_principal_required",
                "message": "This operation requires a worker service credential.",
                "retryable": False,
            },
        )
    service_request = current["principal_type"] == "service"
    return process_document_jobs(
        settings,
        worker_name=(
            request.headers.get("x-perchpoint-worker", "")
            if service_request
            else None
        ),
        credential=(
            request.headers.get("authorization", "").removeprefix("Service ")
            if service_request
            else None
        ),
    )


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
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=15, max_length=64)


class TotpConfirm(BaseModel):
    factor_id: UUID
    code: str = Field(min_length=6, max_length=6)


class DelegationBody(BaseModel):
    grantee_id: UUID
    capability: str = Field(min_length=3, max_length=80)
    reason: str = Field(min_length=3, max_length=500)
    days: int = Field(ge=1, le=30)
    amount_ceiling_minor: int | None = Field(default=None, ge=0)
    resource_type: str = Field(default="organization", min_length=3, max_length=40)
    resource_id: UUID | None = None
    decision_types: list[str] = Field(default_factory=list)
    approval_id: UUID | None = None


class DelegationUseBody(BaseModel):
    action_type: str = Field(min_length=3, max_length=80)
    idempotency_key: str = Field(min_length=8, max_length=128)
    capability: str = Field(min_length=3, max_length=80)
    resource_type: str = Field(min_length=3, max_length=40)
    resource_id: UUID | None = None
    decision_type: str = Field(min_length=3, max_length=80)
    amount_minor: int | None = Field(default=None, ge=0)
    related_transaction_key: str | None = Field(default=None, min_length=3, max_length=120)


class PurchaseBody(BaseModel):
    property_id: UUID
    amount_minor: int = Field(ge=0)
    capital: bool = False
    emergency: bool = False
    imminent_harm_unavoidable: bool = False
    notification_note: str | None = Field(default=None, min_length=10, max_length=1000)
    decision_type: str = Field(default="routine_purchase", min_length=3, max_length=80)
    related_transaction_key: str = Field(min_length=3, max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=128)


class AccessReviewDecisionBody(BaseModel):
    decision: str = Field(pattern="^(attest|revoke|change)$")
    change: dict[str, str] = Field(default_factory=dict)


class MaintenanceCaseBody(BaseModel):
    assignment_id: UUID | None = None
    reported_problem: str = Field(min_length=3, max_length=2000)


class MaintenanceEventBody(BaseModel):
    event_type: str = Field(
        pattern="^(technician_observation|technician_recommendation|manager_decision|approved_solution|ordered_product|installed_solution|variance_reason)$"
    )
    content: str = Field(min_length=1, max_length=4000)


class VendorWorkerProposalBody(BaseModel):
    vendor_relationship_id: UUID
    email: str = Field(min_length=3, max_length=200)
    role_name: str = Field(pattern="^(vendor_worker|technician|cleaner)$")
    property_id: UUID | None = None
    starts_at: datetime
    ends_at: datetime


class VendorWorkerDecisionBody(BaseModel):
    approve: bool
    purpose: str = Field(min_length=3, max_length=500)


class IdentityLifecycleBody(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


def _session_cookie(response: JSONResponse, token: str, csrf: str) -> None:
    secure = os.environ.get("PHASE3_ENVIRONMENT") in {"staging", "production"}
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="strict",
        secure=secure,
        path="/",
        max_age=30 * 24 * 60 * 60,
    )
    response.set_cookie(
        "pp_csrf",
        csrf,
        httponly=False,
        samesite="strict",
        secure=secure,
        path="/",
        max_age=30 * 24 * 60 * 60,
    )


def _session_actor(request: Request, settings: Settings) -> dict:
    session = resolve(settings, request.cookies.get(COOKIE))
    if not session or session.get("status") != "active":
        raise HTTPException(401, {"code": "authentication_required", "message": "Sign in to continue.", "retryable": True})
    with runtime_transaction(
        settings,
        session["id"],
        session["organization_id"],
        uuid4(),
        membership_id=session.get("context_membership"),
        assurance=session["assurance"],
    ) as connection:
        membership = connection.execute(
            text(
                """
                SELECT membership.id, identity.id AS identity_id, identity.mfa_required
                FROM memberships membership
                JOIN identity_accounts identity
                  ON identity.account_id = membership.account_id
                WHERE membership.account_id = :account
                  AND membership.organization_id = :org
                  AND membership.effective_at <= now()
                  AND (
                    membership.ended_at IS NULL
                    OR membership.ended_at > now()
                  )
                  AND (
                    CAST(:context AS uuid) IS NULL
                    OR membership.id = CAST(:context AS uuid)
                  )
                ORDER BY membership.effective_at DESC
                LIMIT 1
                """
            ),
            {
                "account": session["id"],
                "org": session["organization_id"],
                "context": session.get("context_membership"),
            },
        ).mappings().first()
    if membership is None:
        revoke(settings, session["id"], session["organization_id"], session["session_id"], "membership_expired")
        raise HTTPException(401, {"code": "membership_expired", "message": "Your current access has expired.", "retryable": False})
    session["membership_id"] = membership["id"]
    session["identity_id"] = membership["identity_id"]
    session["mfa_required"] = membership["mfa_required"]
    set_authority_context(
        AuthorityContext(
            actor_id=session["id"],
            identity_id=membership["identity_id"],
            organization_id=session["organization_id"],
            membership_id=membership["id"],
            assurance=session["assurance"],
        )
    )
    return session


def _authorize_session(
    settings: Settings,
    session: dict,
    capability: str,
    *,
    privileged: bool = False,
) -> dict:
    if (
        session.get("mfa_required")
        and session["assurance"] != "aal2"
        and capability not in {"identity.profile.read", "session.read", "session.revoke"}
    ):
        _record_security_event(
            settings, session, capability, "denied", "mfa_enrollment_required", privileged=privileged
        )
        raise HTTPException(
            403,
            {
                "code": "mfa_enrollment_required",
                "message": "Complete multi-factor enrollment before continuing.",
                "retryable": False,
            },
        )
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        membership = connection.execute(
            text(
                """
                SELECT id AS membership_id, organization_id, role_name,
                       (
                         perchpoint.has_capability(:capability)
                         OR (
                           :capability = 'property.read'
                           AND perchpoint.worker_assignment_allows(NULL, NULL)
                         )
                       ) AS allowed
                FROM memberships
                WHERE id = :membership AND account_id = :account
                  AND organization_id = :org
                  AND effective_at <= now() AND (ended_at IS NULL OR ended_at > now())
                """
            ),
            {
                "membership": session["membership_id"],
                "account": session["id"],
                "org": session["organization_id"],
                "capability": capability,
            },
        ).mappings().first()
    if membership is None:
        raise HTTPException(403, {"code": "membership_expired", "message": "Your current access has expired.", "retryable": False})
    reauthenticated_at = session.get("reauthenticated_at")
    reauthenticated_age = None
    if reauthenticated_at is not None:
        from datetime import datetime, timezone

        reauthenticated_age = (datetime.now(timezone.utc) - reauthenticated_at).total_seconds()
    denial = None
    if not membership["allowed"]:
        denial = "denied"
    elif privileged and (
        session["assurance"] != "aal2"
        or reauthenticated_age is None
        or reauthenticated_age > 300
    ):
        denial = "step_up_required"
    _record_security_event(
        settings,
        session,
        capability,
        "denied" if denial else "allowed",
        denial,
        privileged=privileged,
    )
    if denial:
        raise HTTPException(403, {"code": denial, "message": "Your current access does not allow this action.", "retryable": False})
    return dict(membership)


def _record_security_event(
    settings: Settings,
    session: dict,
    capability: str,
    outcome: str,
    reason: str | None,
    *,
    privileged: bool = False,
) -> None:
    request_id = _request_context.get() or uuid4()
    event_id = uuid4()
    with runtime_transaction(settings, session["id"], session["organization_id"], request_id) as connection:
        authority = connection.execute(
            text(
                """
                SELECT membership.role_name,
                       COALESCE((
                         SELECT jsonb_agg(
                           jsonb_build_object(
                             'scope_type', scope.scope_type,
                             'resource_id', scope.resource_id
                           )
                           ORDER BY scope.scope_type, scope.resource_id
                         )
                         FROM membership_scope_assignments assignment
                         JOIN authorization_scopes scope ON scope.id = assignment.scope_id
                         WHERE assignment.membership_id = membership.id
                           AND scope.organization_id = :org
                       ), '[]'::jsonb) AS scopes,
                       grant_record.id AS access_grant_id,
                       grant_record.access_request_id
                FROM memberships membership
                LEFT JOIN LATERAL (
                  SELECT access_grant.id, access_grant.access_request_id
                  FROM access_grants access_grant
                  WHERE access_grant.organization_id = membership.organization_id
                    AND access_grant.membership_id = membership.id
                    AND access_grant.account_id = membership.account_id
                    AND access_grant.capability = :capability
                    AND access_grant.starts_at <= now()
                    AND access_grant.ends_at > now()
                    AND access_grant.revoked_at IS NULL
                  ORDER BY access_grant.ends_at, access_grant.id
                  LIMIT 1
                ) grant_record ON true
                WHERE membership.id = :membership
                  AND membership.organization_id = :org
                  AND membership.account_id = :actor
                """
            ),
            {
                "org": session["organization_id"],
                "membership": session["membership_id"],
                "actor": session["id"],
                "capability": capability,
            },
        ).mappings().first()
        connection.execute(
            text(
                """
                INSERT INTO security_events (
                  id, organization_id, identity_id, action, outcome, correlation_id,
                  request_id, actor_account_id, resource_type, reason_code, details
                ) VALUES (
                  :id, :org, :identity, 'authorization', :outcome, :request,
                  :request, :actor, 'capability', :reason,
                  jsonb_build_object('capability', CAST(:capability AS text),
                                     'membership_id', CAST(:membership AS text),
                                     'role_name', CAST(:role AS text),
                                     'scopes', CAST(:scopes AS jsonb),
                                     'access_grant_id', CAST(:access_grant AS text),
                                     'access_request_id', CAST(:access_request AS text),
                                     'aal', CAST(:aal AS text),
                                     'privileged', CAST(:privileged AS boolean),
                                     'policy_version', 'phase6-2',
                                     'resource_type', 'capability')
                )
                """
            ),
            {
                "id": event_id,
                "org": session["organization_id"],
                "identity": session.get("identity_id"),
                "outcome": outcome,
                "request": request_id,
                "actor": session["id"],
                "reason": reason,
                "capability": capability,
                "membership": str(session["membership_id"]),
                "aal": session["assurance"],
                "role": None if authority is None else authority["role_name"],
                "scopes": json.dumps([] if authority is None else authority["scopes"]),
                "access_grant": None if authority is None else authority["access_grant_id"],
                "access_request": None if authority is None else authority["access_request_id"],
                "privileged": privileged,
            },
        )
        if outcome == "denied" and (
            privileged
            or capability in {"csrf.mutation", "role.manage", "scope.manage", "approval.owner"}
        ):
            connection.execute(
                text(
                    """
                    INSERT INTO outbox (
                      organization_id, id, event_type, aggregate_id, payload, status, available_at
                    ) VALUES (
                      :org, :id, 'security.authorization_denied', :event,
                      jsonb_build_object(
                        'synthetic', true,
                        'security_event_id', CAST(:event AS text),
                        'request_id', CAST(:request AS text),
                        'actor_id', CAST(:actor AS text),
                        'capability', CAST(:capability AS text),
                        'reason', CAST(:reason AS text)
                      ),
                      'pending', now()
                    )
                    """
                ),
                {
                    "org": session["organization_id"],
                    "id": uuid4(),
                    "event": event_id,
                    "request": request_id,
                    "actor": session["id"],
                    "capability": capability,
                    "reason": reason,
                },
            )


def _generic_auth_failure() -> HTTPException:
    return HTTPException(401, {"code": "authentication_failed", "message": "The email or password is incorrect.", "retryable": True})


@router.post("/auth/sign-in")
def sign_in(body: LoginBody, request: Request, settings: Settings = Depends(settings)):
    if password_problem(body.password):
        raise _generic_auth_failure()
    try:
        provider_session = password_grant(body.email, body.password)
    except ProviderError as exc:
        if exc.code == "provider_unavailable":
            raise HTTPException(503, {"code": "provider_unavailable", "message": "Sign-in is temporarily unavailable.", "retryable": True}) from exc
        client_host = request.client.host if request.client else "unknown"
        with runtime_transaction(settings, None, None, uuid4()) as connection:
            account_recent = connection.execute(
                text("SELECT perchpoint.note_auth_attempt(:key)"),
                {"key": "account:" + body.email.lower()},
            ).scalar()
            ip_recent = connection.execute(
                text("SELECT perchpoint.note_auth_attempt(:key)"),
                {"key": "ip:" + client_host},
            ).scalar()
            global_recent = connection.execute(
                text("SELECT perchpoint.note_auth_attempt('global')"),
            ).scalar()
        if (
            (account_recent is not None and int(account_recent) > 8)
            or (ip_recent is not None and int(ip_recent) > 30)
            or (global_recent is not None and int(global_recent) > 200)
        ):
            raise HTTPException(429, {"code": "rate_limited", "message": "Wait a few minutes and try again.", "retryable": True}) from exc
        raise _generic_auth_failure() from exc
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        account_id = connection.execute(
            text("SELECT perchpoint.account_id_for_subject(:subject)"),
            {"subject": provider_session.subject},
        ).scalar()
        if account_id is not None and provider_session.email:
            account_id = connection.execute(
                text("SELECT perchpoint.sync_provider_email(:subject, :email)"),
                {"subject": provider_session.subject, "email": provider_session.email},
            ).scalar()
        if account_id is None:
            account_id = connection.execute(
                text("SELECT perchpoint.account_id_for_email(:email)"),
                {"email": body.email},
            ).scalar()
    if account_id is None:
        raise _generic_auth_failure()
    with runtime_transaction(settings, account_id, None, uuid4()) as connection:
        membership = connection.execute(
            text("SELECT membership_id, organization_id, role_name FROM perchpoint.list_memberships(:account) LIMIT 1"),
            {"account": account_id},
        ).mappings().first()
        identity = connection.execute(
            text("SELECT status, mfa_required FROM identity_accounts WHERE account_id = :account"),
            {"account": account_id},
        ).mappings().first()
    identity_status = identity["status"] if identity else "active"
    if identity_status in {"suspended", "closed"}:
        raise HTTPException(403, {"code": identity_status, "message": "This account is not currently available.", "retryable": False})
    if not membership:
        raise HTTPException(403, {"code": "membership_expired", "message": "This account has no current membership.", "retryable": False})
    opened = open_session(
        settings,
        account_id,
        membership["organization_id"],
        membership["role_name"],
        provider_session.subject,
        provider_session.assurance,
        membership_id=membership["membership_id"],
        refresh_token=provider_session.refresh_token,
        provider_session_id=provider_session.provider_session_id,
    )
    response = JSONResponse(
        {
            "organization_id": str(membership["organization_id"]),
            "role_name": membership["role_name"],
            "csrf": opened["csrf"],
            "assurance": opened["assurance"],
            "mfa_required": bool(
                (identity and identity["mfa_required"])
                or membership["role_name"] not in {
                    "applicant",
                    "resident",
                    "household_adult",
                    "guarantor",
                    "service_principal",
                }
            ),
            "synthetic": True,
        }
    )
    _session_cookie(response, opened["token"], opened["csrf"])
    return response


@router.get("/auth/me")
def current_session(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    membership = _authorize_session(settings, session, "identity.profile.read")
    return {
        "account_id": str(session["id"]),
        "organization_id": str(session["organization_id"]),
        "membership_id": str(session["membership_id"]),
        "role_name": membership["role_name"],
        "assurance": session["assurance"],
        "synthetic": True,
    }


@router.get("/me/contexts")
def membership_contexts(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    with runtime_transaction(settings, session["id"], None, uuid4()) as connection:
        rows = connection.execute(
            text(
                """
                SELECT membership_id, organization_id, role_name
                FROM perchpoint.list_memberships(:account)
                """
            ),
            {"account": session["id"]},
        ).mappings().all()
    return {
        "contexts": [
            {
                "membership_id": str(row["membership_id"]),
                "organization_id": str(row["organization_id"]),
                "role_name": row["role_name"],
            }
            for row in rows
        ],
        "synthetic": True,
    }


@router.post("/auth/sign-out")
def sign_out(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    revoke(settings, session["id"], session["organization_id"], session["session_id"], "sign_out")
    response = JSONResponse({"signed_out": True, "synthetic": True})
    response.delete_cookie(COOKIE, path="/")
    response.delete_cookie("pp_csrf", path="/")
    return response


def _require_csrf(request: Request, session: dict) -> None:
    if not csrf_ok(session, request.headers.get(CSRF_HEADER)):
        raise HTTPException(403, {"code": "csrf_rejected", "message": "The security token did not match this session.", "retryable": True})
    if not _origin_allowed(request):
        raise HTTPException(403, {"code": "origin_rejected", "message": "The request origin was not allowed.", "retryable": False})


def _origin_allowed(request: Request) -> bool:
    allowed = {
        origin.strip().rstrip("/")
        for origin in os.environ.get(
            "PHASE6_ALLOWED_ORIGINS",
            "http://127.0.0.1:3000,http://localhost:3000,http://testserver",
        ).split(",")
        if origin.strip()
    }
    origin = request.headers.get("origin", "").rstrip("/")
    referer = request.headers.get("referer", "")
    referer_origin = ""
    if referer:
        from urllib.parse import urlsplit

        parsed = urlsplit(referer)
        referer_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return (bool(origin) and origin in allowed) or (
        bool(referer_origin) and referer_origin in allowed
    )


@router.post("/auth/invitations")
def invite(body: InvitationBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    membership = _authorize_session(settings, session, "invitation.create")
    if not invitation_role_allowed(membership["role_name"], body.role_name):
        raise HTTPException(
            403,
            {
                "code": "invitation_role_forbidden",
                "message": "This role requires a separate approved access workflow.",
                "retryable": False,
            },
        )
    try:
        created = create_invitation(
            settings,
            session["id"],
            session["organization_id"],
            body.email,
            body.role_name,
            body.purpose,
            staff=body.staff,
        )
    except (RuntimeError, ValueError) as exc:
        code = str(exc)
        status = 503 if code == "invitation_delivery_failed" else 400
        raise HTTPException(status, {"code": code, "message": "The invitation could not be created.", "retryable": status == 503}) from exc
    return {**created, "synthetic": True}


@router.post("/auth/invitations/accept")
def accept_invite(body: InvitationAccept, settings: Settings = Depends(settings)):
    if password_problem(body.password):
        raise HTTPException(400, {"code": "password_rejected", "message": "Choose a different password.", "retryable": True})
    created_provider = False
    try:
        provider_subject = create_user(body.email, body.password)
        created_provider = True
    except ProviderError as exc:
        if exc.code == "authentication_failed":
            try:
                provider_subject = password_grant(body.email, body.password).subject
            except ProviderError as retry_exc:
                raise HTTPException(
                    400,
                    {
                        "code": "invitation_invalid",
                        "message": "This invitation is no longer valid.",
                        "retryable": False,
                    },
                ) from retry_exc
        else:
            raise HTTPException(
                503,
                {
                    "code": "provider_unavailable",
                    "message": "Invitation activation is temporarily unavailable.",
                    "retryable": True,
                },
            ) from exc
    try:
        activated = activate_invitation(settings, body.token, body.email, provider_subject)
    except Exception as exc:
        if created_provider:
            try:
                delete_user(provider_subject)
            except ProviderError:
                pass
        raise HTTPException(400, {"code": "invitation_invalid", "message": "This invitation is no longer valid.", "retryable": False}) from exc
    if activated is None:
        if created_provider:
            try:
                delete_user(provider_subject)
            except ProviderError:
                pass
        raise HTTPException(400, {"code": "invitation_invalid", "message": "This invitation is no longer valid.", "retryable": False})
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        assignment_id = connection.execute(
            text("SELECT perchpoint.activate_vendor_worker(:account, :email)"),
            {"account": activated["account_id"], "email": body.email},
        ).scalar()
    return {
        "accepted": True,
        "account_id": str(activated["account_id"]),
        "role_name": activated["role_name"],
        "mfa_required": activated["mfa_required"],
        "worker_assignment_id": None if assignment_id is None else str(assignment_id),
        "synthetic": True,
    }


@router.post("/auth/mfa/enroll")
def mfa_enroll(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    refresh = refresh_token_for(session)
    if not refresh:
        raise HTTPException(401, {"code": "authentication_required", "message": "Sign in to continue.", "retryable": True})
    try:
        provider_session = refresh_grant(refresh)
        replace_provider_refresh(
            settings,
            session["id"],
            session["organization_id"],
            session["session_id"],
            provider_session.refresh_token,
            provider_session.provider_session_id,
        )
        enrolled = enroll_factor(provider_session.access_token)
    except ProviderError as exc:
        if exc.code == "authentication_failed":
            record_provider_refresh_reuse(settings, session["id"], session["organization_id"], session["session_id"])
            raise HTTPException(401, {"code": "session_revoked", "message": "Sign in again to continue.", "retryable": True}) from exc
        raise HTTPException(503, {"code": "provider_unavailable", "message": "Multi-factor setup is temporarily unavailable.", "retryable": True}) from exc
    remember_factor(settings, session["id"], session["organization_id"], enrolled["factor_id"])
    return {"factor_id": enrolled["factor_id"], "secret": enrolled["secret"], "otpauth": enrolled["otpauth"], "synthetic": True}


@router.post("/auth/mfa/confirm")
def mfa_confirm(body: TotpConfirm, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    refresh = refresh_token_for(session)
    if not refresh:
        raise HTTPException(401, {"code": "authentication_required", "message": "Sign in to continue.", "retryable": True})
    try:
        current = refresh_grant(refresh)
        replace_provider_refresh(
            settings,
            session["id"],
            session["organization_id"],
            session["session_id"],
            current.refresh_token,
            current.provider_session_id,
        )
        confirmed = confirm_factor(current.access_token, str(body.factor_id), body.code)
    except ProviderError as exc:
        if exc.code == "authentication_failed":
            record_provider_refresh_reuse(settings, session["id"], session["organization_id"], session["session_id"])
            raise HTTPException(401, {"code": "session_revoked", "message": "Sign in again to continue.", "retryable": True}) from exc
        raise HTTPException(401, {"code": "mfa_invalid", "message": "The authentication code is incorrect.", "retryable": True}) from exc
    mark_factor_confirmed(settings, session["id"], session["organization_id"], str(body.factor_id))
    revoke(settings, session["id"], session["organization_id"], session["session_id"], "assurance_elevated")
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        membership = connection.execute(text("SELECT * FROM perchpoint.current_membership(:account)"), {"account": session["id"]}).mappings().first()
    opened = open_session(
        settings,
        session["id"],
        membership["organization_id"],
        membership["role_name"],
        confirmed.subject,
        confirmed.assurance,
        membership_id=session["membership_id"],
        refresh_token=confirmed.refresh_token,
        provider_session_id=confirmed.provider_session_id,
    )
    response = JSONResponse({"assurance": opened["assurance"], "csrf": opened["csrf"], "synthetic": True})
    _session_cookie(response, opened["token"], opened["csrf"])
    return response


@router.get("/auth/mfa/factors")
def mfa_factors(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _authorize_session(settings, session, "identity.profile.read")
    return {
        "factors": list_factors(settings, session["id"], session["organization_id"]),
        "synthetic": True,
    }


@router.delete("/auth/mfa/factors/{factor_id}")
def mfa_remove_factor(factor_id: UUID, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "identity.profile.read", privileged=True)
    refresh = refresh_token_for(session)
    if not refresh:
        raise HTTPException(401, {"code": "authentication_required", "message": "Sign in to continue.", "retryable": True})
    try:
        current = refresh_grant(refresh)
        replace_provider_refresh(
            settings,
            session["id"],
            session["organization_id"],
            session["session_id"],
            current.refresh_token,
            current.provider_session_id,
        )
        remove_factor(current.access_token, str(factor_id))
    except ProviderError as exc:
        if exc.code == "authentication_failed":
            record_provider_refresh_reuse(settings, session["id"], session["organization_id"], session["session_id"])
            raise HTTPException(401, {"code": "session_revoked", "message": "Sign in again to continue.", "retryable": True}) from exc
        raise HTTPException(503, {"code": "provider_unavailable", "message": "Factor removal is temporarily unavailable.", "retryable": True}) from exc
    if not mark_factor_removed(settings, session["id"], session["organization_id"], str(factor_id)):
        raise HTTPException(404, {"code": "factor_missing", "message": "This factor was not found.", "retryable": False})
    response = JSONResponse({"removed": True, "signed_in": False, "synthetic": True})
    response.delete_cookie(COOKIE, path="/")
    response.delete_cookie("pp_csrf", path="/")
    return response


class ResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)


class ResetBody(BaseModel):
    token: str = Field(min_length=8, max_length=500)
    password: str = Field(min_length=15, max_length=64)


class RecoveryCodeBody(BaseModel):
    code: str = Field(min_length=8, max_length=128)


class EmailChangeBody(BaseModel):
    email: str = Field(min_length=3, max_length=200)


@router.post("/auth/contact/email-change")
def change_email(body: EmailChangeBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "identity.profile.read", privileged=True)
    refresh = refresh_token_for(session)
    if not refresh:
        raise HTTPException(401, {"code": "authentication_required", "message": "Sign in to continue.", "retryable": True})
    try:
        change = begin_email_change(settings, session["id"], session["organization_id"], body.email)
    except ValueError as exc:
        raise HTTPException(
            409,
            {
                "code": str(exc),
                "message": "An email change is already pending or cooling down.",
                "retryable": False,
            },
        ) from exc
    try:
        current = refresh_grant(refresh)
        replace_provider_refresh(
            settings,
            session["id"],
            session["organization_id"],
            session["session_id"],
            current.refresh_token,
            current.provider_session_id,
        )
        provider_request_email_change(current.access_token, body.email)
        send_local_notice(
            change["previous_email"],
            "PerchPoint email change requested",
            "A change to your synthetic PerchPoint sign-in email was requested. Contact Nathan if this was not you.",
        )
        send_local_notice(
            body.email,
            "PerchPoint email verification requested",
            "A synthetic PerchPoint email change is pending provider verification. Follow the separate local Auth verification message.",
        )
    except (ProviderError, OSError) as exc:
        cancel_email_change(settings, session["id"], session["organization_id"], change["change_id"])
        if isinstance(exc, ProviderError) and exc.code == "authentication_failed":
            record_provider_refresh_reuse(settings, session["id"], session["organization_id"], session["session_id"])
            raise HTTPException(401, {"code": "session_revoked", "message": "Sign in again to continue.", "retryable": True}) from exc
        raise HTTPException(503, {"code": "provider_unavailable", "message": "Email change is temporarily unavailable.", "retryable": True}) from exc
    return {"pending_verification": True, "cooldown_hours": 24, "synthetic": True}


@router.post("/auth/password/reset-request")
def reset_request(body: ResetRequest, settings: Settings = Depends(settings)):
    try:
        request_recovery(body.email)
    except ProviderError as exc:
        if exc.code == "provider_unavailable":
            raise HTTPException(503, {"code": "provider_unavailable", "message": "Password reset is temporarily unavailable.", "retryable": True}) from exc
    return {"accepted": True, "message": "If an account exists, a reset message will be sent.", "synthetic": True}


@router.post("/auth/password/reset")
def reset_password(body: ResetBody, settings: Settings = Depends(settings)):
    if password_problem(body.password):
        raise HTTPException(400, {"code": "password_rejected", "message": "Choose a different password.", "retryable": True})
    try:
        email = complete_recovery(body.token, body.password)
    except ProviderError as exc:
        raise HTTPException(400, {"code": "reset_invalid", "message": "This reset link is no longer valid.", "retryable": False}) from exc
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        account_id = connection.execute(text("SELECT perchpoint.account_id_for_email(:email)"), {"email": email}).scalar()
        if account_id is not None:
            connection.execute(text("SELECT perchpoint.revoke_account_sessions(:account, 'password_reset')"), {"account": account_id})
    return {"reset": True, "signed_in": False, "synthetic": True}


@router.post("/auth/recovery-codes")
def recovery_codes(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "identity.profile.read", privileged=True)
    codes = issue_recovery_codes(settings, session["id"], session["organization_id"])
    revoke_others(settings, session["id"], session["organization_id"], session["session_id"])
    return {"codes": codes, "synthetic": True}


@router.post("/auth/recovery-code")
def recover_with_code(body: RecoveryCodeBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    code_id = matching_recovery_code(settings, session["id"], body.code)
    if code_id is None:
        raise HTTPException(400, {"code": "recovery_code_invalid", "message": "This recovery code is not valid.", "retryable": False})
    refresh = refresh_token_for(session)
    if not refresh:
        raise HTTPException(401, {"code": "authentication_required", "message": "Sign in to continue.", "retryable": True})
    try:
        current = refresh_grant(refresh)
        factors = list_factors(settings, session["id"], session["organization_id"])
        for factor_id in list_user_factors(current.subject):
            admin_remove_factor(current.subject, factor_id)
    except ProviderError as exc:
        raise HTTPException(503, {"code": "provider_unavailable", "message": "Account recovery is temporarily unavailable.", "retryable": True}) from exc
    for factor in factors:
        mark_factor_removed(settings, session["id"], session["organization_id"], str(factor["provider_factor_id"]))
    if not consume_recovery_code_id(settings, session["id"], code_id):
        raise HTTPException(400, {"code": "recovery_code_invalid", "message": "This recovery code is not valid.", "retryable": False})
    response = JSONResponse({"accepted": True, "signed_in": False, "synthetic": True})
    response.delete_cookie(COOKIE, path="/")
    response.delete_cookie("pp_csrf", path="/")
    return response


@router.post("/access/delegations")
def delegate(body: DelegationBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    if body.grantee_id == session["id"]:
        raise HTTPException(409, {"code": "self_delegation", "message": "You cannot delegate authority to yourself.", "retryable": False})
    if body.capability in OWNER_RESERVED:
        raise HTTPException(409, {"code": "owner_reserved", "message": "Owner-reserved authority cannot be delegated.", "retryable": False})
    _authorize_session(settings, session, "delegation.grant", privileged=True)
    try:
        delegation_id = create_delegation(
            settings,
            session["id"],
            session["organization_id"],
            body.grantee_id,
            body.capability,
            body.reason,
            days=body.days,
            amount_ceiling_minor=body.amount_ceiling_minor,
            resource_type=body.resource_type,
            resource_id=body.resource_id,
            decision_types=body.decision_types,
            approval_id=body.approval_id,
        )
    except ValueError as exc:
        raise HTTPException(409, {"code": str(exc), "message": "This delegation is not allowed.", "retryable": False}) from exc
    return {"delegation_id": delegation_id, "synthetic": True}


@router.post("/access/delegations/{delegation_id}/use")
def use_delegation(
    delegation_id: UUID,
    body: DelegationUseBody,
    request: Request,
    settings: Settings = Depends(settings),
):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "identity.profile.read", privileged=True)
    if body.capability in OWNER_RESERVED:
        raise HTTPException(409, {"code": "owner_reserved", "message": "Owner-reserved authority cannot be delegated.", "retryable": False})
    request_id = uuid4()
    with runtime_transaction(settings, session["id"], session["organization_id"], request_id) as connection:
        existing_action = connection.execute(
            text(
                """
                SELECT id, action_type, capability, resource_type, resource_id,
                       amount_minor, decision_type, delegation_id
                FROM authorized_business_actions
                WHERE organization_id = :org AND actor_id = :actor
                  AND idempotency_key = :key
                """
            ),
            {
                "org": session["organization_id"],
                "actor": session["id"],
                "key": body.idempotency_key,
            },
        ).mappings().first()
        if existing_action is not None:
            same = (
                existing_action["action_type"] == body.action_type
                and existing_action["capability"] == body.capability
                and existing_action["resource_type"] == body.resource_type
                and existing_action["resource_id"] == body.resource_id
                and existing_action["amount_minor"] == body.amount_minor
                and existing_action["decision_type"] == body.decision_type
                and existing_action["delegation_id"] == delegation_id
            )
            if not same:
                raise HTTPException(409, {"code": "idempotency_conflict", "message": "This key was used for another business action.", "retryable": False})
            return {
                "authorized": True,
                "business_action_id": str(existing_action["id"]),
                "replayed": True,
                "synthetic": True,
            }
        delegation = connection.execute(
            text(
                """
                SELECT capability, amount_ceiling_minor, resource_type, resource_id,
                       decision_types, policy_version
                FROM delegations
                WHERE organization_id = :org
                  AND id = :id
                  AND grantee_id = :actor
                  AND status = 'active'
                  AND starts_at <= now()
                  AND ends_at > now()
                FOR UPDATE
                """
            ),
            {"org": session["organization_id"], "id": delegation_id, "actor": session["id"]},
        ).mappings().first()
        classification = connection.execute(
            text(
                """
                SELECT financial, capital, owner_reserved, policy_version
                FROM business_action_catalog
                WHERE decision_type = :decision_type
                  AND action_type = :action_type
                  AND resource_type = :resource_type
                """
            ),
            {
                "decision_type": body.decision_type,
                "action_type": body.action_type,
                "resource_type": body.resource_type,
            },
        ).mappings().first()
        reason = None
        if delegation is None:
            reason = "delegation_inactive"
        elif delegation["capability"] != body.capability:
            reason = "delegation_capability"
        elif delegation["resource_type"] != body.resource_type:
            reason = "delegation_scope"
        elif delegation["resource_id"] is not None and delegation["resource_id"] != body.resource_id:
            reason = "delegation_scope"
        elif delegation["decision_types"] and body.decision_type not in delegation["decision_types"]:
            reason = "delegation_decision_type"
        elif (
            delegation["amount_ceiling_minor"] is not None
            and body.amount_minor is not None
            and body.amount_minor > delegation["amount_ceiling_minor"]
        ):
            reason = "delegation_amount"
        aggregation_key = None
        if reason is None and (
            body.capability == "expense.approve"
            or body.action_type == "purchase_authorization"
        ):
            if (
                classification is None
                or not classification["financial"]
                or classification["owner_reserved"]
                or body.resource_type != "property"
                or body.resource_id is None
                or body.amount_minor is None
            ):
                reason = "governed_classification_required"
        if reason is None and classification is not None and classification["financial"]:
            aggregation_key = (
                f"{body.resource_id}:{body.decision_type}:"
                f"{datetime.now(UTC).strftime('%Y-%m')}"
            )
            limits = connection.execute(
                text(
                    """
                    SELECT monthly_budget_minor, monthly_rent_minor
                    FROM perchpoint.property_authority_fact(:property)
                    """
                ),
                {
                    "property": body.resource_id,
                },
            ).mappings().first()
            if limits is None:
                reason = "property_limits_unavailable"
            else:
                prior = int(
                    connection.execute(
                        text(
                            """
                            SELECT COALESCE(sum(amount_minor), 0)
                            FROM authorized_business_actions
                            WHERE organization_id = :org
                              AND resource_type = 'property'
                              AND resource_id = :property
                              AND related_transaction_key = :related
                              AND status IN ('authorized', 'executed')
                              AND created_at >= date_trunc('month', now())
                            """
                        ),
                        {
                            "org": session["organization_id"],
                            "property": body.resource_id,
                            "related": aggregation_key,
                        },
                    ).scalar_one()
                )
                amount_minor = 0 if body.amount_minor is None else body.amount_minor
                cumulative = prior + amount_minor
                required_authority = approval_authority(
                    cumulative,
                    int(limits["monthly_rent_minor"]),
                    capital=bool(classification["capital"]),
                    emergency=body.decision_type in {
                        "emergency_stabilization",
                        "unavoidable_imminent_harm",
                    },
                )
                if cumulative > int(limits["monthly_budget_minor"]):
                    required_authority = "owner"
                if required_authority == "owner":
                    reason = "owner_reserved"
                elif (
                    delegation["amount_ceiling_minor"] is None
                    or cumulative > delegation["amount_ceiling_minor"]
                ):
                    reason = "split_transaction"
        elif reason is None and body.related_transaction_key:
            aggregation_key = body.related_transaction_key
        if (
            reason is None
            and body.amount_minor is not None
            and delegation["amount_ceiling_minor"] is not None
            and body.amount_minor > delegation["amount_ceiling_minor"]
        ):
            reason = "split_transaction"
        if reason is not None:
            raise HTTPException(409, {"code": reason, "message": "This delegation does not authorize the action.", "retryable": False})
        action_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO authorized_business_actions (
                  organization_id, id, actor_id, action_type, capability,
                  resource_type, resource_id, amount_minor, decision_type,
                  related_transaction_key, idempotency_key, request_id, delegation_id
                ) VALUES (
                  :org, :id, :actor, :action_type, :capability,
                  :resource_type, :resource_id, :amount, :decision_type,
                  :related, :key, :request, :delegation
                )
                """
            ),
            {
                "org": session["organization_id"],
                "id": action_id,
                "actor": session["id"],
                "action_type": body.action_type,
                "capability": body.capability,
                "resource_type": body.resource_type,
                "resource_id": body.resource_id,
                "amount": body.amount_minor,
                "decision_type": body.decision_type,
                "related": aggregation_key,
                "key": body.idempotency_key,
                "request": request_id,
                "delegation": delegation_id,
            },
        )
        usage_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO delegation_usage (
                  organization_id, id, delegation_id, actor_id, capability,
                  resource_type, resource_id, decision_type, amount_minor,
                  related_transaction_key, request_id, business_action_id
                ) VALUES (
                  :org, :id, :delegation, :actor, :capability,
                  :resource_type, :resource_id, :decision_type, :amount,
                  :related, :request, :business_action
                )
                """
            ),
            {
                "org": session["organization_id"],
                "id": usage_id,
                "delegation": delegation_id,
                "actor": session["id"],
                "capability": body.capability,
                "resource_type": body.resource_type,
                "resource_id": body.resource_id,
                "decision_type": body.decision_type,
                "amount": body.amount_minor,
                "related": aggregation_key,
                "request": request_id,
                "business_action": action_id,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO delegation_events (
                  organization_id, id, delegation_id, actor_id, action,
                  request_id, details
                ) VALUES (
                  :org, :id, :delegation, :actor, 'used', :request,
                  jsonb_build_object(
                    'usage_id', CAST(:usage AS text),
                    'capability', CAST(:capability AS text),
                    'decision_type', CAST(:decision_type AS text),
                    'policy_version', CAST(:policy_version AS text)
                  )
                )
                """
            ),
            {
                "org": session["organization_id"],
                "id": uuid4(),
                "delegation": delegation_id,
                "actor": session["id"],
                "request": request_id,
                "usage": usage_id,
                "capability": body.capability,
                "decision_type": body.decision_type,
                "policy_version": delegation["policy_version"],
            },
        )
    return {
        "authorized": True,
        "usage_id": str(usage_id),
        "business_action_id": str(action_id),
        "request_id": str(request_id),
        "replayed": False,
        "synthetic": True,
    }


def _role_may_approve(role_name: str, authority: str) -> bool:
    if authority == "routine":
        return role_name in {"leasing", "project_manager", "operations_manager", "owner", "maintenance"}
    if authority in {"operations", "operations_emergency"}:
        return role_name in {"project_manager", "operations_manager", "owner"}
    return role_name == "owner"


@router.post("/access/purchase-authority")
def purchase_authority(body: PurchaseBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    membership = _authorize_session(settings, session, "purchase.authorize")
    request_id = uuid4()
    with runtime_transaction(settings, session["id"], session["organization_id"], request_id) as connection:
        existing = connection.execute(
            text(
                """
                SELECT id, resource_id, amount_minor, decision_type, status, details
                FROM authorized_business_actions
                WHERE organization_id = :org AND actor_id = :actor
                  AND idempotency_key = :key
                """
            ),
            {"org": session["organization_id"], "actor": session["id"], "key": body.idempotency_key},
        ).mappings().first()
        if existing is not None:
            same = (
                existing["resource_id"] == body.property_id
                and existing["amount_minor"] == body.amount_minor
                and existing["decision_type"] == body.decision_type
            )
            if not same:
                raise HTTPException(409, {"code": "idempotency_conflict", "message": "This key was used for another purchase decision.", "retryable": False})
            details = existing["details"] or {}
            return {
                "business_action_id": str(existing["id"]),
                "authority": details.get("authority"),
                "allowed": existing["status"] in {"authorized", "executed"},
                "reason": details.get("reason"),
                "act_and_notify": bool(details.get("act_and_notify", False)),
                "monthly_rent_minor": details.get("monthly_rent_minor"),
                "monthly_budget_minor": details.get("monthly_budget_minor"),
                "replayed": True,
                "synthetic": True,
            }
        classification = connection.execute(
            text(
                """
                SELECT capital, owner_reserved, policy_version
                FROM business_action_catalog
                WHERE decision_type = :decision_type
                  AND action_type = 'purchase_authorization'
                  AND resource_type = 'property'
                  AND financial
                """
            ),
            {"decision_type": body.decision_type},
        ).mappings().first()
        if (
            classification is None
            or bool(classification["capital"]) != body.capital
            or body.emergency
            != (body.decision_type in {"emergency_stabilization", "unavoidable_imminent_harm"})
            or body.imminent_harm_unavoidable
            != (body.decision_type == "unavoidable_imminent_harm")
        ):
            raise HTTPException(
                409,
                {
                    "code": "governed_classification_required",
                    "message": "The purchase classification does not match the governed action catalog.",
                    "retryable": False,
                },
            )
        limits = connection.execute(
            text(
                """
                SELECT monthly_budget_minor, monthly_rent_minor, source_kind, source_reference
                FROM perchpoint.property_authority_fact(:property)
                """
            ),
            {"property": body.property_id},
        ).mappings().first()
        if limits is None:
            raise HTTPException(409, {"code": "property_limits_unavailable", "message": "Current property authority limits are unavailable.", "retryable": False})
        aggregation_key = (
            f"{body.property_id}:{body.decision_type}:"
            f"{datetime.now(UTC).strftime('%Y-%m')}"
        )
        related_total = int(
            connection.execute(
                text(
                    """
                    SELECT COALESCE(sum(amount_minor), 0)
                    FROM authorized_business_actions
                    WHERE organization_id = :org
                      AND resource_type = 'property' AND resource_id = :property
                      AND related_transaction_key = :related
                      AND status = 'authorized'
                      AND created_at >= date_trunc('month', now())
                    """
                ),
                {
                    "org": session["organization_id"],
                    "property": body.property_id,
                    "related": aggregation_key,
                },
            ).scalar_one()
        )
        cumulative = related_total + body.amount_minor
        if body.imminent_harm_unavoidable and (
            not body.emergency
            or not body.notification_note
            or cumulative <= 120_000
        ):
            raise HTTPException(
                400,
                {
                    "code": "act_and_notify_invalid",
                    "message": "Act-and-notify is only for documented unavoidable imminent harm above the emergency ceiling.",
                    "retryable": False,
                },
            )
        authority = approval_authority(
            cumulative,
            int(limits["monthly_rent_minor"]),
            capital=bool(classification["capital"]),
            emergency=body.emergency,
        )
        if cumulative > int(limits["monthly_budget_minor"]):
            authority = "owner"
        allowed = _role_may_approve(str(membership["role_name"]), authority)
        act_and_notify = bool(
            body.imminent_harm_unavoidable
            and body.emergency
            and cumulative > 120_000
            and membership["role_name"] in {"project_manager", "operations_manager"}
        )
        if act_and_notify:
            allowed = True
        if allowed and authority == "owner":
            if not act_and_notify:
                _authorize_session(settings, session, "approval.owner", privileged=True)
        reason = "act_and_notify_escalation" if act_and_notify else ("allowed" if allowed else f"{authority}_authority_required")
        action_id = uuid4()
        escalation_outbox_id = uuid4() if act_and_notify else None
        connection.execute(
            text(
                """
                INSERT INTO authorized_business_actions (
                  organization_id, id, actor_id, action_type, capability,
                  resource_type, resource_id, amount_minor, decision_type,
                  related_transaction_key, idempotency_key, request_id, status, details
                ) VALUES (
                  :org, :id, :actor, 'purchase_authorization', 'purchase.authorize',
                  'property', :property, :amount, :decision_type,
                  :related, :key, :request, :status,
                  jsonb_build_object(
                    'authority', CAST(:authority AS text),
                    'reason', CAST(:reason AS text),
                    'monthly_rent_minor', CAST(:rent AS integer),
                    'monthly_budget_minor', CAST(:budget AS integer),
                    'related_total_minor', CAST(:related_total AS integer),
                    'capital', CAST(:capital AS boolean),
                    'emergency', CAST(:emergency AS boolean),
                    'act_and_notify', CAST(:act_and_notify AS boolean),
                    'notification_note', CAST(:notification_note AS text),
                    'authority_source_kind', CAST(:source_kind AS text),
                    'authority_source_reference', CAST(:source_reference AS text),
                    'escalation_outbox_id', CAST(:escalation_outbox_id AS text),
                    'policy_version', 'phase6-2'
                  )
                )
                """
            ),
            {
                "org": session["organization_id"],
                "id": action_id,
                "actor": session["id"],
                "property": body.property_id,
                "amount": body.amount_minor,
                "decision_type": body.decision_type,
                "related": aggregation_key,
                "key": body.idempotency_key,
                "request": request_id,
                "status": "executed" if act_and_notify else ("authorized" if allowed else "denied"),
                "authority": authority,
                "reason": reason,
                "rent": int(limits["monthly_rent_minor"]),
                "budget": int(limits["monthly_budget_minor"]),
                "related_total": related_total,
                "capital": bool(classification["capital"]),
                "emergency": body.emergency,
                "act_and_notify": act_and_notify,
                "notification_note": body.notification_note,
                "source_kind": limits["source_kind"],
                "source_reference": limits["source_reference"],
                "escalation_outbox_id": None if escalation_outbox_id is None else str(escalation_outbox_id),
            },
        )
        if escalation_outbox_id is not None:
            connection.execute(
                text(
                    """
                    INSERT INTO outbox (
                      organization_id, id, event_type, aggregate_id, payload, status, available_at
                    ) VALUES (
                      :org, :id, 'owner.emergency_escalation', :action,
                      jsonb_build_object(
                        'synthetic', true,
                        'business_action_id', CAST(:action AS text),
                        'property_id', CAST(:property AS text),
                        'actor_id', CAST(:actor AS text),
                        'amount_minor', CAST(:amount AS integer),
                        'cumulative_minor', CAST(:cumulative AS integer),
                        'notification_note', CAST(:note AS text),
                        'owner_approval_claimed', false
                      ),
                      'pending', now()
                    )
                    """
                ),
                {
                    "org": session["organization_id"],
                    "id": escalation_outbox_id,
                    "action": action_id,
                    "property": body.property_id,
                    "actor": session["id"],
                    "amount": body.amount_minor,
                    "cumulative": cumulative,
                    "note": body.notification_note,
                },
            )
    return {
        "business_action_id": str(action_id),
        "authority": authority,
        "allowed": allowed,
        "reason": reason,
        "act_and_notify": act_and_notify,
        "escalation_outbox_id": None if escalation_outbox_id is None else str(escalation_outbox_id),
        "policy_version": "phase6-2",
        "monthly_rent_minor": int(limits["monthly_rent_minor"]),
        "monthly_budget_minor": int(limits["monthly_budget_minor"]),
        "replayed": False,
        "synthetic": True,
    }


class AccessRequestBody(BaseModel):
    capability: str = Field(min_length=3, max_length=80)
    purpose: str = Field(min_length=3, max_length=200)
    scope_type: str = Field(min_length=2, max_length=80)
    scope_resource_id: UUID | None = None
    duration_hours: int = Field(ge=1, le=720)
    justification: str = Field(min_length=3, max_length=500)


class AccessDecisionBody(BaseModel):
    approve: bool


class RoleAssignmentBody(BaseModel):
    role_name: str = Field(min_length=2, max_length=80)
    approval_id: UUID | None = None


class ScopeAssignmentBody(BaseModel):
    scope_type: str = Field(min_length=2, max_length=80)
    resource_id: UUID | None = None
    approval_id: UUID


class AuthorityApprovalBody(BaseModel):
    action: str = Field(pattern="^(role|scope)$")
    role_name: str | None = Field(default=None, min_length=2, max_length=80)
    scope_type: str | None = Field(default=None, min_length=2, max_length=80)
    resource_id: UUID | None = None
    reason: str = Field(min_length=3, max_length=500)


class ContextBody(BaseModel):
    membership_id: UUID


class RecoveryOpenBody(BaseModel):
    subject_account: UUID
    evidence: str = Field(min_length=3, max_length=500)
    approver_account: UUID | None = None


def _change_identity_lifecycle(
    account_id: UUID,
    action: str,
    body: IdentityLifecycleBody,
    request: Request,
    settings: Settings,
):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    if account_id == session["id"]:
        raise HTTPException(409, {"code": "self_lifecycle_change", "message": "You cannot change your own account lifecycle.", "retryable": False})
    _authorize_session(settings, session, "role.manage", privileged=True)
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        result = connection.execute(
            text(
                """
                SELECT perchpoint.set_identity_lifecycle(
                  :actor, :target, :org, :action, :reason
                )
                """
            ),
            {
                "actor": session["id"],
                "target": account_id,
                "org": session["organization_id"],
                "action": action,
                "reason": body.reason,
            },
        ).scalar_one()
    return {**result, "synthetic": True}


@router.post("/access/users/{account_id}/suspend")
def suspend_identity(
    account_id: UUID,
    body: IdentityLifecycleBody,
    request: Request,
    settings: Settings = Depends(settings),
):
    return _change_identity_lifecycle(account_id, "suspended", body, request, settings)


@router.post("/access/users/{account_id}/restore")
def restore_identity(
    account_id: UUID,
    body: IdentityLifecycleBody,
    request: Request,
    settings: Settings = Depends(settings),
):
    return _change_identity_lifecycle(account_id, "restored", body, request, settings)


@router.get("/me/sessions")
def sessions(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    return {"sessions": list_sessions(settings, session["id"], session["organization_id"]), "synthetic": True}


@router.post("/me/sessions/revoke-others")
def revoke_other_sessions(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    return {"revoked": revoke_others(settings, session["id"], session["organization_id"], session["session_id"]), "synthetic": True}


@router.post("/me/sessions/{session_id}/revoke")
def revoke_named_session(session_id: UUID, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    if not revoke_session(settings, session["id"], session["organization_id"], session_id):
        raise HTTPException(404, {"code": "session_missing", "message": "This session was not found.", "retryable": False})
    response = JSONResponse({"revoked": True, "synthetic": True})
    if session_id == session["session_id"]:
        response.delete_cookie(COOKIE, path="/")
        response.delete_cookie("pp_csrf", path="/")
    return response


@router.post("/me/context")
def switch_context(body: ContextBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    try:
        selected = select_context(settings, session["id"], session["organization_id"], session["session_id"], body.membership_id)
    except ValueError as exc:
        raise HTTPException(409, {"code": str(exc), "message": "That access context is not available.", "retryable": False}) from exc
    token = selected.pop("token")
    csrf = selected.pop("csrf")
    response = JSONResponse({**selected, "csrf": csrf, "synthetic": True})
    _session_cookie(response, token, csrf)
    return response


@router.post("/access/requests")
def request_access(body: AccessRequestBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "access.request")
    try:
        request_id = create_access_request(
            settings,
            session["id"],
            session["organization_id"],
            body.capability,
            body.purpose,
            body.scope_type,
            body.scope_resource_id,
            body.duration_hours,
            body.justification,
        )
    except ValueError as exc:
        raise HTTPException(400, {"code": str(exc), "message": "This access request is invalid.", "retryable": False}) from exc
    return {"request_id": request_id, "synthetic": True}


@router.post("/access/requests/{request_id}")
def review_access(request_id: UUID, body: AccessDecisionBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        requester_id = connection.execute(
            text("SELECT requester_id FROM access_requests WHERE id = :id AND organization_id = :org AND status = 'pending'"),
            {"id": request_id, "org": session["organization_id"]},
        ).scalar()
    if requester_id is None:
        raise HTTPException(404, {"code": "request_missing", "message": "This access request was not found.", "retryable": False})
    if requester_id == session["id"]:
        raise HTTPException(409, {"code": "self_approval", "message": "You cannot approve your own access request.", "retryable": False})
    _authorize_session(settings, session, "access.approve", privileged=True)
    try:
        decide_access_request(settings, session["id"], session["organization_id"], request_id, body.approve)
    except ValueError as exc:
        raise HTTPException(409, {"code": str(exc), "message": "This access request cannot be decided by you.", "retryable": False}) from exc
    return {"decided": True, "synthetic": True}


@router.post("/access/memberships/{membership_id}/authority-approvals")
def approve_authority_change(
    membership_id: UUID,
    body: AuthorityApprovalBody,
    request: Request,
    settings: Settings = Depends(settings),
):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "approval.owner", privileged=True)
    if body.action == "role" and not body.role_name:
        raise HTTPException(400, {"code": "approval_details_invalid", "message": "A role is required.", "retryable": False})
    if body.action == "scope" and not body.scope_type:
        raise HTTPException(400, {"code": "approval_details_invalid", "message": "A scope is required.", "retryable": False})
    approval_id = uuid4()
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        target = connection.execute(
            text("SELECT account_id FROM memberships WHERE id = :id AND organization_id = :org"),
            {"id": membership_id, "org": session["organization_id"]},
        ).scalar()
        if target is None:
            raise HTTPException(404, {"code": "membership_missing", "message": "This membership was not found.", "retryable": False})
        if target == session["id"]:
            raise HTTPException(409, {"code": "self_approval", "message": "You cannot approve your own authority.", "retryable": False})
        connection.execute(
            text(
                """
                INSERT INTO authority_change_approvals (
                  organization_id, id, membership_id, target_account_id,
                  action, role_name, scope_type, resource_id, reason,
                  approved_by, expires_at
                ) VALUES (
                  :org, :id, :membership, :target,
                  :action, :role, :scope, :resource, :reason,
                  :approver, now() + interval '24 hours'
                )
                """
            ),
            {
                "org": session["organization_id"],
                "id": approval_id,
                "membership": membership_id,
                "target": target,
                "action": body.action,
                "role": body.role_name,
                "scope": body.scope_type,
                "resource": body.resource_id,
                "reason": body.reason,
                "approver": session["id"],
            },
        )
    return {"approval_id": str(approval_id), "expires_in_hours": 24, "synthetic": True}


@router.post("/access/memberships/{membership_id}/role")
def assign_role(membership_id: UUID, body: RoleAssignmentBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "role.manage", privileged=True)
    if body.role_name not in BUNDLES:
        raise HTTPException(400, {"code": "role_invalid", "message": "That role is not available.", "retryable": False})
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        membership = connection.execute(
            text(
                """
                SELECT id, account_id, role_name FROM memberships
                WHERE id = :id AND organization_id = :org
                  AND effective_at <= now() AND (ended_at IS NULL OR ended_at > now())
                """
            ),
            {"id": membership_id, "org": session["organization_id"]},
        ).mappings().first()
        if membership is None:
            raise HTTPException(404, {"code": "membership_missing", "message": "This membership was not found.", "retryable": False})
        if membership["account_id"] == session["id"]:
            raise HTTPException(409, {"code": "self_grant", "message": "You cannot grant a role to yourself.", "retryable": False})
        if body.role_name in {"owner", "platform_admin"}:
            raise HTTPException(
                409,
                {
                    "code": "independent_approval_required",
                    "message": "This privileged role requires the separate approved recovery and access workflow.",
                    "retryable": False,
                },
            )
        materially_privileged = any(
            capability in BUNDLES[body.role_name]
            for capability in {
                "access.approve",
                "delegation.grant",
                "expense.approve",
                "security.read",
                "service.manage",
            }
        )
        if materially_privileged:
            consumed = connection.execute(
                text(
                    """
                    UPDATE authority_change_approvals
                    SET consumed_at = now(), consumed_by = :actor
                    WHERE organization_id = :org AND id = :approval
                      AND membership_id = :membership AND target_account_id = :target
                      AND action = 'role' AND role_name = :role
                      AND consumed_at IS NULL AND expires_at > now()
                      AND approved_by <> :actor AND approved_by <> :target
                    RETURNING id
                    """
                ),
                {
                    "actor": session["id"],
                    "org": session["organization_id"],
                    "approval": body.approval_id,
                    "membership": membership_id,
                    "target": membership["account_id"],
                    "role": body.role_name,
                },
            ).scalar()
            if consumed is None:
                raise HTTPException(
                    409,
                    {
                        "code": "independent_owner_approval_required",
                        "message": "A separate owner must approve this materially privileged role.",
                        "retryable": False,
                    },
                )
        bundle_id = connection.execute(
            text("SELECT id FROM role_bundles WHERE name = :name"),
            {"name": body.role_name},
        ).scalar()
        if bundle_id is None:
            raise HTTPException(409, {"code": "role_unavailable", "message": "That role bundle is unavailable.", "retryable": False})
        connection.execute(
            text(
                """
                UPDATE membership_role_assignments
                SET ended_at = now()
                WHERE membership_id = :membership AND ended_at IS NULL
                """
            ),
            {"membership": membership_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO membership_role_assignments (
                  organization_id, id, membership_id, bundle_id, assigned_by
                ) VALUES (:org, :id, :membership, :bundle, :actor)
                """
            ),
            {
                "org": session["organization_id"],
                "id": uuid4(),
                "membership": membership_id,
                "bundle": bundle_id,
                "actor": session["id"],
            },
        )
        connection.execute(
            text("UPDATE memberships SET role_name = :role WHERE id = :id"),
            {"role": body.role_name, "id": membership_id},
        )
        connection.execute(
            text("SELECT perchpoint.revoke_account_sessions(:account, 'role_changed')"),
            {"account": membership["account_id"]},
        )
    return {"assigned": True, "role_name": body.role_name, "synthetic": True}


@router.post("/access/memberships/{membership_id}/scopes")
def assign_scope(membership_id: UUID, body: ScopeAssignmentBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "scope.manage", privileged=True)
    allowed = {
        "organization", "portfolio", "property", "building", "space", "household", "lease",
        "application", "work_order", "vendor_company", "assignment", "document_classification",
        "amount", "decision_type", "time",
    }
    if body.scope_type not in allowed:
        raise HTTPException(400, {"code": "scope_invalid", "message": "That scope type is not available.", "retryable": False})
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        membership = connection.execute(
            text("SELECT account_id FROM memberships WHERE id = :id AND organization_id = :org"),
            {"id": membership_id, "org": session["organization_id"]},
        ).mappings().first()
        if membership is None:
            raise HTTPException(404, {"code": "membership_missing", "message": "This membership was not found.", "retryable": False})
        if membership["account_id"] == session["id"]:
            raise HTTPException(409, {"code": "self_grant", "message": "You cannot grant a scope to yourself.", "retryable": False})
        consumed = connection.execute(
            text(
                """
                UPDATE authority_change_approvals
                SET consumed_at = now(), consumed_by = :actor
                WHERE organization_id = :org AND id = :approval
                  AND membership_id = :membership AND target_account_id = :target
                  AND action = 'scope' AND scope_type = :scope
                  AND resource_id IS NOT DISTINCT FROM :resource
                  AND consumed_at IS NULL AND expires_at > now()
                  AND approved_by <> :actor AND approved_by <> :target
                RETURNING id
                """
            ),
            {
                "actor": session["id"],
                "org": session["organization_id"],
                "approval": body.approval_id,
                "membership": membership_id,
                "target": membership["account_id"],
                "scope": body.scope_type,
                "resource": body.resource_id,
            },
        ).scalar()
        if consumed is None:
            raise HTTPException(
                409,
                {
                    "code": "independent_owner_approval_required",
                    "message": "A separate owner must approve this authority scope.",
                    "retryable": False,
                },
            )
        if body.scope_type == "organization" and body.resource_id != session["organization_id"]:
            raise HTTPException(400, {"code": "scope_resource_invalid", "message": "The organization scope does not match the active organization.", "retryable": False})
        scope_id = uuid4()
        assignment_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO authorization_scopes (organization_id, id, scope_type, resource_id)
                VALUES (:org, :id, :type, :resource)
                """
            ),
            {"org": session["organization_id"], "id": scope_id, "type": body.scope_type, "resource": body.resource_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO membership_scope_assignments (
                  organization_id, id, membership_id, scope_id
                ) VALUES (:org, :id, :membership, :scope)
                """
            ),
            {
                "org": session["organization_id"],
                "id": assignment_id,
                "membership": membership_id,
                "scope": scope_id,
            },
        )
    return {"assigned": True, "scope_id": str(scope_id), "assignment_id": str(assignment_id), "synthetic": True}


@router.post("/access/service-credentials/{principal_id}")
def service_credential(principal_id: UUID, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "service.manage", privileged=True)
    try:
        credential = issue_service_credential(
            settings, session["id"], session["organization_id"], principal_id
        )
    except ValueError as exc:
        raise HTTPException(409, {"code": str(exc), "message": "This service principal cannot receive a credential.", "retryable": False}) from exc
    return {**credential, "shown_once": True, "synthetic": True}


@router.delete("/access/service-credentials/{credential_id}")
def revoke_service_credential(
    credential_id: UUID,
    request: Request,
    settings: Settings = Depends(settings),
):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "service.manage", privileged=True)
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        updated = connection.execute(
            text(
                """
                UPDATE service_credentials
                SET revoked_at = now()
                WHERE organization_id = :org AND id = :id AND revoked_at IS NULL
                """
            ),
            {"org": session["organization_id"], "id": credential_id},
        ).rowcount
    if not updated:
        raise HTTPException(404, {"code": "credential_missing", "message": "This credential was not found.", "retryable": False})
    return {"revoked": True, "synthetic": True}


@router.get("/access/service-principals")
def service_principals(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _authorize_session(settings, session, "service.manage")
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        rows = connection.execute(
            text(
                """
                SELECT p.id, p.name, p.status, p.audience, p.capabilities,
                       count(c.id) FILTER (
                         WHERE c.revoked_at IS NULL AND c.expires_at > now()
                       ) AS active_credentials,
                       max(c.last_used_at) AS last_used_at
                FROM service_principals p
                LEFT JOIN service_credentials c
                  ON c.organization_id = p.organization_id AND c.principal_id = p.id
                WHERE p.organization_id = :org
                GROUP BY p.id, p.name, p.status, p.audience, p.capabilities
                ORDER BY p.name
                """
            ),
            {"org": session["organization_id"]},
        ).mappings().all()
    return {"principals": [dict(row) for row in rows], "synthetic": True}


@router.post("/access/recoveries")
def open_recovery(body: RecoveryOpenBody, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    if body.subject_account == session["id"]:
        raise HTTPException(409, {"code": "self_recovery", "message": "You cannot recover your own privileged account.", "retryable": False})
    _authorize_session(settings, session, "security.read", privileged=True)
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        initiator_role = connection.execute(
            text("SELECT perchpoint.role_for_account(:account)"),
            {"account": session["id"]},
        ).scalar()
        subject_role = connection.execute(
            text("SELECT perchpoint.role_for_account(:account)"),
            {"account": body.subject_account},
        ).scalar()
        approver_role = (
            connection.execute(
                text("SELECT perchpoint.role_for_account(:account)"),
                {"account": body.approver_account},
            ).scalar()
            if body.approver_account is not None
            else None
        )
    verdict = recovery_participants(
        subject_role or "",
        initiator_role or "",
        approver_role,
    )
    if verdict != "allowed":
        raise HTTPException(409, {"code": verdict, "message": "This recovery needs the required second person.", "retryable": False})
    recovery_id = open_privileged_recovery(settings, session["id"], session["organization_id"], body.subject_account, body.evidence, body.approver_account)
    return {"recovery_id": recovery_id, "status": "waiting", "synthetic": True}


@router.post("/access/recoveries/{recovery_id}/approve")
def approve_recovery(recovery_id: UUID, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "security.read", privileged=True)
    try:
        approve_privileged_recovery(
            settings,
            session["id"],
            session["organization_id"],
            recovery_id,
        )
    except ValueError as exc:
        raise HTTPException(409, {"code": str(exc), "message": "This recovery cannot be approved by you.", "retryable": False}) from exc
    return {"status": "ready", "synthetic": True}


@router.post("/access/recoveries/{recovery_id}/complete")
def complete_governed_recovery(recovery_id: UUID, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "security.read", privileged=True)
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        provider_subject = connection.execute(
            text(
                """
                SELECT perchpoint.recovery_provider_subject(
                  :recovery, :actor, :org
                )
                """
            ),
            {
                "recovery": recovery_id,
                "actor": session["id"],
                "org": session["organization_id"],
            },
        ).scalar()
    if not provider_subject:
        raise HTTPException(409, {"code": "recovery_not_ready", "message": "The recovery approval or cooling period is incomplete.", "retryable": False})
    try:
        for factor_id in list_user_factors(str(provider_subject)):
            admin_remove_factor(str(provider_subject), factor_id)
    except ProviderError as exc:
        raise HTTPException(503, {"code": "provider_unavailable", "message": "Recovery is temporarily unavailable.", "retryable": True}) from exc
    try:
        subject_account = complete_privileged_recovery(
            settings,
            session["id"],
            session["organization_id"],
            recovery_id,
        )
    except ValueError as exc:
        raise HTTPException(409, {"code": str(exc), "message": "This recovery cannot be completed.", "retryable": False}) from exc
    return {"status": "completed", "subject_account": str(subject_account), "authority_changed": False, "synthetic": True}


@router.post("/auth/invitations/{invitation_id}/revoke")
def revoke_invite(invitation_id: UUID, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "invitation.create")
    try:
        revoke_invitation(settings, session["id"], session["organization_id"], invitation_id)
    except ValueError as exc:
        raise HTTPException(400, {"code": str(exc), "message": "This invitation is no longer valid.", "retryable": False}) from exc
    return {"revoked": True, "synthetic": True}


@router.post("/auth/invitations/{invitation_id}/expire")
def expire_invite(invitation_id: UUID, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "invitation.create")
    try:
        expire_invitation(settings, session["id"], session["organization_id"], invitation_id)
    except ValueError as exc:
        raise HTTPException(400, {"code": str(exc), "message": "This invitation is no longer valid.", "retryable": False}) from exc
    return {"expired": True, "synthetic": True}


@router.post("/auth/invitations/{invitation_id}/resend")
def resend_invite(invitation_id: UUID, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "invitation.create")
    try:
        replacement = resend_invitation(
            settings,
            session["id"],
            session["organization_id"],
            invitation_id,
        )
    except ValueError as exc:
        raise HTTPException(400, {"code": str(exc), "message": "This invitation cannot be resent.", "retryable": False}) from exc
    return {**replacement, "synthetic": True}


@router.post("/access/delegations/{delegation_id}/revoke")
def revoke_grant(delegation_id: UUID, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "delegation.revoke", privileged=True)
    try:
        revoke_delegation(settings, session["id"], session["organization_id"], delegation_id)
    except ValueError as exc:
        raise HTTPException(409, {"code": str(exc), "message": "This delegation cannot be revoked.", "retryable": False}) from exc
    return {"revoked": True, "synthetic": True}


@router.post("/access/delegations/{delegation_id}/expire")
def expire_grant(delegation_id: UUID, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "delegation.revoke", privileged=True)
    try:
        expire_delegation(settings, session["id"], session["organization_id"], delegation_id)
    except ValueError as exc:
        raise HTTPException(409, {"code": str(exc), "message": "This delegation cannot be expired.", "retryable": False}) from exc
    return {"expired": True, "synthetic": True}


@router.post("/maintenance/cases")
def create_maintenance_case(
    body: MaintenanceCaseBody,
    request: Request,
    settings: Settings = Depends(settings),
):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "maintenance.coordinate")
    case_id = uuid4()
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        connection.execute(
            text(
                """
                INSERT INTO maintenance_cases (
                  organization_id, id, assignment_id, created_by
                ) VALUES (:org, :id, :assignment, :actor)
                """
            ),
            {
                "org": session["organization_id"],
                "id": case_id,
                "assignment": body.assignment_id,
                "actor": session["id"],
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO maintenance_case_events (
                  organization_id, id, case_id, event_type, content, actor_id
                ) VALUES (
                  :org, :id, :case, 'reported_problem', :content, :actor
                )
                """
            ),
            {
                "org": session["organization_id"],
                "id": uuid4(),
                "case": case_id,
                "content": body.reported_problem,
                "actor": session["id"],
            },
        )
    return {"case_id": str(case_id), "synthetic": True}


@router.post("/access/vendor/workers/proposals")
def propose_vendor_worker(
    body: VendorWorkerProposalBody,
    request: Request,
    settings: Settings = Depends(settings),
):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "vendor.admin")
    if body.ends_at <= body.starts_at:
        raise HTTPException(400, {"code": "assignment_window", "message": "The assignment end must follow its start.", "retryable": True})
    proposal_id = uuid4()
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        relationship = connection.execute(
            text(
                """
                SELECT id FROM vendor_relationships
                WHERE organization_id = :org
                  AND id = :relationship
                  AND status = 'active'
                """
            ),
            {"org": session["organization_id"], "relationship": body.vendor_relationship_id},
        ).scalar()
        if relationship is None:
            raise HTTPException(404, {"code": "vendor_relationship_missing", "message": "This vendor relationship was not found.", "retryable": False})
        connection.execute(
            text(
                """
                INSERT INTO vendor_worker_proposals (
                  organization_id, id, vendor_relationship_id, email, role_name,
                  property_id, starts_at, ends_at, status, proposed_by
                ) VALUES (
                  :org, :id, :relationship, lower(:email), :role,
                  :property, :starts, :ends, 'proposed', :actor
                )
                """
            ),
            {
                "org": session["organization_id"],
                "id": proposal_id,
                "relationship": body.vendor_relationship_id,
                "email": body.email,
                "role": body.role_name,
                "property": body.property_id,
                "starts": body.starts_at,
                "ends": body.ends_at,
                "actor": session["id"],
            },
        )
    return {"proposal_id": str(proposal_id), "status": "proposed", "synthetic": True}


@router.post("/access/vendor/workers/proposals/{proposal_id}")
def decide_vendor_worker(
    proposal_id: UUID,
    body: VendorWorkerDecisionBody,
    request: Request,
    settings: Settings = Depends(settings),
):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "vendor.worker.approve", privileged=True)
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        proposal = connection.execute(
            text(
                """
                SELECT email, role_name, proposed_by
                FROM vendor_worker_proposals
                WHERE organization_id = :org
                  AND id = :id
                  AND status = 'proposed'
                """
            ),
            {"org": session["organization_id"], "id": proposal_id},
        ).mappings().first()
    if proposal is None:
        raise HTTPException(404, {"code": "vendor_proposal_missing", "message": "This worker proposal was not found.", "retryable": False})
    if proposal["proposed_by"] == session["id"]:
        raise HTTPException(409, {"code": "self_approval", "message": "You cannot approve your own worker proposal.", "retryable": False})
    if not body.approve:
        with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
            connection.execute(
                text(
                    """
                    UPDATE vendor_worker_proposals
                    SET status = 'denied', decided_by = :actor, decided_at = now()
                    WHERE organization_id = :org AND id = :id AND status = 'proposed'
                    """
                ),
                {"actor": session["id"], "org": session["organization_id"], "id": proposal_id},
            )
        return {"status": "denied", "synthetic": True}
    invitation = create_invitation(
        settings,
        session["id"],
        session["organization_id"],
        proposal["email"],
        proposal["role_name"],
        body.purpose,
        staff=False,
        relationship_type="vendor_worker_proposal",
        relationship_id=proposal_id,
        scope_payload={"type": "vendor_worker_proposal", "resource_id": str(proposal_id)},
        approval_status="pending",
    )
    invitation_id = UUID(invitation["invitation_id"])
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        bound = connection.execute(
            text(
                """
                WITH approved_proposal AS (
                  UPDATE vendor_worker_proposals
                  SET status = 'approved',
                      decided_by = :actor,
                      decided_at = now(),
                      invitation_id = :invitation
                  WHERE organization_id = :org
                    AND id = :proposal
                    AND status = 'proposed'
                  RETURNING id
                )
                UPDATE identity_invitations
                SET approval_status = 'approved'
                WHERE organization_id = :org
                  AND id = :invitation
                  AND relationship_type = 'vendor_worker_proposal'
                  AND relationship_id = :proposal
                  AND approval_status = 'pending'
                  AND EXISTS (SELECT 1 FROM approved_proposal)
                RETURNING id
                """
            ),
            {
                "actor": session["id"],
                "proposal": proposal_id,
                "org": session["organization_id"],
                "invitation": invitation_id,
            },
        ).scalar()
        if bound is None:
            connection.execute(
                text(
                    """
                    UPDATE identity_invitations
                    SET revoked_at = now()
                    WHERE organization_id = :org
                      AND id = :invitation
                      AND approval_status = 'pending'
                    """
                ),
                {"org": session["organization_id"], "invitation": invitation_id},
            )
            raise HTTPException(
                409,
                {"code": "vendor_proposal_decided", "message": "This worker proposal was already decided.", "retryable": False},
            )
    return {"status": "approved", "invitation_id": str(invitation_id), "synthetic": True}


@router.post("/maintenance/cases/{case_id}/events")
def append_maintenance_event(
    case_id: UUID,
    body: MaintenanceEventBody,
    request: Request,
    settings: Settings = Depends(settings),
):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    technician_events = {
        "technician_observation",
        "technician_recommendation",
        "installed_solution",
    }
    capability = "work.assign" if body.event_type in technician_events else "maintenance.coordinate"
    _authorize_session(settings, session, capability)
    event_id = uuid4()
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        inserted = connection.execute(
            text(
                """
                INSERT INTO maintenance_case_events (
                  organization_id, id, case_id, event_type, content, actor_id
                )
                SELECT :org, :id, case_record.id, :event_type, :content, :actor
                FROM maintenance_cases case_record
                WHERE case_record.organization_id = :org
                  AND case_record.id = :case
                  AND case_record.status = 'open'
                  AND (
                    NOT :technician_event
                    OR EXISTS (
                      SELECT 1
                      FROM worker_assignments assignment
                      WHERE assignment.organization_id = case_record.organization_id
                        AND assignment.id = case_record.assignment_id
                        AND assignment.worker_account_id = :actor
                        AND assignment.status = 'active'
                        AND assignment.starts_at <= now()
                        AND assignment.ends_at > now()
                    )
                  )
                RETURNING id
                """
            ),
            {
                "org": session["organization_id"],
                "id": event_id,
                "case": case_id,
                "event_type": body.event_type,
                "content": body.content,
                "actor": session["id"],
                "technician_event": body.event_type in technician_events,
            },
        ).scalar()
    if inserted is None:
        raise HTTPException(404, {"code": "maintenance_case_missing", "message": "This maintenance case was not found.", "retryable": False})
    return {"event_id": str(event_id), "event_type": body.event_type, "synthetic": True}


@router.get("/maintenance/cases/{case_id}")
def maintenance_case(case_id: UUID, request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _authorize_session(settings, session, "work.assign")
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        events = connection.execute(
            text(
                """
                SELECT id, event_type, content, actor_id, occurred_at
                FROM maintenance_case_events
                WHERE organization_id = :org
                  AND case_id = :case
                ORDER BY occurred_at, id
                """
            ),
            {"org": session["organization_id"], "case": case_id},
        ).mappings().all()
    if not events:
        raise HTTPException(404, {"code": "maintenance_case_missing", "message": "This maintenance case was not found.", "retryable": False})
    return {"case_id": str(case_id), "events": [dict(row) for row in events], "synthetic": True}


@router.get("/households")
def households(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        rows = connection.execute(text("SELECT id, label FROM households ORDER BY label")).mappings().all()
    return {"households": [{"id": str(row["id"]), "label": row["label"]} for row in rows], "synthetic": True}


@router.get("/access/users")
def access_users(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _authorize_session(settings, session, "security.read")
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        rows = connection.execute(
            text("SELECT * FROM perchpoint.access_directory()"),
        ).mappings().all()
    return {
        "users": [
            {
                "account_id": str(row["account_id"]),
                "email": row["email"],
                "membership_id": str(row["membership_id"]),
                "role_name": row["role_name"],
                "lifecycle_status": row["lifecycle_status"],
                "is_self": row["account_id"] == session["id"],
                "can_suspend": row["account_id"] != session["id"] and row["lifecycle_status"] == "active",
                "can_restore": row["account_id"] != session["id"] and row["lifecycle_status"] == "suspended",
            }
            for row in rows
        ],
        "synthetic": True,
    }


@router.get("/access/delegations")
def access_delegations(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _authorize_session(settings, session, "delegation.grant")
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        rows = connection.execute(
            text(
                """
                SELECT id, grantor_id, grantee_id, capability, amount_ceiling_minor,
                       starts_at, ends_at, status, reason, revoked_at
                FROM delegations
                WHERE organization_id = :org
                  AND (grantor_id = :actor OR grantee_id = :actor)
                ORDER BY created_at DESC
                """
            ),
            {"org": session["organization_id"], "actor": session["id"]},
        ).mappings().all()
    return {"delegations": [dict(row) for row in rows], "synthetic": True}


@router.get("/access/requests")
def access_request_list(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _authorize_session(settings, session, "access.request")
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        can_approve = connection.execute(
            text("SELECT perchpoint.has_capability('access.approve')")
        ).scalar_one()
        rows = connection.execute(
            text(
                """
                SELECT id, requester_id, capability, purpose, scope_type, scope_resource_id,
                       justification, requested_until, status, approver_id, created_at, decided_at
                FROM access_requests
                WHERE organization_id = :org
                  AND (
                    requester_id = :actor
                    OR approver_id = :actor
                    OR (:can_approve AND status = 'pending')
                  )
                ORDER BY created_at DESC
                """
            ),
            {
                "org": session["organization_id"],
                "actor": session["id"],
                "can_approve": can_approve,
            },
        ).mappings().all()
    return {"requests": [dict(row) for row in rows], "synthetic": True}


@router.get("/access/reviews")
def access_reviews(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _authorize_session(settings, session, "security.read")
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        rows = connection.execute(
            text(
                """
                SELECT campaign.id, campaign.title, campaign.opens_at, campaign.due_at,
                       count(item.id) AS item_count,
                       count(item.id) FILTER (WHERE item.status = 'pending') AS pending_count
                FROM access_review_campaigns campaign
                LEFT JOIN access_review_items item
                  ON item.organization_id = campaign.organization_id AND item.campaign_id = campaign.id
                WHERE campaign.organization_id = :org
                GROUP BY campaign.id, campaign.title, campaign.opens_at, campaign.due_at
                ORDER BY campaign.due_at
                """
            ),
            {"org": session["organization_id"]},
        ).mappings().all()
    return {"reviews": [dict(row) for row in rows], "synthetic": True}


@router.post("/access/reviews/{campaign_id}/items/{item_id}")
def decide_access_review(
    campaign_id: UUID,
    item_id: UUID,
    body: AccessReviewDecisionBody,
    request: Request,
    settings: Settings = Depends(settings),
):
    session = _session_actor(request, settings)
    _require_csrf(request, session)
    _authorize_session(settings, session, "security.read", privileged=True)
    if body.decision == "change" and not body.change:
        raise HTTPException(400, {"code": "review_change_required", "message": "Describe the required access change.", "retryable": True})
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        item = connection.execute(
            text(
                """
                SELECT review.account_id, (
                  SELECT membership.role_name
                  FROM memberships membership
                  WHERE membership.organization_id = review.organization_id
                    AND membership.account_id = review.account_id
                    AND membership.effective_at <= now()
                    AND (membership.ended_at IS NULL OR membership.ended_at > now())
                  ORDER BY membership.effective_at DESC, membership.id
                  LIMIT 1
                ) AS role_name
                FROM access_review_items review
                WHERE review.organization_id = :org
                  AND review.campaign_id = :campaign
                  AND review.id = :item
                  AND review.status = 'pending'
                FOR UPDATE
                """
            ),
            {
                "org": session["organization_id"],
                "campaign": campaign_id,
                "item": item_id,
            },
        ).mappings().first()
        if item is None:
            raise HTTPException(404, {"code": "review_item_missing", "message": "This review item was not found.", "retryable": False})
        if item["account_id"] == session["id"]:
            raise HTTPException(409, {"code": "self_approval", "message": "You cannot review your own access.", "retryable": False})
        if item["role_name"] in {"owner", "platform_admin"}:
            raise HTTPException(
                409,
                {
                    "code": "governed_privileged_review_required",
                    "message": "Owner and platform-administrator access requires the separate governed authority workflow.",
                    "retryable": False,
                },
            )
        status = "revoked" if body.decision == "revoke" else "certified"
        connection.execute(
            text(
                """
                UPDATE access_review_items
                SET status = :status,
                    reviewer_id = :reviewer,
                    decision = :decision,
                    decided_at = now(),
                    change_payload = CAST(:change AS jsonb)
                WHERE organization_id = :org
                  AND campaign_id = :campaign
                  AND id = :item
                """
            ),
            {
                "status": status,
                "reviewer": session["id"],
                "decision": body.decision,
                "change": json.dumps(body.change),
                "org": session["organization_id"],
                "campaign": campaign_id,
                "item": item_id,
            },
        )
        if body.decision == "revoke":
            connection.execute(
                text(
                    """
                    UPDATE memberships
                    SET ended_at = now()
                    WHERE organization_id = :org
                      AND account_id = :account
                      AND effective_at <= now()
                      AND (ended_at IS NULL OR ended_at > now())
                    """
                ),
                {"org": session["organization_id"], "account": item["account_id"]},
            )
            connection.execute(
                text("SELECT perchpoint.revoke_account_sessions(:account, 'access_review_revoked')"),
                {"account": item["account_id"]},
            )
        elif body.decision == "change":
            connection.execute(
                text(
                    """
                    INSERT INTO access_review_remediations (
                      organization_id, id, review_item_id, action, due_at
                    ) VALUES (
                      :org, :id, :item, :action, now() + interval '7 days'
                    )
                    """
                ),
                {
                    "org": session["organization_id"],
                    "id": uuid4(),
                    "item": item_id,
                    "action": json.dumps(body.change, sort_keys=True),
                },
            )
        remaining = connection.execute(
            text(
                """
                SELECT count(*)
                FROM access_review_items
                WHERE organization_id = :org
                  AND campaign_id = :campaign
                  AND status = 'pending'
                """
            ),
            {"org": session["organization_id"], "campaign": campaign_id},
        ).scalar_one()
        if remaining == 0:
            connection.execute(
                text(
                    """
                    UPDATE access_review_campaigns
                    SET completed_at = now()
                    WHERE organization_id = :org
                      AND id = :campaign
                    """
                ),
                {"org": session["organization_id"], "campaign": campaign_id},
            )
    return {"decision": body.decision, "status": status, "campaign_complete": remaining == 0, "synthetic": True}


@router.get("/access/security-events")
def access_security_events(request: Request, settings: Settings = Depends(settings)):
    session = _session_actor(request, settings)
    _authorize_session(settings, session, "security.read")
    with runtime_transaction(settings, session["id"], session["organization_id"], uuid4()) as connection:
        rows = connection.execute(
            text(
                """
                SELECT id, action, outcome, reason_code, resource_type, created_at
                FROM security_events
                WHERE organization_id = :org
                ORDER BY created_at DESC
                LIMIT 100
                """
            ),
            {"org": session["organization_id"]},
        ).mappings().all()
    return {"events": [dict(row) for row in rows], "synthetic": True}


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
        try:
            request_uuid = UUID(request.headers.get("x-request-id", ""))
        except ValueError:
            request_uuid = uuid4()
        request_id = str(request_uuid)
        request_token = _request_context.set(request_uuid)
        context_token = set_authority_context(None)
        unauthenticated_mutations = {
            "/api/v2/session",
            "/api/v2/inquiries",
            "/api/v2/inbox/synthetic",
            "/api/v2/auth/sign-in",
            "/api/v2/auth/invitations/accept",
            "/api/v2/auth/password/reset-request",
            "/api/v2/auth/password/reset",
        }
        try:
            if (
                request.method in {"POST", "PUT", "PATCH", "DELETE"}
                and request.url.path not in unauthenticated_mutations
                and request.cookies.get(COOKIE)
            ):
                cookie_session = resolve(settings(), request.cookies.get(COOKIE))
                if cookie_session is not None and (
                    not csrf_ok(cookie_session, request.headers.get(CSRF_HEADER))
                    or not _origin_allowed(request)
                ):
                    code = (
                        "csrf_rejected"
                        if not csrf_ok(cookie_session, request.headers.get(CSRF_HEADER))
                        else "origin_rejected"
                    )
                    try:
                        audited_session = _session_actor(request, settings())
                        _record_security_event(
                            settings(),
                            audited_session,
                            "csrf.mutation",
                            "denied",
                            code,
                        )
                    except HTTPException:
                        pass
                    response = JSONResponse(
                        {
                            "detail": {
                                "code": code,
                                "message": "The authenticated mutation was rejected.",
                                "retryable": code == "csrf_rejected",
                            }
                        },
                        status_code=403,
                    )
                else:
                    response = await call_next(request)
            else:
                response = await call_next(request)
        finally:
            reset_authority_context(context_token)
            _request_context.reset(request_token)
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
