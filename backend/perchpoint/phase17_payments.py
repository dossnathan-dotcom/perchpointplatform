"""Phase 17 payment commands. Provider calls stay on the local fake adapter. No money moves."""
from __future__ import annotations

import hashlib
import json
import os
import smtplib
from datetime import date, datetime, timezone
from email.message import EmailMessage
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .commands import CommandError
from .db import application_admin_connection, engine_for, runtime_transaction
from .demo_catalog import HOUSEHOLDS
from .phase16_ledger import _account, _positions, _post
from .phase17_policy import allowance
from .phase17_stripe import TRANSPORT, ProviderTimeout
from .settings import Settings

ZONE = "America/New_York"
RECEIPT_MARKER = "SYNTHETIC PAYMENT RECEIPT — NOT A BANK CREDIT — NO MONEY HAS MOVED"


def server_now() -> datetime:
    raw = os.environ.get("PHASE17_CLOCK", "")
    if raw and os.environ.get("PHASE3_ENVIRONMENT", "local") in {"local", "test"}:
        moment = datetime.fromisoformat(raw)
        return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _org(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _require(connection, capability: str) -> None:
    allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized.", False)


def _require_any(connection, capabilities: tuple[str, ...]) -> None:
    for capability in capabilities:
        allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
        if allowed:
            return
    raise CommandError(403, "denied", "This action is not authorized.", False)


def _fingerprint(parts: list) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode()).hexdigest()


def _replay(connection, key: str, fingerprint: str) -> dict | None:
    existing = connection.execute(
        text("SELECT fingerprint, public_reference FROM payment_commands WHERE idempotency_key = :key"),
        {"key": key},
    ).first()
    if existing is None:
        return None
    if existing.fingerprint != fingerprint:
        raise CommandError(409, "conflict", "The payment request changed and was not accepted.", False)
    return {"accepted": True, "reference": existing.public_reference, "replayed": True}


def _remember(connection, organization, key: str, fingerprint: str, reference: str) -> None:
    connection.execute(
        text(
            "INSERT INTO payment_commands (organization_id, idempotency_key, fingerprint, public_reference) "
            "VALUES (CAST(:org AS uuid), :key, :fingerprint, :reference)"
        ),
        {"org": organization, "key": key, "fingerprint": fingerprint, "reference": reference},
    )


def _email(connection) -> str:
    email = connection.execute(text("SELECT email FROM accounts WHERE id = perchpoint.current_actor()")).scalar()
    if not email:
        raise CommandError(403, "denied", "This action is not authorized.", False)
    return str(email)


def _household(tenancy_code: str) -> dict | None:
    for row in HOUSEHOLDS:
        if row["slug"] == tenancy_code:
            return row
    return None


def _primary_account(settings: Settings, email: str):
    with application_admin_connection(settings) as connection:
        return connection.execute(
            text("SELECT id FROM accounts WHERE lower(email) = lower(:email)"),
            {"email": email},
        ).scalar()


def _ensure_merchant(connection, organization) -> None:
    connection.execute(
        text(
            "INSERT INTO payment_merchant_configs "
            "(organization_id, id, entity_code, environment, provider, live_enabled, resident_surcharge, zone_name, real_values_activated) "
            "VALUES (CAST(:org AS uuid), gen_random_uuid(), 'hawkvision-llc', 'local_fake', 'stripe', false, false, :zone, false) "
            "ON CONFLICT (organization_id, entity_code) DO NOTHING"
        ),
        {"org": organization, "zone": ZONE},
    )


def _collected(connection, obligation_id) -> int:
    value = connection.execute(
        text(
            "SELECT coalesce(sum(amount_minor), 0) FROM payment_orders "
            "WHERE obligation_id = :obligation AND state = 'succeeded'"
        ),
        {"obligation": obligation_id},
    ).scalar_one()
    return int(value)


def _reserved(connection, obligation_id) -> int:
    value = connection.execute(
        text(
            "SELECT coalesce(sum(amount_minor), 0) FROM collection_reservations "
            "WHERE obligation_id = :obligation AND state = 'active'"
        ),
        {"obligation": obligation_id},
    ).scalar_one()
    return int(value)


def publish_charge(settings, actor, organization, body: dict) -> dict:
    amount = int(body["amount_minor"])
    if amount < 1:
        raise CommandError(400, "invalid", "The charge amount must be a positive minor-unit integer.", False)
    category = body.get("category") or "rent"
    if category not in {"rent", "fee", "deposit", "preactivation"}:
        raise CommandError(400, "invalid", "That charge category is not payable.", False)
    tenancy = str(body["tenancy_code"])
    description = str(body.get("description") or "").strip()
    if len(description) < 3:
        raise CommandError(400, "invalid", "Describe the obligation before publishing it.", False)
    household = _household(tenancy)
    rent_basis = int(body.get("rent_basis_minor") or (household["rent_minor"] if household else 0))
    if category == "rent" and rent_basis < 1:
        raise CommandError(409, "conflict", "A monthly rent basis is required before this charge can be refunded later.", False)
    if category == "preactivation" and body.get("account_reference"):
        raise CommandError(409, "conflict", "A pre-activation obligation stays outside the active household ledger until the tenancy is activated.", False)
    fingerprint = _fingerprint([tenancy, amount, category, description, body.get("account_reference"), body["idempotency_key"]])
    reference = f"obligation-{uuid4().hex[:16]}"
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        _ensure_merchant(connection, organization)
        replay = _replay(connection, body["idempotency_key"], fingerprint)
        if replay is not None:
            return replay
        primary = None
        if household is not None:
            primary = _primary_account(settings, household["email"])
        account_reference = body.get("account_reference") or None
        journal = None
        if account_reference:
            account = _account(connection, account_reference)
            occurrence = f"pay-{uuid4().hex[:12]}"
            connection.execute(
                text(
                    "INSERT INTO charge_schedules (organization_id, id, account_id, occurrence_code, amount_minor, category) "
                    "VALUES (CAST(:org AS uuid), gen_random_uuid(), :account_id, :occurrence, :amount, :category)"
                ),
                {
                    "org": organization,
                    "account_id": account.id,
                    "occurrence": occurrence,
                    "amount": amount,
                    "category": "fee" if category == "fee" else "rent",
                },
            )
            journal = _post(
                connection,
                organization,
                account,
                "charge",
                amount,
                [("debit", "receivable", amount), ("credit", "income", amount)],
                tenancy_code=tenancy,
            )
        if rent_basis > 0:
            moment = server_now()
            period_start = moment.astimezone(ZoneInfo(ZONE)).date().replace(day=1)
            connection.execute(
                text(
                    "INSERT INTO tenancy_refund_budgets "
                    "(organization_id, tenancy_code, snapshot_minor, current_minor, period_start, zone_name) "
                    "VALUES (CAST(:org AS uuid), :tenancy, :rent, :rent, :period, :zone) "
                    "ON CONFLICT (organization_id, tenancy_code) DO NOTHING"
                ),
                {"org": organization, "tenancy": tenancy, "rent": rent_basis, "period": period_start, "zone": ZONE},
            )
        connection.execute(
            text(
                "INSERT INTO payment_obligations "
                "(organization_id, id, public_reference, tenancy_code, account_reference, primary_account_id, category, description, amount_minor, due_on, state, currency_code) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, :tenancy, :account_reference, :primary, :category, :description, :amount, :due_on, 'published', 'USD')"
            ),
            {
                "org": organization,
                "reference": reference,
                "tenancy": tenancy,
                "account_reference": account_reference,
                "primary": primary,
                "category": category,
                "description": description,
                "amount": amount,
                "due_on": server_now().astimezone(ZoneInfo(ZONE)).date(),
            },
        )
        _remember(connection, organization, body["idempotency_key"], fingerprint, reference)
    return {
        "accepted": True,
        "reference": reference,
        "replayed": False,
        "journal_reference": journal,
        "payable": True,
        "money_moved": False,
        "real_values_activated": False,
    }


