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

Those closeout scores failed the approved floors. Pull request 19 treated that failure as an accepted client-rendering constraint. That explanation was wrong. The same production page, after compression, a smaller public entry, and build-time HTML for the stable homepage, meets the floors under the official Lighthouse desktop and mobile presets.

Performance remediation build, gzip:

- `main` JavaScript: 104142 bytes gzip, down from 144486 bytes. The foundation dataset is no longer evaluated in the public entry.
- Largest lazy chunk: 24577 bytes.
- CSS: 12766 bytes.
- Compressed transfer of the public entry is Brotli when the client accepts it, then gzip, then identity.

GitHub `phase4-performance` three-run medians, official presets, simulated throttling, cold cache, run https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/36281733622:

| Profile | Performance | LCP | CLS | TBT | Accessibility | Best practices | SEO |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Public desktop | 100 | 0.501 s | 0.002 | 0 ms | 100 | 100 | 100 |
| Public mobile | 100 | 1.758 s | 0.049 | 31 ms | 100 | 100 | 100 |
| Listing | 99 | 2.153 s | 0 | 54 ms | 100 | 100 | 100 |
| Leasing shell | 100 | 0.510 s | 0 | 0 ms | 100 | 100 | 100 |
| Owner shell | 100 | 0.511 s | 0 | 0 ms | 100 | 100 | 100 |

SEO is not a gate for the intentionally non-indexed authenticated routes. Their SEO score remains 63 because of `noindex`.

INP: not directly measurable without suitable interaction or field data. Lab interaction proxy: public TBT median 0 ms desktop and 31 ms mobile on the passing CI job. No unexplained long task remains above the approved public TBT floor.


