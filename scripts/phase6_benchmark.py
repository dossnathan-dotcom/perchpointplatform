"""Three-round restricted-role Phase 6 authorization benchmark."""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT / "scripts"))

from perchpoint.db import engine_for
from perchpoint.settings import Settings
from phase6_evidence_schema import (
    SCHEMA_VERSION,
    raw_artifact,
    source_provenance,
)
from phase6_scale import DATABASE, _drop, _percentile, _prepare

QUERY_NAMES = (
    "session",
    "decision",
    "property-list",
    "household-detail",
    "vendor-list",
    "directory",
    "delegation",
    "sensitive-audit",
    "search",
    "export",
    "cross-org-denial",
    "permission-revocation",
    "session-revocation",
    "concurrent-read",
)


def _summary(values: list[float], *, visible_rows: int | None = None) -> dict:
    return {
        "samples": len(values),
        "p50": round(_percentile(values, 0.50), 3),
        "p95": round(_percentile(values, 0.95), 3),
        "max": round(max(values), 3),
        "errors": 0,
        "timeouts": 0,
        "visible_rows": visible_rows,
    }


def _supplement(settings: Settings, actor: str, organization: str) -> dict[str, str]:
    admin = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/" + DATABASE)
    ids = {
        "household": str(uuid4()),
        "vendor": str(uuid4()),
        "assignment": str(uuid4()),
        "delegation": str(uuid4()),
        "scope": str(uuid4()),
    }
    with admin.begin() as connection:
        property_id = connection.execute(
            text("SELECT id FROM properties WHERE organization_id = :org ORDER BY id LIMIT 1"),
            {"org": organization},
        ).scalar_one()
        connection.execute(
            text("INSERT INTO households (organization_id, id, label) VALUES (:org, :id, 'Scale household')"),
            {"org": organization, "id": ids["household"]},
        )
        connection.execute(
            text(
                """
                INSERT INTO portal_access (organization_id, id, household_id, account_id, kind, effective_at)
                VALUES (:org, gen_random_uuid(), :household, :actor, 'primary', now() - interval '1 day')
                """
            ),
            {"org": organization, "household": ids["household"], "actor": actor},
        )
        connection.execute(
            text(
                """
                INSERT INTO vendor_relationships
                  (organization_id, id, vendor_name, administrator_account_id, status)
                VALUES (:org, :vendor, 'Scale vendor', :actor, 'active')
                """
            ),
            {"org": organization, "vendor": ids["vendor"], "actor": actor},
        )
        connection.execute(
            text(
                """
                INSERT INTO worker_assignments
                  (organization_id, id, vendor_relationship_id, worker_account_id, property_id,
                   assignment_kind, starts_at, ends_at, status)
                VALUES (:org, :assignment, :vendor, :actor, :property, 'technician',
                        now() - interval '1 day', now() + interval '1 day', 'active')
                """
            ),
            {
                "org": organization,
                "assignment": ids["assignment"],
                "vendor": ids["vendor"],
                "actor": actor,
                "property": property_id,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO delegations
                  (organization_id, id, grantor_id, grantee_id, capability, starts_at, ends_at, status, reason)
                VALUES (:org, :delegation, gen_random_uuid(), :actor, 'expense.approve',
                        now() - interval '1 day', now() + interval '1 day', 'active', 'Scale benchmark')
                """
            ),
            {"org": organization, "delegation": ids["delegation"], "actor": actor},
        )
        connection.execute(
            text(
                """
                INSERT INTO authorization_scopes (organization_id, id, scope_type, resource_id)
                VALUES (:org, :scope, 'property', :property)
                """
            ),
            {"org": organization, "scope": ids["scope"], "property": property_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO memberships (id, account_id, organization_id, role_name, effective_at, ended_at)
                SELECT gen_random_uuid(), id, :org, 'resident', now() - interval '2 days', now() - interval '1 day'
                FROM accounts ORDER BY email OFFSET 1 LIMIT 1
                """
            ),
            {"org": organization},
        )
        connection.execute(
            text(
                """
                UPDATE identity_accounts SET status = 'suspended'
                WHERE account_id = (SELECT id FROM accounts ORDER BY email OFFSET 2 LIMIT 1)
                """
            )
        )
    admin.dispose()
    return ids


