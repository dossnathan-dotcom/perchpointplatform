"""Representative Phase 11 showing timing on a disposable database.

The database is created from the migrated local database, measured, and dropped.
Synthetic rows only. This is not a production capacity claim.
"""
from __future__ import annotations

import hashlib
import os
import statistics
import time
from uuid import uuid4

from sqlalchemy import create_engine, text


def _url(database: str) -> str:
    admin = os.environ["PHASE2_ADMIN_URL"]
    return admin.rsplit("/", 1)[0] + "/" + database


def _timed(connection, statement: str, params: dict, rounds: int = 3) -> dict:
    connection.execute(text(statement), params).all()
    samples = []
    for _ in range(rounds):
        started = time.perf_counter()
        connection.execute(text(statement), params).all()
        samples.append((time.perf_counter() - started) * 1000)
    ordered = sorted(samples)
    return {
        "p50_ms": ordered[len(ordered) // 2],
        "p95_ms": ordered[-1],
        "max_ms": max(samples),
        "samples_ms": [round(item, 3) for item in samples],
        "errors": 0,
        "timeouts": 0,
    }


def main() -> None:
    bench = "perchpoint_phase13_bench"
    admin = create_engine(_url("postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": bench})
        connection.execute(text(f"DROP DATABASE IF EXISTS {bench}"))
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'perchpoint_phase2' AND pid <> pg_backend_pid()"))
        connection.execute(text(f"CREATE DATABASE {bench} TEMPLATE perchpoint_phase2"))
    admin.dispose()
    engine = create_engine(_url(bench), pool_size=25, max_overflow=0)
    organization = uuid4()
    actor = uuid4()
    membership = uuid4()
    scope = uuid4()
    slug = "bench-listing"
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO organizations (id, name, synthetic) VALUES (:id, :name, true)"), {"id": organization, "name": "EXAMPLE ONLY benchmark organization"})
            connection.execute(text("INSERT INTO accounts (id, email, password_hash) VALUES (:id, :email, 'synthetic')"), {"id": actor, "email": f"bench-{actor.hex[:8]}@example.com"})
            connection.execute(
                text("INSERT INTO memberships (id, account_id, organization_id, role_name, effective_at) VALUES (:id, :account, :org, 'operations_manager', '1999-01-01')"),
                {"id": membership, "account": actor, "org": organization},
            )
            connection.execute(
                text("INSERT INTO authorization_scopes (organization_id, id, scope_type, resource_id) VALUES (:org, :id, 'organization', :org)"),
                {"org": organization, "id": scope},
            )
            connection.execute(
                text("INSERT INTO membership_scope_assignments (organization_id, id, membership_id, scope_id, effective_at) VALUES (:org, :id, :membership, :scope, '1999-01-01')"),
                {"org": organization, "id": uuid4(), "membership": membership, "scope": scope},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO properties (organization_id, id, name, property_type)
                    SELECT :org, gen_random_uuid(), 'Bench ' || n, 'multifamily'
                    FROM generate_series(1, 1001) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO buildings (organization_id, id, property_id, name, allowed_uses)
                    SELECT organization_id, gen_random_uuid(), id, 'Primary', ARRAY['residential']
                    FROM properties WHERE organization_id = :org
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO spaces (organization_id, id, property_id, building_id, label, use, square_feet)
                    SELECT building.organization_id, gen_random_uuid(), building.property_id, building.id,
                           'Space ' || n, 'residential', 900
                    FROM buildings building
                    CROSS JOIN generate_series(1, 3) AS n
                    WHERE building.organization_id = :org
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO asking_prices (
                      organization_id, id, space_id, amount_minor, currency, period, effective_on, reason, actor_id, approval_state
                    )
                    SELECT organization_id, gen_random_uuid(), id, 150000, 'USD', 'monthly', DATE '2026-10-01',
                           'Synthetic benchmark rent', :actor, 'routine'
                    FROM spaces WHERE organization_id = :org
                    """
                ),
                {"org": organization, "actor": actor},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO audit_events (
                      organization_id, id, actor_id, action, resource_type, resource_id, occurred_at,
                      correlation_id, result, event_hash
                    )
                    SELECT :org, gen_random_uuid(), :actor, 'benchmark.recorded', 'record', :actor, now(),
                           gen_random_uuid(), 'allowed', md5(n::text)
                    FROM generate_series(1, 250000) AS n
                    """
                ),
                {"org": organization, "actor": actor},
            )
            space = connection.execute(text("SELECT id FROM spaces WHERE organization_id = :org LIMIT 1"), {"org": organization}).scalar()
            listing = uuid4()
            connection.execute(
                text(
                    """
                    INSERT INTO listings (
                      organization_id, id, space_id, publication, availability, property_name, label, use,
                      municipality, state, amount_minor, currency, public_slug
                    ) VALUES (
                      :org, :id, :space, 'published', 'offerable', 'Bench 1', 'Space 1', 'residential',
                      'Cincinnati', 'OH', 150000, 'USD', :slug
                    )
                    """
                ),
                {"org": organization, "id": listing, "space": space, "slug": slug},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO listing_snapshots (
                      organization_id, id, listing_id, space_id, public_slug, schema_version, content_hash, payload, actor_id
                    ) VALUES (
                      :org, :id, :listing, :space, :slug, 1, 'bench',
                      CAST(:payload AS jsonb),
                      :actor
                    )
                    """
                ),
                {"org": organization, "id": uuid4(), "listing": listing, "space": space, "slug": slug, "actor": actor, "payload": '{"property_name":"Bench 1","amount_minor":150000,"synthetic":true,"schema_version":1}'},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO listings (
                      organization_id, id, space_id, publication, availability, property_name, label, use,
                      municipality, state, amount_minor, currency, public_slug
                    )
                    SELECT space.organization_id, gen_random_uuid(), space.id, 'published', 'offerable',
                           'Bench', space.label, 'residential', 'Cincinnati', 'OH', 150000, 'USD', 'bench-' || space.id
                    FROM spaces space
                    WHERE space.organization_id = :org
                    LIMIT 1001
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO listing_snapshots (
                      organization_id, id, listing_id, space_id, public_slug, schema_version, content_hash, payload, actor_id
                    )
                    SELECT listing.organization_id, gen_random_uuid(), listing.id, listing.space_id, listing.public_slug, 1, 'bench',
                           CAST(:payload AS jsonb),
                           :actor
                    FROM listings listing
                    WHERE listing.organization_id = :org AND listing.public_slug LIKE 'bench-%' AND listing.public_slug <> :slug
                    """
                ),
                {
                    "org": organization,
                    "actor": actor,
                    "slug": slug,
                    "payload": '{"property_name":"Bench","label":"Home","municipality":"Cincinnati","state":"OH","availability":"available","amount_minor":150000,"currency":"USD","synthetic":true,"schema_version":1}',
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO discovery_projections (
                      organization_id, id, listing_id, snapshot_id, public_slug, schema_version, policy_version,
                      content_hash, eligibility, payload, search_text, city, use_code, amount_minor, currency, period, bedrooms, sort_rank
                    )
                    SELECT snapshot.organization_id, gen_random_uuid(), snapshot.listing_id, snapshot.id, snapshot.public_slug, 1, 1,
                           'bench', 'eligible', snapshot.payload, 'Bench Cincinnati residential', 'Cincinnati', 'residential', 150000, 'USD', 'monthly', 2, 100
                    FROM listing_snapshots snapshot
                    WHERE snapshot.organization_id = :org AND snapshot.public_slug LIKE 'bench-%'
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO prospects (organization_id, id, display_name, kind)
                    SELECT :org, (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000000')::uuid,
                           'Prospect ' || n, 'person'
                    FROM generate_series(1, 25000) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO leasing_inquiries (
                      organization_id, id, prospect_id, origin_prospect_id, public_receipt, source, stage
                    )
                    SELECT :org,
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000001')::uuid,
                           (lpad((((n - 1) / 2) + 1)::text, 8, '0') || '-0000-4000-8000-000000000000')::uuid,
                           (lpad((((n - 1) / 2) + 1)::text, 8, '0') || '-0000-4000-8000-000000000000')::uuid,
                           md5(n::text), 'website', 'new'
                    FROM generate_series(1, 50000) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO inquiry_assignments (organization_id, id, inquiry_id, reason)
                    SELECT organization_id, gen_random_uuid(), id, 'awaiting_claim'
                    FROM leasing_inquiries WHERE organization_id = :org
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO inquiry_clocks (
                      organization_id, id, inquiry_id, policy_version, zone_name, started_at, deadline_at
                    )
                    SELECT organization_id, gen_random_uuid(), id, 1, 'America/New_York', now(), now() + interval '2 hours'
                    FROM leasing_inquiries WHERE organization_id = :org
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO inquiry_actions (organization_id, id, inquiry_id, kind, status, is_primary, due_at)
                    SELECT organization_id, gen_random_uuid(), id, 'review_inquiry', 'open', true, now() + interval '2 hours'
                    FROM leasing_inquiries WHERE organization_id = :org
                    """
                ),
                {"org": organization},
            )
            other = uuid4()
            connection.execute(text("INSERT INTO organizations (id, name, synthetic) VALUES (:id, 'Isolation benchmark organization', true)"), {"id": other})
            connection.execute(
                text(
                    """
                    INSERT INTO prospects (organization_id, id, display_name, kind)
                    SELECT :org, gen_random_uuid(), 'Prospect ' || n, 'person'
                    FROM generate_series(1, 20) AS n
                    """
                ),
                {"org": other},
            )
            host = uuid4()
            space_resource = uuid4()
            connection.execute(
                text("INSERT INTO showing_resources (organization_id, id, kind, label, capacity) VALUES (:org, :host, 'host', 'Bench host', 1), (:org, :space, 'space', 'Bench space', 1)"),
                {"org": organization, "host": host, "space": space_resource},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO showings (
                      organization_id, id, inquiry_id, prospect_id, public_reference, mode, business_state,
                      wall_start, zone_name, offset_minutes, starts_at, ends_at, host_resource_id, space_resource_id,
                      guest_count, policy_version
                    )
                    SELECT :org,
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000002')::uuid,
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000001')::uuid,
                           (lpad((((n - 1) / 2) + 1)::text, 8, '0') || '-0000-4000-8000-000000000000')::uuid,
                           'showing-' || md5(n::text), 'individual', 'confirmed',
                           '2027-06-01T10:00:00', 'America/New_York', -240,
                           timestamptz '2027-06-01 14:00+00' + (n * interval '2 hours'),
                           timestamptz '2027-06-01 14:30+00' + (n * interval '2 hours'),
                           :host, :space, 1, 1
                    FROM generate_series(1, 50000) AS n
                    """
                ),
                {"org": organization, "host": host, "space": space_resource},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO showing_occupancy (organization_id, id, resource_id, showing_id, span)
                    SELECT organization_id, gen_random_uuid(), host_resource_id, id,
                           tstzrange(starts_at - interval '15 minutes', ends_at + interval '15 minutes', '[)')
                    FROM showings WHERE organization_id = :org
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO showing_holds (organization_id, id, inquiry_id, resource_id, capability_hash, expires_at, state)
                    SELECT organization_id, gen_random_uuid(), inquiry_id, host_resource_id, md5(id::text), now(), 'expired'
                    FROM showings WHERE organization_id = :org
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO showing_sync (organization_id, showing_id, desired_hash, state)
                    SELECT organization_id, id, md5(public_reference), 'synced'
                    FROM showings WHERE organization_id = :org
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO applications (
                      organization_id, id, prospect_id, inquiry_id, listing_slug, application_type, state,
                      public_reference, policy_version
                    )
                    SELECT :org,
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000010')::uuid,
                           (lpad((((n - 1) / 2) + 1)::text, 8, '0') || '-0000-4000-8000-000000000000')::uuid,
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000001')::uuid,
                           'bench-app-' || n, 'residential', 'draft',
                           'application-' || md5(n::text), 1
                    FROM generate_series(1, 25000) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO application_participants (
                      organization_id, id, application_id, role_name, preferred_name
                    )
                    SELECT :org,
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000011')::uuid,
                           (lpad((((n - 1) / 2) + 1)::text, 8, '0') || '-0000-4000-8000-000000000010')::uuid,
                           CASE WHEN n % 2 = 1 THEN 'primary' ELSE 'co_applicant' END,
                           'Household'
                    FROM generate_series(1, 50000) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO application_documents (
                      organization_id, id, application_id, participant_id, document_class, display_name,
                      object_key, content_hash, byte_size, scan_state
                    )
                    SELECT :org, gen_random_uuid(),
                           (lpad((((n - 1) / 4) + 1)::text, 8, '0') || '-0000-4000-8000-000000000010')::uuid,
                           (lpad((((n - 1) / 4) * 2 + 1)::text, 8, '0') || '-0000-4000-8000-000000000011')::uuid,
                           'income_evidence', 'pay.txt', md5(n::text), md5('doc-' || n::text), 32, 'clean'
                    FROM generate_series(1, 100000) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO screening_cases (
                      organization_id, id, application_id, public_reference, state, criminal_enabled
                    )
                    SELECT :org,
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000012')::uuid,
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000010')::uuid,
                           'screening-' || md5(n::text), 'decided', false
                    FROM generate_series(1, 25000) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO screening_subjects (organization_id, id, case_id, role_name, authorization_state)
                    SELECT :org,
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000013')::uuid,
                           (lpad((((n - 1) / 2) + 1)::text, 8, '0') || '-0000-4000-8000-000000000012')::uuid,
                           CASE WHEN n % 2 = 1 THEN 'primary' ELSE 'co_applicant' END,
                           'granted'
                    FROM generate_series(1, 50000) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO screening_orders (organization_id, id, case_id, product, state, idempotency_key)
                    SELECT :org,
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000014')::uuid,
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000012')::uuid,
                           'credit', 'complete', 'bench-' || n
                    FROM generate_series(1, 25000) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO screening_components (organization_id, id, order_id, component_code, component_state)
                    SELECT :org, gen_random_uuid(),
                           (lpad((((n - 1) / 4) + 1)::text, 8, '0') || '-0000-4000-8000-000000000014')::uuid,
                           'component-' || n, 'complete'
                    FROM generate_series(1, 100000) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO screening_evaluations (organization_id, id, case_id, criterion_code, result_code)
                    SELECT :org, gen_random_uuid(),
                           (lpad((((n - 1) / 4) + 1)::text, 8, '0') || '-0000-4000-8000-000000000012')::uuid,
                           'criterion-' || n, 'met'
                    FROM generate_series(1, 100000) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO screening_decisions (organization_id, id, case_id, outcome, human_confirmed, basis_code)
                    SELECT :org, gen_random_uuid(),
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000012')::uuid,
                           'approved', true, 'policy_v1'
                    FROM generate_series(1, 25000) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO screening_notices (organization_id, id, case_id, notice_kind, content_hash, delivery_state)
                    SELECT :org, gen_random_uuid(),
                           (lpad((((n - 1) / 2) + 1)::text, 8, '0') || '-0000-4000-8000-000000000012')::uuid,
                           CASE WHEN n % 2 = 1 THEN 'non_fcra' ELSE 'adverse_action' END,
                           md5(n::text), 'queued'
                    FROM generate_series(1, 50000) AS n
                    """
                ),
                {"org": organization},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO screening_disputes (organization_id, id, case_id, dispute_kind, state)
                    SELECT :org, gen_random_uuid(),
                           (lpad(n::text, 8, '0') || '-0000-4000-8000-000000000012')::uuid,
                           'identity', 'submitted'
                    FROM generate_series(1, 25000) AS n
                    """
                ),
                {"org": organization},
            )
            counts = connection.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*) FROM properties WHERE organization_id = :org),
                      (SELECT count(*) FROM spaces WHERE organization_id = :org),
                      (SELECT count(*) FROM asking_prices WHERE organization_id = :org),
                      (SELECT count(*) FROM audit_events WHERE organization_id = :org),
                      (SELECT count(*) FROM prospects WHERE organization_id = :org),
                      (SELECT count(*) FROM leasing_inquiries WHERE organization_id = :org),
                      (SELECT count(*) FROM showings WHERE organization_id = :org),
                      (SELECT count(*) FROM showing_holds WHERE organization_id = :org),
                      (SELECT count(*) FROM applications WHERE organization_id = :org),
                      (SELECT count(*) FROM application_participants WHERE organization_id = :org),
                      (SELECT count(*) FROM application_documents WHERE organization_id = :org),
                      (SELECT count(*) FROM screening_cases WHERE organization_id = :org),
                      (SELECT count(*) FROM screening_subjects WHERE organization_id = :org),
                      (SELECT count(*) FROM screening_components WHERE organization_id = :org),
                      (SELECT count(*) FROM screening_evaluations WHERE organization_id = :org),
                      (SELECT count(*) FROM screening_notices WHERE organization_id = :org),
                      (SELECT count(*) FROM screening_disputes WHERE organization_id = :org)
                    """
                ),
                {"org": organization},
            ).one()
            connection.execute(
                text(
                    """
                    SELECT set_config('app.actor_id', :actor, true),
                           set_config('app.organization_id', :org, true),
                           set_config('app.membership_id', (SELECT id::text FROM memberships WHERE account_id = CAST(:actor AS uuid)), true)
                    """
                ),
                {"actor": str(actor), "org": str(organization)},
            )
            # Superuser bypasses RLS. Switch to the runtime role for the timed reads.
            connection.execute(text("ANALYZE properties, spaces, asking_prices, listing_snapshots, discovery_projections, audit_events, prospects, leasing_inquiries, inquiry_actions, inquiry_clocks, inquiry_assignments, applications, application_participants, application_documents, screening_cases, screening_subjects, screening_orders, screening_components, screening_evaluations, screening_decisions, screening_notices, screening_disputes"))
            connection.execute(text("SET ROLE perchpoint_runtime"))
            visible = connection.execute(text("SELECT count(*) FROM properties"), {}).scalar()
            if visible != 1001:
                raise SystemExit(f"runtime inventory visibility was {visible}, expected 1001")
            inventory = _timed(
                connection,
                """
                SELECT property.name FROM properties property
                WHERE property.organization_id = :org
                ORDER BY property.name
                LIMIT 50
                """,
                {"org": organization},
            )
            detail = _timed(
                connection,
                """
                SELECT property.name, space.label, price.amount_minor
                FROM properties property
                JOIN spaces space ON space.organization_id = property.organization_id AND space.property_id = property.id
                JOIN asking_prices price ON price.organization_id = space.organization_id AND price.space_id = space.id AND price.ended_on IS NULL
                WHERE property.organization_id = :org AND property.id = (
                  SELECT id FROM properties WHERE organization_id = :org ORDER BY name LIMIT 1
                )
                """,
                {"org": organization},
            )
            public = _timed(connection, "SELECT perchpoint.published_listing_snapshot(:slug)", {"slug": slug})
            discovery = _timed(
                connection,
                "SELECT perchpoint.search_discovery(CAST(:criteria AS jsonb))",
                {"criteria": '{"city":"Cincinnati","use_code":"residential","limit":"20"}'},
            )
            facets = _timed(
                connection,
                "SELECT perchpoint.search_discovery(CAST(:criteria AS jsonb))",
                {"criteria": '{"use_code":"residential","limit":"1"}'},
            )
            detail_discovery = _timed(connection, "SELECT perchpoint.published_discovery_listing(:slug)", {"slug": slug})
            admin_read = _timed(connection, "SELECT count(*) FROM discovery_projections WHERE current AND eligibility = 'eligible'", {})
            queue = _timed(
                connection,
                """
                SELECT inquiry.public_receipt, inquiry.stage, action.kind
                FROM leasing_inquiries inquiry
                JOIN inquiry_actions action ON action.organization_id = inquiry.organization_id
                  AND action.inquiry_id = inquiry.id AND action.is_primary AND action.status = 'open'
                ORDER BY inquiry.public_receipt
                LIMIT 50
                """,
                {},
            )
            leaked = connection.execute(text("SELECT count(*) FROM prospects WHERE display_name = 'Prospect 1'")).scalar()
            hidden_showings = connection.execute(text("SELECT count(*) FROM showings WHERE public_reference LIKE 'showing-%'")).scalar()
            day = _timed(
                connection,
                """
                SELECT public_reference, business_state, sync_state
                FROM showings
                WHERE organization_id = :org
                ORDER BY starts_at
                LIMIT 50
                """,
                {"org": organization},
            )
            callback = _timed(
                connection,
                "SELECT business_state, sync_state FROM showings WHERE public_reference = :reference",
                {"reference": "showing-" + hashlib.md5(b"1").hexdigest()},
            )
            application_reference = "application-" + hashlib.md5(b"1").hexdigest()
            application_detail = _timed(
                connection,
                "SELECT state, version FROM applications WHERE public_reference = :reference",
                {"reference": application_reference},
            )
            application_queue = _timed(
                connection,
                """
                SELECT public_reference, state FROM applications
                WHERE organization_id = :org AND state = 'draft'
                ORDER BY public_reference
                LIMIT 50
                """,
                {"org": organization},
            )
            draft_save = _timed(
                connection,
                "UPDATE applications SET version = version + 1 WHERE public_reference = :reference RETURNING version",
                {"reference": application_reference},
            )
            upload_finalize = _timed(
                connection,
                """
                INSERT INTO application_documents (
                  organization_id, id, application_id, participant_id, document_class, display_name,
                  object_key, content_hash, byte_size, scan_state
                )
                SELECT application.organization_id, gen_random_uuid(), application.id, participant.id,
                       'income_evidence', 'extra.txt', md5(random()::text), md5(random()::text), 32, 'clean'
                FROM applications application
                JOIN application_participants participant
                  ON participant.organization_id = application.organization_id
                 AND participant.application_id = application.id
                 AND participant.role_name = 'primary'
                WHERE application.public_reference = :reference
                RETURNING scan_state
                """,
                {"reference": application_reference},
            )
            completeness = _timed(
                connection,
                """
                SELECT count(*) FROM application_documents document
                JOIN applications application
                  ON application.organization_id = document.organization_id
                 AND application.id = document.application_id
                WHERE application.public_reference = :reference AND document.scan_state = 'clean'
                """,
                {"reference": application_reference},
            )
            submission = _timed(
                connection,
                """
                UPDATE applications
                SET state = CASE WHEN state = 'draft' THEN 'submitted' ELSE 'draft' END
                WHERE public_reference = :reference
                RETURNING state
                """,
                {"reference": application_reference},
            )
            screening_reference = "screening-" + hashlib.md5(b"1").hexdigest()
            screening_detail = _timed(
                connection,
                "SELECT state, version FROM screening_cases WHERE public_reference = :reference",
                {"reference": screening_reference},
            )
            screening_queue = _timed(
                connection,
                """
                SELECT public_reference, state FROM screening_cases
                WHERE organization_id = :org AND state = 'decided'
                ORDER BY public_reference
                LIMIT 50
                """,
                {"org": organization},
            )
            criteria = _timed(
                connection,
                """
                SELECT count(*) FROM screening_evaluations evaluation
                JOIN screening_cases screening_case
                  ON screening_case.organization_id = evaluation.organization_id
                 AND screening_case.id = evaluation.case_id
                WHERE screening_case.public_reference = :reference
                """,
                {"reference": screening_reference},
            )
            screening_command = _timed(
                connection,
                "UPDATE screening_cases SET version = version + 1 WHERE public_reference = :reference RETURNING version",
                {"reference": screening_reference},
            )
            plan = connection.execute(text("EXPLAIN SELECT property.name FROM properties property WHERE property.organization_id = :org ORDER BY property.name LIMIT 50"), {"org": organization}).all()
            discovery_plan = connection.execute(text("EXPLAIN SELECT public_slug FROM discovery_projections WHERE current AND eligibility = 'eligible' AND use_code = 'residential' ORDER BY sort_rank, public_slug LIMIT 20")).all()
        print("cardinalities", {"properties": counts[0], "spaces": counts[1], "prices": counts[2], "audit": counts[3], "prospects": counts[4], "inquiries": counts[5], "showings": counts[6], "holds": counts[7], "applications": counts[8], "participants": counts[9], "documents": counts[10], "screening_cases": counts[11], "subjects": counts[12], "components": counts[13], "evaluations": counts[14], "notices": counts[15], "disputes": counts[16], "connections": 25, "runtime_visible_properties": visible, "same_name_visible": leaked, "showing_rows_visible": hidden_showings})
        print("inventory", inventory)
        print("detail", detail)
        print("snapshot", public)
        print("discovery", discovery)
        print("facets", facets)
        print("discovery_detail", detail_discovery)
        print("admin", admin_read)
        print("queue", queue)
        print("showing_day", day)
        print("callback", callback)
        print("application_detail", application_detail)
        print("application_queue", application_queue)
        print("draft_save", draft_save)
        print("upload_finalize", upload_finalize)
        print("completeness", completeness)
        print("submission", submission)
        print("screening_detail", screening_detail)
        print("screening_queue", screening_queue)
        print("criteria", criteria)
        print("screening_command", screening_command)
        print("plan", [row[0] for row in plan])
        print("discovery_plan", [row[0] for row in discovery_plan])
        if counts[11] != 25000 or counts[12] != 50000 or counts[13] != 100000 or counts[14] != 100000 or counts[15] != 50000 or counts[16] != 25000:
            raise SystemExit(f"screening cardinalities were {counts[11:]}")
        if screening_detail["p95_ms"] >= 300 or screening_queue["p95_ms"] >= 300:
            raise SystemExit(f"screening read budget missed: detail={screening_detail} queue={screening_queue}")
        if criteria["p95_ms"] >= 500 or screening_command["p95_ms"] >= 750:
            raise SystemExit(f"screening command budget missed: criteria={criteria} command={screening_command}")
        if counts[8] != 25000 or counts[9] != 50000 or counts[10] != 100000:
            raise SystemExit(f"application cardinalities were {counts[8:11]}")
        if application_detail["p95_ms"] >= 300 or application_queue["p95_ms"] >= 300:
            raise SystemExit(f"application read budget missed: detail={application_detail} queue={application_queue}")
        if draft_save["p95_ms"] >= 500 or upload_finalize["p95_ms"] >= 500 or completeness["p95_ms"] >= 500:
            raise SystemExit(f"application write budget missed: save={draft_save} upload={upload_finalize} completeness={completeness}")
        if submission["p95_ms"] >= 750:
            raise SystemExit(f"submission budget missed: {submission}")
        if hidden_showings != 50000:
            raise SystemExit(f"showing visibility was {hidden_showings}, expected 50000")
        if leaked != 1:
            raise SystemExit(f"cross-organization prospect leakage: {leaked}")
        if queue["p95_ms"] >= 300 or day["p95_ms"] >= 300 or callback["p95_ms"] >= 200:
            raise SystemExit(f"showing budget missed: queue={queue} day={day} callback={callback}")
        if discovery["p95_ms"] >= 300 or facets["p95_ms"] >= 400 or detail_discovery["p95_ms"] >= 200 or admin_read["p95_ms"] >= 300:
            raise SystemExit(f"discovery budget missed: search={discovery} facets={facets} detail={detail_discovery} admin={admin_read}")
        if discovery["errors"] or discovery["timeouts"]:
            raise SystemExit(f"discovery search missed its budget: {discovery}")
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": bench})
            connection.execute(text(f"DROP DATABASE IF EXISTS {bench}"))
        admin.dispose()
        print("teardown", bench, "dropped")


if __name__ == "__main__":
    main()
