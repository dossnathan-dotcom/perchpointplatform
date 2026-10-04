# Phase 6 delegation, approvals, workforce, and machines

## Delegation record and use

A delegation records organization, grantor, grantee, capability, resource type/ID, decision
types, amount ceiling, start/end, reason, approval reference, policy version, status, and
revocation history. The grantor must currently hold the capability, the grantee must be a
current organization member, self-delegation is denied, owner-reserved capabilities are denied,
and the default maximum duration is 30 days.

Delegation is non-transitive. Each use rechecks active dates/status, grantee, capability,
resource, decision type, amount, policy version, and current AAL/authorization. Use creates an
append-only `delegation_usage` row and event with actor/request lineage. Related transactions
sharing a key are aggregated so splitting cannot evade a ceiling. Expiry and revocation are
explicit history events.

Delegation policy changes are prospective, versioned, step-up protected, owner-approved for
material business authority, audited, tested, and communicated before activation. Nathan may
implement policy definitions but platform administration grants no business approval authority.

## Purchasing and owner reservations

Amounts are integer minor units. Ordinary non-capital maintenance spending up to and including
$1,200 may be approved by Ann/project/operations management only when within budget and not
otherwise reserved. Amounts above $1,200, decisions above the property's monthly rent, and all
capital projects require Faruk. Related transactions must be aggregated.

Immediate life-safety/property-preservation action is bounded to $1,200 for Ann. Above that,
Faruk is contacted. Unavoidable imminent harm is a separately documented act-and-notify event,
not fabricated ordinary approval. This narrower Phase 6 decision resolves the older provisional
$2,500 limit for Phase 6; see `CONFLICT-014`.

Owner-reserved decisions include capital projects, new leases and final applicant approval until
validly delegated, eviction/adverse action/termination/nonrenewal, material rent/fee/screening
policy, legal matters, material write-offs/unusual adjustments, insurance claims, delegation
policy, and production launch. Human and specialist gates remain mandatory.

Technicians and cleaners have no standing purchase authority. Diagnosis/recommendation remains
separate from spending approval. Maintenance recommendation, management decision, approved
solution, ordered product, installed solution, and variance reason are append-only event types;
the technician's original recommendation is not overwritten.

## Workforce and vendor lifecycle

Each workforce/contractor account maps to one real individual. Vendor companies never share an
account. A vendor administrator may propose a worker and bounded assignment, but HawkVision
operations approves activation and invitation. Approval binds company relationship, worker
role, optional property, start/end, purpose, and approver.

Vendor access requires:

1. active individual identity and current company membership;
2. active vendor relationship;
3. active assignment or separately approved service scope;
4. required capability, resource, and time window;
5. required MFA/AAL.

Technicians and cleaners receive only minimum tenant/property data needed for assigned work.
Quotes, purchase allowances, invoices, communications, and attachments remain assignment-
scoped. Attachments must pass normal private-storage scanning and audit controls. Access ends at
assignment completion/cancellation, membership expiry, access-end time, suspension, or
offboarding. Contractors cannot approve their own work, change orders, or invoices.

Access review covers privileged staff, vendors, workers, assignments, and material organization
changes. Offboarding transfers unresolved work and preserves immutable history.

## Service principals and workers

Non-human actors use named `service_principals`, not employee accounts. Principals are
organization/audience/capability scoped and `interactive=false`. Credentials are random,
displayed once, stored only as keyed verifiers, expire after one day in the current local
implementation, rotate by revoking active predecessors, and are revocable.

Background jobs must use minimally privileged principals and retain initiating human actor,
request, organization, policy, and causation lineage. Machine credentials cannot open
interactive portals. Webhooks must be signed, timestamped, idempotent, and replay-protected;
provider effects use durable inbox/outbox handling under `PP-PROV-002`.

The repository implements service-principal listing and one-time credential issue. Complete
worker/outbox/webhook adversarial evidence remains a required placeholder; no production
machine credential is authorized.

Requirements: `PP-AUTH-002`, `PP-AUTH-003`, `PP-AUTH-004`, `PP-AUTH-005`,
`PP-AUTH-006`, `PP-AUTH-007`, `PP-FIN-002`, `PP-FIN-006`, `PP-MAINT-002`,
`PP-MAINT-003`, `PP-MAINT-004`, `PP-MAINT-005`, `PP-MAINT-007`,
`PP-WORK-001`, `PP-WORK-002`, `PP-WORK-003`, `PP-PROV-002`, `PP-SEC-004`.
