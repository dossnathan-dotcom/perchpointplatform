"""Restart the local Auth service and prove an existing account can sign in again."""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from perchpoint.phase6_provider import ProviderError, password_grant  # noqa: E402
from perchpoint.settings import Settings  # noqa: E402


def main() -> None:
    subprocess.run(["docker", "restart", "perchpoint-phase6-auth-1"], check=True)
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:9999/health", timeout=2) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(1)
    else:
        raise SystemExit("auth did not return")
    try:
        session = password_grant("ann.synthetic@example.com", Settings.load().dev_password)
    except ProviderError as exc:
        raise SystemExit(exc.code) from exc
    report = ROOT / "test_reports" / "phase6" / "auth-restart.txt"
    report.write_text(f"auth_restart=passed assurance={session.assurance} subject_present={bool(session.subject)}\n", encoding="utf-8")
    print("auth_restart=passed")


if __name__ == "__main__":
    main()
