# Security and privacy

Client route guards remain presentation. PostgreSQL row-level security and the Phase 2 server remain authoritative.

The production static server and the API send `style-src 'self'` and `style-src-attr 'none'`. Element and attribute inline styles are not allowed. Script sources are files from this origin only. There is no `unsafe-eval` and no `unsafe-inline`. The Emergent loader and PostHog session-replay snippet were removed. Fonts are self-hosted Fraunces and Source Sans 3 WOFF2 files. Public images are repository AVIF, WebP, and JPEG files.

HSTS is sent only when `PHASE4_ENABLE_HSTS=1`. HTML and API responses use `cache-control: no-store`. Hashed files under `/static/` may be cached.

Analytics is a no-op in `frontend/src/design-system/analytics.js`. Session replay is disabled. Sentry stays off without a DSN.

Public inquiries reject a filled honeypot and an oversized message. A timing guard and a memory rate limit exist for local and CI use. Production startup refuses to boot until `PHASE4_ABUSE_PROVIDER` names a distributed control. No provider is activated in this phase. Raw IP addresses are hashed for the in-memory window and are not written to the ordinary request log.
