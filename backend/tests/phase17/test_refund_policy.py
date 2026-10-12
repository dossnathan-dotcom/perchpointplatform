"""Phase 17 refund allowance. These cases do not move money and do not call Stripe."""
from datetime import datetime, timezone

from perchpoint.phase17_policy import allowance

ZONE = "America/New_York"
NOW = datetime(2026, 4, 2, 16, 0, tzinfo=timezone.utc)


def _entry(amount, state, when):
    return {"amount_minor": amount, "state": state, "authorized_at": when}


def test_pending_and_succeeded_leave_room_for_250_but_not_250_01():
    entries = [
        _entry(40000, "succeeded", NOW),
        _entry(35000, "pending", NOW),
    ]
    decision = allowance(snapshot_minor=100000, current_minor=100000, entries=entries, source_remaining=100000, moment=NOW, zone_name=ZONE)
    assert decision["ordinary_max_minor"] == 25000
    assert 25000 <= decision["ordinary_max_minor"]
    assert 25001 > decision["ordinary_max_minor"]


def test_consumed_cap_blocks_another_staff_request():
    decision = allowance(
        snapshot_minor=100000,
        current_minor=100000,
        entries=[_entry(100000, "succeeded", NOW)],
        source_remaining=100000,
        moment=NOW,
        zone_name=ZONE,
    )
    assert decision["ordinary_max_minor"] == 0


def test_rolling_window_blocks_a_new_month_full_allowance():
    march = datetime(2026, 3, 31, 15, 0, tzinfo=timezone.utc)
    decision = allowance(
        snapshot_minor=100000,
        current_minor=100000,
        entries=[_entry(70000, "succeeded", march)],
        source_remaining=100000,
        moment=NOW,
        zone_name=ZONE,
    )
    assert decision["calendar_used_minor"] == 0
    assert decision["rolling_used_minor"] == 70000
    assert decision["ordinary_max_minor"] == 30000
    assert 40000 > decision["ordinary_max_minor"]


def test_unresolved_exposure_survives_the_month_boundary():
    old = datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc)
    decision = allowance(
        snapshot_minor=100000,
        current_minor=100000,
        entries=[_entry(60000, "reserved", old)],
        source_remaining=100000,
        moment=NOW,
        zone_name=ZONE,
    )
    assert decision["calendar_used_minor"] == 60000
    assert decision["rolling_used_minor"] == 60000
    assert decision["ordinary_max_minor"] == 40000


def test_midmonth_rent_increase_does_not_replenish_the_snapshot():
    decision = allowance(
        snapshot_minor=100000,
        current_minor=150000,
        entries=[_entry(100000, "succeeded", NOW)],
        source_remaining=100000,
        moment=NOW,
        zone_name=ZONE,
    )
    assert decision["ceiling_minor"] == 100000
    assert decision["ordinary_max_minor"] == 0


def test_missing_rent_basis_has_no_delegated_allowance():
    decision = allowance(snapshot_minor=0, current_minor=0, entries=[], source_remaining=50000, moment=NOW, zone_name=ZONE)
    assert decision["basis_missing"] is True
    assert decision["ordinary_max_minor"] == 0


def test_released_failure_does_not_consume_allowance():
    decision = allowance(
        snapshot_minor=100000,
        current_minor=100000,
        entries=[_entry(80000, "failed", NOW)],
        source_remaining=100000,
        moment=NOW,
        zone_name=ZONE,
    )
    assert decision["ordinary_max_minor"] == 100000


def test_source_remaining_is_part_of_the_ceiling():
    decision = allowance(snapshot_minor=100000, current_minor=100000, entries=[], source_remaining=20000, moment=NOW, zone_name=ZONE)
    assert decision["ordinary_max_minor"] == 20000
