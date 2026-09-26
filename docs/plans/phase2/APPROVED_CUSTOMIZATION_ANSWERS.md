# Approved Phase 2 customization answers

Provenance: Nathan Doss approved the recommendations with “Let's proceed with all recommendations you gave!”

This file is a consolidated decision record. It is not a claim that Nathan separately typed each answer. Each entry keeps its question number, topic, selected option when one was given, and answer meaning. Entries are not collapsed into ranges.

Related map: [ANSWER_TRACEABILITY.md](ANSWER_TRACEABILITY.md).

The missing numbered-questionnaire blocker is cleared only after that map covers Q1–Q120 and its decision and requirement references resolve. Recording these answers is not implementation coverage and is not Phase 2 acceptance.

## Platform boundaries and domain model

### Q1. Architectural deployment model

- Selected option: C
- Answer: Use a modular monolith with enforceable domain boundaries and an extraction path for future services.

### Q2. Primary backend ownership

- Selected option: B
- Answer: FastAPI domain services own business workflows; PostgreSQL enforces critical relational, authorization, uniqueness, and transactional invariants.

### Q3. Frontend architecture

- Selected option: C
- Answer: Preserve the Emergent visual shell while incrementally refactoring application architecture, shared components, routes, API clients, forms, and state handling. No immediate wholesale rewrite.

### Q4. Initial organization model

- Selected option: C
- Answer: Operate one active HawkVision organization with organization-scoped records and a structure that can support additional organizations later, without building a full SaaS management product now.

### Q5. Legal entity separation

- Selected option: B
- Answer: Model legal owning entities separately from the management organization as first-class records.

### Q6. Management relationships

- Selected option: B
- Answer: Preserve effective-dated ownership and management relationships rather than storing only current relationships.

### Q7. Portfolio hierarchy

- Selected option: A
- Answer: Support organization, legal entity, portfolio/group, property, building, unit/leasable space, and household/business-occupant concepts. Apply the relationship-first clarification below rather than a rigid ownership tree.
- Clarification: Q7 follows the relationship-first model recorded in `CONFLICT-008`. It is not a mandatory LLC to portfolio to household foreign-key chain.

### Q8. Mixed-use properties

- Selected option: A
- Answer: Residential and commercial spaces can exist within the same property and building.

### Q9. Leasable-space model

- Selected option: B
- Answer: Use a common unit/space core with validated residential and commercial subtype fields.

### Q10. Property grouping

- Selected option: none numbered
- Answer: Support legal entity, neighborhood, city, state, portfolio, operational territory, assigned manager, maintenance route, and investment strategy. Use governed attributes, memberships, and tags without duplicating properties.

### Q11. Person model

- Selected option: B
- Answer: Reuse one person record within an organization with multiple effective-dated roles, while keeping authentication and role-specific private information separate.

### Q12. Business/contact model

- Selected option: Yes
- Answer: Use first-class businesses and contacts for contractors, commercial tenants, suppliers, legal firms, and service companies, with appropriately scoped addresses, documentation, relationships, assignments, and communication endpoints.

### Q13. Household account model

- Selected option: D
- Answer: Use one primary authenticated resident account by default, with additional household access only through explicit authorization/invitation. Never use a shared household password.
- Clarification: Q13 retains one primary portal account by default, separate individual identity and legal-signing relationships, and explicit additional access per `CONFLICT-010`.

### Q14. Occupants versus lease signers

- Selected option: Yes
- Answer: Distinguish occupants, responsible payers, guarantors, minors, authorized contacts, and lease signers as separate relationships and capacities.

### Q15. Historical relationships

- Selected option: Yes
- Answer: Retain queryable history for former residents, contractors, owners, unit assignments, and expired authorizations through effective dates and archival states, subject to governed retention.

### Q16. Canonical identifiers

- Selected option: D
- Answer: Use UUID primary identifiers plus human-readable reference numbers. Preserve existing stable UUIDs. Evaluate time-sortable UUIDs for new records without regenerating existing identities.
- Clarification: Q16 preserves existing UUIDs. A new generation strategy must not rewrite established identity.

### Q17. Provider identifiers

- Selected option: B
- Answer: Store external identifiers in provider-reference mappings scoped by provider, account, environment, object type, and canonical record. Do not use them as canonical identities.

