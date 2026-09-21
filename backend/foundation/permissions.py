"""Offline permission specification. NEVER use preview role selection as authorization."""
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import Field

from .base import Contract, Identifier, Scope, Sensitivity


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "super-admin"
    LEASING = "leasing"
    ACCOUNTING = "accounting"
    MAINTENANCE = "maintenance"
    SUBCONTRACTOR = "subcontractor"
    RESIDENT = "resident"
    APPLICANT = "applicant"


class Action(str, Enum):
    LIST = "view_list"
    DETAIL = "view_detail"
    SENSITIVE = "view_sensitive_detail"
    CREATE = "create"
    EDIT = "edit"
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    ASSIGN = "assign"
    REASSIGN = "reassign"
    EXPORT = "export"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    ARCHIVE = "delete_or_archive"
    RESTORE = "restore"
    ADJUST = "adjust_financial_record"
    INTEGRATE = "execute_integration_action"
    POLICY = "configure_policy"
    PERMISSIONS = "administer_permissions"


RESOURCES = ["organization", "ownership_entity", "property", "building", "unit", "household", "person", "application", "showing", "lease", "maintenance", "assignment", "vendor", "ledger", "payment", "budget", "document", "restricted_document", "screening_report", "communication", "approval", "delegation", "report", "audit", "integration", "identity", "technical_admin", "source_code", "database_admin", "production_secret", "deployment", "migration_execution", "rls_policy", "developer_flag", "secret_rotation", "support_access", "impersonation"]
FUTURE_ROLES = ["leasing_agent", "property_manager", "maintenance_coordinator", "vendor_administrator", "read_only_auditor", "legal_compliance_reviewer", "household_signer"]


class PermissionRule(Contract):
    resource: str
    action: Action
    role: Role
    organization_scope: Literal["same"] = "same"
    ownership_entity_scope: Literal["authorized"] = "authorized"
    property_scope: Literal["authorized"] = "authorized"
    building_scope: Literal["authorized"] = "authorized"
    unit_scope: Literal["authorized"] = "authorized"
    household_scope: Literal["related", "not_required"] = "not_required"
    assignment_scope: Literal["assigned", "not_required"] = "not_required"
    record_relationship_required: bool = False
    record_sensitivity: list[Sensitivity]
    delegation_eligible: bool = False
    approval_required: bool = False
    audit_required: bool = True
    reason_required: bool = False


class PermissionMatrix(Contract):
    version: Literal["0.1.0"] = "0.1.0"
    default_effect: Literal["deny"] = "deny"
    runtime_enforcement: Literal["not_implemented"] = "not_implemented"
    roles: list[Role]
    future_roles: list[str]
    resources: list[str]
    actions: list[Action]
    allow_rules: list[PermissionRule]


