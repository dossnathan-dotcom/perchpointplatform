"""Validate authoritative PDF bytes, page coverage, and deterministic extraction."""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
PAGE_MARKER_RE = re.compile(r"^<!-- source-page: (\d+) -->$", re.MULTILINE)


@dataclass(frozen=True)
class Source:
    name: str
    original: str
    normalized: str
    sha256: str
    pages: int


SOURCES = (
    Source(
        "Enterprise Platform Delivery Roadmap",
        "docs/source/originals/HawkVision_Homes_Enterprise_Platform_Delivery_Roadmap.pdf",
        "docs/source/normalized/ENTERPRISE_DELIVERY_ROADMAP.md",
        "380B6947DC635DA55CB3FF5C69E6805E9D3C4BB35B9C116C0D2A00CF9F5A6F59",
        17,
    ),
    Source(
        "Discovery Business Meeting",
        "docs/source/originals/Discovery_Business_Meeting_Nathan_and_Faruk.pdf",
        "docs/source/normalized/DISCOVERY_MEETING_TRANSCRIPT.md",
        "415079DD03858A97DF5658FAA51494BD7AA396C7748C68379A46EC056015ABE6",
        29,
    ),
    Source(
        "HawkVision Homes Platform Vision",
        "docs/source/originals/HawkVision_Homes_Platform_Vision.pdf",
        "docs/source/normalized/PLATFORM_VISION.md",
        "173DFB10180534CEA01E1CD8D9625362DF20B0E8DBA3A7790A4147C2B6357CB0",
        2,
    ),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def extract_pages(path: Path) -> list[str]:
    with pymupdf.open(path) as document:
        if document.needs_pass:
            raise ValueError(f"encrypted PDF requires a password: {path}")
        return [page.get_text("text").rstrip() for page in document]


def render_platform_vision(path: Path) -> str:
    pages = extract_pages(path)
    sections = [
        "# Platform Vision — Authoritative Extraction",
        "",
        "> Direct text extraction from the byte-preserved authoritative PDF using PyMuPDF "
        f"{pymupdf.VersionBind}.",
        "> No OCR or analyst interpretation is included below. Page markers preserve PDF "
        "source-page provenance.",
    ]
    for number, text in enumerate(pages, start=1):
        sections.extend(
            [
                "",
                f"<!-- source-page: {number} -->",
                "",
                f"## Source page {number}",
                "",
                text if text else "*[Blank or image-only page; no directly extractable text.]*",
            ]
        )
    return "\n".join(sections).rstrip() + "\n"


def validate_sources(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for source in SOURCES:
        original = root / source.original
        normalized = root / source.normalized
        if not original.is_file():
            errors.append(f"{source.name}: missing original {source.original}")
            continue
        actual_hash = sha256(original)
        if actual_hash != source.sha256:
            errors.append(
                f"{source.name}: SHA-256 {actual_hash} does not match {source.sha256}"
            )
        try:
            with pymupdf.open(original) as document:
                actual_pages = document.page_count
                if document.needs_pass:
                    errors.append(f"{source.name}: PDF requires a password")
        except Exception as exc:  # pragma: no cover - diagnostic boundary
            errors.append(f"{source.name}: unreadable PDF: {exc}")
            continue
        if actual_pages != source.pages:
            errors.append(
                f"{source.name}: page count {actual_pages} does not match {source.pages}"
            )
        if not normalized.is_file():
            errors.append(f"{source.name}: missing extraction {source.normalized}")
            continue
        markers = [
            int(value)
            for value in PAGE_MARKER_RE.findall(normalized.read_text(encoding="utf-8"))
        ]
        expected_markers = list(range(1, source.pages + 1))
        if markers != expected_markers:
            errors.append(
                f"{source.name}: page markers {markers} do not match {expected_markers}"
            )

    platform = SOURCES[-1]
    platform_original = root / platform.original
    platform_normalized = root / platform.normalized
    if platform_original.is_file() and platform_normalized.is_file():
        expected = render_platform_vision(platform_original)
        actual = platform_normalized.read_text(encoding="utf-8")
        if actual != expected:
            errors.append(
                "HawkVision Homes Platform Vision: extraction is not deterministic/current"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-platform",
        action="store_true",
        help="Regenerate the authoritative Platform Vision Markdown extraction.",
    )
    args = parser.parse_args()
    platform = SOURCES[-1]
    if args.write_platform:
        target = ROOT / platform.normalized
        target.write_text(
            render_platform_vision(ROOT / platform.original),
            encoding="utf-8",
            newline="\n",
        )

    errors = validate_sources()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    for source in SOURCES:
        print(f"{source.name}: SHA-256 verified; {source.pages}/{source.pages} pages")
    print(f"Extraction tool: PyMuPDF {pymupdf.VersionBind}; OCR pages: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
