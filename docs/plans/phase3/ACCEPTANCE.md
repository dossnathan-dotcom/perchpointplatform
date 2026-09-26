# Phase 3 acceptance

Classification: Phase 3 local engineering foundation is definitively accepted with no remaining local machine blocker. Hosted operational validation remains owner-deferred under PP-DEC-059. Production readiness remains blocked. Phase 4 is not started.

Docker Desktop 4.92.0 is installed. After the required Windows reboot, the Linux engine starts. Client and engine are 29.8.0. Compose is v5.5.1. WSL is 2.7.14.0 with kernel 6.18.33.2-2. The engine reports Linux containers, overlayfs, 20 CPUs, and 16647888896 bytes of memory. `docker run --rm hello-world` succeeded. PostgreSQL in the disposable project is 16.15.

| Gate | Status | Evidence |
|---|---|---|
| 3A Environment and authority policy | implemented | This file, RUNBOOKS.md, and the Q1–Q174 register |
| 3B Hosted previews and health | owner-deferred | PP-DEC-059. Local `/api/v2/health/live`, `/api/v2/health/ready`, and `/api/v2/version` exist. No paid Render project is activated |
| 3C CI gates | verified for the closeout pull request workflow | Jobs `backend`, `frontend`, `browser`, `contracts`, `governance`, `secrets`, `supply-chain`, `containers`, and `CodeQL` |
| 3D Secrets and backups | local backup passed; hosted PITR owner-deferred | Compose `pg_dump` custom format was 88303 bytes. Restore into `perchpoint_phase3_restore`, including verification, took 412 ms. Elm Court remained 1, head remained `0006_activity_index`, and the restored copy showed 0 Elm Court rows with no organization context. The restore database and dump were removed. Hosted PITR and a company vault stay owner-deferred |
| 3E Restore and rollback drills | local rollback passed; hosted rollback owner-deferred | On disposable database `perchpoint_phase3_rollback`, Alembic moved `0006_activity_index` to `0005_listing_notes` and back to `0006_activity_index` in 1.842 s. The activity index was absent after the downgrade and present after the upgrade. A failed statement left `half_applied` absent. Seed remained idempotent and Elm Court stayed 1. The primary Compose database stayed at `0006_activity_index`. The disposable database was removed |
| 3F Reproducible staging | local Compose passed; hosted staging owner-deferred | Project `perchpoint-phase3` completed a clean-room run and a second bootstrap from empty volumes. Hosted Render staging is not activated |

## Second review

Reviewed on this branch after the CI dependency, driver, seed, and accessibility repairs. Findings that were in repository scope were corrected before this record: supported requirements no longer install the private Emergent packages, CI installs `backend/requirements.txt`, database URLs use psycopg 3, the backend job seeds before pytest, and the environment notice sits inside the public header landmark. No high or medium repository defect from that review remains open. Hosted staging, PITR, a company vault, and a second human reviewer remain externally blocked. This review is not Ann's operational acceptance and not Faruk's business acceptance.

Phase 3 does not authorize production, real tenant data, payments, screening, or Phase 4.

## Closure review

Three review passes were applied to the Phase 3 branch before this record.

Architecture. API startup does not migrate. Migration and seed are one-shot Compose services. Staging and production reject local-development auth and disposable credential markers. The worker claims once and exits. PostgreSQL is published only on loopback port 54329.

Security. Images run as non-root. The Docker socket is not mounted into application services. The frontend image no longer ships the Create React App dependency tree or the Alpine nginx package that remained on a vulnerable revision. The static server loads the production build into an allowlist at startup, so a request path is never joined onto the filesystem and response headers are not copied from request values. Readiness failures do not return database error text. Sentry stays off without a DSN and strips request bodies and secret headers. Gitleaks and CodeQL remain in the pull request workflow.

Operations. The disposable Compose project `perchpoint-phase3` migrated an empty database to `0006_activity_index`, seeded twice with unchanged counts, and kept Elm Court at 1. Twenty application tables force row-level security. `alembic_version` does not. `perchpoint_runtime` is not a superuser, not `BYPASSRLS`, and does not own the tables (`perchpoint_migrator` does). `perchpoint_definer` is `NOLOGIN` and `BYPASSRLS` so security-definer functions can run. Playwright against the Compose web server passed 15 tests in 37.5 s, including the accessibility and 320/768/1024/1440 checks. A smoke of 3 warmup and 20 measured calls on the synthetic seed stayed under a 34 ms p95, inside the Phase 2 500 ms ordinary-read ceiling. That smoke is not the Phase 2 design-mix benchmark. Local Trivy 0.58.1 reported `Total: 0 (HIGH: 0, CRITICAL: 0)` for both runtime images, with no ignore file. While PostgreSQL was stopped, liveness stayed `{"status":"live"}` and readiness returned `{"detail":{"status":"not_ready"}}`. The public page showed "Listings are unavailable" and zero listing cards. The browser recorded the intentional 500 as a failed resource load. Hosted staging, hosted PITR, hosted restore measurement, and a live Sentry event remain owner-deferred under PP-DEC-059.

Q57 allows documented technical sign-off after automated gates while Nathan is the sole engineer. A merge of the Phase 3 pull request after those gates are green is not production acceptance and not hosted operational acceptance.
