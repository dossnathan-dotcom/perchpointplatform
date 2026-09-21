# Identity, MFA and access lifecycle contract

**Not authentication.** There is no login endpoint, password storage, real session, MFA enrollment, tenant account creation or verification service. The former hard-coded email/password demo is removed. “Enter seeded workspace” opens a full role-specific shell and does not claim to authenticate.

Executable metadata: `IdentityLifecycleContract`, `SessionContract`, `identity_contracts()`. Lifecycle metadata is generated into the foundation bundle and is browsable at `/foundation/identity-and-retention`. All `implemented` fields are false; TTLs are null and require approval.

| Lifecycle | Contract requirement |
|---|---|
| Invitation / registration | Scoped named invitation, single-use hashed token, explicit expiry, approved applicant route, one canonical person |
| Email verification | One-time verification and enumeration-resistant response |
| Password reset | One-time hashed token, bounded lifetime, rate limiting, uniform response, session revocation |
| MFA enrollment / recovery | Recent reauthentication, independent recovery, company control, no shared recovery/master codes, revocation and notifications |
| Session duration / revocation | Role/assurance-specific absolute and idle limits, server enforcement, account/session/incident revocation |
| Device visibility | Active-device inventory, last access, individual/all-session revocation |
| Privileged reauthentication | Step-up with reason for restricted data, policies, credentials and technical access |
| Staff termination | Immediate session/role/worker-grant revocation; keep historical actor records |
| Subcontractor expiry | Assignment access expires independently of session duration |
| Resident activation | Approved household relationship; individual identity for adult signers |
| Applicant conversion | Reuse person ID, end prior relationship, preserve consent/decision provenance |
| Abuse / lockout | Account/device/IP controls, bounded lockout, enumeration resistance and audited recovery |
| Technical admin | Named identity + MFA; separate business/technical/development purpose |
| Emergency support | Incident/reason/approval/expiry, least scope, banner and retrospective review |
| Impersonation | Disabled now; future dual-actor audit, visible indication, explicit approval, reason, short expiry |

Session contract carries person/account IDs, authentication/expiry/revocation times, assurance, device label, optional hashed IP metadata, purpose, support reason and initiating actor. No bearer token or credential is represented in public fixtures.

Before implementation: approve provider, session/MFA/recovery policy, company ownership, permission matrix, restricted-data policy, legal retention and audit storage. Future API identity routes must live under `/api/auth/*`. Production server context must never trust the preview role selector.