# Phase 6 authorization and data boundaries

## Policy model

Authorization is hybrid RBAC/ABAC and deny-by-default. A role bundle grants candidate
capabilities; an action is allowed only when all applicable organization, relationship,
resource scope, state, assurance, delegation, amount, decision, and separation-of-duties
conditions also pass. Explicit denial, suspension, legal restriction, expiry, and conflicts
override grants. Policy version `phase6-1` is the current local implementation version.

Role names are not authorization checks outside the typed policy and narrowly defined authority
selection. Provider claims and cached JWT roles are not business authority. The UI may hide or
disable controls for usability, but protected routes, commands, queries, storage access,
exports, workers, and database policies enforce authority.

## Role/capability baseline

This is a readable baseline, not an exhaustive grant. `backend/perchpoint/phase6_policy.py`
contains the implemented bundle sets; database `role_bundles` and
`role_bundle_capabilities` preserve versioned definitions.

| Actor/bundle | Candidate capabilities | Mandatory restrictions |
| --- | --- | --- |
| Public/prospect | public listing projection; inquiry submission | No operational rows, internal IDs, or membership |
| Applicant/resident/household adult | own profile/session, authorized household/resident records and documents, MFA | Relationship-bound; no staff or other-household access |
| Guarantor | own profile/session and authorized obligation documents | No general household or resident authority |
| Leasing/operations/project manager | operational coordination, invitations, properties, inquiries, work, approved documents/search, bounded spend/delegation | No platform secrets/database/deploy/audit deletion; owner reservations remain |
| Maintenance coordinator | maintenance/work/property plus operational bundle where assigned | No standing technician purchase authority; scope and threshold checks |
| Accounting | operational accounting, authorized documents/exports | No unrelated maintenance, tenant documents, provider administration, or source access |
| Limited approver | bounded `expense.approve` | Amount, scope, policy, AAL, and delegation boundaries |
| Vendor administrator | own vendor administration and worker proposals | HawkVision approves activation; no shared company account |
| Vendor worker/technician/cleaner | assigned work and minimum necessary data | Active company relationship, assignment, scope, and time window |
| Platform administrator | identity/membership/role/scope/platform/security/service administration | No automatic business approval, lease, or expense authority |
| Owner | owner approvals, business delegation, audit/security/legal/export/accounting plus operations | Organization-scoped; not source-control/raw-DB/secret operator by role |
| Service principal | named, minimal machine capability | Non-interactive; short-lived scoped credential; initiating lineage retained |

Multiple memberships are allowed. Each request uses one explicit current membership context.
The active organization, role, membership/scope, AAL, and delegated state must remain visible.
Switching context revalidates current server memberships; URL parameters are never authority.

## Scope vocabulary

Implemented scope types are organization, portfolio, property, building, space, household,
lease, application, work order, vendor company, assignment, document classification, amount,
decision type, and time. Property or organization scope alone does not imply every capability.
Mixed-use physical scopes remain independent from occupancy and worker assignments.

Role and scope assignment reject self-grant. Faruk's owner bundle deliberately lacks
`role.manage` and `scope.manage`; Nathan's platform-administrator bundle deliberately lacks
`approval.owner`. A material role or any scope assignment therefore uses a two-person workflow:
the owner creates an exact, 24-hour `authority_change_approvals` record, and the platform
administrator performs the matching technical change. The record cannot approve its creator,
cannot be changed to another role/scope/resource, and is consumed atomically once. Missing,
mismatched, expired, replayed, and self approvals fail closed. Role assignment history is
effective-dated; material permission changes revoke sessions.

## RLS and transaction context

All Phase 6 tenant-bearing tables enable and force PostgreSQL RLS. Application transactions set
actor, identity, organization, membership/request, AAL, and delegation context locally. The
runtime role is not a table owner and ordinary application administrators do not bypass RLS.
Without valid actor context, protected identity rows are invisible.

Relationship-specific policies protect household/portal access and vendor/worker assignments.
The active-membership function denies ended memberships. Security-definer functions are narrow,
explicitly revoke `PUBLIC`, and grant only required execution to the runtime/definer role.

## Search, storage, export, and cache

- Authenticated search uses the same organization/RLS authority as direct record access.
  Results, snippets, counts, facets, pagination, suggestions, saved searches, and indexes must
  not reveal inaccessible existence.
- Storage remains private. Application and RLS authorization precede short-lived content access;
  object URLs are not authority. Classification and scan/quarantine states remain binding.
- Exports are generated from current row and field permissions, are audited, and must be
  reauthorized when fetched. Sensitive export is a step-up action.
- Any cache key for protected data must include organization, audience, policy version, scope,
  classification, and resource version. Cache content cannot outlive authority or revocation.
- Public listings use a deliberate projection. They do not relax RLS on operational property,
  applicant, resident, owner, vendor, or financial records.

Phase 5 implements much of the search/storage/export substrate; Phase 6 applies the identity
context and authorization requirements. Dedicated Phase 6 search/storage/export/cache
adversarial evidence is still required by P6-R5/P6-R10 and is not claimed here.

## Field and existence protection

Screening, bank, SSN, legal, contractor, internal-note, security, and similarly restricted
fields need separate capabilities/classification. Denials may return a generic not-found or
access-denied shape to conceal existence. UI denial states include a correlation ID and an
appropriate access-request path without revealing the record.

Requirements: `PP-AUTH-001`, `PP-AUTH-002`, `PP-AUTH-003`, `PP-AUTH-005`,
`PP-AUTH-006`, `PP-AUTH-007`, `PP-AUTH-008`, `PP-PROD-007`, `PP-WORK-001`,
`PP-WORK-002`, `PP-DATA-004`, `PP-DATA-006`, `PP-DATA-007`, `PP-SEC-001`.
