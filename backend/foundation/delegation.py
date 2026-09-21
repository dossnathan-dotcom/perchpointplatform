"""Pure deterministic policy simulation; no approval persistence or notifications."""
import hashlib
from datetime import datetime
from typing import Literal

from pydantic import Field

from .base import Contract, Identifier, Money, Scope


class DelegationPolicy(Contract):
    version: str
    staff_limit: Money
    parts_limit: Money
    repair_rent_multiplier: float = Field(gt=0)
    owner_reserved: list[str]
    effective_at: datetime
    expires_at: datetime
    status: Literal["seeded_pending_farouk"] = "seeded_pending_farouk"


class Delegation(Contract):
    id: Identifier
    delegate_id: Identifier
    approver_id: Identifier
    scope: Scope
    maximum_value: Money
    decision_types: list[str]
    expense_categories: list[str]
    effective_at: datetime
    expires_at: datetime
    temporary: bool
    policy_version: str


class ApprovalRequest(Contract):
    id: Identifier
    revision: int = Field(ge=1)
    decision_type: str
    expense_category: str
    requested_amount: Money
    cumulative_issue_amount: Money
    monthly_rent: Money | None
    approved_budget_remaining: Money | None
    scope: Scope
    requesting_employee_id: Identifier
    assigned_approver_id: Identifier
    vendor_id: Identifier | None
    emergency: bool
    supporting_evidence: list[str]
    prior_approval_ids: list[Identifier]
    legal_compliance_sensitive: bool

    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class ApprovalDecision(Contract):
    request_id: Identifier
    request_revision: int
    request_fingerprint: str
    policy_version: str
    actor_id: Identifier
    decision: Literal["approve", "reject"]
    expected_version: int
    decided_at: datetime
    reason: str = Field(min_length=1)


class DelegationResult(Contract):
    result: Literal["eligible", "owner_required", "manager_required", "denied", "emergency_exception"]
    reasons: list[str]
    notification_required: bool = False
    retrospective_review_required: bool = False
    executed: Literal[False] = False


def evaluate_delegation(request: ApprovalRequest, delegation: Delegation, policy: DelegationPolicy,
                        actor_id: Identifier, at: datetime, decision: ApprovalDecision | None = None,
                        current_version: int = 0) -> DelegationResult:
    def result(value, reason, **kwargs):
        return DelegationResult(result=value, reasons=[reason], **kwargs)
    if actor_id == request.requesting_employee_id:
        return result("denied", "Self-approval forbidden")
    if actor_id != delegation.delegate_id or actor_id != request.assigned_approver_id:
        return result("denied", "Not the assigned delegated approver")
    if not (delegation.effective_at <= at < delegation.expires_at and policy.effective_at <= at < policy.expires_at):
        return result("denied", "Expired or not-yet-effective delegation/policy")
    if delegation.policy_version != policy.version:
        return result("denied", "Explicit policy-version acceptance required")
    for key, value in delegation.scope.model_dump().items():
        if value is not None and getattr(request.scope, key) != value:
            return result("denied", "Outside delegated scope")
    amounts = [request.requested_amount, request.cumulative_issue_amount, delegation.maximum_value, policy.staff_limit, policy.parts_limit]
    amounts += [m for m in [request.monthly_rent, request.approved_budget_remaining] if m]
    if len({m.currency for m in amounts}) != 1:
        return result("denied", "Currency mismatch requires explicit conversion policy")
    if request.cumulative_issue_amount.amount_minor < request.requested_amount.amount_minor:
        return result("denied", "Cumulative issue amount must include this request")
    if request.decision_type not in delegation.decision_types or request.expense_category not in delegation.expense_categories:
        return result("denied", "Decision/category outside delegation")
    if decision and (decision.request_id != request.id or decision.request_revision != request.revision or decision.request_fingerprint != request.fingerprint() or decision.policy_version != policy.version or decision.expected_version != current_version or decision.actor_id != actor_id):
        return result("denied", "Stale/materially changed request or conflicting decision")
    if request.legal_compliance_sensitive or request.decision_type in policy.owner_reserved:
        return result("owner_required", "Owner-reserved business decision")
    if not request.supporting_evidence:
        return result("denied", "Supporting evidence required")
    if request.emergency and request.decision_type == "protect_life_property":
        return result("emergency_exception", "Necessary protective action only; not a financial approval", notification_required=True, retrospective_review_required=True)
    total = request.cumulative_issue_amount.amount_minor
    if total > delegation.maximum_value.amount_minor:
        return result("denied", "Cumulative issue cost exceeds delegated value")
    if request.approved_budget_remaining is None or request.requested_amount.amount_minor > request.approved_budget_remaining.amount_minor:
        return result("owner_required", "Outside approved budget or budget unknown")
    if request.monthly_rent and total > request.monthly_rent.amount_minor * policy.repair_rent_multiplier:
        return result("owner_required", "Total repair cost exceeds configured rent comparison")
    if request.expense_category == "parts" and total > policy.parts_limit.amount_minor:
        return result("manager_required", "Above configured parts threshold")
    if total > policy.staff_limit.amount_minor:
        return result("manager_required", "Above configured staff threshold")
    return result("eligible", "Within configured scope, period, budget and independent authority")