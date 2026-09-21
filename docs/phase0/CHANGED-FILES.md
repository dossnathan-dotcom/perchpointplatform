# Complete changed-file inventory — Phase 0 refinement

Baseline: `e0e3e7f` (completed PerchPoint repositioning). This list includes application code, generated contracts, documentation, tests and retained evidence. No Git write operation was performed.
Environment files were updated locally with non-secret feature flags; existing values were preserved. They are ignored and must not be committed.

## Project / configuration
- `.gitignore` — ignore local environment files.
- `eslint.config.cjs` — root entry point for the same frontend lint rules.
- `README.md`
- `auth_testing.md`
- `design_guidelines.json`
- `backend/.env` — local `PHASE0_ENABLED`, not for commit.
- `backend/requirements.txt`
- `frontend/.env` — local label/preview flags, not for commit.
- `frontend/package.json` — dependency-manager update.
- `frontend/yarn.lock`
- `frontend/tailwind.config.js`
- `frontend/eslint.config.cjs`
- `frontend/tsconfig.json`
- `frontend/tsconfig.contracts.json`
- `frontend/jsconfig.json` — **deleted**, replaced by TypeScript-compatible configuration.
- `frontend/public/index.html`
- `frontend/scripts/generate-contract-types.cjs`

## Backend
- `backend/server.py`
- `backend/foundation/__init__.py`
- `backend/foundation/base.py`
- `backend/foundation/property.py`
- `backend/foundation/people.py`
- `backend/foundation/permissions.py`
- `backend/foundation/delegation.py`
- `backend/foundation/integrations.py`
- `backend/foundation/workflows.py`
- `backend/foundation/governance.py`
- `backend/foundation/migration.py`
- `backend/foundation/seeds.py`
- `backend/foundation/catalog.py`
- `backend/foundation/export.py`
- `backend/foundation/routes.py`

## Frontend
- `frontend/src/App.js`
- `frontend/src/App.css`
- `frontend/src/index.css`
- `frontend/src/components/DemoNotice.jsx`
- `frontend/src/components/FoundationPage.jsx`
- `frontend/src/components/Footer.jsx`
- `frontend/src/components/Hero.jsx`
- `frontend/src/components/HowToApply.jsx`
- `frontend/src/components/Listings.jsx`
- `frontend/src/components/LoginModal.jsx`
- `frontend/src/components/MaintenanceModal.jsx`
- `frontend/src/components/Navbar.jsx`
- `frontend/src/components/Neighborhoods.jsx`
- `frontend/src/components/PerchPointPortal.jsx`
- `frontend/src/components/PropertyDetailPage.jsx`
- `frontend/src/components/PropertyHierarchyView.jsx`
- `frontend/src/components/TourModal.jsx`
- `frontend/src/components/UnitFacts.jsx`
- `frontend/src/components/portal/PortalToolbar.jsx`
- `frontend/src/components/portal/PreviewState.jsx`
- `frontend/src/components/ui/dialog.jsx`
- `frontend/src/config/phase0.js`
- `frontend/src/contracts/client.ts`
- `frontend/src/contracts/generated.d.ts` — generated.
- `frontend/src/data/siteData.js`
- `frontend/src/data/portalData.js`
- `frontend/src/data/propertyDetails.js` — **deleted**, duplicate static unit records removed.
- `frontend/src/data/generated/foundation.json` — generated.

## Generated fixtures
- `contracts/fixtures/import-template.csv`
- `contracts/fixtures/synthetic-innago.csv`
- `contracts/fixtures/migration-report.json`
- `contracts/fixtures/people.json`
- `contracts/fixtures/portfolio.json`

