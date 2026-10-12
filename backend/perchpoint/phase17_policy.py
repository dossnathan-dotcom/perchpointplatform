"""Refund allowance mathematics. Amounts are USD minor units. The clock is supplied by the server."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

UNRESOLVED = frozenset({"reserved", "dispatched", "pending", "unknown"})
CONSUMING = UNRESOLVED | {"succeeded"}
RELEASED = frozenset({"draft", "rejected", "canceled", "failed"})
ROLLING_DAYS = 31


def month_bounds(moment: datetime, zone_name: str) -> tuple[datetime, datetime]:
    zone = ZoneInfo(zone_name)
    local = moment.astimezone(zone)
    start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def rent_ceiling(snapshot_minor: int, current_minor: int) -> int:
    if snapshot_minor < 1 or current_minor < 1:
        return 0
    return min(snapshot_minor, current_minor)


def _counts(entry: dict, in_window: bool) -> bool:
    state = entry["state"]
    if state in RELEASED:
        return False
    if state in UNRESOLVED:
        return True
    if state == "succeeded":
        return in_window
    return False


def exposure(entries: list[dict], moment: datetime, zone_name: str) -> dict:
    calendar_start, calendar_end = month_bounds(moment, zone_name)
    rolling_start = moment - timedelta(days=ROLLING_DAYS)
    calendar_minor = 0
    rolling_minor = 0
    for entry in entries:
        authorized_at = entry["authorized_at"]
        if authorized_at.tzinfo is None:
            raise ValueError("refund timestamps must be timezone-aware")
        amount = int(entry["amount_minor"])
        if amount < 0:
            raise ValueError("refund exposure cannot be negative")
        in_calendar = calendar_start <= authorized_at.astimezone(calendar_start.tzinfo) < calendar_end
        in_rolling = rolling_start < authorized_at <= moment
        if _counts(entry, in_calendar):
            calendar_minor += amount
        if _counts(entry, in_rolling):
            rolling_minor += amount
    return {
        "calendar_minor": calendar_minor,
        "rolling_minor": rolling_minor,
        "calendar_start": calendar_start.isoformat(),
        "calendar_end": calendar_end.isoformat(),
        "rolling_start": rolling_start.isoformat(),
        "rolling_days": ROLLING_DAYS,
    }


def ordinary_max(ceiling_minor: int, calendar_exposure: int, rolling_exposure: int, source_remaining: int) -> int:
    if min(ceiling_minor, source_remaining) < 0:
        return 0
    return max(0, min(
        ceiling_minor,
        max(0, ceiling_minor - calendar_exposure),
        max(0, ceiling_minor - rolling_exposure),
        source_remaining,
    ))


def allowance(
    *,
    snapshot_minor: int,
    current_minor: int,
    entries: list[dict],
    source_remaining: int,
    moment: datetime,
    zone_name: str = "America/New_York",
) -> dict:
    ceiling = rent_ceiling(snapshot_minor, current_minor)
    totals = exposure(entries, moment, zone_name)
    maximum = ordinary_max(ceiling, totals["calendar_minor"], totals["rolling_minor"], source_remaining)
    return {
        "rent_snapshot_minor": snapshot_minor,
        "rent_current_minor": current_minor,
        "ceiling_minor": ceiling,
        "calendar_used_minor": totals["calendar_minor"],
        "calendar_remaining_minor": max(0, ceiling - totals["calendar_minor"]),
        "rolling_used_minor": totals["rolling_minor"],
        "rolling_remaining_minor": max(0, ceiling - totals["rolling_minor"]),
        "rolling_days": ROLLING_DAYS,
        "source_remaining_minor": source_remaining,
        "ordinary_max_minor": maximum,
        "basis_missing": ceiling < 1,
        "zone": zone_name,
        "calendar_start": totals["calendar_start"],
        "rolling_start": totals["rolling_start"],
        "money_moved": False,
    }
