/* Generated from Pydantic Phase 0 schemas. Do not edit. */

export type AmountMinor = number;
export type Currency = string;
export type EffectiveAt = string;
export type ExpiresAt = string | null;
export type Id = string;
export type SchemaVersion = "0.1.0";
export type Synthetic = boolean;
export type AssignmentId = string | null;
export type BuildingId = string | null;
export type HouseholdId = string | null;
export type OrganizationId = string;
export type OwnershipEntityId = string | null;
export type PropertyId = string | null;
export type SpaceId = string | null;
export type UnitId = string | null;
export type Country = string;
export type County = string;
export type IsExample = boolean;
export type Line1 = string;
export type Municipality = string;
export type PostalCode = string;
export type State = string;
export type BuildingId1 = string | null;
export type Id1 = string;
export type Kind = "hvac" | "appliance" | "meter" | "access" | "plumbing" | "building_system" | "other";
export type Name = string;
export type OrganizationId1 = string;
export type PropertyId1 = string;
export type SchemaVersion1 = "0.1.0";
export type SharedSpaceId = string | null;
export type Synthetic1 = boolean;
export type UnitId1 = string | null;
/**
 * @minItems 1
 */
export type AllowedUses = ["residential" | "commercial", ...("residential" | "commercial")[]];
export type Id2 = string;
export type Name1 = string;
export type OrganizationId2 = string;
export type PropertyId2 = string;
export type SchemaVersion2 = "0.1.0";
export type Synthetic2 = boolean;
export type BuildOutStatus = string;
export type CamNnnTerms = string;
export type IntendedUse = string;
export type LeaseType = string;
export type LoadingAccess = string;
export type Parking = string;
export type RentPeriod = "month" | "year";
export type UtilityResponsibility = string;
export type ZoningNotes = string;
export type BuildingId2 = string | null;
export type Id3 = string;
export type Name2 = string;
export type OrganizationId3 = string;
export type PropertyId3 = string;
export type SchemaVersion3 = "0.1.0";
export type Synthetic3 = boolean;
export type UnitId2 = string | null;
export type Id4 = string;
export type Name3 = string;
export type SchemaVersion4 = "0.1.0";
export type Synthetic4 = boolean;
export type EntityType = "company" | "llc" | "trust" | "individual" | "other";
export type Id5 = string;
export type LegalName = string;
export type ManagementRelationship = "owned" | "third_party_managed";
export type OrganizationId4 = string;
export type SchemaVersion5 = "0.1.0";
export type Synthetic5 = boolean;
export type Assets = Asset[];
export type Buildings = Building[];
export type Organizations = Organization[];
export type OwnershipEntities = OwnershipEntity[];
export type Id6 = string;
export type Name4 = string;
export type OrganizationId5 = string;
export type OwnershipEntityId1 = string;
export type ParcelReferences = string[];
export type PropertyType = "single_family" | "duplex" | "triplex" | "multifamily" | "commercial" | "mixed_use";
export type SchemaVersion6 = "0.1.0";
export type Synthetic6 = boolean;
export type Properties = Property[];
export type BuildingId3 = string | null;
export type Id7 = string;
export type Kind1 =
  "entry" | "hallway" | "parking" | "roof" | "basement" | "laundry" | "utility_room" | "exterior" | "other";
export type Name5 = string;
export type OrganizationId6 = string;
export type PropertyId4 = string;
export type SchemaVersion7 = "0.1.0";
export type Synthetic7 = boolean;
export type UnitId3 = string | null;
export type SharedSpaces = SharedSpace[];
export type AvailableDate = string | null;
export type BuildingId4 = string;
export type Id8 = string;
export type ImageKey = string;
export type Label = string;
export type OrganizationId7 = string;
export type PropertyId5 = string;
export type Bathrooms = number;
export type Bedrooms = number;
export type PetPolicy = string;
export type Utilities = string;
export type SchemaVersion8 = "0.1.0";
export type SquareFeet = number;
export type Status = "available" | "occupied" | "unavailable";
export type Synthetic8 = boolean;
export type Use = "residential" | "commercial";
export type Units = Unit[];
export type Id9 = string;
export type Kind2 = "applicant" | "tenant" | "vendor";
export type LegalName1 = string;
export type OrganizationId8 = string;
export type SchemaVersion9 = "0.1.0";
export type Synthetic9 = boolean;
export type Id10 = string;
export type Label1 = string;
export type OrganizationId9 = string;
export type SchemaVersion10 = "0.1.0";
export type Status1 = "applicant" | "resident" | "former";
export type Synthetic10 = boolean;
export type Id11 = string;
export type IdentityProviderReference = string | null;
export type PersonId = string;
export type SchemaVersion11 = "0.1.0";
export type Status2 = "invited" | "active" | "suspended" | "deactivated" | "synthetic";
export type Synthetic11 = boolean;
export type Accounts = UserAccount[];
export type Businesses = BusinessParty[];
export type Households = Household[];
export type OrganizationIds = string[];
export type AgeClass = "adult" | "minor" | "unknown";
export type DisplayName = string;
export type Id12 = string;
export type IdentityStatus = "unverified" | "verified" | "synthetic";
export type SchemaVersion12 = "0.1.0";
export type Synthetic12 = boolean;
export type People = Person[];
export type AccountId = string | null;
export type AttributableAccessRequired = boolean;
export type BusinessPartyId = string | null;
export type EffectiveAt1 = string;
export type EndedAt = string | null;
export type HouseholdId1 = string | null;
export type Id13 = string;
export type Kind3 =
  | "applicant"
  | "co_applicant"
  | "primary_holder"
  | "adult_signer"
  | "occupant"
  | "minor_occupant"
  | "guarantor"
  | "resident"
  | "former_resident"
  | "emergency_contact"
  | "staff"
  | "maintenance_employee"
  | "subcontractor"
  | "vendor_contact"
  | "business_applicant"
  | "business_tenant";
export type OrganizationId10 = string;
export type PersonId1 = string;
export type SchemaVersion13 = "0.1.0";
export type Synthetic13 = boolean;
export type UnitId4 = string | null;
export type Relationships = PersonRelationship[];
export type Active = boolean;
export type ActorOrganizationId = string;
export type ApprovalPresent = boolean;
export type AssignmentIds = string[];
export type Delegated = boolean;
export type OrganizationWide = boolean;
export type Reason = string | null;
export type RelatedHouseholdIds = string[];
export type RelatedRecord = boolean;
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Role".
 */
export type Role =
  "owner" | "super-admin" | "leasing" | "accounting" | "maintenance" | "subcontractor" | "resident" | "applicant";
export type Sensitivity = "public" | "internal" | "confidential" | "restricted";
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Action".
 */
export type Action =
  | "view_list"
  | "view_detail"
  | "view_sensitive_detail"
  | "create"
  | "edit"
  | "submit"
  | "approve"
  | "reject"
  | "assign"
  | "reassign"
  | "export"
  | "upload"
  | "download"
  | "delete_or_archive"
  | "restore"
  | "adjust_financial_record"
  | "execute_integration_action"
  | "configure_policy"
  | "administer_permissions";
export type Actions = Action[];
export type ApprovalRequired = boolean;
export type AssignmentScope = "assigned" | "not_required";
export type AuditRequired = boolean;
export type BuildingScope = "authorized";
export type DelegationEligible = boolean;
export type HouseholdScope = "related" | "not_required";
export type OrganizationScope = "same";
export type OwnershipEntityScope = "authorized";
export type PropertyScope = "authorized";
export type ReasonRequired = boolean;
export type RecordRelationshipRequired = boolean;
export type RecordSensitivity = ("public" | "internal" | "confidential" | "restricted")[];
export type Resource = string;
export type UnitScope = "authorized";
export type AllowRules = PermissionRule[];
export type DefaultEffect = "deny";
export type FutureRoles = string[];
export type Resources = string[];
export type Roles = Role[];
export type RuntimeEnforcement = "not_implemented";
export type Version = "0.1.0";
export type AllowedInSimulation = boolean;
export type AuditRequired1 = boolean;
export type ProductionAuthorized = false;
export type Reason1 = string;
export type EffectiveAt2 = string;
export type ExpiresAt1 = string | null;
export type PersonId2 = string;
export type Role1 = string;
export type Status3 = "active" | "expired" | "terminated" | "suspended";
export type ActorId = string;
export type DecidedAt = string;
export type Decision = "approve" | "reject";
export type ExpectedVersion = number;
export type PolicyVersion = string;
export type Reason2 = string;
export type RequestFingerprint = string;
export type RequestId = string;
export type RequestRevision = number;
export type AssignedApproverId = string;
export type DecisionType = string;
export type Emergency = boolean;
export type ExpenseCategory = string;
export type Id14 = string;
export type LegalComplianceSensitive = boolean;
export type PriorApprovalIds = string[];
export type RequestingEmployeeId = string;
export type Revision = number;
export type SupportingEvidence = string[];
export type VendorId = string | null;
export type ApproverId = string;
export type DecisionTypes = string[];
export type DelegateId = string;
export type EffectiveAt3 = string;
export type ExpenseCategories = string[];
export type ExpiresAt2 = string;
export type Id15 = string;
export type PolicyVersion1 = string;
export type Temporary = boolean;
export type EffectiveAt4 = string;
export type ExpiresAt3 = string;
export type OwnerReserved = string[];
export type RepairRentMultiplier = number;
export type Status4 = "seeded_pending_farouk";
export type Version1 = string;
export type Executed = false;
export type NotificationRequired = boolean;
export type Reasons = string[];
export type Result = "eligible" | "owner_required" | "manager_required" | "denied" | "emergency_exception";
export type RetrospectiveReviewRequired = boolean;
export type ActorId1 = string;
export type CanonicalRecordId = string;
export type CorrelationId = string;
export type IdempotencyKey = string;
export type Operation = string;
export type OrganizationId11 = string;
export type Accepted = boolean;
export type ErrorCode = string | null;
export type SideEffects = false;
export type Status5 = "disconnected" | "pending" | "completed" | "failed";
export type CanonicalId = string;
export type CanonicalResource = string;
export type Environment = "sandbox" | "production" | "synthetic";
export type Id16 = string;
export type IntegrationId = string;
export type OrganizationId12 = string;
export type ProviderObjectId = string;
export type ProviderObjectType = string;
export type SchemaVersion14 = "0.1.0";
export type Synthetic14 = boolean;
export type ActivationChecklist = string[];
export type ConfigurationStatus = "not_configured" | "incomplete" | "validated";
export type ConnectionStatus = "disconnected" | "pending" | "connected" | "failed" | "disabled";
export type CredentialReference = string | null;
export type DataOwnership = string;
export type DeactivationProcedure = string[];
export type Environment1 = "sandbox" | "production" | "synthetic";
export type Id17 = string;
export type LastFailure = string | null;
export type LastSuccessfulSync = string | null;
export type MappingRecordIds = string[];
export type OrganizationId13 = string;
export type ProviderName = string;
export type ProviderType =
  | "payments"
  | "screening"
  | "e_signature"
  | "voice_sms"
  | "transactional_email"
  | "calendar"
  | "listing_distribution"
  | "accounting_banking"
  | "file_storage"
  | "ai_models";
