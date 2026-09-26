# Requirements Traceability

Canonical Phase 1 requirement register. IDs are immutable; supersede rather than reuse.

## PP-PROD-001

- **Normative statement:** PerchPoint shall be HawkVision's routine operator-facing system and complete intended property operating platform.
- **Rationale:** Avoid fragmented history and founder dependency.
- **Source:** Directive §3.3 and §4.1; Platform Vision pp. 1–2 corroborates
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Phased gates do not reduce scope.
- **Dependencies:** Approved roadmap
- **Risks:** Scope dilution
- **Verification method:** Constitution and capability review
- **Related tests/evidence:** docs/product/PRODUCT_CONSTITUTION.md
- **Affected domains:** product
- **Faruk must confirm later:** yes

## PP-PROD-002

- **Normative statement:** The system shall prioritize measurable recovery of Faruk's attention while preserving reserved judgment.
- **Rationale:** Owner time is the primary business constraint.
- **Source:** Directive §3.2, §4.15, and §4.20
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Source events can define formulas before baselines.
- **Dependencies:** Command-center event model
- **Risks:** Vanity metrics
- **Verification method:** Formula/source-event review
- **Related tests/evidence:** docs/governance/CAPABILITY_REGISTER.md
- **Affected domains:** product,analytics
- **Faruk must confirm later:** yes

## PP-GOV-001

- **Normative statement:** Conflicts shall follow documented source precedence and shall never be resolved silently.
- **Rationale:** Prevent policy drift.
- **Source:** Directive §2
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Directive is current highest authority.
- **Dependencies:** Source manifest
- **Risks:** Hidden contradiction
- **Verification method:** Conflict-register validation
- **Related tests/evidence:** docs/source/provenance/SOURCE_CONFLICT_REGISTER.md
- **Affected domains:** governance
- **Faruk must confirm later:** no

## PP-GOV-002

- **Normative statement:** Every material change shall identify requirements, evidence, rollback, phase, and acceptance authority.
- **Rationale:** Make delivery auditable.
- **Source:** Directive §11–§12
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** GitHub remains canonical.
- **Dependencies:** Change control
- **Risks:** Unreviewable releases
- **Verification method:** PR/change checklist
- **Related tests/evidence:** docs/governance/CHANGE_CONTROL.md
- **Affected domains:** governance
- **Faruk must confirm later:** no

## PP-AUTH-001

- **Normative statement:** Sensitive access and actions shall be denied by default and authorized by authenticated server authority.
- **Rationale:** Client roles are not security boundaries.
- **Source:** Directive §12; Platform Vision p. 1 corroborates role-designed secure access
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Production auth is later phase.
- **Dependencies:** Identity/RLS design
- **Risks:** Unauthorized access
- **Verification method:** Direct negative API/RLS tests
- **Related tests/evidence:** docs/audits/PHASE_0_CURSOR_AUDIT.md
- **Affected domains:** auth,security
- **Faruk must confirm later:** no

## PP-AUTH-002

- **Normative statement:** Delegation shall be attributable, scoped, limited, expiring, revocable, and action-audited without shared master codes.
- **Rationale:** Separate authority from convenience.
- **Source:** Directive §4.9
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** No implicit super-role.
- **Dependencies:** Approval engine
- **Risks:** Privilege abuse
- **Verification method:** Expiry/scope/self-approval tests
- **Related tests/evidence:** docs/governance/APPROVAL_AND_DELEGATION_POLICY.md
- **Affected domains:** auth,governance
- **Faruk must confirm later:** yes

## PP-PROP-001

- **Normative statement:** The canonical model shall represent organization, entity, jurisdiction, property, building, unit, commercial space, and mixed-use structure.
- **Rationale:** Support current and future portfolio types.
- **Source:** Directive §4.14
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Residential receives practical priority.
- **Dependencies:** Domain contracts
- **Risks:** Commercial data hidden in notes
- **Verification method:** Relationship and invalid-link tests
- **Related tests/evidence:** backend/tests/test_foundation_contracts.py
- **Affected domains:** property,data
- **Faruk must confirm later:** no

## PP-PROP-002

