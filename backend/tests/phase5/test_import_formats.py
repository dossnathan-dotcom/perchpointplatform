"""Synthetic CSV, JSON, XLSX, and archive imports."""
from __future__ import annotations

import base64
import io
import zipfile
from uuid import uuid4

from fastapi.testclient import TestClient

from perchpoint.routes import create_app
from tests.phase5.test_canonical import _auth, _login


def _xlsx(name: str) -> str:
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


def _archive(name: str, member: str = "rows.csv") -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member, f"name\n{name}\n")
    return base64.b64encode(buffer.getvalue()).decode()


def _stage(client, token, content, source_format):
    return client.post(
        "/api/v2/imports",
        headers=_auth(token),
        json={"content": content, "source_format": source_format, "idempotency_key": "fmt-" + uuid4().hex},
    )


def test_json_xlsx_and_archive_imports_stage_without_innago():
    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    json_name = "Json " + uuid4().hex[:8]
    staged = _stage(client, token, '[{"display_name": "%s"}]' % json_name, "json")
    assert staged.status_code == 201, staged.text
    assert staged.json()["blockers"] == 0
    report = client.get(f"/api/v2/imports/{staged.json()['id']}", headers=_auth(token))
    assert report.status_code == 200
    assert report.json()["checksum"]
    assert report.json()["mapping_version"] == 1
    workbook = _stage(client, token, _xlsx("Sheet " + uuid4().hex[:8]), "xlsx")
    assert workbook.status_code == 201, workbook.text
    assert workbook.json()["blockers"] == 0
    packaged = _stage(client, token, _archive("Archive " + uuid4().hex[:8]), "archive")
    assert packaged.status_code == 201, packaged.text
    assert packaged.json()["blockers"] == 0


def test_archive_traversal_is_rejected():
    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    response = _stage(client, token, _archive("hidden", "../rows.csv"), "archive")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "archive_traversal"
