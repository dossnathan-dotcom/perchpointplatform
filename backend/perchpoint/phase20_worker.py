"""Apply maintenance escalations outside the API process. Delivery is not acceptance."""
from __future__ import annotations

import os
import time

from perchpoint.phase20_maintenance import process_escalations
from perchpoint.settings import Settings


def main() -> None:
    os.environ.setdefault("PHASE17_RESTRICTED_WORKER", "1")
    settings = Settings.load()
    print("phase20-worker-ready", flush=True)
    if os.environ.get("PHASE20_WORKER_ONCE") == "1":
        result = process_escalations(settings)
        print(f"phase20-worker-once {result['applied']}", flush=True)
        return
    while True:
        result = process_escalations(settings)
        if result["applied"]:
            print(f"phase20-worker-applied {result['applied']}", flush=True)
        time.sleep(0.25)


if __name__ == "__main__":
    main()
