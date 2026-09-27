"""Live MinIO and ClamAV proofs. Skipped unless PHASE5_LIVE_SERVICES=1."""
from __future__ import annotations

import os
import urllib.error
import urllib.request

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE5_LIVE_SERVICES") != "1",
    reason="live MinIO and ClamAV are outside the default suite",
)

EICAR = bytes(
    [
        0x58, 0x35, 0x4F, 0x21, 0x50, 0x25, 0x40, 0x41, 0x50, 0x5B, 0x34, 0x5C,
        0x50, 0x5A, 0x58, 0x35, 0x34, 0x28, 0x50, 0x5E, 0x29, 0x37, 0x43, 0x43,
        0x29, 0x37, 0x7D, 0x24, 0x45, 0x49, 0x43, 0x41, 0x52, 0x2D, 0x53, 0x54,
        0x41, 0x4E, 0x44, 0x41, 0x52, 0x44, 0x2D, 0x41, 0x4E, 0x54, 0x49, 0x56,
        0x49, 0x52, 0x55, 0x53, 0x2D, 0x54, 0x45, 0x53, 0x54, 0x2D, 0x46, 0x49,
        0x4C, 0x45, 0x21, 0x24, 0x48, 0x2B, 0x48, 0x2A,
    ]
)


def test_live_clamav_detects_eicar_and_outage_is_not_clean(monkeypatch):
    monkeypatch.setenv("PHASE5_SCANNER_MODE", "live")
    monkeypatch.setenv("PHASE5_CLAMAV_HOST", os.environ.get("PHASE5_CLAMAV_HOST", "127.0.0.1"))
    monkeypatch.setenv("PHASE5_CLAMAV_PORT", os.environ.get("PHASE5_CLAMAV_PORT", "3310"))
    from perchpoint.phase5_files import _clamav_instream, _external_scan

    host = os.environ["PHASE5_CLAMAV_HOST"]
    port = int(os.environ["PHASE5_CLAMAV_PORT"])
    assert _clamav_instream(host, port, EICAR) == "suspicious"
    assert _external_scan(b"%PDF-1.4 synthetic clean document") == "clean"
    monkeypatch.setenv("PHASE5_CLAMAV_HOST", "127.0.0.1")
    monkeypatch.setenv("PHASE5_CLAMAV_PORT", "1")
    assert _external_scan(b"%PDF-1.4 synthetic clean document") == "unavailable"


def test_live_minio_presign_is_private_and_cleaned_up(monkeypatch):
    monkeypatch.setenv("PHASE5_OBJECT_STORE", "s3")
    monkeypatch.setenv("PHASE5_S3_ENDPOINT", os.environ.get("PHASE5_S3_ENDPOINT", "http://127.0.0.1:9000"))
    monkeypatch.setenv("PHASE5_S3_ACCESS_KEY", os.environ.get("PHASE5_S3_ACCESS_KEY", "local-only-not-production"))
    monkeypatch.setenv("PHASE5_S3_SECRET_KEY", os.environ.get("PHASE5_S3_SECRET_KEY", "local-only-not-production"))
    monkeypatch.setenv("PHASE5_S3_BUCKET", os.environ.get("PHASE5_S3_BUCKET", "perchpoint-documents"))
    from perchpoint.phase5_files import delete_object, ensure_bucket, object_exists, presign_get, read_object, write_object

    ensure_bucket()
    ensure_bucket()
    key = "org/00000000-0000-4000-8000-000000000001/staged/00112233445566778899aabbccddeeff"
    payload = b"phase5-minio-proof"
    write_object(key, payload)
    write_object(key, payload)
    try:
        assert read_object(key) == payload
        url = presign_get(key, 60)
        assert url and "X-Amz-Signature" in url
        with urllib.request.urlopen(url) as response:
            assert response.read() == payload
        with pytest.raises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(os.environ["PHASE5_S3_ENDPOINT"] + "/" + os.environ["PHASE5_S3_BUCKET"] + "/" + key)
        assert denied.value.code == 403
    finally:
        delete_object(key)
    assert not object_exists(key)
