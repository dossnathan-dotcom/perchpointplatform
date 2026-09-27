"""Live Phase 5 journey against the isolated clean-room API.

Uses the application HTTP API, which talks to PostgreSQL, MinIO, and ClamAV.
"""
from __future__ import annotations

import base64
import io
import json
import subprocess
import urllib.error
import urllib.request
import zipfile
from uuid import uuid4

import fitz

BASE = "http://127.0.0.1:8001/api/v2"
PASSWORD = "local-only-not-production-password"


def call(method: str, path: str, token: str | None = None, body=None, data: bytes | None = None, content_type: str | None = None, headers: dict | None = None):
    request_headers = {}
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    payload = data
    if body is not None:
        payload = json.dumps(body).encode()
        request_headers["Content-Type"] = "application/json"
    if content_type:
        request_headers["Content-Type"] = content_type
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(BASE + path, data=payload, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read()
            parsed = json.loads(raw) if raw and "json" in response.headers.get("Content-Type", "") else raw
            return response.status, parsed, dict(response.headers)
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw.decode(errors="replace")
        return error.code, parsed, dict(error.headers)


def login(email: str) -> str:
    status, body, _headers = call("POST", "/session", body={"email": email, "password": PASSWORD})
    if status != 200:
        raise SystemExit(f"login {email} {status} {body}")
    return body["token"]


def multipart(fields: dict, filename: str, content: bytes, media: str) -> tuple[bytes, str]:
    boundary = uuid4().hex
    chunks = []
    for key, value in fields.items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode())
    chunks.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"upload\"; filename=\"{filename}\"\r\nContent-Type: {media}\r\n\r\n".encode()
        + content
        + b"\r\n"
    )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def png() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 140), "Hawthorn boiler inspection")
    image = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
    document.close()
    return image


def xlsx(name: str) -> str:
    shared = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<si><t>name</t></si><si><t>{name}</t></si></sst>"
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row r="1"><c t="s"><v>0</v></c></row>'
        '<row r="2"><c t="s"><v>1</v></c></row></sheetData></worksheet>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", shared)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return base64.b64encode(buffer.getvalue()).decode()


def archive(name: str) -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as packaged:
        packaged.writestr("rows.csv", f"name\n{name}\n")
    return base64.b64encode(buffer.getvalue()).decode()


