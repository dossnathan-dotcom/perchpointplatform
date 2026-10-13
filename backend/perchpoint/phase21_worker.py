"""Escalate overdue callbacks outside the API process. Escalation is not acceptance."""
from __future__ import annotations

import os
import time

from perchpoint.phase21_calls import process_callbacks
from perchpoint.settings import Settings


def main() -> None:
    os.environ.setdefault("PHASE17_RESTRICTED_WORKER", "1")
    settings = Settings.load()
    print("phase21-worker-ready", flush=True)
    if os.environ.get("PHASE21_WORKER_ONCE") == "1":
        result = process_callbacks(settings)
        print(f"phase21-worker-once {result['applied']}", flush=True)
        return
    while True:
        result = process_callbacks(settings)
        if result["applied"]:
            print(f"phase21-worker-applied {result['applied']}", flush=True)
        time.sleep(0.25)


if __name__ == "__main__":
    main()