- **Normative statement:** Stable PerchPoint identifiers shall remain distinct from provider identifiers.
- **Rationale:** Enable provider replacement and lineage.
- **Source:** Directive §6.3 and roadmap §3; Platform Vision p. 2 corroborates
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** UUIDv5 is synthetic-only implementation detail.
- **Dependencies:** Identity model
- **Risks:** Cross-provider collision
- **Verification method:** ID/provenance tests
- **Related tests/evidence:** backend/foundation/base.py
- **Affected domains:** property,data
- **Faruk must confirm later:** no

## PP-LEASE-001

- **Normative statement:** Final applicant approval and new leases shall require Faruk or explicit valid delegation.
- **Rationale:** Preserve housing authority.
- **Source:** Directive §4.6
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Delegation may be introduced later.
- **Dependencies:** Approval/audit/lease state
- **Risks:** Unauthorized housing decision
- **Verification method:** Approval-lock negative tests
- **Related tests/evidence:** docs/governance/RACI.md
- **Affected domains:** leasing,auth
- **Faruk must confirm later:** yes

## PP-LEASE-002

- **Normative statement:** No AI or provider result shall autonomously make tenant or adverse-action decisions.
- **Rationale:** Meet legal and ethical boundaries.
- **Source:** Directive §5
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Qualified counsel and Faruk
- **Status:** accepted
- **Assumptions:** Counsel review remains required.
- **Dependencies:** Screening criteria/notices
- **Risks:** Discrimination/legal exposure
- **Verification method:** Human approval and prohibited-action tests
- **Related tests/evidence:** docs/product/PRODUCT_CONSTITUTION.md
- **Affected domains:** leasing,legal
- **Faruk must confirm later:** yes

## PP-FIN-001

- **Normative statement:** Money movement shall never be inferred solely from browser success; provider state and accounting facts shall remain distinct.
- **Rationale:** Prevent duplicate or false postings.
- **Source:** Directive §4.2; Platform Vision p. 2 corroborates
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Accounting specialist
- **Status:** accepted
- **Assumptions:** Stripe is primary direction.
- **Dependencies:** Signed events/idempotency/journal
- **Risks:** Financial loss
- **Verification method:** Replay/reconciliation tests
- **Related tests/evidence:** docs/governance/PAYMENT_CHANNEL_POLICY.md
- **Affected domains:** finance
- **Faruk must confirm later:** yes

## PP-FIN-002

- **Normative statement:** Routine approval shall be limited to $1,200 inclusive.
- **Rationale:** Preserve owner authority.
- **Source:** Directive §4.6–§4.7
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Emergency policy is separate/provisional.
- **Dependencies:** Policy-as-data/project totals
- **Risks:** Threshold bypass
- **Verification method:** Boundary/aggregation tests
- **Related tests/evidence:** docs/governance/APPROVAL_AND_DELEGATION_POLICY.md
- **Affected domains:** finance,auth
- **Faruk must confirm later:** yes

## PP-MAINT-001

- **Normative statement:** Technicians shall record structured observed conditions, causes, recommendations, repair-versus-replace reasoning, specifications, evidence, safety, estimates, alternatives, consequences, recurrence risk, confidence, and specialist need.
- **Rationale:** Measure and reduce rework/waste.
- **Source:** Directive §4.10
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Maintenance users and Ann
- **Status:** accepted
- **Assumptions:** Technician acknowledgment when practical.
- **Dependencies:** Maintenance state/audit
- **Risks:** Unsafe or incompatible procurement
- **Verification method:** Required-field/override tests
- **Related tests/evidence:** docs/governance/MAINTENANCE_RECOMMENDATION_POLICY.md
- **Affected domains:** maintenance
- **Faruk must confirm later:** yes

## PP-MAINT-002

- **Normative statement:** Maintenance employees shall have no standing purchase authority.
- **Rationale:** Separate diagnosis from spending.
- **Source:** Directive §4.10–§4.11
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Recorded emergency authorization still required.
- **Dependencies:** Approval engine
- **Risks:** Unauthorized spend
- **Verification method:** Denied purchase and emergency tests
- **Related tests/evidence:** docs/governance/APPROVAL_AND_DELEGATION_POLICY.md
- **Affected domains:** maintenance,finance
- **Faruk must confirm later:** yes

## PP-WORK-001

