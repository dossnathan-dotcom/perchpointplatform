# Phase 7 Emergent handoff

Status: Emergent was unavailable in this environment. Under the definitive closeout authorization, Cursor implemented and reconciled the bounded public and staff surfaces against the frozen routes below. A later Emergent branch, if one appears, must be reviewed change by change and must not become a second source of truth.

## Accepted base

- Repository: `dossnathan-dotcom/perchpointplatform`
- Starting main: `2f49cfa6ade9b21e9411b10cbfa2b91cb0f2898b`
- Integration branch: `cursor/phase-07-public-content`
- Suggested Emergent branch, if a later slice is produced: `emergent/phase-07-public-cms`

## Frozen commands

- `GET /api/v2/public/pages/{slug}`
- `GET /api/v2/public/navigation`
- `GET /api/v2/public/sitemap.xml`
- `GET /api/v2/public/robots.txt`
- `GET /api/v2/public/redirect?path=`
- `POST /api/v2/public/submissions`
- `POST /api/v2/public/analytics`
- `POST /api/v2/content/drafts`
- `POST /api/v2/content/{id}/publish`
- `GET /api/v2/content/preview/{slug}`
- `POST /api/v2/content/redirects`
- `GET /api/v2/content/conversions`
- `GET /api/v2/listings`

## Allowed UI paths

- `frontend/src/components/public/`
- `frontend/src/App.js` public route registration
- `frontend/src/components/Navbar.jsx`
- `frontend/src/components/Footer.jsx`

## Prohibited changes

Schema, migrations, authorization, RLS, secrets, CI, session custody, and generated contracts stay with Cursor. Emergent must not invent approved legal, fee, license, or emergency copy. Fixtures stay marked EXAMPLE ONLY.

## Required states

Loading, empty, validation, success, permission denied, not found, unavailable, and retry. Preview responses stay `noindex` and `no-store`. Forms must not claim success before the server returns a reference.

## Return report

Branch, commit, files changed, journeys exercised, screenshots, and any contract deviation. Cursor accepts, refactors, rewrites, or rejects each change.
