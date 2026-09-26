# Phase 3 acceptance

Classification: local engineering foundation accepted, with one external machine blocker. Hosted operational validation is owner-deferred under PP-DEC-059. Production readiness is blocked. Phase 4 is not started.

The Docker Desktop clean-room sequence was not executed. `docker` is not on PATH. Winget listed Docker Desktop, and a non-interactive reinstall stopped because the installer requires an administrator approval that this session cannot grant. Container build, Compose validation, and image scanning ran in GitHub Actions instead. That does not count as the local clean-room drill.

| Gate | Status | Evidence |
|---|---|---|
| 3A Environment and authority policy | implemented | This file, RUNBOOKS.md, and the Q1–Q174 register |
| 3B Hosted previews and health | owner-deferred | PP-DEC-059. Local `/api/v2/health/live`, `/api/v2/health/ready`, and `/api/v2/version` exist. No paid Render project is activated |
| 3C CI gates | verified for this commit's pull request workflow | Jobs `backend`, `frontend`, `browser`, `contracts`, `governance`, `secrets`, `supply-chain`, and `CodeQL` |
| 3D Secrets and backups | partial | Startup rejection tests and a completed Gitleaks scan. Hosted PITR and a company vault are owner-deferred |
| 3E Restore and rollback drills | partial | `scripts/phase3_restore_drill.py` restored 3 synthetic rows, rolled back a failed statement so `half_applied` was absent, left 0 disposable databases, and Elm Court remained 1. Hosted rollback is owner-deferred |
| 3F Reproducible staging | owner-deferred for hosted staging | Compose and Dockerfiles are in the repository. A local Docker engine is required before the clean-room run can be marked passed |

## Second review

Reviewed on this branch after the CI dependency, driver, seed, and accessibility repairs. Findings that were in repository scope were corrected before this record: supported requirements no longer install the private Emergent packages, CI installs `backend/requirements.txt`, database URLs use psycopg 3, the backend job seeds before pytest, and the environment notice sits inside the public header landmark. No high or medium repository defect from that review remains open. Hosted staging, PITR, a company vault, and a second human reviewer remain externally blocked. This review is not Ann's operational acceptance and not Faruk's business acceptance.

Phase 3 does not authorize production, real tenant data, payments, screening, or Phase 4.

## Closure review

Three review passes were applied to the Phase 3 branch before this record.

Architecture. API startup does not migrate. Migration and seed are one-shot Compose services. Staging and production reject local-development auth and disposable credential markers. The worker claims once and exits. PostgreSQL is published only on loopback port 54329.

Security. Images run as non-root. The Docker socket is not mounted into application services. The frontend image no longer ships the Create React App dependency tree or the Alpine nginx package that remained on a vulnerable revision. The static server loads the production build into an allowlist at startup, so a request path is never joined onto the filesystem and response headers are not copied from request values. Readiness failures do not return database error text. Sentry stays off without a DSN and strips request bodies and secret headers. Gitleaks and CodeQL remain in the pull request workflow.

Operations. Local backup and migration rollback drills remain the native script evidence. The clean-room Compose drill is externally blocked until Docker Desktop is started by an administrator. Hosted staging, hosted PITR, hosted restore measurement, and a live Sentry event are owner-deferred external operational evidence under PP-DEC-059. They are not passed gates.

Q57 allows documented technical sign-off after automated gates while Nathan is the sole engineer. A merge of the Phase 3 pull request after those gates are green is not production acceptance and not hosted operational acceptance.
