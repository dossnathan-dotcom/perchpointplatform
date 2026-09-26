"""Conditional Sentry. Missing or placeholder DSNs disable transmission."""
from __future__ import annotations

import os

from .redaction import redact

_PLACEHOLDERS = ("replace-", "changeme", "example", "local-only-not-production")


def sentry_dsn() -> str:
    return os.environ.get("SENTRY_DSN", "").strip()


def sentry_enabled() -> bool:
    dsn = sentry_dsn()
    if not dsn:
        return False
    lowered = dsn.lower()
    if any(marker in lowered for marker in _PLACEHOLDERS):
        return False
    environment = os.environ.get("PHASE3_ENVIRONMENT", "local")
    if environment in {"staging", "production"} and (lowered.startswith("http://") or "localhost" in lowered):
        return False
    return True


def before_send(event, hint):
    del hint
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        if isinstance(request.get("headers"), dict):
            request["headers"] = redact(request["headers"])
    return redact(event)


def init_sentry() -> bool:
    if not sentry_enabled():
        return False
    try:
        import sentry_sdk
    except ImportError:
        return False
    environment = os.environ.get("PHASE3_ENVIRONMENT", "local")
    release = os.environ.get("PHASE3_RELEASE") or os.environ.get("PHASE3_COMMIT") or None
    sample = os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0")
    try:
        rate = float(sample)
    except ValueError:
        rate = 0.0
    sentry_sdk.init(
        dsn=sentry_dsn(),
        environment=environment,
        release=release,
        send_default_pii=False,
        traces_sample_rate=rate,
        before_send=before_send,
    )
    return True
