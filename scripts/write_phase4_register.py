"""One-shot writer for the Phase 4 answer register. The markdown files are authoritative."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "plans" / "phase4"

RANGES = [
    (1, 4, "PP-DEC-060", "PP-PROD-001", "public and internal brand", "docs/plans/phase4/DESIGN_SYSTEM.md"),
    (5, 5, "PP-DEC-061", "PP-PROD-001", "Emergent visual source", "docs/plans/phase4/VISUAL_SOURCE_AUDIT.md"),
    (6, 9, "PP-DEC-065", "PP-NFR-001", "assets, type, and imagery", "docs/plans/phase4/DESIGN_SYSTEM.md"),
    (10, 16, "PP-DEC-060", "PP-PROD-001", "voice, theme, and density", "docs/plans/phase4/DESIGN_SYSTEM.md"),
    (17, 26, "PP-DEC-063", "PP-PROD-001", "role navigation", "docs/plans/phase4/ROLE_NAVIGATION.md"),
    (27, 29, "PP-DEC-064", "PP-PROD-002", "owner, operations, and platform admin", "docs/plans/phase4/ROLE_NAVIGATION.md"),
    (30, 35, "PP-DEC-063", "PP-NFR-001", "context, search, and notifications", "docs/plans/phase4/INFORMATION_ARCHITECTURE.md"),
    (36, 55, "PP-DEC-061", "PP-GOV-001", "Emergent handoff and shells", "docs/plans/phase4/EMERGENT_HANDOFF.md"),
    (56, 100, "PP-DEC-062", "PP-NFR-001", "component system", "docs/plans/phase4/DESIGN_SYSTEM.md"),
    (101, 110, "PP-DEC-067", "PP-SEC-001", "security headers and cache", "docs/plans/phase4/SECURITY_AND_PRIVACY.md"),
    (111, 113, "PP-DEC-068", "PP-SEC-003", "analytics boundary", "docs/plans/phase4/SECURITY_AND_PRIVACY.md"),
    (114, 115, "PP-DEC-069", "PP-SEC-001", "public-form abuse boundary", "docs/plans/phase4/SECURITY_AND_PRIVACY.md"),
    (116, 120, "PP-DEC-067", "PP-SEC-002", "privacy and accessible security", "docs/plans/phase4/SECURITY_AND_PRIVACY.md"),
    (121, 145, "PP-DEC-066", "PP-NFR-001", "accessibility", "docs/plans/phase4/ACCESSIBILITY.md"),
    (146, 147, "PP-DEC-071", "PP-ACCEPT-002", "acceptance and one design system", "docs/plans/phase4/ACCEPTANCE.md"),
    (148, 150, "PP-DEC-070", "PP-GOV-005", "phase boundary", "docs/plans/phase4/SCOPE.md"),
]
OVERRIDES = {
    33: ("PP-DEC-070", "PP-GOV-005", "owner-deferred", "Nathan", "Phase 5 canonical search"),
    94: ("PP-DEC-070", "PP-GOV-005", "implemented", "Nathan", "Phase 5 canonical search"),
    116: ("PP-DEC-070", "PP-GOV-005", "owner-deferred", "Nathan", "Phase 5 document processing"),
    123: ("PP-DEC-066", "PP-NFR-001", "owner-deferred", "Nathan", "Pre-production NVDA, Firefox, and VoiceOver matrix"),
    139: ("PP-DEC-066", "PP-NFR-002", "owner-deferred", "Nathan", "Hosted Lighthouse sample after the local bundle gate"),
    144: ("PP-DEC-066", "PP-NFR-001", "owner-deferred", "Nathan", "Human screen-reader session"),
    146: ("PP-DEC-071", "PP-ACCEPT-002", "owner-deferred", "Ann and Faruk", "Later business and operational review"),
    148: ("PP-DEC-070", "PP-GOV-005", "implemented", "Nathan", "Phase 5 remains unstarted"),
}


def lookup(number: int):
    for start, end, decision, requirement, location, evidence in RANGES:
        if start <= number <= end:
            return decision, requirement, "implemented", "Nathan", "None", location, evidence
    raise KeyError(number)


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    answers = ["# Phase 4 approved customization answers", "", "Nathan Doss approved Q1–Q150. Grouped decisions are PP-DEC-060 through PP-DEC-071.", ""]
    trace = ["# Phase 4 answer traceability", "", "| Q | Decision | Requirement | Status | Evidence |", "|---|---|---|---|---|"]
    for number in range(1, 151):
        decision, requirement, status, owner, dependency, location, evidence = lookup(number)
        if number in OVERRIDES:
            decision, requirement, status, owner, dependency = OVERRIDES[number]
        answer = f"Q{number} follows {decision} and {requirement}. {location}."
        answers.extend([
            f"### Q{number}",
            f"- Answer: {answer}",
            f"- Interpretation: This is presentation architecture. It does not start Phase 5 workflows or change server authorization.",
            f"- Location: {location}",
            f"- Evidence: {evidence}",
            f"- Status: {status}",
            f"- Dependency: {dependency}",
            f"- Owner: {owner}",
            "",
        ])
        trace.append(f"| Q{number} | {decision} | {requirement} | {status} | `{evidence}` |")
    (DOCS / "APPROVED_CUSTOMIZATION_ANSWERS.md").write_text("\n".join(answers) + "\n", encoding="utf-8")
    (DOCS / "ANSWER_TRACEABILITY.md").write_text("\n".join(trace) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
