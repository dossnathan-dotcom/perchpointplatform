"""Representative public-read timings against the isolated Phase 7 database."""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient

from perchpoint.routes import create_app


def main() -> int:
    client = TestClient(create_app())
    samples = []
    errors = 0
    for _ in range(30):
        started = time.perf_counter()
        response = client.get("/api/v2/public/pages/about")
        elapsed = (time.perf_counter() - started) * 1000
        samples.append(elapsed)
        if response.status_code != 200 or "9999" in response.text:
            errors += 1
    ordered = sorted(samples)
    summary = {
        "cardinality": 30,
        "errors": errors,
        "max_ms": round(ordered[-1], 2),
        "p50_ms": round(statistics.median(ordered), 2),
        "p95_ms": round(ordered[int(len(ordered) * 0.95) - 1], 2),
        "route": "/api/v2/public/pages/about",
    }
    print(json.dumps(summary))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
