"""Apply stored provider facts outside the API process. This process does not create a financial intent."""
from __future__ import annotations

import os
import time

from perchpoint.phase17_payments import dispatch_due_autopay, process_provider_inbox
from perchpoint.phase18_assistance import apply_queued_receipts
from perchpoint.settings import Settings


def main() -> None:
    os.environ.pop("PHASE2_ADMIN_URL", None)
    os.environ.pop("PHASE2_MIGRATOR_URL", None)
    os.environ["PHASE17_RESTRICTED_WORKER"] = "1"
    settings = Settings.load()
    print("phase17-worker-ready", flush=True)
    if os.environ.get("PHASE18_WORKER_ONCE") == "1":
        assistance = apply_queued_receipts(settings)
        print(f"phase18-worker-once {assistance['applied']}", flush=True)
        return
    while True:
        dispatched = dispatch_due_autopay(settings)
        if dispatched["dispatched"]:
            print(f"phase17-worker-autopay {dispatched['dispatched']}", flush=True)
        result = process_provider_inbox(settings)
        if result["applied"]:
            print(f"phase17-worker-applied {result['applied']}", flush=True)
        assistance = apply_queued_receipts(settings)
        if assistance["applied"]:
            print(f"phase18-worker-applied {assistance['applied']}", flush=True)
        time.sleep(0.25)


if __name__ == "__main__":
    main()