def _may_act_for_tenancy(connection, tenancy: str, *, grant_counts: bool) -> bool:
    """Staff may act for any tenancy. A resident may act only for a household they belong to."""
    staff = connection.execute(
        text(
            "SELECT perchpoint.has_capability('payment.charge') "
            "OR perchpoint.has_capability('payment.refund') "
            "OR perchpoint.has_capability('payment.exception')"
        )
    ).scalar()
    if staff:
        return True
    household = _household(tenancy)
    if household is not None and household["email"].lower() == _email(connection).lower():
        return True
    primary = connection.execute(
        text(
            "SELECT 1 FROM payment_obligations WHERE tenancy_code = :tenancy "
            "AND primary_account_id = perchpoint.current_actor() LIMIT 1"
        ),
        {"tenancy": tenancy},
    ).first()
    if primary is not None:
        return True
    if not grant_counts:
        return False
    grant = connection.execute(
        text(
            "SELECT 1 FROM payer_grants WHERE tenancy_code = :tenancy "
            "AND payer_account_id = perchpoint.current_actor() AND state = 'active' LIMIT 1"
        ),
        {"tenancy": tenancy},
    ).first()
    if grant is not None:
        return True
    enrolled = connection.execute(
        text(
            "SELECT 1 FROM autopay_enrollments WHERE tenancy_code = :tenancy "
            "AND payer_account_id = perchpoint.current_actor() AND state = 'active' LIMIT 1"
        ),
        {"tenancy": tenancy},
    ).first()
    return enrolled is not None


def _actor_tenancy(connection, settings: Settings) -> str | None:
    email = _email(connection)
    for row in HOUSEHOLDS:
        if row["email"].lower() == email.lower():
            return row["slug"]
    grant = connection.execute(
        text(
            "SELECT tenancy_code FROM payer_grants "
            "WHERE payer_account_id = perchpoint.current_actor() AND state = 'active' "
            "ORDER BY accepted_at DESC NULLS LAST LIMIT 1"
        )
    ).scalar()
    return str(grant) if grant else None


def summary(settings, actor, organization, tenancy_code: str | None) -> dict:
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.read", "payment.pay", "payment.charge", "payment.refund"))
        tenancy = tenancy_code or _actor_tenancy(connection, settings)
        if tenancy is None:
            return {"tenancy_code": None, "obligations": [], "payments": [], "refunds": [], "autopay": None, "money_moved": False}
        if not _may_act_for_tenancy(connection, tenancy, grant_counts=True):
            return {
                "tenancy_code": tenancy,
                "environment": "local_fake",
                "obligations": [],
                "payments": [],
                "refunds": [],
                "allowance": None,
                "autopay": None,
                "ledger": None,
                "money_moved": False,
                "real_values_activated": False,
                "resident_surcharge": False,
            }
        obligations = connection.execute(
            text(
                "SELECT public_reference, description, amount_minor, category, state, account_reference, due_on, id "
                "FROM payment_obligations WHERE tenancy_code = :tenancy ORDER BY created_at"
            ),
            {"tenancy": tenancy},
        ).mappings().all()
        rows = []
        for item in obligations:
            collected = _collected(connection, item["id"])
            reserved = _reserved(connection, item["id"])
            rows.append({
                "reference": item["public_reference"],
                "description": item["description"],
                "category": item["category"],
                "amount_minor": int(item["amount_minor"]),
                "collected_minor": collected,
                "processing_minor": reserved,
                "remaining_minor": max(0, int(item["amount_minor"]) - collected - reserved),
                "state": item["state"],
                "due_on": item["due_on"].isoformat() if item["due_on"] else None,
            })
        payments = connection.execute(
            text(
                "SELECT public_reference, amount_minor, state, method, ledger_status, created_at, payer_account_id "
                "FROM payment_orders WHERE tenancy_code = :tenancy ORDER BY created_at"
            ),
            {"tenancy": tenancy},
        ).mappings().all()
        staff = bool(connection.execute(text("SELECT perchpoint.has_capability('payment.charge') OR perchpoint.has_capability('payment.refund')")).scalar())
        actor_id = connection.execute(text("SELECT perchpoint.current_actor()")).scalar()
        if not staff:
            payments = [row for row in payments if row["payer_account_id"] == actor_id]
        payments = [{key: value for key, value in row.items() if key != "payer_account_id"} for row in payments]
        refunds = connection.execute(
            text(
                "SELECT public_reference, amount_minor, state, description FROM refund_cases "
                "WHERE tenancy_code = :tenancy ORDER BY authorized_at"
            ),
            {"tenancy": tenancy},
        ).mappings().all()
        budget = _allowance_row(connection, tenancy, 0)
        autopay = _autopay_summary(connection, tenancy)
        ledger = None
        if staff and obligations:
            account_reference = obligations[0]["account_reference"]
            counts = {
                row.kind: int(row.total)
                for row in connection.execute(
                    text(
                        "SELECT kind, count(*) AS total FROM journal_transactions "
                        "WHERE tenancy_code = :tenancy AND kind IN ('charge', 'settlement') GROUP BY kind"
                    ),
                    {"tenancy": tenancy},
                )
            }
            due_minor = None
            if account_reference:
                due_minor = int(_positions(connection, _account(connection, account_reference).id)["due_minor"])
            journals = []
            if account_reference:
                journals = connection.execute(
                    text(
                        "SELECT t.public_reference, t.kind, t.amount_minor "
                        "FROM journal_transactions t "
                        "JOIN resident_accounts a ON a.id = t.account_id "
                        "WHERE a.public_reference = :account "
                        "ORDER BY t.public_reference"
                    ),
                    {"account": account_reference},
                ).mappings().all()
            ledger = {
                "account_reference": account_reference,
                "due_minor": due_minor,
                "charge_count": counts.get("charge", 0),
                "settlement_count": counts.get("settlement", 0),
                "journals": [dict(row) for row in journals],
            }
    return {
        "tenancy_code": tenancy,
        "environment": "local_fake",
        "obligations": rows,
        "payments": [dict(row) for row in payments],
        "refunds": [dict(row) for row in refunds],
        "allowance": budget,
        "autopay": autopay,
        "ledger": ledger,
        "money_moved": False,
        "real_values_activated": False,
        "resident_surcharge": False,
    }


def _next_collection_date(day: int, zone_name: str, moment: datetime, latest: dict | None) -> str:
    local = moment.astimezone(ZoneInfo(zone_name)).date()
    year, month = local.year, local.month
    current_period = f"{year:04d}-{month:02d}"
    finished = latest is not None and latest["period_code"] == current_period and latest["state"] in {"collected", "skipped"}
    if finished or day < local.day:
        month += 1
        if month == 13:
            month = 1
            year += 1
    return date(year, month, day).isoformat()


def _autopay_summary(connection, tenancy: str) -> dict | None:
    enrollment = connection.execute(
        text(
            "SELECT id, cap_minor, day_of_month, zone_name, state, policy_version "
            "FROM autopay_enrollments WHERE tenancy_code = :tenancy AND state = 'active' "
            "ORDER BY id LIMIT 1"
        ),
        {"tenancy": tenancy},
    ).mappings().first()
    if enrollment is None:
        return None
    latest = connection.execute(
        text(
            "SELECT period_code, state, reason, amount_minor FROM autopay_occurrences "
            "WHERE enrollment_id = :enrollment ORDER BY period_code DESC LIMIT 1"
        ),
        {"enrollment": enrollment["id"]},
    ).mappings().first()
    latest_row = None
    if latest is not None:
        latest_row = {
            "period_code": latest["period_code"],
            "state": latest["state"],
            "reason": latest["reason"],
            "amount_minor": None if latest["amount_minor"] is None else int(latest["amount_minor"]),
        }
    return {
        "state": enrollment["state"],
        "cap_minor": int(enrollment["cap_minor"]),
        "day_of_month": int(enrollment["day_of_month"]),
        "zone": enrollment["zone_name"],
        "policy_version": enrollment["policy_version"],
        "included_categories": ["rent"],
        "next_on": _next_collection_date(int(enrollment["day_of_month"]), enrollment["zone_name"], server_now(), latest_row),
        "latest": latest_row,
    }


def _allowance_row(connection, tenancy: str, source_remaining: int) -> dict | None:
    budget = connection.execute(
        text(
            "SELECT snapshot_minor, current_minor, zone_name FROM tenancy_refund_budgets WHERE tenancy_code = :tenancy"
        ),
        {"tenancy": tenancy},
    ).mappings().first()
    if budget is None:
        return None
    entries = connection.execute(
        text(
            "SELECT amount_minor, state, authorized_at FROM refund_cases WHERE tenancy_code = :tenancy"
        ),
        {"tenancy": tenancy},
    ).mappings().all()
    return allowance(
        snapshot_minor=int(budget["snapshot_minor"]),
        current_minor=int(budget["current_minor"]),
        entries=[dict(entry) for entry in entries],
        source_remaining=source_remaining,
        moment=server_now(),
        zone_name=budget["zone_name"],
    )


LOCAL_SCENARIOS = {"succeeded", "pending", "decline", "timeout_after_accept", "outage", "callback"}


