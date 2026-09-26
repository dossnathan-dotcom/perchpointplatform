"""Remove leftover copies of packages that are not the installed fixed releases."""
from __future__ import annotations

import pathlib
import shutil
import zipfile

ROOTS = (pathlib.Path("/usr"), pathlib.Path("/root"), pathlib.Path("/opt"))
NEEDLES = ("Version: 70.3.0", "Version: 1.1.2", "Version: 0.45.1", "Version: 5.3.0")
MARKERS = ("70.3.0", "msgpack-1.1.2", "wheel-0.45.1", "jaraco.context-5.3.0")


def main() -> None:
    for root in ROOTS:
        if not root.exists():
            continue
        for meta in list(root.rglob("METADATA")):
            try:
                text = meta.read_text(errors="ignore")
            except OSError:
                continue
            if any(needle in text for needle in NEEDLES):
                print("drop", meta.parent)
                shutil.rmtree(meta.parent, ignore_errors=True)
        for path in list(root.rglob("*")):
            if not path.is_file() or path.suffix not in {".zip", ".egg", ".whl"}:
                continue
            try:
                with zipfile.ZipFile(path) as archive:
                    listing = "\n".join(archive.namelist())
            except (OSError, zipfile.BadZipFile):
                continue
            if any(marker in listing for marker in MARKERS):
                print("drop-archive", path)
                path.unlink()


if __name__ == "__main__":
    main()
