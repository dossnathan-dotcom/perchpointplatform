# Phase 13 acceptance report

Behavior commit: `85e77382fac6d3135f402a1548b1f0c77117d4d8`.

`python scripts/phase13_evidence.py --all` recorded P13-R0 through P13-R16 as passed with exit code 0. The structured record is `test_reports/phase13/acceptance-state.json`. Each gate stores the command, the behavior commit, the exit code, and the SHA-256 of the captured output. Raw output is in `test_reports/phase13/logs/`.

Migration head exercised by the empty-database and clean-room gates: `0041_phase13_screening`. `0040_phase12_application`, `0039_phase11_showing`, `0038_phase10_inquiry`, `0037_phase9_discovery`, `0036_phase8_availability`, `0035_phase7_property_visibility`, and `0031_phase6_authz_remediation` are ancestors of that head.

P13-R17 and P13-R18 are not local gates. They are recorded after the protected pull request and the merged main workflows.

Hosted Supabase, Faruk and Ann stakeholder acceptance, qualified legal and fair-housing review, real-data migration, production providers, advertising, and production deployment are not granted. Phase 14 was not started. Live screening providers were not activated.
