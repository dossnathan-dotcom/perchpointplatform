# Performance budgets

The public entry JavaScript budget is 250KB gzip. Each JavaScript chunk budget is 200KB gzip. Public CSS budget is 60KB gzip. `frontend/scripts/check_bundle_budget.cjs` enforces these after `yarn build`.

Measured production build on the provisional Phase 4 merge, gzip:

- `main` JavaScript: 164089 bytes (163.79 KB).
- Largest lazy chunk: 24577 bytes.
- CSS: 12607 bytes.

Closeout production build, gzip, after self-hosted fonts and image work:

- `main` JavaScript: 144486 bytes.
- Largest lazy chunk: 24577 bytes (`648.*.chunk.js`).
- CSS: 12717 bytes.

Fonts are separate WOFF2 files, not part of the JavaScript budget. Source Sans 3 regular is 15696 bytes and is the only preloaded font. Fraunces 600 is 18096 bytes. Source Sans 3 semibold is 15668 bytes.

Route-level loading splits the portal, foundation page, and reference page from the public entry. The component laboratory is not part of the production route tree. The production bundle does not contain the laboratory, PostHog, or a Google Fonts request.

Closeout Lighthouse on the production static server, simulated throttling:

- Public desktop: performance 68, accessibility 100, best practices 100, SEO 100. LCP 7.05 s. CLS 0. TBT 118 ms.
- Public mobile: performance 75, accessibility 100, best practices 100, SEO 100. LCP 6.90 s. CLS 0. TBT 120 ms.
- Listing: performance 78, accessibility 100, best practices 100, SEO 100. LCP 6.00 s. CLS 0. TBT 86 ms.
- Leasing shell: performance 69, accessibility 100, best practices 100. LCP 6.30 s. CLS 0. TBT 81 ms.
- Owner shell: performance 69, accessibility 100, best practices 100. LCP 6.30 s. CLS 0. TBT 83 ms.

The public performance scores are below 90 desktop and 85 mobile. The largest element is the hero sentence, and it is painted only after the client-rendered JavaScript runs. The approved stack does not include server rendering, and this closeout does not authorize a framework migration. That constraint is recorded here. It is not a lowered bundle budget. The JavaScript budgets above still pass.

INP: not directly measurable without suitable interaction or field data. Lab interaction proxy: TBT = 116 ms desktop and 138 ms mobile.


