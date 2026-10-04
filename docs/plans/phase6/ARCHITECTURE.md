# Phase 6 architecture

## Identity provider boundary

Local development uses Supabase Auth/GoTrue `v2.189.0` (`sha256:385184459f57569c54c25209f51f3b2be99ddd7c4ce9e3555b5d3eea8447b7cf`). Mailpit receives synthetic mail. GoTrue owns its `auth` schema in the separate `perchpoint_auth` database. Alembic does not migrate that schema.

GoTrue verifies passwords and TOTP factors. PerchPoint verifies the provider access token (issuer `perchpoint-local-auth`, audience `authenticated`, signature, expiry, and subject) and maps that immutable subject onto `identity_accounts`. The browser receives only the HttpOnly `pp_session` cookie. Provider refresh tokens stay encrypted in `identity_sessions` and are never returned to the client.

Migration `0014_phase6_provider` removes `identity_factors.secret_ciphertext`. PerchPoint stores the provider factor id only. The earlier encrypted seed path in `0012` is retired for new factors and any synthetic rows were deleted.

Business roles, scopes, and approvals are not read from provider user metadata.

## What remains outside this boundary

Hosted Supabase is not configured. Production startup refuses a missing provider URL or a disposable provider secret. The development JWT remains available only when `PHASE6_ALLOW_DEV_JWT=1`.