def main() -> None:
    evidence = {}
    ann = login("ann.synthetic@example.com")
    status, created, _headers = call(
        "POST",
        "/properties",
        ann,
        {"name": "Cleanroom Court", "property_type": "single_family", "idempotency_key": "prop-" + uuid4().hex},
    )
    evidence["property"] = {"status": status, "id": None if status != 201 else created["id"]}
    if status != 201:
        raise SystemExit(json.dumps({"property": created}))
    property_id = created["id"]
    fields = {
        "title": "Hawthorn text",
        "document_class": "internal-administration",
        "classification": "internal",
        "primary_resource_type": "property",
        "primary_resource_id": property_id,
        "idempotency_key": "doc-" + uuid4().hex,
    }
    payload, content_type = multipart(fields, "note.txt", b"Hawthorn boiler inspection note\n", "text/plain")
    status, text_upload, _headers = call("POST", "/documents", ann, data=payload, content_type=content_type)
    evidence["text_upload"] = {"status": status, "body": text_upload}
    image_fields = dict(fields)
    image_fields["title"] = "Hawthorn scan"
    image_fields["idempotency_key"] = "doc-" + uuid4().hex
    payload, content_type = multipart(image_fields, "scan.png", png(), "image/png")
    status, image_upload, _headers = call("POST", "/documents", ann, data=payload, content_type=content_type)
    evidence["image_upload"] = {"status": status, "body": image_upload}
    jobs = []
    for _ in range(4):
        job_status, job_body, _headers = call("POST", "/phase5/jobs/process", ann)
        jobs.append({"status": job_status, "body": job_body})
    evidence["jobs"] = jobs
    status, search, _headers = call("GET", "/search?q=Hawthorn", ann)
    evidence["search"] = {"status": status, "count": 0 if status != 200 else len(search.get("results", []))}
    document_id = image_upload.get("id") if isinstance(image_upload, dict) else None
    if document_id:
        status, access, _headers = call("POST", f"/documents/{document_id}/access", ann)
        evidence["access"] = {
            "status": status,
            "signed": isinstance(access, dict) and bool(access.get("presigned_url")),
            "signature_logged": False,
        }
        if status == 200 and access.get("presigned_url"):
            fetched = subprocess.run(
                [
                    "docker",
                    "exec",
                    "-e",
                    f"SIGNED_URL={access['presigned_url']}",
                    "perchpoint-phase5-closeout-api-1",
                    "python",
                    "-c",
                    "import os,urllib.request; print(urllib.request.urlopen(os.environ['SIGNED_URL']).read()[:8].hex())",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            evidence["presign_magic"] = fetched.stdout.strip() == "89504e470d0a1a0a"
            evidence["presign_error"] = fetched.stderr[-400:] if fetched.returncode else ""
            status, content, headers = call(
                "GET",
                f"/documents/{document_id}/content",
                ann,
                headers={"X-PerchPoint-Document-Token": access["token"], "Range": "bytes=0-7"},
            )
            evidence["range"] = {"status": status, "cache": headers.get("Cache-Control"), "png": content == b"\x89PNG\r\n\x1a\n"}
        status, exported, _headers = call(
            "POST",
            "/exports",
            ann,
            {"document_ids": [document_id], "idempotency_key": "export-" + uuid4().hex[:12]},
        )
        evidence["export"] = {"status": status}
        if status == 201:
            status, package, _headers = call("GET", f"/exports/{exported['id']}/content", ann)
            evidence["export_zip"] = {"status": status, "pk": isinstance(package, bytes) and package[:2] == b"PK"}
    outsider = login("isolation.synthetic@example.com")
    if document_id:
        status, hidden, _headers = call("POST", f"/documents/{document_id}/access", outsider)
        evidence["cross_org_access"] = status
        status, leaked, _headers = call("GET", "/search?q=Hawthorn", outsider)
        evidence["cross_org_search"] = {
            "status": status,
            "hits": 0
            if status != 200
            else sum(1 for item in leaked.get("results", []) if item.get("resource_id") == document_id),
        }
    csv_name = "Cleanroom " + uuid4().hex[:8]
    status, staged, _headers = call(
        "POST",
        "/imports",
        ann,
        {"content": f"display_name,party_kind\n{csv_name},person\n", "source_format": "csv", "idempotency_key": "imp-" + uuid4().hex},
    )
    evidence["csv"] = {"status": status, "id": None if status != 201 else staged["id"]}
    if status == 201:
        batch = staged["id"]
        evidence["dry_run"] = call("POST", f"/imports/{batch}/dry-run", ann)[0]
        evidence["approve"] = call("POST", f"/imports/{batch}/approve", ann, {"idempotency_key": "appr-" + uuid4().hex})[0]
        evidence["apply"] = call("POST", f"/imports/{batch}/apply", ann, {"idempotency_key": "apply-" + uuid4().hex})[0]
        evidence["report"] = call("GET", f"/imports/{batch}", ann)[0]
        evidence["rollback"] = call("POST", f"/imports/{batch}/rollback", ann, {"idempotency_key": "roll-" + uuid4().hex})[0]
    evidence["json"] = call(
        "POST",
        "/imports",
        ann,
        {"content": json.dumps([{"display_name": "Json " + uuid4().hex[:8]}]), "source_format": "json", "idempotency_key": "imp-" + uuid4().hex},
    )[0]
    evidence["xlsx"] = call(
        "POST",
        "/imports",
        ann,
        {"content": xlsx("Sheet " + uuid4().hex[:8]), "source_format": "xlsx", "idempotency_key": "imp-" + uuid4().hex},
    )[0]
    evidence["archive"] = call(
        "POST",
        "/imports",
        ann,
        {"content": archive("Archive " + uuid4().hex[:8]), "source_format": "archive", "idempotency_key": "imp-" + uuid4().hex},
    )[0]
    nathan = login("nathan.synthetic@example.com")
    evidence["replay"] = call("POST", "/replay", nathan)[1]
    evidence["diagnostics"] = call("GET", "/phase5/diagnostics", nathan)[1]
    evidence["leasing_replay"] = call("POST", "/replay", ann)[0]
    if document_id:
        listed = call("GET", "/documents", ann)[1]
        version = next(item["version"] for item in listed["documents"] if item["id"] == document_id)
        evidence["hold"] = call(
            "POST",
            f"/documents/{document_id}/hold",
            ann,
            {"reason": "synthetic hold", "idempotency_key": "hold-" + uuid4().hex},
        )[0]
        evidence["held_disposition"] = call(
            "POST",
            f"/documents/{document_id}/disposition",
            ann,
            {
                "expected_version": version + 1,
                "confirmation": "destroy",
                "confirm_again": "destroy",
                "idempotency_key": "disp-" + uuid4().hex,
            },
        )[0]
    print(json.dumps(evidence, default=str, indent=2))


if __name__ == "__main__":
    main()
