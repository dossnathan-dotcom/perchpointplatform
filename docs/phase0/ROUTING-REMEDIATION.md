# Narrow Phase 0 routing/API remediation — 2026-09-21

Scope: the reported role-entry/navigation defect, four synthetic read APIs, applicable regressions, and this evidence. Baseline commit: `735fec5`. No visual direction, product positioning, domain schema, provider, production authentication or later-phase workflow changes.

**Independent verification:** `test_reports/iteration_4.json` reports all required routing/API checks passed, no functional regressions, `retest_needed=false`. The earlier failed automation report `iteration_3.json` is retained.

## Root cause: evidence and limits
The initial exact leasing flow did **not** reproduce the indefinite gate/modal stall in the current preview: URL `/perchpoint/leasing`, gate count 0, modal count 0, workspace count 1. Therefore a unique browser timing trigger for the original live observation is **not proven**. No speculative React scheduling/Radix animation explanation is claimed as a confirmed cause, and the optional view segment does not make `/perchpoint/leasing` an invalid URL.

Code inspection found concrete state-lifetime defects:
- `AppContent` maintained separate conditional `Routes` trees and duplicate modal mount locations; the app-level modal flag was not owned by the history entry that opened it.
- Entry called navigation before closing the modal, leaving route transition and overlay cleanup separate.
- The same portal subtree survived role/view parameter changes. Its reset effect omitted delegation-policy state, and toolbar account/notification state was never reset.
- Unknown view IDs silently showed the default view; extra nested path segments had no controlled route fallback.

The remediation removes these independent/stale state paths. The final agent verified immediate modal dismissal plus correct workspace rendering **without reload** for every role, as well as stale-state/history cases. This demonstrates current behavior, not a retrospective reproduction of the original indefinite stall.

## Exact fix
1. One stable `Routes` tree with a public `Outlet` layout, explicit portal/foundation routes and catch-all route.
2. One modal mount; visibility is scoped to `location.key`. Closing explicitly clears the owning key **before** navigation. A history change clears overlay state; back/forward cannot resurrect the old modal.
3. Key the complete portal subtree by history-entry key so route/role/view transitions discard toolbar panels, policy/record dialogs, search, context, and preview-state selections together.
4. Unknown roles/views render the existing unavailable state; excessive/unknown paths render a controlled not-found screen.
5. No reload, artificial timeout, delayed redirect, provider/auth change or router downgrade.

## Eight-role navigation matrix
Each ✓ represents passed independent browser checks. “Entry” means actual gate → modal → select → Enter, with the expected workspace appearing **before any refresh/direct-load checks**.

| Role / route ID | Entry, correct URL/render | Modal closed | Direct + refresh | Back + forward | Switch + clear stale state | Nested direct + client |
|---|---|---|---|---|---|---|
| Owner / Asset Principal — `owner` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Platform Super Administrator — `super-admin` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Leasing / Project Manager — `leasing` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Accounting Contractor — `accounting` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Maintenance Employee — `maintenance` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Subcontractor — `subcontractor` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Primary Resident — `resident` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Applicant — `applicant` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Routes remain `/perchpoint/{roleId}` and `/perchpoint/{roleId}/{viewId}`. Public-header entry also passed.
Unknown-role, unknown-view, excessive-path and `/perchpointx` checks passed controlled states rather than blank/fallback workspaces.
Exact individual cells: `test_reports/routing-remediation/navigation-matrix.json`.

## API verification matrix
All four are intentionally unauthenticated **public synthetic Phase 0 review endpoints only**. They use deterministic fixture builders, not MongoDB, live policies, environment secrets or provider responses. No role/header/query/body grants access or changes the data source.

| Endpoint | Enabled GET | Content type | Response shape | Disabled/missing/invalid flag |
|---|---|---|---|---|
| `/api/rentals` | 200 | `application/json` | `units` (15 synthetic unit records), `data_status=demonstration_phase_0` | 200, `units=[]` |
| `/api/foundation` | 200 | `application/json` | `version`, `data_status=synthetic_contracts_only`, production-auth/provider-execution/canonical-persistence flags all false | 404 JSON `detail` |
| `/api/foundation/portfolio` | 200 | `application/json` | organizations, ownership_entities, properties, buildings, units, shared_spaces, assets | 404 JSON `detail` |
| `/api/foundation/contracts` | 200 | `application/json` | version, data_status, portfolio, people, permissions, delegation, integrations, identity, retention, scenarios, migration | 404 JSON `detail` |

Successful responses include `Cache-Control: no-store` and `X-PerchPoint-Data: synthetic-phase-0`. Foundation disabled error: `{"detail":"Seeded contract previews disabled"}`.
Tested unsupported POST/PUT methods: **405 JSON**; unknown API subpaths: **404 JSON**. Query parameters and request bodies cannot select live data, mutate policy or confer privileges.

Added a fail-closed fixture check: reject non-synthetic versioned records, populated credential references, raw credential fields, connected/production providers, active runtime enforcement or production-execution flags. Tested contaminated fixtures return **503**, `{"detail":"Synthetic preview unavailable"}`, without echoing inserted credential values. All published provider entries remain disconnected/synthetic with null credential references.