## Generated schemas and permission matrix
- `contracts/generated/AdapterCommand.schema.json`
- `contracts/generated/AdapterResult.schema.json`
- `contracts/generated/Address.schema.json`
- `contracts/generated/Allocation.schema.json`
- `contracts/generated/ApplicantConsent.schema.json`
- `contracts/generated/ApprovalDecision.schema.json`
- `contracts/generated/ApprovalRequest.schema.json`
- `contracts/generated/Asset.schema.json`
- `contracts/generated/AuditEvent.schema.json`
- `contracts/generated/AutopayConsent.schema.json`
- `contracts/generated/Building.schema.json`
- `contracts/generated/BusinessParty.schema.json`
- `contracts/generated/Charge.schema.json`
- `contracts/generated/CommercialTerms.schema.json`
- `contracts/generated/Contract.schema.json`
- `contracts/generated/Delegation.schema.json`
- `contracts/generated/DelegationPolicy.schema.json`
- `contracts/generated/DelegationResult.schema.json`
- `contracts/generated/DocumentRecord.schema.json`
- `contracts/generated/DomainEvent.schema.json`
- `contracts/generated/ExternalReference.schema.json`
- `contracts/generated/Household.schema.json`
- `contracts/generated/IdentityLifecycleContract.schema.json`
- `contracts/generated/ImportBatch.schema.json`
- `contracts/generated/InboxRecord.schema.json`
- `contracts/generated/IntegrationRecord.schema.json`
- `contracts/generated/JurisdictionPolicy.schema.json`
- `contracts/generated/Location.schema.json`
- `contracts/generated/MigrationReport.schema.json`
- `contracts/generated/Money.schema.json`
- `contracts/generated/Organization.schema.json`
- `contracts/generated/OutboxRecord.schema.json`
- `contracts/generated/OwnershipEntity.schema.json`
- `contracts/generated/PaymentException.schema.json`
- `contracts/generated/PaymentMethodReference.schema.json`
- `contracts/generated/PaymentRecord.schema.json`
- `contracts/generated/PeopleGraph.schema.json`
- `contracts/generated/Period.schema.json`
- `contracts/generated/PermissionContext.schema.json`
- `contracts/generated/PermissionMatrix.schema.json`
- `contracts/generated/PermissionResult.schema.json`
- `contracts/generated/PermissionRule.schema.json`
- `contracts/generated/Person.schema.json`
- `contracts/generated/PersonRelationship.schema.json`
- `contracts/generated/Portfolio.schema.json`
- `contracts/generated/Property.schema.json`
- `contracts/generated/ProviderEvent.schema.json`
- `contracts/generated/Reconciliation.schema.json`
- `contracts/generated/Record.schema.json`
- `contracts/generated/ResidentialTerms.schema.json`
- `contracts/generated/RetentionPolicy.schema.json`
- `contracts/generated/RoleAssignment.schema.json`
- `contracts/generated/Scope.schema.json`
- `contracts/generated/ScreeningRecord.schema.json`
- `contracts/generated/SessionContract.schema.json`
- `contracts/generated/SharedSpace.schema.json`
- `contracts/generated/StagingRecord.schema.json`
- `contracts/generated/Unit.schema.json`
- `contracts/generated/UserAccount.schema.json`
- `contracts/generated/permission-matrix.csv`
- `contracts/generated/schema-index.json`

## Documentation
- `docs/phase0/README.md`
- `docs/phase0/SCOPE-AND-DECISIONS.md`
- `docs/phase0/CANONICAL-MODEL.md`
- `docs/phase0/ACCESS-CONTRACT.md`
- `docs/phase0/DELEGATION.md`
- `docs/phase0/IDENTITY.md`
- `docs/phase0/INTEGRATIONS.md`
- `docs/phase0/DATA-GOVERNANCE.md`
- `docs/phase0/MIGRATION.md`
- `docs/phase0/AUDIT-EVENTS.md`
- `docs/phase0/SEEDS-AND-FLAGS.md`
- `docs/phase0/LIMITATIONS.md`
- `docs/phase0/ACCEPTANCE.md`
- `docs/phase0/VERIFICATION.md`
- `docs/phase0/CHANGED-FILES.md`
- `memory/PRD.md`
- `memory/test_credentials.md` — access instructions only; no actual passwords/accounts.

## Tests and retained evidence
- `backend/tests/test_foundation_contracts.py`
- `backend/tests/test_perchpoint_api.py`
- `frontend/src/config/phase0Flags.test.js`
- `test_reports/iteration_2.json`
- `test_reports/pytest/pytest_results.xml`
- `test_reports/foundation/accessibility-retest.json`
- `test_reports/foundation/build.log`
- `test_reports/foundation/initial-build.log`
- `test_reports/foundation/initial-mypy.log`
- `test_reports/foundation/final-backend-flags.log`
- `test_reports/foundation/final-build.log`
- `test_reports/foundation/final-eslint.log`
- `test_reports/foundation/final-root-eslint.log`
- `test_reports/foundation/final-export.log`
- `test_reports/foundation/final-jest.log`
- `test_reports/foundation/final-mypy.log`
- `test_reports/foundation/final-pytest.log`
- `test_reports/foundation/final-pytest.xml`
- `test_reports/foundation/final-ruff.log`
- `test_reports/foundation/final-schema-check.log`
- `test_reports/foundation/final-types-repeatability.log`
- `test_reports/foundation/final-typescript.log`
- `test_reports/foundation/final-contrast-ratios.json`
- `test_reports/foundation/ui_iter2_foundation/final_20260921_185402.jpeg`
- `test_reports/foundation/ui_iter2_foundation/foundation_checks.jpeg`
- `test_reports/foundation/ui_iter2_portal/portal_checks.jpeg`
- `test_reports/foundation/ui_iter2_public/final_20260921_185622.jpeg`
- `test_reports/foundation/ui_iter2_public/final_20260921_185642.jpeg`
- `test_reports/foundation/ui_iter2_public/public_checks.jpeg`
- `test_reports/foundation/ui_iter2_smoke/home_loaded.jpeg`

## Recommended commit message
`refactor(phase0): formalize PerchPoint foundations and accessible role previews`

Commit application/docs/generated contracts/tests only after reviewing this diff. Exclude local environment files and any real credentials. This recommendation is a message, not an executed commit or permission to advance phases.