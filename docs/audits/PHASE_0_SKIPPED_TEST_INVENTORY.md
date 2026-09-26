# Phase 0 Skipped-Test Inventory

Audit date: 2026-09-23. Original mechanism for all 17 cases:
`pytest.skip("REACT_APP_BACKEND_URL is not set")` in a shared fixture.

Classification: **accidentally disabled current Phase 0 coverage**. These tests require no
provider credentials. They now run against the real FastAPI app in-process with an isolated
memory capture store when no URL is configured, and retain live-endpoint mode when
`REACT_APP_BACKEND_URL` is set. Assertions were not weakened.

| Test path | Test name | Original reason | Dependency/environment | Risk covered | Intentional? | Runs locally now? | Must run CI? | Phase 1 blocker | Owner | Phase |
|---|---|---|---|---|---|---|---|---|---|---|
| `backend/tests/test_perchpoint_api.py` | `test_health_endpoint` | No base URL | FastAPI app or live URL | Service health | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_perchpoint_api.py` | `test_properties_endpoint` | No base URL | FastAPI app or live URL | Canonical property feed | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_perchpoint_api.py` | `test_create_showing_lead` | No base URL | FastAPI app; memory capture or Mongo | Synthetic showing intake | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_perchpoint_api.py` | `test_create_application_interest_lead` | No base URL | FastAPI app; memory capture or Mongo | Synthetic application intake | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_perchpoint_api.py` | `test_create_maintenance_request` | No base URL | FastAPI app; memory capture or Mongo | Synthetic maintenance intake | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_perchpoint_api.py` | `test_create_lead_rejects_unit_property_mismatch` | No base URL | FastAPI app or live URL | Referential integrity | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_perchpoint_api.py` | `test_lead_rejects_non_example_domain` | No base URL | FastAPI app or live URL | Real-PII contamination guard | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_perchpoint_api.py` | `test_auth_endpoint_absent_by_design` | No base URL | FastAPI app or live URL | No misleading production auth | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_perchpoint_api.py` | `test_maintenance_validation_error` | No base URL | FastAPI app or live URL | Payload validation | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_phase0_public_api_matrix.py` | `test_public_endpoints_status_content_type_and_shape[/api/rentals]` | No base URL | FastAPI app or live URL | Synthetic feed headers/shape | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_phase0_public_api_matrix.py` | `test_public_endpoints_status_content_type_and_shape[/api/foundation]` | No base URL | FastAPI app or live URL | Foundation boundary | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_phase0_public_api_matrix.py` | `test_public_endpoints_status_content_type_and_shape[/api/foundation/portfolio]` | No base URL | FastAPI app or live URL | Portfolio boundary | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_phase0_public_api_matrix.py` | `test_public_endpoints_status_content_type_and_shape[/api/foundation/contracts]` | No base URL | FastAPI app or live URL | Contract boundary | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_phase0_public_api_matrix.py` | `test_rentals_units_and_status` | No base URL | FastAPI app or live URL | Unit count/synthetic status | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_phase0_public_api_matrix.py` | `test_foundation_summary_synthetic_contract_flags` | No base URL | FastAPI app or live URL | Production flags remain false | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_phase0_public_api_matrix.py` | `test_contracts_contains_disconnected_and_no_credential_references` | No base URL | FastAPI app or live URL | Provider/credential isolation | No | Yes | Yes | Resolved | Nathan | Phase 0 |
| `backend/tests/test_phase0_public_api_matrix.py` | `test_public_endpoints_do_not_require_cookie_or_token` | No base URL | FastAPI app or live URL | Honest public-preview boundary | No | Yes | Yes | Resolved | Nathan | Phase 0 |

## Verification
- Collection: 17 formerly skipped cases.
- Final backend run: 58 passed, 0 failed, 0 skipped, including the added source-integrity
  regression.
- Local fallback uses no provider credentials and no external side effects.
- CI should run this suite in local fallback mode on every change and additionally set
  `REACT_APP_BACKEND_URL` for an approved disposable preview integration job.
