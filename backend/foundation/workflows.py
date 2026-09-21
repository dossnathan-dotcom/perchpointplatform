"""Future workflow record contracts only. There are no workflow execution routes."""
from datetime import datetime
from typing import Literal

from pydantic import Field

from .base import Contract, Identifier, Money, Record, Scope


class ScreeningRecord(Record):
    scope: Scope
    applicant_person_id: Identifier
    permissible_purpose: str
    disclosure_version: str
    consent_record_id: Identifier | None
    order_id: Identifier | None
    provider_reference_id: Identifier | None
    status: Literal["not_ordered", "consent_pending", "pending", "review_required", "failed", "disputed", "closed"]
    minimal_normalized_result: Literal["not_requested", "human_review_required", "provider_unavailable"]
    restricted_report_document_id: Identifier | None
    restricted_access_policy_version: str
    criteria_version: str
    human_reviewer_id: Identifier | None
    recommendation_record_id: Identifier | None
    farouk_final_decision_id: Identifier | None
    adverse_action_case_id: Identifier | None
    dispute_case_id: Identifier | None
    retention_policy_version: str
    provider_callback_event_id: Identifier | None
    failure_code: str | None
    retry_state: str
    autonomous_decision: Literal[False] = False


class ApplicantConsent(Record):
    person_id: Identifier
    disclosure_version: str
    purpose: str
    recorded_at: datetime
    evidence_document_id: Identifier
    withdrawn_at: datetime | None


class PaymentMethodReference(Record):
    person_id: Identifier
    provider_token_reference_id: Identifier
    kind: Literal["card_token", "bank_token"]
    # PAN, CVV, account/routing numbers have no fields and are rejected.


class Charge(Record):
    scope: Scope
    amount: Money
    due_at: datetime
    description: str
    ledger_reference_id: Identifier


class Allocation(Contract):
    charge_id: Identifier
    amount: Money


class PaymentRecord(Record):
    scope: Scope
    method_reference_id: Identifier | None
    charge_ids: list[Identifier]
    allocations: list[Allocation]
    attempt_number: int = Field(ge=0)
    processor_status: Literal["not_started", "pending", "succeeded", "failed", "returned", "refunded", "disputed"]
    ledger_posting_status: Literal["not_posted", "pending", "posted", "exception", "reversed"]
    settlement_status: Literal["not_settled", "pending", "settled", "returned"]
    settled_at: datetime | None
    failure_code: str | None
    ach_return_code: str | None
    refund_record_ids: list[Identifier]
    dispute_record_ids: list[Identifier]
    receipt_document_id: Identifier | None
    autopay_consent_id: Identifier | None
    reconciliation_exception_id: Identifier | None
    idempotency_key: str = Field(min_length=8)
    provider_event_ids: list[Identifier]
    browser_success_is_posting: Literal[False] = False


class PaymentException(Record):
    payment_id: Identifier
    kind: Literal["failure", "ach_return", "refund", "dispute", "reconciliation"]
    amount: Money | None
    provider_event_id: Identifier | None
    status: Literal["open", "review", "resolved"]
    reason: str
    reviewer_id: Identifier | None


class AutopayConsent(Record):
    person_id: Identifier
    payment_method_reference_id: Identifier
    terms_version: str
    amount_limit: Money
    frequency: str
    effective_at: datetime
    revoked_at: datetime | None
    evidence_document_id: Identifier


class IdentityLifecycleContract(Contract):
    version: str
    operation: Literal["invitation", "registration", "email_verification", "password_reset", "mfa_enrollment", "mfa_recovery", "session_duration", "session_revocation", "device_session_visibility", "privileged_reauthentication", "staff_termination", "subcontractor_expiration", "resident_activation", "applicant_resident_conversion", "lockout_abuse", "technical_admin_access", "emergency_support_access", "impersonation"]
    preconditions: list[str]
    required_evidence: list[str]
    resulting_events: list[str]
    revocation_behavior: str
    ttl_seconds: int | None
    approval_status: Literal["pending_farouk_and_security_review"]
    implemented: Literal[False] = False


class SessionContract(Record):
    person_id: Identifier
    account_id: Identifier
    authenticated_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    assurance: Literal["single_factor", "mfa", "step_up"]
    device_label: str
    source_ip_hash: str | None
    purpose: Literal["business", "technical", "development", "emergency_support", "impersonation"]
    support_reason: str | None
    initiating_actor_id: Identifier | None