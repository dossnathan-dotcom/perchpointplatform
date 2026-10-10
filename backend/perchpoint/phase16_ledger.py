"""Phase 16 operational resident subledger. Balances are derived. No money moves."""
from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .commands import CommandError
from .db import runtime_transaction
from .settings import Settings

STATEMENT_MARKER = "SYNTHETIC OPERATIONAL STATEMENT — NOT A TAX RETURN — NOT A FORMAL GENERAL LEDGER"


def _org(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _require(connection, capability: str) -> None:
    allowed = connection.execute(
        text("SELECT perchpoint.has_capability(:capability)"),
        {"capability": capability},
    ).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized.", False)


def _replay(connection, key: str, fingerprint: str) -> dict | None:
    existing = connection.execute(
        text("SELECT fingerprint, public_reference FROM ledger_intake_keys WHERE idempotency_key = :key"),
        {"key": key},
    ).first()
    if existing is None:
        return None
    if existing.fingerprint != fingerprint:
        raise CommandError(409, "conflict", "The ledger request could not be accepted.", False)
    return {"accepted": True, "reference": existing.public_reference, "replayed": True}


def _remember(connection, organization, key: str, fingerprint: str, reference: str) -> None:
    connection.execute(
        text(
            "INSERT INTO ledger_intake_keys (organization_id, idempotency_key, fingerprint, public_reference) "
            "VALUES (CAST(:org AS uuid), :key, :fingerprint, :reference)"
        ),
        {"org": organization, "key": key, "fingerprint": fingerprint, "reference": reference},
    )


def _account(connection, reference: str):
    row = connection.execute(
        text(
            "SELECT a.id, a.entity_code, p.id AS period_id, p.state AS period_state "
            "FROM resident_accounts a "
            "JOIN accounting_periods p ON p.organization_id = a.organization_id AND p.period_code = a.period_code "
            "WHERE a.public_reference = :reference"
        ),
        {"reference": reference},
    ).first()
    if row is None:
        raise CommandError(404, "missing", "The ledger account was not found.", False)
    return row


def _positions(connection, account_id) -> dict:
    row = connection.execute(
        text(
            "SELECT "
            "coalesce(sum(CASE WHEN category = 'receivable' AND side = 'debit' THEN amount_minor "
            "WHEN category = 'receivable' AND side = 'credit' THEN -amount_minor ELSE 0 END), 0) AS due_minor, "
            "coalesce(sum(CASE WHEN category = 'prepayment' AND side = 'credit' THEN amount_minor ELSE 0 END), 0) AS prepayment_minor, "
            "coalesce(sum(CASE WHEN category = 'deposit' AND side = 'debit' THEN amount_minor ELSE 0 END), 0) AS deposit_minor, "
            "coalesce(sum(CASE WHEN category = 'subsidy' AND side = 'debit' THEN amount_minor ELSE 0 END), 0) AS subsidy_minor "
            "FROM journal_lines WHERE transaction_id IN "
            "(SELECT id FROM journal_transactions WHERE account_id = :account_id)"
        ),
        {"account_id": account_id},
    ).one()
    return {
        "due_minor": int(row.due_minor),
        "prepayment_minor": int(row.prepayment_minor),
        "deposit_minor": int(row.deposit_minor),
        "subsidy_minor": int(row.subsidy_minor),
        "authoritative_balance_editable": False,
        "formal_general_ledger": False,
        "money_moved": False,
    }


def _post(connection, organization, account, kind: str, amount: int, lines: list[tuple[str, str, int]], reversal_of=None) -> str:
    if account.period_state != "open":
        raise CommandError(409, "conflict", "The accounting period is closed.", False)
    debit = sum(value for side, _category, value in lines if side == "debit")
    credit = sum(value for side, _category, value in lines if side == "credit")
    if debit != credit or debit != amount or amount < 1:
        raise CommandError(400, "invalid", "The journal transaction does not balance.", False)
    reference = f"journal-{uuid4().hex[:16]}"
    transaction_id = uuid4()
    try:
        connection.execute(
            text(
                "INSERT INTO journal_transactions "
                "(organization_id, id, account_id, period_id, public_reference, kind, reversal_of, amount_minor, money_moved) "
                "VALUES (CAST(:org AS uuid), :id, :account_id, :period_id, :reference, :kind, :reversal_of, :amount, false)"
            ),
            {
                "org": organization,
                "id": transaction_id,
                "account_id": account.id,
                "period_id": account.period_id,
                "reference": reference,
                "kind": kind,
                "reversal_of": reversal_of,
                "amount": amount,
            },
        )
    except IntegrityError as exc:
        raise CommandError(409, "conflict", "The ledger request could not be accepted.", False) from exc
    for side, category, value in lines:
        connection.execute(
            text(
                "INSERT INTO journal_lines (organization_id, id, transaction_id, side, category, amount_minor) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :transaction_id, :side, :category, :amount)"
            ),
            {"org": organization, "transaction_id": transaction_id, "side": side, "category": category, "amount": value},
        )
    return reference


def open_account(settings: Settings, actor, organization, reference: str, idempotency_key: str) -> dict:
    fingerprint = hashlib.sha256(f"{reference}:ledger".encode()).hexdigest()
    public_reference = f"account-{uuid4().hex[:16]}"
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        replay = _replay(connection, idempotency_key, fingerprint)
        if replay is not None:
            return {**replay, "state": "open"}
        membership = connection.execute(
            text("SELECT id, state FROM portal_memberships WHERE public_reference = :reference"),
            {"reference": reference},
        ).first()
        if membership is None or membership.state != "active":
            raise CommandError(409, "conflict", "Only an active household membership can open a ledger account.", False)
        period_code = f"2026-10-{uuid4().hex[:12]}"
        connection.execute(
            text(
                "INSERT INTO accounting_periods (organization_id, id, period_code, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :period, 'open')"
            ),
            {"org": organization, "period": period_code},
        )
        try:
            connection.execute(
                text(
                    "INSERT INTO resident_accounts "
                    "(organization_id, id, membership_id, public_reference, period_code, entity_code, state, currency_code) "
                    "VALUES (CAST(:org AS uuid), gen_random_uuid(), :membership_id, :reference, :period, 'example-homes', 'open', 'USD')"
                ),
                {"org": organization, "membership_id": membership.id, "reference": public_reference, "period": period_code},
            )
        except IntegrityError as exc:
            raise CommandError(409, "conflict", "The ledger request could not be accepted.", False) from exc
        _remember(connection, organization, idempotency_key, fingerprint, public_reference)
    return {"accepted": True, "reference": public_reference, "replayed": False, "state": "open", "currency_code": "USD"}


def post_charge(settings: Settings, actor, organization, reference: str, amount_minor: int, occurrence_code: str, idempotency_key: str) -> dict:
    if amount_minor < 1:
        raise CommandError(400, "invalid", "The charge amount must be a positive minor-unit integer.", False)
    fingerprint = hashlib.sha256(f"{reference}:{occurrence_code}:{amount_minor}".encode()).hexdigest()
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        replay = _replay(connection, idempotency_key, fingerprint)
        if replay is not None:
            return replay
        account = _account(connection, reference)
        try:
            connection.execute(
                text(
                    "INSERT INTO charge_schedules (organization_id, id, account_id, occurrence_code, amount_minor, category) "
                    "VALUES (CAST(:org AS uuid), gen_random_uuid(), :account_id, :occurrence, :amount, 'rent')"
                ),
                {"org": organization, "account_id": account.id, "occurrence": occurrence_code, "amount": amount_minor},
            )
        except IntegrityError as exc:
            raise CommandError(409, "conflict", "The ledger request could not be accepted.", False) from exc
        journal = _post(
            connection,
            organization,
            account,
            "charge",
            amount_minor,
            [("debit", "receivable", amount_minor), ("credit", "income", amount_minor)],
        )
        _remember(connection, organization, idempotency_key, fingerprint, journal)
        positions = _positions(connection, account.id)
    return {"accepted": True, "reference": journal, "replayed": False, **positions}


def post_subsidy(settings: Settings, actor, organization, reference: str, amount_minor: int, idempotency_key: str) -> dict:
    fingerprint = hashlib.sha256(f"{reference}:subsidy:{amount_minor}".encode()).hexdigest()
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        replay = _replay(connection, idempotency_key, fingerprint)
        if replay is not None:
            return replay
        account = _account(connection, reference)
        journal = _post(
            connection,
            organization,
            account,
            "subsidy",
            amount_minor,
            [("debit", "subsidy", amount_minor), ("credit", "income", amount_minor)],
        )
        _remember(connection, organization, idempotency_key, fingerprint, journal)
        positions = _positions(connection, account.id)
    return {"accepted": True, "reference": journal, "replayed": False, "resident_debt_created": False, **positions}


def post_deposit(settings: Settings, actor, organization, reference: str, amount_minor: int, idempotency_key: str) -> dict:
    fingerprint = hashlib.sha256(f"{reference}:deposit:{amount_minor}".encode()).hexdigest()
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        replay = _replay(connection, idempotency_key, fingerprint)
        if replay is not None:
            return replay
        account = _account(connection, reference)
        journal = _post(
            connection,
            organization,
            account,
            "deposit",
            amount_minor,
            [("debit", "deposit", amount_minor), ("credit", "liability", amount_minor)],
        )
        _remember(connection, organization, idempotency_key, fingerprint, journal)
        positions = _positions(connection, account.id)
    return {"accepted": True, "reference": journal, "replayed": False, "applied_to_rent": False, **positions}


def post_settlement(settings: Settings, actor, organization, reference: str, amount_minor: int, idempotency_key: str) -> dict:
    fingerprint = hashlib.sha256(f"{reference}:settlement:{amount_minor}".encode()).hexdigest()
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        replay = _replay(connection, idempotency_key, fingerprint)
        if replay is not None:
            return replay
        account = _account(connection, reference)
        due = _positions(connection, account.id)["due_minor"]
        applied = min(due, amount_minor)
        unapplied = amount_minor - applied
        lines: list[tuple[str, str, int]] = [("debit", "unapplied", amount_minor)]
        if applied:
            lines.append(("credit", "receivable", applied))
        if unapplied:
            lines.append(("credit", "prepayment", unapplied))
        journal = _post(connection, organization, account, "settlement", amount_minor, lines)
        connection.execute(
            text(
                "INSERT INTO ledger_allocations "
                "(organization_id, id, settlement_id, amount_applied_minor, amount_unapplied_minor) "
                "SELECT CAST(:org AS uuid), gen_random_uuid(), id, :applied, :unapplied "
                "FROM journal_transactions WHERE public_reference = :reference"
            ),
            {"org": organization, "applied": applied, "unapplied": unapplied, "reference": journal},
        )
        _remember(connection, organization, idempotency_key, fingerprint, journal)
        positions = _positions(connection, account.id)
    return {
        "accepted": True,
        "reference": journal,
        "replayed": False,
        "applied_minor": applied,
        "unapplied_minor": unapplied,
        "processor_called": False,
        **positions,
    }


def reverse_transaction(settings: Settings, actor, organization, reference: str, idempotency_key: str) -> dict:
    fingerprint = hashlib.sha256(f"{reference}:reversal".encode()).hexdigest()
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        replay = _replay(connection, idempotency_key, fingerprint)
        if replay is not None:
            return replay
        original = connection.execute(
            text(
                "SELECT id, account_id, kind, amount_minor FROM journal_transactions WHERE public_reference = :reference"
            ),
            {"reference": reference},
        ).first()
        if original is None or original.kind != "charge":
            raise CommandError(409, "conflict", "The ledger request could not be accepted.", False)
        account = connection.execute(
            text(
                "SELECT a.id, p.id AS period_id, p.state AS period_state FROM resident_accounts a "
                "JOIN accounting_periods p ON p.organization_id = a.organization_id AND p.period_code = a.period_code "
                "WHERE a.id = :account_id"
            ),
            {"account_id": original.account_id},
        ).one()
        original_count = connection.execute(
            text("SELECT count(*) FROM journal_lines WHERE transaction_id = :transaction_id"),
            {"transaction_id": original.id},
        ).scalar_one()
        journal = _post(
            connection,
            organization,
            account,
            "reversal",
            original.amount_minor,
            [("debit", "income", original.amount_minor), ("credit", "receivable", original.amount_minor)],
            reversal_of=original.id,
        )
        remaining = connection.execute(
            text("SELECT count(*) FROM journal_lines WHERE transaction_id = :transaction_id"),
            {"transaction_id": original.id},
        ).scalar_one()
        if remaining != original_count:
            raise CommandError(409, "conflict", "The ledger request could not be accepted.", False)
        _remember(connection, organization, idempotency_key, fingerprint, journal)
    return {"accepted": True, "reference": journal, "replayed": False, "original_lines_unchanged": True, "money_moved": False}


def submit_dispute(settings: Settings, actor, organization, reference: str, reason_code: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        account = _account(connection, reference)
        before = connection.execute(
            text("SELECT count(*) FROM journal_lines WHERE transaction_id IN (SELECT id FROM journal_transactions WHERE account_id = :account_id)"),
            {"account_id": account.id},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO ledger_disputes (organization_id, id, account_id, state, reason_code) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :account_id, 'submitted', :reason)"
            ),
            {"org": organization, "account_id": account.id, "reason": reason_code},
        )
        after = connection.execute(
            text("SELECT count(*) FROM journal_lines WHERE transaction_id IN (SELECT id FROM journal_transactions WHERE account_id = :account_id)"),
            {"account_id": account.id},
        ).scalar_one()
    return {"accepted": True, "state": "submitted", "legal_conclusion": False, "journal_lines_unchanged": before == after}