- **Normative statement:** Contractor access shall be assignment-scoped and shall not permit self-approval of change orders, work, or invoices.
- **Rationale:** Least privilege and separation of duties.
- **Source:** Directive §4.12
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann
- **Status:** accepted
- **Assumptions:** Minimum resident information only.
- **Dependencies:** Identity/assignment/invoice model
- **Risks:** Privacy and fraud
- **Verification method:** Cross-assignment/self-approval tests
- **Related tests/evidence:** docs/governance/RACI.md
- **Affected domains:** workforce,auth
- **Faruk must confirm later:** no

## PP-WORK-002

- **Normative statement:** Cleaners shall have assignment-scoped restricted access with time-limited entry instructions, checklists, media, inspection, rework, invoice, and performance history.
- **Rationale:** Turns require accountable evidence.
- **Source:** Directive §4.12
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann
- **Status:** accepted
- **Assumptions:** Entry instructions are time-limited.
- **Dependencies:** Identity/work order model
- **Risks:** Unsafe access/poor quality
- **Verification method:** Role and closure tests
- **Related tests/evidence:** docs/governance/PROCESS_INVENTORY.md
- **Affected domains:** workforce
- **Faruk must confirm later:** no

## PP-COMM-001

- **Normative statement:** Official operational communications shall occur in or be captured by PerchPoint with consent, delivery, linkage, and attribution.
- **Rationale:** Eliminate personal-channel record loss.
- **Source:** Directive §4.1 and §4.16; Platform Vision pp. 1–2 corroborates
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann and counsel
- **Status:** accepted
- **Assumptions:** Direct calls may be rapidly summarized.
- **Dependencies:** Communication provider/retention
- **Risks:** Missing commitments/privacy
- **Verification method:** Delivery/consent/access tests
- **Related tests/evidence:** docs/governance/COMMUNICATION_POLICY.md
- **Affected domains:** communications,security
- **Faruk must confirm later:** yes

## PP-COMM-002

- **Normative statement:** Routine delegated work shall not individually notify Faruk.
- **Rationale:** Recover owner attention.
- **Source:** Directive §4.16
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk and Ann
- **Status:** accepted
- **Assumptions:** Critical threats escalate immediately.
- **Dependencies:** Notification policy/jobs
- **Risks:** Alert fatigue/missed emergencies
- **Verification method:** Priority/escalation tests
- **Related tests/evidence:** docs/governance/COMMUNICATION_POLICY.md
- **Affected domains:** communications,operations
- **Faruk must confirm later:** yes

## PP-DATA-001

- **Normative statement:** Source imports shall stage, validate, deduplicate, preserve lineage, reconcile control totals, and perform no silent overwrite.
- **Rationale:** Make Innago retirement safe.
- **Source:** Directive §4.1 and §6.3
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan and accounting specialist
- **Status:** accepted
- **Assumptions:** Real import is later phase.
- **Dependencies:** Migration mapping/rollback
- **Risks:** Corruption/duplicate balances
- **Verification method:** Dry-run/conflict/reconciliation tests
- **Related tests/evidence:** docs/governance/SYSTEM_OF_RECORD_MAP.md
- **Affected domains:** data,migration
- **Faruk must confirm later:** yes

## PP-DATA-002

- **Normative statement:** All development data shall remain visibly synthetic, production-shaped, and deeply interconnected.
- **Rationale:** Validate realistic invariants without PII.
- **Source:** Directive §4.18
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Synthetic legal documents are non-executable.
- **Dependencies:** Factories/scenario catalog
- **Risks:** Mock leakage
- **Verification method:** Contamination/scenario tests
- **Related tests/evidence:** contracts/fixtures/portfolio.json
- **Affected domains:** data,testing
- **Faruk must confirm later:** no

## PP-SEC-001

- **Normative statement:** Secrets, raw card credentials, and unnecessary sensitive provider results shall not be committed, logged, or exposed to clients.
- **Rationale:** Reduce breach impact.
- **Source:** Directive §5 and §6.5
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Provider tokens remain server-side.
- **Dependencies:** Secret management/redaction
- **Risks:** Credential/PII exposure
- **Verification method:** Secret/payload/log review
- **Related tests/evidence:** docs/audits/PHASE_0_CURSOR_AUDIT.md
- **Affected domains:** security,privacy
- **Faruk must confirm later:** no