**Publication boundary:** this helper is not a production serializer, authorization engine, PII detector or comprehensive security control. Never connect these endpoints to live models/configuration. Disable/retire public foundation endpoints before production data is introduced; any future private contract/policy access needs approved server authorization. A future public rentals feed requires a separately reviewed publication projection, not the current internal unit fixture shape. Never bundle production permissions, sensitive schemas or secrets into the frontend; its existing bundle contains only the same synthetic design data. Feature flags are not access control.

Exact API matrix: `test_reports/routing-remediation/api-matrix.json`.

## Tests executed by the independent testing agent
| Command / check | Exact final result | Evidence under `test_reports/routing-remediation/` |
|---|---|---|
| `yarn test --watchAll=false --runInBand src/App.routing.test.js` | **20 passed**, 1 suite, 1.361s | `iter4-jest-routing-full.log` |
| `yarn test --watchAll=false --runInBand src/config/phase0Flags.test.js` | **2 passed**, 1 suite, 0.367s | `iter4-jest-flags-full.log` |
| Complete backend pytest with JUnit output | **52 passed, 6 warnings, 2.15s** | `iter4-backend-pytest-full.log`; `../pytest/pytest_results.xml` |
| Root + frontend ESLint | Both passed | `iter4-root-eslint-full.log`, `iter4-frontend-eslint-full.log` |
| Ruff, including backend tests | All checks passed | `iter4-ruff-full.log` |
| Mypy foundation + server | No issues in **15 source files** | `iter4-mypy-full.log` |
| `yarn tsc -p tsconfig.contracts.json` | Passed | `iter4-tsc-contracts-full.log` |
| `yarn build` | Compiled successfully, 12.39s; 190.55kB JS / 12.32kB CSS gzip | `iter4-frontend-build-full.log` |
| `python -m foundation.export --check` | **67 deterministic artifacts verified** | `iter4-foundation-export-check-full.log` |
| `node scripts/generate-contract-types.cjs --check` | Generated TypeScript matches source | `iter4-generate-contract-types-check-full.log` |
| Live navigation / API matrices | All requested cells passed | matrix JSON files + `iteration_4.json` |

The actual TypeScript generator was used for the final check. The earlier `python -m foundation.export --typescript --check` invocation did not check TypeScript (that flag is not supported); it is **not** counted as TypeScript evidence.

### Automation blockers corrected, not hidden
Iteration 3 passed live routing and 52 backend tests but failed frontend Jest resolution and full test lint. CRA/Jest 27 could not resolve React Router 7’s export-only CommonJS entry/subpath. Test-only CRACO mappings now point at the installed package entries, including the router version belonging to `react-router-dom`, plus existing app alias/axios CommonJS resolution. No router mocks or dependency downgrade were added.
The jsdom setup supplies missing TextEncoder/TextDecoder/matchMedia and React’s act environment. Tests query real Radix dialogs in the document-body portal. Direct-load tests remount the app intentionally; client-navigation/history tests use real router links/history instead, not remounts as a workaround. Unused/misordered test imports were corrected without weakening assertions.

## Changed-file list (this remediation only)
### Runtime: no domain schema or visual-style files changed
- `frontend/src/App.js`
- `frontend/src/components/LoginModal.jsx`
- `frontend/src/components/PerchPointPortal.jsx`
- `backend/foundation/routes.py`
- `backend/server.py`

### Test configuration and regression tests
- `frontend/craco.config.js` — test resolver configuration only.
- `frontend/src/setupTests.js` — new jsdom setup.
- `frontend/src/App.routing.test.js` — new real-router regression suite.
- `backend/tests/test_phase0_public_api_matrix.py` — new external API matrix.
- `backend/tests/test_phase0_isolated_guards.py` — new failure-mode tests.
- `backend/tests/test_foundation_contracts.py` — import cleanup only.
- `backend/tests/test_perchpoint_api.py` — import cleanup only.

### Documentation and evidence
- `docs/phase0/VERIFICATION.md` — current remediation addendum; earlier evidence retained.
- `docs/phase0/ROUTING-REMEDIATION.md` — this report.
- `memory/PRD.md` — updated issue/outcome/boundary record.
- `test_reports/iteration_3.json` — initial verification, including automation failures.
- `test_reports/iteration_4.json` — independent final verification.
- `test_reports/pytest/pytest_results.xml` — final 52-test JUnit output.
- `test_reports/routing-remediation/navigation-matrix.json`
- `test_reports/routing-remediation/api-matrix.json`
- `test_reports/routing-remediation/` — retained command logs, synthetic response sample, and browser evidence enumerated in the matrices and final report.

No environment, credentials, dependencies, canonical schema, seeded-data source, CSS, branding or production workflow changes. Pre-existing untracked lockfiles and older foundation logs are not new remediation changes.

## Remaining limitations and stop condition
- The original indefinite stall’s exact environmental trigger was not reproduced. Current requested behavior is independently verified.
- Role previews and API fixtures remain **MOCKED** presentation/design data, not authentication or production authorization.
- Existing FastAPI shutdown-hook and multipart-import deprecation warnings remain (6 pytest warnings across two workers). They are non-blocking and deliberately not expanded into unrelated lifecycle/package work.
- Schema/type checks cover the existing contract boundary; no production RLS or broad security certification is implied.

Recommended commit message: `fix(phase0): synchronize preview routes and enforce synthetic API boundaries`

**Stop here and await user review. No feature additions or phase advancement are authorized.**