"""Local demonstration catalog and feature inventory.

The catalog is a fixed synthetic presentation. It does not replace acceptance-scale
factories and it is not a live listing feed.
"""
from __future__ import annotations

import math

PAGE_SIZE = 10
MARKER = "SAMPLE — SYNTHETIC DEMONSTRATION — NOT FOR EXECUTION"

# Twenty synthetic homes. Resident names stay off the public catalog.
# Rents are fixture inputs in USD minor units. Homes 13–20 stay leased and
# show a future availability date; they are not vacant today.
_ROSTER = (
    ("Maple Court 101", "apartment", 1, 680, 97500, "Avery Morgan", "current"),
    ("Maple Court 102", "apartment", 2, 910, 122500, "Jordan Ellis", "current"),
    ("Maple Court 103", "apartment", 0, 510, 82500, "Riley Bennett", "current"),
    ("Maple Court 104", "apartment", 2, 960, 127500, "Cameron Reed", "current"),
    ("Cedar Lofts 201", "apartment", 1, 735, 105000, "Taylor Brooks", "current"),
    ("Cedar Lofts 202", "apartment", 3, 1260, 155000, "Casey Jordan", "current"),
    ("Cedar Lofts 203", "apartment", 2, 1020, 130000, "Quinn Parker", "current"),
    ("Willow Place 301", "apartment", 1, 790, 110000, "Morgan Hayes", "current"),
    ("Willow Place 302", "apartment", 2, 1080, 137500, "Jamie Sullivan", "current"),
    ("Willow Place 303", "apartment", 3, 1310, 160000, "Devon Carter", "current"),
    ("Birch House", "house", 2, 1120, 145000, "Alex Monroe", "current"),
    ("Linden House", "house", 3, 1480, 180000, "Rowan Spencer", "current"),
    ("Orchard House", "house", 3, 1620, 195000, "Emery Lane", "partial"),
    ("Meadow House", "house", 4, 1940, 235000, "Sage Collins", "partial"),
    ("Juniper House", "house", 2, 1190, 150000, "Robin Foster", "partial"),
    ("Hawthorn House", "house", 3, 1540, 185000, "Drew Wallace", "partial"),
    ("Sycamore House", "house", 4, 2080, 250000, "Reese Harper", "past_due"),
    ("Brookside House", "house", 3, 1430, 177500, "Finley Blake", "past_due"),
    ("Aspen House", "house", 2, 1250, 157500, "Skyler Quinn", "credit"),
    ("Oakridge House", "house", 4, 2220, 265000, "Kendall Avery", "dispute"),
)
FUTURE_AVAILABLE_ON = "2027-06-01"


def _balance(rent: int, scenario: str) -> dict:
    if scenario == "current":
        return {"due_minor": 0, "past_due_minor": 0, "credit_minor": 0, "disputed_minor": 0, "status": "Current"}
    if scenario == "partial":
        half = rent // 2
        return {"due_minor": half, "past_due_minor": 0, "credit_minor": 0, "disputed_minor": 0, "status": "Partial settlement"}
    if scenario == "past_due":
        return {"due_minor": rent, "past_due_minor": rent, "credit_minor": 0, "disputed_minor": 0, "status": "Past due"}
    if scenario == "credit":
        return {"due_minor": -rent, "past_due_minor": 0, "credit_minor": rent, "disputed_minor": 0, "status": "Unapplied credit"}
    return {"due_minor": rent, "past_due_minor": 0, "credit_minor": 0, "disputed_minor": rent, "status": "Open dispute"}


