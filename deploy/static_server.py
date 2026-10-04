"""Serve the production frontend and proxy /api without a second web server package."""
from __future__ import annotations

import hashlib
import mimetypes
import os
import sys
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(os.environ.get("WEB_ROOT", "/srv/web")).resolve()
API = os.environ.get("API_UPSTREAM", "http://api:8000").rstrip("/")
FORWARDED = {
    "accept",
    "authorization",
    "content-type",
    "cookie",
    "if-match",
    "origin",
    "range",
    "referer",
    "x-perchpoint-audience",
    "x-perchpoint-csrf",
    "x-perchpoint-document-token",
    "x-perchpoint-signature",
    "x-perchpoint-worker",
    "x-request-id",
}
RESPONSE_FORWARDED = {
    "accept-ranges",
    "content-disposition",
    "content-range",
    "location",
    "retry-after",
    "set-cookie",
    "x-request-id",
}
MAX_BODY = 1_000_000
COMPRESSIBLE = {".html", ".js", ".css", ".svg", ".json", ".txt", ".map", ".xml"}
MIME = {
    ".js": "text/javascript",
    ".css": "text/css",
    ".html": "text/html; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json",
    ".txt": "text/plain; charset=utf-8",
    ".map": "application/json",
    ".xml": "application/xml",
    ".woff2": "font/woff2",
    ".avif": "image/avif",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".ico": "image/x-icon",
}
CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "style-src-attr 'none'; "
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


def parse_accept_encoding(header: str | None) -> dict[str, float]:
    found: dict[str, float] = {}
    if not header:
        return found
    for part in header.split(","):
        bits = [item.strip() for item in part.split(";") if item.strip()]
        if not bits:
            continue
        coding = bits[0].lower()
        if not coding.replace("-", "").isalnum():
            continue
        quality = 1.0
        valid = True
        for bit in bits[1:]:
            if not bit.lower().startswith("q="):
                continue
            try:
                quality = float(bit[2:])
            except ValueError:
                valid = False
        if not valid or quality < 0 or quality > 1:
            quality = 0.0
        found[coding] = quality
    return found


def choose_encoding(header: str | None, available: dict[str, bytes]) -> str | None:
    parsed = parse_accept_encoding(header)
    if not parsed:
        return None
    ranked: list[tuple[float, int, str]] = []
    for index, coding in enumerate(("br", "gzip")):
        quality = parsed.get(coding, 0)
        if coding in available and quality > 0:
            ranked.append((quality, -index, coding))
    if not ranked:
        return None
    ranked.sort(reverse=True)
    return ranked[0][2]


def published_files(root: Path) -> tuple[dict[str, bytes], dict[str, dict[str, bytes]], dict[str, float]]:
    """Load build files once so request paths are never joined onto the filesystem."""
    published: dict[str, bytes] = {}
    encoded: dict[str, dict[str, bytes]] = {}
    modified: dict[str, float] = {}
    if not root.is_dir():
        return published, encoded, modified
    staged: dict[str, bytes] = {}
    for item in root.rglob("*"):
        if item.is_file():
            staged["/" + item.relative_to(root).as_posix()] = item.read_bytes()
            modified["/" + item.relative_to(root).as_posix()] = item.stat().st_mtime
    for path, payload in staged.items():
        if path.endswith(".br"):
            encoded.setdefault(path[:-3], {})["br"] = payload
        elif path.endswith(".gz"):
            encoded.setdefault(path[:-3], {})["gzip"] = payload
        else:
            published[path] = payload
    return published, encoded, modified


def content_type_for(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix in MIME:
        return MIME[suffix]
    guessed = mimetypes.guess_type(path.rsplit("/", 1)[-1])[0]
    return guessed or "application/octet-stream"


def etag_for(payload: bytes) -> str:
    return '"' + hashlib.sha256(payload).hexdigest()[:32] + '"'


PUBLISHED, ENCODED, MODIFIED = published_files(ROOT)


def resolve_path(path: str) -> str | None:
    if path in {"", "/"}:
        return "/index.html" if "/index.html" in PUBLISHED else None
    if path in PUBLISHED:
        return path
    suffix = Path(path).suffix
    if suffix:
        return None
    if "/shell.html" in PUBLISHED:
        return "/shell.html"
    return "/index.html" if "/index.html" in PUBLISHED else None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_HEAD(self) -> None:
        self.do_GET()

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
            self._send(413, b'{"status":"too_large"}', "application/json", "/api")
            return
        body = self.rfile.read(length) if length else None
        headers = {name: self.headers[name] for name in FORWARDED if name in self.headers}
        request = Request(API + self.path, data=body, headers=headers, method=self.command)
        try:
            with urlopen(request, timeout=30) as upstream:
                payload = upstream.read(8_000_000)
                content_type = upstream.headers.get("content-type", "application/json")
                response_headers = [
                    (name, value)
                    for name in RESPONSE_FORWARDED
                    for value in upstream.headers.get_all(name, [])
                ]
                self._send(
                    upstream.status,
                    payload,
                    content_type.split(";", 1)[0].strip() or "application/json",
                    "/api",
                    response_headers=response_headers,
                )
        except HTTPError as exc:
            payload = exc.read(8_000_000)
            response_headers = [
                (name, value)
                for name in RESPONSE_FORWARDED
                for value in exc.headers.get_all(name, [])
            ]
            self._send(
                exc.code,
                payload,
                "application/json",
                "/api",
                response_headers=response_headers,
            )
        except URLError:
            self._send(502, b'{"status":"unavailable"}', "application/json", "/api")

    def _file(self, path: str) -> None:
        chosen = resolve_path(path)
        if chosen is None or chosen not in PUBLISHED:
            self._send(404, b"Not found", "text/plain", path)
            return
        payload = PUBLISHED[chosen]
        encoding = None
        if Path(chosen).suffix.lower() in COMPRESSIBLE:
            encoding = choose_encoding(self.headers.get("Accept-Encoding"), ENCODED.get(chosen, {}))
            if encoding:
                payload = ENCODED[chosen][encoding]
        self._send(200, payload, content_type_for(chosen), chosen, encoding, MODIFIED.get(chosen))

    def _send(
        self,
        status: int,
        payload: bytes,
        content_type: str,
        path: str,
        encoding: str | None = None,
        modified: float | None = None,
        response_headers: list[tuple[str, str]] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(payload)))
        self.send_header("etag", etag_for(payload))
        if modified is not None:
            self.send_header("last-modified", formatdate(modified, usegmt=True))
        if encoding:
            self.send_header("content-encoding", encoding)
        if Path(path).suffix.lower() in COMPRESSIBLE:
            self.send_header("vary", "Accept-Encoding")
        for name, value in security_headers(content_type, path).items():
            self.send_header(name, value)
        for name, value in response_headers or []:
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def log_message(self, fmt: str, *args) -> None:
        path = self.path.split("?", 1)[0]
        sys.stderr.write(f"{self.command} {path}\n")


def main() -> None:
    print(f"serving {ROOT} files={len(PUBLISHED)}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()


if __name__ == "__main__":
    main()
