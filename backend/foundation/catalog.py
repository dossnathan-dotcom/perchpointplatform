from datetime import datetime, timezone

from .base import Money, Scope
from .delegation import (
    ApprovalRequest,
    Delegation,
    DelegationPolicy,
    evaluate_delegation,
)
from .governance import DOCUMENT_CLASSES, RetentionPolicy
from .migration import CSV_COLUMNS, validate_import
from .permissions import (
    Action,
    PermissionContext,
    evaluate_permission,
    permission_matrix,
)
from .seeds import NOW, integration_registry, money, people_graph, portfolio, sid
from .workflows import IdentityLifecycleContract


def identity_contracts():
    operations = {
        "invitation": ["Named recipient and organization scope", "Single-use hashed token; expiry pending approval"],
        "registration": ["Validated invitation or approved public applicant route", "One person; independent credential; no shared passwords"],
        "email_verification": ["Single-use challenge", "Do not expose whether an address exists"],
        "password_reset": ["Uniform responses and abuse limits", "Single-use hashed token; revoke existing sessions"],
        "mfa_enrollment": ["Recent reauthentication", "Prefer phishing-resistant factors for privileged users"],
        "mfa_recovery": ["Verified independent recovery; no shared master code", "Recovery alerts and revocation; HawkVision controls recovery"],
        "session_duration": ["Idle and absolute duration by assurance/role", "Durations await security approval; server enforced"],
        "session_revocation": ["Revoke by account, session, role or incident", "Invalidate server sessions and worker grants"],
        "device_session_visibility": ["Show active devices and last access", "Allow individual and all-session revocation"],
        "privileged_reauthentication": ["Recent step-up with purpose", "Required for restricted access, permissions and credentials"],
        "staff_termination": ["Authorized termination event", "Immediate session/role revocation; historical attribution retained"],
        "subcontractor_expiration": ["Assignment and access end timestamps", "Revoke access on expiry regardless of session expiry"],
        "resident_activation": ["Approved household relationship", "Individual verified identity for every adult signer"],
        "applicant_resident_conversion": ["Owner-approved decision and lease gate", "Reuse person ID; end applicant relationship; preserve history"],
        "lockout_abuse": ["Account/device/IP-aware rate limits", "Bounded lockout, enumeration resistance, recovery abuse review"],
        "technical_admin_access": ["Named technical identity with MFA", "Separate business, infrastructure and development purpose"],
        "emergency_support_access": ["Approved incident, purpose and expiry", "Visible indication; least scope; retrospective review"],
        "impersonation": ["Not available in Phase 0", "Future dual identity, explicit approval, reason, time limit and banner"],
    }
    return [IdentityLifecycleContract(version="0.1.0", operation=k, preconditions=v, required_evidence=["Actor, purpose, policy version and correlation reference"], resulting_events=[f"account_lifecycle.{k}"], revocation_behavior="Re-evaluate current relationships server-side; preserve historical actor IDs", ttl_seconds=None, approval_status="pending_farouk_and_security_review") for k,v in operations.items()]


def delegation_examples():
    scope = Scope(organization_id=sid("organization-demo"), property_id=sid("property-elm"))
    expiry = datetime(2027,9,21,tzinfo=timezone.utc)
    policy = DelegationPolicy(version="0.1.0", staff_limit=money(250), parts_limit=money(500), repair_rent_multiplier=1, owner_reserved=["new_lease", "final_applicant", "legal_matter"], effective_at=NOW, expires_at=expiry)
    grant = Delegation(id=sid("delegation-example"), delegate_id=sid("person-5"), approver_id=sid("owner-approver"), scope=scope, maximum_value=money(1000), decision_types=["routine_purchase", "protect_life_property", "new_lease", "final_applicant", "legal_matter"], expense_categories=["parts", "repair", "legal"], effective_at=NOW, expires_at=expiry, temporary=True, policy_version=policy.version)
    request = ApprovalRequest(id=sid("approval-request"), revision=1, decision_type="routine_purchase", expense_category="parts", requested_amount=money(100), cumulative_issue_amount=money(100), monthly_rent=money(2250), approved_budget_remaining=money(3000), scope=scope, requesting_employee_id=sid("person-6"), assigned_approver_id=sid("person-5"), vendor_id=sid("vendor-example"), emergency=False, supporting_evidence=["Synthetic quote reference; no file uploaded"], prior_approval_ids=[], legal_compliance_sensitive=False)
    variants = [
        ("Delegated approval below threshold", request, grant, NOW, "eligible"),
        ("Approval exceeds delegated authority", request.model_copy(update={"requested_amount":Money(**money(1200)),"cumulative_issue_amount":Money(**money(1200))}), grant, NOW, "denied"),
        ("Expired delegation", request, grant, datetime(2028,1,1,tzinfo=timezone.utc), "denied"),
        ("Emergency maintenance exception", request.model_copy(update={"emergency":True,"decision_type":"protect_life_property"}), grant, NOW, "emergency_exception"),
    ]
    results = []
    for title, req, delegation, at, expected in variants:
        req = ApprovalRequest.model_validate(req.model_dump())
        result = evaluate_delegation(req, delegation, policy, grant.delegate_id, at)
        results.append({"name": title, "expected": expected, "actual": result.result, "detail": result.model_dump(mode="json")})
    return policy, grant, request, results


