"""Serve the production frontend and proxy /api without a second web server package."""
from __future__ import annotations

import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(os.environ.get("WEB_ROOT", "/srv/web")).resolve()
API = os.environ.get("API_UPSTREAM", "http://api:8000").rstrip("/")
FORWARDED = {"accept", "authorization", "content-type", "x-request-id"}
MAX_BODY = 1_000_000
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


def security_headers(content_type: str, path: str) -> dict[str, str]:
    headers = {
        "content-security-policy": CSP,
        "referrer-policy": "no-referrer",
        "x-content-type-options": "nosniff",
        "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=()",
        "x-frame-options": "DENY",
        "cross-origin-opener-policy": "same-origin",
        "cross-origin-resource-policy": "same-origin",
        "cache-control": "public, max-age=31536000, immutable" if "/static/" in path else "no-store",
    }
    if os.environ.get("PHASE4_ENABLE_HSTS") == "1":
        headers["strict-transport-security"] = "max-age=31536000; includeSubDomains"
    return headers


def published_files(root: Path) -> dict[str, bytes]:
    """Load build files once so request paths are never joined onto the filesystem."""
    published: dict[str, bytes] = {}
    if not root.is_dir():
        return published
    for item in root.rglob("*"):
        if item.is_file():
            published["/" + item.relative_to(root).as_posix()] = item.read_bytes()
    return published


PUBLISHED = published_files(ROOT)


def media_type(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    token = value.split(";", 1)[0].strip()
    if "/" in token and all(character.isalnum() or character in "/.+-" for character in token):
        return token
    return fallback


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def do_PUT(self) -> None:
        self._handle()

    def do_PATCH(self) -> None:
        self._handle()

    def do_DELETE(self) -> None:
        self._handle()

    def do_OPTIONS(self) -> None:
        self._handle()

    def _handle(self) -> None:
        path = self.path.split("?", 1)[0]
        if path.startswith("/api/"):
            self._proxy()
            return
        self._file(path)

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > MAX_BODY:
            self._send(413, b'{"status":"too_large"}', "application/json")
            return
        body = self.rfile.read(length) if length else None
        headers = {name: self.headers[name] for name in FORWARDED if name in self.headers}
        request = Request(API + self.path, data=body, headers=headers, method=self.command)
        try:
            with urlopen(request, timeout=30) as upstream:
                payload = upstream.read(8_000_000)
                content_type = upstream.headers.get("content-type", "application/json")
                self._send(upstream.status, payload, media_type(content_type, "application/json"))
        except HTTPError as exc:
            payload = exc.read(8_000_000)
            self._send(exc.code, payload, media_type(exc.headers.get("content-type"), "application/json"))
        except URLError:
            self._send(502, b'{"status":"unavailable"}', "application/json")

    def _file(self, path: str) -> None:
        payload = PUBLISHED.get(path if path != "/" else "/index.html")
        chosen = path if payload is not None and path != "/" else "/index.html"
        if payload is None:
            payload = PUBLISHED.get("/index.html")
        if payload is None:
            self._send(404, b"Not found", "text/plain")
            return
        guessed = mimetypes.guess_type(chosen.rsplit("/", 1)[-1])[0]
        self._send(200, payload, media_type(guessed, "application/octet-stream"))

    def _send(self, status: int, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(payload)))
        for name, value in security_headers(content_type, self.path.split("?", 1)[0]).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args) -> None:
        path = self.path.split("?", 1)[0]
        sys.stderr.write(f"{self.command} {path}\n")


def main() -> None:
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()


if __name__ == "__main__":
    main()
