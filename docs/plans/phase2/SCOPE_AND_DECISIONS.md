# Phase 2 Scope and Approved Decisions

Classification: planning. Implementation is not authorized by this document.

## Complete business objective

PerchPoint is HawkVision Homes' complete property operating platform, not a reduced
commercial MVP. Phases are evidence gates (`PP-PROD-001`, `PP-GOV-005`, CONFLICT-003).

The platform centralizes the public website and website-only listings; leasing inquiry
through move-in; resident accounts, payment operations, documents, service, and
communication; maintenance intake through verified completion; and staff queues,
approvals, delegation, visibility, and decision support.

It replaces Innago and fragmented operator workflows (`PP-DATA-003`). It does not
replace professional general-ledger accounting, tax, payroll, or the accountant
(`PP-FIN-005`). Specialized payment, screening, signing, email, SMS, and phone
providers may execute behind PerchPoint interfaces (`PP-PROV-002`).

Initial operating focus is Greater Cincinnati with approximately 100 properties and
more than 100 tenants across single-family, duplex, triplex, multifamily, commercial,
and mixed-use assets (`PP-PROP-001`, `PP-PROP-003`). Core identity must support
additional cities and states (`PP-PROP-004`).

Preserve the premium public design and denser professional internal experience from
the existing React application.

## Authority

| Person | Role | Phase 2 implication |
|---|---|---|
| Faruk Atmaca | Business owner; reserved decisions | Escalations above $1,200, all capital projects, and constitution-reserved items (`PP-AUTH-003`, `PP-FIN-002`, `PP-AUTH-004`). Not a default work queue. |
| Nathan Doss | Technical/platform owner and separately granted operator | Architecture, security, releases; operational writes only under separately granted HawkVision authority (`PP-AUTH-006`, `PP-AUTH-007`, `PP-AUTH-008`). |
| Ann Springer | Project/leasing and delegated operations | Routine operational authority within policy; no developer or secret authority (`PP-AUTH-005`). |
| Workers, cleaners, contractors, residents, applicants, accounting users | Scoped access | Assignment or household scope; no standing purchase authority (`PP-MAINT-002`, `PP-WORK-001`, `PP-WORK-002`). |

Overlapping property, rent-relative, parts-purchase, time-period, sensitivity, and
emergency aggregation rules in
`docs/governance/APPROVAL_AND_DELEGATION_POLICY.md` remain controlling. Do not
collapse them to a universal $1,200 test (`PP-FIN-006`, `PP-MAINT-007`).

The maintenance recommendation chain
(recommendation → management decision → ordered → delivered → installed →
verified or rework) remains required later (`PP-MAINT-001` through `PP-MAINT-006`).
The dedicated maintenance app remains post-core (`PP-MAINT-008`).

All development data remains synthetic (`PP-SEC-003`, `PP-DATA-002`). Production
readiness remains blocked.

## Phase 2 implements

A reusable reference kernel for one journey:

property → building → leasable space → published synthetic listing → inquiry →
staff triage → authorized activity history.

That kernel includes local PostgreSQL persistence, constraints, local synthetic
authentication on persistent routes, RLS, audit, outbox, a separately runnable
worker, a deterministic fake provider, and a signed synthetic webhook inbox.

Read-only task and approval examples may be shown. The complete approval engine,
financial ledger, screening, executed leases, maintenance/procurement, chat/IVR,
and dedicated maintenance app are out of scope.

## Phase 2 does not implement

Production identity/MFA/invitation/recovery; real providers or credentials;
Innago migration execution; document storage pipeline; payments or screening
orders; lease execution; CI/production infrastructure; Next.js rewrite; Zillow
or Facebook connectors; autonomous AI housing, legal, spending, or money
decisions (`PP-SEC-004`).

## Decision-to-requirement map

No new `PP-*` requirement IDs are added. Phase 2 planning decisions reuse the
Phase 1 register.

