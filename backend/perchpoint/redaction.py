"""Operational-log redaction. This is not the business audit trail."""
from __future__ import annotations

SECRET_MARKERS = (
    "password",
    "authorization",
    "cookie",
    "token",
    "secret",
    "dsn",
    "credential",
    "api_key",
    "apikey",
)


def redact(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            name = str(key).lower().replace("-", "_")
            if any(marker in name for marker in SECRET_MARKERS):
                cleaned[key] = "[redacted]"
            else:
                cleaned[key] = redact(item)
        return cleaned
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
