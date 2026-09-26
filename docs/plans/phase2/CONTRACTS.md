# Phase 2 Contracts

Classification: planning. Authoring authority remains `backend/foundation/` until
Nathan approves a split. Generated artifacts stay derived.

## Authoring and compatibility

| Artifact | Authority | Consumers |
|---|---|---|
| Pydantic models | `backend/foundation/` | FastAPI, export, tests |
| JSON Schema | `python -m foundation.export` → `contracts/generated/` | TypeScript generator, schema checks |
| TypeScript types | `frontend/scripts/generate-contract-types.cjs` | frontend |
| OpenAPI | FastAPI generation from the same models | humans, later clients |
| Fixtures | `backend/foundation/seeds.py` + exporter | UI, tests |

Do not manually maintain conflicting JSON Schema, Pydantic, TypeScript, or OpenAPI
copies (`PP-NFR-002`, `ADR-P2-005`).

Current contract version is `0.1.0` (`Record.schema_version`). Phase 2 additive
models and revised space-state fields use `0.2.0`. Compatibility classification
for P2-01:

- Additive: new `0.2.0` types in `backend/foundation/reference.py`, including
  relationship rows, separated space states, public inquiry, command envelopes,
  and read models. Phase 0 `Record.schema_version` stays `0.1.0`.
- Projection, not a rename: `Unit.status` remains. `project_phase0_unit_status`
  does not invent publication, condition, or legal facts.
- Unchanged write path: Phase 0 MongoDB remains the existing synthetic inquiry
  and maintenance capture only (`docs/phase0/LIMITATIONS.md`). P2-01 does not
  add a second HTTP writer. Future material commands such as `SubmitPublicInquiry`
  are the single intended authoritative write for that operation, and they are
  not routed or persisted in this package.
- Public inquiry contracts carry untrusted request metadata only. They do not
  include `TrustedActorContext`.

Compatibility rules:

- Additive optional fields and new event types are allowed in a minor bump.
- Renames, type changes, and enum removals require a documented compatibility
  mapping and dual-read window.
- Stable operation IDs are explicit FastAPI `operation_id` values.
- Unknown fields are rejected (`extra = "forbid"`) on write commands.
- Nullability is explicit. Enums are closed on write and documented on read.
- Numbers that are money use integer minor units. Other counts are integers.
- Generated-client checks remain `--check` on both export and TypeScript.

## REST shape

Use REST with explicit commands, events, and optimized read endpoints.

Proposed reference operations (persistent, authenticated, organization-scoped):

| Method | Path | Command / read | Notes |
|---|---|---|---|
| GET | `/api/v2/properties` | read | scoped list, never internal wholesale |
| GET | `/api/v2/properties/{id}` | read | includes buildings summary |
| GET | `/api/v2/spaces/{id}` | read | leasable space + current states |
| GET | `/api/v2/listings/{id}` | public or staff | published projection only on public |
| POST | `/api/v2/inquiries` | `SubmitInquiry` | idempotent command |
| POST | `/api/v2/inquiries/{id}/triage` | `TriageInquiry` | staff only |
| GET | `/api/v2/inquiries/{id}` | read | authorized history included |
| GET | `/api/v2/activity` | read | authorization-safe pagination |
| GET | `/api/v2/tasks` | read-only example | no engine |
| GET | `/api/v2/approvals` | read-only example | no engine |

Existing Phase 0 public routes (`/api/properties`, `/api/rentals`, `/api/leads`,
`/api/foundation*`) remain synthetic preview surfaces. They are not
authorization.

## Standard envelopes

```text
Error { code, message, correlation_id, details[] }
  details item { field?, reason }
```

Safe errors never echo secrets, raw provider payloads, or other tenants' IDs
beyond the caller's scope.

Every command and event carries:

- `correlation_id`
- `causation_id` (optional; command ID when originating)
- `actor_id` and `delegated_authority_id`
- `organization_id`
- `idempotency_key` + payload fingerprint on commands
- `expected_version` for optimistic concurrency
- `schema_version`

Pagination, search, counts, and related-record queries must apply the same
authorization predicate as list reads. Bulk operations are denied unless an
explicit later command exists. Long-running work uses durable jobs via outbox,
not request-held provider calls.

## Reference command transaction

Prove this sequence for `SubmitInquiry` and `TriageInquiry`:

1. Verify actor, organization membership, scope, and feature flag.
2. Begin a transaction using the restricted runtime database role.
3. Resolve the scoped idempotency key and payload fingerprint.
4. Check authoritative state, expected version, allowed transition, and locks.
5. Perform the domain mutation.
6. Write the material audit entry, outbox event, and stable command result in
   the same transaction.
7. Commit.
8. Deliver external effects asynchronously (fake provider / message sink only).

Do not call providers while the business transaction is open.

Cover: identical retry; concurrent retry; reused key with different payload;
in-progress command; stale `expected_version`; crash before response delivery.

## Events, inbox, and worker

Emit versioned domain events, not every column change. Proposed Phase 2 events:

- `property.space_states_projected.v1` (read-model helper; not a write API)
- `listing.published.v1` / `listing.withdrawn.v1`
- `inquiry.submitted.v1`
- `inquiry.triaged.v1`
- `activity.recorded.v1`

Delivery is at-least-once with idempotent consumers. Do not claim distributed
exactly-once.

Event payload minimum: aggregate ID, aggregate version, organization ID, event
ID, occurred_at (UTC), correlation_id, causation_id, schema_version, and
reference IDs only.

Worker requirements (`ADR-P2-003`):

- Claim with lease expiry.
- Two-worker competition must yield one winner.
- Bounded backoff and attempt counters.
- Crash recovery from `claimed` after lease expiry.
- Dead-letter ownership and visible exception.
- Success-before-acknowledgment: replay must be idempotent.

Use a deterministic fake provider and a signed synthetic webhook inbox to prove
authenticity, persistence, deduplication, retry, and out-of-order handling. No
live provider calls.

## Audit limitation

Audit is distinct from editable activity notes and ordinary delivery logs.
Append-only grants plus hash checkpoints provide bounded tamper evidence, not
administrator-proof immutability. A future independent checkpoint (separate
custody) is required before production audit reliance
(`docs/phase0/AUDIT-EVENTS.md`).

## Adapter ports

Define narrow interfaces now; select vendors later (`PP-PROV-001`):

| Port | Phase 2 implementation |
|---|---|
| Payments | disconnected / fake |
| Screening | disconnected |
| E-signature | disconnected |
| Communications / voice | message sink only |
| Email / SMS | message sink only |
| Calendar | disconnected |
| Accounting | disconnected |
| Storage | disconnected |
| AI | disconnected; no autonomous decisions |
| Listing distribution | dormant; no Zillow/Facebook connector |

The future maintenance app is another authorized client of the same backend,
not a second domain model (`PP-MAINT-008`).
