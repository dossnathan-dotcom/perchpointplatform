# ADR-P2-001 Modular monolith

Status: proposed (pending Nathan approval)

## Context

Phase 0 is a FastAPI + React modular tree with Pydantic contracts and Mongo
intake. The complete product will grow leasing, payments, maintenance, and
more. Microservices would multiply undeclared consistency costs before the
reference kernel exists.

## Decision

Implement Phase 2 as a modular monolith: FastAPI domain packages with
enforceable boundaries and an eventual extraction path. One API process and
one separately runnable worker in this repository.

## Consequences

- Faster evidence for transactions, RLS, and outbox.
- Requires package discipline (`backend/perchpoint/domains/*`).
- Rejects Kafka, Kubernetes, and a general workflow platform for Phase 2.
