"""Remove pip from a runtime image and refuse to leave known-vulnerable copies.

pip 26.2 vendors MessagePack 1.1.2 under ``pip/_vendor/msgpack`` and ships
``pip/_vendor/bom.cdx.json``, which records setuptools 70.3.0 even though
``setuptools/package_index.py`` is not in the pip wheel. PerchPoint does not
import pip at runtime. Deleting the pip package removes that vendored code and
that SBOM together. The web image also drops packaging tools it never imports.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil

SITE = pathlib.Path("/usr/local/lib/python3.13/site-packages")
ROOTS = (pathlib.Path("/usr"), pathlib.Path("/root"), pathlib.Path("/opt"))
PACKAGING_NAMES = (
    "setuptools",
    "pkg_resources",
    "_distutils_hack",
    "wheel",
    "jaraco",
    "msgpack",
    "pip",
)


def _rmtree(path: pathlib.Path) -> None:
    if path.exists():
        print("drop", path)
        shutil.rmtree(path)


def remove_pip() -> None:
    if SITE.exists():
        _rmtree(SITE / "pip")
        for dist in SITE.glob("pip-*.dist-info"):
            _rmtree(dist)
    binary_dir = pathlib.Path("/usr/local/bin")
    if binary_dir.exists():
        for binary in binary_dir.glob("pip*"):
            print("drop", binary)
            binary.unlink()
    _rmtree(pathlib.Path("/usr/local/lib/python3.13/ensurepip"))
    for root in ROOTS:
        if not root.exists():
            continue
        for archive in list(root.rglob("*.whl")):
            print("drop", archive)
            archive.unlink()


def remove_packaging_tools() -> None:
    if not SITE.exists():
        return
    for name in PACKAGING_NAMES:
        _rmtree(SITE / name)
    patterns = (
        "setuptools-*",
        "wheel-*",
        "jaraco*",
        "msgpack-*",
        "pip-*",
    )
    for pattern in patterns:
        for path in SITE.glob(pattern):
            _rmtree(path)


def assert_clean() -> None:
    leftovers: list[pathlib.Path] = []
    for root in ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.name == "__init__.py" and path.parent.name == "msgpack":
                text = path.read_text(errors="ignore")
                if '__version__ = "1.1.2"' in text:
                    leftovers.append(path)
            elif path.name in {"bom.cdx.json", "vendor.txt"}:
                text = path.read_text(errors="ignore")
                if "70.3.0" in text or "msgpack==1.1.2" in text or "msgpack@1.1.2" in text:
                    leftovers.append(path)
            elif path.name == "METADATA":
                for line in path.read_text(errors="ignore").splitlines():
                    if line in {"Version: 70.3.0", "Version: 1.1.2", "Version: 0.45.1", "Version: 5.3.0"}:
                        leftovers.append(path)
                        break
    if leftovers:
        raise SystemExit("vulnerable package copies remain: " + ", ".join(str(path) for path in leftovers))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove-packaging-tools", action="store_true")
    args = parser.parse_args()
    remove_pip()
    if args.remove_packaging_tools:
        remove_packaging_tools()
    assert_clean()


if __name__ == "__main__":
    main()