### Q18. Address model

- Selected option: none numbered
- Answer: Use normalized address records plus immutable address snapshots on issued leases, notices, applications, and executed documents.

### Q19. Time standard

- Selected option: none numbered
- Answer: Store instants in UTC, retain appropriate originating/property time zones, and display locally. Use property-local rules for schedules/deadlines and true date-only values for date-only terms.

### Q20. Currency model

- Selected option: none numbered
- Answer: Store money in integer minor units with an ISO currency code, initially USD. Use exact intermediate calculations and explicit rounding. Prohibit binary floating-point money calculations.

## State machines and workflow ownership

### Q21. State-transition enforcement

- Selected option: C
- Answer: Enforce transitions in backend services with authorization and database safeguards. Consequential status fields are not unrestricted editable attributes.

### Q22. Property lifecycle

- Selected option: approved vocabulary
- Answer: Approve onboarding, active, restricted, disposition_pending, inactive, and archived. Define permitted transitions, prerequisites, and reversal/reactivation rules rather than automatically progressing through every state.
- Clarification: Q22–Q27 describe state vocabularies and guarded transitions/projections, with separated unit dimensions per `CONFLICT-009`.

### Q23. Building lifecycle

- Selected option: approved vocabulary
- Answer: Approve planned, active, renovation, partially_unavailable, unavailable, and inactive as the proposed vocabulary. Model overlapping operational dimensions explicitly where needed.

### Q24. Unit/leasable-space lifecycle

- Selected option: separated dimensions
- Answer: Use separate physical-condition, occupancy, leasing-availability, publication, maintenance-restriction, and legal-restriction dimensions. Do not collapse them into one overloaded status.

### Q25. Person lifecycle

- Selected option: none numbered
- Answer: Do not routinely delete people when a relationship ends. Use justified active/inactive/deceased/restricted/anonymized states where appropriate, with separate relationship dates and governed retention/deletion.

### Q26. Household lifecycle

- Selected option: derived journey
- Answer: Support the displayed journey prospective, applicant, approved, lease_pending, active_resident, notice_period, former_resident, and archived. Keep denied/withdrawn outcomes on applications and derive household journey from relationships rather than imposing one exclusive permanent household status.

### Q27. Contractor lifecycle

- Selected option: approved vocabulary
- Answer: Approve prospect, onboarding, active, conditionally_approved, suspended, expired, terminated, and archived, with explicit authorized transitions and supporting evidence.

### Q28. Work ownership standard

- Selected option: none numbered
- Answer: Every actionable operational record carries the applicable responsible owner, assigned team, state, priority, due date/SLA, next action, escalation status, source, and history. Explain genuinely non-applicable fields.

### Q29. Workflow implementation

- Selected option: C
- Answer: Use explicit domain state machines with shared task, approval, and escalation frameworks. Do not introduce a general workflow-engine purchase or freely editable no-code topology now.

### Q30. Administrative configurability

- Selected option: none numbered
- Answer: Authorized administrators may configure categories, SLA targets, assignment rules, escalation contacts, approval thresholds, notification templates, office hours, property instructions, document requirements, and reason codes. State-machine topology and financial posting logic remain developer-controlled.

## Data ownership and source of truth

### Q31. Source of truth

- Selected option: none numbered
- Answer: PerchPoint is the authoritative operational record even when an external provider executes an action. Preserve authoritative provider observations and reconcile them. Do not invent provider settlement or completion facts.

### Q32. Provider conflict behavior

- Selected option: C
- Answer: Create a visible exception, preserve both observations, and use deterministic reconciliation. Neither side silently overwrites the other.

### Q33. Derived values

- Selected option: none numbered
- Answer: Balances, occupancy, availability, performance metrics, and approval status derive from authoritative facts. Correct underlying records through controlled workflows rather than directly editing derived results.

### Q34. Record deletion

- Selected option: C
- Answer: Use domain-specific archival, anonymization, and governed deletion. Neither universal soft deletion nor indefinite retention is the default for every record class.

### Q35. Historical correction

- Selected option: B
- Answer: Preserve the original fact and create an attributable correction with reason, actor, effective date, recorded date, and changed values, especially for financial, lease, approval, screening, maintenance, and identity history.