def _simulation_allowed() -> bool:
    return os.environ.get("PHASE3_ENVIRONMENT", "local") in {"local", "test"}


def _resolve_checkout_scenario(method: str, requested: str | None, staff: bool) -> tuple[str, bool]:
    """Local card checkout settles through the shared normalizer. Explicit callback waits for a provider fact."""
    if not _simulation_allowed():
        if requested:
            raise CommandError(400, "invalid", "A scenario cannot choose the provider result outside the local fake environment.", False)
        raise CommandError(409, "conflict", "Live collection is not activated.", False)
    if requested and requested not in LOCAL_SCENARIOS:
        raise CommandError(400, "invalid", "That payment scenario is not recognized.", False)
    if requested == "callback":
        return "callback", True
    if requested and not staff:
        raise CommandError(400, "invalid", "That payment scenario is not available for this payer.", False)
    if requested and staff:
        return requested, False
    return ("pending" if method == "ach" else "succeeded"), False


def _autopay_scenario() -> str:
    requested = os.environ.get("PHASE17_AUTOPAY_SCENARIO", "")
    if requested in {"callback", "pending"} and _simulation_allowed():
        return requested
    return "succeeded"


def checkout(settings, actor, organization, body: dict) -> dict:
    amount = int(body["amount_minor"])
    method = body.get("method") or "card"
    if method not in {"card", "ach"} or amount < 1:
        raise CommandError(400, "invalid", "Choose a synthetic card or bank debit and a positive amount.", False)
    fingerprint = _fingerprint([body["obligation_reference"], amount, method, body["idempotency_key"]])
    reference = f"payment-{uuid4().hex[:16]}"
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.pay", "payment.charge"))
        replay = _replay(connection, body["idempotency_key"], fingerprint)
        if replay is not None:
            return replay
        staff = bool(connection.execute(text("SELECT perchpoint.has_capability('payment.charge')")).scalar())
        obligation = connection.execute(
            text(
                "SELECT id, amount_minor, tenancy_code, account_reference, state, primary_account_id "
                "FROM payment_obligations WHERE public_reference = :reference FOR UPDATE"
            ),
            {"reference": body["obligation_reference"]},
        ).mappings().first()
        if obligation is None or obligation["state"] != "published":
            raise CommandError(404, "missing", "That obligation is not payable.", False)
        actor_id = connection.execute(text("SELECT perchpoint.current_actor()")).scalar()
        if not staff and obligation["primary_account_id"] != actor_id:
            grant = connection.execute(
                text(
                    "SELECT 1 FROM payer_grants WHERE tenancy_code = :tenancy AND payer_account_id = :actor AND state = 'active'"
                ),
                {"tenancy": obligation["tenancy_code"], "actor": actor_id},
            ).first()
            if grant is None:
                raise CommandError(403, "denied", "This action is not authorized.", False)
        remaining = int(obligation["amount_minor"]) - _collected(connection, obligation["id"]) - _reserved(connection, obligation["id"])
        if amount > remaining:
            raise CommandError(409, "conflict", "That amount is more than the eligible balance.", False)
        scenario, deferred = _resolve_checkout_scenario(method, body.get("scenario"), staff)
        order_id = uuid4()
        connection.execute(
            text(
                "INSERT INTO payment_orders "
                "(organization_id, id, public_reference, obligation_id, tenancy_code, payer_account_id, amount_minor, fee_minor, method, state, environment, idempotency_key, ledger_status) "
                "VALUES (CAST(:org AS uuid), :id, :reference, :obligation, :tenancy, :payer, :amount, 0, :method, 'processing', 'local_fake', :key, 'pending')"
            ),
            {
                "org": organization,
                "id": order_id,
                "reference": reference,
                "obligation": obligation["id"],
                "tenancy": obligation["tenancy_code"],
                "payer": body["payer_account_id"] if staff and body.get("payer_account_id") else actor_id,
                "amount": amount,
                "method": method,
                "key": body["idempotency_key"],
            },
        )
        connection.execute(
            text(
                "INSERT INTO collection_reservations (organization_id, id, obligation_id, order_id, amount_minor, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :obligation, :order_id, :amount, 'active')"
            ),
            {"org": organization, "obligation": obligation["id"], "order_id": order_id, "amount": amount},
        )
        _remember(connection, organization, body["idempotency_key"], fingerprint, reference)
        account_reference = obligation["account_reference"]
        tenancy = obligation["tenancy_code"]
    try:
        provider = TRANSPORT.charge(idempotency_key=body["idempotency_key"], amount_minor=amount, method=method, scenario=scenario)
        provider_state = provider["status"]
        provider_reference = provider["id"]
    except ProviderTimeout as exc:
        provider_state = "unknown"
        provider_reference = exc.provider_reference
    except ConnectionError as exc:
        raise CommandError(503, "unavailable", "The local payment adapter is unavailable.", True) from exc
    if deferred and provider_state == "succeeded":
        return {
            "accepted": True,
            "reference": reference,
            "replayed": False,
            "state": "processing",
            "ledger_status": "pending",
            "ledger_reference": None,
            "due_minor": None,
            "money_moved": False,
            "real_values_activated": False,
            "provider_execution": "local_fake",
        }
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _apply_provider(connection, organization, reference, provider_state, provider_reference, account_reference, tenancy, amount, scenario)
        order = connection.execute(
            text("SELECT state, ledger_status, ledger_reference FROM payment_orders WHERE public_reference = :reference"),
            {"reference": reference},
        ).one()
        due_minor = None
        if account_reference and order.ledger_status == "posted":
            account = _account(connection, account_reference)
            due_minor = _positions(connection, account.id)["due_minor"]
    return {
        "accepted": True,
        "reference": reference,
        "replayed": False,
        "state": order.state,
        "ledger_status": order.ledger_status,
        "ledger_reference": order.ledger_reference,
        "due_minor": due_minor,
        "money_moved": False,
        "real_values_activated": False,
        "provider_execution": "local_fake",
    }


def _apply_provider(connection, organization, reference, provider_state, provider_reference, account_reference, tenancy, amount, scenario) -> None:
    order = connection.execute(
        text("SELECT id, state, obligation_id FROM payment_orders WHERE public_reference = :reference FOR UPDATE"),
        {"reference": reference},
    ).one()
    if order.state in {"succeeded", "failed", "canceled"}:
        return
    local_state = {"succeeded": "succeeded", "failed": "failed", "processing": "processing"}.get(provider_state, "unknown")
    ledger_reference = None
    ledger_status = "pending"
    if local_state == "succeeded" and account_reference:
        account = _account(connection, account_reference)
        due = _positions(connection, account.id)["due_minor"]
        applied = min(max(due, 0), amount)
        unapplied = amount - applied
        lines: list[tuple[str, str, int]] = [("debit", "unapplied", amount)]
        if applied:
            lines.append(("credit", "receivable", applied))
        if unapplied:
            lines.append(("credit", "prepayment", unapplied))
        ledger_reference = _post(connection, organization, account, "settlement", amount, lines, tenancy_code=tenancy)
        connection.execute(
            text(
                "INSERT INTO ledger_allocations (organization_id, id, settlement_id, amount_applied_minor, amount_unapplied_minor) "
                "SELECT CAST(:org AS uuid), gen_random_uuid(), id, :applied, :unapplied "
                "FROM journal_transactions WHERE public_reference = :reference"
            ),
            {"org": organization, "applied": applied, "unapplied": unapplied, "reference": ledger_reference},
        )
        ledger_status = "posted"
    elif local_state == "succeeded":
        ledger_status = "not_linked"
    reservation_state = "consumed" if local_state == "succeeded" else "released" if local_state == "failed" else "active"
    connection.execute(
        text("UPDATE payment_orders SET state = :state, ledger_reference = :ledger, ledger_status = :ledger_status WHERE id = :id"),
        {"state": local_state, "ledger": ledger_reference, "ledger_status": ledger_status, "id": order.id},
    )
    connection.execute(
        text(
            "INSERT INTO payment_attempts (organization_id, id, order_id, provider_reference, state, scenario) "
            "VALUES (CAST(:org AS uuid), gen_random_uuid(), :order_id, :provider, :state, :scenario)"
        ),
        {"org": organization, "order_id": order.id, "provider": provider_reference, "state": local_state if local_state != "processing" else "processing", "scenario": scenario},
    )
    connection.execute(
        text("UPDATE collection_reservations SET state = :state WHERE order_id = :order_id"),
        {"state": reservation_state, "order_id": order.id},
    )
    if local_state == "succeeded":
        connection.execute(
            text(
                "INSERT INTO payment_receipts (organization_id, id, public_reference, order_id, payer_account_id, tenancy_code, body) "
                "SELECT organization_id, gen_random_uuid(), :receipt, id, payer_account_id, tenancy_code, :body "
                "FROM payment_orders WHERE id = :order_id"
            ),
            {
                "receipt": f"receipt-{uuid4().hex[:16]}",
                "body": f"{RECEIPT_MARKER}. Synthetic {scenario} collection of {amount} minor units. Provider acceptance is not a bank deposit.",
                "order_id": order.id,
            },
        )
        connection.execute(
            text(
                "INSERT INTO payment_notices (organization_id, id, tenancy_code, recipient_account_id, kind, state, body) "
                "SELECT organization_id, gen_random_uuid(), tenancy_code, payer_account_id, 'payment_status', 'synthetic_local', :body "
                "FROM payment_orders WHERE id = :order_id"
            ),
            {"body": "A synthetic payment was recorded. No email or SMS was sent.", "order_id": order.id},
        )


