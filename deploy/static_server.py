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
                self._send(upstream.status, payload, content_type, upstream.headers.get("x-request-id"))
        except HTTPError as exc:
            payload = exc.read(8_000_000)
            self._send(exc.code, payload, exc.headers.get("content-type", "application/json"))
        except URLError:
            self._send(502, b'{"status":"unavailable"}', "application/json")

    def _file(self, path: str) -> None:
        relative = path.lstrip("/") or "index.html"
        candidate = (ROOT / relative).resolve()
        if ROOT not in candidate.parents and candidate != ROOT:
            self._send(404, b"Not found", "text/plain")
            return
        if not candidate.is_file():
            candidate = ROOT / "index.html"
        if not candidate.is_file():
            self._send(404, b"Not found", "text/plain")
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self._send(200, candidate.read_bytes(), content_type)

    def _send(self, status: int, payload: bytes, content_type: str, request_id: str | None = None) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(payload)))
        if request_id:
            self.send_header("x-request-id", request_id)
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args) -> None:
        path = self.path.split("?", 1)[0]
        sys.stderr.write(f"{self.command} {path}\n")


def main() -> None:
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()


if __name__ == "__main__":
    main()