## Privacy classification and retention

### Q36. Data classification

- Selected option: approved vocabulary
- Answer: Approve public, internal operational, confidential business, personal information, highly sensitive/restricted, financial/legal regulated, and secrets/credentials classifications. A field may need more than one applicable label.

### Q37. Field-level classification

- Selected option: Yes
- Answer: Classify sensitive fields individually and define their visibility, projection, logging, export, and retention treatment.

### Q38. Screening reports

- Selected option: C
- Answer: Store only provider references and results needed for approved operations, with restricted access and retention determined through provider and qualified legal review.

### Q39. Government identifiers

- Selected option: C
- Answer: Avoid storing full Social Security numbers. Prefer provider-hosted/tokenized collection. Any genuinely unavoidable handling requires a separately reviewed, isolated, encrypted, audited, masked, and time-limited design.

### Q40. Payment credentials

- Selected option: none numbered
- Answer: Use processor tokens and provider-hosted collection. Do not store raw card or bank credentials. Restrict any necessary masked account metadata.

### Q41. Document retention

- Selected option: B
- Answer: Use policies determined by document/data class, jurisdiction, relationship, business purpose, and legal hold.

### Q42. Retention before legal review

- Selected option: B
- Answer: Use visible, configurable provisional policies without automatic destructive processing before approved durations and rules are available.

### Q43. Legal holds

- Selected option: Yes
- Answer: Holds override automated deletion/anonymization and require authorized creation/release, scope, reason, custodian, and audit history.

### Q44. Sensitive access auditing

- Selected option: Yes
- Answer: Audit access to screening reports, executed leases, financial records, legal documents, government identifiers, and private employee information as appropriate. Audit metadata must not unnecessarily duplicate sensitive content.

### Q45. Data exports

- Selected option: Yes
- Answer: Treat exports as privileged, auditable operations with scoped contents, expiring access, and watermarking where appropriate.

## API and application contracts

### Q46. API style

- Selected option: C
- Answer: REST resource/command interfaces plus versioned event contracts and optimized read endpoints.

### Q47. API versioning

- Selected option: B
- Answer: Version externally consumed/provider-facing contracts from the beginning and define compatibility rules for internal contracts without gratuitously changing every existing route.

### Q48. Contract authority

- Selected option: C
- Answer: Use JSON Schema/OpenAPI contracts with generated language representations and one authoring authority per contract. The verified repository-specific implementation retains Pydantic foundation authoring, exports schemas, and generates TypeScript. Do not create competing hand-edited definitions.
- Clarification: Q48 uses the verified Pydantic to exported JSON Schema/contracts to TypeScript pipeline. Generated artifacts are not independent authoring sources.

### Q49. Command/query separation

- Selected option: none numbered
- Answer: Use explicit commands for material business actions. Validated generic PATCH may remain for low-risk profile or metadata fields.

### Q50. Error contract

- Selected option: none numbered
- Answer: Standardize stable error code, safe user message, correlation ID, field violations, retryability, required action, and permission-safe metadata. Do not return internal stack traces.

### Q51. Idempotency

- Selected option: none numbered
- Answer: Require scoped idempotency for externally triggered or retryable material commands, including payments, applications, leases, screening, approvals, communications, scheduling, maintenance creation, imports, and provider orders. Define request fingerprints and same-key/different-payload conflicts.

### Q52. Concurrency control

- Selected option: C
- Answer: Use optimistic concurrency/version checks by default and targeted transactional locking for scarce-resource, financial, or other critical invariants. Avoid silent last-write-wins behavior.

### Q53. Pagination

- Selected option: none numbered
- Answer: Use stable cursor-based pagination for large/changing operational collections. Offset pagination is acceptable for small stable administrative lists.

### Q54. Search contracts

- Selected option: none numbered
- Answer: Enforce role, organization, property, relationship, privacy, and assignment scope before returning results, counts, facets, snippets, or suggestions.

### Q55. Bulk operations

- Selected option: none numbered
- Answer: Require preview, validation, per-record permission evaluation, impact count, appropriate confirmation, idempotency, execution-time revalidation, and a retained outcome report.