def _record(index: int, row: tuple) -> dict:
    label, home_type, bedrooms, sqft, rent, _resident, scenario = row
    slug = f"demo-{index + 1:02d}"
    leased_with_future_date = index >= 12
    baths = 1 if bedrooms <= 1 else 2
    building = label.rsplit(" ", 1)[0] if home_type == "apartment" else label
    return {
        "slug": slug,
        "property_name": building,
        "label": label,
        "city": "Cincinnati",
        "state": "OH",
        "home_type": home_type,
        "use": home_type,
        "bedrooms": bedrooms,
        "bathrooms": baths,
        "sqft": sqft,
        "amount_minor": rent,
        "currency": "USD",
        "occupancy": "leased",
        "availability": "upcoming" if leased_with_future_date else "leased",
        "available_on": FUTURE_AVAILABLE_ON if leased_with_future_date else None,
        "amenity": "In-unit laundry" if home_type == "apartment" else "Private yard",
        "entry_fact": "Step-free building entry" if index % 3 == 0 else "Upper-floor walk-up" if home_type == "apartment" else "Ground-floor entry",
        "hero": f"/demo-photos/gallery/{'apartment' if home_type == 'apartment' else 'house'}-exterior.jpg",
        "gallery": [
            {"src": f"/demo-photos/gallery/{'apartment' if home_type == 'apartment' else 'house'}-exterior.jpg", "alt": f"{'Apartment' if home_type == 'apartment' else 'House'} exterior used to illustrate {label}"},
            {"src": "/demo-photos/gallery/living-room.jpg", "alt": f"Living area used to illustrate {label}"},
            {"src": "/demo-photos/gallery/kitchen.jpg", "alt": f"Kitchen used to illustrate {label}"},
            {"src": "/demo-photos/gallery/bedroom.jpg", "alt": f"Bedroom used to illustrate {label}"},
        ],
        "disclosure": "Illustrative local demonstration. This home is leased and is not a real vacant listing.",
        "synthetic": True,
    }


def _household(index: int, row: tuple) -> dict:
    label, home_type, bedrooms, sqft, rent, resident, scenario = row
    email = "dossnathan2@gmail.com" if index == 0 else f"resident{index + 1:02d}@demo.perchpoint.invalid"
    balance = _balance(rent, scenario)
    return {
        "number": index + 1,
        "email": email,
        "person_label": resident,
        "home_label": label,
        "home_type": home_type,
        "bedrooms": bedrooms,
        "sqft": sqft,
        "rent_minor": rent,
        "slug": f"demo-{index + 1:02d}",
        "scenario": scenario,
        "sample_marker": "SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION",
        **balance,
    }


LISTINGS = tuple(_record(index, row) for index, row in enumerate(_ROSTER))
HOUSEHOLDS = tuple(_household(index, row) for index, row in enumerate(_ROSTER))


def _bedrooms_match(value: str, bedrooms: int) -> bool:
    if value in {"", "all"}:
        return True
    if value == "studio":
        return bedrooms == 0
    if value == "4":
        return bedrooms >= 4
    if value in {"1", "2", "3"}:
        return bedrooms == int(value)
    raise ValueError("bedrooms")


def search_demo(criteria: dict) -> dict:
    home_type = str(criteria.get("home_type") or "all").lower()
    bedrooms = str(criteria.get("bedrooms") or "all").lower()
    city = str(criteria.get("city") or "").strip()
    if home_type not in {"all", "house", "apartment"}:
        raise ValueError("home_type")
    try:
        min_sqft = int(criteria["min_sqft"]) if criteria.get("min_sqft") not in (None, "") else None
        max_sqft = int(criteria["max_sqft"]) if criteria.get("max_sqft") not in (None, "") else None
        page = int(criteria.get("page") or 1)
    except (TypeError, ValueError) as exc:
        raise ValueError("number") from exc
    if page < 1 or (min_sqft is not None and min_sqft < 0) or (max_sqft is not None and max_sqft < 0):
        raise ValueError("range")
    if min_sqft is not None and max_sqft is not None and min_sqft > max_sqft:
        raise ValueError("range")
    rows = []
    for row in LISTINGS:
        if home_type != "all" and row["home_type"] != home_type:
            continue
        if not _bedrooms_match(bedrooms, row["bedrooms"]):
            continue
        if city and row["city"].lower() != city.lower():
            continue
        if min_sqft is not None and row["sqft"] < min_sqft:
            continue
        if max_sqft is not None and row["sqft"] > max_sqft:
            continue
        rows.append(row)
    rows.sort(key=lambda row: row["slug"])
    start = (page - 1) * PAGE_SIZE
    page_rows = rows[start : start + PAGE_SIZE]
    return {
        "total": len(rows),
        "page": page,
        "page_size": PAGE_SIZE,
        "pages": max(1, math.ceil(len(rows) / PAGE_SIZE)) if rows else 0,
        "records": page_rows,
        "synthetic": True,
        "disclosure": "Demo portfolio — all 20 homes. Every home is currently leased. Eight have a future availability date and are not vacant today.",
    }


def household_for_email(email: str) -> dict | None:
    normalized = email.strip().lower()
    for row in HOUSEHOLDS:
        if row["email"].lower() == normalized:
            return row
    return None