## PP-SEC-002

- **Normative statement:** Qualified counsel shall approve regulated housing, lease, fee, recording, retention, and new-state policy before activation.
- **Rationale:** Avoid unauthorized legal conclusions.
- **Source:** Directive §5
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Qualified counsel
- **Status:** accepted
- **Assumptions:** Governance may document gates.
- **Dependencies:** Counsel engagement/versioned policies
- **Risks:** Legal exposure
- **Verification method:** Activation-gate review
- **Related tests/evidence:** docs/governance/ACCEPTANCE_AUTHORITY.md
- **Affected domains:** security,legal
- **Faruk must confirm later:** yes

## PP-PROV-001

- **Normative statement:** Providers shall be selected by weighted total value, security, reliability, API completeness, and exit cost rather than sticker price.
- **Rationale:** Control operational and lock-in risk.
- **Source:** Directive §4.19
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk and Nathan
- **Status:** accepted
- **Assumptions:** No activation in Phase 1.
- **Dependencies:** Provider evidence
- **Risks:** Poor fit/lock-in
- **Verification method:** Scored evaluation
- **Related tests/evidence:** docs/governance/PROVIDER_EVALUATION_FRAMEWORK.md
- **Affected domains:** providers
- **Faruk must confirm later:** yes

## PP-PROV-002

- **Normative statement:** Every external operation shall use replaceable adapters, idempotency, durable event handling, retries, and visible exceptions.
- **Rationale:** Fail safely under outages/replays.
- **Source:** Directive §12 and roadmap §3; Platform Vision pp. 1–2 corroborates
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Implementation is later phase.
- **Dependencies:** Queues/inbox/outbox
- **Risks:** Duplicate/lost effects
- **Verification method:** Replay/outage tests
- **Related tests/evidence:** backend/foundation/integrations.py
- **Affected domains:** providers,reliability
- **Faruk must confirm later:** no

## PP-NFR-001

- **Normative statement:** Critical journeys shall provide responsive, keyboard-accessible loading, empty, error, denied, and unavailable states.
- **Rationale:** Make operations usable and honest.
- **Source:** Directive §6.3 and §12
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan and operational users
- **Status:** accepted
- **Assumptions:** WCAG requires manual validation.
- **Dependencies:** Design system/browser matrix
- **Risks:** Exclusion/task failure
- **Verification method:** Axe plus manual AT/keyboard tests
- **Related tests/evidence:** docs/phase0/VERIFICATION.md
- **Affected domains:** accessibility,reliability
- **Faruk must confirm later:** no

## PP-NFR-002

- **Normative statement:** Builds, generation, migrations, tests, rollback, and restore shall be reproducible from canonical source.
- **Rationale:** Enable safe delivery and recovery.
- **Source:** Directive §3 and §6.4
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Current frontend lacks a lockfile/CI.
- **Dependencies:** Runtime pins/CI/backups
- **Risks:** Non-reproducible release
- **Verification method:** Clean environment and restore drill
- **Related tests/evidence:** docs/audits/PHASE_0_CURSOR_AUDIT.md
- **Affected domains:** reliability,delivery
- **Faruk must confirm later:** no

## PP-ACCEPT-001

- **Normative statement:** Every claim shall record source, code, test, command, observation, verdict, severity, remediation, and phase.
- **Rationale:** Evidence over assertion.
- **Source:** Directive §6.3
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Deferred is a valid honest verdict.
- **Dependencies:** Audit evidence
- **Risks:** False completion
- **Verification method:** Audit matrix validation
- **Related tests/evidence:** docs/audits/PHASE_0_CURSOR_AUDIT.md
- **Affected domains:** acceptance
- **Faruk must confirm later:** no

## PP-ACCEPT-002

- **Normative statement:** Acceptance shall remain separated among technical, business, operational, accounting, maintenance, and legal authorities.
- **Rationale:** Prevent invalid sign-off.
- **Source:** Directive §8.2
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Named authority by domain
- **Status:** accepted
- **Assumptions:** Provisional acceptance is explicit.
- **Dependencies:** RACI/open decisions
- **Risks:** Unauthorized acceptance
- **Verification method:** Authority consistency review
- **Related tests/evidence:** docs/governance/ACCEPTANCE_AUTHORITY.md
- **Affected domains:** acceptance,governance
- **Faruk must confirm later:** yes