### Q56. Long-running operations

- Selected option: B
- Answer: Use durable jobs with progress, ownership, retries, defined cancellation rules, and visible results for imports, reports, mass communication, document processing, and reconciliation.

## Events, audit, and reliability

### Q57. Domain events

- Selected option: none numbered
- Answer: Emit versioned events for meaningful business changes. Do not require full event sourcing or an event for every database column change.

### Q58. Transactional outbox

- Selected option: none numbered
- Answer: Write the business mutation and its outbox event together. Include the relevant audit entry and idempotent command result in the same transaction where required by the command design.

### Q59. Webhook inbox

- Selected option: none numbered
- Answer: Verify authenticity/signatures, persist accepted events durably, deduplicate, protect against replay, handle ordering where relevant, and connect processing to retry and dead-letter ownership.

### Q60. Delivery semantics

- Selected option: B
- Answer: At least once with idempotent consumers. Do not promise distributed exactly-once delivery across providers.

### Q61. Event versioning

- Selected option: none numbered
- Answer: Consumers tolerate agreed additive changes. Breaking payload or semantic changes require an explicit new version and compatibility handling.

### Q62. Audit architecture

- Selected option: B
- Answer: Append-only audit events, separate from editable activity notes, conversation messages, and ordinary database/application logs.

### Q63. Audit content

- Selected option: none numbered
- Answer: Record actor, effective actor, delegated authority, action, target, timestamp, request/correlation ID, source channel, material before/after values, policy version, reason, related approval, and proportionate IP/device metadata. Redact sensitive values.

### Q64. Audit tamper resistance

- Selected option: B
- Answer: Restricted append-only permissions with chained hashes/checkpoints. Define the threat model and independent-checkpoint requirement. Do not claim administrator-proof immutability or introduce blockchain.
- Clarification: Q64 provides tamper evidence with documented privileged-administrator limitations, not absolute immutability.

### Q65. Replay policy

- Selected option: none numbered
- Answer: Failed integration deliveries can be replayed without repeating the underlying business decision. Protect against duplicate charges, approvals, lease actions, messages where provider capability permits, and work orders. Document residual delivery uncertainty.

### Q66. Dead-letter ownership

- Selected option: D
- Answer: Route failures to domain-appropriate queues with Nathan as technical escalation. Faruk receives material business consequences, not routine integration noise.

## Integration adapter contracts

### Q67. Adapter pattern

- Selected option: none numbered
- Answer: Place payment, voice/SMS, email, calendar, screening, e-signature, accounting, storage, and AI providers behind PerchPoint-owned interfaces.

### Q68. Provider selection timing

- Selected option: B
- Answer: Define replaceable contracts now. Select actual providers in their implementation phases using cost, capability, eligibility, and review requirements. Stripe is a likely payment provider, not an already activated dependency.

### Q69. Provider-specific features

- Selected option: B
- Answer: Map useful features to a PerchPoint capability or isolate the provider-specific extension rather than leaking it throughout the domain model.

### Q70. Sandbox policy

- Selected option: none numbered
- Answer: Use deterministic fake adapters, appropriately sanitized fixtures, or separately authorized official sandboxes. No live tenant messages, charges, screenings, signatures, or financial imports in Phase 2.

### Q71. Webhook isolation

- Selected option: none numbered
- Answer: Keep provider/account/environment configuration and verification secrets independently scoped and validated.

### Q72. Integration health

- Selected option: none numbered
- Answer: Expose configuration state, last successful request, last webhook, degradation/outage state, queued failures, rate-limit status, and reconciliation freshness through standardized, timestamped health information.

### Q73. Communication ownership

- Selected option: none numbered
- Answer: PerchPoint owns conversation records. Approved email, SMS, and calls are channel deliveries or inbound events connected to those conversations with scoped visibility.

### Q74. Website-only listings

- Selected option: none numbered
- Answer: Retain an optional dormant distribution boundary for possible future use. HawkVision’s website is the approved listing destination. Do not implement or activate Zillow/Facebook distribution now.

### Q75. Accounting boundary

- Selected option: none numbered
- Answer: PerchPoint owns operational subledger, payment state, property-level visibility, approvals, reconciliation evidence, and exports. Professional accounting owns general ledger, tax, payroll, and formal books.

