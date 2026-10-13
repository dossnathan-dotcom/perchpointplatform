"""Phase 19 observes bank and processor rows without posting them again."""
import os
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from perchpoint.db import application_admin_connection
from perchpoint.settings import Settings
from tests.phase15.test_portal import _key, _login
from tests.phase18.test_assistance import _books, _determination


def _client():
    from perchpoint.routes import create_app

    return TestClient(create_app())


def _journals() -> int:
    with application_admin_connection(Settings.load()) as connection:
        return int(connection.execute(text("SELECT count(*) FROM journal_transactions")).scalar_one())


def _line_count(external_id: str) -> int:
    with application_admin_connection(Settings.load()) as connection:
        return int(
            connection.execute(
                text("SELECT count(*) FROM reconciliation_lines WHERE external_id = :external"),
                {"external": external_id},
            ).scalar_one()
        )


def test_preview_uses_exact_minor_units_and_writes_nothing():
    client = _client()
    headers = _login(client, "ann.synthetic@example.com")
    before = _journals()
    preview = client.post(
        "/api/v2/payments/reconciliation/preview",
        headers=headers,
        json={
            "lines": [
                {"external_id": "c1", "kind": "processor_charge", "amount_minor": "1000.00", "status": "posted"},
                {"external_id": "c2", "kind": "processor_charge", "amount_minor": 60000, "status": "posted"},
                {"external_id": "f1", "kind": "processor_fee", "amount_minor": 3000, "status": "posted"},
                {"external_id": "f2", "kind": "processor_fee", "amount_minor": 1800, "status": "posted"},
                {"external_id": "r1", "kind": "processor_refund", "amount_minor": 20000, "status": "posted"},
                {"external_id": "b1", "kind": "bank_deposit", "amount_minor": 135000, "status": "posted"},
            ]
        },
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["processor_net_minor"] == 135200
    assert body["bank_minor"] == 135000
    assert body["residual_minor"] == 200
    assert body["posted"] is False
    assert _journals() == before
    rejected = client.post(
        "/api/v2/payments/reconciliation/preview",
        headers=headers,
        json={"lines": [{"external_id": "x", "kind": "processor_charge", "amount_minor": "10.001", "status": "posted"}]},
    )
    assert rejected.status_code == 400
    converted = client.post(
        "/api/v2/payments/reconciliation/preview",
        headers=headers,
        json={"lines": [{"external_id": "x", "kind": "bank_deposit", "amount_minor": 100, "status": "posted", "currency_code": "EUR"}]},
    )
    assert converted.status_code == 400


def test_import_keeps_the_two_dollar_residual_and_does_not_post_a_journal():
    client = _client()
    headers = _login(client, "ann.synthetic@example.com")
    before = _journals()
    stamp = uuid4().hex[:8]
    payload = {
        "source_reference": f"processor-{stamp}",
        "source_kind": "processor",
        "lines": [
            {"external_id": f"c1-{stamp}", "kind": "processor_charge", "amount_minor": 100000, "status": "posted"},
            {"external_id": f"c2-{stamp}", "kind": "processor_charge", "amount_minor": 60000, "status": "posted"},
            {"external_id": f"f1-{stamp}", "kind": "processor_fee", "amount_minor": 3000, "status": "posted"},
            {"external_id": f"f2-{stamp}", "kind": "processor_fee", "amount_minor": 1800, "status": "posted"},
            {"external_id": f"r1-{stamp}", "kind": "processor_refund", "amount_minor": 20000, "status": "posted"},
            {"external_id": f"b1-{stamp}", "kind": "bank_deposit", "amount_minor": 135000, "status": "posted"},
            {"external_id": f"t1-{stamp}", "kind": "internal_transfer", "amount_minor": 500000, "status": "posted"},
            {"external_id": f"u1-{stamp}", "kind": "unknown", "amount_minor": 7500, "status": "pending"},
        ],
        "idempotency_key": _key("import"),
    }
    created = client.post("/api/v2/payments/reconciliation/imports", headers=headers, json=payload)
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["processor_net_minor"] == 135200
    assert body["residual_minor"] == 200
    assert body["internal_transfer_minor"] == 500000
    assert body["unidentified_minor"] == 7500
    assert body["revenue_journal_count"] == 0
    assert _journals() == before
    same = client.post("/api/v2/payments/reconciliation/imports", headers=headers, json=payload)
    assert same.status_code == 200, same.text
    assert same.json()["replayed"] is True
    conflict = client.post(
        "/api/v2/payments/reconciliation/imports",
        headers=headers,
        json={
            "source_reference": f"processor-{stamp}",
            "source_kind": "processor",
            "lines": [{"external_id": f"c1-{stamp}", "kind": "processor_charge", "amount_minor": 1, "status": "posted"}],
            "idempotency_key": _key("conflict"),
        },
    )
    assert conflict.status_code == 409


def test_a_crash_before_commit_leaves_no_line():
    client = TestClient(__import__("perchpoint.routes", fromlist=["create_app"]).create_app(), raise_server_exceptions=False)
    headers = _login(client, "ann.synthetic@example.com")
    external = f"crash-{uuid4().hex[:8]}"
    os.environ["PHASE19_FAULT"] = "before_commit"
    try:
        response = client.post(
            "/api/v2/payments/reconciliation/imports",
            headers=headers,
            json={
                "source_reference": f"bank-{external}",
                "source_kind": "bank",
                "lines": [{"external_id": external, "kind": "bank_deposit", "amount_minor": 100, "status": "posted"}],
                "idempotency_key": _key("crash"),
            },
        )
        assert response.status_code >= 500
    finally:
        os.environ.pop("PHASE19_FAULT", None)
    assert _line_count(external) == 0


def test_assistance_and_history_are_linked_without_posting_again():
    client = _client()
    headers = _login(client, "ann.synthetic@example.com")
    account = _books(client, headers)
    tenancy, _body = _determination(client, headers, account, resident=40000, agency=110000)
    batch = client.post(
        "/api/v2/payments/assistance/batches",
        headers=headers,
        json={
            "external_id": f"advice-{uuid4().hex[:8]}",
            "gross_minor": 110000,
            "recoupment_minor": 0,
            "net_minor": 110000,
            "rows": [{"tenancy_code": tenancy, "service_period": "2026-11", "gross_minor": 110000}],
            "idempotency_key": _key("advice"),
        },
    )
    assert batch.status_code == 200, batch.text
    historical = client.post(
        "/api/v2/payments/assistance/receipts",
        headers=headers,
        json={
            "source": "historical_import",
            "external_id": f"old-{uuid4().hex[:8]}",
            "method": "check",
            "amount_minor": 197500,
            "idempotency_key": _key("historical"),
        },
    )
    assert historical.status_code == 200, historical.text
    before = _journals()
    linked = client.post(
        "/api/v2/payments/reconciliation/imports",
        headers=headers,
        json={
            "source_reference": f"bank-{uuid4().hex[:8]}",
            "source_kind": "bank",
            "lines": [
                {
                    "external_id": f"assist-{uuid4().hex[:8]}",
                    "kind": "assistance_evidence",
                    "amount_minor": 110000,
                    "status": "posted",
                    "link_reference": batch.json()["reference"],
                },
                {
                    "external_id": f"hist-{uuid4().hex[:8]}",
                    "kind": "historical_observation",
                    "amount_minor": 197500,
                    "status": "posted",
                    "link_reference": historical.json()["reference"],
                },
            ],
            "idempotency_key": _key("link"),
        },
    )
    assert linked.status_code == 200, linked.text
    assert _journals() == before
    with application_admin_connection(Settings.load()) as connection:
        state = connection.execute(
            text("SELECT state FROM remittance_batches WHERE public_reference = :reference"),
            {"reference": batch.json()["reference"]},
        ).scalar_one()
        receipt = connection.execute(
            text("SELECT application_state FROM digital_receipts WHERE public_reference = :reference"),
            {"reference": historical.json()["reference"]},
        ).scalar_one()
    assert state != "applied"
    assert receipt in {"staged", "excluded"}
    view = client.get("/api/v2/payments/assistance/household", headers=headers, params={"tenancy_code": tenancy}).json()
    assert view["subsidy_minor"] == 0
    assert view["due_minor"] == 40000


def test_allocations_cannot_consume_a_line_twice_and_versions_conflict():
    client = _client()
    headers = _login(client, "ann.synthetic@example.com")
    stamp = uuid4().hex[:8]
    created = client.post(
        "/api/v2/payments/reconciliation/imports",
        headers=headers,
        json={
            "source_reference": f"unknown-{stamp}",
            "source_kind": "bank",
            "lines": [{"external_id": f"unknown-{stamp}", "kind": "unknown", "amount_minor": 5000, "status": "posted"}],
            "idempotency_key": _key("unknown"),
        },
    )
    assert created.status_code == 200, created.text
    line = next(item for item in created.json()["lines"] if item["kind"] == "unknown")
    first = client.post(
        "/api/v2/payments/reconciliation/matches",
        headers=headers,
        json={"line_reference": line["reference"], "target_reference": "hold-a", "amount_minor": 5000, "idempotency_key": _key("match-a")},
    )
    assert first.status_code == 200, first.text
    assert first.json()["remaining_minor"] == 0
    second = client.post(
        "/api/v2/payments/reconciliation/matches",
        headers=headers,
        json={"line_reference": line["reference"], "target_reference": "hold-b", "amount_minor": 1, "idempotency_key": _key("match-b")},
    )
    assert second.status_code == 409
    found = client.get("/api/v2/payments/reconciliation/queue", headers=headers, params={"q": stamp})
    assert found.status_code == 200, found.text
    assert any(item["external_id"] == f"unknown-{stamp}" for item in found.json()["items"])
    claimed = client.post(
        "/api/v2/payments/reconciliation/claims",
        headers=headers,
        json={"line_reference": line["reference"], "version": 1, "idempotency_key": _key("claim")},
    )
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["version"] == 2
    stale = client.post(
        "/api/v2/payments/reconciliation/claims",
        headers=headers,
        json={"line_reference": line["reference"], "version": 1, "idempotency_key": _key("stale")},
    )
    assert stale.status_code == 409


def test_briefing_acknowledgement_and_close_keep_one_snapshot():
    client = _client()
    ann = _login(client, "ann.synthetic@example.com")
    faruk = _login(client, "faruk.synthetic@example.com")
    stamp = uuid4().hex[:8]
    imported = client.post(
        "/api/v2/payments/reconciliation/imports",
        headers=ann,
        json={
            "source_reference": f"stale-{stamp}",
            "source_kind": "bank",
            "refresh_state": "stale",
            "lines": [
                {"external_id": f"pend-{stamp}", "kind": "bank_deposit", "amount_minor": 4000, "status": "pending"},
                {"external_id": f"out-{stamp}", "kind": "processor_refund", "amount_minor": 900, "status": "posted"},
            ],
            "idempotency_key": _key("stale"),
        },
    )
    assert imported.status_code == 200, imported.text
    briefing = client.get("/api/v2/payments/reconciliation/briefing", headers=faruk)
    assert briefing.status_code == 200, briefing.text
    body = briefing.json()
    assert body["owed_minor"] == 427500
    assert body["october"]["sycamore_minor"] == 250000
    assert body["october"]["brookside_minor"] == 177500
    assert body["october"]["maple_court_101_due_minor"] == 0
    assert body["october"]["maple_court_101_resident"] == "Avery Morgan"
    assert body["october"]["homes"] == 20 and body["october"]["households"] == 20
    assert body["processing_minor"] >= 4000
    assert body["paid_out_minor"] >= 900
    assert body["revenue_from_internal_transfer_minor"] == 0
    assert body["stale_sources"]
    assert body["refresh_failed"] is False
    acknowledged = client.post(
        "/api/v2/payments/reconciliation/acknowledgements",
        headers=faruk,
        json={"snapshot_reference": body["reference"], "idempotency_key": _key("ack")},
    )
    assert acknowledged.status_code == 200, acknowledged.text
    assert acknowledged.json()["resolved"] is False
    assert acknowledged.json()["decisions"] == body["decisions"]
    os.environ["PHASE19_FAULT"] = "refresh"
    try:
        failed = client.get("/api/v2/payments/reconciliation/briefing", headers=faruk)
    finally:
        os.environ.pop("PHASE19_FAULT", None)
    assert failed.status_code == 200, failed.text
    assert failed.json()["refresh_failed"] is True
    assert failed.json()["owed_minor"] == 427500
    assert failed.json()["reference"] == body["reference"]
    prepared = client.post(
        "/api/v2/payments/reconciliation/closes",
        headers=ann,
        json={"snapshot_reference": body["reference"], "idempotency_key": _key("prepare")},
    )
    assert prepared.status_code == 200, prepared.text
    own = client.post(
        "/api/v2/payments/reconciliation/closes/issue",
        headers=ann,
        json={"close_reference": prepared.json()["reference"], "idempotency_key": _key("own")},
    )
    assert own.status_code == 403
    issued = client.post(
        "/api/v2/payments/reconciliation/closes/issue",
        headers=faruk,
        json={"close_reference": prepared.json()["reference"], "idempotency_key": _key("issue")},
    )
    assert issued.status_code == 200, issued.text
    assert issued.json()["packet_sha"] == prepared.json()["packet_sha"]
    late = client.post(
        "/api/v2/payments/reconciliation/imports",
        headers=ann,
        json={
            "source_reference": f"late-{stamp}",
            "source_kind": "bank",
            "lines": [{"external_id": f"late-{stamp}", "kind": "unknown", "amount_minor": 50, "status": "posted"}],
            "idempotency_key": _key("late"),
        },
    )
    assert late.status_code == 200, late.text
    saved = client.get("/api/v2/payments/reconciliation/packet", headers=faruk, params={"reference": issued.json()["reference"]})
    assert saved.status_code == 200, saved.text
    assert saved.json()["packet_sha"] == issued.json()["packet_sha"]
    assert saved.json()["packet"]["owed_minor"] == 427500
