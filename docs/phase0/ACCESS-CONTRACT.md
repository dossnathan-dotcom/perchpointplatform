# Role inventory and deny-by-default permission contract

Source: `backend/foundation/permissions.py`. Version: **0.1.0**. Expanded matrix: `contracts/generated/permission-matrix.csv`.
Every combination of 8 roles × 37 resources × 19 actions has a row; absent grants are explicit deny. Conditional grants do not mean the action is implemented.

## Phase 0 role intentions
| Role | Intended access | Boundaries |
|---|---|---|
| Owner / Asset Principal — Farouk | All business operations, properties, households, applicants, leasing, work, vendors, financials/budgets/documents/communications, approvals/reporting/business audits | No automatic source code, DB superuser, secrets, deployment, migrations, RLS modification, audit deletion, developer flags, secret rotation |
| Platform Super Administrator — Nathan | Complete application/configuration/integration/security/environment/migration/development administration | Technical actions require explicit purpose and approval context; no silent impersonation; audit deletion never granted |
| Leasing / Project Manager | Portfolio-wide operations, showings, applications, leasing, tenants, communications, assignments/maintenance/property records | No secrets/raw payment credentials, unrestricted screening, technical controls, audit administration, privileged financial adjustments or reserved owner decisions |
| Accounting Contractor | Authorized ledgers, reconciliation, payment exceptions, reports, financial documents/import-export | Related-record restriction; no unrestricted financial adjustments |
| Maintenance Employee | Assigned jobs and required property/unit/access/scheduling/resident coordination context, evidence/estimates | Assignment scope; no broad household or financial records |
| Subcontractor | One assigned job in the required seed; minimum access, communication, estimate/evidence/invoice context | No portfolio/tenant/applicant/financial browsing |
| Primary Resident | Own household lease/balance/charges/payments/receipts/documents/communication/maintenance/preferences | Household and related-record scope; not other adults’ restricted records |
| Applicant | Own application, household application relationships, allowed document/consent/status/showing/communication/decision/lease disclosures | Individual related-record and household scope |

Future roles are inventoried but not granted permissions: leasing agent, property manager, maintenance coordinator, vendor administrator, read-only auditor, legal/compliance reviewer, additional household signer.

## Rule dimensions
Resource; action; role; organization; ownership entity; property; building; unit; household; assignment; record sensitivity; delegation eligibility; approval requirement; audit requirement; reason requirement. Context includes active relationship and authorized scope lists. Actor role alone never grants access.

Actions: view list/detail/sensitive detail, create, edit, submit, approve, reject, assign, reassign, export, upload, download, delete-or-archive, restore, financial adjustment, integration execution, policy configuration, permission administration. Production must split archive vs irreversible deletion by data/retention policy even though the inventory groups that action.

## Simulation behavior
`evaluate_permission` denies inactive contexts, cross-organization requests, out-of-scope location IDs, unrelated households/records, unassigned jobs, excluded sensitivities, missing reasons/approvals/delegations. It returns `allowed_in_simulation` and **always `production_authorized=false`**.
Sensitive identity/screening/restricted-document owner access requires a reason and audit. Owner cannot read restricted reports through an ordinary `view_detail` grant. A simulation does not write an audit event or establish authority. The caller must not derive trusted context from browser role selection.

## Required production enforcement (not implemented)
Authenticate on server, derive actor/org/relationships from trusted records, evaluate action policy, apply row-level scope to list queries, then field/document sensitivity checks. Use PostgreSQL RLS with server-set transaction-local context and direct cross-tenant tests. Workers and integrations require equally scoped service identity and initiating-actor attribution. Never rely on hidden buttons, URL names or local storage.

Technical support/impersonation requires reason, case, approval, bounded target scope, expiry, visible banner and both initiating/effective actors in immutable audits. No impersonation capability exists now.