def issue_statement(settings: Settings, actor, organization, reference: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        account = _account(connection, reference)
        positions = _positions(connection, account.id)
        version = connection.execute(
            text("SELECT coalesce(max(version), 0) + 1 FROM resident_statements WHERE account_id = :account_id"),
            {"account_id": account.id},
        ).scalar_one()
        body = (
            f"{STATEMENT_MARKER}\n"
            f"Fictional account for Casey Synthetic at Example Homes. "
            f"Due {positions['due_minor']} minor units. "
            f"Deposit held {positions['deposit_minor']} minor units. "
            f"This artifact is not a tax return and no money moved."
        )
        content_hash = hashlib.sha256(body.encode()).hexdigest()
        connection.execute(
            text(
                "INSERT INTO resident_statements "
                "(organization_id, id, account_id, version, content_hash, due_minor, body) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :account_id, :version, :content_hash, :due, :body)"
            ),
            {
                "org": organization,
                "account_id": account.id,
                "version": version,
                "content_hash": content_hash,
                "due": positions["due_minor"],
                "body": body,
            },
        )
    return {"accepted": True, "version": int(version), "due_minor": positions["due_minor"], "body": body, "delivered": False}


def close_period(settings: Settings, actor, organization, reference: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        updated = connection.execute(
            text(
                "UPDATE accounting_periods SET state = 'closed' "
                "WHERE period_code = (SELECT period_code FROM resident_accounts WHERE public_reference = :reference) "
                "RETURNING state"
            ),
            {"reference": reference},
        ).first()
        if updated is None:
            raise CommandError(409, "conflict", "The ledger request could not be accepted.", False)
    return {"accepted": True, "state": "closed"}


def dry_run_manifest(settings: Settings, actor, organization, payload: dict) -> dict:
    blocked = {"secret", "credential", "password", "token"}
    if blocked.intersection(payload):
        raise CommandError(400, "invalid", "The manifest contains a value that cannot be activated.", False)
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        connection.execute(
            text(
                "INSERT INTO ledger_manifest_runs "
                "(organization_id, id, manifest_version, dry_run, real_values_activated) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), 1, true, false)"
            ),
            {"org": organization},
        )
    return {"accepted": True, "dry_run": True, "real_values_activated": False}


def reject_live_payment(settings: Settings, actor, organization) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
    raise CommandError(400, "invalid", "Live payment, refund, and processor settlement stay closed.", False)
