"""Validate the Phase 3 Q1–Q174 register."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "plans" / "phase3" / "APPROVED_CUSTOMIZATION_ANSWERS.md"
TRACE = ROOT / "docs" / "plans" / "phase3" / "ANSWER_TRACEABILITY.md"
FIELDS = ("Answer", "Interpretation", "Location", "Evidence", "Status", "Dependency")
ALLOWED = {"implemented", "verified", "externally blocked", "owner-deferred", "future-live policy", "non-applicable"}


def main() -> int:
    text = REGISTER.read_text(encoding="utf-8")
    ids = [int(item) for item in re.findall(r"^### Q(\d+)\s*$", text, re.M)]
    errors = []
    if ids != list(range(1, 175)):
        missing = [n for n in range(1, 175) if n not in ids]
        dupes = sorted({n for n in ids if ids.count(n) > 1})
        errors.append(f"ids={len(ids)} missing={missing} duplicates={dupes}")
    for number in range(1, 175):
        match = re.search(rf"### Q{number}\n(.*?)(?=\n### Q|\Z)", text, re.S)
        if not match:
            continue
        body = match.group(1)
        for field in FIELDS:
            if f"- {field}:" not in body:
                errors.append(f"Q{number} missing {field}")
        status = re.search(r"- Status: (.+)", body)
        if status and status.group(1).strip() not in ALLOWED:
            errors.append(f"Q{number} bad status {status.group(1)}")
    trace = TRACE.read_text(encoding="utf-8")
    traced = [int(item) for item in re.findall(r"^\| Q(\d+) \|", trace, re.M)]
    if traced != list(range(1, 175)):
        errors.append(f"trace count {len(traced)}")
    if errors:
        print("\n".join(errors))
        return 1
    print("Validated 174 unique Phase 3 answers and trace rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
