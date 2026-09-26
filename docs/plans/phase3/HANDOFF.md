# Phase 3 external handoff

Phase 3 is not accepted. Complete these actions in order. Do not send passwords in chat.

1. Confirm whether `hawkvisionhomes.com` and `platform@hawkvisionhomes.com` are controlled by HawkVision. If not, Faruk and Nathan approve a dedicated transferable mailbox. Do not use Nathan's personal email.
2. Faruk creates or claims the billing owner for Render, Supabase, Sentry, and a company password vault. Enable MFA for Faruk and Nathan as separate users.
3. Invite Nathan as an individual administrator. Do not share one password. Ann receives no console or secrets access.
4. Choose an eastern-US region. Expected starting recurring cost, before usage spikes: Render staging web, API, and worker about 21 to 60 USD per month if services do not sleep; Supabase staging about 25 USD per month if PITR is required; Sentry team about 26 USD per month; previews extra per concurrent pull request. Production stays unprovisioned, so its cost is zero until a later approval.
5. After accounts exist, apply `deploy/render.yaml` only for staging, with auto-deploy still off until CI is green. Create a separate Supabase project for staging. Do not load production data.
6. Enable seven-day PITR on the future production database only after the paid plan is approved. Daily backup is not PITR and does not prove a one-hour RPO.
7. Store deploy identity in GitHub Environments. Prefer provider OIDC. If the host cannot use OIDC, create a scoped rotatable token in the vault, not a committed key.
8. Tell Cursor the account names and regions, not the secrets. Cursor will then rerun the staging migration, RLS, health, and browser checks on that same Phase 3 scope.

The GitHub repository `dossnathan-dotcom/perchpointplatform` is already public. This phase does not change that visibility. `main` had no branch protection at the start of Phase 3.
