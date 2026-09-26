"""Provider-neutral public-form abuse boundary. No CAPTCHA and no retained raw IP address."""
from __future__ import annotations

import hashlib
import os
import time
from collections import deque

_WINDOWS: dict[str, deque[float]] = {}


def client_digest(host: str) -> str:
    return hashlib.sha256(host.encode("utf-8")).hexdigest()[:16]


def assess_inquiry(body: dict, host: str, now: float | None = None) -> str | None:
    """Return a generic rejection code, or None when the request may proceed."""
    if str(body.get("company_website") or "").strip():
        return "rejected"
    message = str(body.get("message") or "")
    if len(message) > 4000:
        return "rejected"
    started = body.get("started_at_ms")
    minimum = int(os.environ.get("PHASE4_ABUSE_MIN_MS", "0") or "0")
    current = time.time() if now is None else now
    if started is not None and minimum > 0:
        try:
            elapsed_ms = current * 1000 - float(started)
        except (TypeError, ValueError):
            return "rejected"
        if elapsed_ms < minimum:
            return "rejected"
    limit = int(os.environ.get("PHASE4_ABUSE_LIMIT", "1000") or "1000")
    digest = client_digest(host or "unknown")
    window = _WINDOWS.setdefault(digest, deque())
    cutoff = current - 60
    while window and window[0] < cutoff:
        window.popleft()
    if len(window) >= limit:
        return "rate_limited"
    window.append(current)
    return None
