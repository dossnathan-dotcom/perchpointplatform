# HawkVision Homes · Powered by PerchPoint

Premium rental and property-operations public site with explicitly synthetic Phase 0 workspaces.
**No production authentication, MFA, payment processing, screening, lease execution, document uploads or messaging.**

- [Phase 0 documentation](docs/phase0/README.md)
- [Verification and exact results](docs/phase0/VERIFICATION.md)
- [Complete changed-file list](docs/phase0/CHANGED-FILES.md)
- [Approved/open decisions](docs/phase0/SCOPE-AND-DECISIONS.md)
- [Known limitations / architecture review](docs/phase0/LIMITATIONS.md)

React frontend, FastAPI backend, existing MongoDB synthetic intake. All API calls use `REACT_APP_BACKEND_URL`; MongoDB uses `MONGO_URL` and `DB_NAME`. Do not add real credentials or production records.
Environment values remain local and ignored. Required new preview flags are documented in [Seeds and flags](docs/phase0/SEEDS-AND-FLAGS.md).

Preview routes: `/`, `/rentals/:unitId`, `/perchpoint`, `/perchpoint/:roleId/:viewId?`, `/foundation/:sectionId?`.
Regenerate versioned schema/fixtures with `cd backend && python -m foundation.export`; see the documentation for test/build commands.
No phase advancement is authorized by this repository state.
