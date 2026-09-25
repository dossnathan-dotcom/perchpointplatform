# Phase 3 runbooks

These procedures are the enforceable local and repository controls. Hosted staging and production steps stay inactive until the handoff in [HANDOFF.md](HANDOFF.md) is complete. Do not paste secrets into chat or this file.

## Owners

- Technical rollback and recovery: Nathan.
- Business authorization for the first production launch: Faruk Atmaca.
- Staging and operations review: Ann Springer. Ann has no deployment or secrets access.
- Agents do not deploy production.

## Local setup

Native Windows PostgreSQL 16 remains supported. From `backend/`, with `backend/.env` copied from `.env.example` and filled locally:

```
python -m perchpoint.bootstrap
python -m perchpoint.seed
python -m uvicorn perchpoint.routes:create_app --factory --host 127.0.0.1 --port 8000
```

From `frontend/`: `corepack yarn install --frozen-lockfile --non-interactive` then `corepack yarn start`.

Docker Compose is the canonical reproducible path and uses port 54329 so it does not reinitialize a native PostgreSQL data directory:

```
docker compose up --build
```

Docker was not installed on the implementation machine, so this command is not yet a measured clean-room result.

## Deploy and rollback

1. CI on the pull request must pass.
2. Staging promotion requires Nathan's explicit approval. Production also requires Faruk's business approval.
3. Promote the digest or commit CI tested. If Render rebuilds from source, record that the artifact is not byte-identical.
4. Run migrations as a controlled predeploy step. Prefer expand-and-contract changes.
5. Call `/api/v2/health/live` and `/api/v2/health/ready` before traffic is marked healthy.
6. If health fails, stop the release and redeploy the previous commit. Nathan may do this before a business meeting and notify Faruk afterward.

## Backup and restore

Do not copy production data into development or preview. Do not overwrite `perchpoint_phase2`.

A synthetic restore uses two disposable databases, `pg_dump`, and `pg_restore` or SQL replay, then compares a control count. Backup creation without that comparison is not restore evidence. Hosted seven-day PITR is not enabled because no Supabase project exists.

## Secret rotation

Store recovery in a company vault. Never share one password. On suspected exposure, revoke the credential at the provider even if Git history is rewritten. Rotate high-value credentials at least every 90 days when that does not require downtime solely for the calendar. Production startup rejects `PHASE2_LOCAL_AUTH=development`, placeholder secrets, synthetic-credential flags, and permissive origins.

## Incidents

- SEV-1: security, payment integrity, or total outage. Immediate response and Faruk notification.
- SEV-2: major workflow or data risk. Acknowledge within 30 minutes during supported hours.
- SEV-3: degraded, with a workaround.
- SEV-4: minor or informational.
- SEV-1 and SEV-2 get a written blameless review.
- Technical alerts go to Nathan. Faruk gets business-critical or prolonged-outage escalation. Ann gets operational alerts only after those live workflows exist.
- The 99.9 percent monthly target applies after launch. It is not a measured production result.

## Provider outage

The synthetic worker does not deliver to an external provider. During a host outage, stop promotion, keep the last healthy commit, and retry only after readiness succeeds. No tenant traffic is in production.