def migration_fixture(p):
    org = str(p.organizations[0].id)
    b = p.buildings[0]
    base = f"Innago-synthetic,SRC-001,{org},{b.property_id},{b.id},EXAMPLE-NEW,residential,120000,USD,2"
    lines = [",".join(CSV_COLUMNS), base, base,
        f"Innago-synthetic,SRC-002,{org},{b.property_id},{b.id},INVALID,residential,-1,USD,0",
        f"Innago-synthetic,SRC-003,{org},{b.property_id},{sid('unknown-building')},BAD-CHAIN,residential,100000,USD,1",
        f"Innago-synthetic,SRC-004,{org},{b.property_id},{b.id},{p.units[0].label},residential,225000,USD,3"]
    return "\n".join(lines)+"\n"


def foundation_bundle():
    p = portfolio()
    people = people_graph(p)
    policy, delegation, request, scenarios = delegation_examples()
    assignment_id = sid("assignment-hvac")
    for role in permission_matrix().roles:
        resource = {"owner":"property", "super-admin":"technical_admin", "leasing":"application", "accounting":"ledger", "maintenance":"assignment", "subcontractor":"assignment", "resident":"household", "applicant":"application"}[role.value]
        ctx = PermissionContext(role=role, actor_organization_id=p.organizations[0].id, record_scope=Scope(organization_id=p.organizations[0].id, property_id=p.properties[0].id, household_id=people.households[0].id, assignment_id=assignment_id), organization_wide=True, related_household_ids=[people.households[0].id], assignment_ids=[assignment_id], related_record=True, sensitivity="internal", active=True, reason="Synthetic access-contract evaluation", approval_present=True)
        result = evaluate_permission(resource, Action.DETAIL, ctx)
        scenarios.append({"name": f"{role.value} access preview", "expected": True, "actual": result.allowed_in_simulation, "detail": result.model_dump()})
    denied = ctx.model_copy(update={"role":"subcontractor", "sensitivity":"restricted", "assignment_ids":[]})
    sensitive = evaluate_permission("restricted_document", Action.SENSITIVE, denied)
    scenarios.append({"name": "Sensitive document access denied", "expected": False, "actual": sensitive.allowed_in_simulation, "detail": sensitive.model_dump()})
    return {"version": "0.1.0", "data_status": "synthetic_contracts_only", "portfolio": p.model_dump(mode="json"), "people": people.model_dump(mode="json"), "permissions": permission_matrix().model_dump(mode="json"), "delegation": {"policy": policy.model_dump(mode="json"), "grant": delegation.model_dump(mode="json"), "request": request.model_dump(mode="json")}, "integrations": [i.model_dump(mode="json") for i in integration_registry(p)], "identity": [i.model_dump(mode="json") for i in identity_contracts()], "retention": [RetentionPolicy(id=sid(f"retention-{kind}"), version="0.1.0", document_class=kind, jurisdiction_policy_id=None, trigger_event="Class-specific trigger awaiting qualified review", retention_days=None, legal_review_status="qualified_review_required").model_dump(mode="json") for kind in DOCUMENT_CLASSES], "scenarios": scenarios, "migration": validate_import(migration_fixture(p),p).model_dump(mode="json")}