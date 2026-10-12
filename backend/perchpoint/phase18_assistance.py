"""Phase 18 digital receipts and housing-assistance schedules.

The Phase 16 ledger remains the financial authority. A resident report is a case.
An agency deposit is not a second resident charge, and it is not a manufactured Stripe payment.
Cash, check, and money-order intake stay closed. No money moves in this local phase.
"""
from __future__ import annotations

import html
import os
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .commands import CommandError
from .db import engine_for, runtime_transaction
from .phase16_ledger import _account, _positions, _post
from .demo_catalog import HOUSEHOLDS
from .phase17_payments import _fingerprint, _household, _may_act_for_tenancy, _primary_account, _remember, _replay, publish_charge
from .settings import Settings

PHYSICAL = {"cash", "check", "money_order", "money-order"}
NO_RESIDENT_SETTLEMENT = {"cash_balance.funded", "customer_cash_balance_transaction.created", "payout.paid"}
RESIDENT_SETTLEMENT = {"payment_intent.succeeded"}
RULE_VERSION = "phase18-exact-v1"
INSTRUCTION_MARKER = "SYNTHETIC BANK INSTRUCTIONS — DO NOT SEND REAL FUNDS"
MAX_MINOR = 100_000_000_00


def _org(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _minor(value, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CommandError(400, "invalid", "Amounts must be integer USD minor units.", False)
    if value > MAX_MINOR or value < 0 or (value == 0 and not allow_zero):
        raise CommandError(400, "invalid", "That amount is outside the supported range.", False)
    return value


def _require(connection, capability: str) -> None:
    allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized.", False)


def _dollars(minor: int) -> str:
    value = int(minor)
    sign = "-" if value < 0 else ""
    value = abs(value)
    return f"{sign}${value // 100}.{value % 100:02d}"


def _display(tenancy_code: str | None) -> str | None:
    if not tenancy_code:
        return None
    row = _household(tenancy_code)
    if row is None:
        return None
    return f"{row['person_label']} — {row['home_label']}"


def _next_action(kind: str, state: str | None = None) -> str:
    if state == "unmatched":
        return "Assign the household and period"
    if state == "queued":
        return "Apply the exact match"
    if state == "review" or kind == "review":
        return "A person needs to review this"
    if kind == "resident_overpayment":
        return "Review the required return"
    if kind == "agency_delay":
        return "Follow up with the agency"
    return "Review the open item"


def _require_any(connection, capabilities: tuple[str, ...]) -> None:
    for capability in capabilities:
        allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
        if allowed:
            return
    raise CommandError(403, "denied", "This action is not authorized.", False)


def stripe_effect(kind: str) -> str:
    """The resident settlement is recognized once, when the payment is applied.

    Funding a Stripe cash balance, and a later payout of collections to the bank,
    are observations. They do not create another resident settlement.
    """
    if kind in RESIDENT_SETTLEMENT:
        return "resident_settlement"
    if kind in NO_RESIDENT_SETTLEMENT:
        return "no_resident_settlement"
    return "review"


def cash_app_payment_intent_params(amount_minor: int) -> dict:
    """Request shape for Cash App Pay through the pinned Stripe PaymentIntent path.

    Live eligibility is an activation check. This does not call Stripe.
    """
    _minor(amount_minor)
    return {
        "amount": amount_minor,
        "currency": "usd",
        "payment_method_types": ["cashapp"],
        "confirm": False,
    }


def configuration() -> dict:
    return {
        "collecting_entity": "HawkVision LLC",
        "collecting_entity_status": "provisional",
        "physical_intake": False,
        "zelle": {
            "available": False,
            "reason": "No supported business-bank Zelle feed is configured. Evidence can be imported and reviewed.",
        },
        "cash_app": {"mode": "stripe_method", "live_eligibility": "activation"},
        "bank_transfer": {"mode": "instructions", "creates_debit_mandate": False, "synthetic": True},
        "ach_debit": {"mode": "consent", "same_as_bank_transfer": False},
        "programs": {"hcv": "synthetic_demonstration", "pbv": "not_configured", "pbra": "not_configured"},
        "auto_post_rule": RULE_VERSION,
        "real_values_activated": False,
        "money_moved": False,
    }


def _split(body: dict) -> dict:
    program = body.get("program_kind") or "hcv"
    if program != "hcv":
        raise CommandError(409, "conflict", "That assistance program workflow is not configured.", False)
    rent = _minor(int(body["rent_to_owner_minor"]))
    resident = _minor(int(body["resident_minor"]), allow_zero=True)
    agency = _minor(int(body["agency_minor"]), allow_zero=True)
    utility_allowance = _minor(int(body.get("utility_allowance_minor") or 0), allow_zero=True)
    utility_reimbursement = _minor(int(body.get("utility_reimbursement_minor") or 0), allow_zero=True)
    if resident + agency != rent:
        raise CommandError(400, "invalid", "The resident and agency portions must equal the rent-to-owner amount.", False)
    period = str(body.get("service_period") or "")
    if len(period) != 7 or period[4] != "-":
        raise CommandError(400, "invalid", "A service period uses YYYY-MM.", False)
    return {
        "program": program,
        "rent": rent,
        "resident": resident,
        "agency": agency,
        "utility_allowance": utility_allowance,
        "utility_reimbursement": utility_reimbursement,
        "period": period,
        "tenancy": str(body["tenancy_code"]),
        "account": body.get("account_reference"),
        "agency_name": str(body.get("agency_name") or "Synthetic housing agency"),
    }


def record_determination(settings: Settings, actor, organization, body: dict) -> dict:
    parts = _split(body)
    if parts["resident"] > 0 and not parts["account"]:
        raise CommandError(400, "invalid", "A resident portion needs the household ledger account.", False)
    fingerprint = _fingerprint(
        [parts["tenancy"], parts["period"], parts["rent"], parts["resident"], parts["agency"], body["idempotency_key"]]
    )
    reference = f"determination-{uuid4().hex[:16]}"
    obligation = None
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        existing = _replay(connection, body["idempotency_key"], fingerprint)
        if existing is not None:
            return existing
        prior_row = connection.execute(
            text(
                "SELECT 1 FROM assistance_determinations "
                "WHERE tenancy_code = :tenancy AND service_period = :period AND state = 'approved'"
            ),
            {"tenancy": parts["tenancy"], "period": parts["period"]},
        ).first()
    if prior_row is None and parts["resident"] > 0:
        published = publish_charge(
            settings,
            actor,
            organization,
            {
                "tenancy_code": parts["tenancy"],
                "amount_minor": parts["resident"],
                "category": "rent",
                "description": f"Resident rent portion for {parts['period']}",
                "account_reference": parts["account"],
                "rent_basis_minor": parts["resident"],
                "idempotency_key": f"{body['idempotency_key']}:resident",
            },
        )
        obligation = published["reference"]
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        replay = _replay(connection, body["idempotency_key"], fingerprint)
        if replay is not None:
            return replay
        prior = connection.execute(
            text(
                "SELECT id, version, resident_minor, agency_received_minor, obligation_reference, household_label "
                "FROM assistance_determinations "
                "WHERE tenancy_code = :tenancy AND service_period = :period AND state = 'approved' "
                "FOR UPDATE"
            ),
            {"tenancy": parts["tenancy"], "period": parts["period"]},
        ).mappings().first()
        version = 1 if prior is None else int(prior["version"]) + 1
        received = 0 if prior is None else int(prior["agency_received_minor"])
        if prior is not None:
            connection.execute(
                text("UPDATE assistance_determinations SET state = 'superseded' WHERE id = :id"),
                {"id": prior["id"]},
            )
            _revise_resident(connection, organization, prior, parts, body)
            obligation = prior["obligation_reference"]
            if parts["resident"] > int(prior["resident_minor"]):
                connection.execute(
                    text(
                        "INSERT INTO assistance_exceptions "
                        "(organization_id, id, public_reference, tenancy_code, service_period, kind, amount_minor, detail, state) "
                        "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, :tenancy, :period, 'review', :amount, :detail, 'open')"
                    ),
                    {
                        "org": organization,
                        "reference": f"exception-{uuid4().hex[:16]}",
                        "tenancy": parts["tenancy"],
                        "period": parts["period"],
                        "amount": parts["resident"] - int(prior["resident_minor"]),
                        "detail": "The resident portion increased. Autopay consent was not expanded.",
                    },
                )
        try:
            connection.execute(
                text(
                    "INSERT INTO assistance_determinations "
                    "(organization_id, id, public_reference, tenancy_code, account_reference, program_kind, agency_name, "
                    "household_label, service_period, version, rent_to_owner_minor, resident_minor, agency_minor, "
                    "utility_allowance_minor, utility_reimbursement_minor, agency_received_minor, obligation_reference, state, supersedes) "
                    "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, :tenancy, :account, :program, :agency, "
                    ":label, :period, :version, :rent, :resident, :agency_minor, :allowance, :reimbursement, :received, :obligation, "
                    "'approved', :supersedes)"
                ),
                {
                    "org": organization,
                    "reference": reference,
                    "tenancy": parts["tenancy"],
                    "account": parts["account"],
                    "program": parts["program"],
                    "agency": parts["agency_name"],
                    "label": str(body.get("household_label") or "").strip() or (None if prior is None else prior["household_label"]),
                    "period": parts["period"],
                    "version": version,
                    "rent": parts["rent"],
                    "resident": parts["resident"],
                    "agency_minor": parts["agency"],
                    "allowance": parts["utility_allowance"],
                    "reimbursement": parts["utility_reimbursement"],
                    "received": received,
                    "obligation": obligation,
                    "supersedes": None if prior is None else prior["id"],
                },
            )
        except IntegrityError as exc:
            raise CommandError(409, "conflict", "That assistance schedule was not accepted.", False) from exc
        resident_email = str(body.get("resident_email") or "").strip()
        if resident_email and obligation:
            resident_id = _primary_account(settings, resident_email)
            if resident_id is None:
                raise CommandError(400, "invalid", "That resident sign-in was not found.", False)
            connection.execute(
                text("UPDATE payment_obligations SET primary_account_id = :resident WHERE public_reference = :reference"),
                {"resident": resident_id, "reference": obligation},
            )
        _remember(connection, organization, body["idempotency_key"], fingerprint, reference)
    return {
        "accepted": True,
        "reference": reference,
        "replayed": False,
        "resident_obligation": obligation,
        "resident_minor": parts["resident"],
        "agency_minor": parts["agency"],
        "version": version,
        "money_moved": False,
        "real_values_activated": False,
    }


def _revise_resident(connection, organization, prior, parts, body) -> None:
    old_resident = int(prior["resident_minor"])
    new_resident = parts["resident"]
    if new_resident >= old_resident or not prior["obligation_reference"]:
        return
    obligation = connection.execute(
        text("SELECT id, amount_minor FROM payment_obligations WHERE public_reference = :reference FOR UPDATE"),
        {"reference": prior["obligation_reference"]},
    ).mappings().first()
    if obligation is None:
        return
    collected = int(
        connection.execute(
            text(
                "SELECT coalesce(sum(amount_minor), 0) FROM payment_orders "
                "WHERE obligation_id = :id AND state = 'succeeded'"
            ),
            {"id": obligation["id"]},
        ).scalar()
        or 0
    )
    if new_resident == 0 and collected == 0:
        account = _account(connection, parts["account"])
        _post(
            connection,
            organization,
            account,
            "waiver",
            old_resident,
            [("debit", "income", old_resident), ("credit", "receivable", old_resident)],
            tenancy_code=parts["tenancy"],
        )
        connection.execute(text("UPDATE payment_obligations SET state = 'held' WHERE id = :id"), {"id": obligation["id"]})
        return
    returned = int(
        connection.execute(
            text(
                "SELECT coalesce(sum(amount_minor), 0) FROM assistance_exceptions "
                "WHERE tenancy_code = :tenancy AND kind = 'required_return' AND state = 'resolved'"
            ),
            {"tenancy": parts["tenancy"]},
        ).scalar()
        or 0
    )
    excess = collected - returned - new_resident
    if excess > 0:
        connection.execute(
            text(
                "INSERT INTO assistance_exceptions "
                "(organization_id, id, public_reference, tenancy_code, service_period, kind, amount_minor, detail, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, :tenancy, :period, 'resident_overpayment', :amount, :detail, 'open')"
            ),
            {
                "org": organization,
                "reference": f"exception-{uuid4().hex[:16]}",
                "tenancy": parts["tenancy"],
                "period": parts["period"],
                "amount": excess,
                "detail": "A revised resident portion is below the amount already paid. No agency receipt was created.",
            },
        )
        return
    waiver = old_resident - new_resident
    account = _account(connection, parts["account"])
    _post(
        connection,
        organization,
        account,
        "waiver",
        waiver,
        [("debit", "income", waiver), ("credit", "receivable", waiver)],
        tenancy_code=parts["tenancy"],
    )
    connection.execute(
        text("UPDATE payment_obligations SET amount_minor = :amount WHERE id = :id"),
        {"amount": new_resident, "id": obligation["id"]},
    )


def report_transfer(settings: Settings, actor, organization, body: dict) -> dict:
    amount = _minor(int(body["amount_minor"]))
    explanation = str(body.get("explanation") or "").strip()
    reference_text = str(body.get("reference_text") or "").strip()
    if len(explanation) < 3 or len(reference_text) < 3:
        raise CommandError(400, "invalid", "A transfer report needs a reference and an explanation.", False)
    fingerprint = _fingerprint([body["tenancy_code"], amount, reference_text, body["idempotency_key"]])
    reference = f"report-{uuid4().hex[:16]}"
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.pay", "payment.charge"))
        if not _may_act_for_tenancy(connection, str(body["tenancy_code"]), grant_counts=True):
            raise CommandError(403, "denied", "This household is not available for this sign-in.", False)
        replay = _replay(connection, body["idempotency_key"], fingerprint)
        if replay is not None:
            return replay
        connection.execute(
            text(
                "INSERT INTO transfer_reports "
                "(organization_id, id, public_reference, tenancy_code, amount_minor, reference_text, explanation, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, :tenancy, :amount, :note, :explanation, 'reported')"
            ),
            {
                "org": organization,
                "reference": reference,
                "tenancy": str(body["tenancy_code"]),
                "amount": amount,
                "note": reference_text,
                "explanation": explanation,
            },
        )
        _remember(connection, organization, body["idempotency_key"], fingerprint, reference)
    return {
        "accepted": True,
        "reference": reference,
        "state": "reported",
        "payment_posted": False,
        "replayed": False,
        "money_moved": False,
    }


def _effect_for(source: str, kind: str | None, method: str) -> tuple[str, str, str]:
    if source == "historical_import":
        return "historical", "staged", "excluded"
    if source == "zelle_evidence":
        return "agency_cash", "pending", "review"
    if source == "stripe":
        effect = stripe_effect(kind or "")
        if effect == "review":
            raise CommandError(400, "invalid", "That Stripe observation needs an explicit kind.", False)
        return effect, "confirmed", "excluded"
    if method in PHYSICAL:
        raise CommandError(400, "invalid", "Cash, check, and money-order payments are not accepted.", False)
    return "agency_cash", "confirmed", "queued"


def ingest_receipt(settings: Settings, actor, organization, body: dict) -> dict:
    source = str(body.get("source") or "")
    method = str(body.get("method") or "")
    if source not in {"stripe", "business_bank", "agency_remittance", "zelle_evidence", "historical_import"}:
        raise CommandError(400, "invalid", "That receipt source is not supported.", False)
    if method in PHYSICAL and source != "historical_import":
        raise CommandError(400, "invalid", "Cash, check, and money-order payments are not accepted.", False)
    if source != "historical_import" and method in PHYSICAL:
        raise CommandError(400, "invalid", "Cash, check, and money-order payments are not accepted.", False)
    amount = _minor(int(body["amount_minor"]))
    purpose = str(body.get("purpose") or ("historical" if source == "historical_import" else "rent_assistance"))
    if purpose == "utility_reimbursement":
        application = "excluded"
    effect, state, application = _effect_for(source, body.get("stripe_kind"), method)
    if purpose == "utility_reimbursement":
        application = "excluded"
    if purpose == "resident_rent":
        effect, state, application = "resident_settlement", "confirmed", "queued"
    if not body.get("tenancy_code") or not body.get("service_period"):
        if application == "queued":
            application = "unmatched"
    economic = str(body.get("external_id") or "").strip()
    if len(economic) < 3:
        raise CommandError(400, "invalid", "A receipt needs a stable source identifier.", False)
    fingerprint = _fingerprint([source, economic, amount, body["idempotency_key"]])
    reference = f"receipt-{uuid4().hex[:16]}"
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        replay = _replay(connection, body["idempotency_key"], fingerprint)
        if replay is not None:
            return replay
        existing = connection.execute(
            text(
                "SELECT public_reference, application_state FROM digital_receipts "
                "WHERE source = :source AND economic_key = :key"
            ),
            {"source": source, "key": economic},
        ).mappings().first()
        if existing is not None:
            _remember(connection, organization, body["idempotency_key"], fingerprint, existing["public_reference"])
            return {
                "accepted": True,
                "reference": existing["public_reference"],
                "replayed": True,
                "application_state": existing["application_state"],
                "money_moved": False,
            }
        connection.execute(
            text(
                "INSERT INTO digital_receipts "
                "(organization_id, id, public_reference, source, economic_key, method, amount_minor, currency_code, "
                "tenancy_code, service_period, purpose, effect_class, state, application_state, environment, money_moved, real_values_activated) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, :source, :key, :method, :amount, 'USD', "
                ":tenancy, :period, :purpose, :effect, :state, :application, 'local_fake', false, false)"
            ),
            {
                "org": organization,
                "reference": reference,
                "source": source,
                "key": economic,
                "method": method or "digital",
                "amount": amount,
                "tenancy": body.get("tenancy_code"),
                "period": body.get("service_period"),
                "purpose": purpose,
                "effect": effect,
                "state": state,
                "application": application,
            },
        )
        if purpose == "resident_rent" and body.get("tenancy_code"):
            connection.execute(
                text(
                    "UPDATE transfer_reports SET state = 'matched' "
                    "WHERE tenancy_code = :tenancy AND state = 'reported' AND amount_minor = :amount"
                ),
                {"tenancy": body.get("tenancy_code"), "amount": amount},
            )
        _remember(connection, organization, body["idempotency_key"], fingerprint, reference)
    return {
        "accepted": True,
        "reference": reference,
        "replayed": False,
        "state": state,
        "application_state": application,
        "effect_class": effect,
        "money_moved": False,
        "real_values_activated": False,
    }


def _fault(name: str) -> None:
    if os.environ.get("PHASE3_ENVIRONMENT", "local") not in {"local", "test"}:
        return
    if os.environ.get("PHASE18_FAULT") != name:
        return
    os.environ.pop("PHASE18_FAULT", None)
    raise RuntimeError("injected fault")


def _apply_resident(connection, organization, receipt) -> dict:
    """Post one resident settlement. An in-flight debit stays intact and this receipt waits."""
    if receipt["state"] != "confirmed" or receipt["effect_class"] != "resident_settlement":
        raise CommandError(409, "conflict", "That transfer is not confirmed resident money and was not posted.", False)
    if not receipt["tenancy_code"] or not receipt["service_period"]:
        connection.execute(text("UPDATE digital_receipts SET application_state = 'unmatched' WHERE id = :id"), {"id": receipt["id"]})
        return {"accepted": True, "reference": receipt["public_reference"], "application_state": "unmatched", "posted": False, "money_moved": False}
    determination = connection.execute(
        text(
            "SELECT obligation_reference, account_reference, resident_minor FROM assistance_determinations "
            "WHERE tenancy_code = :tenancy AND service_period = :period AND state = 'approved' FOR UPDATE"
        ),
        {"tenancy": receipt["tenancy_code"], "period": receipt["service_period"]},
    ).mappings().first()
    if determination is None or not determination["obligation_reference"] or not determination["account_reference"]:
        connection.execute(text("UPDATE digital_receipts SET application_state = 'review' WHERE id = :id"), {"id": receipt["id"]})
        return {"accepted": True, "reference": receipt["public_reference"], "application_state": "review", "posted": False, "money_moved": False}
    obligation = connection.execute(
        text(
            "SELECT id, amount_minor FROM payment_obligations "
            "WHERE public_reference = :reference AND state = 'published' FOR UPDATE"
        ),
        {"reference": determination["obligation_reference"]},
    ).mappings().first()
    if obligation is None:
        connection.execute(text("UPDATE digital_receipts SET application_state = 'review' WHERE id = :id"), {"id": receipt["id"]})
        return {"accepted": True, "reference": receipt["public_reference"], "application_state": "review", "posted": False, "money_moved": False}
    in_flight = connection.execute(
        text("SELECT 1 FROM collection_reservations WHERE obligation_id = :id AND state = 'active'"),
        {"id": obligation["id"]},
    ).first()
    amount = int(receipt["amount_minor"])
    orders = int(
        connection.execute(
            text("SELECT coalesce(sum(amount_minor), 0) FROM payment_orders WHERE obligation_id = :id AND state = 'succeeded'"),
            {"id": obligation["id"]},
        ).scalar()
        or 0
    )
    applied_receipts = int(
        connection.execute(
            text(
                "SELECT coalesce(sum(amount_minor), 0) FROM digital_receipts "
                "WHERE tenancy_code = :tenancy AND purpose = 'resident_rent' AND application_state = 'applied' AND id <> :id"
            ),
            {"tenancy": receipt["tenancy_code"], "id": receipt["id"]},
        ).scalar()
        or 0
    )
    other_holds = int(
        connection.execute(
            text(
                "SELECT coalesce(sum(amount_minor), 0) FROM digital_receipts "
                "WHERE tenancy_code = :tenancy AND purpose = 'resident_rent' "
                "AND application_state IN ('queued', 'claimed') AND id <> :id"
            ),
            {"tenancy": receipt["tenancy_code"], "id": receipt["id"]},
        ).scalar()
        or 0
    )
    active_reservation = int(
        connection.execute(
            text("SELECT coalesce(sum(amount_minor), 0) FROM collection_reservations WHERE obligation_id = :id AND state = 'active'"),
            {"id": obligation["id"]},
        ).scalar()
        or 0
    )
    remaining = int(obligation["amount_minor"]) - orders - applied_receipts - other_holds - active_reservation
    if in_flight is not None or amount != remaining or remaining < 1:
        connection.execute(text("UPDATE digital_receipts SET application_state = 'review' WHERE id = :id"), {"id": receipt["id"]})
        connection.execute(
            text(
                "INSERT INTO assistance_exceptions "
                "(organization_id, id, public_reference, tenancy_code, service_period, kind, amount_minor, detail, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, :tenancy, :period, 'review', :amount, :detail, 'open')"
            ),
            {
                "org": organization,
                "reference": f"exception-{uuid4().hex[:16]}",
                "tenancy": receipt["tenancy_code"],
                "period": receipt["service_period"],
                "amount": amount,
                "detail": "A collection is already in flight, or the transfer does not match the resident remainder. The original debit was not cancelled.",
            },
        )
        return {"accepted": True, "reference": receipt["public_reference"], "application_state": "review", "posted": False, "reason": "in_flight_or_unmatched", "money_moved": False}
    account = _account(connection, determination["account_reference"])
    _fault("before_commit")
    due = _positions(connection, account.id)["due_minor"]
    applied = min(max(due, 0), amount)
    unapplied = amount - applied
    lines: list[tuple[str, str, int]] = [("debit", "unapplied", amount)]
    if applied:
        lines.append(("credit", "receivable", applied))
    if unapplied:
        lines.append(("credit", "prepayment", unapplied))
    journal = _post(connection, organization, account, "settlement", amount, lines, tenancy_code=receipt["tenancy_code"])
    connection.execute(
        text("UPDATE digital_receipts SET application_state = 'applied', journal_reference = :journal WHERE id = :id"),
        {"journal": journal, "id": receipt["id"]},
    )
    return {
        "accepted": True,
        "reference": receipt["public_reference"],
        "posted": True,
        "replayed": False,
        "journal_reference": journal,
        "rule": RULE_VERSION,
        "resident_settlement": True,
        "money_moved": False,
        "real_values_activated": False,
    }


def _apply_connection(connection, organization, receipt_id) -> dict:
    receipt = connection.execute(
        text(
            "SELECT id, public_reference, amount_minor, tenancy_code, service_period, purpose, effect_class, state, "
            "application_state, source, journal_reference "
            "FROM digital_receipts WHERE id = :id FOR UPDATE"
        ),
        {"id": receipt_id},
    ).mappings().first()
    if receipt is None:
        raise CommandError(404, "missing", "That receipt was not found.", False)
    if receipt["application_state"] == "applied":
        return {"accepted": True, "reference": receipt["public_reference"], "replayed": True, "journal_reference": receipt["journal_reference"], "money_moved": False}
    if receipt["source"] == "historical_import" or receipt["effect_class"] == "historical":
        raise CommandError(409, "conflict", "A historical import cannot be used as a new operational receipt.", False)
    if receipt["purpose"] == "resident_rent":
        return _apply_resident(connection, organization, receipt)
    if receipt["effect_class"] != "agency_cash" or receipt["state"] != "confirmed":
        raise CommandError(409, "conflict", "That observation is not confirmed agency cash and was not posted.", False)
    if receipt["purpose"] != "rent_assistance":
        raise CommandError(409, "conflict", "A restricted receipt cannot be applied to ordinary rent.", False)
    if receipt["application_state"] == "batch":
        raise CommandError(409, "conflict", "This receipt belongs to a remittance batch.", False)
    if not receipt["tenancy_code"] or not receipt["service_period"]:
        connection.execute(
            text("UPDATE digital_receipts SET application_state = 'unmatched' WHERE id = :id"),
            {"id": receipt["id"]},
        )
        return {"accepted": True, "reference": receipt["public_reference"], "application_state": "unmatched", "posted": False, "money_moved": False}
    determination = connection.execute(
        text(
            "SELECT id, agency_minor, agency_received_minor, account_reference "
            "FROM assistance_determinations "
            "WHERE tenancy_code = :tenancy AND service_period = :period AND state = 'approved' "
            "FOR UPDATE"
        ),
        {"tenancy": receipt["tenancy_code"], "period": receipt["service_period"]},
    ).mappings().first()
    if determination is None or not determination["account_reference"]:
        connection.execute(text("UPDATE digital_receipts SET application_state = 'review' WHERE id = :id"), {"id": receipt["id"]})
        return {"accepted": True, "reference": receipt["public_reference"], "application_state": "review", "posted": False, "money_moved": False}
    remaining = int(determination["agency_minor"]) - int(determination["agency_received_minor"])
    amount = int(receipt["amount_minor"])
    if amount != remaining or remaining < 1:
        connection.execute(text("UPDATE digital_receipts SET application_state = 'review' WHERE id = :id"), {"id": receipt["id"]})
        return {"accepted": True, "reference": receipt["public_reference"], "application_state": "review", "posted": False, "rule": RULE_VERSION, "money_moved": False}
    account = _account(connection, determination["account_reference"])
    _fault("before_commit")
    journal = _post(
        connection,
        organization,
        account,
        "subsidy",
        amount,
        [("debit", "subsidy", amount), ("credit", "income", amount)],
        tenancy_code=receipt["tenancy_code"],
    )
    connection.execute(
        text(
            "UPDATE assistance_determinations SET agency_received_minor = agency_received_minor + :amount WHERE id = :id"
        ),
        {"amount": amount, "id": determination["id"]},
    )
    connection.execute(
        text(
            "UPDATE digital_receipts SET application_state = 'applied', journal_reference = :journal WHERE id = :id"
        ),
        {"journal": journal, "id": receipt["id"]},
    )
    return {
        "accepted": True,
        "reference": receipt["public_reference"],
        "posted": True,
        "replayed": False,
        "journal_reference": journal,
        "rule": RULE_VERSION,
        "money_moved": False,
        "real_values_activated": False,
    }


def resolve_receipt(settings: Settings, actor, organization, body: dict) -> dict:
    """Attach an unmatched receipt to one household and period. This does not post by itself."""
    tenancy = str(body.get("tenancy_code") or "").strip()
    period = str(body.get("service_period") or "").strip()
    if len(tenancy) < 3 or len(period) != 7:
        raise CommandError(400, "invalid", "Name the household and service period before resolving a receipt.", False)
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        receipt = connection.execute(
            text(
                "SELECT id, public_reference, amount_minor, application_state, effect_class, state, purpose "
                "FROM digital_receipts WHERE public_reference = :reference FOR UPDATE"
            ),
            {"reference": body["receipt_reference"]},
        ).mappings().first()
        if receipt is None:
            raise CommandError(404, "missing", "That receipt was not found.", False)
        if receipt["application_state"] == "applied":
            return {"accepted": True, "reference": receipt["public_reference"], "replayed": True, "posted": False, "money_moved": False}
        determination = connection.execute(
            text(
                "SELECT agency_minor, agency_received_minor, resident_minor FROM assistance_determinations "
                "WHERE tenancy_code = :tenancy AND service_period = :period AND state = 'approved'"
            ),
            {"tenancy": tenancy, "period": period},
        ).mappings().first()
        if receipt["purpose"] == "resident_rent" and determination is not None:
            resident_remaining = int(determination["resident_minor"])
            application = "queued" if int(receipt["amount_minor"]) == resident_remaining and receipt["state"] == "confirmed" else "review"
        else:
            remaining = 0 if determination is None else int(determination["agency_minor"]) - int(determination["agency_received_minor"])
            application = "queued" if determination is not None and int(receipt["amount_minor"]) == remaining and receipt["effect_class"] == "agency_cash" and receipt["state"] == "confirmed" else "review"
        connection.execute(
            text(
                "UPDATE digital_receipts SET tenancy_code = :tenancy, service_period = :period, application_state = :application "
                "WHERE id = :id"
            ),
            {"tenancy": tenancy, "period": period, "application": application, "id": receipt["id"]},
        )
    return {
        "accepted": True,
        "reference": receipt["public_reference"],
        "application_state": application,
        "posted": False,
        "replayed": False,
        "money_moved": False,
    }


def apply_receipt(settings: Settings, actor, organization, body: dict) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        receipt_id = connection.execute(
            text("SELECT id FROM digital_receipts WHERE public_reference = :reference"),
            {"reference": body["receipt_reference"]},
        ).scalar()
        if receipt_id is None:
            raise CommandError(404, "missing", "That receipt was not found.", False)
        return _apply_connection(connection, organization, receipt_id)


def apply_queued_receipts(settings: Settings) -> dict:
    engine = engine_for(settings.runtime_url)
    with engine.connect() as connection:
        scopes = connection.execute(text("SELECT organization_id, principal_id FROM perchpoint.assistance_apply_scopes()")).mappings().all()
        connection.commit()
    engine.dispose()
    applied = 0
    errors: list[str] = []
    expire_now = os.environ.get("PHASE18_FAULT") == "before_commit"
    for scope in scopes:
        with runtime_transaction(settings, scope["principal_id"], scope["organization_id"], uuid4()) as connection:
            pending = connection.execute(
                text(
                    "UPDATE digital_receipts SET application_state = 'claimed', "
                    "claim_expires_at = CASE WHEN :expire_now THEN now() - interval '1 second' ELSE now() + interval '2 minutes' END "
                    "WHERE organization_id = CAST(:org AS uuid) AND ("
                    "application_state = 'queued' OR (application_state = 'claimed' AND claim_expires_at IS NOT NULL AND claim_expires_at < now())"
                    ") RETURNING id"
                ),
                {"org": scope["organization_id"], "expire_now": expire_now},
            ).scalars().all()
        for receipt_id in pending:
            try:
                with runtime_transaction(settings, scope["principal_id"], scope["organization_id"], uuid4()) as connection:
                    result = _apply_connection(connection, scope["organization_id"], receipt_id)
                if result.get("posted"):
                    applied += 1
            except CommandError as exc:
                errors.append(exc.code)
    return {"applied": applied, "errors": errors, "money_moved": False, "real_values_activated": False}


def record_batch(settings: Settings, actor, organization, body: dict) -> dict:
    gross = _minor(int(body["gross_minor"]), allow_zero=True)
    recoupment = _minor(int(body.get("recoupment_minor") or 0), allow_zero=True)
    adjustment = int(body.get("adjustment_minor") or 0)
    if isinstance(body.get("adjustment_minor"), bool) or not isinstance(adjustment, int):
        raise CommandError(400, "invalid", "Amounts must be integer USD minor units.", False)
    net = _minor(int(body["net_minor"]), allow_zero=True)
    if gross - recoupment + adjustment != net:
        raise CommandError(400, "invalid", "The batch does not reconcile to the net transfer.", False)
    rows = list(body.get("rows") or [])
    if sum(int(row["gross_minor"]) for row in rows) != gross:
        raise CommandError(400, "invalid", "The remittance lines do not add up to the gross assistance.", False)
    if any(row.get("tenancy_code") in (None, "") and int(row["gross_minor"]) > 0 for row in rows):
        pass
    economic = str(body.get("external_id") or "").strip()
    if len(economic) < 3:
        raise CommandError(400, "invalid", "A batch needs a stable source identifier.", False)
    fingerprint = _fingerprint([economic, gross, recoupment, net, body["idempotency_key"]])
    reference = f"batch-{uuid4().hex[:16]}"
    receipt_reference = None
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        replay = _replay(connection, body["idempotency_key"], fingerprint)
        if replay is not None:
            return replay
        existing = connection.execute(
            text("SELECT public_reference, gross_minor, recoupment_minor, net_minor FROM remittance_batches WHERE economic_key = :key"),
            {"key": economic},
        ).mappings().first()
        if existing is not None:
            if int(existing["gross_minor"]) != gross or int(existing["recoupment_minor"]) != recoupment or int(existing["net_minor"]) != net:
                raise CommandError(409, "conflict", "That remittance identifier already belongs to a different batch.", False)
            _remember(connection, organization, body["idempotency_key"], fingerprint, existing["public_reference"])
            return {"accepted": True, "reference": existing["public_reference"], "replayed": True, "money_moved": False}
        if body.get("cash_external_id"):
            receipt_reference = f"receipt-{uuid4().hex[:16]}"
            connection.execute(
                text(
                    "INSERT INTO digital_receipts "
                    "(organization_id, id, public_reference, source, economic_key, method, amount_minor, currency_code, "
                    "purpose, effect_class, state, application_state, batch_reference, environment, money_moved, real_values_activated) "
                    "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, 'business_bank', :key, 'bank_transfer', :amount, 'USD', "
                    "'rent_assistance', 'agency_cash', 'confirmed', 'batch', :batch, 'local_fake', false, false)"
                ),
                {
                    "org": organization,
                    "reference": receipt_reference,
                    "key": str(body["cash_external_id"]),
                    "amount": net,
                    "batch": reference,
                },
            )
        batch_id = uuid4()
        connection.execute(
            text(
                "INSERT INTO remittance_batches "
                "(organization_id, id, public_reference, economic_key, gross_minor, recoupment_minor, adjustment_minor, net_minor, "
                "receipt_reference, state, unexplained_minor, environment, money_moved) "
                "VALUES (CAST(:org AS uuid), :id, :reference, :key, :gross, :recoupment, :adjustment, :net, :receipt, 'preview', :gap, 'local_fake', false)"
            ),
            {
                "org": organization,
                "id": batch_id,
                "reference": reference,
                "key": economic,
                "gross": gross,
                "recoupment": recoupment,
                "adjustment": adjustment,
                "net": net,
                "receipt": receipt_reference,
                "gap": 0 if body.get("cash_external_id") else net,
            },
        )
        for row in rows:
            connection.execute(
                text(
                    "INSERT INTO remittance_rows "
                    "(organization_id, id, batch_id, tenancy_code, service_period, gross_minor, state) "
                    "VALUES (CAST(:org AS uuid), gen_random_uuid(), :batch, :tenancy, :period, :amount, 'open')"
                ),
                {
                    "org": organization,
                    "batch": batch_id,
                    "tenancy": row.get("tenancy_code"),
                    "period": row.get("service_period"),
                    "amount": int(row["gross_minor"]),
                },
            )
        _remember(connection, organization, body["idempotency_key"], fingerprint, reference)
    return {
        "accepted": True,
        "reference": reference,
        "receipt_reference": receipt_reference,
        "posted": False,
        "replayed": False,
        "gross_minor": gross,
        "recoupment_minor": recoupment,
        "net_minor": net,
        "money_moved": False,
    }


def apply_batch(settings: Settings, actor, organization, body: dict) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        batch = connection.execute(
            text(
                "SELECT id, public_reference, gross_minor, recoupment_minor, adjustment_minor, net_minor, receipt_reference, state "
                "FROM remittance_batches WHERE public_reference = :reference FOR UPDATE"
            ),
            {"reference": body["batch_reference"]},
        ).mappings().first()
        if batch is None:
            raise CommandError(404, "missing", "That remittance batch was not found.", False)
        if batch["state"] == "applied":
            return {"accepted": True, "reference": batch["public_reference"], "replayed": True, "unexplained_minor": 0, "money_moved": False}
        rows = connection.execute(
            text(
                "SELECT id, tenancy_code, service_period, gross_minor, state FROM remittance_rows "
                "WHERE batch_id = :batch ORDER BY id FOR UPDATE"
            ),
            {"batch": batch["id"]},
        ).mappings().all()
        posted = 0
        open_rows = 0
        for row in rows:
            if row["state"] == "applied":
                posted += 1
                continue
            if not row["tenancy_code"]:
                open_rows += 1
                continue
            determination = connection.execute(
                text(
                    "SELECT id, account_reference, agency_minor, agency_received_minor FROM assistance_determinations "
                    "WHERE tenancy_code = :tenancy AND service_period = :period AND state = 'approved' FOR UPDATE"
                ),
                {"tenancy": row["tenancy_code"], "period": row["service_period"]},
            ).mappings().first()
            if determination is None or not determination["account_reference"]:
                open_rows += 1
                continue
            amount = int(row["gross_minor"])
            if int(determination["agency_received_minor"]) + amount > int(determination["agency_minor"]):
                open_rows += 1
                continue
            account = _account(connection, determination["account_reference"])
            journal = _post(
                connection,
                organization,
                account,
                "subsidy",
                amount,
                [("debit", "subsidy", amount), ("credit", "income", amount)],
                tenancy_code=row["tenancy_code"],
            )
            connection.execute(
                text("UPDATE assistance_determinations SET agency_received_minor = agency_received_minor + :amount WHERE id = :id"),
                {"amount": amount, "id": determination["id"]},
            )
            connection.execute(
                text("UPDATE remittance_rows SET state = 'applied', journal_reference = :journal WHERE id = :id"),
                {"journal": journal, "id": row["id"]},
            )
            posted += 1
        equation = int(batch["gross_minor"]) - int(batch["recoupment_minor"]) + int(batch["adjustment_minor"])
        cash = 0
        if batch["receipt_reference"]:
            cash = int(
                connection.execute(
                    text("SELECT amount_minor FROM digital_receipts WHERE public_reference = :reference"),
                    {"reference": batch["receipt_reference"]},
                ).scalar()
                or 0
            )
        unexplained = 0 if open_rows == 0 and equation == int(batch["net_minor"]) and cash == int(batch["net_minor"]) else int(batch["net_minor"])
        state = "applied" if unexplained == 0 else "partial"
        if state == "applied" and batch["receipt_reference"]:
            connection.execute(
                text("UPDATE digital_receipts SET application_state = 'applied' WHERE public_reference = :reference AND application_state = 'batch'"),
                {"reference": batch["receipt_reference"]},
            )
        connection.execute(
            text("UPDATE remittance_batches SET state = :state, unexplained_minor = :gap WHERE id = :id"),
            {"state": state, "gap": unexplained, "id": batch["id"]},
        )
        return {
            "accepted": True,
            "reference": batch["public_reference"],
            "posted_rows": posted,
            "open_rows": open_rows,
            "gross_minor": int(batch["gross_minor"]),
            "recoupment_minor": int(batch["recoupment_minor"]),
            "net_minor": int(batch["net_minor"]),
            "confirmed_cash_minor": cash,
            "unexplained_minor": unexplained,
            "replayed": False,
            "money_moved": False,
            "real_values_activated": False,
        }


def assign_remittance_row(settings: Settings, actor, organization, body: dict) -> dict:
    """Name an open remittance line. Naming it does not post the subsidy."""
    fingerprint = _fingerprint([body["batch_reference"], body["row_reference"], body["tenancy_code"], body["service_period"], body["idempotency_key"]])
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        replay = _replay(connection, body["idempotency_key"], fingerprint)
        if replay is not None:
            return replay
        determination = connection.execute(
            text(
                "SELECT 1 FROM assistance_determinations "
                "WHERE tenancy_code = :tenancy AND service_period = :period AND state = 'approved'"
            ),
            {"tenancy": body["tenancy_code"], "period": body["service_period"]},
        ).first()
        if determination is None:
            raise CommandError(404, "missing", "That household has no approved schedule for this period.", False)
        updated = connection.execute(
            text(
                "UPDATE remittance_rows AS row SET tenancy_code = :tenancy, service_period = :period "
                "FROM remittance_batches AS batch "
                "WHERE row.batch_id = batch.id AND batch.public_reference = :batch "
                "AND row.id = CAST(:row AS uuid) AND row.state = 'open' AND row.tenancy_code IS NULL "
                "RETURNING row.id"
            ),
            {
                "tenancy": body["tenancy_code"],
                "period": body["service_period"],
                "batch": body["batch_reference"],
                "row": body["row_reference"],
            },
        ).first()
        if updated is None:
            raise CommandError(409, "conflict", "That remittance line is no longer unassigned.", False)
        reference = body["batch_reference"]
        _remember(connection, organization, body["idempotency_key"], fingerprint, reference)
    return {"accepted": True, "reference": reference, "posted": False, "money_moved": False}


def hold_separate_deposit(settings: Settings, actor, organization, body: dict) -> dict:
    """Keep a distinct deposit in review when the same assistance is already posted."""
    fingerprint = _fingerprint([body["batch_reference"], "separate-deposit", body["idempotency_key"]])
    reference = f"review-{uuid4().hex[:16]}"
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        replay = _replay(connection, body["idempotency_key"], fingerprint)
        if replay is not None:
            return replay
        batch = connection.execute(
            text(
                "SELECT id, public_reference, state, unexplained_minor, net_minor FROM remittance_batches "
                "WHERE public_reference = :reference FOR UPDATE"
            ),
            {"reference": body["batch_reference"]},
        ).mappings().first()
        if batch is None:
            raise CommandError(404, "missing", "That remittance batch was not found.", False)
        if batch["state"] == "applied" or int(batch["unexplained_minor"]) == 0:
            raise CommandError(409, "conflict", "An applied remittance does not need a separate-deposit review.", False)
        detail = f"batch:{batch['public_reference']}"
        existing = connection.execute(
            text(
                "SELECT public_reference FROM assistance_exceptions "
                "WHERE kind = 'review' AND state = 'open' AND detail = :detail"
            ),
            {"detail": detail},
        ).mappings().first()
        if existing is not None:
            _remember(connection, organization, body["idempotency_key"], fingerprint, existing["public_reference"])
            return {
                "accepted": True,
                "reference": existing["public_reference"],
                "replayed": True,
                "posted": False,
                "unexplained_minor": int(batch["unexplained_minor"]),
                "money_moved": False,
            }
        period = connection.execute(
            text("SELECT service_period FROM remittance_rows WHERE batch_id = :batch AND service_period IS NOT NULL LIMIT 1"),
            {"batch": batch["id"]},
        ).scalar() or "2026-11"
        connection.execute(
            text(
                "INSERT INTO assistance_exceptions "
                "(organization_id, id, public_reference, tenancy_code, service_period, kind, amount_minor, detail, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, 'unallocated-source', :period, 'review', :amount, :detail, 'open')"
            ),
            {
                "org": organization,
                "reference": reference,
                "period": period,
                "amount": int(batch["unexplained_minor"]),
                "detail": detail,
            },
        )
        _remember(connection, organization, body["idempotency_key"], fingerprint, reference)
    return {
        "accepted": True,
        "reference": reference,
        "replayed": False,
        "posted": False,
        "unexplained_minor": int(batch["unexplained_minor"]),
        "money_moved": False,
    }


def household_view(settings: Settings, actor, organization, tenancy_code: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.read", "payment.charge", "payment.pay"))
        if not _may_act_for_tenancy(connection, tenancy_code, grant_counts=True):
            raise CommandError(403, "denied", "This household is not available for this sign-in.", False)
        determination = connection.execute(
            text(
                "SELECT public_reference, service_period, version, rent_to_owner_minor, resident_minor, agency_minor, "
                "agency_received_minor, utility_allowance_minor, utility_reimbursement_minor, account_reference, state, household_label "
                "FROM assistance_determinations WHERE tenancy_code = :tenancy AND state = 'approved' "
                "ORDER BY service_period DESC, version DESC LIMIT 1"
            ),
            {"tenancy": tenancy_code},
        ).mappings().first()
        reports = connection.execute(
            text(
                "SELECT public_reference, amount_minor, state FROM transfer_reports "
                "WHERE tenancy_code = :tenancy ORDER BY created_at DESC LIMIT 20"
            ),
            {"tenancy": tenancy_code},
        ).mappings().all()
        positions = None
        if determination is not None and determination["account_reference"]:
            try:
                account = _account(connection, determination["account_reference"])
                positions = _positions(connection, account.id)
            except CommandError:
                positions = None
        exceptions = connection.execute(
            text(
                "SELECT public_reference, kind, amount_minor, state FROM assistance_exceptions "
                "WHERE tenancy_code = :tenancy AND state = 'open' ORDER BY created_at DESC LIMIT 20"
            ),
            {"tenancy": tenancy_code},
        ).mappings().all()
        received = connection.execute(
            text(
                "SELECT coalesce(sum(amount_minor), 0) FROM payment_orders "
                "WHERE tenancy_code = :tenancy AND state = 'succeeded'"
            ),
            {"tenancy": tenancy_code},
        ).scalar()
        received = int(received or 0) + int(
            connection.execute(
                text(
                    "SELECT coalesce(sum(amount_minor), 0) FROM digital_receipts "
                    "WHERE tenancy_code = :tenancy AND purpose = 'resident_rent' AND application_state = 'applied'"
                ),
                {"tenancy": tenancy_code},
            ).scalar()
            or 0
        )
        returned = int(
            connection.execute(
                text(
                    "SELECT coalesce(sum(amount_minor), 0) FROM assistance_exceptions "
                    "WHERE tenancy_code = :tenancy AND kind = 'required_return' AND state = 'resolved'"
                ),
                {"tenancy": tenancy_code},
            ).scalar()
            or 0
        )
        reserved = int(
            connection.execute(
                text(
                    "SELECT coalesce(sum(amount_minor), 0) FROM digital_receipts "
                    "WHERE tenancy_code = :tenancy AND purpose = 'resident_rent' "
                    "AND application_state IN ('queued', 'claimed')"
                ),
                {"tenancy": tenancy_code},
            ).scalar()
            or 0
        )
    agency = 0 if determination is None else int(determination["agency_minor"])
    agency_received = 0 if determination is None else int(determination["agency_received_minor"])
    label = None if determination is None else determination["household_label"] or _display(tenancy_code)
    return {
        "tenancy_code": tenancy_code,
        "label": label,
        "service_period": None if determination is None else determination["service_period"],
        "rent_to_owner_minor": None if determination is None else int(determination["rent_to_owner_minor"]),
        "resident_responsibility_minor": None if determination is None else int(determination["resident_minor"]),
        "agency_responsibility_minor": None if determination is None else agency,
        "agency_received_minor": agency_received,
        "agency_outstanding_minor": agency - agency_received,
        "resident_received_minor": received,
        "resident_returned_minor": returned,
        "resident_net_minor": received - returned,
        "reserved_minor": reserved,
        "utility_allowance_minor": 0 if determination is None else int(determination["utility_allowance_minor"]),
        "utility_reimbursement_minor": 0 if determination is None else int(determination["utility_reimbursement_minor"]),
        "due_minor": None if positions is None else positions["due_minor"],
        "subsidy_minor": None if positions is None else positions["subsidy_minor"],
        "reports": [dict(row) for row in reports],
        "exceptions": [dict(row) for row in exceptions],
        "payment_default_includes_agency": False,
        "money_moved": False,
        "real_values_activated": False,
    }


def owner_measures(settings: Settings, actor, organization) -> dict:
    """Separate owner measures. Gross assistance, cash, and household settlements are not one revenue number."""
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.charge", "payment.refund", "payment.exception"))
        assistance = connection.execute(
            text(
                "SELECT coalesce(sum(agency_minor - agency_received_minor), 0) AS expected_minor, "
                "coalesce(sum(agency_received_minor), 0) AS received_minor "
                "FROM assistance_determinations WHERE state = 'approved'"
            )
        ).one()
        cash = connection.execute(
            text(
                "SELECT coalesce(sum(amount_minor) FILTER (WHERE application_state = 'applied'), 0) AS confirmed_minor, "
                "coalesce(sum(amount_minor) FILTER (WHERE application_state = 'unmatched' AND state = 'confirmed'), 0) AS unmatched_minor "
                "FROM digital_receipts"
            )
        ).one()
    return {
        "as_of_period": "2026-11",
        "assistance_expected_minor": int(assistance.expected_minor),
        "assistance_received_minor": int(assistance.received_minor),
        "confirmed_cash_minor": int(cash.confirmed_minor),
        "unmatched_confirmed_minor": int(cash.unmatched_minor),
        "definitions": {
            "assistance_expected_minor": "Approved agency portion that is not yet matched to a posted receipt.",
            "assistance_received_minor": "Agency portion matched to a posted receipt. This is not cash by itself.",
            "confirmed_cash_minor": "Confirmed digital receipts that have been applied once.",
            "unmatched_confirmed_minor": "Confirmed money that is not yet tied to a household.",
        },
        "money_moved": False,
        "real_values_activated": False,
    }


def queue(settings: Settings, actor, organization) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        receipts = connection.execute(
            text(
                "SELECT public_reference, source, amount_minor, tenancy_code, service_period, application_state, state "
                "FROM digital_receipts WHERE application_state IN ('unmatched', 'queued', 'review') "
                "ORDER BY created_at DESC LIMIT 50"
            )
        ).mappings().all()
        exceptions = connection.execute(
            text(
                "SELECT exception.public_reference, exception.tenancy_code, exception.service_period, exception.kind, "
                "exception.amount_minor, exception.state, determination.household_label "
                "FROM assistance_exceptions exception "
                "LEFT JOIN LATERAL ("
                "  SELECT household_label FROM assistance_determinations "
                "  WHERE tenancy_code = exception.tenancy_code AND state = 'approved' "
                "  ORDER BY service_period DESC LIMIT 1"
                ") determination ON true "
                "WHERE exception.state = 'open' ORDER BY exception.created_at DESC LIMIT 50"
            )
        ).mappings().all()
        reports = connection.execute(
            text(
                "SELECT report.public_reference, report.tenancy_code, report.amount_minor, report.state, report.reference_text, "
                "determination.household_label, determination.service_period "
                "FROM transfer_reports report "
                "LEFT JOIN LATERAL ("
                "  SELECT household_label, service_period FROM assistance_determinations "
                "  WHERE tenancy_code = report.tenancy_code AND state = 'approved' "
                "  ORDER BY service_period DESC LIMIT 1"
                ") determination ON true "
                "WHERE report.state = 'reported' ORDER BY report.created_at DESC LIMIT 50"
            )
        ).mappings().all()
        batches = connection.execute(
            text(
                "SELECT public_reference, gross_minor, recoupment_minor, net_minor, unexplained_minor, state "
                "FROM remittance_batches WHERE state IN ('preview', 'partial') "
                "ORDER BY created_at DESC LIMIT 50"
            )
        ).mappings().all()
        unassigned = connection.execute(
            text(
                "SELECT row.id::text AS row_reference, batch.public_reference AS batch_reference, "
                "row.gross_minor, row.service_period "
                "FROM remittance_rows row "
                "JOIN remittance_batches batch ON batch.id = row.batch_id AND batch.organization_id = row.organization_id "
                "WHERE row.state = 'open' AND row.tenancy_code IS NULL "
                "ORDER BY batch.created_at DESC LIMIT 50"
            )
        ).mappings().all()
    def _queue_label(row) -> str | None:
        if row.get("tenancy_code") == "unallocated-source":
            return "Separate deposit"
        return row.get("household_label") or _display(row.get("tenancy_code"))

    return {
        "receipts": [
            {
                **dict(row),
                "label": _display(row["tenancy_code"]),
                "next_action": _next_action(row["application_state"], row["application_state"]),
            }
            for row in receipts
        ],
        "exceptions": [
            {
                **dict(row),
                "label": _queue_label(row),
                "next_action": _next_action(row["kind"]),
            }
            for row in exceptions
        ],
        "reports": [
            {
                **dict(row),
                "label": _queue_label(row),
                "next_action": "Match a confirmed receipt. This report is not a payment.",
            }
            for row in reports
        ],
        "batches": [
            {
                **dict(row),
                "next_action": "Hold this deposit for review. Do not post assistance that is already applied.",
            }
            for row in batches
        ],
        "unassigned_rows": [
            {
                **dict(row),
                "next_action": "Choose the household by name. This does not post the line.",
            }
            for row in unassigned
        ],
        "money_moved": False,
    }


def assistance_document(settings: Settings, actor, organization, kind: str, tenancy_code: str) -> str:
    """Render one household's synthetic notice from the ledger. Other households stay out."""
    if kind not in {"determination", "return"}:
        raise CommandError(404, "missing", "That document is not available.", False)
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.read", "payment.charge", "payment.pay"))
        if not _may_act_for_tenancy(connection, tenancy_code, grant_counts=True):
            raise CommandError(403, "denied", "This household is not available for this sign-in.", False)
        if kind == "determination":
            row = connection.execute(
                text(
                    "SELECT service_period, resident_minor, agency_minor, rent_to_owner_minor, household_label "
                    "FROM assistance_determinations WHERE tenancy_code = :tenancy AND state = 'approved' "
                    "ORDER BY service_period DESC, version DESC LIMIT 1"
                ),
                {"tenancy": tenancy_code},
            ).mappings().first()
            if row is None:
                raise CommandError(404, "missing", "There is no approved schedule to open.", False)
            title = "Synthetic assistance schedule"
            lines = [
                f"Household {row['household_label'] or tenancy_code}",
                f"Service period {row['service_period']}",
                f"Rent to owner {_dollars(row['rent_to_owner_minor'])}",
                f"Resident portion {_dollars(row['resident_minor'])}",
                f"Agency portion {_dollars(row['agency_minor'])}",
            ]
        else:
            row = connection.execute(
                text(
                    "SELECT amount_minor, service_period, state FROM assistance_exceptions "
                    "WHERE tenancy_code = :tenancy AND kind = 'required_return' AND state = 'resolved' "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"tenancy": tenancy_code},
            ).mappings().first()
            if row is None:
                raise CommandError(404, "missing", "There is no completed return to open.", False)
            title = "Synthetic return confirmation"
            lines = [
                f"Service period {row['service_period']}",
                f"Returned {_dollars(row['amount_minor'])}",
                "This return is complete. The same overpayment cannot be opened again.",
            ]
    body = "".join(f"<p>{html.escape(line)}</p>" for line in lines)
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title></head><body>"
        f"<h1>{html.escape(title)}</h1>"
        "<p>SYNTHETIC — NOT AN OFFICIAL AGENCY DOCUMENT</p>"
        f"{body}</body></html>"
    )


def record_required_return(settings: Settings, actor, organization, body: dict) -> dict:
    """Open an owned return. This does not pay it and does not spend the discretionary refund cap."""
    if body.get("paid") is True or str(body.get("state") or "") == "paid":
        raise CommandError(400, "invalid", "A required return cannot be marked paid from this request.", False)
    recipient = str(body.get("recipient") or "")
    if recipient not in {"resident", "agency"}:
        raise CommandError(400, "invalid", "A required return needs the entitled recipient.", False)
    fingerprint = _fingerprint([body["exception_reference"], recipient, body["idempotency_key"]])
    reference = f"return-{uuid4().hex[:16]}"
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        replay = _replay(connection, body["idempotency_key"], fingerprint)
        if replay is not None:
            return replay
        source = connection.execute(
            text(
                "SELECT tenancy_code, service_period, kind, amount_minor FROM assistance_exceptions "
                "WHERE public_reference = :reference AND state = 'open' FOR UPDATE"
            ),
            {"reference": body["exception_reference"]},
        ).mappings().first()
        if source is None or source["kind"] != "resident_overpayment":
            raise CommandError(404, "not_found", "There is no open resident overpayment to return.", False)
        if recipient != "resident":
            raise CommandError(409, "conflict", "A resident overpayment returns to the resident, not the agency.", False)
        source_detail = f"source:{body['exception_reference']}"
        existing_return = connection.execute(
            text(
                "SELECT 1 FROM assistance_exceptions "
                "WHERE tenancy_code = :tenancy AND service_period = :period AND kind = 'required_return' "
                "AND state = 'open' AND detail = :source"
            ),
            {"tenancy": source["tenancy_code"], "period": source["service_period"], "source": source_detail},
        ).first()
        if existing_return is not None:
            raise CommandError(409, "conflict", "An open required return already reserves this overpayment.", False)
        already_returned = int(
            connection.execute(
                text(
                    "SELECT coalesce(sum(amount_minor), 0) FROM assistance_exceptions "
                    "WHERE tenancy_code = :tenancy AND service_period = :period AND kind = 'required_return' "
                    "AND state = 'resolved' AND detail = :source"
                ),
                {"tenancy": source["tenancy_code"], "period": source["service_period"], "source": source_detail},
            ).scalar()
            or 0
        )
        if already_returned >= int(source["amount_minor"]):
            raise CommandError(409, "conflict", "This overpayment already has a completed required return.", False)
        connection.execute(
            text(
                "INSERT INTO assistance_exceptions "
                "(organization_id, id, public_reference, tenancy_code, service_period, kind, amount_minor, detail, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :reference, :tenancy, :period, 'required_return', :amount, :detail, 'open')"
            ),
            {
                "org": organization,
                "reference": reference,
                "tenancy": source["tenancy_code"],
                "period": source["service_period"],
                "amount": int(source["amount_minor"]),
                "detail": source_detail,
            },
        )
        _remember(connection, organization, body["idempotency_key"], fingerprint, reference)
    return {
        "accepted": True,
        "reference": reference,
        "state": "open",
        "paid": False,
        "amount_minor": int(source["amount_minor"]),
        "recipient": "resident",
        "money_moved": False,
        "real_values_activated": False,
    }


def complete_required_return(settings: Settings, actor, organization, body: dict) -> dict:
    """Post one verified resident return. A checkbox cannot authorize it, and replay does not post twice.

    Lock succeeded payments before the return row so two completions cannot spend the same source funds.
    """
    if body.get("paid") is True or body.get("mandatory") is True:
        raise CommandError(400, "invalid", "A flag does not complete a return or bypass the source limit.", False)
    evidence = str(body.get("evidence_key") or "").strip()
    if not evidence.startswith("bank-return-") or len(evidence) < 16 or any(character.isspace() for character in evidence):
        raise CommandError(400, "invalid", "Verified bank evidence is required. A note does not complete the return.", False)
    fingerprint = _fingerprint([body["return_reference"], evidence, body["idempotency_key"]])
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "payment.charge")
        replay = _replay(connection, body["idempotency_key"], fingerprint)
        if replay is not None:
            return replay
        preview = connection.execute(
            text(
                "SELECT tenancy_code FROM assistance_exceptions "
                "WHERE public_reference = :reference AND kind = 'required_return'"
            ),
            {"reference": body["return_reference"]},
        ).mappings().first()
        if preview is None:
            raise CommandError(404, "not_found", "That required return was not found.", False)
        connection.execute(
            text("SELECT id FROM payment_orders WHERE tenancy_code = :tenancy AND state = 'succeeded' ORDER BY id FOR UPDATE"),
            {"tenancy": preview["tenancy_code"]},
        )
        case = connection.execute(
            text(
                "SELECT id, tenancy_code, service_period, amount_minor, state, journal_reference, evidence_key, detail "
                "FROM assistance_exceptions WHERE public_reference = :reference AND kind = 'required_return' FOR UPDATE"
            ),
            {"reference": body["return_reference"]},
        ).mappings().first()
        if case is None:
            raise CommandError(404, "not_found", "That required return was not found.", False)
        if case["state"] == "resolved":
            if case["evidence_key"] == evidence:
                return {
                    "accepted": True,
                    "reference": body["return_reference"],
                    "state": "resolved",
                    "paid": False,
                    "replayed": True,
                    "journal_reference": case["journal_reference"],
                    "amount_minor": int(case["amount_minor"]),
                    "money_moved": False,
                }
            raise CommandError(409, "conflict", "That return is already complete.", False)
        received = int(
            connection.execute(
                text("SELECT coalesce(sum(amount_minor), 0) FROM payment_orders WHERE tenancy_code = :tenancy AND state = 'succeeded'"),
                {"tenancy": case["tenancy_code"]},
            ).scalar()
            or 0
        )
        received += int(
            connection.execute(
                text(
                    "SELECT coalesce(sum(amount_minor), 0) FROM digital_receipts "
                    "WHERE tenancy_code = :tenancy AND purpose = 'resident_rent' AND application_state = 'applied'"
                ),
                {"tenancy": case["tenancy_code"]},
            ).scalar()
            or 0
        )
        already = int(
            connection.execute(
                text(
                    "SELECT coalesce(sum(amount_minor), 0) FROM assistance_exceptions "
                    "WHERE tenancy_code = :tenancy AND kind = 'required_return' AND state = 'resolved'"
                ),
                {"tenancy": case["tenancy_code"]},
            ).scalar()
            or 0
        )
        determination = connection.execute(
            text(
                "SELECT resident_minor, account_reference, obligation_reference FROM assistance_determinations "
                "WHERE tenancy_code = :tenancy AND state = 'approved' ORDER BY service_period DESC LIMIT 1"
            ),
            {"tenancy": case["tenancy_code"]},
        ).mappings().first()
        if determination is None or not determination["account_reference"]:
            raise CommandError(409, "conflict", "The household account for this return is not available.", False)
        returnable = received - int(determination["resident_minor"]) - already
        amount = int(case["amount_minor"])
        if amount > returnable:
            raise CommandError(409, "conflict", "The source does not have enough refundable resident funds for another return.", False)
        account = _account(connection, determination["account_reference"])
        journal = _post(
            connection,
            organization,
            account,
            "return",
            amount,
            [("debit", "income", amount), ("credit", "unapplied", amount)],
            tenancy_code=case["tenancy_code"],
        )
        connection.execute(
            text(
                "UPDATE assistance_exceptions SET state = 'resolved', journal_reference = :journal, evidence_key = :evidence "
                "WHERE id = :id"
            ),
            {"journal": journal, "evidence": evidence, "id": case["id"]},
        )
        source_reference = str(case["detail"] or "")
        if source_reference.startswith("source:"):
            connection.execute(
                text(
                    "UPDATE assistance_exceptions SET state = 'resolved' "
                    "WHERE public_reference = :source AND kind = 'resident_overpayment' AND state = 'open' "
                    "AND amount_minor <= :amount"
                ),
                {"source": source_reference.removeprefix("source:"), "amount": amount},
            )
        if determination["obligation_reference"]:
            connection.execute(
                text("UPDATE payment_obligations SET amount_minor = :amount WHERE public_reference = :reference"),
                {"amount": int(determination["resident_minor"]), "reference": determination["obligation_reference"]},
            )
        _remember(connection, organization, body["idempotency_key"], fingerprint, body["return_reference"])
    return {
        "accepted": True,
        "reference": body["return_reference"],
        "state": "resolved",
        "paid": False,
        "replayed": False,
        "journal_reference": journal,
        "amount_minor": amount,
        "recipient": "resident",
        "money_moved": False,
        "real_values_activated": False,
    }


def household_directory(settings: Settings, actor, organization, query: str | None) -> dict:
    """List households a sign-in may open. Residents do not receive another household."""
    needle = (query or "").strip().lower()
    named = [
        row["slug"]
        for row in HOUSEHOLDS
        if needle and needle in f"{row['person_label']} {row['home_label']}".lower()
    ]
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.read", "payment.charge", "payment.pay"))
        rows = connection.execute(
            text(
                "SELECT tenancy_code, service_period, resident_minor, agency_minor, agency_name, program_kind, household_label "
                "FROM assistance_determinations WHERE state = 'approved' "
                "AND ("
                "  :needle = '' "
                "  OR lower(agency_name) LIKE '%' || :needle || '%' "
                "  OR lower(coalesce(household_label, '')) LIKE '%' || :needle || '%' "
                "  OR service_period LIKE '%' || :needle || '%' "
                "  OR lower(program_kind) LIKE '%' || :needle || '%' "
                "  OR tenancy_code = ANY(CAST(:named AS text[]))"
                ") "
                "ORDER BY created_at DESC LIMIT 50"
            ),
            {"needle": needle, "named": named},
        ).mappings().all()
        visible = []
        for row in rows:
            if not _may_act_for_tenancy(connection, row["tenancy_code"], grant_counts=True):
                continue
            label = row["household_label"] or _display(row["tenancy_code"]) or f"{row['agency_name']} · {row['service_period']}"
            haystack = " ".join(
                [label, str(row["agency_name"]), str(row["service_period"]), str(row["program_kind"])]
            ).lower()
            if needle and needle not in haystack:
                continue
            visible.append(
                {
                    "tenancy_code": row["tenancy_code"],
                    "label": label,
                    "service_period": row["service_period"],
                    "resident_minor": int(row["resident_minor"]),
                    "agency_minor": int(row["agency_minor"]),
                    "agency_name": row["agency_name"],
                    "program_kind": row["program_kind"],
                }
            )
            if len(visible) >= 50:
                break
    return {"households": visible, "money_moved": False, "real_values_activated": False}


def transfer_instructions(settings: Settings, actor, organization, body: dict) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require_any(connection, ("payment.read", "payment.pay", "payment.charge"))
        determination = connection.execute(
            text(
                "SELECT resident_minor FROM assistance_determinations "
                "WHERE tenancy_code = :tenancy AND state = 'approved' "
                "ORDER BY service_period DESC LIMIT 1"
            ),
            {"tenancy": body["tenancy_code"]},
        ).scalar()
    amount = 0 if determination is None else int(determination)
    return {
        "marker": INSTRUCTION_MARKER,
        "synthetic": True,
        "creates_debit_mandate": False,
        "reference": f"HV-{uuid4().hex[:10].upper()}",
        "resident_amount_minor": amount,
        "includes_agency_share": False,
        "money_moved": False,
        "real_values_activated": False,
    }
