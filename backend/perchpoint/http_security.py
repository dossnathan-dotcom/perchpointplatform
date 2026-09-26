"""Shared response-header policy for the API and the production static server."""
from __future__ import annotations

import os

CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "worker-src 'self'; "
    "form-action 'self'"
)


def security_headers(content_type: str, path: str = "/") -> dict[str, str]:
    headers = {
        "content-security-policy": CSP,
        "referrer-policy": "no-referrer",
        "x-content-type-options": "nosniff",
        "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=()",
        "x-frame-options": "DENY",
        "cross-origin-opener-policy": "same-origin",
        "cross-origin-resource-policy": "same-origin",
    }
    if os.environ.get("PHASE4_ENABLE_HSTS") == "1":
        headers["strict-transport-security"] = "max-age=31536000; includeSubDomains"
    hashed_asset = "/static/" in path and any(path.endswith(suffix) for suffix in (".js", ".css", ".woff2", ".png", ".jpg", ".webp", ".avif", ".svg"))
    if hashed_asset:
        headers["cache-control"] = "public, max-age=31536000, immutable"
    elif content_type.startswith("text/html") or path.startswith("/api/") or content_type.startswith("application/json"):
        headers["cache-control"] = "no-store"
    else:
        headers["cache-control"] = "no-store"
    return headers