def account_statement(row: dict) -> dict:
    """Explain one household balance with explicit synthetic lines.

    The due amount is the cohort balance. Lines show the charge and any
    synthetic settlement that produces it. No money has moved.
    """
    rent = row["rent_minor"]
    lines = [{
        "posted_on": "2026-10-01",
        "kind": "charge",
        "description": "October 2026 rent",
        "amount_minor": rent,
        "money_moved": False,
    }]
    if row["scenario"] == "current":
        lines.append({
            "posted_on": "2026-10-03",
            "kind": "synthetic_settlement",
            "description": "Synthetic settlement of October rent",
            "amount_minor": -rent,
            "money_moved": False,
        })
    elif row["scenario"] == "partial":
        lines.append({
            "posted_on": "2026-10-04",
            "kind": "synthetic_settlement",
            "description": "Partial synthetic settlement of October rent",
            "amount_minor": -(rent - row["due_minor"]),
            "money_moved": False,
        })
    elif row["scenario"] == "credit":
        lines.append({
            "posted_on": "2026-10-02",
            "kind": "synthetic_settlement",
            "description": "Synthetic settlement larger than October rent",
            "amount_minor": -(rent + row["credit_minor"]),
            "money_moved": False,
        })
    elif row["scenario"] == "dispute":
        lines.append({
            "posted_on": "2026-10-06",
            "kind": "dispute",
            "description": "Open dispute on the October rent charge",
            "amount_minor": rent,
            "money_moved": False,
        })
    future = row["slug"] >= "demo-13"
    return {
        "slug": row["slug"],
        "person_label": row["person_label"],
        "home_label": row["home_label"],
        "home_type": row["home_type"],
        "status": row["status"],
        "scenario": row["scenario"],
        "as_of": "2026-10-10",
        "period": "2026-10",
        "currency": "USD",
        "rent_minor": rent,
        "due_minor": row["due_minor"],
        "past_due_minor": row["past_due_minor"],
        "credit_minor": row["credit_minor"],
        "disputed_minor": row["disputed_minor"],
        "lease_start": "2026-06-01" if future else "2026-07-01",
        "lease_end": "2027-05-31" if future else "2027-06-30",
        "due_on": "2026-10-01",
        "sample_marker": row["sample_marker"],
        "statement_marker": "SYNTHETIC OPERATIONAL STATEMENT — NOT A TAX RETURN — NOT A FORMAL GENERAL LEDGER",
        "money_moved": False,
        "lines": lines,
        "hero": f"/demo-photos/gallery/{'apartment' if row['home_type'] == 'apartment' else 'house'}-exterior.jpg",
    }


def document_html(account: dict, kind: str) -> str:
    import html

    if kind not in {"lease", "statement"}:
        raise ValueError("kind")
    person = html.escape(account["person_label"])
    home = html.escape(account["home_label"])
    rent = f"${account['rent_minor'] / 100:,.2f}"
    due = f"${account['due_minor'] / 100:,.2f}"
    if kind == "lease":
        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Sample lease — {home}</title></head>
<body>
<p>SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION</p>
<h1>Sample lease</h1>
<p>Parties: HawkVision Homes — synthetic organization and {person}.</p>
<p>Premises: {home}, Cincinnati, OH. Illustrative demonstration premises, not a real street address.</p>
<p>Term: {account['lease_start']} through {account['lease_end']}.</p>
<p>Rent: {rent} per month, due on the first day of the month.</p>
<p>Deposit: one month of rent, held separately from the monthly rent balance.</p>
<p>Utilities: the resident pays electric service. The owner pays water and trash in this sample.</p>
<p>Property section: {html.escape(account['home_type'])} home. This sample does not change an issued package.</p>
<p>Attachments: property information sheet and move-in checklist, both synthetic.</p>
<p>Sample signature: {person}, resident. Sample signature: owner representative. Not for execution.</p>
<p>SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION</p>
</body></html>"""
    rows = "".join(
        f"<tr><td>{html.escape(line['posted_on'])}</td><td>{html.escape(line['description'])}</td><td>${line['amount_minor'] / 100:,.2f}</td></tr>"
        for line in account["lines"]
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>October 2026 statement — {home}</title></head>
<body>
<p>{html.escape(account['statement_marker'])}</p>
<h1>October 2026 statement</h1>
<p>{person} at {home}. Period {account['period']}. As of {account['as_of']}.</p>
<p>Amount due {due}. Past due ${account['past_due_minor'] / 100:,.2f}. Unapplied credit ${account['credit_minor'] / 100:,.2f}. Disputed ${account['disputed_minor'] / 100:,.2f}.</p>
<p>The deposit is held separately and is not included in the amount due. No money has moved.</p>
<table><caption>Posted lines</caption><thead><tr><th>Date</th><th>Description</th><th>Amount</th></tr></thead><tbody>{rows}</tbody></table>
<p>{html.escape(account['statement_marker'])}</p>
</body></html>"""