def reconcile(settings, actor, organization, reference: str) -> dict:
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.pay", "payment.charge"))
        order = connection.execute(
            text(
                "SELECT o.idempotency_key, o.amount_minor, o.tenancy_code, o.state, ob.account_reference "
                "FROM payment_orders o JOIN payment_obligations ob ON ob.id = o.obligation_id "
                "WHERE o.public_reference = :reference"
            ),
            {"reference": reference},
        ).mappings().first()
        if order is None:
            raise CommandError(404, "missing", "That payment was not found.", False)
        if order["state"] != "unknown":
            return {"accepted": True, "reference": reference, "replayed": True, "state": order["state"], "money_moved": False}
        found = TRANSPORT.retrieve(order["idempotency_key"])
        if found is None:
            return {"accepted": True, "reference": reference, "state": "unknown", "money_moved": False}
        _apply_provider(
            connection,
            organization,
            reference,
            found["status"],
            found["id"],
            order["account_reference"],
            order["tenancy_code"],
            int(order["amount_minor"]),
            "reconcile",
        )
    return {"accepted": True, "reference": reference, "state": found["status"], "money_moved": False, "provider_execution": "local_fake"}


def _source_remaining(connection, order_id, collected: int) -> int:
    used = connection.execute(
        text(
            "SELECT coalesce(sum(amount_minor), 0) FROM refund_cases "
            "WHERE order_id = :order AND state IN ('reserved', 'owner_approved', 'succeeded', 'unknown')"
        ),
        {"order": order_id},
    ).scalar_one()
    returned = connection.execute(
        text(
            "SELECT coalesce(sum(amount_minor), 0) FROM processor_disputes "
            "WHERE order_id = :order AND state = 'lost'"
        ),
        {"order": order_id},
    ).scalar_one()
    return max(0, collected - int(used) - int(returned))


def _lock_budget(connection, organization, tenancy: str):
    row = connection.execute(
        text(
            "SELECT snapshot_minor, current_minor, period_start, zone_name FROM tenancy_refund_budgets "
            "WHERE organization_id = CAST(:org AS uuid) AND tenancy_code = :tenancy FOR UPDATE"
        ),
        {"org": organization, "tenancy": tenancy},
    ).mappings().first()
    if row is None:
        raise CommandError(409, "conflict", "This tenancy has no approved monthly rent basis, so an ordinary refund is not available.", False)
    moment = server_now()
    period_start = moment.astimezone(ZoneInfo(row["zone_name"])).date().replace(day=1)
    if row["period_start"] != period_start:
        connection.execute(
            text(
                "UPDATE tenancy_refund_budgets SET snapshot_minor = current_minor, period_start = :period "
                "WHERE organization_id = CAST(:org AS uuid) AND tenancy_code = :tenancy"
            ),
            {"period": period_start, "org": organization, "tenancy": tenancy},
        )
        row = connection.execute(
            text(
                "SELECT snapshot_minor, current_minor, period_start, zone_name FROM tenancy_refund_budgets "
                "WHERE organization_id = CAST(:org AS uuid) AND tenancy_code = :tenancy"
            ),
            {"org": organization, "tenancy": tenancy},
        ).mappings().one()
    return row


def request_refund(settings, actor, organization, body: dict) -> dict:
    amount = int(body["amount_minor"])
    description = str(body.get("description") or "").strip()
    explanation = str(body.get("resident_explanation") or description).strip()
    if amount < 1 or len(description) < 8 or len(explanation) < 8:
        raise CommandError(400, "invalid", "A refund needs a positive amount and a written explanation.", False)
    fingerprint = _fingerprint([body["payment_reference"], amount, description, body["idempotency_key"]])
    reference = f"refund-{uuid4().hex[:16]}"
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "payment.refund")
        replay = _replay(connection, body["idempotency_key"], fingerprint)
        if replay is not None:
            reserved = connection.execute(
                text(
                    "SELECT c.amount_minor, c.state, c.tenancy_code, p.ledger_reference "
                    "FROM refund_cases c JOIN payment_orders p ON p.id = c.order_id "
                    "WHERE c.public_reference = :reference FOR UPDATE"
                ),
                {"reference": replay["reference"]},
            ).mappings().first()
            if reserved is None or reserved["state"] not in {"reserved", "unknown"}:
                return replay
            reference = replay["reference"]
            amount = int(reserved["amount_minor"])
            ledger_reference = reserved["ledger_reference"]
            tenancy = reserved["tenancy_code"]
        else:
            order = connection.execute(
                text(
                    "SELECT id, amount_minor, tenancy_code, state, ledger_reference FROM payment_orders "
                    "WHERE public_reference = :reference FOR UPDATE"
                ),
                {"reference": body["payment_reference"]},
            ).mappings().first()
            if order is None or order["state"] != "succeeded":
                raise CommandError(409, "conflict", "Only a confirmed synthetic payment can be refunded.", False)
            open_dispute = connection.execute(
                text("SELECT 1 FROM processor_disputes WHERE order_id = :order AND state IN ('open', 'evidence_needed')"),
                {"order": order["id"]},
            ).first()
            if open_dispute is not None:
                raise CommandError(409, "conflict", "A processor dispute is open on this payment, so another refund is held.", False)
            budget = _lock_budget(connection, organization, order["tenancy_code"])
            source_remaining = _source_remaining(connection, order["id"], int(order["amount_minor"]))
            entries = connection.execute(
                text("SELECT amount_minor, state, authorized_at FROM refund_cases WHERE tenancy_code = :tenancy"),
                {"tenancy": order["tenancy_code"]},
            ).mappings().all()
            decision = allowance(
                snapshot_minor=int(budget["snapshot_minor"]),
                current_minor=int(budget["current_minor"]),
                entries=[dict(entry) for entry in entries],
                source_remaining=source_remaining,
                moment=server_now(),
                zone_name=budget["zone_name"],
            )
            state = "reserved" if amount <= decision["ordinary_max_minor"] else "owner_decision_required"
            connection.execute(
                text(
                    "INSERT INTO refund_cases "
                    "(organization_id, id, public_reference, tenancy_code, order_id, amount_minor, reason_category, description, resident_explanation, state, idempotency_key) "
                    "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, :tenancy, :order_id, :amount, :reason, :description, :explanation, :state, :key)"
                ),
                {
                    "org": organization,
                    "reference": reference,
                    "tenancy": order["tenancy_code"],
                    "order_id": order["id"],
                    "amount": amount,
                    "reason": body.get("reason_category") or "resident_request",
                    "description": description,
                    "explanation": explanation,
                    "state": state,
                    "key": body["idempotency_key"],
                },
            )
            _remember(connection, organization, body["idempotency_key"], fingerprint, reference)
            if state != "reserved":
                return {"accepted": True, "reference": reference, "state": state, "ordinary_max_minor": decision["ordinary_max_minor"], "money_moved": False, **decision}
            ledger_reference = order["ledger_reference"]
            tenancy = order["tenancy_code"]
    _fault("before_refund_dispatch")
    outcome = _execute_refund(settings, actor, organization, reference, amount, ledger_reference, tenancy, body.get("scenario") or "succeeded")
    return {"accepted": True, "reference": reference, "state": outcome, "replayed": False, "money_moved": False, "provider_execution": "local_fake"}