export type ReplacementProcedure = string[];
export type RequiredWebhooks = string[];
export type RetryExceptionState = string;
export type SchemaVersion15 = "0.1.0";
export type SupportedCapabilities = string[];
export type Synthetic15 = boolean;
export type ChargeId = string;
export type DisclosureVersion = string;
export type EvidenceDocumentId = string;
export type Id18 = string;
export type PersonId3 = string;
export type Purpose = string;
export type RecordedAt = string;
export type SchemaVersion16 = "0.1.0";
export type Synthetic16 = boolean;
export type WithdrawnAt = string | null;
export type EffectiveAt5 = string;
export type EvidenceDocumentId1 = string;
export type Frequency = string;
export type Id19 = string;
export type PaymentMethodReferenceId = string;
export type PersonId4 = string;
export type RevokedAt = string | null;
export type SchemaVersion17 = "0.1.0";
export type Synthetic17 = boolean;
export type TermsVersion = string;
export type Description = string;
export type DueAt = string;
export type Id20 = string;
export type LedgerReferenceId = string;
export type SchemaVersion18 = "0.1.0";
export type Synthetic18 = boolean;
export type ApprovalStatus = "pending_farouk_and_security_review";
export type Implemented = false;
export type Operation1 =
  | "invitation"
  | "registration"
  | "email_verification"
  | "password_reset"
  | "mfa_enrollment"
  | "mfa_recovery"
  | "session_duration"
  | "session_revocation"
  | "device_session_visibility"
  | "privileged_reauthentication"
  | "staff_termination"
  | "subcontractor_expiration"
  | "resident_activation"
  | "applicant_resident_conversion"
  | "lockout_abuse"
  | "technical_admin_access"
  | "emergency_support_access"
  | "impersonation";
export type Preconditions = string[];
export type RequiredEvidence = string[];
export type ResultingEvents = string[];
export type RevocationBehavior = string;
export type TtlSeconds = number | null;
export type Version2 = string;
export type Id21 = string;
export type Kind4 = "failure" | "ach_return" | "refund" | "dispute" | "reconciliation";
export type PaymentId = string;
export type ProviderEventId = string | null;
export type Reason3 = string;
export type ReviewerId = string | null;
export type SchemaVersion19 = "0.1.0";
export type Status6 = "open" | "review" | "resolved";
export type Synthetic19 = boolean;
export type Id22 = string;
export type Kind5 = "card_token" | "bank_token";
export type PersonId5 = string;
export type ProviderTokenReferenceId = string;
export type SchemaVersion20 = "0.1.0";
export type Synthetic20 = boolean;
export type AchReturnCode = string | null;
export type Allocations = Allocation[];
export type AttemptNumber = number;
export type AutopayConsentId = string | null;
export type BrowserSuccessIsPosting = false;
export type ChargeIds = string[];
export type DisputeRecordIds = string[];
export type FailureCode = string | null;
export type Id23 = string;
export type IdempotencyKey1 = string;
export type LedgerPostingStatus = "not_posted" | "pending" | "posted" | "exception" | "reversed";
export type MethodReferenceId = string | null;
export type ProcessorStatus = "not_started" | "pending" | "succeeded" | "failed" | "returned" | "refunded" | "disputed";
export type ProviderEventIds = string[];
export type ReceiptDocumentId = string | null;
export type ReconciliationExceptionId = string | null;
export type RefundRecordIds = string[];
export type SchemaVersion21 = "0.1.0";
export type SettledAt = string | null;
export type SettlementStatus = "not_settled" | "pending" | "settled" | "returned";
export type Synthetic21 = boolean;
export type AdverseActionCaseId = string | null;
export type ApplicantPersonId = string;
export type AutonomousDecision = false;
export type ConsentRecordId = string | null;
export type CriteriaVersion = string;
export type DisclosureVersion1 = string;
export type DisputeCaseId = string | null;
export type FailureCode1 = string | null;
export type FaroukFinalDecisionId = string | null;
export type HumanReviewerId = string | null;
export type Id24 = string;
export type MinimalNormalizedResult = "not_requested" | "human_review_required" | "provider_unavailable";
export type OrderId = string | null;
export type PermissiblePurpose = string;
export type ProviderCallbackEventId = string | null;
export type ProviderReferenceId = string | null;
export type RecommendationRecordId = string | null;
export type RestrictedAccessPolicyVersion = string;
export type RestrictedReportDocumentId = string | null;
export type RetentionPolicyVersion = string;
export type RetryState = string;
export type SchemaVersion22 = "0.1.0";
export type Status7 =
  "not_ordered" | "consent_pending" | "pending" | "review_required" | "failed" | "disputed" | "closed";
export type Synthetic22 = boolean;
export type AccountId1 = string;
export type Assurance = "single_factor" | "mfa" | "step_up";
export type AuthenticatedAt = string;
export type DeviceLabel = string;
export type ExpiresAt4 = string;
export type Id25 = string;
export type InitiatingActorId = string | null;
export type PersonId6 = string;
export type Purpose1 = "business" | "technical" | "development" | "emergency_support" | "impersonation";
export type RevokedAt1 = string | null;
export type SchemaVersion23 = "0.1.0";
export type SourceIpHash = string | null;
export type SupportReason = string | null;
export type Synthetic23 = boolean;
export type Action1 = string;
export type ActorId2 = string;
export type CorrelationId1 = string;
export type DelegatedAuthorityId = string | null;
export type EffectiveRole = string;
export type EventHash = string;
export type Id26 = string;
export type PreviousEventHash = string | null;
export type Reason4 = string | null;
export type RelatedApprovalId = string | null;
export type RelatedProviderEventId = string | null;
export type ResourceId = string;
export type ResourceType = string;
export type Result1 = "allowed" | "denied" | "failed" | "simulated";
export type SchemaVersion24 = "0.1.0";
export type SourceChannel = "web" | "api" | "worker" | "migration" | "support" | "synthetic";
export type Synthetic24 = boolean;
export type Timestamp = string;
export type AccessRule = string;
export type AuditRequired2 = boolean;
export type ChecksumSha256 = string;
export type DeletionEligible = boolean;
export type DocumentClass =
  | "application_document"
  | "identity_document"
  | "screening_document"
  | "lease"
  | "addendum"
  | "notice"
  | "payment_evidence"
  | "maintenance_media"
  | "estimate"
  | "invoice"
  | "insurance_policy"
  | "vendor_credential"
  | "inspection"
  | "property_record"
  | "legal_document"
  | "communication_attachment"
  | "migration_archive";
export type DownloadRule = string;
export type EffectiveAt6 = string | null;
export type ExpiresAt5 = string | null;
export type Id27 = string;
export type LegalHold = boolean;
export type OwnerOrganizationId = string;
export type OwnerPersonId = string | null;
export type RelatedRecordIds = string[];
export type RetentionRuleId = string;
export type SchemaVersion25 = "0.1.0";
export type Sensitivity1 = "public" | "internal" | "confidential" | "restricted";
export type Source = string;
export type StorageReferenceId = string | null;
export type Synthetic25 = boolean;
export type Version3 = number;
export type AggregateId = string;
export type AggregateVersion = number;
export type CausationId = string | null;
export type CorrelationId2 = string;
export type Domain =
  | "payment"
  | "screening"
  | "lease"
  | "showing"
  | "communication"
  | "maintenance"
  | "approval"
  | "document"
  | "migration"
  | "account_lifecycle";
