"""Validate the Phase 4 Q1–Q150 register."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "plans" / "phase4" / "APPROVED_CUSTOMIZATION_ANSWERS.md"
TRACE = ROOT / "docs" / "plans" / "phase4" / "ANSWER_TRACEABILITY.md"
DECISIONS = ROOT / "docs" / "governance" / "APPROVED_DECISION_REGISTER.md"
REQUIREMENTS = ROOT / "docs" / "governance" / "REQUIREMENTS_TRACEABILITY.md"
FIELDS = ("Answer", "Interpretation", "Location", "Evidence", "Status", "Dependency", "Owner")
ALLOWED = {"implemented", "verified", "externally blocked", "owner-deferred", "future-live policy", "non-applicable"}
IMPLEMENTED = {"implemented", "verified"}
DEFERRED = {"owner-deferred", "externally blocked", "future-live policy"}


def field_map(body: str) -> dict[str, str]:
    found = {}
    for field in FIELDS:
        match = re.search(rf"^- {field}: (.*)$", body, re.M)
        found[field] = match.group(1).strip() if match else ""
    return found


def main() -> int:
    text = REGISTER.read_text(encoding="utf-8")
    trace = TRACE.read_text(encoding="utf-8")
    decisions = set(re.findall(r"PP-DEC-\d{3}", DECISIONS.read_text(encoding="utf-8")))
    requirements = set(re.findall(r"## (PP-(?!DEC)[A-Z]+-\d{3})", REQUIREMENTS.read_text(encoding="utf-8")))
    errors: list[str] = []
    ids = [int(item) for item in re.findall(r"^### Q(\d+)\s*$", text, re.M)]
    if ids != list(range(1, 151)):
        missing = [n for n in range(1, 151) if n not in ids]
        dupes = sorted({n for n in ids if ids.count(n) > 1})
        errors.append(f"ids={len(ids)} missing={missing} duplicates={dupes}")
    traced = [int(item) for item in re.findall(r"^\| Q(\d+) \|", trace, re.M)]
    if traced != list(range(1, 151)):
        orphan = sorted(set(traced) - set(ids))
        missing = [n for n in range(1, 151) if n not in traced]
        errors.append(f"trace count={len(traced)} missing={missing} orphan={orphan}")
    for number in range(1, 151):
        match = re.search(rf"^### Q{number}\n(.*?)(?=^### Q|\Z)", text, re.S | re.M)
        if not match:
            continue
        values = field_map(match.group(1))
        for field, value in values.items():
            if not value:
                errors.append(f"Q{number} empty {field}")
        if values["Status"] not in ALLOWED:
            errors.append(f"Q{number} bad status {values['Status']}")
        for decision in re.findall(r"PP-DEC-\d{3}", match.group(1)):
            if decision not in decisions:
                errors.append(f"Q{number} unresolved decision {decision}")
        for requirement in re.findall(r"PP-(?!DEC)[A-Z]+-\d{3}", match.group(1)):
            if requirement not in requirements:
                errors.append(f"Q{number} unresolved requirement {requirement}")
        if values["Status"] in IMPLEMENTED:
            evidence = values["Evidence"].strip("`")
            if evidence in {"", "none"} or not (ROOT / evidence).exists():
                errors.append(f"Q{number} implemented without evidence")
        if values["Status"] in DEFERRED and values["Owner"] in {"", "none", "unassigned"}:
            errors.append(f"Q{number} deferred without owner")
    for decision in re.findall(r"PP-DEC-\d{3}", trace):
        if decision not in decisions:
            errors.append(f"trace unresolved decision {decision}")
    for requirement in re.findall(r"PP-(?!DEC)[A-Z]+-\d{3}", trace):
        if requirement not in requirements:
            errors.append(f"trace unresolved requirement {requirement}")
    if errors:
        print("\n".join(errors))
        return 1
    print("Validated 150 unique Phase 4 answers and trace rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