## PP-PROD-003

- **Normative statement:** HawkVision's website shall be the exclusive target listing and application destination.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.1/§4.3; Platform Vision p. 1 corroborates website scope, not exclusivity
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Listing-boundary scan
- **Related tests/evidence:** docs/product/SYSTEM_REPLACEMENT_BOUNDARY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-PROD-004

- **Normative statement:** Faruk's command center shall prioritize material threats, reserved decisions, deadlines, patterns, portfolio opportunity, and delegated-work evidence.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.15; Platform Vision p. 2 corroborates owner metrics
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Owner command-center acceptance cases
- **Related tests/evidence:** docs/governance/CAPABILITY_REGISTER.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-PROD-005

- **Normative statement:** Ann's operations center shall provide organized queues, saved views, filters, search, workload, exceptions, approvals, and drill-down.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.15
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Operations-center acceptance cases
- **Related tests/evidence:** docs/governance/CAPABILITY_REGISTER.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-PROD-006

- **Normative statement:** Nathan shall have a distinct platform-administration workspace separate from operational authority.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.15
- **Business owner:** Nathan
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Workspace and privilege-separation tests
- **Related tests/evidence:** docs/governance/RACI.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-PROD-007

- **Normative statement:** PerchPoint shall provide global search across authorized operational records.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.15 and target operating model
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Authorized global-search acceptance tests
- **Related tests/evidence:** docs/governance/PROCESS_INVENTORY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-GOV-003

- **Normative statement:** Production repositories, provider accounts, billing, and recovery ownership shall belong to HawkVision with individual administrative access.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.4
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Account-ownership readiness review
- **Related tests/evidence:** docs/product/PRODUCT_CONSTITUTION.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-GOV-004

- **Normative statement:** Support, incident, platform-management, and business-management responsibilities shall be explicitly assigned.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §3.3/§4.5
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk and Nathan
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** RACI and runbook review
- **Related tests/evidence:** docs/governance/RACI.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-GOV-005

- **Normative statement:** Phase 1 shall not implement or activate Phase 2 production capabilities.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §9
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Changed-file and prohibited-capability scan
- **Related tests/evidence:** docs/plans/PHASE_1_IMPLEMENTATION_PLAN.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-GOV-006

- **Normative statement:** Canonical governed content shall use PerchPoint, HawkVision Homes, Faruk Atmaca, Nathan Doss, and Ann Springer as approved names.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §3.1
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Canonical-name scan
- **Related tests/evidence:** docs/product/TERMINOLOGY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-AUTH-003

- **Normative statement:** Faruk-reserved decisions shall require Faruk or an explicit valid delegation where delegation is permitted.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.6
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Reserved-decision authorization tests
- **Related tests/evidence:** docs/governance/APPROVAL_AND_DELEGATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-AUTH-004

- **Normative statement:** All capital projects shall require Faruk's approval.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.6
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Capital-project denial and approval tests
- **Related tests/evidence:** docs/governance/APPROVAL_AND_DELEGATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-AUTH-005

- **Normative statement:** Ann shall have broad operational authority within policy but no developer, secret, raw-database, deployment, or audit-deletion authority.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.7
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk and Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Positive operations and negative infrastructure tests
- **Related tests/evidence:** docs/governance/RACI.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-AUTH-006

- **Normative statement:** Nathan shall control architecture, integrations, security, releases, and approved technical configuration.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.8
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Technical-authority review
- **Related tests/evidence:** docs/governance/RACI.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-AUTH-007

- **Normative statement:** Nathan's operational actions shall remain limited to separately granted HawkVision authority.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.5/§4.8
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Operational role-assignment tests
- **Related tests/evidence:** docs/governance/RACI.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-AUTH-008

- **Normative statement:** Technical administration and operational business authority shall be represented as separate assignments.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.5
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk and Nathan
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Privilege-separation tests
- **Related tests/evidence:** docs/governance/RACI.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-AUTH-009

- **Normative statement:** PerchPoint shall not use a shared master password, code, or implicit super-role.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.9
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Credential and role-model scan
- **Related tests/evidence:** docs/governance/APPROVAL_AND_DELEGATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-AUTH-010

