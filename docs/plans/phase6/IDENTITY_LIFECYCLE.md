# Phase 6 identity lifecycle

## Registration and invitations

Public listing and initial inquiry do not require an account. Applicant access begins through
application initiation or a secure relationship-bound invitation. Staff registration is
invitation-only. Authorized operations/leasing staff may invite approved external roles;
ordinary invitation routes cannot create owner or platform-administrator authority.

Invitations use random single-use tokens stored as keyed hashes. Staff invitations expire after
24 hours and external invitations after 72 hours. They bind email, organization, role/purpose,
inviter, expiration, and the relationship data available to the activation transaction.
Acceptance atomically rechecks token, email, current inviter authority, permitted role,
relationship, and activation state. Resend first creates a replacement and then invalidates the
old token. Delivery failure revokes the new invitation. Local delivery goes only to Mailpit and
synthetic recipients.

Activation creates the provider user, then atomically creates/links the PerchPoint identity and
membership. Failed PerchPoint activation attempts delete the newly created provider user where
possible. Acceptance does not sign the user in. Required MFA must be completed before protected
work.

## Identity continuity and relationships

An applicant becoming a resident keeps the same identity. Adult residents use individual
accounts; one primary account is the household default, and no shared password is permitted.
Guarantors are individual and obligation-scoped. Minors have no account by default. Former
residents retain only explicitly authorized historical access.

Identity, party, household, occupancy, membership, employment, vendor relationship, and worker
assignment remain separate effective-dated records. Typed addresses and contact fields never
create authority. One human workforce or contractor account represents one real individual.

## Password and sign-in policy

Passwords are 15–64 characters, permit paste/password managers, have no composition or periodic
rotation requirement, and reject a local common/compromised set. Authentication, recovery, and
reset responses are generic where account enumeration would be possible. Sign-in rate controls
track account, IP, and global attempts; IP/device/browser changes are risk signals, not identity
bindings.

The supported browser flow uses provider password verification, verified provider claims, active
PerchPoint identity, and a current membership. The development JWT is disabled unless an
isolated test explicitly opts in.

## MFA and step-up

TOTP is the Phase 6 factor. SMS and email codes are not primary or recovery factors. Privileged
workforce/vendor roles require MFA; ordinary applicants/residents may remain at AAL1 until a
future high-risk operation requires step-up. Enrollment is activated only after provider
verification. PerchPoint stores the provider factor ID and confirmation/removal timestamps, not
the plaintext seed.

AAL is enforced in backend authorization and transaction context. Role/scope changes,
delegation, MFA/contact/recovery changes, sensitive exports/records, financial destination or
refund actions, owner approvals, legal/adverse actions, API credentials, and security
administration require AAL2 plus reauthentication within five minutes when implemented.

## Recovery and contact change

Ten one-time recovery codes are displayed once and stored as bcrypt verifiers. Regeneration
replaces unused codes and revokes other sessions; consumption removes provider factors and
revokes account sessions. Password-reset links are provider-issued, expire under provider
configuration, are single use, and do not sign the user in; completion revokes sessions.

Privileged recovery is two-person and delayed. Faruk and Nathan recover each other; Ann requires
Nathan technical action plus Faruk or an authorized business approver. The flow rejects
self-recovery, records offline evidence, waits at least 15 minutes, requires the named approver,
removes factors, revokes sessions, and retains immutable recovery history. Hosted operational
proof and alert routing remain unexecuted.

Email change requires recent step-up, a provider refresh, new-address verification, notices to
both addresses, identity-preserving subject mapping, contact history, and a 24-hour cooldown.
Phone remains contact data until independently verified.

## Sessions and devices

See `ARCHITECTURE.md` for custody, cookie, timeout, concurrency, CSRF, origin, rotation, and
refresh-reuse controls. Users can list and revoke their sessions or revoke all others. MFA
factor removal, recovery, password reset, suspension, membership expiry, role reduction,
compromise, and administrative revocation terminate stale authority. The UI warns near timeout,
may preserve explicitly safe non-sensitive drafts in session storage, and routes stale sessions
to reauthentication.

## Access requests, reviews, suspension, and offboarding

Access requests preserve capability and justification; the connected UI also records purpose,
scope, and duration inside the supported justification field until dedicated API fields exist.
The requester cannot approve their own request. Role/scope changes require privileged
authorization and revoke affected sessions.

Privileged access reviews occur quarterly and after material employment/vendor/portfolio/
organization changes. Review decisions are attest, revoke, or require change and are attributed
to reviewer/time. Revocation ends membership and sessions.

Suspension/offboarding revokes sessions, delegations, and current authority, ends active
assignments, preserves business/audit/legal/financial history, and records transfer needs for
unresolved work. Restoration creates new authority deliberately; it does not resurrect ended
memberships, delegations, or assignments.

Account closure disables authentication but does not erase required records.

Requirements: `PP-AUTH-001`, `PP-AUTH-009`, `PP-AUTH-010`, `PP-AUTH-011`,
`PP-WORK-001`, `PP-WORK-002`, `PP-DATA-004`, `PP-SEC-001`, `PP-SEC-003`,
`PP-NFR-001`, `PP-ACCEPT-001`.
