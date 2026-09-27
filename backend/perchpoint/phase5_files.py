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
        if os.environ.get("PHASE5_SCANNER_MODE", "live") == "live":
            return FileDecision("pending_scan", "scanner_unavailable", expected)
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
    """A missing or failed scanner is not a clean result."""
    if os.environ.get("PHASE5_SCANNER_MODE", "live") == "signature":
        return "clean"
    if os.environ.get("PHASE5_CLAMAV_FORCE_UNAVAILABLE") == "1":
        return "unavailable"
    host = os.environ.get("PHASE5_CLAMAV_HOST", "")
    if not host:
        return "unavailable"
    try:
        return _clamav_instream(host, int(os.environ.get("PHASE5_CLAMAV_PORT", "3310")), data)
    except OSError:
        return "unavailable"


def _clamav_instream(host: str, port: int, data: bytes) -> str:
    import socket

    timeout = float(os.environ.get("PHASE5_CLAMAV_TIMEOUT", "20"))
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(b"zINSTREAM\0")
        view = memoryview(data)
        for offset in range(0, len(data), 65536):
            piece = view[offset : offset + 65536]
            sock.sendall(len(piece).to_bytes(4, "big") + piece.tobytes())
        sock.sendall((0).to_bytes(4, "big"))
        response = b""
        while b"\0" not in response and len(response) < 4096:
            packet = sock.recv(4096)
            if not packet:
                break
            response += packet
    text = response.split(b"\0", 1)[0].decode(errors="replace")
    if "FOUND" in text:
        return "suspicious"
    if text.endswith("OK"):
        return "clean"
    return "unavailable"


def object_root() -> Path:
    root = Path(os.environ.get("PHASE5_OBJECT_ROOT", Path.cwd() / ".phase5-objects"))
    root.mkdir(parents=True, exist_ok=True)
    return root


NAMESPACES = {"staged", "accepted", "quarantined", "derived", "exports"}


def object_key(organization: str, namespace: str) -> str:
    from uuid import uuid4

    if namespace not in NAMESPACES:
        raise ValueError("object namespace is not allowed")
    return f"org/{organization}/{namespace}/{uuid4().hex}"


def store_mode() -> str:
    explicit = os.environ.get("PHASE5_OBJECT_STORE", "")
    if explicit:
        return explicit
    if os.environ.get("PHASE5_S3_ENDPOINT"):
        return "s3"
    return "filesystem"


def write_object(key: str, data: bytes) -> None:
    """Store bytes through the configured object store. Keys stay organization-scoped."""
    _require_key(key)
    if store_mode() == "s3":
        _write_s3(key, data)
        return
    path = _local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def read_object(key: str) -> bytes:
    _require_key(key)
    if store_mode() == "s3":
        return _read_s3(key)
    return _local_path(key).read_bytes()


def delete_object(key: str) -> None:
    _require_key(key)
    if store_mode() == "s3":
        _client().delete_object(Bucket=_bucket(), Key=key)
        return
    path = _local_path(key)
    if path.exists():
        path.unlink()


def object_exists(key: str) -> bool:
    _require_key(key)
    if store_mode() == "s3":
        from botocore.exceptions import ClientError

        try:
            _client().head_object(Bucket=_bucket(), Key=key)
        except ClientError:
            return False
        return True
    return _local_path(key).exists()


def list_objects(prefix: str) -> list[str]:
    if prefix.startswith("/") or ".." in prefix.split("/"):
        raise ValueError("object key is not allowed")
    if store_mode() == "s3":
        keys: list[str] = []
        token = None
        while True:
            args = {"Bucket": _bucket(), "Prefix": prefix}
            if token:
                args["ContinuationToken"] = token
            page = _client().list_objects_v2(**args)
            keys.extend(item["Key"] for item in page.get("Contents", []))
            if not page.get("IsTruncated"):
                return keys
            token = page.get("NextContinuationToken")
    root = object_root()
    folder = _local_path(prefix)
    if not folder.exists():
        return []
    return [path.relative_to(root).as_posix() for path in folder.rglob("*") if path.is_file()]


def presign_get(key: str, seconds: int = 300) -> str | None:
    _require_key(key)
    if store_mode() != "s3":
        return None
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": _bucket(), "Key": key},
        ExpiresIn=seconds,
    )


def ensure_bucket() -> None:
    if store_mode() != "s3":
        return
    from botocore.exceptions import ClientError

    client = _client()
    bucket = _bucket()
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def _require_key(key: str) -> None:
    parts = key.split("/")
    if len(parts) != 4 or parts[0] != "org" or parts[2] not in NAMESPACES or ".." in parts:
        raise ValueError("object key is not allowed")


def _local_path(key: str) -> Path:
    if key.startswith("/") or ".." in key.split("/"):
        raise ValueError("object key is not allowed")
    return object_root() / key


def _client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=os.environ["PHASE5_S3_ENDPOINT"],
        aws_access_key_id=os.environ.get("PHASE5_S3_ACCESS_KEY", ""),
        aws_secret_access_key=os.environ.get("PHASE5_S3_SECRET_KEY", ""),
        region_name=os.environ.get("PHASE5_S3_REGION", "us-east-1"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def _bucket() -> str:
    return os.environ.get("PHASE5_S3_BUCKET", "perchpoint-documents")


def _write_s3(key: str, data: bytes) -> None:
    _client().put_object(Bucket=_bucket(), Key=key, Body=data)


def _read_s3(key: str) -> bytes:
    response = _client().get_object(Bucket=_bucket(), Key=key)
    return response["Body"].read()
