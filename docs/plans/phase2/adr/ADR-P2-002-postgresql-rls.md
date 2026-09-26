# ADR-P2-002 PostgreSQL and restricted runtime role

Status: proposed (pending Nathan approval)

## Context

Phase 0 documents that Pydantic is not a database constraint and that
PostgreSQL RLS is a future enforcement target. No SQLAlchemy, Alembic, or
PostgreSQL project files exist. Mongo remains the Phase 0 capture store.

## Decision

Use local PostgreSQL 16 or local Supabase for Phase 2 evidence. Propose
SQLAlchemy 2.0.x, Alembic, and psycopg 3 as the migration/runtime stack
without installing them in planning. Application and worker connections use
`perchpoint_runtime` with RLS and no bypass. Test policies as that role.

## Consequences

- SQLite/memory is not acceptance evidence.
- Mongo is not the reference system of record.
- Local DB availability is a stop condition for P2-02, not a skip.
- Production cloud accounts are not authorized.
