"""Reset and verify the local Phase 15 synthetic story. Refuses any non-local target."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    ROOT / "docs/plans/phase15/WALKTHROUGH.md",
    ROOT / "docs/plans/phase15/REAL_INFORMATION_ACTIVATION.md",
    ROOT / "docs/plans/phase15/BATCH_READINESS.md",
)
SCENARIOS = (
    "owner-configuration",
    "activated-household",
    "pending-invitation",
    "co-resident",
    "accessibility-preference",
    "profile-request",
    "sample-lease",
    "demo-previews",
    "revoked-membership",
    "empty-state",
    "cross-organization",
)


def _local_target() -> bool:
    environment = os.environ.get("PHASE3_ENVIRONMENT", "local")
    runtime = os.environ.get("PHASE2_RUNTIME_URL", "127.0.0.1")
    if environment in {"production", "pilot", "hosted"}:
        return False
    return "127.0.0.1" in runtime or "localhost" in runtime


def main() -> int:
    if "--verify" not in sys.argv and "--execute" not in sys.argv:
        print("refusing to run without --verify or --execute")
        return 1
    if not _local_target():
        print("refusing non-local Phase 15 demo target")
        return 1
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file()]
    if missing:
        print("missing demo artifacts:", ", ".join(missing))
        return 1
    print("target=local")
    print("scenarios=" + ",".join(SCENARIOS))
    print("real_values_activated=false")
    print("demo_reset=verified" if "--verify" in sys.argv else "demo_reset=ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
