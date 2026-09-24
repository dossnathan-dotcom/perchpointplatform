# HawkVision Homes · Powered by PerchPoint

Premium rental and property-operations public site with explicitly synthetic Phase 0 workspaces.
**No production authentication, MFA, payment processing, screening, lease execution, document uploads or messaging.**

- [Phase 0 documentation](docs/phase0/README.md)
- [Verification and exact results](docs/phase0/VERIFICATION.md)
- [Complete changed-file list](docs/phase0/CHANGED-FILES.md)
- [Approved/open decisions](docs/phase0/SCOPE-AND-DECISIONS.md)
- [Known limitations / architecture review](docs/phase0/LIMITATIONS.md)
- [Product constitution](docs/product/PRODUCT_CONSTITUTION.md)
- [Phase 1 governance index](docs/governance/README.md)
- [Requirements traceability](docs/governance/REQUIREMENTS_TRACEABILITY.md)
- [Independent Phase 0 Cursor audit](docs/audits/PHASE_0_CURSOR_AUDIT.md)
- [Source provenance and extraction](docs/source/provenance/SOURCE_MANIFEST.md)
- [Phase 2 planning package](docs/plans/phase2/README.md)

React frontend, FastAPI backend, existing MongoDB synthetic intake. All API calls use `REACT_APP_BACKEND_URL`; MongoDB uses `MONGO_URL` and `DB_NAME`. Do not add real credentials or production records.
Environment values remain local and ignored. Required new preview flags are documented in [Seeds and flags](docs/phase0/SEEDS-AND-FLAGS.md).

Preview routes: `/`, `/rentals/:unitId`, `/perchpoint`, `/perchpoint/:roleId/:viewId?`, `/foundation/:sectionId?`.
Regenerate versioned schema/fixtures with `cd backend && python -m foundation.export`; see the documentation for test/build commands.
No phase advancement is authorized by this repository state.

The Phase 1 source-ingestion, technical-validation, and governance-consistency dimensions
pass. Business acceptance remains provisional and named business, operational, accounting,
maintenance, and legal acceptance remains pending. Phase 2 application implementation,
production authentication, provider execution, migration, and deployment are not
authorized until Nathan approves `docs/plans/phase2/`.

## Reproducible frontend setup

The authoritative frontend package manager is Yarn 1.22.22, declared in
`frontend/package.json`; `frontend/yarn.lock` is canonical. Node 24.13.0 is the audited
runtime for this closure run.

```sh
cd frontend
corepack yarn install --frozen-lockfile --non-interactive
node scripts/generate-contract-types.cjs --check
corepack yarn tsc -p tsconfig.contracts.json
corepack yarn eslint src --max-warnings 0
set REACT_APP_SHOW_DEMO_LABELS=true
set REACT_APP_ENABLE_SEEDED_PREVIEWS=true
corepack yarn test --watchAll=false --runInBand
corepack yarn build
```

The `set` lines above are Windows `cmd.exe` syntax; PowerShell uses
`$env:NAME='true'` and POSIX shells use `NAME=true`. CI should set both preview flags explicitly,
then execute the same frozen install and gates. Do not add npm, pnpm, or Bun lockfiles.
