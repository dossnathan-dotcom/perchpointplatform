"""Phase 7 public content, publication authority, and attributable intake."""
import os
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from perchpoint.routes import create_app


def _login(client, email):
    response = client.post("/api/v2/session", json={"email": email, "password": os.environ["PHASE2_DEV_PASSWORD"]})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_published_page_is_public_and_draft_is_not():
    client = TestClient(create_app())
    published = client.get("/api/v2/public/pages/about")
    assert published.status_code == 200, published.text
    assert "EXAMPLE ONLY" in published.json()["snapshot"]["blocks"][0]["text"]
    hidden = client.get("/api/v2/public/pages/internal-draft")
    assert hidden.status_code == 404
    assert "9999" not in hidden.text


def test_routine_publish_and_elevated_denial():
    client = TestClient(create_app())
    ann = _login(client, "ann.synthetic@example.com")
    slug = "routine-" + uuid4().hex[:8]
    draft = client.post(
        "/api/v2/content/drafts",
        headers=_auth(ann),
        json={
            "slug": slug,
            "title": "Hours update",
            "body": "EXAMPLE ONLY. Office hours are synthetic.",
            "kind": "page",
            "risk_class": "routine",
            "reason": "synthetic routine correction",
        },
    )
    assert draft.status_code == 201, draft.text
    published = client.post(
        f"/api/v2/content/{draft.json()['id']}/publish",
        headers=_auth(ann),
        json={"expected_version": 1},
    )
    assert published.status_code == 200, published.text
    public = client.get(f"/api/v2/public/pages/{slug}")
    assert public.status_code == 200
    stale = client.post(
        f"/api/v2/content/{draft.json()['id']}/publish",
        headers=_auth(ann),
        json={"expected_version": 1},
    )
    assert stale.status_code == 409
    elevated = client.post(
        "/api/v2/content/drafts",
        headers=_auth(ann),
        json={
            "slug": "legal-" + uuid4().hex[:8],
            "title": "Policy draft",
            "body": "EXAMPLE ONLY. This is not approved legal text.",
            "kind": "legal",
            "risk_class": "elevated",
            "reason": "synthetic elevated draft",
        },
    )
    assert elevated.status_code == 201, elevated.text
    denied = client.post(
        f"/api/v2/content/{elevated.json()['id']}/publish",
        headers=_auth(ann),
        json={"expected_version": 1},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "elevated_approval_required"


def test_submission_is_idempotent_and_rejects_conflict_and_attachment():
    client = TestClient(create_app())
    key = "form-" + uuid4().hex
    body = {
        "intent": "general",
        "name": "Synthetic Guest",
        "email": "guest@example.com",
        "message": "EXAMPLE ONLY inquiry",
        "consent_version": "synthetic-contact-v1",
        "source_page": "/contact",
        "first_touch": "direct",
        "last_touch": "contact",
        "idempotency_key": key,
    }
    first = client.post("/api/v2/public/submissions", json=body)
    assert first.status_code == 201, first.text
    assert first.json()["replayed"] is False
    second = client.post("/api/v2/public/submissions", json=body)
    assert second.status_code == 201, second.text
    assert second.json()["replayed"] is True
    assert second.json()["reference"] == first.json()["reference"]
    changed = dict(body)
    changed["message"] = "A different message"
    conflict = client.post("/api/v2/public/submissions", json=changed)
    assert conflict.status_code == 409
    attached = dict(body)
    attached["idempotency_key"] = "form-" + uuid4().hex
    attached["attachment"] = "lease.pdf"
    rejected = client.post("/api/v2/public/submissions", json=attached)
    assert rejected.status_code == 400
    ann = _login(client, "ann.synthetic@example.com")
    report = client.get("/api/v2/content/conversions", headers=_auth(ann))
    assert report.status_code == 200, report.text
    assert any(row["intent"] == "general" and row["total"] >= 1 for row in report.json()["totals"])


def test_unsafe_markup_and_resident_edit_are_denied():
    client = TestClient(create_app())
    ann = _login(client, "ann.synthetic@example.com")
    unsafe = client.post(
        "/api/v2/content/drafts",
        headers=_auth(ann),
        json={
            "slug": "unsafe-" + uuid4().hex[:8],
            "title": "Unsafe",
            "body": "<script>alert(1)</script>",
            "kind": "page",
            "risk_class": "routine",
            "reason": "injection attempt",
        },
    )
    assert unsafe.status_code == 400
    resident = _login(client, "resident.synthetic@example.com")
    denied = client.post(
        "/api/v2/content/drafts",
        headers=_auth(resident),
        json={
            "slug": "resident-" + uuid4().hex[:8],
            "title": "Resident draft",
            "body": "This should not save.",
            "kind": "page",
            "risk_class": "routine",
            "reason": "unauthorized",
        },
    )
    assert denied.status_code == 403


def test_honeypot_sitemap_preview_redirect_and_privacy():
    client = TestClient(create_app())
    honeypot = client.post(
        "/api/v2/public/submissions",
        json={
            "intent": "general",
            "name": "Synthetic Guest",
            "email": "guest@example.com",
            "message": "EXAMPLE ONLY",
            "consent_version": "synthetic-contact-v1",
            "source_page": "/contact",
            "idempotency_key": "form-" + uuid4().hex,
            "company_website": "https://spam.example",
        },
    )
    assert honeypot.status_code == 400
    sitemap = client.get("/api/v2/public/sitemap.xml")
    assert sitemap.status_code == 200
    assert "internal-draft" not in sitemap.text
    assert "9999" not in sitemap.text
    robots = client.get("/api/v2/public/robots.txt")
    assert robots.status_code == 200
    assert "Disallow: /staff/" in robots.text
    ann = _login(client, "ann.synthetic@example.com")
    preview = client.get("/api/v2/content/preview/internal-draft", headers=_auth(ann))
    assert preview.status_code == 200, preview.text
    assert preview.json()["noindex"] is True
    assert preview.headers["x-robots-tag"] == "noindex, nofollow"
    source = "/old-" + uuid4().hex[:8]
    created = client.post(
        "/api/v2/content/redirects",
        headers=_auth(ann),
        json={"source_path": source, "destination_path": "/about", "status_code": 301},
    )
    assert created.status_code == 201, created.text
    loop = client.post(
        "/api/v2/content/redirects",
        headers=_auth(ann),
        json={"source_path": "/about", "destination_path": source, "status_code": 301},
    )
    assert loop.status_code == 400
    external = client.post(
        "/api/v2/content/redirects",
        headers=_auth(ann),
        json={"source_path": "/away", "destination_path": "https://example.com", "status_code": 301},
    )
    assert external.status_code == 400
    followed = client.get("/api/v2/public/redirect", params={"path": source})
    assert followed.status_code == 200, followed.text
    assert followed.json()["destination"] == "/about"
    optional = client.post(
        "/api/v2/public/analytics",
        headers={"Sec-GPC": "1"},
        json={"name": "page_view", "consent": "optional", "properties": {"page": "about"}, "analytics_allowed": True},
    )
    assert optional.status_code == 202, optional.text
    assert optional.json()["stored"] is False
    leaked = client.post(
        "/api/v2/public/analytics",
        json={"name": "page_view", "consent": "essential", "properties": {"email": "guest@example.com"}},
    )
    assert leaked.status_code == 400


def test_rental_inquiry_requires_a_publishable_listing():
    client = TestClient(create_app())
    base = {
        "intent": "rental_inquiry",
        "name": "Synthetic Guest",
        "email": "guest@example.com",
        "message": "EXAMPLE ONLY rental question",
        "consent_version": "synthetic-contact-v1",
        "source_page": "/rentals/example-elm-court",
        "first_touch": "rentals",
        "last_touch": "listing",
    }
    accepted = client.post("/api/v2/public/submissions", json={**base, "listing_slug": "example-elm-court", "idempotency_key": "form-" + uuid4().hex})
    assert accepted.status_code == 201, accepted.text
    refused = client.post("/api/v2/public/submissions", json={**base, "listing_slug": "not-a-home", "idempotency_key": "form-" + uuid4().hex})
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "listing_unavailable"


def test_publication_lifecycle_cache_guardrail_and_schedule():
    client = TestClient(create_app())
    ann = _login(client, "ann.synthetic@example.com")
    slug = "lifecycle-" + uuid4().hex[:8]
    draft = client.post(
        "/api/v2/content/drafts",
        headers=_auth(ann),
        json={
            "slug": slug,
            "title": "Lifecycle page",
            "body": "EXAMPLE ONLY first revision.",
            "kind": "page",
            "risk_class": "routine",
            "reason": "synthetic first revision",
        },
    )
    assert draft.status_code == 201, draft.text
    item_id = draft.json()["id"]
    published = client.post(f"/api/v2/content/{item_id}/publish", headers=_auth(ann), json={"expected_version": 1})
    assert published.status_code == 200, published.text
    first = client.get(f"/api/v2/public/pages/{slug}")
    assert first.status_code == 200, first.text
    assert first.json()["canonical"] == f"/{slug}"
    assert first.json()["structured_data"]["@type"] == "WebPage"
    assert "aggregateRating" not in first.text
    edited = client.post(
        f"/api/v2/content/{item_id}/revisions",
        headers=_auth(ann),
        json={"expected_version": 2, "title": "Lifecycle page", "body": "EXAMPLE ONLY second revision.", "reason": "synthetic correction"},
    )
    assert edited.status_code == 201, edited.text
    republished = client.post(f"/api/v2/content/{item_id}/publish", headers=_auth(ann), json={"expected_version": 2})
    assert republished.status_code == 200, republished.text
    current = client.get(f"/api/v2/public/pages/{slug}")
    assert "second revision" in current.text
    restored = client.post(
        f"/api/v2/content/{item_id}/rollback",
        headers=_auth(ann),
        json={"expected_version": 3, "revision_id": draft.json()["revision_id"], "reason": "synthetic rollback"},
    )
    assert restored.status_code == 200, restored.text
    rolled = client.get(f"/api/v2/public/pages/{slug}")
    assert "first revision" in rolled.text
    assert "second revision" not in rolled.text
    removed = client.post(f"/api/v2/content/{item_id}/unpublish", headers=_auth(ann), json={"expected_version": restored.json()["version"]})
    assert removed.status_code == 200, removed.text
    hidden = client.get(f"/api/v2/public/pages/{slug}")
    assert hidden.status_code == 404
    protected = client.get("/api/v2/public/pages/privacy")
    privacy_id = None
    listing = client.get("/api/v2/content/preview/privacy", headers=_auth(ann))
    assert listing.status_code == 200
    guard = client.post(
        "/api/v2/content/jobs/run",
        headers=_auth(ann),
    )
    assert guard.status_code == 200
    blocked = client.post("/api/v2/public/pages/privacy")
    assert protected.status_code == 200
    assert blocked.status_code == 405
    elevated_slug = "scheduled-" + uuid4().hex[:8]
    elevated = client.post(
        "/api/v2/content/drafts",
        headers=_auth(ann),
        json={
            "slug": elevated_slug,
            "title": "Scheduled policy",
            "body": "EXAMPLE ONLY. Not approved legal text.",
            "kind": "legal",
            "risk_class": "elevated",
            "reason": "synthetic schedule",
        },
    )
    assert elevated.status_code == 201, elevated.text
    scheduled = client.post(
        f"/api/v2/content/{elevated.json()['id']}/schedule",
        headers=_auth(ann),
        json={"expected_version": 1, "run_at": "2020-01-01T00:00:00+00:00", "time_zone": "America/New_York", "action": "publish"},
    )
    assert scheduled.status_code == 202, scheduled.text
    ran = client.post("/api/v2/content/jobs/run", headers=_auth(ann))
    assert ran.status_code == 200, ran.text
    assert ran.json()["jobs"][-1]["status"] == "failed"
    assert ran.json()["jobs"][-1]["error"] == "authority_recheck_failed"
    leaked = client.get(f"/api/v2/public/pages/{elevated_slug}")
    assert leaked.status_code == 404
    assert privacy_id is None


def test_runtime_context_does_not_leak_content():
    import jwt
    from sqlalchemy import text

    from perchpoint.db import runtime_transaction
    from perchpoint.settings import Settings

    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    current = Settings.load()
    payload = jwt.decode(token, current.jwt_secret, algorithms=["HS256"])
    with runtime_transaction(current, UUID(payload["sub"]), UUID(payload["org"]), uuid4()) as connection:
        visible = connection.execute(text("SELECT count(*) FROM content_items")).scalar()
    assert visible and visible > 0
    with runtime_transaction(current, None, None, uuid4()) as connection:
        hidden = connection.execute(text("SELECT count(*) FROM content_items")).scalar()
    assert hidden == 0


def test_database_preflight_fails_fast_on_a_closed_port():
    import subprocess
    import sys

    completed = subprocess.run(
        [sys.executable, "scripts/phase7_db_preflight.py"],
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
        env={**os.environ, "PHASE7_PREFLIGHT_HOST": "127.0.0.1", "PHASE7_PREFLIGHT_PORT": "1"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "did not accept a connection" in completed.stdout + completed.stderr
    assert "Start the scoped PostgreSQL service" in completed.stdout + completed.stderr


def test_listings_keep_a_public_slug():
    client = TestClient(create_app())
    listed = client.get("/api/v2/listings")
    assert listed.status_code == 200, listed.text
    match = next(item for item in listed.json()["listings"] if item["property_name"] == "Example Elm Court")
    assert match["public_slug"] == "example-elm-court"


def test_content_dashboard_is_staff_only_and_lists_pages():
    client = TestClient(create_app())
    ann = _login(client, "ann.synthetic@example.com")
    listed = client.get("/api/v2/content/items", headers=_auth(ann))
    assert listed.status_code == 200, listed.text
    slugs = {item["slug"] for item in listed.json()["items"]}
    assert "about" in slugs
    assert "internal-draft" in slugs
    jobs = client.get("/api/v2/content/jobs", headers=_auth(ann))
    redirects = client.get("/api/v2/content/redirects", headers=_auth(ann))
    assert jobs.status_code == 200
    assert redirects.status_code == 200
    resident = _login(client, "resident.synthetic@example.com")
    denied = client.get("/api/v2/content/items", headers=_auth(resident))
    assert denied.status_code == 403


def test_property_visibility_policy_includes_worker_assignments():
    from sqlalchemy import create_engine, text

    from perchpoint.settings import Settings

    settings = Settings.load()
    database = create_engine(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with database.connect() as connection:
        expression = connection.execute(
            text(
                """
                SELECT pg_get_expr(polqual, polrelid)
                FROM pg_policy
                WHERE polrelid = 'properties'::regclass AND polname = 'property_capability_scope'
                """
            )
        ).scalar_one()
    database.dispose()
    assert "worker_assignment_allows" in expression
    assert "authorized_for" in expression
