import gzip
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("static_server", ROOT / "deploy" / "static_server.py")
SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER)


def test_precompressed_assets_round_trip_and_negotiate():
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        source = b"HawkVision Homes public shell " * 20
        (folder / "app.js").write_bytes(source)
        (folder / "app.js.gz").write_bytes(gzip.compress(source))
        (folder / "photo.avif").write_bytes(b"avif-bytes")
        published, encoded, modified = SERVER.published_files(folder)
        assert published["/app.js"] == source
        assert published["/photo.avif"] == b"avif-bytes"
        assert "/app.js.gz" not in published
        assert gzip.decompress(encoded["/app.js"]["gzip"]) == source
        assert "/photo.avif" not in encoded
        assert SERVER.choose_encoding(None, encoded["/app.js"]) is None
        assert SERVER.choose_encoding("", encoded["/app.js"]) is None
        assert SERVER.choose_encoding("%%% not-a-coding", encoded["/app.js"]) is None
        assert SERVER.choose_encoding("gzip", encoded["/app.js"]) == "gzip"
        assert SERVER.choose_encoding("br;q=0, gzip;q=1", encoded["/app.js"]) == "gzip"
        assert SERVER.choose_encoding("identity", encoded["/app.js"]) is None
        assert modified["/app.js"] > 0
        assert SERVER.content_type_for("/app.js") == "text/javascript"
        assert "immutable" in SERVER.security_headers("text/javascript", "/static/js/app.js")["cache-control"]
        assert SERVER.security_headers("text/html", "/")["cache-control"] == "no-store"
        assert "unsafe-inline" not in SERVER.CSP
