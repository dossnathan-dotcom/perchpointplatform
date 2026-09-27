# Phase 5 canonical data, documents, and search

Phase 5 extends the existing FastAPI and PostgreSQL monolith. Alembic revision `0007_phase5_canonical` is the only new migration authority. Supabase is the selected hosted platform and is not activated here.

## What is implemented

- Organization-scoped parties, exclusive effective-dated relationships, addresses, parcels, property facts, and property issues.
- Document metadata, immutable versions, quarantine, legal hold, and a 50 MB byte limit. Bytes go to the local object directory or to an S3 endpoint when `PHASE5_S3_ENDPOINT` is set.
- PostgreSQL search documents with full text and trigram matching. Authenticated search is forced through row-level security. Public search returns `classification = public` only.
- CSV import staging that blocks formula-like cells until an explicit apply.
- Append-only audit remains insert-only for `perchpoint_runtime`. Digest verification compares hashes and does not rewrite history.

## Audit shutdown finding

PostgreSQL logs `permission denied for table audit_events` when the runtime role attempts `UPDATE`. That denial is the immutability control. Container shutdown collects the database log after `backend/tests/phase2/test_reference_slice.py` proves the update fails. Phase 5 does not grant `UPDATE` or `DELETE` on `audit_events`. `has_table_privilege` remains false.

## Retention boundary

`retention_policies.provisional` must stay true. A legal hold blocks disposition. These defaults are not legal advice and are not production approval.

## Hosted staging

`scripts/phase5_staging_preflight.py` reports whether `SUPABASE_DB_URL`, `SUPABASE_STORAGE_URL`, and `SUPABASE_STORAGE_KEY` are present. It does not print values and it refuses a production-designated target. Absent names mean hosted validation is externally blocked.

## Local document services

The Compose profile `documents` starts MinIO and ClamAV. The default API path uses the local object directory and the in-process signature scanner so tests do not require those containers. Set `PHASE5_CLAMAV_HOST` only when ClamAV is actually running. An unavailable scanner quarantines the file instead of accepting it.

## Scale

`scripts/phase5_scale.py` loads a disposable database and drops it. It does not write the development seed.
