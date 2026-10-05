"""Application journey against live MinIO and ClamAV. Skipped unless PHASE5_LIVE_SERVICES=1."""
from __future__ import annotations

import logging
import os
import urllib.request
import zipfile
import io

import fitz
import pytest
from fastapi.testclient import TestClient

from perchpoint.routes import create_app
from tests.phase5.test_canonical import _auth, _login
from tests.phase5.test_closeout import _property, _upload, _worker_headers

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE5_LIVE_SERVICES") != "1",
    reason="live MinIO and ClamAV are outside the default suite",
)


def _png() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 140), "Hawthorn boiler inspection")
    image = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
    document.close()
    return image


def test_live_api_access_export_and_ocr(monkeypatch, caplog):
    monkeypatch.setenv("PHASE5_OBJECT_STORE", "s3")
    monkeypatch.setenv("PHASE5_S3_ENDPOINT", os.environ.get("PHASE5_S3_ENDPOINT", "http://127.0.0.1:9000"))
    monkeypatch.setenv("PHASE5_S3_ACCESS_KEY", os.environ.get("PHASE5_S3_ACCESS_KEY", "local-only-not-production"))
    monkeypatch.setenv("PHASE5_S3_SECRET_KEY", os.environ.get("PHASE5_S3_SECRET_KEY", "local-only-not-production"))
    monkeypatch.setenv("PHASE5_S3_BUCKET", "perchpoint-documents")
    monkeypatch.setenv("PHASE5_SCANNER_MODE", "live")
    monkeypatch.setenv("PHASE5_CLAMAV_HOST", os.environ.get("PHASE5_CLAMAV_HOST", "127.0.0.1"))
    monkeypatch.setenv("PHASE5_CLAMAV_PORT", os.environ.get("PHASE5_CLAMAV_PORT", "3310"))
    monkeypatch.setenv("PHASE5_TESSERACT_IMAGE", "perchpoint-api:phase5-closeout")
    caplog.set_level(logging.INFO, logger="perchpoint")
    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    property_id = _property(client, token)
    text_upload = _upload(client, token, property_id, "note.txt", b"Hawthorn boiler inspection note\n", "text/plain", "Hawthorn text")
    assert text_upload.status_code == 201, text_upload.text
    image_upload = _upload(client, token, property_id, "scan.png", _png(), "image/png", "Hawthorn scan")
    assert image_upload.status_code == 201, image_upload.text
    assert image_upload.json()["lifecycle"] == "available"
    for _ in range(6):
        processed = client.post("/api/v2/phase5/jobs/process", headers=_worker_headers())
        assert processed.status_code == 200, processed.text
    found = client.get("/api/v2/search", headers=_auth(token), params={"q": "Hawthorn"})
    assert found.status_code == 200, found.text
    assert any(item["title"].startswith("Hawthorn") for item in found.json()["results"])
    document_id = image_upload.json()["id"]
    access = client.post(f"/api/v2/documents/{document_id}/access", headers=_auth(token))
    assert access.status_code == 200, access.text
    signed = access.json()["presigned_url"]
    assert signed and "X-Amz-Signature" in signed
    assert "X-Amz-Signature" not in " ".join(record.getMessage() for record in caplog.records)
    with urllib.request.urlopen(signed) as response:
        assert response.read()[:8] == b"\x89PNG\r\n\x1a\n"
    content = client.get(
        f"/api/v2/documents/{document_id}/content",
        headers={**_auth(token), "X-PerchPoint-Document-Token": access.json()["token"], "Range": "bytes=0-7"},
    )
    assert content.status_code == 200
    assert "no-store" in content.headers["cache-control"]
    assert content.content == b"\x89PNG\r\n\x1a\n"
    exported = client.post(
        "/api/v2/exports",
        headers=_auth(token),
        json={"document_ids": [document_id], "idempotency_key": "live-export-" + document_id[:8]},
    )
    assert exported.status_code == 201, exported.text
    package = client.get(f"/api/v2/exports/{exported.json()['id']}/content", headers=_auth(token))
    assert package.status_code == 200
    assert package.content[:2] == b"PK"
    with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
        assert "manifest.json" in archive.namelist()
    outsider = _login(client, "isolation.synthetic@example.com")
    hidden = client.post(f"/api/v2/documents/{document_id}/access", headers=_auth(outsider))
    assert hidden.status_code == 404
    leaked = client.get("/api/v2/search", headers=_auth(outsider), params={"q": "Hawthorn"})
    assert all(item["resource_id"] != document_id for item in leaked.json()["results"])