### Q76. Maintenance-system boundary

- Selected option: none numbered
- Answer: Define shared maintenance APIs/events so the post-completion app uses PerchPoint identities and records rather than duplicating the system of record.

## Reference vertical slice

### Q77. Proof-slice scope

- Selected option: B
- Answer: Property, building, unit/space, inquiry, and activity history, with read-only task/approval examples. Do not implement the complete leasing or approval engines during this reference slice.

### Q78. Synthetic portfolio

- Selected option: none numbered
- Answer: Extend existing fixtures to cover single-family, duplex, triplex, multifamily, mixed-use, commercial, vacant renovation, occupied space, and another-state scenarios. Preserve valid existing fixture identities.

### Q79. Mixed-use example

- Selected option: none numbered
- Answer: Use a wholly synthetic property with upstairs residential units and a downstairs bakery/commercial conversion as an architectural reference.

### Q80. Reference actors

- Selected option: none numbered
- Answer: Cover Nathan/platform administrator, Faruk/owner, Ann/project and leasing manager, leasing staff, maintenance coordinator, contractor, resident, applicant, and accounting viewer. Map personas to existing role definitions. Later-workflow participants can remain read-only/simulated.

### Q81. Emergent role

- Selected option: B
- Answer: Cursor defines and freezes contracts. Emergent builds the bounded connected visual slice. Cursor reviews and hardens the returned implementation.

### Q82. Visual preservation

- Selected option: none numbered
- Answer: Preserve the existing premium HawkVision/PerchPoint language while improving component organization, accessibility, information density, state handling, and responsive behavior.

### Q83. Database behavior

- Selected option: B
- Answer: Use real isolated local/test PostgreSQL with migrations and synthetic data. Memory-only or SQLite tests do not prove PostgreSQL constraints, RLS, or transaction behavior.

### Q84. Supabase timing

- Selected option: B
- Answer: Prefer local Supabase or suitable disposable development infrastructure before final production account setup. No production subscription or cloud activation is implied.

### Q85. Proof-slice writes

- Selected option: none numbered
- Answer: Support synthetic property, building/space, and inquiry creation/updates with real persistence, validation, authorization, audit, and events in the designated implementation packages.

### Q86. Demonstration cases

- Selected option: none numbered
- Answer: Cover valid creation, invalid relationship rejection, unauthorized access denial, concurrency conflict, audit history, outbox/event creation, adapter failure, retry, archived historical relationships, and multi-property filtering.

## Nonfunctional requirements

### Q87. Scale

- Selected option: none numbered
- Answer: Design and test for at least 10× current operating scale, with an explicit representative workload and schemas that allow further growth. Do not claim unlimited capacity.

### Q88. Availability

- Selected option: C
- Answer: A provisional 99.9% monthly target for core authenticated operations, with planned maintenance explicitly treated in the measurement definition. This is not yet an achieved SLA.

### Q89. Performance

- Selected option: none numbered
- Answer: Initial targets: ordinary authenticated reads p95 below 500 ms server-side; material commands p95 below one second excluding providers; good public Core Web Vitals at p75; typical search below one second; useful dashboard content below two seconds under declared normal load.

### Q90. Recovery

- Selected option: none numbered
- Answer: Initial general-data planning targets: RPO no worse than 24 hours and RTO no worse than four hours. Financial/ledger/audit data need a separately defined tighter recovery objective. Near-zero committed-data loss is a design goal requiring appropriate backup/replication/PITR and restore evidence, not a guarantee established by transactions alone.
- Clarification: Q90 separates transaction durability from disaster recovery. No near-zero recovery claim is accepted without infrastructure and restore proof.

### Q91. Accessibility

- Selected option: none numbered
- Answer: Target WCAG 2.2 AA for critical journeys with both automated and appropriate manual verification.

### Q92. Browser/device support

- Selected option: none numbered
- Answer: Current and previous major Chrome, Edge, Firefox, and Safari; modern iOS Safari and Android Chrome; responsive layouts from approximately 320 px; installable PWA where useful; no dedicated native app now.

### Q93. Offline behavior

- Selected option: C
- Answer: Resilient drafts and retry for field workflows, without claiming full offline availability or permitting uncontrolled sensitive caches and offline payment/approval authority.

