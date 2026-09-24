"""Phase 0 foundation contract tests: schemas, model invariants, permissions, delegation, integrations, migration."""

import csv
import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
from jsonschema import validate
from pydantic import ValidationError

from foundation.catalog import migration_fixture
from foundation.delegation import ApprovalDecision, evaluate_delegation
from foundation.integrations import AdapterCommand, DisconnectedAdapter
from foundation.migration import validate_import
from foundation.people import PeopleGraph
from foundation.permissions import (
    Action,
    PermissionContext,
    Role,
    evaluate_permission,
    permission_matrix,
)
from foundation.property import Portfolio, Unit
from foundation.reference import (
    ReferenceSlice,
    SafeErrorEnvelope,
    SubmitPublicInquiry,
    allowed_space_transition,
    project_phase0_unit_status,
)
from foundation.seeds import money, people_graph, portfolio, reference_slice, sid
from foundation.workflows import PaymentMethodReference, ScreeningRecord

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPOSITORY_ROOT


def test_repository_root_is_independent_of_working_directory(tmp_path):
    previous = Path.cwd()
    try:
        os.chdir(tmp_path)
        assert (ROOT / "contracts/generated/schema-index.json").is_file()
        assert (ROOT / "contracts/fixtures/portfolio.json").is_file()
    finally:
        os.chdir(previous)


# schema and fixture contract validation
def test_generated_schemas_and_fixtures_validate():
    generated = ROOT / "contracts" / "generated"
    fixtures = ROOT / "contracts" / "fixtures"

    index = json.loads((generated / "schema-index.json").read_text())
    assert index["version"] == "0.1.0"
    assert len(index["schemas"]) > 10

    schema_map = {
        "Portfolio": json.loads((generated / "Portfolio.schema.json").read_text()),
        "PeopleGraph": json.loads((generated / "PeopleGraph.schema.json").read_text()),
        "MigrationReport": json.loads((generated / "MigrationReport.schema.json").read_text()),
    }
    fixture_map = {
        "Portfolio": json.loads((fixtures / "portfolio.json").read_text()),
        "PeopleGraph": json.loads((fixtures / "people.json").read_text()),
        "MigrationReport": json.loads((fixtures / "migration-report.json").read_text()),
    }

    for name, payload in fixture_map.items():
        validate(instance=payload, schema=schema_map[name])


# canonical property hierarchy negative tests
def test_portfolio_duplicate_global_ids_rejected():
    data = portfolio().model_dump(mode="json")
    data["properties"][0]["id"] = data["organizations"][0]["id"]
    with pytest.raises(ValidationError, match="globally unique"):
        Portfolio.model_validate(data)


def test_portfolio_cross_org_ownership_rejected():
    data = portfolio().model_dump(mode="json")
    data["ownership_entities"][0]["organization_id"] = str(sid("other-org"))
    with pytest.raises(ValidationError, match="Unknown organization|outside organization"):
        Portfolio.model_validate(data)


def test_portfolio_wrong_property_building_unit_asset_links_rejected():
    data = portfolio().model_dump(mode="json")
    data["buildings"][0]["property_id"] = data["properties"][1]["id"]
    with pytest.raises(ValidationError, match="Building outside property"):
        Portfolio.model_validate(data)

    data = portfolio().model_dump(mode="json")
    data["units"][0]["building_id"] = data["buildings"][1]["id"]
    with pytest.raises(ValidationError, match="Building outside property"):
        Portfolio.model_validate(data)

    data = portfolio().model_dump(mode="json")
    first_asset = data["assets"][0]
    incompatible = next(
        s
        for s in data["shared_spaces"]
        if s["property_id"] != first_asset["property_id"] or s.get("building_id") != first_asset.get("building_id")
    )
    first_asset["shared_space_id"] = incompatible["id"]
    with pytest.raises(ValidationError, match="Asset outside shared location"):
        Portfolio.model_validate(data)


def test_unit_terms_exclusivity_enforced():
    unit = portfolio().units[0].model_dump(mode="json")
    unit["use"] = "residential"
    unit["commercial"] = {
        "intended_use": "Retail",
        "base_rent": money(1000),
        "rent_period": "month",
        "deposit": money(1000),
        "lease_type": "NNN",
        "cam_nnn_terms": "example",
        "utility_responsibility": "example",
        "zoning_notes": "example",
        "loading_access": "example",
        "parking": "example",
        "build_out_status": "example",
    }
    with pytest.raises(ValidationError, match="Residential units require only residential terms"):
        Unit.model_validate(unit)


