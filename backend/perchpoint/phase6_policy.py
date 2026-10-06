"""Phase 6 authorization policy. The identity provider does not decide business authority."""
from __future__ import annotations

from dataclasses import dataclass

COMMON_PASSWORDS = {
    "passwordpassword",
    "correcthorsebatterystaple",
    "hawthornhomes1234",
    "123456789012345",
    "qwertyuiopasdfgh",
    "letmeinletmein",
    "iloveyouiloveyou",
    "adminadminadmin",
    "welcome123456789",
    "password123456",
    "changemechangeme",
}

_CONTENT = frozenset({
    "content.read", "content.edit", "content.preview", "content.publish", "content.schedule",
    "content.report", "content.redirect",
})
_OPERATIONS = frozenset({
    "identity.profile.read", "session.read", "session.revoke", "invitation.create", "membership.read",
    "access.request", "leasing.coordinate", "maintenance.coordinate", "work.assign", "property.read",
    "property.manage", "inquiry.manage", "document.read", "document.manage", "search.read",
    "expense.approve", "resident.read", "household.read", "vendor.admin", "vendor.worker.approve",
    "delegation.grant", "delegation.revoke",
}) | _CONTENT
_RESIDENT = frozenset({"identity.profile.read", "session.read", "session.revoke", "resident.read", "household.read", "document.read", "mfa.enroll"})
BUNDLES = {
    "owner": _OPERATIONS | frozenset({"approval.owner", "delegation.grant", "delegation.revoke", "access.approve", "audit.read", "security.read", "legal.read", "export.create", "accounting.read", "import.manage", "content.approve", "content.emergency", "content.export"}),
    "platform_admin": frozenset({"identity.profile.read", "session.read", "session.revoke", "membership.read", "membership.grant", "role.manage", "scope.manage", "platform.configure", "security.read", "service.manage", "audit.read", "invitation.create"}),
    "project_manager": _OPERATIONS | frozenset({"access.approve", "security.read", "import.manage"}),
    "operations_manager": _OPERATIONS | frozenset({"access.approve", "security.read", "import.manage"}),
    "leasing": _OPERATIONS,
    "leasing_staff": _OPERATIONS,
    "maintenance": frozenset({"identity.profile.read", "session.read", "maintenance.coordinate", "work.assign", "property.read", "document.read"}),
    "maintenance_coordinator": _OPERATIONS,
    "accounting": frozenset({"identity.profile.read", "session.read", "accounting.read", "export.create", "document.read"}),
    "limited_approver": frozenset({"identity.profile.read", "session.read", "expense.approve"}),
    "applicant": _RESIDENT,
    "resident": _RESIDENT,
    "household_adult": _RESIDENT,
    "guarantor": frozenset({"identity.profile.read", "session.read", "document.read"}),
    "vendor_admin": frozenset({"identity.profile.read", "session.read", "vendor.admin", "work.assign", "mfa.enroll"}),
    "vendor_worker": frozenset({"identity.profile.read", "session.read", "work.assign", "mfa.enroll"}),
    "technician": frozenset({"identity.profile.read", "session.read", "work.assign", "mfa.enroll"}),
    "cleaner": frozenset({"identity.profile.read", "session.read", "work.assign", "mfa.enroll"}),
    "service_principal": frozenset({"search.read"}),
}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    authority: str
    assurance: str
    policy_version: str = "phase6-1"


def password_problem(password: str) -> str | None:
    if len(password) < 15:
        return "password_too_short"
    if len(password) > 64:
        return "password_too_long"
    if password.lower() in COMMON_PASSWORDS:
        return "password_common"
    if len(set(password.casefold())) < 4:
        return "password_common"
    return None


OWNER_RESERVED = frozenset({
    "approval.owner", "legal.adverse", "lease.approve", "eviction.decide", "screening.policy",
    "writeoff.material", "insurance.claim", "delegation.policy", "production.launch",
})


def invitation_role_allowed(inviter_role: str, target_role: str) -> bool:
    if target_role in {"owner", "platform_admin"}:
        return False
    external_roles = {
        "applicant",
        "resident",
        "household_adult",
        "guarantor",
        "vendor_admin",
        "vendor_worker",
        "technician",
        "cleaner",
    }
    if target_role in external_roles:
        return inviter_role in {
            "owner",
            "platform_admin",
            "project_manager",
            "operations_manager",
            "leasing",
            "leasing_staff",
            "maintenance_coordinator",
        }
    return inviter_role in {"owner", "platform_admin"}


def approval_authority(amount_minor: int, monthly_rent_minor: int | None, *, capital: bool, emergency: bool) -> str:
    if capital or amount_minor > 120_000 or (monthly_rent_minor is not None and amount_minor > monthly_rent_minor):
        return "owner"
    if emergency and amount_minor <= 120_000:
        return "operations_emergency"
    if amount_minor >= 50_000:
        return "operations"
    return "routine"


def authorize(
    *,
    capability: str,
    role_name: str,
    actor_id: str,
    target_id: str | None = None,
    assurance: str = "aal1",
    reauthenticated_age_seconds: float | None = None,
    self_grant: bool = False,
    self_approval: bool = False,
    delegated: bool = False,
    delegation_active: bool = False,
    suspended: bool = False,
    privileged: bool = False,
) -> Decision:
    if suspended:
        return Decision(False, "suspended", "none", assurance)
    if self_grant or (target_id is not None and actor_id == target_id and capability.startswith("membership.")):
        return Decision(False, "self_grant", "none", assurance)
    if self_approval:
        return Decision(False, "self_approval", "none", assurance)
    if delegated and not delegation_active:
        return Decision(False, "delegation_inactive", "none", assurance)
    if delegated and capability == "delegation.grant":
        return Decision(False, "delegation_non_transitive", "none", assurance)
    if privileged and (assurance != "aal2" or reauthenticated_age_seconds is None or reauthenticated_age_seconds > 300):
        return Decision(False, "step_up_required", role_name, assurance)
    if role_name == "platform_admin" and capability in {"approval.owner", "lease.approve", "expense.approve"}:
        return Decision(False, "technical_role_is_not_business_authority", role_name, assurance)
    if role_name == "owner" and capability in {"platform.secrets", "platform.database"}:
        return Decision(False, "owner_is_not_technical_operator", role_name, assurance)
    if role_name == "leasing" and capability in {"platform.secrets", "audit.delete", "platform.deploy"}:
        return Decision(False, "operations_boundary", role_name, assurance)
    if capability not in BUNDLES.get(role_name, frozenset()):
        return Decision(False, "denied", "none", assurance)
    return Decision(True, "allowed", role_name, assurance)


def recovery_participants(subject_role: str, initiator_role: str, approver_role: str | None) -> str:
    if not subject_role or not initiator_role:
        return "recovery_participant_invalid"
    if subject_role == "owner" and initiator_role == "platform_admin":
        return "allowed"
    if subject_role == "platform_admin" and initiator_role == "owner":
        return "allowed"
    if subject_role in {"leasing", "project_manager", "operations_manager"} and initiator_role == "platform_admin" and approver_role == "owner":
        return "allowed"
    if subject_role in {"owner", "platform_admin", "leasing", "project_manager", "operations_manager"}:
        return "supervised_recovery_required"
    return "allowed"
