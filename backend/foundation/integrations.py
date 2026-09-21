from datetime import datetime
from typing import Literal, Protocol

from pydantic import Field

from .base import Contract, Identifier, Record

ProviderType = Literal["payments", "screening", "e_signature", "voice_sms", "transactional_email", "calendar", "listing_distribution", "accounting_banking", "file_storage", "ai_models"]
PROVIDER_TYPES: list[ProviderType] = ["payments", "screening", "e_signature", "voice_sms", "transactional_email", "calendar", "listing_distribution", "accounting_banking", "file_storage", "ai_models"]


class ExternalReference(Record):
    organization_id: Identifier
    integration_id: Identifier
    canonical_resource: str
    canonical_id: Identifier
    provider_object_type: str
    provider_object_id: str
    environment: Literal["sandbox", "production", "synthetic"]


class IntegrationRecord(Record):
    organization_id: Identifier
    provider_type: ProviderType
    provider_name: str
    environment: Literal["sandbox", "production", "synthetic"]
    connection_status: Literal["disconnected", "pending", "connected", "failed", "disabled"]
    configuration_status: Literal["not_configured", "incomplete", "validated"]
    credential_reference: str | None
    supported_capabilities: list[str]
    required_webhooks: list[str]
    last_successful_sync: datetime | None
    last_failure: str | None
    retry_exception_state: str
    data_ownership: str
    mapping_record_ids: list[Identifier]
    activation_checklist: list[str]
    deactivation_procedure: list[str]
    replacement_procedure: list[str]


class AdapterCommand(Contract):
    organization_id: Identifier
    actor_id: Identifier
    correlation_id: Identifier
    operation: str
    canonical_record_id: Identifier
    idempotency_key: str = Field(min_length=8, max_length=200)
    # References only: never raw screening, payment or document contents.


class AdapterResult(Contract):
    accepted: bool
    status: Literal["disconnected", "pending", "completed", "failed"]
    error_code: str | None
    side_effects: Literal[False] = False


class ProviderAdapter(Protocol):
    def execute(self, command: AdapterCommand) -> AdapterResult: ...


class DisconnectedAdapter:
    def execute(self, command: AdapterCommand) -> AdapterResult:
        return AdapterResult(accepted=False, status="disconnected", error_code="PHASE0_EXECUTION_DISABLED")