@pytest.mark.parametrize(
    "property_type, expected_message",
    [
        ("single_family", "shape mismatch"),
        ("duplex", "shape mismatch"),
        ("triplex", "shape mismatch"),
    ],
)
def test_property_shape_capacities_enforced(property_type, expected_message):
    data = portfolio().model_dump(mode="json")
    candidate = next(p for p in data["properties"] if p["property_type"] == property_type)
    units = [u for u in data["units"] if u["property_id"] == candidate["id"]]
    data["units"] = [u for u in data["units"] if u["id"] != units[-1]["id"]]
    with pytest.raises(ValidationError, match="shape mismatch|Complete portfolio requires a building and rentable unit"):
        Portfolio.model_validate(data)


# people, account, household relationship invariants
def test_people_account_sharing_and_age_constraints_enforced():
    p = portfolio()
    base = people_graph(p).model_dump(mode="json")

    shared = deepcopy(base)
    shared["accounts"][1]["person_id"] = shared["accounts"][0]["person_id"]
    with pytest.raises(ValidationError, match="One canonical account per person"):
        PeopleGraph.model_validate(shared)

    minor_adult_signer = deepcopy(base)
    rel = next(r for r in minor_adult_signer["relationships"] if r["kind"] == "adult_signer")
    adult_signer_person = next(p for p in minor_adult_signer["people"] if p["id"] == rel["person_id"])
    adult_signer_person["age_class"] = "minor"
    with pytest.raises(ValidationError, match="Adult relationship requires an adult person"):
        PeopleGraph.model_validate(minor_adult_signer)


def test_people_primary_household_and_cross_org_constraints_enforced():
    p = portfolio()
    base = people_graph(p).model_dump(mode="json")

    duplicate_primary = deepcopy(base)
    template = next(r for r in duplicate_primary["relationships"] if r["kind"] == "primary_holder")
    dup = deepcopy(template)
    dup["id"] = str(sid("duplicate-primary-holder"))
    dup["person_id"] = next(person["id"] for person in duplicate_primary["people"] if person["id"] != template["person_id"] and person["age_class"] == "adult")
    dup["account_id"] = next(acc["id"] for acc in duplicate_primary["accounts"] if acc["person_id"] == dup["person_id"])
    duplicate_primary["relationships"].append(dup)
    with pytest.raises(ValidationError, match="Only one active primary household holder"):
        PeopleGraph.model_validate(duplicate_primary)

    cross_org = deepcopy(base)
    cross_org["relationships"][0]["organization_id"] = str(sid("unknown-org"))
    with pytest.raises(ValidationError, match="Unknown organization"):
        PeopleGraph.model_validate(cross_org)


def test_seed_generation_is_deterministic():
    first = portfolio().model_dump(mode="json")
    second = portfolio().model_dump(mode="json")
    assert first == second
    assert people_graph(portfolio()).model_dump(mode="json") == people_graph(portfolio()).model_dump(mode="json")


# permission matrix and deny-by-default checks
def test_permission_matrix_csv_complete_with_unique_tuples():
    matrix = permission_matrix().model_dump(mode="json")
    path = ROOT / "contracts" / "generated" / "permission-matrix.csv"
    rows = list(csv.DictReader(path.read_text().splitlines()))
    expected = len(matrix["roles"]) * len(matrix["resources"]) * len(matrix["actions"])
    assert len(rows) == expected
    tuples = {(r["role"], r["resource"], r["action"]) for r in rows}
    assert len(tuples) == expected


