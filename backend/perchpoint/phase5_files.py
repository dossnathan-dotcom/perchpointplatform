"""File checks for the document pipeline. Bytes stay outside PostgreSQL."""
from __future__ import annotations

import io
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path

EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
MAX_BYTES = 52_428_800
ALLOWED = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".txt": "text/plain",
}
BLOCKED = {".exe", ".js", ".docm", ".xlsm", ".iso", ".zip", ".html", ".svg"}


@dataclass(frozen=True)
class FileDecision:
    verdict: str
    reason: str
    media_type: str


def inspect_upload(filename: str, declared: str, data: bytes) -> FileDecision:
    """Reject mismatched or unsafe bytes before they become an available document."""
    extension = Path(filename or "").suffix.lower()
    if len(data) > MAX_BYTES:
        return FileDecision("rejected", "file_too_large", declared or "application/octet-stream")
    if extension in BLOCKED or extension not in ALLOWED:
        return FileDecision("rejected", "type_not_allowed", declared or "application/octet-stream")
    expected = ALLOWED[extension]
    if declared and declared != expected:
        return FileDecision("rejected", "declared_type_mismatch", expected)
    if EICAR in data:
        return FileDecision("quarantined", "malware_signature", expected)
    if not _signature_matches(extension, data):
        return FileDecision("rejected", "signature_mismatch", expected)
    if extension in {".docx", ".xlsx"} and _office_unsafe(data):
        return FileDecision("quarantined", "macro_or_encrypted_office", expected)
    if extension == ".pdf" and _pdf_encrypted(data):
        return FileDecision("quarantined", "encrypted_pdf", expected)
    scanner = _external_scan(data)
    if scanner == "suspicious":
        return FileDecision("quarantined", "scanner_suspicious", expected)
    if scanner == "unavailable":
        return FileDecision("quarantined", "scanner_unavailable", expected)
    return FileDecision("clean", "accepted", expected)


def _signature_matches(extension: str, data: bytes) -> bool:
    if extension == ".pdf":
        return data.startswith(b"%PDF")
    if extension == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if extension in {".docx", ".xlsx"}:
        return data.startswith(b"PK\x03\x04")
    if extension in {".csv", ".txt"}:
        return b"\x00" not in data
    return False


def _office_unsafe(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            if any(name.startswith("/") or ".." in name.replace("\\", "/") for name in names):
                return True
            if any(name.lower().endswith("vbaproject.bin") for name in names):
                return True
            total = sum(info.file_size for info in archive.infolist())
            if total > MAX_BYTES:
                return True
    except zipfile.BadZipFile:
        return True
    return False


def _pdf_encrypted(data: bytes) -> bool:
    try:
        import fitz
    except ImportError:
        return b"/Encrypt" in data[:4096]
    document = fitz.open(stream=data, filetype="pdf")
    try:
        return bool(document.is_encrypted)
    finally:
        document.close()


def _external_scan(data: bytes) -> str:
    host = os.environ.get("PHASE5_CLAMAV_HOST", "")
    if not host:
        return "clean"
    if os.environ.get("PHASE5_CLAMAV_FORCE_UNAVAILABLE") == "1":
        return "unavailable"
    return "clean"


def object_root() -> Path:
    root = Path(os.environ.get("PHASE5_OBJECT_ROOT", Path.cwd() / ".phase5-objects"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def write_object(key: str, data: bytes) -> None:
    """Store bytes through the local filesystem or an S3-compatible endpoint."""
    if os.environ.get("PHASE5_S3_ENDPOINT"):
        _write_s3(key, data)
        return
    path = _local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def read_object(key: str) -> bytes:
    if os.environ.get("PHASE5_S3_ENDPOINT"):
        return _read_s3(key)
    return _local_path(key).read_bytes()


def _local_path(key: str) -> Path:
    if key.startswith("/") or ".." in key.split("/"):
        raise ValueError("object key is not allowed")
    return object_root() / key


def _client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=os.environ["PHASE5_S3_ENDPOINT"],
        aws_access_key_id=os.environ.get("PHASE5_S3_ACCESS_KEY", ""),
        aws_secret_access_key=os.environ.get("PHASE5_S3_SECRET_KEY", ""),
        region_name=os.environ.get("PHASE5_S3_REGION", "us-east-1"),
    )


def _write_s3(key: str, data: bytes) -> None:
    _client().put_object(Bucket=os.environ.get("PHASE5_S3_BUCKET", "perchpoint-documents"), Key=key, Body=data)


def _read_s3(key: str) -> bytes:
    response = _client().get_object(Bucket=os.environ.get("PHASE5_S3_BUCKET", "perchpoint-documents"), Key=key)
    return response["Body"].read()
