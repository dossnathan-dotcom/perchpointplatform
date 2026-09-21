# Audit, domain events and outbox/inbox contracts

`AuditEvent` includes actor, effective role, delegated authority, action, resource type/ID, organization/ownership/property/building/unit/household/assignment scope, UTC timestamp, source channel, correlation ID, reason, material before/after state, IP/device metadata, result, approval/provider-event references and hash-chain fields.

Production immutability is a **storage guarantee still to implement**: append-only service identity, write-once/retention controls, no update/delete grants (including owner/admin), hash/signature verification and directly tested restore/export behavior. Frozen Pydantic models are only contract validation, not tamper-proof storage. Synthetic evaluations do not pretend to write a real immutable audit.

Sensitive record access must produce actor/record/time/purpose/action audit whether allowed, denied or failed. Preserve original actor and effective actor separately for any later emergency support or impersonation. Redact secrets and unnecessary personal data from diffs and IP/device logs.

## Domain events
Domains: payment, screening, lease, showing, communication, maintenance, approval, document, migration, account lifecycle.
`DomainEvent`: canonical aggregate ID/version, organization, event type, occurrence time, correlation/causation and reference-only payload IDs. Schema version belongs to the event record. Do not forward unfiltered provider objects as domain events.

## Future reliable side effects
`OutboxRecord`: event, idempotency key, pending/claimed/delivered/failed/dead-letter state, attempts, next retry, claim expiry, last error.
`ProviderEvent`: integration/org/provider event ID, receive time, signature-verification status, payload checksum, canonical event reference.
`InboxRecord`: provider event, deduplication key, received/validated/processed/rejected/failed state, processing time/failure.

Future transaction: commit canonical mutation + audit + outbox in one database transaction. Worker claims with bounded lease, delivers idempotently, records attempt/result, retries transient failures and exposes dead letters. Receiver verifies signature/timestamp, deduplicates `(integration, environment, provider_event_id)`, validates state transition and commits inbox/domain effects atomically. Replays must not duplicate ledger posts, screening orders, leases or communications.

No queue, worker, webhook receiver, retry scheduler, audit store or side-effect executor is installed. This prevents accidental direct-provider behavior from being mistaken for Phase 0 completion.