def staff_accounts() -> list[dict]:
    return [account_statement(row) for row in HOUSEHOLDS]


def account_for_slug(slug: str) -> dict | None:
    for row in HOUSEHOLDS:
        if row["slug"] == slug:
            return account_statement(row)
    return None


def work_items() -> list[dict]:
    """Open examples on homes that already have a future availability date.

    These prospects are not a second household for that home.
    """
    return [
        {"id": "inquiry-orchard", "workflow": "Inquiry", "subject": "Prospect interested in Orchard House", "home_label": "Orchard House", "status": "Unassigned", "assignee": "Unassigned", "age_days": 2, "next_action": "Assign a leasing owner", "amount_minor": None},
        {"id": "showing-meadow", "workflow": "Showing", "subject": "Showing at Meadow House", "home_label": "Meadow House", "status": "Scheduled", "assignee": "Leasing staff", "age_days": 1, "next_action": "Record the showing outcome after 2026-10-14", "amount_minor": None},
        {"id": "application-juniper", "workflow": "Application", "subject": "Application for Juniper House", "home_label": "Juniper House", "status": "Missing document", "assignee": "Leasing staff", "age_days": 4, "next_action": "Request the missing income document", "amount_minor": None},
        {"id": "screening-hawthorn", "workflow": "Screening", "subject": "Screening case for Hawthorn House", "home_label": "Hawthorn House", "status": "Awaiting decision", "assignee": "Operations manager", "age_days": 3, "next_action": "Record the human screening decision", "amount_minor": None},
        {"id": "lease-sycamore", "workflow": "Lease", "subject": "Future package for Sycamore House", "home_label": "Sycamore House", "status": "Ready for review", "assignee": "Operations manager", "age_days": 6, "next_action": "Review the sample package. It does not replace the current lease.", "amount_minor": None},
        {"id": "dispute-oakridge", "workflow": "Dispute", "subject": "Kendall Avery at Oakridge House", "home_label": "Oakridge House", "status": "Open dispute", "assignee": "Owner", "age_days": 5, "next_action": "Review the disputed October rent", "amount_minor": 265000},
    ]


def cohort_summary() -> dict:
    past_due = [row for row in HOUSEHOLDS if row["past_due_minor"] > 0]
    partial = [row for row in HOUSEHOLDS if row["scenario"] == "partial"]
    disputes = [row for row in HOUSEHOLDS if row["disputed_minor"] > 0]
    return {
        "homes": len(LISTINGS),
        "households": len(HOUSEHOLDS),
        "occupied": sum(1 for row in LISTINGS if row["occupancy"] == "leased"),
        "future_availability": sum(1 for row in LISTINGS if row["available_on"]),
        "past_due_accounts": len(past_due),
        "past_due_minor": sum(row["past_due_minor"] for row in past_due),
        "partial_accounts": len(partial),
        "partial_due_minor": sum(row["due_minor"] for row in partial),
        "open_disputes": len(disputes),
        "currency": "USD",
        "as_of": "2026-10-10",
    }


def demo_listing(slug: str) -> dict | None:
    for row in LISTINGS:
        if row["slug"] == slug:
            return row
    return None