export type EventType = string;
export type Id28 = string;
export type OccurredAt = string;
export type OrganizationId14 = string;
export type PayloadRecordIds = string[];
export type SchemaVersion26 = "0.1.0";
export type Synthetic26 = boolean;
export type DeduplicationKey = string;
export type FailureCode2 = string | null;
export type Id29 = string;
export type ProcessedAt = string | null;
export type CanonicalEventId = string | null;
export type Id30 = string;
export type IntegrationId1 = string;
export type OrganizationId15 = string;
export type PayloadChecksum = string;
export type ProviderEventId1 = string;
export type ReceivedAt = string;
export type SchemaVersion27 = "0.1.0";
export type SignatureVerified = boolean;
export type Synthetic27 = boolean;
export type SchemaVersion28 = "0.1.0";
export type State1 = "received" | "validated" | "processed" | "rejected" | "failed";
export type Synthetic28 = boolean;
export type ApprovedRuleDocumentId = string | null;
export type ConflictResolution = "qualified_review_required";
export type Country1 = string;
export type County1 = string | null;
export type EffectiveAt7 = string;
export type ExpiresAt6 = string | null;
export type Id31 = string;
export type LeaseType1 = string | null;
export type Municipality1 = string | null;
export type PolicyArea =
  | "application_disclosures"
  | "screening"
  | "fees"
  | "notices"
  | "deposits"
  | "late_payment"
  | "maintenance"
  | "retention"
  | "lease_templates"
  | "emergency_instructions";
export type PropertyId6 = string | null;
export type SchemaVersion29 = "0.1.0";
export type State2 = string | null;
export type Synthetic29 = boolean;
export type UnitType = string | null;
export type Version4 = string;
export type Attempts = number;
export type ClaimExpiresAt = string | null;
export type Id32 = string;
export type IdempotencyKey2 = string;
export type LastError = string | null;
export type NextAttemptAt = string | null;
export type SchemaVersion30 = "0.1.0";
export type State3 = "pending" | "claimed" | "delivered" | "failed" | "dead_letter";
export type Synthetic30 = boolean;
export type DeletionWithoutReview = false;
export type DocumentClass1 =
  | "application_document"
  | "identity_document"
  | "screening_document"
  | "lease"
  | "addendum"
  | "notice"
  | "payment_evidence"
  | "maintenance_media"
  | "estimate"
  | "invoice"
  | "insurance_policy"
  | "vendor_credential"
  | "inspection"
  | "property_record"
  | "legal_document"
  | "communication_attachment"
  | "migration_archive";
export type Id33 = string;
export type JurisdictionPolicyId = string | null;
export type LegalHoldOverridesDeletion = true;
export type LegalReviewStatus = "qualified_review_required";
export type RetentionDays = number | null;
export type SchemaVersion31 = "0.1.0";
export type Synthetic31 = boolean;
export type TriggerEvent = string;
export type Version5 = string;
export type ApprovalId = string | null;
export type Id34 = string;
export type ImmutableReportChecksum = string | null;
export type MappingVersion = string;
export type OrganizationId16 = string;
export type RollbackBatchId = string | null;
export type SchemaVersion32 = "0.1.0";
export type SourceChecksum = string;
export type SourceFile = string;
export type SourceSystem = string;
export type Status8 = "staging" | "review" | "approved" | "imported" | "rolled_back";
export type Synthetic32 = boolean;
export type ConflictRows = number;
export type DocumentCountDifference = number;
export type DocumentReconciliation = "review_required" | "matched";
export type DuplicateRows = number;
export type ExpectedRows = number;
export type FinancialDifferenceMinor = number;
export type FinancialReconciliation = "review_required" | "matched";
export type ObservedRows = number;
export type RejectedRows = number;
export type SourceDocumentCount = number;
export type SourceFinancialTotalMinor = number;
export type StagedDocumentCount = number;
export type StagedValidTotalMinor = number;
export type ValidRows = number;
export type MappingVersion1 = "0.1.0";
export type ReportChecksum = string;
export type RollbackStrategy = "batch-scoped reversible mappings; compensating financial entries; never erase audits";
export type ApprovalId1 = string | null;
export type Conflict = string | null;
export type Correction = string | null;
export type DuplicateCandidate = string | null;
export type ImportedCanonicalRecordId = string | null;
export type Issues = string[];
export type Rejected = boolean;
export type RowNumber = number;
export type SourceFile1 = string;
export type SourceRecordIdentifier = string;
export type SourceSystem1 = string;
export type ValidationResult = "valid" | "invalid" | "duplicate" | "conflict";
export type Rows = StagingRecord[];
export type WritesPerformed = 0;
export type ActorId3 = string | null;
export type Id35 = string;
export type OccurredAt1 = string;
export type OrganizationId17 = string;
export type ResourceId1 = string;
export type ResourceType1 = string;
export type SchemaVersion33 = "0.2.0";
export type Summary = string;
export type Synthetic33 = boolean;
export type Visibility = "staff" | "resident" | "public";
export type Engine = "read_only_example";
export type Id36 = string;
export type OrganizationId18 = string;
export type SchemaVersion34 = "0.2.0";
export type State4 = "pending" | "approved" | "denied";
export type Synthetic34 = boolean;
export type Title = string;
export type Accepted1 = boolean;
export type AggregateId1 = string | null;
export type AggregateVersion1 = number | null;
export type CorrelationId3 = string;
export type Id37 = string;
export type Message = string;
export type Replayed = boolean;
export type ResultCode = string;
export type SchemaVersion35 = "0.2.0";
export type Synthetic35 = boolean;
/**
 * @minItems 1
 */
export type AllowedUses1 = ["residential" | "commercial", ...("residential" | "commercial")[]];
export type AggregateId2 = string;
export type ExpectedVersion2 = number;
export type Name6 = string;
export type PropertyId7 = string;
export type ClientObservedAt = string | null;
export type CorrelationId4 = string;
export type IdempotencyKey3 = string;
export type RequestFingerprint1 = string;
export type BuildingId5 = string;
export type Label2 = string;
export type PropertyId8 = string;
export type SquareFeet1 = number;
export type Use1 = "residential" | "commercial";
export type Name7 = string;
export type ParcelReferences1 = string[];
export type PropertyType1 = "single_family" | "duplex" | "triplex" | "multifamily" | "commercial" | "mixed_use";
export type AttemptNumber1 = number;
export type FinishedAt = string | null;
export type Id38 = string;
export type OutboxId = string;
export type Outcome = "delivered" | "retryable" | "dead_letter";
export type RepeatsBusinessDecision = false;
export type SchemaVersion36 = "0.2.0";
export type StartedAt = string;
export type Synthetic36 = boolean;
export type IdempotencyKey4 = string;
export type Operation2 = "echo" | "signed_webhook";
export type OrganizationId19 = string;
export type PayloadRecordIds1 = string[];
export type Accepted2 = boolean;
export type LiveNetwork = false;
export type ProviderEventId2 = string | null;
export type Status9 = "synthetic_ok" | "synthetic_rejected";
export type AccountId2 = string;
export type AuthorizationReason = string;
export type HouseholdId2 = string;
export type Id39 = string;
export type EffectiveAt8 = string;
export type EndedAt1 = string | null;
export type Kind6 = "primary" | "additional";
export type OrganizationId20 = string;
export type PersonId7 = string;
export type SchemaVersion37 = "0.2.0";
export type Synthetic37 = boolean;
export type EffectiveOn = string;
export type EndedOn = string | null;
export type Id40 = string;
export type ManagerOrganizationId = string;
export type Note = string | null;
export type OrganizationId21 = string;
export type PropertyId9 = string;
export type SchemaVersion38 = "0.2.0";
export type Synthetic38 = boolean;
export type BusinessPartyId1 = string | null;
export type HouseholdId3 = string | null;
export type Id41 = string;
export type OrganizationId22 = string;
export type SchemaVersion39 = "0.2.0";
export type SpaceId1 = string;
export type Synthetic39 = boolean;
export type Id42 = string;
export type LegalEntityId = string;
export type Note1 = string | null;
export type OrganizationId23 = string;
export type PropertyId10 = string;
export type SchemaVersion40 = "0.2.0";
export type Synthetic40 = boolean;
export type Cursor = string | null;
export type Limit = number;
export type AppliedAuthorization = "same_predicate_as_list";
export type NextCursor = string | null;
export type TotalCount = number | null;
export type Id43 = string;
export type Label3 = string;
export type OrganizationId24 = string;
export type SchemaVersion41 = "0.2.0";
export type Synthetic41 = boolean;
export type GroupId = string;
export type Id44 = string;
export type OrganizationId25 = string;
export type PropertyId11 = string;
export type SchemaVersion42 = "0.2.0";
export type Synthetic42 = boolean;
export type AbuseControl = "rate_limit_and_fingerprint_required";
export type CorrelationId5 = string;
export type InquiryId = string;
export type Message1 = string;
export type RetrySemantics = "identical_key_and_fingerprint_replays_ack";
export type Status10 = "received";
export type Synthetic43 = true;
export type Availability = "offerable";
export type AvailableDate1 = string | null;
export type Label4 = string;
export type ListingId = string;
export type Municipality2 = string;
export type PropertyName = string;
export type Publication = "published";
export type SpaceId2 = string;
export type State5 = string;
export type Synthetic44 = true;
export type Use2 = "residential" | "commercial";
export type Action2 = string;
export type ActorId4 = string | null;
export type CorrelationId6 = string;
export type DelegatedAuthorityId1 = string | null;
export type EventHash1 = string;
export type Id45 = string;
export type OccurredAt2 = string;
export type PreviousEventHash1 = string | null;
export type Redacted = true;
export type ResourceId2 = string;
export type ResourceType2 = string;
export type Result2 = "allowed" | "denied" | "failed" | "replayed";
export type SchemaVersion43 = "0.2.0";
export type Synthetic45 = boolean;
export type AggregateId3 = string;
export type AggregateVersion2 = number;
export type CausationId1 = string | null;
export type CorrelationId7 = string;
export type EventType1 =
  | "listing.published.v1"
  | "listing.withdrawn.v1"
  | "inquiry.submitted.v1"
  | "inquiry.triaged.v1"
  | "activity.recorded.v1"
  | "property.space_states_projected.v1";
