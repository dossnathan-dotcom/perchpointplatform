"""Require exactly 160 unique Phase 6 answers and a matching traceability row."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANSWERS = ROOT / "docs/plans/phase6/APPROVED_CUSTOMIZATION_ANSWERS.md"
TRACE = ROOT / "docs/plans/phase6/ANSWER_TRACEABILITY.md"
ROW = re.compile(r"^\| Q(\d+) \| (.+) \|$")


def questions(path: Path) -> dict[int, str]:
    found = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if not match:
            continue
        number = int(match.group(1))
        if number in found:
            raise SystemExit(f"duplicate Q{number} in {path.name}")
        if not match.group(2).strip():
            raise SystemExit(f"empty Q{number} in {path.name}")
        found[number] = match.group(2).strip()
    return found


def main() -> None:
    answers = questions(ANSWERS)
    trace = questions(TRACE)
    expected = set(range(1, 161))
    if set(answers) != expected:
        raise SystemExit(f"answer questions missing or unexpected: {sorted(expected - set(answers))[:8]}")
    if set(trace) != expected:
        raise SystemExit("traceability does not cover Q1–Q160")
    print("phase6 answers 160")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(exc)
        sys.exit(1)
