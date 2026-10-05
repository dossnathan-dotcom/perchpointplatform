# ADR-P6-002 — Server-custodied sessions

Status: accepted for Phase 6 local design; operational evidence pending.

## Context

Q81–Q90 require narrow secure cookies, no browser refresh-token storage, role-appropriate
timeouts/concurrency, user revocation, risk response, and stale-authority UX.

## Decision

Custody provider refresh tokens encrypted in PostgreSQL and give the browser an opaque random
HttpOnly session cookie. Bind unsafe requests to an HMAC CSRF token and allowed origin. Resolve
current identity/membership on each protected request. Apply idle/absolute/concurrency limits
and revoke on reset, recovery, factor removal, suspension, membership/role change, explicit
action, or refresh reuse.

## Consequences

Browser compromise exposes less provider material, and revocation is immediate at the
application boundary. The application must protect/rotate encryption keys, keep database
availability, test CSRF/origin behavior, and prove timeout/recovery behavior in browsers.

Source: Q81–Q90. Owner/acceptance: Nathan. Requirements: `PP-AUTH-001`, `PP-AUTH-011`,
`PP-SEC-001`, `PP-NFR-001`, `PP-NFR-002`.
