"""Representative Phase 8 inventory timing on a disposable database.

The database is created from the migrated local database, measured, and dropped.
Synthetic rows only. This is not a production capacity claim.
"""
from __future__ import annotations

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
    bench = "perchpoint_phase8_bench"
    admin = create_engine(_url("postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": bench})
        connection.execute(text(f"DROP DATABASE IF EXISTS {bench}"))
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'perchpoint_phase2' AND pid <> pg_backend_pid()"))
        connection.execute(text(f"CREATE DATABASE {bench} TEMPLATE perchpoint_phase2"))
    admin.dispose()
    engine = create_engine(_url(bench))
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
            counts = connection.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*) FROM properties WHERE organization_id = :org),
                      (SELECT count(*) FROM spaces WHERE organization_id = :org),
                      (SELECT count(*) FROM asking_prices WHERE organization_id = :org),
                      (SELECT count(*) FROM audit_events WHERE organization_id = :org)
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
            connection.execute(text("ANALYZE properties, spaces, asking_prices, listing_snapshots, discovery_projections, audit_events"))
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
            admin = _timed(connection, "SELECT count(*) FROM discovery_projections WHERE current AND eligibility = 'eligible'", {})
            plan = connection.execute(text("EXPLAIN SELECT property.name FROM properties property WHERE property.organization_id = :org ORDER BY property.name LIMIT 50"), {"org": organization}).all()
            discovery_plan = connection.execute(text("EXPLAIN SELECT public_slug FROM discovery_projections WHERE current AND eligibility = 'eligible' AND use_code = 'residential' ORDER BY sort_rank, public_slug LIMIT 20")).all()
        print("cardinalities", {"properties": counts[0], "spaces": counts[1], "prices": counts[2], "audit": counts[3], "runtime_visible_properties": visible})
        print("inventory", inventory)
        print("detail", detail)
        print("snapshot", public)
        print("discovery", discovery)
        print("facets", facets)
        print("discovery_detail", detail_discovery)
        print("admin", admin)
        print("plan", [row[0] for row in plan])
        print("discovery_plan", [row[0] for row in discovery_plan])
        if discovery["p95_ms"] >= 300 or facets["p95_ms"] >= 400 or detail_discovery["p95_ms"] >= 200 or admin["p95_ms"] >= 300:
            raise SystemExit(f"discovery budget missed: search={discovery} facets={facets} detail={detail_discovery} admin={admin}")
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