export type Id46 = string;
export type OccurredAt3 = string;
export type OrganizationId26 = string;
export type PayloadRecordIds2 = string[];
export type SchemaVersion44 = "0.2.0";
export type Synthetic46 = boolean;
export type Id47 = string;
export type SchemaVersion45 = "0.2.0";
export type Synthetic47 = boolean;
export type Groups = PortfolioGroup[];
export type KnownAccountIds = string[];
export type KnownEntityIds = string[];
export type KnownHouseholdIds = string[];
export type KnownOrganizationIds = string[];
export type KnownPersonIds = string[];
export type KnownPropertyIds = string[];
export type KnownSpaceIds = string[];
export type Management = ManagementRelationship1[];
export type Memberships = PortfolioMembership[];
export type Occupancies = OccupancyRelationship[];
export type Ownership = OwnershipRelationship[];
export type PortalAccess = HouseholdPortalAccess[];
export type PublishedListings = PublishedListingRead[];
export type SchemaVersion46 = "0.2.0";
export type Availability1 = "offerable" | "withheld" | "unknown";
export type AvailabilitySource = "derived" | "ambiguous" | "explicit";
export type Condition = "rent_ready" | "renovation" | "damaged" | "unknown";
export type ConditionSource = "derived" | "ambiguous" | "explicit";
export type Id48 = string;
export type LegalRestriction = "none" | "hold" | "litigation" | "unknown";
export type LegalRestrictionSource = "derived" | "ambiguous" | "explicit";
export type MaintenanceRestriction = "none" | "limited_access" | "unsafe" | "unknown";
export type MaintenanceRestrictionSource = "derived" | "ambiguous" | "explicit";
export type MappingNotes = string[];
export type Occupancy = "vacant" | "occupied" | "notice" | "unknown";
export type OccupancySource = "derived" | "ambiguous" | "explicit";
export type OrganizationId27 = string;
export type Publication1 = "unpublished" | "published" | "withdrawn";
export type PublicationSource = "derived" | "ambiguous" | "explicit";
export type SchemaVersion47 = "0.2.0";
export type SpaceId3 = string;
export type Synthetic48 = boolean;
export type SpaceStates = SpaceOperatingState[];
export type Field = string | null;
export type Reason5 = string;
export type Code = string;
export type CorrelationId8 = string;
export type Details = SafeErrorDetail[];
export type Message2 = string;
export type PermissionSafe = true;
export type RequiredAction = string | null;
export type Retryable = boolean;
export type Availability2 = "offerable" | "withheld" | "unknown";
export type SpaceId4 = string;
export type Publication2 = "unpublished" | "published" | "withdrawn";
export type SpaceId5 = string;
export type AssignedStaffId = string | null;
export type Email = string;
export type Id49 = string;
export type Intent = "showing" | "application" | "contact" | "other";
export type ListingId1 = string;
export type Message3 = string;
export type Name8 = string;
export type OrganizationId28 = string;
export type PreferredDate = string | null;
export type ReceivedAt1 = string;
export type SchemaVersion48 = "0.2.0";
export type SpaceId6 = string;
export type Status11 = "new" | "assigned" | "waiting" | "closed_duplicate" | "closed_not_pursuing";
export type Synthetic49 = boolean;
export type Version6 = number;
export type Email1 = string;
export type Intent1 = "showing" | "application" | "contact" | "other";
export type ListingId2 = string;
export type Message4 = string;
export type Name9 = string;
export type PreferredDate1 = string | null;
export type DueOn = string | null;
export type Engine1 = "read_only_example";
export type Id50 = string;
export type NextAction = string;
export type OrganizationId29 = string;
export type OwnerId = string | null;
export type SchemaVersion49 = "0.2.0";
export type Status12 = "open" | "waiting" | "done";
export type Synthetic50 = boolean;
export type Title1 = string;
export type Decision1 = "new" | "assigned" | "waiting" | "closed_duplicate" | "closed_not_pursuing";
export type InquiryId1 = string;
export type Note2 = string;
export type ActorId5 = string;
export type DelegatedAuthorityId2 = string | null;
export type FeatureFlags = string[];
export type MembershipIds = string[];
export type OrganizationId30 = string;
export type Label5 = string | null;
export type SpaceId7 = string;
export type SquareFeet2 = number | null;
export type Name10 = string | null;
export type ParcelReferences2 = string[] | null;
export type PropertyId12 = string;

