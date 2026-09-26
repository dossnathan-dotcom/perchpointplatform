"""Phase 4 closeout completeness. Answers are checked against code, not Markdown status."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NAV = {
    "frontend/src/components/Navbar.jsx": ["Rentals", "Commercial", "About HawkVision", "Contact", "Apply", "Resident Login", "Staff Login"],
    "frontend/src/data/portalData.js": [
        "Overview", "Application", "Household", "Documents", "Messages", "Appointments", "Status",
        "Home", "Payments", "Lease", "Maintenance",
        "Today", "Portfolio", "Leasing", "Applicants", "Residents", "Communications", "Finance", "Tasks", "Reports",
        "Triage", "Work Orders", "Schedule", "Properties", "Technicians", "Vendors", "Recommendations", "Parts/Purchases", "History",
        "Receivables", "Resident Ledgers", "Exceptions", "Reconciliation", "Property Performance", "Exports",
        "Assignments", "Property Access", "Estimates", "Receipts", "Compliance", "Completed Work",
        "Decisions", "Financial Position", "Projects", "Risk", "Accountability", "Trends",
        "Organizations", "Users", "Roles", "Policies", "Integrations", "Feature Flags", "Environments", "Audit", "System Health", "Configuration",
    ],
}

COMPONENTS = [
    "Button", "IconButton", "ButtonGroup", "ExternalLink", "CopyAction", "DestructiveConfirm",
    "Field", "TextInput", "TextArea", "SelectField", "CheckboxField", "RadioGroup", "SwitchField",
    "DateField", "MoneyField", "AddressField", "SearchField", "ErrorSummary", "FormSection",
    "CharacterCount", "ReadOnlyValue", "SavingIndicator", "SkipLink", "Breadcrumbs", "Tabs",
    "Pagination", "CommandPalette", "Alert", "InlineNotice", "Progress", "Spinner", "Skeleton",
    "EmptyState", "StatePanel", "Drawer", "Popover", "Menu", "Tooltip", "DecisionCard", "Metric",
    "StatusBadge", "DescriptionList", "DataTable", "Timeline", "Money", "OperationalTime", "Address",
    "Avatar", "RoleMarker", "PlaceMarker", "ChartFrame", "KeyValueComparison", "PageHeader", "Section",
    "FilterBar", "StickyActionBar", "MaintenanceRecommendation",
]


def main() -> None:
    missing = []
    for relative, labels in NAV.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for label in labels:
            if f"'{label}'" not in text and f'"{label}"' not in text and f">{label}<" not in text:
                missing.append(f"{relative} missing {label}")
    sources = "\n".join((ROOT / "frontend/src").joinpath(path).read_text(encoding="utf-8") for path in [
        "design-system/library.jsx", "design-system/components.jsx", "components/ui/dialog.jsx", "components/ui/progress.jsx",
    ])
    for name in COMPONENTS:
        if f"function {name}" not in sources and f"const {name}" not in sources:
            missing.append(f"component {name}")
    routes = (ROOT / "frontend/src/design-system/routes.js").read_text(encoding="utf-8")
    if 'capability: "presentation-only"' in routes:
        missing.append("routes still use presentation-only")
    if '"functional"' not in routes or '"synthetic"' not in routes:
        missing.append("route classes")
    policy = (ROOT / "backend/perchpoint/http_security.py").read_text(encoding="utf-8")
    if "unsafe-inline" in policy or "style-src-attr 'none'" not in policy:
        missing.append("csp")
    fonts = ROOT / "frontend/public/fonts"
    for name in ["source-sans-3-400.woff2", "source-sans-3-600.woff2", "fraunces-600.woff2", "Fraunces-OFL.txt", "SourceSans3-OFL.txt"]:
        if not (fonts / name).is_file():
            missing.append(name)
    media = list((ROOT / "frontend/public/media").glob("*.avif"))
    if len(media) < 7 or len(list((ROOT / "frontend/public/media").glob("*.webp"))) < 7:
        missing.append("optimized images")
    if missing:
        raise SystemExit("Phase 4 completeness failed:\n" + "\n".join(missing))
    print(f"phase4 completeness passed: {len(NAV['frontend/src/data/portalData.js']) + len(NAV['frontend/src/components/Navbar.jsx'])} destinations, {len(COMPONENTS)} components")


if __name__ == "__main__":
    main()
