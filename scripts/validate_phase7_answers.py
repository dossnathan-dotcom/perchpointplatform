"""Validate Phase 7 decisions and traceability as substantive records."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANSWERS = ROOT / "docs/plans/phase7/APPROVED_CUSTOMIZATION_ANSWERS.md"
TRACE = ROOT / "docs/plans/phase7/ANSWER_TRACEABILITY.md"
ROW = re.compile(r"^\| Q(\d+) \| (.+) \|$")
PLACEHOLDER = re.compile(r"\b(?:tbd|todo|unknown|n/?a|same as above|placeholder)\b", re.I)


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


def validate_substance(answers: dict[int, str], trace: dict[int, str]) -> list[str]:
    errors: list[str] = []
    normalized: dict[str, list[int]] = {}
    for number, answer in answers.items():
        cleaned = " ".join(answer.lower().split())
        normalized.setdefault(cleaned, []).append(number)
        if len(answer) < 24 or PLACEHOLDER.search(answer):
            errors.append(f"Q{number} answer is not substantive")
        if answer[-1:] not in {".", "!", "?"}:
            errors.append(f"Q{number} answer is not a complete statement")
    for _value, numbers in normalized.items():
        if len(numbers) > 1:
            errors.append(f"duplicate decision text: Q{numbers[0]} and Q{numbers[1]}")
    for number, mapping in trace.items():
        if PLACEHOLDER.search(mapping):
            errors.append(f"Q{number} traceability is a placeholder")
            continue
        references = [item.strip().replace("\\", "/") for item in mapping.split(";") if item.strip()]
        if not references:
            errors.append(f"Q{number} traceability is empty")
            continue
        code_references = 0
        for reference in references:
            target = ROOT / reference
            if not target.exists():
                errors.append(f"Q{number} traceability target absent: {reference}")
            if reference.startswith(("backend/", "frontend/", "scripts/", ".github/")):
                code_references += 1
        if code_references == 0:
            errors.append(f"Q{number} has no implementation trace")
    return errors


def main() -> None:
    answers = questions(ANSWERS)
    trace = questions(TRACE)
    expected = set(range(1, 121))
    if set(answers) != expected:
        raise SystemExit(f"answer questions missing or unexpected: {sorted(expected - set(answers))[:8]}")
    if set(trace) != expected:
        raise SystemExit("traceability does not cover Q1–Q120")
    errors = validate_substance(answers, trace)
    if errors:
        raise SystemExit("phase7 answer completeness failed:\n- " + "\n- ".join(errors))
    print("phase7 answers 120 substantive and traced")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(exc)
        sys.exit(1)
