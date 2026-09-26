from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate_governance import parse_register, validate  # noqa: E402
from scripts.verify_sources import validate_sources  # noqa: E402


def test_repository_governance_is_consistent():
    assert validate(ROOT) == []


def test_authoritative_sources_are_complete_and_current():
    assert validate_sources(ROOT) == []


def test_duplicate_requirement_is_rejected(tmp_path):
    fixture = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", fixture / "docs")
    shutil.copytree(ROOT / ".cursor", fixture / ".cursor")
    shutil.copy2(ROOT / "AGENTS.md", fixture / "AGENTS.md")
    register = fixture / "docs/governance/REQUIREMENTS_TRACEABILITY.md"
    text = register.read_text(encoding="utf-8")
    first = parse_register(text)[0][0]
    section = text[text.index(f"## {first}") :]
    section = section[: section.find("\n## ", 4)] if "\n## " in section[4:] else section
    register.write_text(text + "\n" + section, encoding="utf-8")
    assert any("Duplicate requirement IDs" in error for error in validate(fixture))


def test_missing_required_field_is_rejected(tmp_path):
    fixture = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", fixture / "docs")
    shutil.copytree(ROOT / ".cursor", fixture / ".cursor")
    shutil.copy2(ROOT / "AGENTS.md", fixture / "AGENTS.md")
    register = fixture / "docs/governance/REQUIREMENTS_TRACEABILITY.md"
    text = register.read_text(encoding="utf-8")
    register.write_text(
        text.replace("- **Rationale:**", "- **Removed rationale:**", 1),
        encoding="utf-8",
    )
    assert any("missing fields Rationale" in error for error in validate(fixture))


def test_duplicate_decision_is_rejected(tmp_path):
    fixture = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", fixture / "docs")
    shutil.copytree(ROOT / ".cursor", fixture / ".cursor")
    shutil.copy2(ROOT / "AGENTS.md", fixture / "AGENTS.md")
    register = fixture / "docs/governance/APPROVED_DECISION_REGISTER.md"
    text = register.read_text(encoding="utf-8")
    decision_line = next(line for line in text.splitlines() if line.startswith("| PP-DEC-"))
    register.write_text(text + decision_line + "\n", encoding="utf-8")
    assert any("Duplicate decision IDs" in error for error in validate(fixture))
