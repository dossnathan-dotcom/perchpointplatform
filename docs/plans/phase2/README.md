# Phase 2 Planning Package

Status: **Q1–Q120 recorded. P2-01 contract work is the authorized package. P2-02 and
later packages are not approved.**

This directory's planning records do not implement persistence, authentication,
providers, migrations, or UI writes. P2-01 adds versioned contracts and fixtures only.

| Document | Purpose |
|---|---|
| [Scope and approved decisions](SCOPE_AND_DECISIONS.md) | Business objective, decision-to-requirement map, phase boundaries |
| [Architecture](ARCHITECTURE.md) | Modular monolith, domain model, states, diagrams |
| [Implementation plan](IMPLEMENTATION_PLAN.md) | P2-00 through P2-06 work packages and file impact |
| [Contracts](CONTRACTS.md) | API, event, error, adapter, compatibility rules |
| [Security and threat model](SECURITY.md) | Local auth, RLS, threat controls, later-phase cases |
| [Acceptance matrix](ACCEPTANCE.md) | Evidence, benchmarks, stop conditions |
| [Emergent handoff](EMERGENT_HANDOFF.md) | External UI envelope; blocked until contracts freeze |
| [ADRs](adr/README.md) | Architecture decision records |
| [Approved customization answers](APPROVED_CUSTOMIZATION_ANSWERS.md) | Q1–Q120 consolidated register |
| [Answer traceability](ANSWER_TRACEABILITY.md) | Question-to-decision map; not implementation coverage |

Normative product obligations remain in `docs/governance/REQUIREMENTS_TRACEABILITY.md`.
These files are planning/explanatory unless Nathan accepts a statement as policy.

Related: [Phase 1 acceptance](../../governance/PHASE_1_ACCEPTANCE.md),
[source precedence](../../product/SOURCE_PRECEDENCE.md),
[conflict register](../../source/provenance/SOURCE_CONFLICT_REGISTER.md).