FEATURES = (
    {"name": "Public home", "phase": 0, "persona": None, "route": "/", "scenario": "Public marketing home", "state": "implemented", "boundary": "No account is required.", "executable": True},
    {"name": "Public listings", "phase": 9, "persona": None, "route": "/rentals", "scenario": "20 leased demo homes, 10 per page", "state": "implemented", "boundary": "Local catalog only while demo mode is on. Resident names are not public.", "executable": True},
    {"name": "Renter resources", "phase": 0, "persona": None, "route": "/resources", "scenario": "Published renter guidance", "state": "implemented", "boundary": "Content is public and synthetic.", "executable": True},
    {"name": "Rental inquiry", "phase": 8, "persona": None, "route": "/rentals", "scenario": "Inquiry form on the rentals page", "state": "implemented", "boundary": "Records interest only. It does not schedule a showing.", "executable": True},
    {"name": "Application guide", "phase": 8, "persona": None, "route": "/apply", "scenario": "Published application guidance", "state": "implemented", "boundary": "Does not submit a live application by itself.", "executable": True},
    {"name": "Technical operator", "phase": 6, "persona": "platform_admin", "route": "/access/onboarding", "scenario": "dossnathan1@gmail.com", "state": "implemented", "boundary": "Technical authority is not business approval.", "executable": True},
    {"name": "Owner workspace", "phase": 6, "persona": "owner", "route": "/owner", "scenario": "dossnathan@gmail.com", "state": "implemented", "boundary": "Owner approval stays server-authorized.", "executable": True},
    {"name": "Operations workspace", "phase": 6, "persona": "operations", "route": "/leasing-desk", "scenario": "operations@demo.perchpoint.invalid", "state": "implemented", "boundary": "Operations cannot read another organization.", "executable": True},
    {"name": "Leasing desk", "phase": 8, "persona": "leasing", "route": "/applications", "scenario": "leasing@demo.perchpoint.invalid", "state": "implemented", "boundary": "Staff session is separate from the owner session.", "executable": True},
    {"name": "Showings", "phase": 10, "persona": "operations", "route": "/showings", "scenario": "Showing desk", "state": "implemented", "boundary": "Synthetic scheduling only.", "executable": True},
    {"name": "Screening", "phase": 12, "persona": "operations", "route": "/screening", "scenario": "Synthetic screening desk", "state": "implemented_synthetic_provider", "boundary": "Criminal screening products stay disabled. No live consumer-report pull.", "executable": True},
    {"name": "Lease packages", "phase": 14, "persona": "operations", "route": "/leases", "scenario": "Synthetic lease desk", "state": "implemented_synthetic_provider", "boundary": MARKER, "executable": True},
    {"name": "Resident portal", "phase": 15, "persona": "resident", "route": "/portal", "scenario": "dossnathan2@gmail.com", "state": "implemented", "boundary": "Household scope only. Synthetic payments are a separate route.", "executable": True},
    {"name": "Resident account", "phase": 16, "persona": "operations", "route": "/ledger", "scenario": "Synthetic operational journal", "state": "implemented_synthetic_provider", "boundary": "money_moved remains false. Not a formal general ledger.", "executable": True},
    {"name": "Access administration", "phase": 6, "persona": "platform_admin", "route": "/access/users-access", "scenario": "Users and access", "state": "implemented", "boundary": "Deny by default. Demo entry does not grant extra capabilities.", "executable": True},
    {"name": "Maintenance history", "phase": 6, "persona": "maintenance", "route": "/access/maintenance-history", "scenario": "maintenance@demo.perchpoint.invalid", "state": "preview", "boundary": "Existing access history only. A production work-order workflow is not open.", "executable": True},
    {"name": "Vendor access", "phase": 6, "persona": "technician", "route": "/access/vendor-access", "scenario": "technician@demo.perchpoint.invalid", "state": "implemented", "boundary": "Assignment fields stay inside the existing vendor relationship.", "executable": True},
    {"name": "Synthetic resident payments", "phase": 17, "persona": "resident", "route": "/payments", "scenario": "Published charge, partial payment, and autopay", "state": "implemented_synthetic_provider", "boundary": "Fake provider only. real_values_activated and money_moved stay false.", "executable": True},
    {"name": "Additional payer", "phase": 17, "persona": "additional_payer", "route": "/pay", "scenario": "One invited payer", "state": "implemented_synthetic_provider", "boundary": "One active grant. No other household records.", "executable": True},
    {"name": "Live payment processor", "phase": 17, "persona": None, "route": None, "scenario": "Not activated", "state": "intentionally_disabled", "boundary": "No live processor, no money movement, no public webhook.", "executable": False},
    {"name": "Live e-signature", "phase": 17, "persona": None, "route": None, "scenario": "Not seeded", "state": "intentionally_disabled", "boundary": "Signature artifacts stay synthetic and are not executable instruments.", "executable": False},
)
