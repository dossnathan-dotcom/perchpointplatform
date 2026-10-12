"""Representative Phase 17 payment scale on a disposable database.

The demo database on port 54339 is not cloned and is not written. Rows stay in
this container. Database timing only: API, worker-process, and browser timing
are not measured here. Thresholds are printed before the timed section.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "postgres:16@sha256:1a6ab3f5345eb6dbe04a1349529caabdb0ab09293a09590fad07b2246bfa4b54"
CONTAINER = "perchpoint-phase17-bench"
PASSWORD = "local-only-not-production"
PORT = "54341"
ADMIN = f"postgresql+psycopg://postgres:{PASSWORD}@127.0.0.1:{PORT}/postgres"
RUNTIME = f"postgresql+psycopg://perchpoint_runtime:{PASSWORD}@127.0.0.1:{PORT}/perchpoint_phase2"
MIGRATOR = f"postgresql+psycopg://perchpoint_migrator:{PASSWORD}@127.0.0.1:{PORT}/perchpoint_phase2"

CONNECTIONS = 25
ROUNDS = 3
READ_P95_MS = 300
OBLIGATIONS = 500
ORDERS = 5000
ATTEMPTS = 5000
EVENTS = 5000
ENROLLMENTS = 200
OCCURRENCES = 1000
GRANTS = 200
REFUNDS = 400
DISPUTES = 200
RECEIPTS = 1000
AUDITS = 5000
COMMANDS = 5000
RECEIVED_EVENTS = 50
REFUND_CAP_MINOR = 100_000
REFUND_REQUEST_MINOR = 20_000
HOT = "bench-hot"
CAPABILITIES = [
    "payment.read",
    "payment.pay",
    "payment.charge",
    "payment.refund",
    "payment.exception",
    "payment.configure",
]


def _run(command: list[str], *, cwd: Path = ROOT, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if check and completed.returncode:
        raise RuntimeError(f"{command[0:4]} failed with exit {completed.returncode}\n{completed.stdout[-2000:]}\n{completed.stderr[-2000:]}")
    return completed


def _psql(sql: str, database: str = "postgres") -> str:
    completed = _run(
        ["docker", "exec", CONTAINER, "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", database, "-At", "-c", sql]
    )
    return completed.stdout.strip()


def _wait_ready() -> None:
    deadline = time.time() + 60
    while time.time() < deadline:
        probe = _run(["docker", "exec", CONTAINER, "pg_isready", "-U", "postgres"], check=False)
        if probe.returncode == 0:
            print(f"ready {CONTAINER}")
            return
        time.sleep(1)
    raise RuntimeError(f"{CONTAINER} did not become ready")


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PHASE2_ADMIN_URL": ADMIN,
            "PHASE2_MIGRATOR_URL": MIGRATOR,
            "PHASE2_RUNTIME_URL": RUNTIME,
            "PHASE2_JWT_SECRET": "local-only-not-production-jwt-secret-32-plus",
            "PHASE2_DEV_PASSWORD": PASSWORD + "-password",
            "PHASE2_WEBHOOK_SECRET": PASSWORD + "-webhook",
            "PHASE3_ENVIRONMENT": "local",
            "PHASE6_ALLOW_DEV_JWT": "1",
            "PHASE6_AUTH_URL": "http://127.0.0.1:9998",
            "PHASE6_PROVIDER_JWT_SECRET": "local-only-not-production-gotrue-jwt-secret",
            "PHASE6_ALLOWED_ORIGINS": "http://127.0.0.1:3000,http://localhost:3000,http://testserver",
            "PYTHONPATH": str(ROOT / "backend"),
        }
    )
    return env


def _declare() -> None:
    print("declared_before_measure")
    print(
        f"dataset obligations={OBLIGATIONS} orders={ORDERS} attempts={ATTEMPTS} callbacks={EVENTS} "
        f"enrollments={ENROLLMENTS} occurrences={OCCURRENCES} payer_grants={GRANTS} refunds={REFUNDS} "
        f"disputes={DISPUTES} receipts={RECEIPTS} audits={AUDITS} commands={COMMANDS} "
        f"received_callbacks={RECEIVED_EVENTS}"
    )
    print(
        f"thresholds connections={CONNECTIONS} rounds={ROUNDS} read_p95_ms<{READ_P95_MS} "
        f"refund_cap_minor={REFUND_CAP_MINOR} refund_request_minor={REFUND_REQUEST_MINOR} "
        f"active_reservations=1 expected_reservation_rejections={CONNECTIONS - 1} "
        f"reserved_refund_exposure_minor<={REFUND_CAP_MINOR}"
    )
    print("measured=database_only api=not_measured worker_process=not_measured browser=not_measured")


def _seed(admin) -> dict:
    organization = uuid4()
    foreign = uuid4()
    actor = uuid4()
    outsider = uuid4()
    denied = uuid4()
    payer = uuid4()
    hot_obligation = uuid4()
    hot_order = uuid4()
    foreign_obligation = uuid4()
    with admin.begin() as connection:
        connection.execute(
            text("INSERT INTO organizations (id, name, synthetic) VALUES (:id, :name, true), (:foreign, :foreign_name, true)"),
            {"id": organization, "name": "EXAMPLE ONLY phase17 bench", "foreign": foreign, "foreign_name": "EXAMPLE ONLY phase17 foreign"},
        )
        for principal, org, capabilities in (
            (actor, organization, CAPABILITIES),
            (outsider, foreign, CAPABILITIES),
            (denied, organization, ["session.read"]),
        ):
            connection.execute(
                text(
                    "INSERT INTO service_principals (organization_id, id, name, status, capabilities) "
                    "VALUES (:org, :id, :name, 'active', :capabilities)"
                ),
                {"org": org, "id": principal, "name": f"bench-{principal.hex[:8]}", "capabilities": capabilities},
            )
        connection.execute(
            text(
                "INSERT INTO payment_merchant_configs "
                "(organization_id, id, entity_code, environment, provider, live_enabled, resident_surcharge, zone_name, real_values_activated) "
                "VALUES (:org, :id, 'bench', 'local_fake', 'stripe', false, false, 'America/New_York', false)"
            ),
            {"org": organization, "id": uuid4()},
        )
        connection.execute(
            text(
                "INSERT INTO payment_obligations "
                "(organization_id, id, public_reference, tenancy_code, primary_account_id, category, description, amount_minor, due_on, state, currency_code) "
                "SELECT :org, gen_random_uuid(), 'obl-' || n, 'bench-spread-' || ((n % 50) + 1), :payer, 'rent', 'Synthetic bench charge', 100000, DATE '2026-10-01', 'published', 'USD' "
                "FROM generate_series(1, :count) AS n"
            ),
            {"org": organization, "payer": payer, "count": OBLIGATIONS},
        )
        connection.execute(
            text(
                "INSERT INTO payment_obligations "
                "(organization_id, id, public_reference, tenancy_code, primary_account_id, category, description, amount_minor, due_on, state, currency_code) "
                "VALUES (:org, :id, 'obl-hot', :tenancy, :payer, 'rent', 'Synthetic hot charge', 10000000, DATE '2026-10-01', 'published', 'USD')"
            ),
            {"org": organization, "id": hot_obligation, "tenancy": HOT, "payer": payer},
        )
        connection.execute(
            text(
                "INSERT INTO payment_orders "
                "(organization_id, id, public_reference, obligation_id, tenancy_code, payer_account_id, amount_minor, fee_minor, method, state, environment, idempotency_key, ledger_status) "
                "SELECT :org, gen_random_uuid(), 'pay-' || n, obligation.id, obligation.tenancy_code, :payer, 100000, 0, 'card', 'succeeded', 'local_fake', 'idem-' || n, 'posted' "
                "FROM generate_series(1, :count) AS n "
                "JOIN payment_obligations obligation ON obligation.public_reference = 'obl-' || ((n % :obligations) + 1)"
            ),
            {"org": organization, "payer": payer, "count": ORDERS, "obligations": OBLIGATIONS},
        )
        connection.execute(
            text(
                "INSERT INTO payment_orders "
                "(organization_id, id, public_reference, obligation_id, tenancy_code, payer_account_id, amount_minor, fee_minor, method, state, environment, idempotency_key, ledger_status) "
                "VALUES (:org, :id, 'pay-hot-source', :obligation, :tenancy, :payer, 10000000, 0, 'card', 'succeeded', 'local_fake', 'idem-hot-source', 'posted')"
            ),
            {"org": organization, "id": hot_order, "obligation": hot_obligation, "tenancy": HOT, "payer": payer},
        )
        connection.execute(
            text(
                "INSERT INTO payment_orders "
                "(organization_id, id, public_reference, obligation_id, tenancy_code, payer_account_id, amount_minor, fee_minor, method, state, environment, idempotency_key, ledger_status) "
                "SELECT :org, gen_random_uuid(), 'pay-race-' || n, :obligation, :tenancy, :payer, 20000, 0, 'card', 'processing', 'local_fake', 'idem-race-' || n, 'pending' "
                "FROM generate_series(1, :count) AS n"
            ),
            {"org": organization, "obligation": hot_obligation, "tenancy": HOT, "payer": payer, "count": CONNECTIONS},
        )
        connection.execute(
            text(
                "INSERT INTO payment_obligations "
                "(organization_id, id, public_reference, tenancy_code, primary_account_id, category, description, amount_minor, due_on, state, currency_code) "
                "VALUES (:org, :id, 'obl-foreign', 'foreign-only', :payer, 'rent', 'Synthetic foreign charge', 100, DATE '2026-10-01', 'published', 'USD')"
            ),
            {"org": foreign, "id": foreign_obligation, "payer": payer},
        )
        connection.execute(
            text(
                "INSERT INTO payment_orders "
                "(organization_id, id, public_reference, obligation_id, tenancy_code, payer_account_id, amount_minor, fee_minor, method, state, environment, idempotency_key, ledger_status) "
                "VALUES (:org, :id, 'pay-foreign', :obligation, 'foreign-only', :payer, 100, 0, 'card', 'succeeded', 'local_fake', 'idem-foreign', 'not_linked')"
            ),
            {"org": foreign, "id": uuid4(), "obligation": foreign_obligation, "payer": payer},
        )
        connection.execute(
            text(
                "INSERT INTO payment_attempts (organization_id, id, order_id, provider_reference, state, scenario) "
                "SELECT organization_id, gen_random_uuid(), id, 'synthetic-' || public_reference, 'succeeded', 'bench' FROM payment_orders"
            )
        )
        connection.execute(
            text(
                "INSERT INTO provider_events (organization_id, id, provider_event_id, effect_key, state, payload_kind, payload) "
                "SELECT organization_id, gen_random_uuid(), 'evt-' || public_reference, 'effect-' || public_reference, "
                "CASE WHEN row_number() OVER (ORDER BY public_reference) <= :received THEN 'received' ELSE 'applied' END, "
                "'payment_intent.succeeded', '{}'::jsonb FROM payment_orders"
            ),
            {"received": RECEIVED_EVENTS},
        )
        connection.execute(
            text(
                "INSERT INTO payment_instruments (organization_id, id, payer_account_id, provider_reference, method, display_label, environment, state) "
                "SELECT :org, gen_random_uuid(), :payer, 'instrument-' || n, 'card', 'Synthetic card ' || n, 'local_fake', 'synthetic' "
                "FROM generate_series(1, :count) AS n"
            ),
            {"org": organization, "payer": payer, "count": ENROLLMENTS},
        )
        connection.execute(
            text(
                "INSERT INTO autopay_enrollments "
                "(organization_id, id, tenancy_code, payer_account_id, instrument_id, cap_minor, day_of_month, zone_name, state, policy_version) "
                "SELECT instrument.organization_id, gen_random_uuid(), 'bench-auto-' || row_number() OVER (ORDER BY instrument.provider_reference), "
                ":payer, instrument.id, 100000, 11, 'America/New_York', 'active', 'local-v1' "
                "FROM payment_instruments instrument"
            ),
            {"payer": payer},
        )
        connection.execute(
            text(
                "INSERT INTO autopay_occurrences (organization_id, id, enrollment_id, period_code, state, amount_minor, reason) "
                "SELECT enrollment.organization_id, gen_random_uuid(), enrollment.id, '2026-0' || period.n, 'scheduled', 100000, 'bench' "
                "FROM autopay_enrollments enrollment CROSS JOIN generate_series(1, 5) AS period(n)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO payer_grants (organization_id, id, tenancy_code, payer_account_id, grantor_account_id, email, state) "
                "SELECT :org, gen_random_uuid(), 'bench-grant-' || n, :payer, :actor, 'payer-' || n || '@example.invalid', 'invited' "
                "FROM generate_series(1, :count) AS n"
            ),
            {"org": organization, "payer": payer, "actor": actor, "count": GRANTS},
        )
        connection.execute(
            text(
                "INSERT INTO payer_grants (organization_id, id, tenancy_code, payer_account_id, grantor_account_id, email, state) "
                "VALUES (:org, :id, :tenancy, :payer, :actor, 'hot-payer@example.invalid', 'active')"
            ),
            {"org": organization, "id": uuid4(), "tenancy": HOT, "payer": payer, "actor": actor},
        )
        connection.execute(
            text(
                "INSERT INTO refund_cases "
                "(organization_id, id, public_reference, tenancy_code, order_id, amount_minor, reason_category, description, resident_explanation, state, idempotency_key) "
                "SELECT organization_id, gen_random_uuid(), 'refund-seed-' || public_reference, tenancy_code, id, 1000, 'resident_request', "
                "'Seeded historical refund', 'Seeded historical refund', 'failed', 'refund-seed-' || public_reference "
                "FROM payment_orders WHERE tenancy_code <> :hot ORDER BY public_reference LIMIT :count"
            ),
            {"hot": HOT, "count": REFUNDS},
        )
        connection.execute(
            text(
                "INSERT INTO processor_disputes (organization_id, id, public_reference, order_id, tenancy_code, amount_minor, reason_code, state, deadline_on) "
                "SELECT organization_id, gen_random_uuid(), 'dispute-' || public_reference, id, tenancy_code, 1000, 'card_inquiry', 'open', DATE '2026-11-01' "
                "FROM payment_orders WHERE tenancy_code <> :hot ORDER BY public_reference LIMIT :count"
            ),
            {"hot": HOT, "count": DISPUTES},
        )
        connection.execute(
            text(
                "INSERT INTO payment_receipts (organization_id, id, public_reference, order_id, payer_account_id, tenancy_code, body) "
                "SELECT organization_id, gen_random_uuid(), 'receipt-' || public_reference, id, payer_account_id, tenancy_code, "
                "'SYNTHETIC PAYMENT RECEIPT ' || public_reference FROM payment_orders WHERE tenancy_code <> :hot ORDER BY public_reference LIMIT :count"
            ),
            {"hot": HOT, "count": RECEIPTS},
        )
        connection.execute(
            text(
                "INSERT INTO payment_commands (organization_id, idempotency_key, fingerprint, public_reference) "
                "SELECT :org, 'command-' || n, 'fingerprint-' || n, 'pay-' || n FROM generate_series(1, :count) AS n"
            ),
            {"org": organization, "count": COMMANDS},
        )
        connection.execute(
            text(
                "INSERT INTO audit_events "
                "(organization_id, id, actor_id, action, resource_type, resource_id, occurred_at, correlation_id, result, event_hash, redacted) "
                "SELECT :org, gen_random_uuid(), :actor, 'payment.bench', 'payment_order', :org, now(), gen_random_uuid(), 'recorded', md5(n::text), true "
                "FROM generate_series(1, :count) AS n"
            ),
            {"org": organization, "actor": actor, "count": AUDITS},
        )
        connection.execute(
            text(
                "INSERT INTO tenancy_refund_budgets (organization_id, tenancy_code, snapshot_minor, current_minor, period_start, zone_name) "
                "VALUES (:org, :tenancy, :cap, :cap, DATE '2026-10-01', 'America/New_York')"
            ),
            {"org": organization, "tenancy": HOT, "cap": REFUND_CAP_MINOR},
        )
    return {"organization": organization, "foreign": foreign, "actor": actor, "outsider": outsider, "denied": denied, "payer": payer, "hot_order": hot_order}


def _scope(connection, organization, actor) -> None:
    connection.execute(
        text("SELECT set_config('app.organization_id', :organization, true), set_config('app.actor_id', :actor, true)"),
        {"organization": str(organization), "actor": str(actor)},
    )


def _percentile(samples: list[float], fraction: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def _read_once(engine, organization, actor, statement: str) -> float:
    started = time.perf_counter()
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET LOCAL statement_timeout = '10s'"))
            _scope(connection, organization, actor)
            connection.execute(text(statement)).scalar_one()
    return (time.perf_counter() - started) * 1000


def _measure_reads(engine, organization, actor) -> dict:
    statements = {
        "tenancy_order_count": "SELECT count(*) FROM payment_orders WHERE tenancy_code = 'bench-spread-1'",
        "received_callback_count": "SELECT count(*) FROM provider_events WHERE state = 'received'",
    }
    report = {}
    for name, statement in statements.items():
        samples = []
        errors = 0
        for _ in range(ROUNDS):
            with ThreadPoolExecutor(max_workers=CONNECTIONS) as pool:
                futures = [pool.submit(_read_once, engine, organization, actor, statement) for _ in range(CONNECTIONS)]
                for future in futures:
                    try:
                        samples.append(future.result())
                    except Exception as exc:
                        errors += 1
                        if errors == 1:
                            print(f"read_error {name} {type(exc).__name__}: {exc.__cause__ or exc}")
        report[name] = {
            "samples": len(samples),
            "p50_ms": round(_percentile(samples, 0.50), 3),
            "p95_ms": round(_percentile(samples, 0.95), 3),
            "max_ms": round(max(samples) if samples else 0, 3),
            "errors": errors,
            "timeouts": 0,
        }
        print(
            f"read {name} samples={len(samples)} p50_ms={report[name]['p50_ms']} "
            f"p95_ms={report[name]['p95_ms']} max_ms={report[name]['max_ms']} errors={errors}"
        )
    return report


def _reserve_once(engine, organization, actor, slot: int) -> str:
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET LOCAL statement_timeout = '10s'"))
                _scope(connection, organization, actor)
                connection.execute(
                    text(
                        "INSERT INTO collection_reservations (organization_id, id, obligation_id, order_id, amount_minor, state) "
                        "SELECT :org, gen_random_uuid(), obligation_id, id, amount_minor, 'active' "
                        "FROM payment_orders WHERE public_reference = :reference"
                    ),
                    {"org": organization, "reference": f"pay-race-{slot}"},
                )
        return "reserved"
    except IntegrityError:
        return "rejected"


def _refund_once(engine, organization, actor, slot: int, hot_order) -> str:
    for _attempt in range(3):
        try:
            with engine.connect() as connection:
                with connection.begin():
                    connection.execute(text("SET LOCAL statement_timeout = '10s'"))
                    _scope(connection, organization, actor)
                    connection.execute(
                        text(
                            "SELECT snapshot_minor FROM tenancy_refund_budgets "
                            "WHERE organization_id = :org AND tenancy_code = :tenancy FOR UPDATE"
                        ),
                        {"org": organization, "tenancy": HOT},
                    ).scalar_one()
                    used = connection.execute(
                        text(
                            "SELECT coalesce(sum(amount_minor), 0) FROM refund_cases "
                            "WHERE organization_id = :org AND tenancy_code = :tenancy "
                            "AND state IN ('reserved', 'owner_approved', 'succeeded', 'unknown')"
                        ),
                        {"org": organization, "tenancy": HOT},
                    ).scalar_one()
                    state = "reserved" if int(used) + REFUND_REQUEST_MINOR <= REFUND_CAP_MINOR else "owner_decision_required"
                    connection.execute(
                        text(
                            "INSERT INTO refund_cases "
                            "(organization_id, id, public_reference, tenancy_code, order_id, amount_minor, reason_category, description, resident_explanation, state, idempotency_key) "
                            "VALUES (:org, gen_random_uuid(), :reference, :tenancy, :order_id, :amount, 'resident_request', "
                            "'Concurrent bench refund', 'Concurrent bench refund', :state, :key)"
                        ),
                        {
                            "org": organization,
                            "reference": f"refund-race-{slot}",
                            "tenancy": HOT,
                            "order_id": hot_order,
                            "amount": REFUND_REQUEST_MINOR,
                            "state": state,
                            "key": f"refund-race-{slot}",
                        },
                    )
            return state
        except IntegrityError as exc:
            if "40001" in str(exc) or "40P01" in str(exc):
                continue
            return "integrity"
    return "lock_retry_exhausted"


def _count(runtime, organization, actor, statement: str) -> int:
    with runtime.connect() as connection:
        with connection.begin():
            _scope(connection, organization, actor)
            return int(connection.execute(text(statement)).scalar_one())


def _demo_still_opens() -> None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:3000", timeout=5) as response:
            print(f"demo_frontend status={response.status}")
    except Exception as exc:
        print(f"demo_frontend unavailable {type(exc).__name__}")
    names = _run(["docker", "ps", "--filter", "name=postgres", "--format", "{{.Names}}"], check=False)
    demo_name = next((item for item in names.stdout.splitlines() if "accept" in item and "bench" not in item), "")
    probe = _run(["docker", "exec", demo_name, "pg_isready", "-U", "postgres"], check=False) if demo_name else None
    print(f"demo_postgres name={demo_name or 'missing'} ready={probe is not None and probe.returncode == 0}")


def main() -> int:
    if "--execute" not in sys.argv:
        print("refusing to run without --execute")
        return 1
    _declare()
    _run(["docker", "rm", "-f", CONTAINER], check=False)
    admin = None
    runtime = None
    try:
        _run(
            [
                "docker", "run", "-d", "--name", CONTAINER,
                "-p", f"127.0.0.1:{PORT}:5432",
                "-e", "POSTGRES_USER=postgres",
                "-e", f"POSTGRES_PASSWORD={PASSWORD}",
                "-e", "POSTGRES_DB=postgres",
                IMAGE,
            ]
        )
        _wait_ready()
        for statement in (
            "CREATE ROLE perchpoint_migrator LOGIN NOBYPASSRLS NOSUPERUSER PASSWORD 'local-only-not-production'",
            "CREATE ROLE perchpoint_runtime LOGIN NOBYPASSRLS NOSUPERUSER PASSWORD 'local-only-not-production'",
            "CREATE ROLE perchpoint_definer NOLOGIN BYPASSRLS NOSUPERUSER",
            "CREATE DATABASE perchpoint_phase2",
        ):
            _psql(statement)
        _psql("GRANT CONNECT, CREATE ON DATABASE perchpoint_phase2 TO perchpoint_migrator")
        _psql("GRANT CONNECT ON DATABASE perchpoint_phase2 TO perchpoint_runtime")
        _psql("GRANT ALL ON SCHEMA public TO perchpoint_migrator", "perchpoint_phase2")
        _psql("GRANT perchpoint_definer TO perchpoint_migrator", "perchpoint_phase2")
        _run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT / "backend", env=_env())
        version = _psql("SELECT version_num FROM alembic_version", "perchpoint_phase2")
        print(f"migration_head={version}")
        if version != "0057_phase17_autopay_due":
            raise RuntimeError(f"unexpected head {version}")
        actor_acl = _psql(
            "SELECT coalesce(proacl::text, 'null') FROM pg_proc JOIN pg_namespace n ON n.oid = pronamespace "
            "WHERE n.nspname = 'perchpoint' AND proname = 'current_actor'",
            "perchpoint_phase2",
        )
        print(f"current_actor_acl={actor_acl}")
        if "perchpoint_definer=X" not in actor_acl:
            raise RuntimeError("definer cannot execute current_actor")
        admin = create_engine(ADMIN.rsplit("/", 1)[0] + "/perchpoint_phase2")
        started = time.perf_counter()
        seeded = _seed(admin)
        print(f"seed_seconds={time.perf_counter() - started:.3f}")
        counts = {
            name: _psql(f"SELECT count(*) FROM {name}", "perchpoint_phase2")
            for name in (
                "payment_obligations",
                "payment_orders",
                "payment_attempts",
                "provider_events",
                "autopay_enrollments",
                "autopay_occurrences",
                "payer_grants",
                "refund_cases",
                "processor_disputes",
                "payment_receipts",
                "audit_events",
                "payment_commands",
            )
        }
        print("seed_counts " + " ".join(f"{key}={value}" for key, value in counts.items()))
        expected = {
            "payment_obligations": OBLIGATIONS + 2,
            "payment_orders": ORDERS + 1 + CONNECTIONS + 1,
            "payment_attempts": ORDERS + 1 + CONNECTIONS + 1,
            "provider_events": ORDERS + 1 + CONNECTIONS + 1,
            "autopay_enrollments": ENROLLMENTS,
            "autopay_occurrences": OCCURRENCES,
            "payer_grants": GRANTS + 1,
            "refund_cases": REFUNDS,
            "processor_disputes": DISPUTES,
            "payment_receipts": RECEIPTS,
            "audit_events": AUDITS,
            "payment_commands": COMMANDS,
        }
        if {key: int(value) for key, value in counts.items()} != expected:
            raise RuntimeError(f"seed counts {counts} did not match {expected}")
        runtime = create_engine(RUNTIME, pool_size=CONNECTIONS, max_overflow=0)
        visible = _count(
            runtime,
            seeded["organization"],
            seeded["actor"],
            "SELECT count(*) FROM payment_orders WHERE tenancy_code = 'bench-spread-1'",
        )
        print(f"scoped_spread_orders={visible}")
        if visible < 1:
            raise RuntimeError("runtime scope saw no bench orders")
        reads = _measure_reads(runtime, seeded["organization"], seeded["actor"])
        with ThreadPoolExecutor(max_workers=CONNECTIONS) as pool:
            reservation_results = list(pool.map(lambda slot: _reserve_once(runtime, seeded["organization"], seeded["actor"], slot), range(1, CONNECTIONS + 1)))
        reserved = reservation_results.count("reserved")
        reservation_rejected = reservation_results.count("rejected")
        print(f"reservation_contention reserved={reserved} rejected={reservation_rejected} other={len(reservation_results) - reserved - reservation_rejected}")
        with ThreadPoolExecutor(max_workers=CONNECTIONS) as pool:
            refund_results = list(
                pool.map(lambda slot: _refund_once(runtime, seeded["organization"], seeded["actor"], slot, seeded["hot_order"]), range(1, CONNECTIONS + 1))
            )
        refund_reserved = refund_results.count("reserved")
        refund_review = refund_results.count("owner_decision_required")
        print(f"refund_contention reserved={refund_reserved} owner_decision_required={refund_review} other={len(refund_results) - refund_reserved - refund_review}")
        active = _count(
            runtime,
            seeded["organization"],
            seeded["actor"],
            "SELECT count(*) FROM collection_reservations WHERE state = 'active'",
        )
        exposure = _count(
            runtime,
            seeded["organization"],
            seeded["actor"],
            "SELECT coalesce(sum(amount_minor), 0) FROM refund_cases WHERE tenancy_code = 'bench-hot' "
            "AND state IN ('reserved', 'owner_approved', 'succeeded', 'unknown')",
        )
        duplicate_orders = int(_psql("SELECT count(*) FROM (SELECT idempotency_key FROM payment_orders GROUP BY organization_id, idempotency_key HAVING count(*) > 1) duplicates", "perchpoint_phase2"))
        outsider_orders = _count(runtime, seeded["foreign"], seeded["outsider"], "SELECT count(*) FROM payment_orders WHERE tenancy_code LIKE 'bench%'")
        denied_orders = _count(runtime, seeded["organization"], seeded["denied"], "SELECT count(*) FROM payment_orders")
        print(f"active_reservations={active} reserved_refund_exposure_minor={exposure} duplicate_order_keys={duplicate_orders}")
        print(f"leakage foreign_visible_bench_orders={outsider_orders} denied_capability_orders={denied_orders}")
        failures = []
        for name, item in reads.items():
            if item["errors"] or item["p95_ms"] >= READ_P95_MS:
                failures.append(name)
        if reserved != 1 or reservation_rejected != CONNECTIONS - 1 or active != 1:
            failures.append("reservations")
        if exposure > REFUND_CAP_MINOR or refund_reserved * REFUND_REQUEST_MINOR != exposure or refund_reserved + refund_review != CONNECTIONS:
            failures.append("refunds")
        if duplicate_orders or outsider_orders or denied_orders:
            failures.append("isolation")
        if failures:
            print("scale=failed " + ",".join(failures))
            return 1
        print("scale=passed")
        return 0
    finally:
        if runtime is not None:
            runtime.dispose()
        if admin is not None:
            admin.dispose()
        _run(["docker", "rm", "-f", CONTAINER], check=False)
        removed = _run(["docker", "ps", "-a", "--filter", f"name={CONTAINER}", "--format", "{{.ID}}"], check=False)
        print(f"bench_container_removed={removed.stdout.strip() == ''}")
        _demo_still_opens()


if __name__ == "__main__":
    raise SystemExit(main())
