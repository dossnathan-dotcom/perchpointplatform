# Secret inventory

Names only. No values belong in this file.

| Variable | Purpose | Service | Environments | Class | Creation | Rotation | Injection | Status |
|---|---|---|---|---|---|---|---|---|
| PHASE2_ADMIN_URL | Admin database URL | API migrate | local, ci, later staging | Secret | Nathan | On exposure | Env, not git | Local and CI use disposable values |
| PHASE2_MIGRATOR_URL | Migration role URL | Alembic | local, ci, later staging | Secret | Nathan | On exposure | Env, not git | Local and CI use disposable values |
| PHASE2_RUNTIME_URL | Runtime role URL | API, worker | local, ci, later staging | Secret | Nathan | On exposure | Env, not git | Local and CI use disposable values |
| PHASE2_JWT_SECRET | Local session signing | API | local, ci | Secret | Nathan | On exposure | Env, not git | Rejected for staging and production |
| PHASE2_DEV_PASSWORD | Synthetic local password | API | local, ci | Secret | Nathan | On exposure | Env, not git | Rejected outside local development |
| PHASE2_WEBHOOK_SECRET | Synthetic inbox HMAC | API | local, ci | Secret | Nathan | On exposure | Env, not git | Required locally. Absent for hosted |
| PHASE2_LOCAL_AUTH | Development auth switch | API | local | Non-secret flag | Nathan | n/a | Env | Must be development locally. Rejected for staging and production |
| PHASE3_ENVIRONMENT | Environment name | API, web | all | Non-secret | Nathan | n/a | Env | local, test, ci, staging, or production |
| SENTRY_DSN | Backend error transport | API, worker | later staging | Secret | Nathan | On exposure | Env, not git | Unset. Telemetry stays off |
| REACT_APP_SENTRY_DSN | Browser error transport | Web | later staging | Public DSN | Nathan | On exposure | Build env | Unset. SDK stays idle |
| SENTRY_AUTH_TOKEN | Source-map upload | CI, later | later staging | Secret | Nathan | On exposure | GitHub environment | Not created. Upload stays inactive |
| PHASE3_COMMIT | Safe release SHA | API | ci, later staging | Non-secret | CI | Each build | Env | Optional |

Revocation: remove the value from the environment or vault, restart the process, and confirm startup no longer loads it. Do not commit the old or new value.
