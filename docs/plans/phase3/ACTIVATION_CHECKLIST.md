# Hosted activation checklist

Use this only after Faruk authorizes billing and Nathan has a non-production secret channel. Do not run it during the current deferral.

1. Confirm the permanent mailbox is a HawkVision-controlled domain address.
2. Confirm separate Faruk and Nathan users with MFA. Ann receives no console access.
3. Select an eastern-US region and record the quoted monthly cost before creating resources.
4. Create a staging Supabase project. Enable seven-day PITR only on the paid plan Faruk approved.
5. Apply deploy/render.yaml for staging only. Leave auto-deploy off. Do not apply the production services.
6. Inject secrets by name from the secret inventory. Do not paste them into git, chat, or this file.
7. Run migrations as the one-shot migrate step. Do not start the API against an empty schema.
8. Confirm `/api/v2/health/live` and `/api/v2/health/ready` on the staging URL.
9. Restore a staging backup into a separate recovery database and record the duration.
10. Send one synthetic Sentry event with a staging DSN and record the event id. Then rotate any DSN that was exposed.
11. Keep production services unprovisioned until a later production approval.

Rollback is the previous staging revision, or a restore into a new database if the migration itself failed. Do not copy production data into staging.
