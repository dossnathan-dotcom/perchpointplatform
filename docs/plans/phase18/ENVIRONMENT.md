# Phase 18 environment profiles

Passwords, tokens, and connection strings stay in ignored local configuration. This page records endpoints and which suite owns each profile. SMTP delivery and the Mailpit HTTP retrieval endpoint are different ports.

## Local presentation demo

Compose project `perchpoint-phase8-accept`. Host Postgres `127.0.0.1:54339`, database `perchpoint_phase2`. GoTrue `127.0.0.1:9998`. Mailpit HTTP `127.0.0.1:8125`. Host SMTP mapping `127.0.0.1:1125` to container port 1025. MinIO `127.0.0.1:9100`. ClamAV `127.0.0.1:3410`. Frontend origin `http://127.0.0.1:3000`. API origin `http://127.0.0.1:8000`. `DEMO_MODE=1` with the ignored demo configuration. Worker entry point `python -m perchpoint.phase17_worker`. Migration head for this phase is `0064_phase18_return_completion`, descending from `0063_phase18_required_return`, `0062_phase18_resident_receipt`, and `0061_phase18_digital_receipts`.

## Dedicated phase acceptance

Disposable identities come from the test fixtures, not from a committed password file. Phase 17 browser coverage stays on `frontend/playwright.phase17.config.js`. The shared Playwright config ignores `phase17-.*` and `recovery-owner.spec.js`. Phase 18 assistance behavior is exercised by `python -m pytest tests/phase18/test_assistance.py -n 0`. `frontend/playwright.phase18.config.js` runs `phase18-.*` and is not part of the shared CI Playwright job. That job ignores those specs. Shared CI must not read `backend/.env.demo.local`.

## Shared Phase 6 CI

Workflow `.github/workflows/ci.yml` sets `PHASE6_SMTP_HOST=127.0.0.1`, `PHASE6_SMTP_PORT=1025`, and `PHASE6_MAILPIT_URL=http://127.0.0.1:8025`. It does not load `backend/.env.demo.local` and does not require the presentation cohort. `docker-compose.phase6.yml` publishes Mailpit HTTP `127.0.0.1:8025` and SMTP `127.0.0.1:1025`. Inherited listing, discovery, household, and ledger journeys stay in the shared Playwright job with the demo catalog disabled.

## Closeout and clean room

`docker-compose.phase6-closeout.yml` publishes Mailpit HTTP `127.0.0.1:8125` and SMTP `127.0.0.1:1125`. Inside that compose network, SMTP is port 1025 and Mailpit HTTP is `http://mailpit:8025`. Phase 17 clean-room and predecessor scripts remain pinned to `0060_phase17_grant_accept`. A Phase 18 clean room must migrate to the current head on its own disposable database and then tear it down. The long-lived database on `127.0.0.1:5432` is not acceptance evidence.

## Suite ownership

| Selection | Owner |
| --- | --- |
| `frontend/playwright.config.js` Chromium, Firefox, and WebKit, ignoring Phase 17 and recovery-owner specs | Shared CI browser job |
| `frontend/playwright.phase17.config.js` | Dedicated Phase 17 matrix, including the local recovery-owner spec |
| `tests/phase18/test_assistance.py` with `-n 0` | Phase 18 assistance, overlap, and worker recovery |
| `scripts/phase17_clean_room.py` and `scripts/phase17_predecessor.py` | Phase 17 only, head `0060_phase17_grant_accept` |
