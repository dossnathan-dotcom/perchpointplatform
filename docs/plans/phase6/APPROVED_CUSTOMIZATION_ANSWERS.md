# Phase 6 approved customization answers

These 160 decisions are the Phase 6 customization record. They do not grant hosted Supabase, stakeholder, or production acceptance.

| ID | Decision |
| --- | --- |
| Q1 | Supabase Auth is the hosted identity provider; Phase 6 uses its local Docker-compatible Auth service. |
| Q2 | Hosted Supabase secrets are not required for local implementation; hosted acceptance stays blocked. |
| Q3 | PerchPoint owns authorization. The identity provider authenticates and does not define business authority. |
| Q4 | Immutable provider subjects map to stable identity_account_id values. Email is not the identity key. |
| Q5 | Authentication identity, party, household, membership, employment, vendor relationship, and occupancy stay separate and effective-dated. |
| Q6 | Trust only verified issuer, subject, audience, session, expiration, method, and assurance claims. |
| Q7 | Long-lived JWT role metadata is not current authority. |
| Q8 | The development JWT is removed from supported interactive startup and remains only as an isolated test fixture. |
| Q9 | Local, hosted development, staging, and production identity environments stay separate. |
| Q10 | Cursor owns Phase 6 implementation. Emergent is not an implementation dependency. |
| Q11 | Public visitors browse listings without accounts. |
| Q12 | Prospects may submit an initial inquiry without accounts. |
| Q13 | Authenticated applicant access is created at application initiation or secure invitation acceptance. |
| Q14 | The same identity is preserved when an applicant becomes a resident. |
| Q15 | One primary resident portal account is the household default. |
| Q16 | Additional adults receive individual accounts. Shared credentials are prohibited. |
| Q17 | Guarantors receive individual identities scoped to their own obligations and authorized records. |
| Q18 | Minors do not receive accounts by default. |
| Q19 | Staff registration is invitation-only. |
| Q20 | Non-human actors use service principals, not fake employee accounts. |
| Q21 | Supported actors are public, prospect, applicant, resident primary, household adult, guarantor, vendor administrator, vendor worker, technician, cleaner, leasing, maintenance coordinator, project/operations manager, accounting, limited approver, platform administrator, owner, and service principal. |
| Q22 | Access is represented by granular capabilities and versioned role bundles. |
| Q23 | Multiple-role memberships are allowed, and each action records its authorizing role and scope. |
| Q24 | Explicit denial, suspension, legal restriction, expiration, and separation of duties override grants. |
| Q25 | Access is denied by default unless current server authority explicitly permits it. |
| Q26 | Owner authority is scoped to a specific organization. |
| Q27 | Faruk is HawkVision owner and final business authority without development-console, raw-database, deployment-secret, or source-control duties. |
| Q28 | Nathan is platform administrator and may hold a separate operational membership. Platform administration is not business approval authority. |
| Q29 | Ann is project/operations manager with leasing and maintenance coordination authority and without development, secret, raw-database, audit-deletion, or deployment authority. |
| Q30 | Role-bundle changes are versioned and audited. |
| Q31 | Scopes include organization, portfolio, property, building, space, household, lease, application, work order, vendor company, assignment, document classification, amount, decision type, and time. |
| Q32 | Property scope alone does not grant every capability. |
| Q33 | Organization membership alone does not expose all organizational records. |
| Q34 | Assignments are effective-dated with immutable history. |
| Q35 | Resident authority comes from relationship records, never a typed address. |
| Q36 | Former residents retain only specifically authorized historical access. |
| Q37 | Vendor access requires company membership and an active assignment or approved service scope. |
| Q38 | Technicians see assigned work, not all vendor-company properties by default. |
| Q39 | Mixed-use property, building, residential space, commercial space, occupancy, and assignment scopes are independent. |
| Q40 | Context switching is explicit and visible. URL parameters are not authority. |
| Q41 | Verified email and password, controlled invitations and recovery, and TOTP MFA are in scope. |
| Q42 | Social login is not added in Phase 6. |
| Q43 | Contracts stay passkey-ready. WebAuthn is not custom-built around the provider. |
| Q44 | Passwords are at least 15 characters and at most 64 are accepted. |
| Q45 | No arbitrary character-composition rules are imposed. |
| Q46 | Periodic password changes are not required. |
| Q47 | Password managers and paste are allowed. |
| Q48 | Common and compromised passwords are rejected by a privacy-preserving local mechanism. |
| Q49 | Authentication and recovery responses are generic. |
| Q50 | Layered IP, account, and global rate controls must not create easy denial-of-service lockouts. |
| Q51 | MFA is required for Faruk, Nathan, Ann, internal staff, vendor administrators, technicians, cleaners, contractors, and privileged support operators. |
| Q52 | MFA is optional for ordinary applicant and resident access and mandatory before future high-risk financial or identity changes. |
| Q53 | Authenticator-app TOTP is the factor. SMS is not a primary or recovery factor. |
| Q54 | Email verification codes do not replace TOTP for privileged users. |
| Q55 | Privileged work requires AAL2 plus current PerchPoint authorization. |
| Q56 | Recent step-up is required for role changes, delegation, MFA changes, recovery, sensitive exports, restricted records, payment-destination changes, refunds, owner approvals, legal or adverse actions, API credentials, and security administration. |
| Q57 | Critical reauthentication freshness is five minutes. |
| Q58 | AAL is enforced in the backend and database command context. |
| Q59 | TOTP enrollment is verified before activation. PerchPoint does not log or retain the plaintext seed. |
| Q60 | Recovery codes are used first. Otherwise recovery is supervised for the role. |
| Q61 | Nathan manages technical identity mechanics. Faruk approves owner-equivalent or materially privileged business memberships. |
| Q62 | Ann may request ordinary staff access. Nathan provisions it after required approval. |
| Q63 | Authorized leasing and operations staff invite applicants, residents, guarantors, vendors, and workers through relationship-bound workflows. |
| Q64 | Staff invitations expire after 24 hours. External-user invitations expire after 72 hours. |
| Q65 | Invitations are single-use, random, revocable, expiring, and protected at rest. |
| Q66 | Invitations bind email, organization, relationship, proposed roles, scopes, expiration, inviter, approval, and purpose. |
| Q67 | Every invitation is reauthorized at acceptance. |
| Q68 | Resending an invitation invalidates prior active tokens. |
| Q69 | Verification, credential setup, required MFA, acknowledgement, and profile confirmation complete before a full session. |
| Q70 | Local email uses Mailpit and synthetic recipients. Real email is not sent. |
| Q71 | Secure self-service password reset is supported. |
| Q72 | Reset links expire in 15 minutes for privileged users and no more than 30 minutes for ordinary users. |
| Q73 | Password reset does not automatically sign the user in. |
| Q74 | Security questions are not used. |
| Q75 | Ten one-time recovery codes are displayed once and stored only as protected verifiers. |
| Q76 | Email changes require step-up, new-address verification, notices to both addresses, history, and a risk cooldown. |
| Q77 | Phone numbers are contact data unless independently verified. |
| Q78 | Faruk and Nathan privileged recovery requires the other authorized principal, offline evidence, alerts, delay, and immutable audit. Neither silently recovers themselves. |
| Q79 | Ann privileged recovery requires Nathan technical action plus Faruk or an authorized business approver. |
| Q80 | Account closure disables authentication and does not erase required business, audit, legal, lease, or financial history. |
| Q81 | Sessions use backend-for-frontend custody with Secure, HttpOnly, host-only cookies. Refresh tokens are not stored in browser local storage. |
| Q82 | Cookie scope is narrow, with SameSite, CSRF defense, short session identifiers, and production-safe defaults. |
| Q83 | Owner and platform-admin sessions use a 15-minute inactivity timeout and an eight-hour absolute limit. |
| Q84 | Ordinary workforce and vendor sessions use a one-hour inactivity timeout and a 24-hour absolute limit. |
| Q85 | Applicant and resident remembered devices may persist longer, with full authentication at least every 30 days and recent step-up for sensitive actions. |
| Q86 | Concurrent-session limits are three workforce sessions and five external-user sessions. |
| Q87 | Users can view and revoke their own sessions and devices. |
| Q88 | Password reset, MFA recovery, suspension, membership expiry, material permission reduction, compromise, administrative revocation, and refresh-token reuse revoke or downgrade sessions. |
| Q89 | IP, browser, and device changes are risk signals, not hard identity bindings. |
| Q90 | The interface warns before expiration, preserves safe drafts when possible, and never continues under stale authority. |
| Q91 | Authorization is hybrid RBAC and ABAC. |
| Q92 | The typed policy module lives in the modular monolith and PostgreSQL. No external policy engine is introduced. |
| Q93 | Authorization is enforced at routes, commands, queries, storage signing, search, exports, workers, caches, and RLS. |
| Q94 | Frontend visibility is usability, not security. |
| Q95 | Decisions use capabilities rather than scattered role-name comparisons. |
| Q96 | Lists, totals, counts, facets, suggestions, and pagination are filtered inside authorized query boundaries. |
| Q97 | Sensitive resource existence is concealed when appropriate. |
| Q98 | Token-cached permissions are not authoritative for the token lifetime. |
| Q99 | Field-level restrictions apply to screening, bank, SSN, legal, contractor, internal-note, and security data. |
| Q100 | High-risk commands record permission, bundle, scope, delegation, approval, policy version, AAL, actor, and effective authority. |
| Q101 | Forced PostgreSQL RLS remains on every tenant-bearing application table. |
| Q102 | Actor, identity, organization, membership, request, AAL, and delegation context are transaction-local. |
| Q103 | Client-provided actor or organization headers are not authority. |
| Q104 | Ordinary application administrators do not bypass RLS. |
| Q105 | Storage stays private. Short-lived access is issued only after application and RLS authorization. |
| Q106 | Exports use current row and field permissions and each export is audited. |
| Q107 | Search results, snippets, counts, saved searches, suggestions, and indexing follow the same rules. |
| Q108 | Cache isolation includes organization, audience, policy version, scope, classification, and resource version. |
| Q109 | Background jobs use named, minimally privileged service principals and retain initiating actor and request lineage. |
| Q110 | Public listings use a deliberate public projection, not relaxed access to operational property records. |
| Q111 | Delegations include grantor, grantee, organization, capabilities, resource scope, amount ceiling, decision types, start, end, reason, approval, status, and revocation history. |
| Q112 | Delegation is non-transitive. |
| Q113 | Delegations last no more than 30 days by default and less for high-risk authority. |
| Q114 | Ann may approve ordinary non-capital maintenance purchases up to 1200 dollars when within the property budget and not otherwise reserved. |
| Q115 | Decisions exceeding the property monthly rent require Faruk. |
| Q116 | Amounts over 1200 dollars and all capital projects require Faruk. |
| Q117 | Nathan receives no automatic business approval authority from platform administration. |
| Q118 | Ann may authorize immediate life-safety or property-preservation actions up to 1200 dollars. Above that, Faruk is contacted. Unavoidable imminent harm uses documented act-and-notify escalation. |
| Q119 | Capital projects, new leases until delegated, final applicant approval until delegated, evictions, adverse actions, termination or nonrenewal, material rent or fee policy, screening criteria, legal matters, material write-offs, unusual adjustments, insurance claims, delegation policy, and production launch remain owner-reserved. |
| Q120 | Delegation-policy changes are versioned, prospective, step-up protected, owner-approved, audited, tested, and communicated. |
| Q121 | Nathan may change policy definitions technically. Faruk approves activation of material business-authority changes. |
| Q122 | Nobody grants themselves roles, scopes, or delegations. |
| Q123 | Platform administration cannot approve Nathan own business requests. |
| Q124 | Ann has no source-control, raw-database, secret, development, or deployment access. |
| Q125 | Accounting receives operational financial capabilities without unrelated maintenance, tenant-document, source-code, or identity-provider authority. |
| Q126 | Temporary technical access is just-in-time, purpose-bound, expiring, step-up protected, visible, and audited. |
| Q127 | Invisible resident impersonation is prohibited. Future support view is read-only, visibly bannered, reason-bound, and audited. |
| Q128 | Suspension and offboarding revoke sessions, delegations, access, and active assignments while preserving history and transferring unresolved work. |
| Q129 | Privileged access is reviewed quarterly and after material employment, vendor, portfolio, or organizational changes. |
| Q130 | Every human workforce and contractor account represents one real individual. Shared credentials are prohibited. |
| Q131 | One unified sign-in routes after authentication from current memberships. |
| Q132 | First-time onboarding validates the invitation, identity, credentials, MFA, policies, profile, and access summary. |
| Q133 | Users with multiple roles switch contexts without separate accounts. |
| Q134 | The active organization, role, property or household scope, and delegated or elevated state stay visible. |
| Q135 | Access-denied screens protect resource existence, provide a correlation ID, and offer an appropriate access-request path. |
| Q136 | Access requests include purpose, scope, duration, and justification and route to the correct approver. |
| Q137 | Security Center includes password, MFA, recovery codes, verified contacts, devices, sessions, security events, and sign-out controls. |
| Q138 | Delegation Center includes incoming and outgoing grants, requests, limits, expiry, usage, and revocation. |
| Q139 | Identity interfaces meet premium responsive, keyboard, focus, screen-reader, error-summary, reduced-motion, and automated-accessibility standards. |
| Q140 | No nonfunctional controls, fake success states, or unexplained disabled actions are allowed. |
| Q141 | Vendor companies never share a single account. |
| Q142 | Vendor administrators may propose workers. HawkVision operations approves activation. |
| Q143 | Contractor access requires active company membership, active assignment, capability, scope, and time window. |
| Q144 | Technicians and cleaners receive only the tenant and property information necessary for assigned work. |
| Q145 | Contractors see only their own approved quote, purchase allowance, invoice status, and payment status. |
| Q146 | Contractor communication and attachments remain assignment-scoped, scanned, timestamped, and auditable. |
| Q147 | Contractor access expires at assignment completion, cancellation, membership expiry, or access-end time. |
| Q148 | Service principals use short-lived machine credentials or signed workload identity and cannot use interactive portals. |
| Q149 | API credentials are random, scoped, expiring, rotatable, revocable, shown once, and protected at rest. Webhooks are signed and replay-protected. |
| Q150 | All Phase 6 users, invitations, devices, assignments, emails, and service principals remain synthetic. |
| Q151 | Registration, invitation, verification, sign-in, MFA, recovery, reset, contact change, session, suspension, role, scope, delegation, access-request, and service-principal events are audited. |
| Q152 | Authorization denials, owner approvals, policy changes, sensitive reads, exports, document access, support views, financial actions, and legal or adverse operations are audited. |
| Q153 | Passwords, tokens, TOTP seeds, recovery codes, API keys, full bank data, and unnecessary sensitive content are never logged. |
| Q154 | Rate controls, generic errors, CSRF protection, secure cookies, token rotation, replay detection, compromised-password blocking, redirect allowlists, security headers, and suspicious-event detection are required. |
| Q155 | Technical alerts route to Nathan. Owner-authority and major account-risk alerts route to Faruk. Relevant staff and vendor alerts route to Ann. |
| Q156 | A deny-by-default authorization matrix covers actors, capabilities, resources, organizations, relationships, states, AAL, delegation, and monetary boundaries. |
| Q157 | Tests cover guessed IDs, direct APIs, cross-organization, household, and vendor access, forged headers, stale roles, expiration, replay, refresh reuse, CSRF, export, cache, search, storage, and privilege escalation. |
| Q158 | Chromium, Firefox, and WebKit identity and access journeys include accessibility, keyboard, and responsive checks. |
| Q159 | Authentication, session validation, authorization, RLS, revocation, and a 1,000-property synthetic workload are benchmarked. |
| Q160 | Local Phase 6 acceptance requires end-to-end local operation, removal of the development JWT from supported interactive startup, complete cross-channel isolation, passing required gates, and committed merged evidence. Hosted Supabase, real users, business acceptance, and production remain separate gates. |