### Q94. Observability

- Selected option: none numbered
- Answer: Standardize structured logs, correlation IDs, error monitoring, request/job/queue metrics, integration health, audit links, performance traces, business-event metrics, and privacy redaction.

### Q95. Alerting

- Selected option: C
- Answer: Nathan handles technical alerts. Ann and designated staff handle operational alerts. Faruk receives business-critical incidents and reserved decisions.

### Q96. Security baseline

- Selected option: none numbered
- Answer: Apply OWASP ASVS principles, least privilege, deny-by-default authorization, secure headers/CSP, encryption in transit/at rest, isolated secrets, dependency scanning, rate limits, abuse prevention, input/file validation, and explicit threat modeling. Do not claim certification from a checklist.

### Q97. Rate limiting

- Selected option: none numbered
- Answer: Consider actor, IP, organization, endpoint, property, provider, and action sensitivity rather than one universal limit.

### Q98. Data residency

- Selected option: A
- Answer: Require United States hosting where supported for relevant sensitive data. Evaluate backups, logs, telemetry, and provider processing as well as the primary database region.

### Q99. Logging retention

- Selected option: B
- Answer: Tiered, configurable retention with sensitive-field redaction rather than retaining all logs indefinitely.

### Q100. Feature flags

- Selected option: none numbered
- Answer: Server-enforced flags scoped as appropriate by environment, organization, role, and property. Feature flags do not replace or grant authorization.

## Testing and architecture evidence

### Q101. Test layers

- Selected option: approved list
- Answer: Approve unit, domain-invariant, schema/constraint, migration, API-contract, event-contract, authorization/RLS, adapter-contract, concurrency/idempotency, integration, accessibility, performance-smoke, and deterministic synthetic-scenario testing. Implement evidence appropriate to the current package. Retain later tests as planned.

### Q102. Property-based testing

- Selected option: none numbered
- Answer: Use it where valuable for financial allocation, access boundaries, state transitions, identifiers, and relationship invariants, when the corresponding behavior is implemented.

### Q103. Mutation testing

- Selected option: B
- Answer: Target critical domain rules rather than requiring mutation testing everywhere.

### Q104. Compatibility gates

- Selected option: none numbered
- Answer: Detect breaking API/event/schema changes and require explicit review and migration handling. Local checks precede later remote CI enforcement.

### Q105. Migration policy

- Selected option: none numbered
- Answer: Use reviewed forward migrations, deterministic clean application, upgrades from prior versions, separate backfills, rollback/mitigation plans, and no manual production schema edits.

### Q106. Diagrams

- Selected option: none numbered
- Answer: Maintain version-controlled system context, containers/components, domain boundaries, canonical relationships, authorization flow, command/event transaction, provider webhook flow, document/data classification, and deployment topology diagrams, generated where practical.

### Q107. ADR coverage

- Selected option: none numbered
- Answer: Record consequential decisions about database ownership, modular-monolith boundaries, identity, authorization, event/outbox architecture, audit, storage, API/versioning, jobs, provider adapters, organization scoping, and the financial boundary. Reuse existing ADRs where appropriate.

### Q108. Performance evidence

- Selected option: none numbered
- Answer: Use representative query plans and measured load tests with dataset, hardware, workload, concurrency, latency distribution, and errors reported.

### Q109. Threat coverage

- Selected option: none numbered
- Answer: Address cross-property and cross-household access, vendor overreach, ID enumeration, privilege escalation, forged webhooks, replay, duplicate commands, malicious uploads, mass assignment, sensitive logging, stale delegation, and export abuse. Execute tests for active surfaces and document later-phase controls for absent surfaces.

### Q110. Failure simulation

- Selected option: none numbered
- Answer: Cover database conflicts, provider timeouts, duplicate webhooks, queue retries, malformed payloads, expired credentials, and partial failures as applicable to the implemented surface.

## Ownership, acceptance, and delivery

### Q111. Technical authority

- Selected option: E
- Answer: Nathan is the accountable technical owner. Faruk retains business authority. Cursor and other AI tools advise and implement without becoming approval owners.

### Q112. Domain acceptance

