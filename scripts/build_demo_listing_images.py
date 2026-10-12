"""Build distinct local heroes from the generated demonstration photographs."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\Admin\.cursor\projects\c-Users-Admin-PerchPoint\assets")
PUBLIC = ROOT / "frontend" / "public" / "demo-photos"
GALLERY = {
    "house-exterior.jpg": "Exterior photograph generated for the local demonstration.",
    "apartment-exterior.jpg": "Apartment exterior generated for the local demonstration.",
    "living-room.jpg": "Living area generated for the local demonstration.",
    "kitchen.jpg": "Kitchen generated for the local demonstration.",
    "bedroom.jpg": "Bedroom generated for the local demonstration.",
}


def main() -> None:
    gallery = PUBLIC / "gallery"
    heroes = PUBLIC / "heroes"
    gallery.mkdir(parents=True, exist_ok=True)
    heroes.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, note in GALLERY.items():
        target = gallery / name
        shutil.copyfile(SOURCE / name, target)
        manifest.append({"file": f"gallery/{name}", "origin": "generated", "listing": "shared gallery", "license": note})
    house = Image.open(gallery / "house-exterior.jpg").convert("RGB")
    apartment = Image.open(gallery / "apartment-exterior.jpg").convert("RGB")
    for index in range(35):
        base = house if index % 2 == 0 else apartment
        width, height = base.size
        shift = (index * 17) % 48
        crop = base.crop((shift, shift // 2, width - (48 - shift), height - 24))
        graded = ImageEnhance.Color(crop).enhance(0.85 + (index % 5) * 0.05)
        graded = ImageEnhance.Brightness(graded).enhance(0.92 + (index % 4) * 0.04)
        slug = f"demo-{index + 1:02d}.webp"
        graded.save(heroes / slug, "WEBP", quality=78)
        manifest.append({"file": f"heroes/{slug}", "origin": "generated", "listing": f"demo-{index + 1:02d}", "license": "Derived locally from a generated demonstration photograph. No third-party listing photo."})
    (PUBLIC / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
