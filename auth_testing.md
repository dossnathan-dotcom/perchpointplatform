# PerchPoint Authentication Testing Boundary

## Current Phase 0 state

Authentication and authorization are **MOCKED** frontend-only role previews. `/api/auth/*` endpoints, password hashing, JWT cookies, refresh sessions, MFA, brute-force controls, protected database reads, and production role enforcement do not exist yet by design.

## Current checks

- Confirm each selected role opens its matching preview shell; switching roles is freely allowed because it is NOT authentication.
- Confirm all pages disclose Phase 0 demonstration status.
- Confirm no UI claims that production authentication, payment, screening, or protected document access is active.
- Confirm Owner and Platform Super Administrator boundaries are described separately.
- Confirm no password or actual account is required; obsolete demonstration passwords were removed. See `/app/memory/test_credentials.md`.

## Future production-auth gate

Before production auth testing begins, approve identity provider, password/MFA policy, session duration, cookie policy, brute-force policy, role matrix, delegated authority, sensitive-record audit requirements, retention rules, and recovery ownership.

Once implemented, test `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`, `/api/auth/refresh`, password reset, lockout, unique email indexes, cookie security, CORS/CSRF behavior, session revocation, role enforcement, and sensitive-access audit logging.