def _execute_refund(settings, actor, organization, reference, amount, ledger_reference, tenancy, scenario) -> str:
    try:
        provider = TRANSPORT.refund(idempotency_key=reference, amount_minor=amount, scenario=scenario)
        provider_state = provider["status"]
    except ProviderTimeout:
        provider_state = "unknown"
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        case = connection.execute(
            text("SELECT id, state, order_id FROM refund_cases WHERE public_reference = :reference FOR UPDATE"),
            {"reference": reference},
        ).one()
        if case.state in {"succeeded", "failed"}:
            return case.state
        journal = None
        local = {"succeeded": "succeeded", "failed": "failed"}.get(provider_state, "unknown")
        if local == "succeeded" and ledger_reference:
            account_reference = connection.execute(
                text(
                    "SELECT account_reference FROM payment_obligations o JOIN payment_orders p ON p.obligation_id = o.id "
                    "WHERE p.id = :order_id"
                ),
                {"order_id": case.order_id},
            ).scalar()
            if account_reference:
                account = _writable_account(connection, organization, account_reference)
                allocation = connection.execute(
                    text(
                        "SELECT amount_applied_minor, amount_unapplied_minor FROM ledger_allocations a "
                        "JOIN journal_transactions t ON t.id = a.settlement_id WHERE t.public_reference = :reference"
                    ),
                    {"reference": ledger_reference},
                ).first()
                applied_room = int(allocation.amount_applied_minor) if allocation else amount
                applied = min(amount, applied_room)
                unapplied = amount - applied
                lines: list[tuple[str, str, int]] = []
                if applied:
                    lines.append(("debit", "receivable", applied))
                if unapplied:
                    lines.append(("debit", "prepayment", unapplied))
                lines.append(("credit", "unapplied", amount))
                journal = _post(connection, organization, account, "refund", amount, lines, tenancy_code=tenancy)
        if local == "failed":
            connection.execute(text("UPDATE refund_cases SET state = 'failed' WHERE id = :id"), {"id": case.id})
        else:
            connection.execute(
                text("UPDATE refund_cases SET state = :state, ledger_reference = :journal WHERE id = :id"),
                {"state": local, "journal": journal, "id": case.id},
            )
        return local


def _writable_account(connection, organization, reference: str):
    account = _account(connection, reference)
    if account.period_state == "open":
        return account
    period_code = f"correction-{uuid4().hex[:12]}"
    connection.execute(
        text(
            "INSERT INTO accounting_periods (organization_id, id, period_code, state) "
            "VALUES (CAST(:org AS uuid), gen_random_uuid(), :period, 'open')"
        ),
        {"org": organization, "period": period_code},
    )
    connection.execute(
        text("UPDATE resident_accounts SET period_code = :period WHERE public_reference = :reference"),
        {"period": period_code, "reference": reference},
    )
    return _account(connection, reference)


def approve_exception(settings, actor, organization, body: dict) -> dict:
    fingerprint = _fingerprint([body["reference"], body["amount_minor"], body["idempotency_key"]])
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "payment.exception")
        replay = _replay(connection, body["idempotency_key"], fingerprint)
        if replay is not None:
            return replay
        case = connection.execute(
            text(
                "SELECT id, amount_minor, state, tenancy_code, order_id FROM refund_cases "
                "WHERE public_reference = :reference FOR UPDATE"
            ),
            {"reference": body["reference"]},
        ).mappings().first()
        if case is None or case["state"] != "owner_decision_required":
            raise CommandError(409, "conflict", "That refund is not waiting for an owner decision.", False)
        if int(body["amount_minor"]) != int(case["amount_minor"]):
            raise CommandError(409, "conflict", "An owner exception must match the exact requested amount.", False)
        reason = str(body.get("reason") or "").strip()
        if len(reason) < 8:
            raise CommandError(400, "invalid", "The owner exception needs a written reason.", False)
        order = connection.execute(
            text("SELECT id, amount_minor, ledger_reference FROM payment_orders WHERE id = :id FOR UPDATE"),
            {"id": case["order_id"]},
        ).one()
        source_remaining = _source_remaining(connection, order.id, int(order.amount_minor))
        if int(case["amount_minor"]) > source_remaining:
            raise CommandError(409, "conflict", "The source payment does not have that much left to refund.", False)
        _lock_budget(connection, organization, case["tenancy_code"])
        connection.execute(
            text(
                "UPDATE refund_cases SET state = 'owner_approved', exception_reference = :reason WHERE id = :id"
            ),
            {"reason": reason[:500], "id": case["id"]},
        )
        _remember(connection, organization, body["idempotency_key"], fingerprint, body["reference"])
        ledger_reference = order.ledger_reference
        tenancy = case["tenancy_code"]
        amount = int(case["amount_minor"])
    _execute_refund(settings, actor, organization, body["reference"], amount, ledger_reference, tenancy, "succeeded")
    return {"accepted": True, "reference": body["reference"], "state": "succeeded", "ordinary_cap_reset": False, "money_moved": False}


def link_tenancy_resident(settings, actor, organization, body: dict) -> dict:
    email = str(body.get("email") or "").strip().lower()
    tenancy = str(body.get("tenancy_code") or "").strip()
    if "@" not in email or not tenancy:
        raise CommandError(400, "invalid", "Link the resident with an email and a tenancy.", False)
    account_id = _primary_account(settings, email)
    if account_id is None:
        raise CommandError(404, "missing", "That person does not have an account.", False)
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        updated = connection.execute(
            text(
                "UPDATE payment_obligations SET primary_account_id = :account "
                "WHERE tenancy_code = :tenancy RETURNING id"
            ),
            {"account": account_id, "tenancy": tenancy},
        ).first()
        if updated is None:
            raise CommandError(409, "conflict", "That tenancy has no published charge to link.", False)
    return {"accepted": True, "tenancy_code": tenancy, "linked": True, "money_moved": False}


def invite_payer(settings, actor, organization, body: dict) -> dict:
    email = str(body.get("email") or "").strip().lower()
    if "@" not in email:
        raise CommandError(400, "invalid", "The additional payer needs an email address.", False)
    token = uuid4().hex
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.pay", "payment.charge"))
        tenancy = body.get("tenancy_code") or _actor_tenancy(connection, settings)
        if not tenancy:
            raise CommandError(409, "conflict", "This session is not linked to a tenancy.", False)
        if not _may_act_for_tenancy(connection, tenancy, grant_counts=False):
            raise CommandError(403, "denied", "This action is not authorized.", False)
        recent = connection.execute(
            text(
                "SELECT count(*) FROM payer_grants WHERE tenancy_code = :tenancy AND state = 'invited' "
                "AND expires_at > now()"
            ),
            {"tenancy": tenancy},
        ).scalar_one()
        if int(recent) >= 3:
            raise CommandError(429, "conflict", "Too many open payer invitations exist for this tenancy.", True)
        connection.execute(
            text(
                "INSERT INTO payer_grants "
                "(organization_id, id, tenancy_code, grantor_account_id, email, state, token_hash, expires_at) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :tenancy, perchpoint.current_actor(), :email, 'invited', :token_hash, now() + interval '24 hours')"
            ),
            {"org": organization, "tenancy": tenancy, "email": email, "token_hash": token_hash},
        )
    _deliver_payer_invitation(email, token, tenancy)
    return {"accepted": True, "tenancy_code": tenancy, "invitation_token": token, "expires_in_hours": 24, "money_moved": False}


