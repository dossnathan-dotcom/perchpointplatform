"""Fail closed unless the Phase 6 evidence files record completed local gates."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "test_reports" / "phase6"
ANSWERS = ROOT / "docs/plans/phase6/APPROVED_CUSTOMIZATION_ANSWERS.md"
TRACE = ROOT / "docs/plans/phase6/ANSWER_TRACEABILITY.md"
ROW = re.compile(r"^\| Q(\d+) \|")


def _count(path: Path) -> int:
    return len({int(match.group(1)) for line in path.read_text(encoding="utf-8").splitlines() if (match := ROW.match(line))})


def main() -> None:
    missing = []
    if _count(ANSWERS) != 160 or _count(TRACE) != 160:
        missing.append("Q1-Q160")
    scale = (REPORTS / "scale.txt").read_text(encoding="utf-8") if (REPORTS / "scale.txt").exists() else ""
    if len(re.findall(r"^round=\d+", scale, re.M)) != 3 or "cross_org=0" not in scale:
        missing.append("three benchmark rounds")
    browser = (REPORTS / "browser.txt").read_text(encoding="utf-8") if (REPORTS / "browser.txt").exists() else ""
    spec = (ROOT / "frontend/e2e/phase6-engines.spec.js").read_text(encoding="utf-8")
    if "3 passed" not in browser or "EXIT:0" not in browser or "AxeBuilder" not in spec or "320" not in spec:
        missing.append("chromium firefox webkit accessibility responsive")
    restart = (REPORTS / "auth-restart.txt").read_text(encoding="utf-8") if (REPORTS / "auth-restart.txt").exists() else ""
    if "auth_restart=passed" not in restart:
        missing.append("auth restart")
    for gate in ("clean-room.txt", "ci-head.txt", "merged-main.txt"):
        if not (REPORTS / gate).exists():
            missing.append(gate)
    if missing:
        print("phase6 acceptance incomplete: " + ", ".join(missing))
        raise SystemExit(1)
    print("phase6 acceptance passed")


if __name__ == "__main__":
    main()