export interface FoundationContracts {
  Contract?: Contract;
  Money?: Money;
  Period?: Period;
  Record?: Record;
  Scope?: Scope;
  Address?: Address;
  Asset?: Asset;
  Building?: Building;
  CommercialTerms?: CommercialTerms;
  Location?: Location;
  Organization?: Organization;
  OwnershipEntity?: OwnershipEntity;
  Portfolio?: Portfolio;
  Property?: Property;
  ResidentialTerms?: ResidentialTerms;
  SharedSpace?: SharedSpace;
  Unit?: Unit;
  BusinessParty?: BusinessParty;
  Household?: Household;
  PeopleGraph?: PeopleGraph;
  Person?: Person;
  PersonRelationship?: PersonRelationship;
  UserAccount?: UserAccount;
  PermissionContext?: PermissionContext;
  PermissionMatrix?: PermissionMatrix;
  PermissionResult?: PermissionResult;
  PermissionRule?: PermissionRule;
  RoleAssignment?: RoleAssignment;
  ApprovalDecision?: ApprovalDecision;
  ApprovalRequest?: ApprovalRequest;
  Delegation?: Delegation;
  DelegationPolicy?: DelegationPolicy;
  DelegationResult?: DelegationResult;
  AdapterCommand?: AdapterCommand;
  AdapterResult?: AdapterResult;
  ExternalReference?: ExternalReference;
  IntegrationRecord?: IntegrationRecord;
  Allocation?: Allocation;
  ApplicantConsent?: ApplicantConsent;
  AutopayConsent?: AutopayConsent;
  Charge?: Charge;
  IdentityLifecycleContract?: IdentityLifecycleContract;
  PaymentException?: PaymentException;
  PaymentMethodReference?: PaymentMethodReference;
  PaymentRecord?: PaymentRecord;
  ScreeningRecord?: ScreeningRecord;
  SessionContract?: SessionContract;
  AuditEvent?: AuditEvent;
  DocumentRecord?: DocumentRecord;
  DomainEvent?: DomainEvent;
  InboxRecord?: InboxRecord;
  JurisdictionPolicy?: JurisdictionPolicy;
  OutboxRecord?: OutboxRecord;
  ProviderEvent?: ProviderEvent;
  RetentionPolicy?: RetentionPolicy;
  ImportBatch?: ImportBatch;
  MigrationReport?: MigrationReport;
  Reconciliation?: Reconciliation;
  StagingRecord?: StagingRecord;
  ActivityHistoryRead?: ActivityHistoryRead;
  ApprovalExampleRead?: ApprovalExampleRead;
  CommandResult?: CommandResult;
  CreateBuilding?: CreateBuilding;
  CreateLeasableSpace?: CreateLeasableSpace;
  CreateProperty?: CreateProperty;
  DeliveryAttempt?: DeliveryAttempt;
  ExpectedVersion?: ExpectedVersion1;
  FakeProviderCommand?: FakeProviderCommand;
  FakeProviderResult?: FakeProviderResult;
  HouseholdPortalAccess?: HouseholdPortalAccess;
  InclusiveExclusiveDateRange?: InclusiveExclusiveDateRange;
  InclusiveExclusiveDateTimeRange?: InclusiveExclusiveDateTimeRange;
  ManagementRelationship?: ManagementRelationship1;
  OccupancyRelationship?: OccupancyRelationship;
  OwnershipRelationship?: OwnershipRelationship;
  PageQuery?: PageQuery;
  PageResult?: PageResult;
  PortfolioGroup?: PortfolioGroup;
  PortfolioMembership?: PortfolioMembership;
  PublicInquiryAcknowledgement?: PublicInquiryAcknowledgement;
  PublishedListingRead?: PublishedListingRead;
  ReferenceAuditEntry?: ReferenceAuditEntry;
  ReferenceDomainEvent?: ReferenceDomainEvent;
  ReferenceRecord?: ReferenceRecord;
  ReferenceSlice?: ReferenceSlice;
  SafeErrorDetail?: SafeErrorDetail;
  SafeErrorEnvelope?: SafeErrorEnvelope;
  SetSpaceAvailability?: SetSpaceAvailability;
  SetSpacePublication?: SetSpacePublication;
  SpaceOperatingState?: SpaceOperatingState;
  StaffInquiryRead?: StaffInquiryRead;
  SubmitPublicInquiry?: SubmitPublicInquiry;
  TaskExampleRead?: TaskExampleRead;
  TriageInquiry?: TriageInquiry;
  TrustedActorContext?: TrustedActorContext;
  UntrustedRequestInput?: UntrustedRequestInput;
  UpdateLeasableSpace?: UpdateLeasableSpace;
  UpdateProperty?: UpdateProperty;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Contract".
 */
export interface Contract {}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Money".
 */
export interface Money {
  amount_minor: AmountMinor;
  currency: Currency;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Period".
 */
export interface Period {
  effective_at: EffectiveAt;
  expires_at?: ExpiresAt;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Record".
 */
export interface Record {
  id: Id;
  schema_version?: SchemaVersion;
  synthetic?: Synthetic;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Scope".
 */
export interface Scope {
  assignment_id?: AssignmentId;
  building_id?: BuildingId;
  household_id?: HouseholdId;
  organization_id: OrganizationId;
  ownership_entity_id?: OwnershipEntityId;
  property_id?: PropertyId;
  space_id?: SpaceId;
  unit_id?: UnitId;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Address".
 */
export interface Address {
  country: Country;
  county: County;
  is_example: IsExample;
  line1: Line1;
  municipality: Municipality;
  postal_code: PostalCode;
  state: State;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Asset".
 */
export interface Asset {
  building_id?: BuildingId1;
  id: Id1;
  kind: Kind;
  name: Name;
  organization_id: OrganizationId1;
  property_id: PropertyId1;
  schema_version?: SchemaVersion1;
  shared_space_id?: SharedSpaceId;
  synthetic?: Synthetic1;
  unit_id?: UnitId1;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Building".
 */
export interface Building {
  allowed_uses: AllowedUses;
  id: Id2;
  name: Name1;
  organization_id: OrganizationId2;
  property_id: PropertyId2;
  schema_version?: SchemaVersion2;
  synthetic?: Synthetic2;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "CommercialTerms".
 */
export interface CommercialTerms {
  base_rent: Money;
  build_out_status: BuildOutStatus;
  cam_nnn_terms: CamNnnTerms;
  deposit: Money;
  intended_use: IntendedUse;
  lease_type: LeaseType;
  loading_access: LoadingAccess;
  parking: Parking;
  rent_period: RentPeriod;
  utility_responsibility: UtilityResponsibility;
  zoning_notes: ZoningNotes;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Location".
 */
export interface Location {
  building_id?: BuildingId2;
  id: Id3;
  name: Name2;
  organization_id: OrganizationId3;
  property_id: PropertyId3;
  schema_version?: SchemaVersion3;
  synthetic?: Synthetic3;
  unit_id?: UnitId2;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Organization".
 */
export interface Organization {
  id: Id4;
  name: Name3;
  schema_version?: SchemaVersion4;
  synthetic?: Synthetic4;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "OwnershipEntity".
 */
export interface OwnershipEntity {
  entity_type: EntityType;
  id: Id5;
  legal_name: LegalName;
  management_relationship: ManagementRelationship;
  organization_id: OrganizationId4;
  schema_version?: SchemaVersion5;
  synthetic?: Synthetic5;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Portfolio".
 */
export interface Portfolio {
  assets: Assets;
  buildings: Buildings;
  organizations: Organizations;
  ownership_entities: OwnershipEntities;
  properties: Properties;
  shared_spaces: SharedSpaces;
  units: Units;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Property".
 */
export interface Property {
  address: Address;
  id: Id6;
  name: Name4;
  organization_id: OrganizationId5;
  ownership_entity_id: OwnershipEntityId1;
  parcel_references?: ParcelReferences;
  property_type: PropertyType;
  schema_version?: SchemaVersion6;
  synthetic?: Synthetic6;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "SharedSpace".
 */
export interface SharedSpace {
  building_id?: BuildingId3;
  id: Id7;
  kind: Kind1;
  name: Name5;
  organization_id: OrganizationId6;
  property_id: PropertyId4;
  schema_version?: SchemaVersion7;
  synthetic?: Synthetic7;
  unit_id?: UnitId3;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Unit".
 */
export interface Unit {
  available_date?: AvailableDate;
  building_id: BuildingId4;
  commercial?: CommercialTerms | null;
  id: Id8;
  image_key: ImageKey;
  label: Label;
  organization_id: OrganizationId7;
  property_id: PropertyId5;
  residential?: ResidentialTerms | null;
  schema_version?: SchemaVersion8;
  square_feet: SquareFeet;
  status: Status;
  synthetic?: Synthetic8;
  use: Use;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ResidentialTerms".
 */
export interface ResidentialTerms {
  application_fee: Money;
  bathrooms: Bathrooms;
  bedrooms: Bedrooms;
  monthly_rent: Money;
  pet_policy: PetPolicy;
  security_deposit: Money;
  utilities: Utilities;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "BusinessParty".
 */
export interface BusinessParty {
  id: Id9;
  kind: Kind2;
  legal_name: LegalName1;
  organization_id: OrganizationId8;
  schema_version?: SchemaVersion9;
  synthetic?: Synthetic9;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Household".
 */
export interface Household {
  id: Id10;
  label: Label1;
  organization_id: OrganizationId9;
  schema_version?: SchemaVersion10;
  status: Status1;
  synthetic?: Synthetic10;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PeopleGraph".
 */
export interface PeopleGraph {
  accounts: Accounts;
  businesses: Businesses;
  households: Households;
  organization_ids: OrganizationIds;
  people: People;
  relationships: Relationships;
  unit_organizations?: UnitOrganizations;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "UserAccount".
 */
export interface UserAccount {
  id: Id11;
  identity_provider_reference?: IdentityProviderReference;
  person_id: PersonId;
  schema_version?: SchemaVersion11;
  status: Status2;
  synthetic?: Synthetic11;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Person".
 */
export interface Person {
  age_class: AgeClass;
  display_name: DisplayName;
  id: Id12;
  identity_status: IdentityStatus;
  schema_version?: SchemaVersion12;
  synthetic?: Synthetic12;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PersonRelationship".
 */
export interface PersonRelationship {
  account_id?: AccountId;
  attributable_access_required?: AttributableAccessRequired;
  business_party_id?: BusinessPartyId;
  effective_at: EffectiveAt1;
  ended_at?: EndedAt;
  household_id?: HouseholdId1;
  id: Id13;
  kind: Kind3;
  organization_id: OrganizationId10;
  person_id: PersonId1;
  schema_version?: SchemaVersion13;
  synthetic?: Synthetic13;
  unit_id?: UnitId4;
}
export interface UnitOrganizations {
  [k: string]: string;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PermissionContext".
 */
export interface PermissionContext {
  active: Active;
  actor_organization_id: ActorOrganizationId;
  approval_present?: ApprovalPresent;
  assignment_ids?: AssignmentIds;
  authorized_scopes?: AuthorizedScopes;
  delegated?: Delegated;
  organization_wide?: OrganizationWide;
  reason?: Reason;
  record_scope: Scope;
  related_household_ids?: RelatedHouseholdIds;
  related_record?: RelatedRecord;
  role: Role;
  sensitivity: Sensitivity;
}
export interface AuthorizedScopes {
  [k: string]: string[];
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PermissionMatrix".
 */
export interface PermissionMatrix {
  actions: Actions;
  allow_rules: AllowRules;
  default_effect?: DefaultEffect;
  future_roles: FutureRoles;
  resources: Resources;
  roles: Roles;
  runtime_enforcement?: RuntimeEnforcement;
  version?: Version;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PermissionRule".
 */
export interface PermissionRule {
  action: Action;
  approval_required?: ApprovalRequired;
  assignment_scope?: AssignmentScope;
  audit_required?: AuditRequired;
  building_scope?: BuildingScope;
  delegation_eligible?: DelegationEligible;
  household_scope?: HouseholdScope;
  organization_scope?: OrganizationScope;
  ownership_entity_scope?: OwnershipEntityScope;
  property_scope?: PropertyScope;
  reason_required?: ReasonRequired;
  record_relationship_required?: RecordRelationshipRequired;
  record_sensitivity: RecordSensitivity;
  resource: Resource;
  role: Role;
  unit_scope?: UnitScope;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PermissionResult".
 */
export interface PermissionResult {
  allowed_in_simulation: AllowedInSimulation;
  audit_required?: AuditRequired1;
  production_authorized?: ProductionAuthorized;
  reason: Reason1;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "RoleAssignment".
 */
export interface RoleAssignment {
  effective_at: EffectiveAt2;
  expires_at: ExpiresAt1;
  person_id: PersonId2;
  role: Role1;
  scope: Scope;
  status: Status3;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ApprovalDecision".
 */
export interface ApprovalDecision {
  actor_id: ActorId;
  decided_at: DecidedAt;
  decision: Decision;
  expected_version: ExpectedVersion;
  policy_version: PolicyVersion;
  reason: Reason2;
  request_fingerprint: RequestFingerprint;
  request_id: RequestId;
  request_revision: RequestRevision;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ApprovalRequest".
 */
export interface ApprovalRequest {
  approved_budget_remaining: Money | null;
  assigned_approver_id: AssignedApproverId;
  cumulative_issue_amount: Money;
  decision_type: DecisionType;
  emergency: Emergency;
  expense_category: ExpenseCategory;
  id: Id14;
  legal_compliance_sensitive: LegalComplianceSensitive;
  monthly_rent: Money | null;
  prior_approval_ids: PriorApprovalIds;
  requested_amount: Money;
  requesting_employee_id: RequestingEmployeeId;
  revision: Revision;
  scope: Scope;
  supporting_evidence: SupportingEvidence;
  vendor_id: VendorId;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Delegation".
 */
export interface Delegation {
  approver_id: ApproverId;
  decision_types: DecisionTypes;
  delegate_id: DelegateId;
  effective_at: EffectiveAt3;
  expense_categories: ExpenseCategories;
  expires_at: ExpiresAt2;
  id: Id15;
  maximum_value: Money;
  policy_version: PolicyVersion1;
  scope: Scope;
  temporary: Temporary;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "DelegationPolicy".
 */
export interface DelegationPolicy {
  effective_at: EffectiveAt4;
  expires_at: ExpiresAt3;
  owner_reserved: OwnerReserved;
  parts_limit: Money;
  repair_rent_multiplier: RepairRentMultiplier;
  staff_limit: Money;
  status?: Status4;
  version: Version1;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "DelegationResult".
 */
export interface DelegationResult {
  executed?: Executed;
  notification_required?: NotificationRequired;
  reasons: Reasons;
  result: Result;
  retrospective_review_required?: RetrospectiveReviewRequired;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "AdapterCommand".
 */
export interface AdapterCommand {
  actor_id: ActorId1;
  canonical_record_id: CanonicalRecordId;
  correlation_id: CorrelationId;
  idempotency_key: IdempotencyKey;
  operation: Operation;
  organization_id: OrganizationId11;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "AdapterResult".
 */
export interface AdapterResult {
  accepted: Accepted;
  error_code: ErrorCode;
  side_effects?: SideEffects;
  status: Status5;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ExternalReference".
 */
export interface ExternalReference {
  canonical_id: CanonicalId;
  canonical_resource: CanonicalResource;
  environment: Environment;
  id: Id16;
  integration_id: IntegrationId;
  organization_id: OrganizationId12;
  provider_object_id: ProviderObjectId;
  provider_object_type: ProviderObjectType;
  schema_version?: SchemaVersion14;
  synthetic?: Synthetic14;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "IntegrationRecord".
 */
export interface IntegrationRecord {
  activation_checklist: ActivationChecklist;
  configuration_status: ConfigurationStatus;
  connection_status: ConnectionStatus;
  credential_reference: CredentialReference;
  data_ownership: DataOwnership;
  deactivation_procedure: DeactivationProcedure;
  environment: Environment1;
  id: Id17;
  last_failure: LastFailure;
  last_successful_sync: LastSuccessfulSync;
  mapping_record_ids: MappingRecordIds;
  organization_id: OrganizationId13;
  provider_name: ProviderName;
  provider_type: ProviderType;
  replacement_procedure: ReplacementProcedure;
  required_webhooks: RequiredWebhooks;
  retry_exception_state: RetryExceptionState;
  schema_version?: SchemaVersion15;
  supported_capabilities: SupportedCapabilities;
  synthetic?: Synthetic15;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Allocation".
 */
export interface Allocation {
  amount: Money;
  charge_id: ChargeId;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ApplicantConsent".
 */
export interface ApplicantConsent {
  disclosure_version: DisclosureVersion;
  evidence_document_id: EvidenceDocumentId;
  id: Id18;
  person_id: PersonId3;
  purpose: Purpose;
  recorded_at: RecordedAt;
  schema_version?: SchemaVersion16;
  synthetic?: Synthetic16;
  withdrawn_at: WithdrawnAt;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "AutopayConsent".
 */
export interface AutopayConsent {
  amount_limit: Money;
  effective_at: EffectiveAt5;
  evidence_document_id: EvidenceDocumentId1;
  frequency: Frequency;
  id: Id19;
  payment_method_reference_id: PaymentMethodReferenceId;
  person_id: PersonId4;
  revoked_at: RevokedAt;
  schema_version?: SchemaVersion17;
  synthetic?: Synthetic17;
  terms_version: TermsVersion;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Charge".
 */
export interface Charge {
  amount: Money;
  description: Description;
  due_at: DueAt;
  id: Id20;
  ledger_reference_id: LedgerReferenceId;
  schema_version?: SchemaVersion18;
  scope: Scope;
  synthetic?: Synthetic18;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "IdentityLifecycleContract".
 */
export interface IdentityLifecycleContract {
  approval_status: ApprovalStatus;
  implemented?: Implemented;
  operation: Operation1;
  preconditions: Preconditions;
  required_evidence: RequiredEvidence;
  resulting_events: ResultingEvents;
  revocation_behavior: RevocationBehavior;
  ttl_seconds: TtlSeconds;
  version: Version2;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PaymentException".
 */
export interface PaymentException {
  amount: Money | null;
  id: Id21;
  kind: Kind4;
  payment_id: PaymentId;
  provider_event_id: ProviderEventId;
  reason: Reason3;
  reviewer_id: ReviewerId;
  schema_version?: SchemaVersion19;
  status: Status6;
  synthetic?: Synthetic19;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PaymentMethodReference".
 */
export interface PaymentMethodReference {
  id: Id22;
  kind: Kind5;
  person_id: PersonId5;
  provider_token_reference_id: ProviderTokenReferenceId;
  schema_version?: SchemaVersion20;
  synthetic?: Synthetic20;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PaymentRecord".
 */
export interface PaymentRecord {
  ach_return_code: AchReturnCode;
  allocations: Allocations;
  attempt_number: AttemptNumber;
  autopay_consent_id: AutopayConsentId;
  browser_success_is_posting?: BrowserSuccessIsPosting;
  charge_ids: ChargeIds;
  dispute_record_ids: DisputeRecordIds;
  failure_code: FailureCode;
  id: Id23;
  idempotency_key: IdempotencyKey1;
  ledger_posting_status: LedgerPostingStatus;
  method_reference_id: MethodReferenceId;
  processor_status: ProcessorStatus;
  provider_event_ids: ProviderEventIds;
  receipt_document_id: ReceiptDocumentId;
  reconciliation_exception_id: ReconciliationExceptionId;
  refund_record_ids: RefundRecordIds;
  schema_version?: SchemaVersion21;
  scope: Scope;
  settled_at: SettledAt;
  settlement_status: SettlementStatus;
  synthetic?: Synthetic21;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ScreeningRecord".
 */
export interface ScreeningRecord {
  adverse_action_case_id: AdverseActionCaseId;
  applicant_person_id: ApplicantPersonId;
  autonomous_decision?: AutonomousDecision;
  consent_record_id: ConsentRecordId;
  criteria_version: CriteriaVersion;
  disclosure_version: DisclosureVersion1;
  dispute_case_id: DisputeCaseId;
  failure_code: FailureCode1;
  farouk_final_decision_id: FaroukFinalDecisionId;
  human_reviewer_id: HumanReviewerId;
  id: Id24;
  minimal_normalized_result: MinimalNormalizedResult;
  order_id: OrderId;
  permissible_purpose: PermissiblePurpose;
  provider_callback_event_id: ProviderCallbackEventId;
  provider_reference_id: ProviderReferenceId;
  recommendation_record_id: RecommendationRecordId;
  restricted_access_policy_version: RestrictedAccessPolicyVersion;
  restricted_report_document_id: RestrictedReportDocumentId;
  retention_policy_version: RetentionPolicyVersion;
  retry_state: RetryState;
  schema_version?: SchemaVersion22;
  scope: Scope;
  status: Status7;
  synthetic?: Synthetic22;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "SessionContract".
 */
export interface SessionContract {
  account_id: AccountId1;
  assurance: Assurance;
  authenticated_at: AuthenticatedAt;
  device_label: DeviceLabel;
  expires_at: ExpiresAt4;
  id: Id25;
  initiating_actor_id: InitiatingActorId;
  person_id: PersonId6;
  purpose: Purpose1;
  revoked_at: RevokedAt1;
  schema_version?: SchemaVersion23;
  source_ip_hash: SourceIpHash;
  support_reason: SupportReason;
  synthetic?: Synthetic23;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "AuditEvent".
 */
export interface AuditEvent {
  action: Action1;
  actor_id: ActorId2;
  correlation_id: CorrelationId1;
  delegated_authority_id: DelegatedAuthorityId;
  effective_role: EffectiveRole;
  event_hash: EventHash;
  id: Id26;
  ip_device_metadata: IpDeviceMetadata;
  material_after: MaterialAfter;
  material_before: MaterialBefore;
  previous_event_hash: PreviousEventHash;
  reason: Reason4;
  related_approval_id: RelatedApprovalId;
  related_provider_event_id: RelatedProviderEventId;
  resource_id: ResourceId;
  resource_type: ResourceType;
  result: Result1;
  schema_version?: SchemaVersion24;
  scope: Scope;
  source_channel: SourceChannel;
  synthetic?: Synthetic24;
  timestamp: Timestamp;
}
export interface IpDeviceMetadata {
  [k: string]: string;
}
export interface MaterialAfter {
  [k: string]: string | number | boolean | null;
}
export interface MaterialBefore {
  [k: string]: string | number | boolean | null;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "DocumentRecord".
 */
export interface DocumentRecord {
  access_rule: AccessRule;
  audit_required: AuditRequired2;
  checksum_sha256: ChecksumSha256;
  deletion_eligible: DeletionEligible;
  document_class: DocumentClass;
  download_rule: DownloadRule;
  effective_at: EffectiveAt6;
  expires_at: ExpiresAt5;
  id: Id27;
  legal_hold: LegalHold;
  owner_organization_id: OwnerOrganizationId;
  owner_person_id: OwnerPersonId;
  related_record_ids: RelatedRecordIds;
  retention_rule_id: RetentionRuleId;
  schema_version?: SchemaVersion25;
  scope: Scope;
  sensitivity: Sensitivity1;
  source: Source;
  storage_reference_id: StorageReferenceId;
  synthetic?: Synthetic25;
  version: Version3;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "DomainEvent".
 */
export interface DomainEvent {
  aggregate_id: AggregateId;
  aggregate_version: AggregateVersion;
  causation_id: CausationId;
  correlation_id: CorrelationId2;
  domain: Domain;
  event_type: EventType;
  id: Id28;
  occurred_at: OccurredAt;
  organization_id: OrganizationId14;
  payload_record_ids: PayloadRecordIds;
  schema_version?: SchemaVersion26;
  synthetic?: Synthetic26;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "InboxRecord".
 */
export interface InboxRecord {
  deduplication_key: DeduplicationKey;
  failure_code: FailureCode2;
  id: Id29;
  processed_at: ProcessedAt;
  provider_event: ProviderEvent;
  schema_version?: SchemaVersion28;
  state: State1;
  synthetic?: Synthetic28;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ProviderEvent".
 */
export interface ProviderEvent {
  canonical_event_id: CanonicalEventId;
  id: Id30;
  integration_id: IntegrationId1;
  organization_id: OrganizationId15;
  payload_checksum: PayloadChecksum;
  provider_event_id: ProviderEventId1;
  received_at: ReceivedAt;
  schema_version?: SchemaVersion27;
  signature_verified: SignatureVerified;
  synthetic?: Synthetic27;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "JurisdictionPolicy".
 */
export interface JurisdictionPolicy {
  approved_rule_document_id: ApprovedRuleDocumentId;
  conflict_resolution: ConflictResolution;
  country: Country1;
  county: County1;
  effective_at: EffectiveAt7;
  expires_at: ExpiresAt6;
  id: Id31;
  lease_type: LeaseType1;
  municipality: Municipality1;
  policy_area: PolicyArea;
  property_id: PropertyId6;
  schema_version?: SchemaVersion29;
  state: State2;
  synthetic?: Synthetic29;
  unit_type: UnitType;
  version: Version4;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "OutboxRecord".
 */
export interface OutboxRecord {
  attempts: Attempts;
  claim_expires_at: ClaimExpiresAt;
  event: DomainEvent;
  id: Id32;
  idempotency_key: IdempotencyKey2;
  last_error: LastError;
  next_attempt_at: NextAttemptAt;
  schema_version?: SchemaVersion30;
  state: State3;
  synthetic?: Synthetic30;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "RetentionPolicy".
 */
export interface RetentionPolicy {
  deletion_without_review?: DeletionWithoutReview;
  document_class: DocumentClass1;
  id: Id33;
  jurisdiction_policy_id: JurisdictionPolicyId;
  legal_hold_overrides_deletion?: LegalHoldOverridesDeletion;
  legal_review_status: LegalReviewStatus;
  retention_days: RetentionDays;
  schema_version?: SchemaVersion31;
  synthetic?: Synthetic31;
  trigger_event: TriggerEvent;
  version: Version5;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ImportBatch".
 */
export interface ImportBatch {
  approval_id: ApprovalId;
  id: Id34;
  immutable_report_checksum: ImmutableReportChecksum;
  mapping_version: MappingVersion;
  organization_id: OrganizationId16;
  rollback_batch_id: RollbackBatchId;
  schema_version?: SchemaVersion32;
  source_checksum: SourceChecksum;
  source_file: SourceFile;
  source_system: SourceSystem;
  status: Status8;
  synthetic?: Synthetic32;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "MigrationReport".
 */
export interface MigrationReport {
  control_totals: Reconciliation;
  mapping_version?: MappingVersion1;
  report_checksum: ReportChecksum;
  rollback_strategy?: RollbackStrategy;
  rows: Rows;
  writes_performed?: WritesPerformed;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "Reconciliation".
 */
export interface Reconciliation {
  conflict_rows: ConflictRows;
  document_count_difference: DocumentCountDifference;
  document_reconciliation: DocumentReconciliation;
  duplicate_rows: DuplicateRows;
  expected_rows: ExpectedRows;
  financial_difference_minor: FinancialDifferenceMinor;
  financial_reconciliation: FinancialReconciliation;
  observed_rows: ObservedRows;
  rejected_rows: RejectedRows;
  source_document_count: SourceDocumentCount;
  source_financial_total_minor: SourceFinancialTotalMinor;
  staged_document_count: StagedDocumentCount;
  staged_valid_total_minor: StagedValidTotalMinor;
  valid_rows: ValidRows;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "StagingRecord".
 */
export interface StagingRecord {
  approval_id: ApprovalId1;
  conflict: Conflict;
  correction: Correction;
  duplicate_candidate: DuplicateCandidate;
  imported_canonical_record_id: ImportedCanonicalRecordId;
  issues: Issues;
  mapped_fields: MappedFields;
  rejected: Rejected;
  row_number: RowNumber;
  source_file: SourceFile1;
  source_record_identifier: SourceRecordIdentifier;
  source_system: SourceSystem1;
  validation_result: ValidationResult;
}
export interface MappedFields {
  [k: string]: string;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ActivityHistoryRead".
 */
export interface ActivityHistoryRead {
  actor_id?: ActorId3;
  id: Id35;
  occurred_at: OccurredAt1;
  organization_id: OrganizationId17;
  resource_id: ResourceId1;
  resource_type: ResourceType1;
  schema_version?: SchemaVersion33;
  summary: Summary;
  synthetic?: Synthetic33;
  visibility: Visibility;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ApprovalExampleRead".
 */
export interface ApprovalExampleRead {
  amount?: Money | null;
  engine?: Engine;
  id: Id36;
  organization_id: OrganizationId18;
  schema_version?: SchemaVersion34;
  state: State4;
  synthetic?: Synthetic34;
  title: Title;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "CommandResult".
 */
export interface CommandResult {
  accepted: Accepted1;
  aggregate_id?: AggregateId1;
  aggregate_version?: AggregateVersion1;
  correlation_id: CorrelationId3;
  id: Id37;
  message: Message;
  replayed?: Replayed;
  result_code: ResultCode;
  schema_version?: SchemaVersion35;
  synthetic?: Synthetic35;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "CreateBuilding".
 */
export interface CreateBuilding {
  allowed_uses: AllowedUses1;
  expected_version?: ExpectedVersion1 | null;
  name: Name6;
  property_id: PropertyId7;
  request: UntrustedRequestInput;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ExpectedVersion".
 */
export interface ExpectedVersion1 {
  aggregate_id: AggregateId2;
  expected_version: ExpectedVersion2;
}
/**
 * External request metadata. Never treated as authenticated actor context.
 *
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "UntrustedRequestInput".
 */
export interface UntrustedRequestInput {
  client_observed_at?: ClientObservedAt;
  correlation_id: CorrelationId4;
  idempotency_key: IdempotencyKey3;
  request_fingerprint: RequestFingerprint1;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "CreateLeasableSpace".
 */
export interface CreateLeasableSpace {
  building_id: BuildingId5;
  commercial?: CommercialTerms | null;
  expected_version?: ExpectedVersion1 | null;
  label: Label2;
  property_id: PropertyId8;
  request: UntrustedRequestInput;
  residential?: ResidentialTerms | null;
  square_feet: SquareFeet1;
  use: Use1;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "CreateProperty".
 */
export interface CreateProperty {
  address: Address;
  expected_version?: ExpectedVersion1 | null;
  name: Name7;
  parcel_references?: ParcelReferences1;
  property_type: PropertyType1;
  request: UntrustedRequestInput;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "DeliveryAttempt".
 */
export interface DeliveryAttempt {
  attempt_number: AttemptNumber1;
  finished_at?: FinishedAt;
  id: Id38;
  outbox_id: OutboxId;
  outcome: Outcome;
  repeats_business_decision?: RepeatsBusinessDecision;
  schema_version?: SchemaVersion36;
  started_at: StartedAt;
  synthetic?: Synthetic36;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "FakeProviderCommand".
 */
export interface FakeProviderCommand {
  idempotency_key: IdempotencyKey4;
  operation: Operation2;
  organization_id: OrganizationId19;
  payload_record_ids?: PayloadRecordIds1;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "FakeProviderResult".
 */
export interface FakeProviderResult {
  accepted: Accepted2;
  live_network?: LiveNetwork;
  provider_event_id?: ProviderEventId2;
  status: Status9;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "HouseholdPortalAccess".
 */
export interface HouseholdPortalAccess {
  account_id: AccountId2;
  authorization_reason: AuthorizationReason;
  household_id: HouseholdId2;
  id: Id39;
  interval: InclusiveExclusiveDateTimeRange;
  kind: Kind6;
  organization_id: OrganizationId20;
  person_id: PersonId7;
  schema_version?: SchemaVersion37;
  synthetic?: Synthetic37;
}
/**
 * effective_at is inclusive. ended_at is exclusive. Open-ended when ended_at is null.
 *
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "InclusiveExclusiveDateTimeRange".
 */
export interface InclusiveExclusiveDateTimeRange {
  effective_at: EffectiveAt8;
  ended_at?: EndedAt1;
}
/**
 * effective_on is inclusive. ended_on is exclusive. Open-ended when ended_on is null.
 *
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "InclusiveExclusiveDateRange".
 */
export interface InclusiveExclusiveDateRange {
  effective_on: EffectiveOn;
  ended_on?: EndedOn;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ManagementRelationship".
 */
export interface ManagementRelationship1 {
  id: Id40;
  interval: InclusiveExclusiveDateRange;
  manager_organization_id: ManagerOrganizationId;
  note?: Note;
  organization_id: OrganizationId21;
  property_id: PropertyId9;
  schema_version?: SchemaVersion38;
  synthetic?: Synthetic38;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "OccupancyRelationship".
 */
export interface OccupancyRelationship {
  business_party_id?: BusinessPartyId1;
  household_id?: HouseholdId3;
  id: Id41;
  interval: InclusiveExclusiveDateTimeRange;
  organization_id: OrganizationId22;
  schema_version?: SchemaVersion39;
  space_id: SpaceId1;
  synthetic?: Synthetic39;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "OwnershipRelationship".
 */
export interface OwnershipRelationship {
  id: Id42;
  interval: InclusiveExclusiveDateRange;
  legal_entity_id: LegalEntityId;
  note?: Note1;
  organization_id: OrganizationId23;
  property_id: PropertyId10;
  schema_version?: SchemaVersion40;
  synthetic?: Synthetic40;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PageQuery".
 */
export interface PageQuery {
  cursor?: Cursor;
  limit: Limit;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PageResult".
 */
export interface PageResult {
  applied_authorization: AppliedAuthorization;
  next_cursor?: NextCursor;
  total_count?: TotalCount;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PortfolioGroup".
 */
export interface PortfolioGroup {
  id: Id43;
  label: Label3;
  organization_id: OrganizationId24;
  schema_version?: SchemaVersion41;
  synthetic?: Synthetic41;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PortfolioMembership".
 */
export interface PortfolioMembership {
  group_id: GroupId;
  id: Id44;
  interval: InclusiveExclusiveDateRange;
  organization_id: OrganizationId25;
  property_id: PropertyId11;
  schema_version?: SchemaVersion42;
  synthetic?: Synthetic42;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PublicInquiryAcknowledgement".
 */
export interface PublicInquiryAcknowledgement {
  abuse_control: AbuseControl;
  correlation_id: CorrelationId5;
  inquiry_id: InquiryId;
  message: Message1;
  retry_semantics: RetrySemantics;
  status: Status10;
  synthetic?: Synthetic43;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "PublishedListingRead".
 */
export interface PublishedListingRead {
  availability: Availability;
  available_date?: AvailableDate1;
  label: Label4;
  listing_id: ListingId;
  monthly_amount: Money;
  municipality: Municipality2;
  property_name: PropertyName;
  publication: Publication;
  space_id: SpaceId2;
  state: State5;
  synthetic?: Synthetic44;
  use: Use2;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ReferenceAuditEntry".
 */
export interface ReferenceAuditEntry {
  action: Action2;
  actor_id: ActorId4;
  correlation_id: CorrelationId6;
  delegated_authority_id?: DelegatedAuthorityId1;
  event_hash: EventHash1;
  id: Id45;
  occurred_at: OccurredAt2;
  previous_event_hash?: PreviousEventHash1;
  redacted?: Redacted;
  resource_id: ResourceId2;
  resource_type: ResourceType2;
  result: Result2;
  schema_version?: SchemaVersion43;
  scope: Scope;
  synthetic?: Synthetic45;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ReferenceDomainEvent".
 */
export interface ReferenceDomainEvent {
  aggregate_id: AggregateId3;
  aggregate_version: AggregateVersion2;
  causation_id?: CausationId1;
  correlation_id: CorrelationId7;
  event_type: EventType1;
  id: Id46;
  occurred_at: OccurredAt3;
  organization_id: OrganizationId26;
  payload_record_ids?: PayloadRecordIds2;
  schema_version?: SchemaVersion44;
  synthetic?: Synthetic46;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ReferenceRecord".
 */
export interface ReferenceRecord {
  id: Id47;
  schema_version?: SchemaVersion45;
  synthetic?: Synthetic47;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "ReferenceSlice".
 */
export interface ReferenceSlice {
  groups: Groups;
  known_account_ids: KnownAccountIds;
  known_entity_ids: KnownEntityIds;
  known_household_ids: KnownHouseholdIds;
  known_organization_ids: KnownOrganizationIds;
  known_person_ids: KnownPersonIds;
  known_property_ids: KnownPropertyIds;
  known_space_ids: KnownSpaceIds;
  management: Management;
  memberships: Memberships;
  occupancies: Occupancies;
  ownership: Ownership;
  portal_access: PortalAccess;
  published_listings: PublishedListings;
  schema_version?: SchemaVersion46;
  space_states: SpaceStates;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "SpaceOperatingState".
 */
export interface SpaceOperatingState {
  availability: Availability1;
  availability_source: AvailabilitySource;
  condition: Condition;
  condition_source: ConditionSource;
  id: Id48;
  legal_restriction: LegalRestriction;
  legal_restriction_source: LegalRestrictionSource;
  maintenance_restriction: MaintenanceRestriction;
  maintenance_restriction_source: MaintenanceRestrictionSource;
  mapping_notes?: MappingNotes;
  occupancy: Occupancy;
  occupancy_source: OccupancySource;
  organization_id: OrganizationId27;
  publication: Publication1;
  publication_source: PublicationSource;
  schema_version?: SchemaVersion47;
  space_id: SpaceId3;
  synthetic?: Synthetic48;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "SafeErrorDetail".
 */
export interface SafeErrorDetail {
  field?: Field;
  reason: Reason5;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "SafeErrorEnvelope".
 */
export interface SafeErrorEnvelope {
  code: Code;
  correlation_id: CorrelationId8;
  details?: Details;
  message: Message2;
  permission_safe?: PermissionSafe;
  required_action?: RequiredAction;
  retryable: Retryable;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "SetSpaceAvailability".
 */
export interface SetSpaceAvailability {
  availability: Availability2;
  expected_version: ExpectedVersion1;
  request: UntrustedRequestInput;
  space_id: SpaceId4;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "SetSpacePublication".
 */
export interface SetSpacePublication {
  expected_version: ExpectedVersion1;
  publication: Publication2;
  request: UntrustedRequestInput;
  space_id: SpaceId5;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "StaffInquiryRead".
 */
export interface StaffInquiryRead {
  assigned_staff_id?: AssignedStaffId;
  email: Email;
  id: Id49;
  intent: Intent;
  listing_id: ListingId1;
  message: Message3;
  name: Name8;
  organization_id: OrganizationId28;
  preferred_date?: PreferredDate;
  received_at: ReceivedAt1;
  schema_version?: SchemaVersion48;
  space_id: SpaceId6;
  status: Status11;
  synthetic?: Synthetic49;
  version: Version6;
}
/**
 * Public write. Does not grant staff identity or read of internal records.
 *
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "SubmitPublicInquiry".
 */
export interface SubmitPublicInquiry {
  email: Email1;
  intent: Intent1;
  listing_id: ListingId2;
  message?: Message4;
  name: Name9;
  preferred_date?: PreferredDate1;
  request: UntrustedRequestInput;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "TaskExampleRead".
 */
export interface TaskExampleRead {
  due_on?: DueOn;
  engine?: Engine1;
  id: Id50;
  next_action: NextAction;
  organization_id: OrganizationId29;
  owner_id?: OwnerId;
  schema_version?: SchemaVersion49;
  status: Status12;
  synthetic?: Synthetic50;
  title: Title1;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "TriageInquiry".
 */
export interface TriageInquiry {
  decision: Decision1;
  expected_version: ExpectedVersion1;
  inquiry_id: InquiryId1;
  note: Note2;
  request: UntrustedRequestInput;
}
/**
 * Server-resolved actor. Must not appear on public or generic update payloads.
 *
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "TrustedActorContext".
 */
export interface TrustedActorContext {
  actor_id: ActorId5;
  delegated_authority_id?: DelegatedAuthorityId2;
  feature_flags?: FeatureFlags;
  membership_ids?: MembershipIds;
  organization_id: OrganizationId30;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "UpdateLeasableSpace".
 */
export interface UpdateLeasableSpace {
  commercial?: CommercialTerms | null;
  expected_version: ExpectedVersion1;
  label?: Label5;
  request: UntrustedRequestInput;
  residential?: ResidentialTerms | null;
  space_id: SpaceId7;
  square_feet?: SquareFeet2;
}
/**
 * This interface was referenced by `FoundationContracts`'s JSON-Schema
 * via the `definition` "UpdateProperty".
 */
export interface UpdateProperty {
  address?: Address | null;
  expected_version: ExpectedVersion1;
  name?: Name10;
  parcel_references?: ParcelReferences2;
  property_id: PropertyId12;
  request: UntrustedRequestInput;
}