def _deliver_payer_invitation(email: str, token: str, tenancy: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Your synthetic PerchPoint payment invitation"
    message["From"] = "noreply@perchpoint.local"
    message["To"] = email
    message.set_content(
        "This message is synthetic and was delivered only to local Mailpit.\n\n"
        f"Accept: http://127.0.0.1:3000/pay?token={token}\n"
        f"Tenancy: {tenancy}\n"
    )
    host = os.environ.get("PHASE6_SMTP_HOST", "127.0.0.1")
    port = int(os.environ.get("PHASE6_SMTP_PORT", "1125"))
    try:
        with smtplib.SMTP(host, port, timeout=8) as smtp:
            smtp.send_message(message)
    except OSError as exc:
        raise CommandError(503, "unavailable", "The invitation could not be delivered.", True) from exc


def accept_payer(settings, actor, organization, token: str) -> dict:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.pay", "payment.read"))
        grant = connection.execute(
            text(
                "SELECT id, tenancy_code, state, expires_at FROM payer_grants "
                "WHERE token_hash = :token_hash FOR UPDATE"
            ),
            {"token_hash": token_hash},
        ).mappings().first()
        if grant is None or grant["state"] != "invited" or grant["expires_at"] is None:
            raise CommandError(409, "conflict", "That invitation cannot be accepted.", False)
        invited_email = connection.execute(
            text("SELECT email FROM payer_grants WHERE id = :id"),
            {"id": grant["id"]},
        ).scalar()
        if str(invited_email or "").lower() != _email(connection).lower():
            raise CommandError(403, "denied", "This invitation was issued to a different person.", False)
        active = connection.execute(
            text("SELECT 1 FROM payer_grants WHERE tenancy_code = :tenancy AND state = 'active'"),
            {"tenancy": grant["tenancy_code"]},
        ).first()
        if active is not None:
            raise CommandError(409, "conflict", "This tenancy already has an additional payer.", False)
        connection.execute(
            text(
                "UPDATE payer_grants SET state = 'active', payer_account_id = perchpoint.current_actor(), "
                "accepted_at = now(), token_hash = NULL WHERE id = :id"
            ),
            {"id": grant["id"]},
        )
    return {"accepted": True, "tenancy_code": grant["tenancy_code"], "state": "active", "money_moved": False}


def revoke_payer(settings, actor, organization, body: dict) -> dict:
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.pay", "payment.charge"))
        tenancy = body.get("tenancy_code") or _actor_tenancy(connection, settings)
        if not tenancy or not _may_act_for_tenancy(connection, str(tenancy), grant_counts=False):
            raise CommandError(403, "denied", "This action is not authorized.", False)
        grant = connection.execute(
            text(
                "SELECT id FROM payer_grants WHERE tenancy_code = :tenancy AND state = 'active' FOR UPDATE"
            ),
            {"tenancy": tenancy},
        ).first()
        if grant is None:
            raise CommandError(409, "conflict", "This tenancy has no active additional payer.", False)
        connection.execute(
            text("UPDATE payer_grants SET state = 'revoked', token_hash = NULL WHERE id = :id"),
            {"id": grant.id},
        )
        connection.execute(
            text(
                "UPDATE autopay_enrollments SET state = 'canceled' "
                "WHERE tenancy_code = :tenancy AND payer_account_id = ("
                "SELECT payer_account_id FROM payer_grants WHERE id = :id) AND state = 'active'"
            ),
            {"tenancy": tenancy, "id": grant.id},
        )
    return {"accepted": True, "tenancy_code": tenancy, "state": "revoked", "money_moved": False}


def enroll_autopay(settings, actor, organization, body: dict) -> dict:
    cap = int(body["cap_minor"])
    day = int(body.get("day_of_month") or 1)
    if cap < 1 or not 1 <= day <= 28:
        raise CommandError(400, "invalid", "Autopay needs a positive cap and a day from 1 to 28.", False)
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.pay", "payment.charge"))
        tenancy = body.get("tenancy_code") or _actor_tenancy(connection, settings)
        if not tenancy:
            raise CommandError(409, "conflict", "This session is not linked to a tenancy.", False)
        if not _may_act_for_tenancy(connection, tenancy, grant_counts=True):
            raise CommandError(403, "denied", "This action is not authorized.", False)
        actor_id = connection.execute(text("SELECT perchpoint.current_actor()")).scalar()
        instrument_id = uuid4()
        connection.execute(
            text(
                "INSERT INTO payment_instruments "
                "(organization_id, id, payer_account_id, provider_reference, method, display_label, environment, state) "
                "VALUES (CAST(:org AS uuid), :id, :payer, :provider, 'ach', 'Synthetic bank debit', 'local_fake', 'synthetic')"
            ),
            {"org": organization, "id": instrument_id, "payer": actor_id, "provider": f"pm_local_{uuid4().hex[:12]}"},
        )
        connection.execute(
            text(
                "UPDATE autopay_enrollments SET state = 'canceled' "
                "WHERE tenancy_code = :tenancy AND state = 'active'"
            ),
            {"tenancy": tenancy},
        )
        connection.execute(
            text(
                "INSERT INTO autopay_enrollments "
                "(organization_id, id, tenancy_code, payer_account_id, instrument_id, cap_minor, day_of_month, zone_name, state, policy_version) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :tenancy, :payer, :instrument, :cap, :day, :zone, 'active', 'local-default-1')"
            ),
            {"org": organization, "tenancy": tenancy, "payer": actor_id, "instrument": instrument_id, "cap": cap, "day": day, "zone": ZONE},
        )
    return {"accepted": True, "tenancy_code": tenancy, "cap_minor": cap, "zone": ZONE, "state": "active", "money_moved": False}


def set_autopay_state(settings, actor, organization, body: dict) -> dict:
    requested = body.get("state")
    tenancy = str(body.get("tenancy_code") or "")
    if requested not in {"paused", "canceled"} or not tenancy:
        raise CommandError(400, "invalid", "Autopay can be paused or canceled for one tenancy.", False)
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.pay", "payment.charge"))
        if not _may_act_for_tenancy(connection, tenancy, grant_counts=True):
            raise CommandError(403, "denied", "This action is not authorized.", False)
        updated = connection.execute(
            text(
                "UPDATE autopay_enrollments SET state = :state "
                "WHERE tenancy_code = :tenancy AND state = 'active' RETURNING id"
            ),
            {"state": requested, "tenancy": tenancy},
        ).first()
        if updated is None:
            raise CommandError(404, "missing", "There is no active autopay enrollment to change.", False)
    return {"accepted": True, "tenancy_code": tenancy, "state": requested, "money_moved": False}


def dispatch_due_autopay(settings) -> dict:
    """Claim enrollments that are due on the organization-local clock. The caller is the worker, not a browser request."""
    moment = server_now().astimezone(ZoneInfo(ZONE))
    period = moment.strftime("%Y-%m")
    engine = engine_for(settings.runtime_url)
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT organization_id, tenancy_code, payer_account_id "
                "FROM perchpoint.due_autopay_claims(:day, :period)"
            ),
            {"day": moment.day, "period": period},
        ).mappings().all()
        connection.commit()
    engine.dispose()
    dispatched = 0
    for row in rows:
        try:
            result = run_autopay(
                settings,
                row["payer_account_id"],
                row["organization_id"],
                {"tenancy_code": row["tenancy_code"], "period_code": period},
            )
        except CommandError:
            continue
        if result.get("state") == "collected" and not result.get("replayed"):
            dispatched += 1
    return {"dispatched": dispatched, "money_moved": False}


