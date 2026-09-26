# Performance budgets

The public entry JavaScript budget is 250KB gzip. Each JavaScript chunk budget is 200KB gzip. Public CSS budget is 60KB gzip. `frontend/scripts/check_bundle_budget.cjs` enforces these after `yarn build`.

Measured production build on this phase, gzip:

- `main` JavaScript: 164089 bytes (163.79 KB). The previous public main chunk was about 189 KB gzip.
- Largest lazy chunk: 24577 bytes.
- CSS: 12607 bytes.

Route-level loading splits the portal, foundation page, and reference page from the public entry. The component laboratory is not part of the production route tree. The production bundle does not contain the laboratory, PostHog, or a Google Fonts request.

A hosted or CI Lighthouse sample for the public mobile and desktop scores remains owner-deferred to Nathan. The bundle gate is the local blocking performance control. Do not treat a missing Lighthouse run as a passing score.
