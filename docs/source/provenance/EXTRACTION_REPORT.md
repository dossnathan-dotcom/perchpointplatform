# Extraction Report

Initial extraction run: 2026-09-23T20:17:32+00:00.
Platform Vision closure run: 2026-09-23.

## Method
PyMuPDF ordered-text extraction was performed page by page. Page markers were added to normalized Markdown. Source/copy SHA-256 equality was required before acceptance.

## Results
- `HawkVision Homes — Enterprise Platform Delivery Roadmap.pdf`: 17 pages, 37,694 characters, empty pages: none.
- `Discovery Business Meeting- Nathan and Faruk.pdf`: 29 pages, 27,733 characters, empty pages: none.
- `HawkVision_Homes_Platform_Vision (1).pdf`: 2/2 pages directly extracted, empty,
  unreadable, image-only, and OCR-derived pages: none.
- First page marker: present. Final page marker: present. Marker sequence: 1, 2 with no gaps.
- Repeated generation with `python scripts/verify_sources.py --write-platform` produced the
  same Markdown SHA-256:
  `F317FBF15B35006FF9EC7F9A1CBBBFEBD4C0D8719263B9A4CD81EAF68BD56453`.

## Limitations and manual verification
- The discovery PDF is an editorialized discovery summary rather than a verbatim speaker-by-speaker transcript; uncertain speaker attribution cannot be repaired without audio.
- PyMuPDF preserves reading order but not guaranteed visual table geometry. Roadmap tables and
  the Platform Vision two-column scope tables require visual comparison.
- No malformed NUL characters remained after normalization.
- No OCR was required for any of the three PDFs.
- `PLATFORM_VISION.md` contains only direct extraction and provenance labels. Analyst
  reconciliation is kept in governance/provenance documents. The earlier pasted text remains
  separately labeled non-authoritative in `PLATFORM_VISION_PROVISIONAL.md`.

## Acceptance
All three originals pass checksum, readability, expected-page, complete-marker, and
deterministic Platform Vision extraction checks in `scripts/verify_sources.py`.