def run_autopay(settings, actor, organization, body: dict) -> dict:
    period = str(body.get("period_code") or "")
    tenancy = str(body.get("tenancy_code") or "")
    if len(period) < 6 or not tenancy:
        raise CommandError(400, "invalid", "Autopay needs a tenancy and a period.", False)
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        enrollment = connection.execute(
            text(
                "SELECT id, cap_minor, payer_account_id, instrument_id, state FROM autopay_enrollments "
                "WHERE tenancy_code = :tenancy AND state = 'active' FOR UPDATE"
            ),
            {"tenancy": tenancy},
        ).mappings().first()
        if enrollment is None:
            return {"accepted": True, "state": "skipped", "reason": "no_active_enrollment", "money_moved": False}
        existing = connection.execute(
            text(
                "SELECT state, reason, amount_minor FROM autopay_occurrences "
                "WHERE enrollment_id = :enrollment AND period_code = :period"
            ),
            {"enrollment": enrollment["id"], "period": period},
        ).mappings().first()
        if existing is not None and existing["state"] != "scheduled":
            return {"accepted": True, "replayed": True, "state": existing["state"], "reason": existing["reason"], "amount_minor": existing["amount_minor"], "money_moved": False}
        if existing is None:
            connection.execute(
                text(
                    "INSERT INTO autopay_occurrences (organization_id, id, enrollment_id, period_code, state, reason) "
                    "VALUES (CAST(:org AS uuid), gen_random_uuid(), :enrollment, :period, 'scheduled', 'evaluating')"
                ),
                {"org": organization, "enrollment": enrollment["id"], "period": period},
            )
        prior = connection.execute(
            text("SELECT amount_minor, state FROM payment_orders WHERE idempotency_key = :key"),
            {"key": f"autopay-{tenancy}-{period}"},
        ).mappings().first()
        if prior is not None and prior["state"] == "processing":
            return {
                "accepted": True,
                "replayed": True,
                "state": "processing",
                "reason": "awaiting_provider",
                "amount_minor": prior["amount_minor"],
                "money_moved": False,
            }
        if prior is not None and prior["state"] == "succeeded":
            connection.execute(
                text(
                    "UPDATE autopay_occurrences SET state = 'collected', reason = 'eligible_remainder', amount_minor = :amount "
                    "WHERE enrollment_id = :enrollment AND period_code = :period"
                ),
                {"amount": prior["amount_minor"], "enrollment": enrollment["id"], "period": period},
            )
            return {
                "accepted": True,
                "replayed": True,
                "state": "collected",
                "reason": "eligible_remainder",
                "amount_minor": prior["amount_minor"],
                "money_moved": False,
            }
        obligation = connection.execute(
            text(
                "SELECT id, public_reference, amount_minor FROM payment_obligations "
                "WHERE tenancy_code = :tenancy AND state = 'published' AND category = 'rent' "
                "ORDER BY created_at LIMIT 1"
            ),
            {"tenancy": tenancy},
        ).mappings().first()
        instrument_state = connection.execute(
            text("SELECT state FROM payment_instruments WHERE id = :id"),
            {"id": enrollment["instrument_id"]},
        ).scalar()
        if instrument_state != "synthetic":
            connection.execute(
                text(
                    "UPDATE autopay_occurrences SET state = 'action_required', reason = 'blocked_instrument', amount_minor = NULL "
                    "WHERE enrollment_id = :enrollment AND period_code = :period"
                ),
                {"enrollment": enrollment["id"], "period": period},
            )
            return {"accepted": True, "state": "action_required", "reason": "blocked_instrument", "amount_minor": 0, "money_moved": False}
        grant_state = connection.execute(
            text(
                "SELECT state FROM payer_grants "
                "WHERE tenancy_code = :tenancy AND payer_account_id = :payer "
                "ORDER BY accepted_at DESC NULLS LAST LIMIT 1"
            ),
            {"tenancy": tenancy, "payer": enrollment["payer_account_id"]},
        ).scalar()
        if grant_state not in {None, "active"}:
            connection.execute(
                text(
                    "UPDATE autopay_occurrences SET state = 'action_required', reason = 'revoked_grant', amount_minor = NULL "
                    "WHERE enrollment_id = :enrollment AND period_code = :period"
                ),
                {"enrollment": enrollment["id"], "period": period},
            )
            return {"accepted": True, "state": "action_required", "reason": "revoked_grant", "amount_minor": 0, "money_moved": False}
        eligible = 0 if obligation is None else max(0, int(obligation["amount_minor"]) - _collected(connection, obligation["id"]) - _reserved(connection, obligation["id"]))
        cap = int(enrollment["cap_minor"])
        if eligible < 1:
            state, reason, amount = "skipped", "nothing_due", 0
        elif eligible > cap:
            state, reason, amount = "action_required", "over_cap", eligible
        else:
            state, reason, amount = "collected", "eligible_remainder", eligible
        reference = obligation["public_reference"] if obligation and state == "collected" else None
        payer = enrollment["payer_account_id"]
        if state != "collected" or reference is None:
            connection.execute(
                text(
                    "UPDATE autopay_occurrences SET state = :state, reason = :reason, amount_minor = :amount "
                    "WHERE enrollment_id = :enrollment AND period_code = :period"
                ),
                {"state": state, "reason": reason, "amount": amount or None, "enrollment": enrollment["id"], "period": period},
            )
            return {"accepted": True, "state": state, "reason": reason, "amount_minor": amount, "money_moved": False}
    paid = checkout(settings, actor, organization, {
        "obligation_reference": reference,
        "amount_minor": amount,
        "method": "ach",
        "scenario": _autopay_scenario(),
        "payer_account_id": payer,
        "idempotency_key": f"autopay-{tenancy}-{period}",
    })
    if paid.get("state") != "succeeded":
        with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
            connection.execute(
                text(
                    "UPDATE autopay_occurrences SET reason = 'awaiting_provider', amount_minor = :amount "
                    "WHERE enrollment_id = :enrollment AND period_code = :period AND state = 'scheduled'"
                ),
                {"amount": amount, "enrollment": enrollment["id"], "period": period},
            )
        return {
            "accepted": True,
            "state": paid.get("state"),
            "reason": "awaiting_provider",
            "amount_minor": amount,
            "payment": paid,
            "money_moved": False,
        }
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        connection.execute(
            text(
                "UPDATE autopay_occurrences SET state = 'collected', reason = 'eligible_remainder', amount_minor = :amount "
                "WHERE enrollment_id = :enrollment AND period_code = :period AND state = 'scheduled'"
            ),
            {"amount": amount, "enrollment": enrollment["id"], "period": period},
        )
    return {"accepted": True, "state": "collected", "reason": reason, "amount_minor": amount, "payment": paid, "money_moved": False}


def _invalidate_returned_instrument(connection, tenancy: str) -> None:
    connection.execute(
        text(
            "UPDATE payment_instruments SET state = 'revoked' "
            "WHERE id IN ("
            "SELECT instrument_id FROM autopay_enrollments WHERE tenancy_code = :tenancy AND state = 'active'"
            ")"
        ),
        {"tenancy": tenancy},
    )


def record_return(settings, actor, organization, body: dict) -> dict:
    amount = int(body["amount_minor"])
    if amount < 1:
        raise CommandError(400, "invalid", "A return needs a positive amount.", False)
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "payment.refund")
        order = connection.execute(
            text(
                "SELECT id, amount_minor, tenancy_code, state, ledger_reference, public_reference FROM payment_orders "
                "WHERE public_reference = :reference FOR UPDATE"
            ),
            {"reference": body["payment_reference"]},
        ).mappings().first()
        if order is None or order["state"] != "succeeded":
            raise CommandError(409, "conflict", "Only a confirmed payment can be returned.", False)
        source_remaining = _source_remaining(connection, order["id"], int(order["amount_minor"]))
        if amount > source_remaining:
            raise CommandError(409, "conflict", "The return is larger than the amount still with the payer.", False)
        reference = f"return-{uuid4().hex[:16]}"
        account_reference = connection.execute(
            text(
                "SELECT account_reference FROM payment_obligations WHERE id = ("
                "SELECT obligation_id FROM payment_orders WHERE id = :order_id)"
            ),
            {"order_id": order["id"]},
        ).scalar()
        journal = None
        if account_reference and order["ledger_reference"]:
            account = _writable_account(connection, organization, account_reference)
            journal = _post(
                connection,
                organization,
                account,
                "return",
                amount,
                [("debit", "receivable", amount), ("credit", "unapplied", amount)],
                tenancy_code=order["tenancy_code"],
            )
        connection.execute(
            text(
                "INSERT INTO processor_disputes "
                "(organization_id, id, public_reference, order_id, tenancy_code, amount_minor, reason_code, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, :order_id, :tenancy, :amount, 'ach_return', 'lost')"
            ),
            {"org": organization, "reference": reference, "order_id": order["id"], "tenancy": order["tenancy_code"], "amount": amount},
        )
        _invalidate_returned_instrument(connection, order["tenancy_code"])
        due_minor = None
        if account_reference:
            due_minor = _positions(connection, _account(connection, account_reference).id)["due_minor"]
    return {
        "accepted": True,
        "reference": reference,
        "ledger_reference": journal,
        "due_minor": due_minor,
        "state": "lost",
        "money_moved": False,
        "kind": "return",
    }


def open_processor_dispute(settings, actor, organization, body: dict) -> dict:
    amount = int(body["amount_minor"])
    if amount < 1:
        raise CommandError(400, "invalid", "A dispute needs a positive amount.", False)
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "payment.refund")
        order = connection.execute(
            text("SELECT id, tenancy_code, state FROM payment_orders WHERE public_reference = :reference"),
            {"reference": body["payment_reference"]},
        ).mappings().first()
        if order is None or order["state"] != "succeeded":
            raise CommandError(409, "conflict", "Only a confirmed payment can have a processor dispute.", False)
        reference = f"dispute-{uuid4().hex[:16]}"
        connection.execute(
            text(
                "INSERT INTO processor_disputes "
                "(organization_id, id, public_reference, order_id, tenancy_code, amount_minor, reason_code, state, deadline_on) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, :order_id, :tenancy, :amount, :reason, 'open', CURRENT_DATE + 7)"
            ),
            {
                "org": organization,
                "reference": reference,
                "order_id": order["id"],
                "tenancy": order["tenancy_code"],
                "amount": amount,
                "reason": body.get("reason_code") or "card_dispute",
            },
        )
    return {"accepted": True, "reference": reference, "state": "open", "journal_posted": False, "money_moved": False}


def exceptions(settings, actor, organization) -> dict:
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "payment.exception")
        rows = connection.execute(
            text(
                "SELECT public_reference, tenancy_code, amount_minor, description, state "
                "FROM refund_cases WHERE state = 'owner_decision_required' ORDER BY authorized_at"
            )
        ).mappings().all()
    return {"exceptions": [dict(row) for row in rows], "money_moved": False, "real_values_activated": False}