- **Normative statement:** Each adult resident shall use an individually authenticated account linked to a household.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.13
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Household attribution and shared-login denial tests
- **Related tests/evidence:** docs/product/TERMINOLOGY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-AUTH-011

- **Normative statement:** Production individual accounts and privileged MFA shall be required before production activation.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §5/§9 and roadmap Phase 6
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Production identity activation gate
- **Related tests/evidence:** docs/governance/DEPENDENCY_REGISTER.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-PROP-003

- **Normative statement:** The initial operating geography shall be Greater Cincinnati.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §3.1
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Business-scope review
- **Related tests/evidence:** docs/product/PRODUCT_CONSTITUTION.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-PROP-004

- **Normative statement:** Core identity, jurisdiction, organization, property, money, and policy models shall support additional cities and states without redesign.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §3.1
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Multi-jurisdiction architecture review
- **Related tests/evidence:** docs/governance/SYSTEM_OF_RECORD_MAP.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-PROP-005

- **Normative statement:** Each property record shall support ownership, jurisdiction, structure, parties, leases, balances, work, assets, documents, utilities, costs, availability, communications, decisions, tasks, approvals, exceptions, and audit history.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.14; Platform Vision p. 2 corroborates
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan and Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Property-record coverage tests
- **Related tests/evidence:** docs/governance/CAPABILITY_REGISTER.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-LEASE-003

- **Normative statement:** The party model shall distinguish applicants, co-applicants, guarantors, occupants, business applicants, and authorized representatives.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.13; Platform Vision p. 1 corroborates application-party detail
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann and counsel
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Party-role relationship tests
- **Related tests/evidence:** docs/product/TERMINOLOGY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-FIN-003

- **Normative statement:** Stripe shall be the primary direction for eligible ACH, card, autopay, deposit, fee, and refund processing.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.2; Platform Vision p. 2 corroborates
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk and accounting specialist
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Provider-evaluation and activation gate
- **Related tests/evidence:** docs/governance/PAYMENT_CHANNEL_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-FIN-004

- **Normative statement:** Manual payment exceptions shall record payer, recipient, amount, time, property, household, evidence, recorder, approval, deposit, match, and reconciliation states.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.2
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Accounting specialist
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Required-field and reconciliation tests
- **Related tests/evidence:** docs/governance/PAYMENT_CHANNEL_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-FIN-005

- **Normative statement:** PerchPoint shall provide operational accounting while formal accounting software retains GL, tax, close, and finalized-statement authority.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §3.3/§4.2; Platform Vision p. 2 corroborates ledger separation
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Accounting specialist
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Accounting-boundary review
- **Related tests/evidence:** docs/governance/SYSTEM_OF_RECORD_MAP.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-FIN-006

- **Normative statement:** Related transactions shall be aggregated and shall not be split to evade approval thresholds.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.6
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Aggregation-window and split-attempt tests
- **Related tests/evidence:** docs/governance/APPROVAL_AND_DELEGATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-MAINT-003

- **Normative statement:** A technician's original recommendation shall remain immutable when management selects another remedy.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.10
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Maintenance users and Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Recommendation immutability tests
- **Related tests/evidence:** docs/governance/MAINTENANCE_RECOMMENDATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-MAINT-004

- **Normative statement:** A management override shall preserve its reason, decision maker, risk acknowledgment, and technician review when practical.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.10
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann and maintenance users
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Override attribution tests
- **Related tests/evidence:** docs/governance/MAINTENANCE_RECOMMENDATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-MAINT-005

- **Normative statement:** A materially different maintenance selection shall record compatibility confirmation and cost comparison.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.10
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann and maintenance users
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Compatibility and cost-field tests
- **Related tests/evidence:** docs/governance/MAINTENANCE_RECOMMENDATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-MAINT-006

- **Normative statement:** PerchPoint shall measure incorrect parts, returns, duplicate trips, delays, rework, repeat failures, temporary fixes, disruption, and wasted labor.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.10
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Metric source-event review
- **Related tests/evidence:** docs/governance/MAINTENANCE_RECOMMENDATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-MAINT-007

- **Normative statement:** Emergency authority shall be limited to reasonable stabilization, recorded authorization, immediate Faruk notice, a provisional $2,500 Ann limit, and post-event review.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.11
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk
- **Status:** provisional
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Emergency boundary and post-review tests
- **Related tests/evidence:** docs/governance/APPROVAL_AND_DELEGATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-MAINT-008

