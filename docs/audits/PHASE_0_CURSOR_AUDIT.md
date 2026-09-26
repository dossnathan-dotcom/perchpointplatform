# Phase 0 Cursor Audit

Audit date: 2026-09-23. Branch base: `main@9706914916c124784bd1bad3715de239e2774469`.
Audit branch: `cursor/phase-01-governance-audit`. Remote: public
`https://github.com/dossnathan-dotcom/perchpointplatform.git`.

## Architecture
React 19/CRA/CRACO frontend; FastAPI backend; Motor/Mongo synthetic form intake; executable
Pydantic foundation contracts; generated JSON Schema/fixtures/permission matrix/TypeScript.
There is no production authentication, server authorization, PostgreSQL/RLS, immutable audit
store, upload pipeline, provider execution, CI workflow, or `.env.example`.
Role workspaces and permission evaluation are synthetic review surfaces.

## Command evidence
- Python 3.13.11; Node 24.13.0; Yarn 1.22.22 via Corepack.
- `python -m foundation.export --check`: PASS, 67 deterministic artifacts.
- `ruff check foundation server.py tests ../scripts/validate_governance.py`: PASS after
  relocating three late imports in `backend/server.py`.
- `mypy foundation server.py --ignore-missing-imports`: PASS for 15 source files.
  `compileall`: PASS.
- Contract and guard portability suite: 36 passed from both repository root and `backend/`.
- Isolated guards: 18 pass with three deprecation warnings.
- Final full backend tree: 58 passed, 0 failed, 0 skipped, with seven deprecation warnings.
  The 17 formerly skipped HTTP cases now use an in-process FastAPI/memory-store fallback and
  retain live-URL mode for disposable preview CI.
- TypeScript generator `--check`: PASS after deterministic regeneration.
- TypeScript compile: PASS after declaring exact `@types/node@18.19.70`, compatible with
  the existing TypeScript 4.9.5.
- ESLint: PASS. Frontend Jest: 22/22 PASS with explicit preview flags. CRA build: PASS
  (185.32 kB main JS gzip; 12.23 kB CSS gzip).
- `frontend/yarn.lock` is now canonical. A deleted-`node_modules` reproduction with
  `corepack yarn install --frozen-lockfile --non-interactive` passed. Existing resolution,
  peer-dependency, and deprecation warnings remain documented risks, not proven vulnerabilities.
- Fresh terminal output was observed during the audit but was not committed as a complete
  timestamped command log. The exact commands and summarized exit results are retained here;
  final release evidence requires durable logs.

## Claim matrix
| Claim | Code/test evidence | Observed verdict | Severity/remediation/phase |
|---|---|---|---|
| 59 JSON Schemas | `schema-index.json`, exporter | Verified by source enumeration; no test pins 59 | Add explicit regression if count is contractual |
| 67 repeatable artifacts | exporter `--check` | Verified | None |
| Generated TypeScript | generator and committed `.d.ts` | Verified after regeneration | Frozen Yarn install and generator check pass |
| 5,624 permission combinations | 8×37×19 and CSV/export | Verified by source/CSV inspection; tests derive current dimensions | Simulation only; add pinned regression if contractual |
| Canonical hierarchy/invalid links | foundation contract tests | Verified | Portable module-derived repository root |
| Person/household/business links | Pydantic contracts/tests | Verified | None |
| Stable PerchPoint/provider IDs | UUIDv5 seeds and external refs | Verified for synthetic data | Production identity later |
| 6 properties/7 buildings/15 units/3 states | fixture/export/contracts | Verified by fixture/source inspection; tests do not pin all counts | Add pinned regression if contractual |
| Innago valid/duplicate/invalid/conflict | migration logic/report | Verified | Portable fixture checks pass |
| Eight role workspaces | routing/data + 20 Jest cases | Verified | Preview only |
| Synthetic catalog/foundation GET boundaries | isolated and HTTP matrix tests | Verified locally | Disposable live-preview CI mode remains available |
| Deny-by-default permissions | permission engine/matrix | Verified in simulation | No runtime enforcement |
| Loading/empty/error/denied states | preview components/static inspection | Partially verified | Browser replay deferred |
| Disabled later-phase actions | disclosures/disconnected adapters | Verified statically | Preserve boundary |
| Responsive/accessibility claims | committed evidence only | Unverified independently | Manual/browser review required |
| Unified routing/modal/history/reset/deep links/unknowns | `App.js`, 20 Jest tests | Verified | None |
| No forced refresh/artificial delays | static route review | Verified | None |

## Security/privacy findings
1. High: role URLs are not authentication; permissions are not server enforcement.
2. High: foundation portfolio/people/permission payloads are public when preview is enabled.
3. High: no CI currently enforces the now-reproducible lockfile-based dependency/build workflow.
4. Medium: synthetic POST intake has no rate limit and stores free text in Mongo.
5. Medium: CORS permits all methods/headers for configured credentialed origins.
6. Medium: audit/outbox/inbox are contracts, not immutable/persistent controls.
7. Medium: broad unused dependency surface increases maintenance/supply-chain burden.
8. No committed runtime secret was identified in reviewed tracked configuration; this is not a
   history-wide secret-scanner attestation.
9. Low: `/api/properties` does not use the synthetic headers/contamination guard applied to
   `/api/rentals` and is not covered by the four-endpoint matrix.

## Portable repository-root remediation
The three failures came from `ROOT = Path("/app")` and `sys.path.insert(0, "/app/backend")` in
tests. Emergent's container mounts the repository at `/app`, masking the coupling. Tests now
derive the repository root from `Path(__file__).resolve()`, while `backend/tests/conftest.py`
provides portable import and synthetic test defaults. The affected contract/guard suite passes
from two working directories. Legitimate `/app` paths remain in `.emergent/cron` deployment
scripts and historical container command examples under `docs/phase0`; runtime code no longer
depends on that mount for tests.

## Skipped-test closure
All 17 skipped cases were current Phase 0 API checks accidentally disabled whenever no external
base URL was configured. Assertions were retained. Local runs now exercise the real FastAPI app
with an isolated memory capture store; setting `REACT_APP_BACKEND_URL` switches the same tests
to disposable live-preview mode. See `PHASE_0_SKIPPED_TEST_INVENTORY.md`.

## Test-quality assessment
Contract invariants, negative guards, contamination, routing history, synthetic boundaries, and
portable local API coverage are meaningful. Remaining weaknesses are no CI workflow, no
committed browser suite, no Mongo failure/timeout coverage, and evidence logs cited by historical
documentation but absent from Git.

## Remediation decision
Narrow Phase 0 remediation corrected path portability, all skipped tests, frontend lockfile/type
reproducibility, generated declarations, and backend lint without adding production behavior.
The authoritative Platform Vision is now preserved with matching pre/post SHA-256, complete
2/2-page extraction, deterministic regeneration, and source-precedence reconciliation. No
critical Phase 0 technical closure blocker remains.

## Acceptance boundary
- Phase 0 technical checks in this closure pass; production security remains explicitly
  unimplemented and browser/accessibility evidence retains its documented manual limitations.
- Phase 1 source-ingestion, technical-validation, and governance-consistency dimensions pass.
- Business, operations, accounting, maintenance, and legal acceptance remains pending with the
  named authority. Those pending acceptances do not block later-phase planning, but production
  activation remains blocked.