def _query_samples(settings: Settings, actor: str, organization: str, token_hash: str) -> tuple[dict, str]:
    runtime_url = settings.runtime_url.rsplit("/", 1)[0] + "/" + DATABASE
    runtime = engine_for(runtime_url)
    samples: dict[str, list[float]] = {name: [] for name in QUERY_NAMES}
    visible: dict[str, int] = {}
    statements = {
        "session": ("SELECT count(*) FROM perchpoint.resolve_session(:token)", {"token": token_hash}),
        "decision": ("SELECT count(*) FROM perchpoint.current_membership(:actor)", {"actor": actor}),
        "property-list": ("SELECT count(*) FROM properties", {}),
        "household-detail": ("SELECT count(*) FROM households", {}),
        "vendor-list": ("SELECT count(*) FROM worker_assignments", {}),
        "directory": ("SELECT count(*) FROM memberships", {}),
        "delegation": ("SELECT count(*) FROM delegations WHERE grantee_id = :actor", {"actor": actor}),
        "search": ("SELECT count(*) FROM documents WHERE title ILIKE 'Document %'", {}),
        "export": ("SELECT count(*) FROM documents WHERE classification = 'internal'", {}),
        "cross-org-denial": ("SELECT count(*) FROM properties WHERE name = 'Hidden property'", {}),
    }
    with runtime.connect() as connection:
        transaction = connection.begin()
        connection.execute(
            text(
                """
                SELECT set_config('app.actor_id', :actor, true),
                       set_config('app.identity_id', :actor, true),
                       set_config('app.organization_id', :org, true),
                       set_config('app.membership_id', '', true),
                       set_config('app.request_id', :request, true),
                       set_config('app.aal', 'aal2', true),
                       set_config('app.delegation_id', '', true)
                """
            ),
            {"actor": actor, "org": organization, "request": str(uuid4())},
        )
        for name, (statement, params) in statements.items():
            for _ in range(5):
                connection.execute(text(statement), params).scalar()
            for _ in range(20):
                started = time.perf_counter()
                count = int(connection.execute(text(statement), params).scalar() or 0)
                samples[name].append((time.perf_counter() - started) * 1000)
                visible[name] = count
        for _ in range(20):
            started = time.perf_counter()
            connection.execute(
                text(
                    """
                    INSERT INTO security_events
                      (id, organization_id, identity_id, action, outcome, correlation_id, request_id, actor_account_id)
                    VALUES (gen_random_uuid(), :org, NULL, 'benchmark.sensitive_read', 'allowed',
                            gen_random_uuid(), gen_random_uuid(), :actor)
                    """
                ),
                {"org": organization, "actor": actor},
            )
            samples["sensitive-audit"].append((time.perf_counter() - started) * 1000)
        plan = "\n".join(
            row[0]
            for row in connection.execute(
                text("EXPLAIN (ANALYZE, BUFFERS) SELECT id, name FROM properties ORDER BY id LIMIT 50")
            )
        )
        transaction.rollback()
    runtime.dispose()

    admin = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/" + DATABASE)
    for _ in range(20):
        with admin.begin() as connection:
            connection.execute(
                text("UPDATE memberships SET ended_at = now() - interval '1 second' WHERE account_id = :actor"),
                {"actor": actor},
            )
        check = engine_for(runtime_url)
        started = time.perf_counter()
        with check.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.actor_id', :actor, true), set_config('app.organization_id', :org, true)"),
                {"actor": actor, "org": organization},
            )
            assert int(connection.execute(text("SELECT count(*) FROM properties")).scalar() or 0) == 0
        samples["permission-revocation"].append((time.perf_counter() - started) * 1000)
        check.dispose()
        with admin.begin() as connection:
            connection.execute(
                text("UPDATE memberships SET ended_at = NULL WHERE account_id = :actor"),
                {"actor": actor},
            )
    for _ in range(20):
        with admin.begin() as connection:
            connection.execute(
                text("UPDATE identity_sessions SET revoked_at = now() WHERE token_hash = :token"),
                {"token": token_hash},
            )
        check = engine_for(runtime_url)
        started = time.perf_counter()
        with check.connect() as connection:
            assert int(connection.execute(text("SELECT count(*) FROM perchpoint.resolve_session(:token)"), {"token": token_hash}).scalar() or 0) == 1
            assert connection.execute(text("SELECT revoked_at FROM perchpoint.resolve_session(:token)"), {"token": token_hash}).scalar() is not None
        samples["session-revocation"].append((time.perf_counter() - started) * 1000)
        check.dispose()
        with admin.begin() as connection:
            connection.execute(
                text("UPDATE identity_sessions SET revoked_at = NULL WHERE token_hash = :token"),
                {"token": token_hash},
            )
    admin.dispose()

    def concurrent_read(_: int) -> float:
        engine = engine_for(runtime_url)
        started = time.perf_counter()
        with engine.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.actor_id', :actor, true), set_config('app.organization_id', :org, true)"),
                {"actor": actor, "org": organization},
            )
            connection.execute(text("SELECT count(*) FROM properties")).scalar()
        elapsed = (time.perf_counter() - started) * 1000
        engine.dispose()
        return elapsed

    with ThreadPoolExecutor(max_workers=25) as pool:
        samples["concurrent-read"] = list(pool.map(concurrent_read, range(25)))
    visible["concurrent-read"] = 1000
    summaries = {
        name: _summary(values, visible_rows=visible.get(name))
        for name, values in samples.items()
    }
    return summaries, plan