- **Normative statement:** A dedicated maintenance mobile application shall remain outside the core Phase 0/1 program and require later approval after core completion.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §9
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk and Nathan
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Phase-boundary scan
- **Related tests/evidence:** docs/plans/PHASE_1_IMPLEMENTATION_PLAN.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-WORK-003

- **Normative statement:** Assigned work shall require role-appropriate completion evidence before closure.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.12/§4.17; Platform Vision p. 2 corroborates completion evidence
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Evidence-completeness closure tests
- **Related tests/evidence:** docs/governance/PROCESS_INVENTORY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-WORK-004

- **Normative statement:** Turns, cleaning, major, repeat, high-cost, safety, and disputed work shall require verification and support reopening or rework.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.17
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann and maintenance users
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Inspection, reopen, and rework tests
- **Related tests/evidence:** docs/governance/MAINTENANCE_RECOMMENDATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-WORK-005

- **Normative statement:** Staff and vendor scorecards shall use role-appropriate evidence for coaching and decisions without autonomous sensitive employment conclusions.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.17
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk and Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Metric lineage and prohibited-conclusion review
- **Related tests/evidence:** docs/governance/CAPABILITY_REGISTER.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-COMM-003

- **Normative statement:** Material results, commitments, and follow-up from direct calls shall be rapidly recorded in PerchPoint.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.1
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Call-outcome completeness tests
- **Related tests/evidence:** docs/governance/COMMUNICATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-COMM-004

- **Normative statement:** Notifications shall use critical, decision-required, action-required, and informational levels.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.16
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Notification classification tests
- **Related tests/evidence:** docs/governance/COMMUNICATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-COMM-005

- **Normative statement:** Overdue work shall escalate from assignee to supervisor and reach Faruk only when material or unresolved.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.16
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk and Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Escalation-order tests
- **Related tests/evidence:** docs/governance/COMMUNICATION_POLICY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-DATA-003

- **Normative statement:** Innago shall be migrated, reconciled, archived read-only, and retired rather than retained as a long-term operating system.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.1
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk and accounting specialist
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Migration reconciliation and retirement gate
- **Related tests/evidence:** docs/product/SYSTEM_REPLACEMENT_BOUNDARY.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-DATA-004

- **Normative statement:** PerchPoint shall maintain a unified attributable activity history across communications, decisions, tasks, approvals, exceptions, and material state changes.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §3.3/§4.14; Platform Vision pp. 1–2 corroborates
- **Business owner:** Ann
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan and Ann
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Cross-domain history tests
- **Related tests/evidence:** docs/governance/SYSTEM_OF_RECORD_MAP.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-SEC-003

- **Normative statement:** Synthetic development data shall contain no real PII and shall remain visibly synthetic.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §4.18
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** PII and synthetic-marker scans
- **Related tests/evidence:** docs/governance/RISK_REGISTER.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no

## PP-SEC-004

- **Normative statement:** AI shall not autonomously make housing, legal, spending, lease, payment, ledger, capital-project, or dangerous-maintenance decisions.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Directive §5 and roadmap Phase 27; Platform Vision p. 2 corroborates human-approved AI actions
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Faruk and qualified specialists
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Prohibited-tool/action tests
- **Related tests/evidence:** docs/product/PRODUCT_CONSTITUTION.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** yes

## PP-ACCEPT-003

- **Normative statement:** Every material approved decision shall have a stable decision ID mapped to requirements, policy, owner, authority, verification, evidence, and status.
- **Rationale:** Preserve an approved, independently verifiable operating decision.
- **Source:** Closure directive §7
- **Business owner:** Faruk
- **Technical owner:** Nathan
- **Acceptance authority:** Nathan
- **Status:** accepted
- **Assumptions:** Later-phase implementation remains separately gated.
- **Dependencies:** Approved domain design and acceptance evidence
- **Risks:** Policy drift or unauthorized implementation
- **Verification method:** Decision-reference validation
- **Related tests/evidence:** docs/governance/APPROVED_DECISION_REGISTER.md
- **Affected domains:** governance,operations
- **Faruk must confirm later:** no
