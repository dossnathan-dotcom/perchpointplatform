# Normative Governance Coverage

Every normative statement in the listed artifact is governed by the referenced requirement
IDs. Definitions, observations, evidence summaries, risks, dependencies, examples, and
historical descriptions that do not state an obligation are explanatory/non-normative.

| Artifact | Requirement coverage | Classification |
|---|---|---|
| `docs/product/PRODUCT_CONSTITUTION.md` | PP-PROD-001..003, PP-GOV-003, PP-GOV-005..006, PP-AUTH-003..004, PP-AUTH-008..011, PP-FIN-003..005, PP-SEC-002, PP-SEC-004 | Normative constitution |
| `docs/product/TERMINOLOGY.md` | PP-GOV-006, PP-PROP-001, PP-LEASE-003, PP-AUTH-010 | Normative definitions |
| `docs/product/SOURCE_PRECEDENCE.md` | PP-GOV-001 | Normative precedence |
| `docs/product/SYSTEM_REPLACEMENT_BOUNDARY.md` | PP-PROD-001, PP-PROD-003, PP-DATA-003, PP-FIN-005 | Normative boundary |
| `docs/governance/CAPABILITY_REGISTER.md` | PP-PROP-005, PP-PROD-004..007, PP-WORK-005 | Normative target; current-state cells explanatory |
| `docs/governance/PROCESS_INVENTORY.md` | PP-PROD-005, PP-PROD-007, PP-WORK-002..004 | Normative process coverage |
| `docs/governance/SYSTEM_OF_RECORD_MAP.md` | PP-PROP-004, PP-FIN-001, PP-FIN-005, PP-DATA-004 | Normative authority map |
| `docs/governance/RACI.md` | PP-AUTH-003..008, PP-GOV-004 | Normative role authority |
| `docs/governance/ACCEPTANCE_AUTHORITY.md` | PP-ACCEPT-002 | Normative acceptance authority |
| `docs/governance/APPROVAL_AND_DELEGATION_POLICY.md` | PP-AUTH-002..005, PP-AUTH-009, PP-FIN-002, PP-FIN-006, PP-MAINT-007 | Normative policy |
| `docs/governance/MAINTENANCE_RECOMMENDATION_POLICY.md` | PP-MAINT-001..006, PP-WORK-003..004 | Normative policy |
| `docs/governance/COMMUNICATION_POLICY.md` | PP-COMM-001..005 | Normative policy |
| `docs/governance/PAYMENT_CHANNEL_POLICY.md` | PP-FIN-001, PP-FIN-003..005 | Normative policy |
| `docs/governance/CHANGE_CONTROL.md` | PP-GOV-002, PP-GOV-005 | Normative control |
| `docs/governance/PROVIDER_EVALUATION_FRAMEWORK.md` | PP-PROV-001..002 | Normative evaluation method |
| `docs/governance/RISK_REGISTER.md` | PP-ACCEPT-001 | Explanatory risk evidence; owners/actions normative through mapped requirements |
| `docs/governance/DEPENDENCY_REGISTER.md` | PP-ACCEPT-001 | Explanatory dependency evidence |
| `docs/governance/ASSUMPTIONS_AND_OPEN_DECISIONS.md` | PP-GOV-001, PP-ACCEPT-001 | Explanatory decision status |
| `docs/governance/APPROVED_DECISION_REGISTER.md` | PP-ACCEPT-003 | Canonical approved-decision traceability |
| `docs/governance/PLATFORM_VISION_TRACEABILITY.md` | Existing IDs listed per row | Explanatory source corroboration; no new policy |
| `docs/governance/REQUIREMENTS_TRACEABILITY.md` | All PP-* IDs | Canonical normative requirement source |
| `docs/governance/PHASE_1_ACCEPTANCE.md` | PP-ACCEPT-001..003 | Evidence/verdict, not new policy |
| `docs/plans/phase2/*.md` and `docs/plans/phase2/adr/*.md` | Existing IDs cited per document | Planning/explanatory until Nathan accepts the plan |
| `AGENTS.md` | PP-GOV-002, PP-GOV-005, PP-SEC-001, PP-ACCEPT-001..002, PP-NFR-002 | Repository execution controls |
| `.cursor/rules/*.mdc` | Exact PP-* IDs listed in each rule | Repository execution controls |
| `.cursor/agents/*.md` | Exact PP-* IDs listed in each reviewer definition | Review protocol; no new product policy |

Ranges use inclusive numeric ordering within one prefix. A range does not imply that unused
identifiers exist. The decision and requirement validator resolves every explicit decision
reference and every evidence/document path.