def record_provider_event(settings, payload: dict) -> dict:
    """Store an authenticated provider delivery before any financial effect is applied."""
    event_id = str(payload.get("id") or "").strip()
    organization = str(payload.get("organization_id") or "").strip()
    kind = str(payload.get("type") or "unknown")
    if not event_id or not organization:
        return {"accepted": True, "stored": False, "ignored": True, "applied": False, "money_moved": False}
    effect_key = str(payload.get("effect_key") or event_id)
    engine = engine_for(settings.runtime_url)
    with engine.connect() as connection:
        inserted = connection.execute(
            text(
                "SELECT perchpoint.store_provider_event("
                "CAST(:org AS uuid), :event, :effect, :kind, CAST(:payload AS jsonb))"
            ),
            {
                "org": organization,
                "event": event_id,
                "effect": effect_key,
                "kind": kind[:80],
                "payload": json.dumps(payload),
            },
        ).scalar_one()
        connection.commit()
    engine.dispose()
    return {
        "accepted": True,
        "stored": bool(inserted),
        "duplicate": not bool(inserted),
        "applied": False,
        "ignored": False,
        "money_moved": False,
    }


def _fault(name: str) -> None:
    if os.environ.get("PHASE3_ENVIRONMENT", "local") not in {"local", "test"}:
        return
    if os.environ.get("PHASE17_FAULT") != name:
        return
    os.environ.pop("PHASE17_FAULT", None)
    raise RuntimeError("injected fault")


def _inbox_scopes(settings) -> list:
    engine = engine_for(settings.runtime_url)
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT organization_id, principal_id FROM perchpoint.payment_inbox_scopes()")
        ).mappings().all()
        connection.commit()
    engine.dispose()
    return rows


def _apply_one_provider_event(settings, principal, organization, event_id) -> bool:
    with runtime_transaction(settings, principal, organization, uuid4()) as connection:
        row = connection.execute(
            text(
                "SELECT id, organization_id, provider_event_id, effect_key, payload_kind, payload "
                "FROM provider_events WHERE id = :id AND state = 'received' FOR UPDATE"
            ),
            {"id": event_id},
        ).mappings().first()
        if row is None:
            return False
        payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"] or "{}")
        if row["payload_kind"] == "payment.returned":
            return _callback_return(connection, row, payload)
        if row["payload_kind"] in {"payment.succeeded", "payment.failed", "payment.processing"}:
            _fault("before_provider_commit")
            return bool(_callback_payment(connection, row, payload))
        connection.execute(
            text("UPDATE provider_events SET state = 'quarantined' WHERE id = :id"),
            {"id": row["id"]},
        )
        return False


def process_provider_inbox(settings) -> dict:
    """Apply stored provider facts once. A crash before commit leaves the delivery receivable."""
    applied = 0
    rank = {"payment.succeeded": 0, "payment.failed": 1, "payment.returned": 2, "payment.processing": 3}
    for scope in _inbox_scopes(settings):
        with runtime_transaction(settings, scope["principal_id"], scope["organization_id"], uuid4()) as connection:
            pending = connection.execute(
                text("SELECT id, payload_kind FROM provider_events WHERE state = 'received' ORDER BY created_at")
            ).mappings().all()
        for item in sorted(pending, key=lambda row: (rank.get(row["payload_kind"], 9), str(row["id"]))):
            if not _apply_one_provider_event(settings, scope["principal_id"], scope["organization_id"], item["id"]):
                continue
            _fault("before_ack")
            with runtime_transaction(settings, scope["principal_id"], scope["organization_id"], uuid4()) as connection:
                connection.execute(
                    text("UPDATE provider_events SET state = 'applied' WHERE id = :id AND state = 'received'"),
                    {"id": item["id"]},
                )
            applied += 1
    return {"applied": applied, "money_moved": False, "real_values_activated": False}


def _callback_payment(connection, row, payload: dict) -> bool:
    order = connection.execute(
        text(
            "SELECT id, organization_id, public_reference, amount_minor, tenancy_code, state, obligation_id, idempotency_key "
            "FROM payment_orders WHERE public_reference = :reference FOR UPDATE"
        ),
        {"reference": row["effect_key"]},
    ).mappings().first()
    if order is None or str(order["organization_id"]) != str(row["organization_id"]):
        connection.execute(text("UPDATE provider_events SET state = 'quarantined' WHERE id = :id"), {"id": row["id"]})
        return False
    if payload.get("environment") not in {None, "local_fake"}:
        connection.execute(text("UPDATE provider_events SET state = 'quarantined' WHERE id = :id"), {"id": row["id"]})
        return False
    if payload.get("amount_minor") is not None and int(payload["amount_minor"]) != int(order["amount_minor"]):
        connection.execute(text("UPDATE provider_events SET state = 'quarantined' WHERE id = :id"), {"id": row["id"]})
        return False
    account_reference = connection.execute(
        text("SELECT account_reference FROM payment_obligations WHERE id = :id"),
        {"id": order["obligation_id"]},
    ).scalar()
    status = {"payment.succeeded": "succeeded", "payment.failed": "failed", "payment.processing": "processing"}[row["payload_kind"]]
    if order["state"] == "succeeded" and status != "succeeded":
        return True
    if order["state"] == "succeeded" and status == "succeeded":
        return True
    _apply_provider(
        connection,
        order["organization_id"],
        order["public_reference"],
        status,
        str(payload.get("provider_reference") or row["provider_event_id"]),
        account_reference,
        order["tenancy_code"],
        int(order["amount_minor"]),
        "callback",
    )
    if status == "succeeded":
        connection.execute(
            text(
                "UPDATE autopay_occurrences SET state = 'collected', reason = 'provider_confirmed', amount_minor = :amount "
                "WHERE state = 'scheduled' AND enrollment_id IN ("
                "SELECT id FROM autopay_enrollments WHERE tenancy_code = :tenancy) "
                "AND :key = 'autopay-' || :tenancy || '-' || period_code"
            ),
            {"amount": int(order["amount_minor"]), "tenancy": order["tenancy_code"], "key": order["idempotency_key"]},
        )
    return True


def _callback_return(connection, row, payload: dict) -> bool:
    order = connection.execute(
        text(
            "SELECT id, organization_id, public_reference, amount_minor, tenancy_code, state, ledger_reference, obligation_id "
            "FROM payment_orders WHERE public_reference = :reference FOR UPDATE"
        ),
        {"reference": str(payload.get("payment_reference") or "")},
    ).mappings().first()
    if order is None or order["state"] != "succeeded" or str(order["organization_id"]) != str(row["organization_id"]):
        return False
    existing = connection.execute(
        text("SELECT 1 FROM processor_disputes WHERE public_reference = :reference"),
        {"reference": row["effect_key"]},
    ).first()
    if existing is not None:
        return True
    amount = int(payload.get("amount_minor") or order["amount_minor"])
    if amount > _source_remaining(connection, order["id"], int(order["amount_minor"])):
        connection.execute(text("UPDATE provider_events SET state = 'quarantined' WHERE id = :id"), {"id": row["id"]})
        return False
    account_reference = connection.execute(
        text("SELECT account_reference FROM payment_obligations WHERE id = :id"),
        {"id": order["obligation_id"]},
    ).scalar()
    if account_reference and order["ledger_reference"]:
        account = _writable_account(connection, order["organization_id"], account_reference)
        _post(
            connection,
            order["organization_id"],
            account,
            "return",
            amount,
            [("debit", "receivable", amount), ("credit", "unapplied", amount)],
            tenancy_code=order["tenancy_code"],
        )
    connection.execute(
        text(
            "INSERT INTO processor_disputes "
            "(organization_id, id, public_reference, order_id, tenancy_code, amount_minor, reason_code, state) "
            "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, :order_id, :tenancy, :amount, 'ach_return', 'lost')"
        ),
        {
            "org": order["organization_id"],
            "reference": row["effect_key"],
            "order_id": order["id"],
            "tenancy": order["tenancy_code"],
            "amount": amount,
        },
    )
    _invalidate_returned_instrument(connection, order["tenancy_code"])
    return True


def integration_health(settings, actor, organization) -> dict:
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "payment.configure")
        _ensure_merchant(connection, organization)
        config = connection.execute(
            text(
                "SELECT entity_code, environment, provider, live_enabled, resident_surcharge, real_values_activated, zone_name "
                "FROM payment_merchant_configs LIMIT 1"
            )
        ).mappings().one()
    return {**dict(config), "sandbox_executed": False, "production": "not_authorized", "money_moved": False}
