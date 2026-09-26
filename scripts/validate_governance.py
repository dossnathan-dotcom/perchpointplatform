"""Validate PerchPoint governance IDs, metadata, references, and policy invariants."""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

try:
    from scripts.verify_sources import validate_sources
except ModuleNotFoundError:  # Direct execution: python scripts/validate_governance.py
    from verify_sources import validate_sources


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs/governance/REQUIREMENTS_TRACEABILITY.md"
DECISIONS = ROOT / "docs/governance/APPROVED_DECISION_REGISTER.md"
PREFIXES = {
    "PP-PROD",
    "PP-GOV",
    "PP-AUTH",
    "PP-PROP",
    "PP-LEASE",
    "PP-FIN",
    "PP-MAINT",
    "PP-WORK",
    "PP-COMM",
    "PP-DATA",
    "PP-SEC",
    "PP-PROV",
    "PP-NFR",
    "PP-ACCEPT",
}
FIELDS = {
    "Normative statement",
    "Rationale",
    "Source",
    "Business owner",
    "Technical owner",
    "Acceptance authority",
    "Status",
    "Assumptions",
    "Dependencies",
    "Risks",
    "Verification method",
    "Related tests/evidence",
    "Affected domains",
    "Faruk must confirm later",
}
ID_RE = re.compile(r"^## (PP-[A-Z]+-\d{3})$", re.MULTILINE)
FIELD_RE = re.compile(r"^- \*\*([^*]+):\*\* (.+)$", re.MULTILINE)
PATH_RE = re.compile(
    r"(?:(?:docs|backend|frontend|contracts|scripts)/[A-Za-z0-9_./-]+\.(?:md|py|json|csv|js|ts|jsx|d\.ts))"
)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
DECISION_RE = re.compile(r"^\| (PP-DEC-\d{3}) \|(.+)\|$", re.MULTILINE)