- Selected option: none numbered
- Answer: Faruk: reserved owner decisions/strategy. Nathan: technical/platform acceptance. Ann: leasing/operating usability. Accounting professional: accounting boundaries/exports. Counsel: legal/compliance policies. Maintenance specialists: field-workflow validity.

### Q113. Provisional acceptance

- Selected option: B
- Answer: Nathan can give documented provisional acceptance within assumptions when a stakeholder is unavailable. This cannot substitute for required legal/financial authority or production activation approval.

### Q114. Branch model

- Selected option: none numbered
- Answer: Use `cursor/phase-02-contracts`, `emergent/phase-02-reference-slice`, and `integration/phase-02` when their work actually begins. Preserve existing work and verify ancestry. Do not create branches merely for documentation volume.

### Q115. Contract-freeze sequence

- Selected option: none numbered
- Answer: Cursor audits, proposes architecture/contracts, Nathan approves plan, Cursor implements reference contracts/core, contracts freeze, Emergent builds within the envelope, Cursor reviews/hardens, integration gates run, and Phase 2 acceptance is recorded.

### Q116. Emergent restrictions

- Selected option: none numbered
- Answer: No independent changes to canonical schemas, approved migrations, authentication, authorization, event contracts, financial calculations, provider security, audit semantics, or dependency strategy. Propose and review necessary changes explicitly.

### Q117. Phase 2 technical completion

- Selected option: none numbered
- Answer: Require documented domains/terminology, reference database and repeatable migrations, typed API/event/error contracts, authorization interfaces, proven outbox/inbox and audit reference behavior, provider interfaces, working synthetic slice, negative-access tests, measured performance, diagrams/ADRs, passing required tests, and no real production data/provider activation. These are full-Phase-2 gates, not claims that P2-01 alone fulfills them.
- Clarification: Q117 is the full Phase 2 exit gate. Database/RLS/worker evidence belongs in its designated packages. Do not claim it from P2-01 model tests.

### Q118. Business completion

- Selected option: none numbered
- Answer: Keep business acceptance provisional until Faruk and relevant specialists review their domains, without blocking all Phase 3 planning once applicable technical/governance gates pass.

### Q119. Production readiness

- Selected option: none numbered
- Answer: Remain blocked after Phase 2 until the necessary identity, environments, security, provider, workflow, legal, real-data, migration, reconciliation, and operating acceptance gates are met.

### Q120. Implementation authorization

- Selected option: B
- Answer: Nathan approves the specific implementation plan before implementation. The subsequent P2-01 authorization already supplied is the current scope: continue P2-01 after recording this register, then stop for review before P2-02. Do not revert to an earlier planning-only gate or treat this answer register as permission to implement all later packages.
- Clarification: Q120 does not revoke the subsequent P2-01 implementation authorization.

## Recorded implementation clarifications

Preserve the distinction between an approved design choice, a repository-grounded implementation interpretation, and executed acceptance evidence.

- Q7 follows the relationship-first model recorded in `CONFLICT-008`. It is not a mandatory LLC to portfolio to household foreign-key chain.
- Q22–Q27 describe state vocabularies and guarded transitions/projections, with separated unit dimensions per `CONFLICT-009`.
- Q13 retains one primary portal account by default, separate individual identity and legal-signing relationships, and explicit additional access per `CONFLICT-010`.
- Q16 preserves existing UUIDs. A new generation strategy must not rewrite established identity.
- Q48 uses the verified Pydantic to exported JSON Schema/contracts to TypeScript pipeline. Generated artifacts are not independent authoring sources.
- Q64 provides tamper evidence with documented privileged-administrator limitations, not absolute immutability.
- Q90 separates transaction durability from disaster recovery. No near-zero recovery claim is accepted without infrastructure and restore proof.
- Q117 is the full Phase 2 exit gate. Database/RLS/worker evidence belongs in its designated packages. Do not claim it from P2-01 model tests.
- Q120 does not revoke the subsequent P2-01 implementation authorization.

P2-01 conditions remain: explicit compatibility classification, narrowly scoped public inquiry contracts, one authoritative write path per operation with MongoDB’s legacy scope documented, stable fixtures, no new database/auth/worker runtime during P2-01, and honest test evidence.