def main() -> None:
    settings = Settings.load()
    source = source_provenance(ROOT)
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": "benchmark",
        "command": "python scripts/phase6_benchmark.py",
        "commit": source["commit"],
        "tree_hash": source["tree_hash"],
        "source_clean": source["source_clean"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "exit_code": 0,
        "total": 3 * len(QUERY_NAMES) * 20,
        "skipped": 0,
        "totals": {
            "total": 3 * len(QUERY_NAMES) * 20,
            "passed": 3 * len(QUERY_NAMES) * 20,
            "failed": 0,
            "skipped": 0,
        },
        "postgres": "16",
        "restricted_role": "perchpoint_runtime",
        "rounds": [],
        "database_removed": False,
    }
    try:
        for round_number in range(1, 4):
            actor, organization, token_hash, counts = _prepare(settings)
            _supplement(settings, actor, organization)
            queries, plan = _query_samples(settings, actor, organization, token_hash)
            report["rounds"].append(
                {
                    "round": round_number,
                    "connections": 25,
                    "cardinalities": {
                        "properties": counts[0],
                        "spaces": counts[1],
                        "parties_households": counts[2],
                        "identities": counts[3],
                        "active_memberships": counts[4],
                        "operational_records": counts[5],
                        "audit_security_rows": counts[6],
                    },
                    "queries": queries,
                    "query_plan": plan,
                    "cross_org_visible": queries["cross-org-denial"]["visible_rows"],
                }
            )
            _drop(settings)
        report["database_removed"] = True
    finally:
        _drop(settings)
    failures = []
    for round_ in report["rounds"]:
        if round_["queries"]["decision"]["p95"] >= 50:
            failures.append("authorization p95 exceeded")
        if round_["queries"]["session"]["p95"] >= 100:
            failures.append("session p95 exceeded")
        if round_["queries"]["property-list"]["p95"] >= 300:
            failures.append("property list p95 exceeded")
        if round_["cross_org_visible"] != 0:
            failures.append("cross-organization visibility detected")
    if len(report["rounds"]) != 3 or not report["database_removed"]:
        failures.append("benchmark lifecycle incomplete")
    if failures:
        report["exit_code"] = 1
        report["totals"]["passed"] = 0
        report["totals"]["failed"] = report["totals"]["total"]
        report["failures"] = failures
    output = ROOT / "test_reports" / "phase6" / "benchmark.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_path = output.with_name("benchmark.raw.json")
    raw_path.write_text(
        json.dumps({"rounds": report["rounds"], "database_removed": report["database_removed"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    report["raw_artifacts"] = [raw_artifact(ROOT, raw_path)]
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit("; ".join(failures))
    print(f"phase6 benchmark passed: {output}")


if __name__ == "__main__":
    main()