def test_permission_matrix_role_boundaries_and_denials():
    p = portfolio()
    base_scope = {
        "actor_organization_id": p.organizations[0].id,
        "record_scope": {
            "organization_id": p.organizations[0].id,
            "ownership_entity_id": p.ownership_entities[0].id,
            "property_id": p.properties[0].id,
            "building_id": p.buildings[0].id,
            "unit_id": p.units[0].id,
            "household_id": sid("household-resident"),
            "assignment_id": sid("assignment-hvac"),
        },
        "authorized_scopes": {
            "ownership_entity_id": [p.ownership_entities[0].id],
            "property_id": [p.properties[0].id],
            "building_id": [p.buildings[0].id],
            "unit_id": [p.units[0].id],
        },
        "related_household_ids": [sid("household-resident")],
        "assignment_ids": [sid("assignment-hvac")],
        "related_record": True,
        "sensitivity": "internal",
        "active": True,
        "organization_wide": False,
        "approval_present": True,
        "reason": "synthetic contract review",
    }

    def mkctx(role, **updates):
        return PermissionContext(role=role, **{**base_scope, **updates})

    owner_tech = evaluate_permission("technical_admin", Action.DETAIL, mkctx(Role.OWNER))
    owner_sensitive_no_reason = evaluate_permission("restricted_document", Action.SENSITIVE, mkctx(Role.OWNER, sensitivity="restricted", reason=None))
    admin_tech = evaluate_permission("technical_admin", Action.DETAIL, mkctx(Role.ADMIN))
    leasing_owner_reserved = evaluate_permission("lease", Action.APPROVE, mkctx(Role.LEASING, delegated=True))
    accounting_unrelated = evaluate_permission("ledger", Action.SUBMIT, mkctx(Role.ACCOUNTING, related_record=False))
    subcontractor_unassigned = evaluate_permission("assignment", Action.DETAIL, mkctx(Role.SUBCONTRACTOR, assignment_ids=[]))
    resident_unrelated_household = evaluate_permission("household", Action.DETAIL, mkctx(Role.RESIDENT, related_household_ids=[]))
    expired_actor = evaluate_permission("unit", Action.DETAIL, mkctx(Role.MAINTENANCE, active=False))
    cross_org = evaluate_permission("unit", Action.DETAIL, mkctx(Role.MAINTENANCE, actor_organization_id=sid("other-org")))

    assert owner_tech.allowed_in_simulation is False
    assert owner_sensitive_no_reason.allowed_in_simulation is False
    assert admin_tech.allowed_in_simulation is True
    assert leasing_owner_reserved.allowed_in_simulation is False
    assert accounting_unrelated.allowed_in_simulation is False
    assert subcontractor_unassigned.allowed_in_simulation is False
    assert resident_unrelated_household.allowed_in_simulation is False
    assert expired_actor.allowed_in_simulation is False
    assert cross_org.allowed_in_simulation is False


# delegation simulation tests (execution always disabled)
def test_delegation_scenarios_cover_threshold_scope_and_revision_cases():
    from foundation.catalog import delegation_examples

    policy, grant, request, _ = delegation_examples()
    now = datetime(2026, 9, 21, tzinfo=timezone.utc)

    eligible = evaluate_delegation(request, grant, policy, grant.delegate_id, now)
    assert eligible.result == "eligible"
    assert eligible.executed is False

    over_parts = evaluate_delegation(
        request.model_copy(
            update={
                "requested_amount": request.requested_amount.model_copy(update={"amount_minor": 70000}),
                "cumulative_issue_amount": request.cumulative_issue_amount.model_copy(update={"amount_minor": 70000}),
            }
        ),
        grant,
        policy,
        grant.delegate_id,
        now,
    )
    assert over_parts.result == "manager_required"

    over_max = evaluate_delegation(
        request.model_copy(
            update={
                "requested_amount": request.requested_amount.model_copy(update={"amount_minor": 110000}),
                "cumulative_issue_amount": request.cumulative_issue_amount.model_copy(update={"amount_minor": 110000}),
            }
        ),
        grant,
        policy,
        grant.delegate_id,
        now,
    )
    assert over_max.result == "denied"

    expired = evaluate_delegation(request, grant, policy, grant.delegate_id, datetime(2028, 1, 1, tzinfo=timezone.utc))
    future = evaluate_delegation(request, grant, policy, grant.delegate_id, datetime(2026, 1, 1, tzinfo=timezone.utc))
    wrong_actor = evaluate_delegation(request, grant, policy, sid("not-assigned"), now)
    wrong_property = evaluate_delegation(request.model_copy(update={"scope": request.scope.model_copy(update={"property_id": sid("another-property")})}), grant, policy, grant.delegate_id, now)
    self_approval = evaluate_delegation(request, grant, policy, request.requesting_employee_id, now)
    owner_reserved = evaluate_delegation(request.model_copy(update={"decision_type": "new_lease"}), grant, policy, grant.delegate_id, now)
    budget_unknown = evaluate_delegation(request.model_copy(update={"approved_budget_remaining": None}), grant, policy, grant.delegate_id, now)
    rent_check = evaluate_delegation(
        request.model_copy(
            update={
                "monthly_rent": request.monthly_rent.model_copy(update={"amount_minor": 10000}),
                "cumulative_issue_amount": request.cumulative_issue_amount.model_copy(update={"amount_minor": 30000}),
            }
        ),
        grant,
        policy,
        grant.delegate_id,
        now,
    )
    emergency = evaluate_delegation(request.model_copy(update={"emergency": True, "decision_type": "protect_life_property"}), grant, policy, grant.delegate_id, now)
    stale_decision = evaluate_delegation(
        request,
        grant,
        policy,
        grant.delegate_id,
        now,
        decision=ApprovalDecision(
            request_id=request.id,
            request_revision=request.revision,
            request_fingerprint=request.fingerprint(),
            policy_version=policy.version,
            actor_id=grant.delegate_id,
            decision="approve",
            expected_version=1,
            decided_at=now,
            reason="ok",
        ),
        current_version=2,
    )

    assert expired.result == "denied"
    assert future.result == "denied"
    assert wrong_actor.result == "denied"
    assert wrong_property.result == "denied"
    assert self_approval.result == "denied"
    assert owner_reserved.result == "owner_required"
    assert budget_unknown.result == "owner_required"
    assert rent_check.result == "owner_required"
    assert emergency.result == "emergency_exception"
    assert emergency.notification_required is True
    assert emergency.retrospective_review_required is True
    assert stale_decision.result == "denied"


