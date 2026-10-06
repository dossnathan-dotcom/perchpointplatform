"""Phase 4 closeout completeness. Answers are checked against code, not Markdown status."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Phase 4 baseline. Commercial moved to the footer, which phase4-engines still
# requires as a visible link. About HawkVision remains the homepage section.
PHASE4_SURFACES = {
    "frontend/src/components/Navbar.jsx": ["Rentals", "Contact", "Apply", "Resident Login", "Staff Login"],
    "frontend/src/components/Footer.jsx": ["Commercial"],
    "frontend/src/components/AboutHawkVision.jsx": ["About HawkVision"],
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

# Additive Phase 7 public navigation. These do not replace the baseline above.
PHASE7_SURFACES = {
    "frontend/src/components/Navbar.jsx": ["Home", "Resources", "Maintenance", "About"],
}


def required_destinations(*groups: dict[str, list[str]]) -> dict[str, list[str]]:
    required: dict[str, list[str]] = {}
    for group in groups:
        for relative, labels in group.items():
            current = required.setdefault(relative, [])
            for label in labels:
                if label not in current:
                    current.append(label)
    return required


def label_present(text: str, label: str) -> bool:
    return f"'{label}'" in text or f'"{label}"' in text or f">{label}<" in text


def destination_gaps(root: Path, inventory: dict[str, list[str]]) -> list[str]:
    missing = []
    for relative, labels in inventory.items():
        path = root / relative
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for label in labels:
            if not label_present(text, label):
                missing.append(f"{relative} missing {label}")
    return missing

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
    inventory = required_destinations(PHASE4_SURFACES, PHASE7_SURFACES)
    missing = destination_gaps(ROOT, inventory)
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
    destinations = sum(len(labels) for labels in inventory.values())
    print(f"phase4 completeness passed: {destinations} destinations, {len(COMPONENTS)} components")


if __name__ == "__main__":
    main()
