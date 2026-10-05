"""Fail fast when the configured PostgreSQL port is not accepting connections."""
from __future__ import annotations

import os
import socket
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "backend" / ".env")


def target_from_environment() -> tuple[str, int]:
    raw = os.environ.get("PHASE2_ADMIN_URL") or os.environ.get("PHASE2_MIGRATOR_URL") or ""
    if not raw:
        raise SystemExit("database preflight: PHASE2_ADMIN_URL is not configured")
    parsed = urlparse(raw)
    if not parsed.hostname or not parsed.port:
        raise SystemExit("database preflight: the configured database URL has no host and port")
    return parsed.hostname, parsed.port


def probe(host: str, port: int, attempts: int = 8, delay_seconds: float = 0.5) -> None:
    deadline = time.monotonic() + attempts * delay_seconds
    last_error = "connection was not attempted"
    while time.monotonic() <= deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                print(f"database preflight: {host}:{port} accepted a connection")
                return
        except OSError as exc:
            last_error = exc.strerror or exc.__class__.__name__
            time.sleep(delay_seconds)
    raise SystemExit(
        f"database preflight: {host}:{port} did not accept a connection before the deadline ({last_error}). "
        "Start the scoped PostgreSQL service, then rerun bootstrap or migration."
    )


def main() -> None:
    host = os.environ.get("PHASE7_PREFLIGHT_HOST")
    port = os.environ.get("PHASE7_PREFLIGHT_PORT")
    if host and port:
        probe(host, int(port), attempts=2, delay_seconds=0.2)
        return
    configured_host, configured_port = target_from_environment()
    probe(configured_host, configured_port)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        if exc.code not in (0, None):
            print(exc.code if isinstance(exc.code, str) else "database preflight failed")
        raise
