# Security and privacy

Client route guards remain presentation. PostgreSQL row-level security and the Phase 2 server remain authoritative.

The production static server and the API send a content security policy with `default-src 'self'`, `frame-ancestors 'none'`, and no `unsafe-eval`. `style-src` includes `'unsafe-inline'` because existing components set element style attributes. Script sources are files from this origin only. The Emergent loader and PostHog session-replay snippet were removed.

HSTS is sent only when `PHASE4_ENABLE_HSTS=1`. HTML and API responses use `cache-control: no-store`. Hashed files under `/static/` may be cached.

Analytics is a no-op in `frontend/src/design-system/analytics.js`. Session replay is disabled. Sentry stays off without a DSN.

Public inquiries reject a filled honeypot and an oversized message. A timing guard and a memory rate limit exist for local and CI use. Production startup refuses to boot until `PHASE4_ABUSE_PROVIDER` names a distributed control. No provider is activated in this phase. Raw IP addresses are hashed for the in-memory window and are not written to the ordinary request log.
