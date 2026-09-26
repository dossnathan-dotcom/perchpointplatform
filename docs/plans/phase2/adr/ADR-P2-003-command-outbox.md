# ADR-P2-003 Command transaction, outbox, and worker

Status: proposed (pending Nathan approval)

## Context

`AuditEvent`, `DomainEvent`, `OutboxRecord`, and `InboxRecord` already exist
as contracts. No worker or durable delivery is installed. Provider calls
inside a business transaction would couple latency and partial failure.

## Decision

Execute authorized domain commands in one PostgreSQL transaction that writes
the mutation, audit row, outbox event, and command result. Deliver external
effects asynchronously via a same-repo worker. Use at-least-once delivery and
idempotent consumers. Use a fake provider and signed synthetic inbox only.

## Consequences

- Crash and retry tests become mandatory.
- Exactly-once distributed delivery is not claimed.
- Hash-chained audit is bounded tamper evidence, not WORM.
