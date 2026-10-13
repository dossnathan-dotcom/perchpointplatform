# Phase 20 requirement map

| Requirement | Where it is enforced | Verification |
| --- | --- | --- |
| `PP-MAINT-007` spending limits and preserved recommendations | `decide` in `backend/perchpoint/phase20_maintenance.py` | `tests/phase20/test_maintenance.py` |
| `PP-FIN-001` no inferred money movement | intake, decisions, and notices compare journal counts | the same test file |
| `PP-AUTH-001` server authority | capability checks and `0066_phase20_maintenance.sql` policies | direct API denials in that test file |
| `PP-SEC-001` deny by default | row security on the new tables, forced | Phase 20 clean room |
| `PP-NFR-001` loading, empty, denied, and unavailable states | `frontend/src/components/demo/MaintenanceDesk.jsx` | `frontend/e2e/phase20-maintenance.spec.js` |
| `PP-ACCEPT-001` evidence | `scripts/phase20_acceptance.py` and `test_reports/phase20/` | the acceptance checker |

Source: Nathan's Phase 20 assignment, recorded in `DECISIONS.md`. The roadmap
numbering difference is CONFLICT-028 in `docs/source/provenance/SOURCE_CONFLICT_REGISTER.md`.
Owner of the implementation decision: Nathan. Faruk still accepts later field
operations and spending adoption. Ann accepts operations. This map does not
substitute one authority for another.
