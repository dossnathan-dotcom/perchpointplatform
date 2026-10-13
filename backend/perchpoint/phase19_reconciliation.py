"""Phase 19 reconciliation observations.

A bank or processor row is evidence. It does not post a resident settlement or a
subsidy again, and it does not open a second ledger. No money moves.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from uuid import UUID, uuid4

from sqlalchemy import text

from .commands import CommandError
from .db import runtime_transaction
from .demo_catalog import HOUSEHOLDS, cohort_summary
from .phase17_payments import _fingerprint, _remember, _replay
from .settings import Settings

KINDS = {
    "processor_charge",
    "processor_fee",
    "processor_refund",
    "bank_deposit",
    "internal_transfer",
    "unknown",
    "assistance_evidence",
    "historical_observation",
    "residual",
}
DECIMAL = re.compile(r"-?\d+\.\d{2}")
MAX_MINOR = 100_000_000_00


def _org(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _require(connection, capability: str) -> None:
    allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized.", False)


def _minor(value, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or isinstance(value, float) or not isinstance(value, int):
        raise CommandError(400, "invalid", "Amounts must be exact integer USD minor units or a two-decimal string.", False)
    if value > MAX_MINOR or value < -MAX_MINOR or (value == 0 and not allow_zero):
        raise CommandError(400, "invalid", "That amount is outside the supported range.", False)
    return value


def parse_amount(value, *, allow_zero: bool = False) -> int:
    """Accept an integer minor amount or an exact two-decimal USD string. Never a float."""
    if isinstance(value, str):
        text_value = value.strip()
        if not DECIMAL.fullmatch(text_value):
            raise CommandError(400, "invalid", "A money string must be an exact two-decimal USD amount.", False)
        sign = -1 if text_value.startswith("-") else 1
        whole, fraction = text_value.lstrip("-").split(".")
        return _minor(sign * (int(whole) * 100 + int(fraction)), allow_zero=allow_zero)
    return _minor(value, allow_zero=allow_zero)


def _reference(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _fault(name: str) -> None:
    if os.environ.get("PHASE3_ENVIRONMENT", "local") not in {"local", "test"}:
        return
    if os.environ.get("PHASE19_FAULT") == name:
        raise RuntimeError("injected fault")


def _currency(value) -> str:
    code = str(value or "USD")
    if code != "USD":
        raise CommandError(400, "invalid", "This phase does not convert currency.", False)
    return code


def preview_lines(lines: list[dict]) -> dict:
    """Classify a feed without writing. A bank row is not a new resident or subsidy posting."""
    charges = fees = refunds = bank = transfers = unknown = 0
    for line in lines:
        kind = str(line.get("kind") or "")
        if kind not in KINDS or kind == "residual":
            raise CommandError(400, "invalid", "That line kind is not a reconciliation source.", False)
        amount = parse_amount(line.get("amount_minor"), allow_zero=False)
        if amount < 0:
            raise CommandError(400, "invalid", "Use a line kind for direction. Do not send a negative amount.", False)
        _currency(line.get("currency_code"))
        status = str(line.get("status") or "")
        if status not in {"pending", "posted"}:
            raise CommandError(400, "invalid", "A line is pending or posted.", False)
        if kind == "processor_charge":
            charges += amount
        elif kind == "processor_fee":
            fees += amount
        elif kind == "processor_refund":
            refunds += amount
        elif kind == "bank_deposit":
            bank += amount
        elif kind == "internal_transfer":
            transfers += amount
        elif kind == "unknown":
            unknown += amount
    net = charges - fees - refunds
    return {
        "accepted": True,
        "posted": False,
        "processor_net_minor": net,
        "bank_minor": bank,
        "residual_minor": net - bank,
        "unidentified_minor": unknown,
        "internal_transfer_minor": transfers,
        "revenue_journal_count": 0,
        "money_moved": False,
        "real_values_activated": False,
    }


def _journal_count(connection) -> int:
    return int(connection.execute(text("SELECT count(*) FROM journal_transactions")).scalar_one())


def import_lines(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    lines = body.get("lines")
    if not isinstance(lines, list) or not lines:
        raise CommandError(400, "invalid", "A reconciliation import needs at least one line.", False)
    summary = preview_lines(lines)
    source_reference = str(body.get("source_reference") or "").strip()
    if not source_reference:
        raise CommandError(400, "invalid", "Name the processor or bank source.", False)
    key = str(body.get("idempotency_key") or "")
    fingerprint = _fingerprint([source_reference, json.dumps(lines, sort_keys=True, default=str)])
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "payment.charge")
        replay = _replay(connection, key, fingerprint)
        if replay:
            replay.update(summary)
            replay["posted"] = False
            return replay
        before = _journal_count(connection)
        source_kind = str(body.get("source_kind") or "bank")
        if source_kind not in {"processor", "bank"}:
            raise CommandError(400, "invalid", "A source is a processor or a bank.", False)
        refresh_state = str(body.get("refresh_state") or "current")
        if refresh_state not in {"current", "stale"}:
            raise CommandError(400, "invalid", "A source is current or stale.", False)
        source_id = uuid4()
        source_public = _reference("source")
        connection.execute(
            text(
                "INSERT INTO reconciliation_sources (organization_id, id, public_reference, label, kind, refresh_state, environment, money_moved, real_values_activated) "
                "VALUES (:org, :id, :reference, :label, :kind, :refresh, 'local_fake', false, false)"
            ),
            {
                "org": organization,
                "id": source_id,
                "reference": source_public,
                "label": source_reference,
                "kind": source_kind,
                "refresh": refresh_state,
            },
        )
        stored = []
        for line in lines:
            external_id = str(line.get("external_id") or "").strip()
            if not external_id:
                raise CommandError(400, "invalid", "Each line needs a source identity.", False)
            existing = connection.execute(
                text(
                    "SELECT public_reference, amount_minor, kind FROM reconciliation_lines "
                    "WHERE source_reference = :source AND external_id = :external"
                ),
                {"source": source_reference, "external": external_id},
            ).mappings().first()
            amount = parse_amount(line.get("amount_minor"))
            kind = str(line["kind"])
            if existing:
                if int(existing["amount_minor"]) != amount or existing["kind"] != kind:
                    raise CommandError(409, "conflict", "That source line already exists with different amounts.", False)
                stored.append({"reference": existing["public_reference"], "replayed": True})
                continue
            reference = _reference("line")
            connection.execute(
                text(
                    "INSERT INTO reconciliation_lines (organization_id, id, public_reference, source_reference, external_id, kind, amount_minor, currency_code, status, link_reference, environment, money_moved, real_values_activated) "
                    "VALUES (:org, :id, :reference, :source, :external, :kind, :amount, 'USD', :status, :link, 'local_fake', false, false)"
                ),
                {
                    "org": organization,
                    "id": uuid4(),
                    "reference": reference,
                    "source": source_reference,
                    "external": external_id,
                    "kind": kind,
                    "amount": amount,
                    "status": line["status"],
                    "link": line.get("link_reference"),
                },
            )
            stored.append({"reference": reference, "replayed": False, "kind": kind})
        if summary["residual_minor"] > 0:
            residual_external = f"{source_reference}:residual"
            existing_residual = connection.execute(
                text("SELECT public_reference FROM reconciliation_lines WHERE source_reference = :source AND external_id = :external"),
                {"source": source_reference, "external": residual_external},
            ).scalar()
            if existing_residual:
                stored.append({"reference": existing_residual, "replayed": True, "kind": "residual"})
            else:
                reference = _reference("line")
                connection.execute(
                    text(
                        "INSERT INTO reconciliation_lines (organization_id, id, public_reference, source_reference, external_id, kind, amount_minor, currency_code, status, environment, money_moved, real_values_activated) "
                        "VALUES (:org, :id, :reference, :source, :external, 'residual', :amount, 'USD', 'posted', 'local_fake', false, false)"
                    ),
                    {
                        "org": organization,
                        "id": uuid4(),
                        "reference": reference,
                        "source": source_reference,
                        "external": residual_external,
                        "amount": summary["residual_minor"],
                    },
                )
                stored.append({"reference": reference, "replayed": False, "kind": "residual"})
        _fault("before_commit")
        after = _journal_count(connection)
        if after != before:
            raise CommandError(409, "conflict", "A reconciliation import must not post a journal.", False)
        batch = _reference("import")
        _remember(connection, organization, key, fingerprint, batch)
        summary.update({"reference": batch, "source_reference": source_public, "lines": stored, "replayed": False, "posted": False})
        return summary


def match_line(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    amount = parse_amount(body.get("amount_minor"))
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "payment.charge")
        line = connection.execute(
            text(
                "SELECT id, amount_minor, matched_minor, kind FROM reconciliation_lines "
                "WHERE public_reference = :reference FOR UPDATE"
            ),
            {"reference": str(body.get("line_reference") or "")},
        ).mappings().first()
        if line is None:
            raise CommandError(404, "missing", "That reconciliation line is not in this organization.", False)
        remaining = int(line["amount_minor"]) - int(line["matched_minor"])
        if amount > remaining:
            raise CommandError(409, "conflict", "That allocation would use the same capacity twice.", False)
        connection.execute(
            text(
                "INSERT INTO reconciliation_matches (organization_id, id, line_id, target_reference, amount_minor) "
                "VALUES (:org, :id, :line, :target, :amount)"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "line": line["id"],
                "target": str(body.get("target_reference") or ""),
                "amount": amount,
            },
        )
        connection.execute(
            text("UPDATE reconciliation_lines SET matched_minor = matched_minor + :amount WHERE id = :id"),
            {"amount": amount, "id": line["id"]},
        )
        return {"accepted": True, "remaining_minor": remaining - amount, "money_moved": False, "posted": False}


def queue(settings: Settings, actor, organization, query: str | None) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "payment.read")
        clause = ""
        params: dict = {}
        if query:
            clause = "AND (public_reference ILIKE :q OR external_id ILIKE :q OR kind ILIKE :q OR coalesce(link_reference, '') ILIKE :q)"
            params["q"] = f"%{query.strip()}%"
        rows = connection.execute(
            text(
                "SELECT public_reference, external_id, kind, amount_minor, status, version, owner_actor, link_reference "
                f"FROM reconciliation_lines WHERE kind IN ('unknown', 'residual', 'internal_transfer') {clause} "
                "ORDER BY created_at"
            ),
            params,
        ).mappings().all()
    return {
        "items": [dict(row) for row in rows],
        "empty": not rows,
        "money_moved": False,
    }


def claim(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "payment.charge")
        updated = connection.execute(
            text(
                "UPDATE reconciliation_lines SET owner_actor = perchpoint.current_actor(), version = version + 1 "
                "WHERE public_reference = :reference AND version = :version "
                "RETURNING public_reference, version, owner_actor"
            ),
            {"reference": str(body.get("line_reference") or ""), "version": int(body.get("version") or 0)},
        ).mappings().first()
        if updated is None:
            raise CommandError(409, "conflict", "That queue item changed. Refresh it and try again.", False)
        return {"accepted": True, "reference": updated["public_reference"], "version": int(updated["version"]), "money_moved": False}


def _october() -> dict:
    summary = cohort_summary()
    named = {row["home_label"]: row for row in HOUSEHOLDS}
    maple = named["Maple Court 101"]
    return {
        "as_of": summary["as_of"],
        "owed_minor": summary["past_due_minor"],
        "sycamore_minor": named["Sycamore House"]["past_due_minor"],
        "brookside_minor": named["Brookside House"]["past_due_minor"],
        "maple_court_101_due_minor": maple["due_minor"],
        "maple_court_101_resident": maple["person_label"],
        "homes": summary["homes"],
        "households": summary["households"],
    }


def _positions(connection) -> dict:
    rows = connection.execute(
        text(
            "SELECT kind, status, coalesce(sum(amount_minor), 0) AS amount "
            "FROM reconciliation_lines GROUP BY kind, status"
        )
    ).mappings().all()
    totals = {(row["kind"], row["status"]): int(row["amount"]) for row in rows}
    pending = sum(amount for (kind, status), amount in totals.items() if status == "pending")
    bank = sum(amount for (kind, status), amount in totals.items() if kind == "bank_deposit" and status == "posted")
    paid_out = sum(amount for (kind, status), amount in totals.items() if kind == "processor_refund")
    unknown = sum(amount for (kind, status), amount in totals.items() if kind == "unknown")
    transfers = sum(amount for (kind, status), amount in totals.items() if kind == "internal_transfer")
    residual = sum(amount for (kind, status), amount in totals.items() if kind == "residual")
    stale = connection.execute(
        text("SELECT public_reference, label FROM reconciliation_sources WHERE refresh_state = 'stale' ORDER BY label")
    ).mappings().all()
    owners = connection.execute(
        text(
            "SELECT public_reference, kind, amount_minor FROM reconciliation_lines "
            "WHERE owner_actor IS NOT NULL ORDER BY public_reference"
        )
    ).mappings().all()
    october = _october()
    return {
        "owed_minor": october["owed_minor"],
        "processing_minor": pending,
        "paid_out_minor": paid_out,
        "at_bank_minor": bank,
        "unidentified_minor": unknown,
        "internal_transfer_minor": transfers,
        "residual_minor": residual,
        "decisions": residual + unknown,
        "exposure_minor": unknown + residual,
        "owners": [dict(row) for row in owners],
        "stale_sources": [dict(row) for row in stale],
        "october": october,
        "revenue_from_internal_transfer_minor": 0,
        "money_moved": False,
        "real_values_activated": False,
    }


def briefing(settings: Settings, actor, organization) -> dict:
    organization = _org(organization)
    try:
        _fault("refresh")
    except RuntimeError:
        with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
            _require(connection, "payment.read")
            previous = connection.execute(
                text("SELECT public_reference, body FROM reconciliation_snapshots ORDER BY created_at DESC LIMIT 1")
            ).mappings().first()
        if previous is None:
            raise CommandError(503, "unavailable", "The briefing could not be refreshed, and there is no earlier snapshot.", True)
        body = previous["body"] if isinstance(previous["body"], dict) else json.loads(previous["body"])
        body["refresh_failed"] = True
        body["reference"] = previous["public_reference"]
        return body
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "payment.read")
        body = _positions(connection)
        reference = _reference("briefing")
        body["reference"] = reference
        body["refresh_failed"] = False
        body["acknowledged"] = False
        connection.execute(
            text(
                "INSERT INTO reconciliation_snapshots (organization_id, id, public_reference, body) "
                "VALUES (:org, :id, :reference, CAST(:body AS jsonb))"
            ),
            {"org": organization, "id": uuid4(), "reference": reference, "body": json.dumps(body)},
        )
        return body


def acknowledge(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    reference = str(body.get("snapshot_reference") or "")
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "payment.read")
        snapshot = connection.execute(
            text("SELECT body FROM reconciliation_snapshots WHERE public_reference = :reference"),
            {"reference": reference},
        ).mappings().first()
        if snapshot is None:
            raise CommandError(404, "missing", "That briefing snapshot is not in this organization.", False)
        connection.execute(
            text(
                "INSERT INTO reconciliation_acknowledgements (organization_id, id, snapshot_reference, actor_id) "
                "VALUES (:org, :id, :reference, perchpoint.current_actor())"
            ),
            {"org": organization, "id": uuid4(), "reference": reference},
        )
        stored = snapshot["body"] if isinstance(snapshot["body"], dict) else json.loads(snapshot["body"])
        return {
            "accepted": True,
            "resolved": False,
            "reference": reference,
            "decisions": stored.get("decisions"),
            "money_moved": False,
        }


def prepare_close(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    reference = str(body.get("snapshot_reference") or "")
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "payment.charge")
        snapshot = connection.execute(
            text("SELECT body FROM reconciliation_snapshots WHERE public_reference = :reference"),
            {"reference": reference},
        ).mappings().first()
        if snapshot is None:
            raise CommandError(404, "missing", "That briefing snapshot is not in this organization.", False)
        packet = snapshot["body"] if isinstance(snapshot["body"], dict) else json.loads(snapshot["body"])
        version = int(
            connection.execute(
                text("SELECT coalesce(max(version), 0) FROM reconciliation_closes WHERE snapshot_reference = :reference"),
                {"reference": reference},
            ).scalar_one()
        ) + 1
        digest = hashlib.sha256(json.dumps(packet, sort_keys=True, default=str).encode()).hexdigest()
        public = _reference("close")
        connection.execute(
            text(
                "INSERT INTO reconciliation_closes (organization_id, id, public_reference, snapshot_reference, version, state, preparer_actor, packet, packet_sha) "
                "VALUES (:org, :id, :public, :snapshot, :version, 'draft', perchpoint.current_actor(), CAST(:packet AS jsonb), :sha)"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "public": public,
                "snapshot": reference,
                "version": version,
                "packet": json.dumps(packet, default=str),
                "sha": digest,
            },
        )
        return {"accepted": True, "reference": public, "version": version, "state": "draft", "packet_sha": digest, "money_moved": False}


def issue_close(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "payment.exception")
        draft = connection.execute(
            text(
                "SELECT snapshot_reference, version, preparer_actor, packet, packet_sha "
                "FROM reconciliation_closes WHERE public_reference = :reference AND state = 'draft'"
            ),
            {"reference": str(body.get("close_reference") or "")},
        ).mappings().first()
        if draft is None:
            raise CommandError(404, "missing", "That draft close is not in this organization.", False)
        reviewer = connection.execute(text("SELECT perchpoint.current_actor()")).scalar_one()
        if str(reviewer) == str(draft["preparer_actor"]):
            raise CommandError(403, "denied", "The person who prepared this close cannot approve it.", False)
        version = int(draft["version"]) + 1
        public = _reference("close")
        packet = draft["packet"] if isinstance(draft["packet"], dict) else json.loads(draft["packet"])
        connection.execute(
            text(
                "INSERT INTO reconciliation_closes (organization_id, id, public_reference, snapshot_reference, version, state, preparer_actor, reviewer_actor, packet, packet_sha) "
                "VALUES (:org, :id, :public, :snapshot, :version, 'issued', :preparer, perchpoint.current_actor(), CAST(:packet AS jsonb), :sha)"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "public": public,
                "snapshot": draft["snapshot_reference"],
                "version": version,
                "preparer": draft["preparer_actor"],
                "packet": json.dumps(packet, default=str),
                "sha": draft["packet_sha"],
            },
        )
        return {
            "accepted": True,
            "reference": public,
            "version": version,
            "state": "issued",
            "packet_sha": draft["packet_sha"],
            "money_moved": False,
        }


def packet(settings: Settings, actor, organization, reference: str) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "payment.read")
        row = connection.execute(
            text(
                "SELECT public_reference, version, state, packet, packet_sha FROM reconciliation_closes "
                "WHERE public_reference = :reference"
            ),
            {"reference": reference},
        ).mappings().first()
        if row is None:
            raise CommandError(404, "missing", "That close packet is not in this organization.", False)
        body = row["packet"] if isinstance(row["packet"], dict) else json.loads(row["packet"])
        return {
            "reference": row["public_reference"],
            "version": int(row["version"]),
            "state": row["state"],
            "packet_sha": row["packet_sha"],
            "packet": body,
            "money_moved": False,
        }