# disconnected integrations and workflow contract guards
def test_disconnected_adapter_and_workflow_contract_guards():
    cmd = AdapterCommand(
        organization_id=sid("organization-demo"),
        actor_id=sid("person-0"),
        correlation_id=sid("correlation"),
        operation="screening.order",
        canonical_record_id=sid("screening-record"),
        idempotency_key="synthetic-key-1234",
    )
    result = DisconnectedAdapter().execute(cmd)
    assert result.accepted is False
    assert result.status == "disconnected"
    assert result.side_effects is False

    with pytest.raises(ValidationError):
        PaymentMethodReference.model_validate(
            {
                "id": str(sid("pmr")),
                "person_id": str(sid("person-0")),
                "provider_token_reference_id": str(sid("provider-token")),
                "kind": "card_token",
                "pan": "4111111111111111",
            }
        )

    with pytest.raises(ValidationError):
        ScreeningRecord.model_validate(
            {
                "id": str(sid("screening")),
                "scope": {"organization_id": str(sid("organization-demo"))},
                "applicant_person_id": str(sid("person-1")),
                "permissible_purpose": "tenant_screening",
                "disclosure_version": "0.1.0",
                "consent_record_id": None,
                "order_id": None,
                "provider_reference_id": None,
                "status": "not_ordered",
                "minimal_normalized_result": "not_requested",
                "restricted_report_document_id": None,
                "restricted_access_policy_version": "0.1.0",
                "criteria_version": "0.1.0",
                "human_reviewer_id": None,
                "recommendation_record_id": None,
                "farouk_final_decision_id": None,
                "adverse_action_case_id": None,
                "dispute_case_id": None,
                "retention_policy_version": "0.1.0",
                "provider_callback_event_id": None,
                "failure_code": None,
                "retry_state": "none",
                "autonomous_decision": True,
            }
        )


# migration fixture and staging validations
def test_migration_fixture_report_is_stable_and_no_writes():
    p = portfolio()
    fixture_text = migration_fixture(p)
    report = validate_import(fixture_text, p)
    statuses = [r.validation_result for r in report.rows]

    assert len(report.rows) == 5
    assert statuses.count("valid") == 1
    assert statuses.count("duplicate") == 1
    assert statuses.count("invalid") == 2
    assert statuses.count("conflict") == 1
    assert report.writes_performed == 0
    assert report.control_totals.expected_rows == 5

    saved = json.loads((ROOT / "contracts" / "fixtures" / "migration-report.json").read_text())
    assert report.report_checksum == saved["report_checksum"]


def test_malformed_csv_is_rejected():
    p = portfolio()
    malformed = "source_system,source_record_id\nInnago,only-two-columns\n"
    with pytest.raises(ValueError, match="CSV header does not match versioned mapping"):
        validate_import(malformed, p)


