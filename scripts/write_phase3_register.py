"""Write the Phase 3 answer register from the approved one-line answers."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINES = (ROOT / "scripts" / "phase3_answer_lines.txt").read_text(encoding="utf-8").splitlines()
assert len(LINES) == 174, len(LINES)
BLOCKED = {3, 168}
DEFERRED = {11, 12, 25, 37, 38, 41, 42, 111, 128, 129, 141, 148, 161, 174}
FUTURE = {4, 5, 6, 7, 8, 9, 10, 14, 15, 16, 17, 18, 19, 20, 27, 28, 29, 30, 31, 32, 33, 34, 45, 46, 47, 48, 57, 58, 98, 99, 100, 101, 109, 110, 117, 118, 119, 120, 121, 122, 125, 126, 127, 130, 131, 132, 133, 137, 149, 150, 151, 152, 158, 159, 160, 162, 163, 164}
VERIFIED = {1, 123, 124, 136, 140, 144, 146, 147, 170, 171}
LOC = {
    "docs": "docs/plans/phase3/",
    "ci": ".github/workflows/ci.yml",
    "settings": "backend/perchpoint/settings.py",
}


def status(number: int) -> str:
    if number in VERIFIED:
        return "verified"
    if number in DEFERRED:
        return "owner-deferred"
    if number in BLOCKED:
        return "externally blocked"
    if number in FUTURE:
        return "future-live policy"
    return "implemented"


def location(number: int) -> str:
    specific = {
        13: "docs/plans/phase3/ACCOUNT_OWNERSHIP.md",
        24: "docker-compose.yml",
        90: ".github/workflows/ci.yml",
        113: "backend/.env.example",
        136: "scripts/phase3_restore_drill.py",
        141: "docs/plans/phase3/SENTRY.md",
        143: "backend/perchpoint/routes.py",
        146: "backend/perchpoint/routes.py",
        165: "scripts/phase3_compose.ps1",
        168: "docs/plans/phase3/LOCAL_DOCKER.md",
        174: "docs/plans/phase3/OWNER_DIRECTIVE.md",
    }
    if number in specific:
        return specific[number]
    if number in DEFERRED:
        return "docs/plans/phase3/OWNER_DIRECTIVE.md"
    if number in BLOCKED and number in {37, 38, 41, 42, 45, 111, 128, 129, 141, 148, 149, 161}:
        return "docs/plans/phase3/HANDOFF.md"
    if number >= 125:
        return "docs/plans/phase3/RUNBOOKS.md"
    if 49 <= number <= 97:
        return ".github/workflows/ci.yml"
    if number in {123, 124}:
        return "backend/perchpoint/settings.py"
    return "docs/plans/phase3/APPROVED_CUSTOMIZATION_ANSWERS.md"


parts = ["# Approved Phase 3 customization answers", "", "Provenance: Nathan approved all 174 Phase 3 recommendations in the 2026-09-25 implementation prompt.", "", "This register does not rewrite the Phase 2 Q1–Q120 record. Related map: [ANSWER_TRACEABILITY.md](ANSWER_TRACEABILITY.md).", ""]
rows = ["# Phase 3 answer traceability", "", "Source register: [APPROVED_CUSTOMIZATION_ANSWERS.md](APPROVED_CUSTOMIZATION_ANSWERS.md).", "", "| Question | Status | Location |", "|---|---|---|"]
for number, answer in enumerate(LINES, start=1):
    state = status(number)
    place = location(number)
    parts.append(f"### Q{number}")
    parts.append(f"- Answer: {answer}")
    parts.append(f"- Interpretation: Enforce this decision in repository configuration or a runbook. Do not treat a future live control as already executed.")
    parts.append(f"- Location: {place}")
    parts.append(f"- Evidence: See docs/plans/phase3/ACCEPTANCE.md for the command or the external blocker.")
    parts.append(f"- Status: {state}")
    parts.append("- Dependency: Hosted execution needs HawkVision-owned accounts. Local policy does not.")
    parts.append("")
    rows.append(f"| Q{number} | {state} | {place} |")
out = ROOT / "docs" / "plans" / "phase3"
out.mkdir(parents=True, exist_ok=True)
(out / "APPROVED_CUSTOMIZATION_ANSWERS.md").write_text("\n".join(parts) + "\n", encoding="utf-8")
(out / "ANSWER_TRACEABILITY.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
print("wrote", len(LINES))
