# Phase 6 architecture

## Decision summary

The approved design is a modular-monolith identity/access module with a replaceable
authentication-provider boundary and PostgreSQL as the current authorization authority. See
`adr/` for the individual decisions. This document describes current repository behavior; it
does not assert that acceptance tests have run.

## Identity and data separation

The model intentionally separates:

1. provider subject — immutable authentication-provider identifier;
2. `identity_accounts` — PerchPoint identity lifecycle and assurance record;
3. `accounts` — stable PerchPoint human/account record and contact address;
4. memberships and versioned role assignments — organization authority;
5. authorization scopes — resource/time/amount/decision bounds;
6. parties, households, occupancies, applications, leases, employment, vendor relationships,
   and worker assignments — business relationships that may confer narrowly defined access;
7. sessions/factors/recovery/contact history — authentication security state;
8. service principals/credentials — non-human identity, never a fake employee.

Email, phone, typed address, URL identifiers, provider metadata, and UI role previews are not
identity or authority keys. Relationship records are effective-dated, and historical records
remain reconstructable. Stable PerchPoint IDs remain separate from provider IDs.

## Authentication-provider boundary

Local development uses Supabase Auth/GoTrue `v2.189.0`
(`sha256:385184459f57569c54c25209f51f3b2be99ddd7c4ce9e3555b5d3eea8447b7cf`).
Mailpit receives synthetic mail. GoTrue owns the `auth` schema in separate database
`perchpoint_auth`; Alembic does not migrate that schema.

`backend/perchpoint/phase6_provider.py` is the adapter. GoTrue verifies passwords, recovery
links, and TOTP. PerchPoint verifies signature, issuer `perchpoint-local-auth`, audience
`authenticated`, expiry, subject, provider session, authentication methods, and AAL. It maps the
immutable subject to `identity_accounts`; email is synchronized contact data, not the key.

Provider metadata never defines roles, scopes, approvals, or business authority. Hosted
Supabase is not configured. Staging/production startup rejects missing or disposable provider
URLs/secrets, permissive origins/redirects, synthetic credentials, development JWTs, and
unseparated session/provider keys.

## Session security

`backend/perchpoint/phase6_identity.py` keeps provider refresh tokens encrypted at rest and
issues a random opaque `pp_session` cookie. The browser does not receive provider refresh
tokens. Cookies are HttpOnly, host-only by omission of `Domain`, `SameSite=Strict`, narrow to
`Path=/`, and `Secure` in staging/production. A separate readable CSRF token is bound by HMAC to
the server session; unsafe requests require the matching header plus allowed Origin/Referer.

Owner/platform-admin sessions use 15-minute idle and eight-hour absolute windows. Workforce and
vendor sessions use one-hour idle and 24-hour absolute windows. Applicant/resident sessions may
last 30 days. Concurrency is three workforce sessions or five external sessions. Password
reset, MFA removal/recovery, suspension, membership expiry, role change, explicit revocation,
and refresh-token reuse revoke affected sessions. Encryption/session-key rotation accepts old
keys while writing with the first current key.

## Authorization flow

Every protected route resolves the opaque session, verifies active identity and effective
membership, sets transaction-local actor/organization/request context, and asks the typed policy
module for a capability decision. Privileged commands require AAL2 and reauthentication no
older than five minutes. PostgreSQL forced RLS remains a second boundary. Client-supplied actor
or organization headers and frontend visibility are never authority.

Command authorization combines capability bundle, organization, resource relationship/scope,
state, AAL, delegation, amount, decision type, and separation-of-duties constraints. Decisions
and high-risk effects preserve request/actor/policy lineage where implemented.

## Migration map

- `0012` identity accounts, sessions, factors, recovery codes, invitations, delegations, access
  requests, service principals, and security events; forced RLS.
- `0013` invitation claim/accept bootstrap functions.
- `0014` provider custody, encrypted refresh sessions, capabilities/bundles/scopes, service
  credentials, privileged recovery, review campaigns/items, auth rate records.
- `0015` governance fields, contact history, delegation events, role-assignment history, bundle
  seed, recovery-code functions and indexes.
- `0016`, `0020`, `0029` invitation email binding, atomic activation, and acceptance-time
  reauthorization.
- `0017`, `0019` vendor/worker and household relationship isolation plus active-membership guard.
- `0018` authorized directory.
- `0021`, `0022` subject-based identity lookup and contact synchronization correction.
- `0023` access-review decisions.
- `0024` append-only delegation usage and related-transaction lineage.
- `0025` append-only maintenance recommendation/decision history.
- `0026` vendor-worker proposal and approved activation.
- `0027` required-MFA session recording.
- `0028` append-only identity lifecycle and revocation/transfer behavior.
- `0030` provider subject lookup for privileged recovery.

Migration SQL is canonical for database behavior; version files apply those scripts. Historical
migration failures are retained in `EXECUTION_LEDGER.md`.

## Known architectural limits

The typed policy still lives in process rather than a separately versioned policy service,
which is approved for this phase. Some UI fields are packed into existing API fields and some
listing APIs are absent; the UI states this explicitly. No external search engine, public
storage bucket, or shared cache authorization source is introduced. Hosted key management,
provider administration, operational monitoring, and restore proof remain external gates.

Requirements: `PP-AUTH-001`, `PP-AUTH-008`, `PP-AUTH-009`, `PP-AUTH-010`,
`PP-AUTH-011`, `PP-PROP-002`, `PP-DATA-004`, `PP-DATA-005`, `PP-DATA-006`,
`PP-DATA-007`, `PP-PROV-002`, `PP-SEC-001`, `PP-NFR-002`.