def test_phase0_fixture_identities_stay_stable():
    assert sid("organization-demo") == UUID("d807a7ad-5ae1-5496-8af8-c4bb9c6d1ef3")
    assert sid("property-elm") == UUID("9960c7ea-3d4b-5fd7-90b3-6360439a6875")
    assert sid("unit-elm-0-2") == UUID("f3bf0ef3-9c0d-5c7e-99d8-2bd5b58ae7d7")
    elm = next(item for item in portfolio().properties if item.id == sid("property-elm"))
    bakery = next(item for item in portfolio().units if item.id == sid("unit-elm-0-2"))
    assert elm.property_type == "mixed_use"
    assert bakery.label == "Bakery C1"
    assert bakery.use == "commercial"


def test_reference_slice_keeps_relationships_outside_the_property_row():
    first = reference_slice()
    second = reference_slice()
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert sid("property-elm") in first.known_property_ids
    assert sid("organization-isolation") in first.known_organization_ids
    assert any(item.interval.ended_on is not None for item in first.ownership)
    occupied = project_phase0_unit_status("occupied")
    assert occupied["occupancy"] == "occupied"
    assert occupied["availability"] == "withheld"
    assert occupied["publication"] == "unpublished"
    assert allowed_space_transition("publication", "unpublished", "published")
    assert not allowed_space_transition("publication", "unpublished", "withdrawn")


def test_reference_slice_rejects_unknown_property_and_second_primary():
    data = reference_slice().model_dump(mode="json")
    foreign = deepcopy(data)
    foreign["ownership"][0]["property_id"] = str(sid("property-not-in-graph"))
    with pytest.raises(ValidationError, match="Ownership relationship outside known organization graph"):
        ReferenceSlice.model_validate(foreign)
    duplicate = deepcopy(data)
    extra = deepcopy(duplicate["portal_access"][0])
    extra["id"] = str(sid("portal-second-primary"))
    extra["person_id"] = str(sid("person-1"))
    extra["account_id"] = str(sid("account-1"))
    duplicate["portal_access"].append(extra)
    with pytest.raises(ValidationError, match="Only one active primary portal account per household"):
        ReferenceSlice.model_validate(duplicate)


def test_public_inquiry_has_no_trusted_actor_and_error_envelope_is_safe():
    assert "actor_id" not in SubmitPublicInquiry.model_fields
    assert "organization_id" not in SubmitPublicInquiry.model_fields
    envelope = SafeErrorEnvelope(
        code="validation_failed",
        message="Check the highlighted fields.",
        correlation_id=sid("correlation-reference"),
        details=[{"field": "email", "reason": "invalid"}],
        retryable=False,
        required_action="correct_fields",
    )
    assert envelope.permission_safe is True
    assert "traceback" not in envelope.model_dump()


def test_customization_answers_cover_q1_through_q120():
    answers = (ROOT / "docs/plans/phase2/APPROVED_CUSTOMIZATION_ANSWERS.md").read_text(encoding="utf-8")
    trace = (ROOT / "docs/plans/phase2/ANSWER_TRACEABILITY.md").read_text(encoding="utf-8")
    requirements = set(re.findall(r"^## (PP-[A-Z]+-\d+)$", (ROOT / "docs/governance/REQUIREMENTS_TRACEABILITY.md").read_text(encoding="utf-8"), re.M))
    decisions = set(re.findall(r"PP-P2-DEC-\d+", (ROOT / "docs/plans/phase2/SCOPE_AND_DECISIONS.md").read_text(encoding="utf-8")))
    found = re.findall(r"^### (Q\d+)\.", answers, re.M)
    mapped = re.findall(r"^\| (Q\d+) \|", trace, re.M)
    expected = [f"Q{number}" for number in range(1, 121)]
    assert found == expected
    assert mapped == expected
    for number in expected:
        block = answers.split(f"### {number}.", 1)[1].split("\n### ", 1)[0]
        assert "- Answer:" in block
        assert block.split("- Answer:", 1)[1].strip()
    cited_decisions = set(re.findall(r"PP-P2-DEC-\d+", trace))
    cited_requirements = set(re.findall(r"PP-(?!P2-DEC)[A-Z]+-\d+", trace))
    assert cited_decisions <= decisions
    assert cited_requirements <= requirements
