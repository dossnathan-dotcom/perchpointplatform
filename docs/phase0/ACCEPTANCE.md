# Phase 0 acceptance and retained verification

Final execution results and artifacts are recorded under `test_reports/` and `docs/phase0/VERIFICATION.md`. Items are not declared passed until actually run.

## Reproducible checks
```sh
cd /app/backend
python -m foundation.export --check
ruff check foundation server.py
python -m mypy foundation --ignore-missing-imports
python -m compileall -q foundation server.py
pytest -q
cd /app/frontend
node scripts/generate-contract-types.cjs --check
yarn tsc -p tsconfig.contracts.json
yarn eslint src --max-warnings 0
yarn build
```

## Required validation scope
- Clean frontend build and backend compilation.
- Python/JavaScript lint; generated-contract and typed-client TypeScript checks; Python contract types.
- Retain existing API test intent; update explicit breaking property-vs-unit feed semantics and honest demo response wording.
- JSON Schema validation, negative relationship/term/people checks, duplicate IDs, cross-org/property/building/unit scope.
- Repeat fixture generation without timestamps/random data changes or database writes.
- Permission coverage/unique tuples/default-deny and sensitive, owner/technical, subcontractor and household boundaries.
- Delegation amount/expiry/scope/currency/self-approval/fingerprint/conflict/policy-version examples; no executed decisions.
- Synthetic migration duplicate/invalid/conflicting records, totals and zero writes.
- Flags including hidden-label mode suppressing seed surfaces; absent production auth/payment/screening/messages.
- Public 320/768/1024/1440 layouts, mobile navigation, all carousel slides, keyboard focus and pause/reduced motion.
- All role paths/tabs, scoped search/context, row preview, disabled actions, notification/account menus and all state previews.
- Accessibility, measured contrast, broken links and test-ID checks.
- No newly embedded real provider credentials or production data; no real money movement or autonomous decisions.

## Current corrections recorded during implementation
The initial repeatability check exposed CSV newline normalization; exporter now uses deterministic LF. Initial lint exposed form-label associations; labels now have explicit matching IDs. Initial build could not resolve the new typed client until CRA TypeScript configuration was added. Initial Python type checking exposed dictionary-vs-model construction; fixture aggregates now explicitly validate dictionaries through `model_validate`.
These failures remain documented rather than presented as uninterrupted success.