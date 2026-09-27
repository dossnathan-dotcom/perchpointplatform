# Phase 5 canonical data, documents, and search

Phase 5 extends the existing FastAPI and PostgreSQL monolith. Alembic revision `0008_phase5_closeout` follows `0007_phase5_canonical`. Supabase is the selected hosted platform and is not activated here.

## What is implemented

- Organization-scoped parties, exclusive effective-dated relationships, addresses, parcels, property facts, and property issues.
- Document metadata, immutable versions, quarantine, legal hold, disposition, and a 50 MB byte limit. Accepted bytes go to MinIO when `PHASE5_OBJECT_STORE=s3`. The filesystem directory is only a unit-test double and is not Phase 5 acceptance evidence.
- PostgreSQL search documents with full text and trigram matching. Authenticated search is forced through row-level security. Public search returns `classification = public` only. Saved searches are private until explicitly shared with the organization.
- CSV import staging, dry run, approval, apply, and rollback. Formula-like cells stay blocked.
- OCR and previews are derived artifacts. They do not replace original bytes. A missing scanner or OCR engine is a failure, not a clean result.
- Append-only audit remains insert-only for `perchpoint_runtime`. Digest verification compares hashes and does not rewrite history. Replay rebuilds the search projection from canonical rows.

## Audit shutdown finding

PostgreSQL logs `permission denied for table audit_events` when the runtime role attempts `UPDATE`. That denial is the immutability control. Container shutdown collects the database log after `backend/tests/phase2/test_reference_slice.py` proves the update fails. Phase 5 does not grant `UPDATE` or `DELETE` on `audit_events`. `has_table_privilege` remains false.

## Retention boundary

`retention_policies.provisional` must stay true. A legal hold blocks disposition. These defaults are not legal advice and are not production approval.

## Hosted staging

`scripts/phase5_staging_preflight.py` reports whether `SUPABASE_DB_URL`, `SUPABASE_STORAGE_URL`, and `SUPABASE_STORAGE_KEY` are present. It does not print values and it refuses a production-designated target. Absent names mean hosted validation is externally blocked.

## Local document services

The Compose profile `documents` starts MinIO and ClamAV. Official `minio/minio` images are no longer pullable from Docker Hub, so the pinned local image is `bitnamilegacy/minio:2025.7.23`. The API creates the private `perchpoint-documents` bucket idempotently. Unit tests set `PHASE5_OBJECT_STORE=filesystem` and `PHASE5_SCANNER_MODE=signature`; those doubles are not acceptance evidence. Live mode treats a missing or stopped scanner as `pending_scan` / unavailable, never as clean.

## Scale

`scripts/phase5_scale.py` loads a disposable database and drops it. It does not write the development seed.