| Planning ID | Approved direction | Existing requirement IDs | Canonical policy | Owner |
|---|---|---|---|---|
| PP-P2-DEC-001 | Complete operating platform; phases are gates, not MVP cuts | PP-PROD-001, PP-GOV-005 | `docs/product/PRODUCT_CONSTITUTION.md` | Faruk / Nathan |
| PP-P2-DEC-002 | Website-only listings; syndication dormant | PP-PROD-003 | `docs/product/SYSTEM_REPLACEMENT_BOUNDARY.md` | Faruk |
| PP-P2-DEC-003 | Innago retired after migrate/reconcile/archive | PP-DATA-003 | `docs/product/SYSTEM_REPLACEMENT_BOUNDARY.md` | Faruk |
| PP-P2-DEC-004 | Operational accounting only | PP-FIN-005, PP-FIN-001 | `docs/governance/SYSTEM_OF_RECORD_MAP.md` | Accounting specialist |
| PP-P2-DEC-005 | Stripe-primary payments later; no live processor now | PP-FIN-003 | `docs/governance/PAYMENT_CHANNEL_POLICY.md` | Faruk |
| PP-P2-DEC-006 | Faruk reserved decisions and $1,200 / capital / aggregation / emergency rules | PP-AUTH-003, PP-AUTH-004, PP-FIN-002, PP-FIN-006, PP-MAINT-007 | `docs/governance/APPROVAL_AND_DELEGATION_POLICY.md` | Faruk |
| PP-P2-DEC-007 | Nathan dual-role separation | PP-AUTH-006, PP-AUTH-007, PP-AUTH-008 | `docs/governance/RACI.md` | Faruk / Nathan |
| PP-P2-DEC-008 | Ann operational, not developer | PP-AUTH-005 | `docs/governance/RACI.md` | Faruk / Ann |
| PP-P2-DEC-009 | Individual accounts; no shared passwords; default one primary portal account | PP-AUTH-010, PP-AUTH-009 | `docs/product/TERMINOLOGY.md` | Ann / Nathan |
| PP-P2-DEC-010 | Modular monolith + FastAPI domain services + PostgreSQL | PP-NFR-002, PP-AUTH-001 | `ARCHITECTURE.md` | Nathan |
| PP-P2-DEC-011 | Preserve React/CRA/CRACO; no automatic Next.js rewrite | PP-NFR-001 | `adr/ADR-P2-004-preserve-react.md` | Nathan |
| PP-P2-DEC-012 | One active HawkVision org; second synthetic org for isolation tests | PP-PROP-002, PP-SEC-003 | `ARCHITECTURE.md` | Nathan |
| PP-P2-DEC-013 | Physical containment distinct from ownership/occupancy relationships | PP-PROP-001, PP-PROP-005 | `ARCHITECTURE.md` | Nathan |
| PP-P2-DEC-014 | Preserve existing fixture UUIDs; provider IDs stay in mappings | PP-PROP-002 | `docs/phase0/CANONICAL-MODEL.md` | Nathan |
| PP-P2-DEC-015 | Exact money; no binary float money | PP-FIN-001 | `backend/foundation/base.py` `Money` | Nathan |
| PP-P2-DEC-016 | Explicit domain commands and guarded transitions | PP-DATA-004, PP-GOV-002 | `CONTRACTS.md` | Nathan |
| PP-P2-DEC-017 | One contract authoring authority; reuse Phase 0 generation | PP-NFR-002 | `adr/ADR-P2-005-contract-authoring.md` | Nathan |
| PP-P2-DEC-018 | Atomic command + audit + outbox; async external effects | PP-PROV-002, PP-DATA-004 | `adr/ADR-P2-003-command-outbox.md` | Nathan |
| PP-P2-DEC-019 | Local authenticated actors on persistent routes; preview is not auth | PP-AUTH-001 | `SECURITY.md` | Nathan |
| PP-P2-DEC-020 | Restricted runtime DB role; direct RLS tests | PP-AUTH-001, PP-SEC-001 | `adr/ADR-P2-002-postgresql-rls.md` | Nathan |
| PP-P2-DEC-021 | Reference journey only; later phases own full product surfaces | PP-GOV-005, PP-MAINT-008 | `IMPLEMENTATION_PLAN.md` | Nathan |
| PP-P2-DEC-022 | Yarn 1.22.22 lockfile retained | PP-NFR-002 | `frontend/package.json` | Nathan |
| PP-P2-DEC-023 | AI assist only with human review; no autonomous protected decisions | PP-SEC-004 | `docs/product/PRODUCT_CONSTITUTION.md` | Faruk |
| PP-P2-DEC-024 | Emergent may implement connected UI inside frozen contracts only | PP-GOV-002 | `EMERGENT_HANDOFF.md` | Nathan |
| PP-P2-DEC-025 | Nathan must approve this plan before application implementation | PP-ACCEPT-002, PP-GOV-002 | this package | Nathan |

## Unresolved material items

None of the following prevent planning. They prevent later activation in their domains.

- OD-001 / OD-002 legal names.
- OD-003 formal accounting platform.
- OD-004 provisional $2,500 emergency policy.
- OD-005 counsel-approved housing/legal policies.
- CONFLICT-004 accounting-platform detail.
- Production accounts, MFA, providers, and real portfolio data.

CONFLICT-008, CONFLICT-009, and CONFLICT-010 are recorded and resolved for planning
in `docs/source/provenance/SOURCE_CONFLICT_REGISTER.md`.
