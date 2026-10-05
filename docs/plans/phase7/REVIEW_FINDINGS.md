# Phase 7 review findings

Reviewed against behavior commit `5a948762b3126d01704e4811c8ccecd24e7b9ee6` after the isolated suite, browser journeys, and policy migration. This pass is separate from the implementation commits.

## Resolved

- Technician property visibility. On the fresh database the seeded technician sees only the Elm assignment. Firefox and WebKit fixture properties, and a property inserted with no assignment, stay hidden. The long-lived database failed the older exact-list assertion because its property policy predates `worker_assignment_allows`. `0035_phase7_property_visibility` reapplies the accepted policy on upgrade. The permission test was not deleted or broadened to ignore unauthorized rows.
- Phase 5 live MinIO and ClamAV tests are included when `PHASE5_LIVE_SERVICES=1`. The isolated suite reported no skips.
- The content studio can list pages, save a draft, preview a revision, publish, unpublish, schedule, roll back, and read job, redirect, navigation, and conversion state. Required public paths still cannot be unpublished.
- Public pages, rentals, contact intake, and branded 404/410/429/503 states render without the seeded draft secret.

## Deferred

| Id | Severity | Owner | Risk | Reason | Due |
| --- | --- | --- | --- | --- | --- |
| P7-M1 | medium | Nathan | Low. Listing facts stay on the listing projection. | Media derivatives and property-media administration are Phase 8. The studio states that those facts are read-only. | Phase 8 |
| P7-M2 | medium | Nathan | Low. Draft and publication APIs already govern page content. | A bulk content import/export package and emergency-template library are not required to publish the approved public pages. | A later content-operations increment, not Phase 8 discovery |

No critical or high finding remains open. These deferred items do not let a draft, internal page, or unassigned property become public.