def parse_register(text: str) -> list[tuple[str, dict[str, str]]]:
    matches = list(ID_RE.finditer(text))
    records: list[tuple[str, dict[str, str]]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        records.append((match.group(1), dict(FIELD_RE.findall(text[match.end() : end]))))
    return records


def parse_decisions(text: str) -> list[tuple[str, list[str]]]:
    records = []
    for match in DECISION_RE.finditer(text):
        cells = [cell.strip().strip("`") for cell in match.group(2).split("|")]
        records.append((match.group(1), cells))
    return records


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = validate_sources(root)
    register = root / REGISTER.relative_to(ROOT)
    if not register.exists():
        return [f"Missing requirement register: {register}"]

    records = parse_register(register.read_text(encoding="utf-8"))
    ids = [requirement_id for requirement_id, _ in records]
    duplicates = [item for item, count in Counter(ids).items() if count > 1]
    if duplicates:
        errors.append(f"Duplicate requirement IDs: {', '.join(duplicates)}")
    if len(records) != 71:
        errors.append(f"Requirement register count changed: found {len(records)}, expected 71")

    seen_prefixes: set[str] = set()
    for requirement_id, metadata in records:
        prefix = requirement_id.rsplit("-", 1)[0]
        seen_prefixes.add(prefix)
        if prefix not in PREFIXES:
            errors.append(f"{requirement_id}: unknown prefix {prefix}")
        missing = sorted(FIELDS - metadata.keys())
        if missing:
            errors.append(f"{requirement_id}: missing fields {', '.join(missing)}")
        if metadata.get("Status") not in {
            "proposed",
            "provisional",
            "accepted",
            "deferred",
            "blocked",
            "superseded",
        }:
            errors.append(f"{requirement_id}: invalid status {metadata.get('Status')!r}")
        if metadata.get("Faruk must confirm later") not in {"yes", "no"}:
            errors.append(f"{requirement_id}: Faruk confirmation must be yes/no")
        for candidate in PATH_RE.findall(metadata.get("Related tests/evidence", "")):
            if not (root / candidate).exists():
                errors.append(f"{requirement_id}: missing evidence path {candidate}")

    missing_prefixes = sorted(PREFIXES - seen_prefixes)
    if missing_prefixes:
        errors.append(f"Requirement prefixes without coverage: {', '.join(missing_prefixes)}")

    decision_file = root / DECISIONS.relative_to(ROOT)
    if not decision_file.exists():
        errors.append(f"Missing approved decision register: {decision_file}")
        decision_records = []
    else:
        decision_records = parse_decisions(decision_file.read_text(encoding="utf-8"))
    decision_ids = [decision_id for decision_id, _ in decision_records]
    duplicate_decisions = [
        item for item, count in Counter(decision_ids).items() if count > 1
    ]
    if duplicate_decisions:
        errors.append(f"Duplicate decision IDs: {', '.join(duplicate_decisions)}")
    if len(decision_records) != 59:
        errors.append(f"Decision register count changed: found {len(decision_records)}, expected 59")
    known_requirements = set(ids)
    for decision_id, cells in decision_records:
        if len(cells) != 10:
            errors.append(f"{decision_id}: expected 10 decision fields, found {len(cells)}")
            continue
        requirement_ids = {
            token.strip()
            for token in re.split(r"[, ]+", cells[2])
            if token.strip().startswith("PP-")
        }
        if not requirement_ids:
            errors.append(f"{decision_id}: no requirement reference")
        unresolved = sorted(requirement_ids - known_requirements)
        if unresolved:
            errors.append(f"{decision_id}: unresolved requirements {', '.join(unresolved)}")
        policy_path = cells[3]
        if not (root / policy_path).exists():
            errors.append(f"{decision_id}: missing canonical policy {policy_path}")
        if cells[8] not in {"accepted", "provisional", "deferred", "blocked", "superseded"}:
            errors.append(f"{decision_id}: invalid decision status {cells[8]!r}")
        if cells[9] not in {"yes", "no"}:
            errors.append(f"{decision_id}: Faruk confirmation must be yes/no")

    vision_traceability = root / "docs/governance/PLATFORM_VISION_TRACEABILITY.md"
    if vision_traceability.is_file():
        vision_text = vision_traceability.read_text(encoding="utf-8")
        vision_requirements = set(
            re.findall(r"\bPP-(?!DEC-)[A-Z]+-\d{3}\b", vision_text)
        )
        unresolved_vision_requirements = sorted(vision_requirements - known_requirements)
        if unresolved_vision_requirements:
            errors.append(
                "Platform Vision traceability has unresolved requirements: "
                + ", ".join(unresolved_vision_requirements)
            )
        vision_decisions = set(re.findall(r"\bPP-DEC-\d{3}\b", vision_text))
        unresolved_vision_decisions = sorted(vision_decisions - set(decision_ids))
        if unresolved_vision_decisions:
            errors.append(
                "Platform Vision traceability has unresolved decisions: "
                + ", ".join(unresolved_vision_decisions)
            )
        if "CONFLICT-007 resolved" not in vision_text:
            errors.append("Platform Vision traceability does not mark CONFLICT-007 resolved")

    expected = [
        "docs/product/PRODUCT_CONSTITUTION.md",
        "docs/product/SOURCE_PRECEDENCE.md",
        "docs/governance/RACI.md",
        "docs/governance/APPROVED_DECISION_REGISTER.md",
        "docs/governance/PLATFORM_VISION_TRACEABILITY.md",
        "docs/governance/NORMATIVE_COVERAGE.md",
        "docs/governance/APPROVAL_AND_DELEGATION_POLICY.md",
        "docs/governance/PHASE_1_ACCEPTANCE.md",
        "docs/audits/PHASE_0_CURSOR_AUDIT.md",
        "AGENTS.md",
    ]
    for path in expected:
        if not (root / path).exists():
            errors.append(f"Missing canonical artifact: {path}")

    canonical_paths = [
        root / "AGENTS.md",
        root / ".cursor",
        root / "docs/product",
        root / "docs/governance",
    ]
    canonical_text = "\n".join(
        path.read_text(encoding="utf-8")
        for base in canonical_paths
        for path in ([base] if base.is_file() else sorted(base.rglob("*")))
        if path.is_file()
    )
    if re.search(r"\bFarouk\b", canonical_text):
        errors.append("Canonical governance uses non-approved spelling 'Farouk'")
    if "$1,200" not in canonical_text:
        errors.append("Routine approval threshold $1,200 is missing")
    if "$2,500" not in canonical_text or "provisional" not in canonical_text.lower():
        errors.append("Provisional emergency threshold $2,500 is missing")
    if "shared master code" not in canonical_text.lower():
        errors.append("Shared-master-code prohibition is missing")
    if "formal accounting" not in canonical_text.lower():
        errors.append("Formal accounting boundary is missing")
    forbidden_claims = {
        r"\b(?:implement|enable|plan)\w*\s+(?:future\s+)?(?:zillow|facebook)\b": "listing syndication reintroduced",
        r"\bperchpoint\s+(?:shall|will)\s+replace\s+formal accounting\b": "formal accounting replacement claimed",
        r"\b(?:allow|use|rely on)\w*\s+shared (?:resident |household )?(?:password|login|credential)\b": "shared credentials allowed",
        r"\bmaintenance employees? (?:may|can) purchase\b": "maintenance standing purchase authority",
        r"\bai (?:may|can|shall|will) (?:approve|decide|move funds)\b": "unsupported autonomous AI authority",
    }
    for pattern, message in forbidden_claims.items():
        if re.search(pattern, canonical_text, flags=re.IGNORECASE):
            errors.append(message)
    incomplete_cursor_ids = []
    for base in (root / ".cursor/rules", root / ".cursor/agents"):
        for path in base.glob("*"):
            if path.is_file() and re.search(
                r"\bPP-[A-Z]+\b(?!-\d)", path.read_text(encoding="utf-8")
            ):
                incomplete_cursor_ids.append(str(path.relative_to(root)))
    if incomplete_cursor_ids:
        errors.append(
            "Cursor files use requirement-family prefixes instead of stable IDs: "
            + ", ".join(incomplete_cursor_ids)
        )
    semantic_fragments = {
        "all capital projects shall require faruk": "capital-project authority",
        "broad operational authority within policy but no developer": "Ann authority separation",
        "operational actions shall remain limited to separately granted": "Nathan dual-role separation",
        "formal accounting software retains": "formal accounting boundary",
        "sole target routine operational interface": "sole operational interface",
        "exclusive target listing": "website-only listings",
        "original recommendation shall remain immutable": "recommendation preservation",
        "contractor access shall be assignment-scoped": "contractor scope",
        "synthetic development data shall contain no real pii": "synthetic PII prohibition",
        "maintenance mobile application shall remain outside": "maintenance mobile boundary",
        "weighted total value": "provider value-for-cost policy",
        "provisional $2,500": "provisional emergency threshold",
    }
    lower_canonical = canonical_text.lower()
    for fragment, policy in semantic_fragments.items():
        if fragment not in lower_canonical:
            errors.append(f"Missing semantic policy: {policy}")

    link_roots = [
        root / "README.md",
        root / "docs/phase0/README.md",
        root / "docs/product",
        root / "docs/governance",
        root / "docs/audits",
        root / "docs/plans",
        root / "docs/source/README.md",
        root / "docs/source/provenance",
    ]
    link_files = [
        path
        for base in link_roots
        for path in ([base] if base.is_file() else sorted(base.rglob("*.md")))
        if path.is_file()
    ]
    for path in link_files:
        markdown = path.read_text(encoding="utf-8")
        if not markdown.startswith("#"):
            errors.append(f"{path.relative_to(root)}: Markdown must start with a heading")
        if "\x00" in markdown or "\t" in markdown:
            errors.append(f"{path.relative_to(root)}: Markdown contains NUL or tab characters")
        if any(line.endswith((" ", "\t")) for line in markdown.splitlines()):
            errors.append(f"{path.relative_to(root)}: Markdown contains trailing whitespace")
        for link in LINK_RE.findall(markdown):
            if "://" in link or link.startswith("#"):
                continue
            local = link.split("#", 1)[0]
            if local and not (path.parent / local).resolve().exists():
                errors.append(f"{path.relative_to(root)}: broken local link {link}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    records = parse_register(REGISTER.read_text(encoding="utf-8"))
    counts = Counter(requirement_id.rsplit("-", 1)[0] for requirement_id, _ in records)
    print(f"Validated {len(records)} requirements across {len(counts)} prefixes.")
    print(f"Validated {len(parse_decisions(DECISIONS.read_text(encoding='utf-8')))} decisions.")
    print(" ".join(f"{prefix}={counts[prefix]}" for prefix in sorted(counts)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