def permission_matrix() -> PermissionMatrix:
    rules = []
    read = [Action.LIST, Action.DETAIL]
    operating = read + [Action.CREATE, Action.EDIT, Action.SUBMIT, Action.ASSIGN, Action.REASSIGN, Action.UPLOAD, Action.DOWNLOAD]
    business = RESOURCES[:24]

    def grant(role, resources, actions, **conditions):
        for resource in resources:
            for action in actions:
                rules.append(PermissionRule(resource=resource, action=action, role=role,
                    record_sensitivity=["public", "internal", "confidential"], **conditions))

    grant(Role.OWNER, business, operating + [Action.EXPORT, Action.ARCHIVE, Action.RESTORE])
    grant(Role.OWNER, ["approval", "application", "lease"], [Action.APPROVE, Action.REJECT], reason_required=True)
    grant(Role.OWNER, ["ledger"], [Action.ADJUST], approval_required=True, reason_required=True)
    grant(Role.OWNER, ["delegation", "budget"], [Action.POLICY], reason_required=True)
    grant(Role.OWNER, ["audit"], read + [Action.EXPORT], reason_required=True)
    technical = RESOURCES[24:]
    grant(Role.ADMIN, [r for r in technical if r != "impersonation"], list(Action), approval_required=True, reason_required=True)
    # No audit deletion, even for administrators; no unrestricted impersonation grant.
    grant(Role.ADMIN, ["audit"], read + [Action.EXPORT], reason_required=True)
    grant(Role.LEASING, ["property", "building", "unit", "household", "person", "application", "showing", "lease", "maintenance", "assignment", "vendor", "communication", "document"], operating)
    grant(Role.LEASING, ["payment", "budget", "approval", "integration"], read)
    grant(Role.LEASING, ["approval"], [Action.APPROVE, Action.REJECT], delegation_eligible=True, approval_required=True, reason_required=True)
    grant(Role.ACCOUNTING, ["ledger", "payment", "report", "budget", "document"], read + [Action.EXPORT, Action.DOWNLOAD], record_relationship_required=True)
    grant(Role.ACCOUNTING, ["ledger", "payment"], [Action.SUBMIT], record_relationship_required=True, approval_required=True, reason_required=True)
    for role in [Role.MAINTENANCE, Role.SUBCONTRACTOR]:
        grant(role, ["assignment", "maintenance", "unit", "document", "communication"], read + [Action.SUBMIT, Action.UPLOAD, Action.DOWNLOAD], assignment_scope="assigned")
    grant(Role.RESIDENT, ["household", "lease", "ledger", "payment", "document", "maintenance", "communication"], read + [Action.SUBMIT, Action.DOWNLOAD], household_scope="related", record_relationship_required=True)
    grant(Role.APPLICANT, ["application", "showing", "document", "communication", "lease"], read + [Action.SUBMIT, Action.UPLOAD, Action.DOWNLOAD], household_scope="related", record_relationship_required=True)
    for resource in ["restricted_document", "screening_report", "identity"]:
        rules.append(PermissionRule(resource=resource, action=Action.SENSITIVE, role=Role.OWNER,
            record_sensitivity=["restricted"], reason_required=True))
    return PermissionMatrix(roles=list(Role), future_roles=FUTURE_ROLES, resources=RESOURCES, actions=list(Action), allow_rules=rules)


class PermissionContext(Contract):
    role: Role
    actor_organization_id: Identifier
    record_scope: Scope
    authorized_scopes: dict[str, list[Identifier]] = Field(default_factory=dict)
    organization_wide: bool = False
    related_household_ids: list[Identifier] = Field(default_factory=list)
    assignment_ids: list[Identifier] = Field(default_factory=list)
    related_record: bool = False
    sensitivity: Sensitivity
    active: bool
    delegated: bool = False
    approval_present: bool = False
    reason: str | None = None


class PermissionResult(Contract):
    allowed_in_simulation: bool
    reason: str
    audit_required: bool = True
    production_authorized: Literal[False] = False


def evaluate_permission(resource: str, action: Action, ctx: PermissionContext) -> PermissionResult:
    def deny(reason):
        return PermissionResult(allowed_in_simulation=False, reason=reason)
    if not ctx.active or ctx.actor_organization_id != ctx.record_scope.organization_id:
        return deny("Inactive relationship or organization mismatch")
    for field in ["ownership_entity_id", "property_id", "building_id", "unit_id"]:
        value = getattr(ctx.record_scope, field)
        if value and not ctx.organization_wide and value not in ctx.authorized_scopes.get(field, []):
            return deny(f"Outside authorized {field}")
    matches = [r for r in permission_matrix().allow_rules if r.resource == resource and r.action == action and r.role == ctx.role]
    for rule in matches:
        if ctx.sensitivity not in rule.record_sensitivity:
            continue
        if rule.household_scope == "related" and ctx.record_scope.household_id not in ctx.related_household_ids:
            continue
        if rule.assignment_scope == "assigned" and ctx.record_scope.assignment_id not in ctx.assignment_ids:
            continue
        if rule.record_relationship_required and not ctx.related_record:
            continue
        if rule.reason_required and not (ctx.reason and ctx.reason.strip()):
            continue
        if rule.delegation_eligible and not ctx.delegated:
            continue
        if rule.approval_required and not ctx.approval_present:
            continue
        return PermissionResult(allowed_in_simulation=True, reason="Contract conditions satisfied; no production grant")
    return deny("Deny by default: no matching grant with all conditions satisfied")


class RoleAssignment(Contract):
    person_id: Identifier
    role: str
    scope: Scope
    effective_at: datetime
    expires_at: datetime | None
    status: Literal["active", "expired", "terminated", "suspended"]