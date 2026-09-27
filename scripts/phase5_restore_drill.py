"""Disposable Phase 5 backup and restore. Does not touch perchpoint_phase2."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from perchpoint.db import engine_for  # noqa: E402
from perchpoint.settings import Settings  # noqa: E402

SOURCE = "perchpoint_phase5_drill_source"
RECOVERY = "perchpoint_phase5_drill_recovery"
FAILED = "perchpoint_phase5_drill_failed"
PG_BIN = Path(r"C:\Program Files\PostgreSQL\16\bin")


def _admin(settings: Settings):
    return engine_for(settings.admin_url.rsplit("/", 1)[0] + "/postgres")


def main() -> None:
    settings = Settings.load()
    admin = _admin(settings)
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        for name in (SOURCE, RECOVERY, FAILED):
            connection.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))
        connection.execute(text(f"CREATE DATABASE {SOURCE}"))
        connection.execute(text(f"GRANT CONNECT, CREATE ON DATABASE {SOURCE} TO perchpoint_migrator"))
    prepared = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/" + SOURCE)
    with prepared.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("GRANT ALL ON SCHEMA public TO perchpoint_migrator"))
    prepared.dispose()
    migrator = os.environ["PHASE2_MIGRATOR_URL"]
    os.environ["PHASE2_MIGRATOR_URL"] = migrator.rsplit("/", 1)[0] + "/" + SOURCE
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, check=True)
    os.environ["PHASE2_MIGRATOR_URL"] = migrator
    source = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/" + SOURCE)
    with source.begin() as connection:
        connection.execute(text("INSERT INTO organizations (id, name, synthetic) VALUES ('00000000-0000-4000-8000-0000000000a1', 'Drill Org', true)"))
        connection.execute(
            text(
                """
                INSERT INTO properties (organization_id, id, name, property_type)
                VALUES ('00000000-0000-4000-8000-0000000000a1', '00000000-0000-4000-8000-0000000000b1', 'Drill Hawthorn', 'single_family')
                """
            )
        )
        head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        expected = connection.execute(text("SELECT count(*) FROM properties")).scalar()
    source.dispose()
    parsed = urlparse(settings.admin_url)
    dump = Path(os.environ.get("TEMP", "/tmp")) / "perchpoint-phase5-drill.dump"
    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password or ""
    subprocess.run(
        [str(PG_BIN / "pg_dump.exe"), "-h", parsed.hostname or "127.0.0.1", "-p", str(parsed.port or 5432), "-U", parsed.username or "postgres", "-d", SOURCE, "-Fc", "-f", str(dump)],
        check=True,
        env=env,
    )
    size = dump.stat().st_size
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f"CREATE DATABASE {RECOVERY}"))
    subprocess.run(
        [str(PG_BIN / "pg_restore.exe"), "-h", parsed.hostname or "127.0.0.1", "-p", str(parsed.port or 5432), "-U", parsed.username or "postgres", "-d", RECOVERY, "--no-owner", str(dump)],
        check=True,
        env=env,
    )
    dump.unlink()
    recovery = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/" + RECOVERY)
    with recovery.connect() as connection:
        actual_head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        actual = connection.execute(text("SELECT count(*) FROM properties WHERE name = 'Drill Hawthorn'")).scalar()
    recovery.dispose()
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        for name in (SOURCE, RECOVERY):
            connection.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))
        left = connection.execute(text("SELECT count(*) FROM pg_database WHERE datname IN (:source, :recovery)"), {"source": SOURCE, "recovery": RECOVERY}).scalar()
    dev = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with dev.connect() as connection:
        elm = connection.execute(text("SELECT count(*) FROM properties WHERE id = '9960c7ea-3d4b-5fd7-90b3-6360439a6875'")).scalar()
    dev.dispose()
    if head != actual_head or expected != actual or left != 0 or elm != 1:
        raise SystemExit(f"restore mismatch head={head}/{actual_head} count={expected}/{actual} left={left} elm={elm}")
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f"CREATE DATABASE {FAILED}"))
    failed = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/" + FAILED)
    rolled_back = False
    try:
        with failed.begin() as connection:
            connection.execute(text("CREATE TABLE half_applied (id integer)"))
            connection.execute(text("THIS IS NOT SQL"))
    except Exception:
        rolled_back = True
    with failed.connect() as connection:
        present = connection.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_name = 'half_applied'")).scalar()
    failed.dispose()
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {FAILED} WITH (FORCE)"))
        failed_left = connection.execute(text("SELECT count(*) FROM pg_database WHERE datname = :name"), {"name": FAILED}).scalar()
    admin.dispose()
    if not rolled_back or present != 0 or failed_left != 0:
        raise SystemExit(f"rollback drill failed rolled_back={rolled_back} present={present} left={failed_left}")
    object_note = _object_roundtrip()
    print(f"restore_ok head={head} properties={actual} dump_bytes={size} disposable_left={left} elm={elm}")
    print(f"migration_rollback_ok rolled_back={rolled_back} half_applied={present} disposable_left={failed_left}")
    print(object_note)


def _object_roundtrip() -> str:
    if not os.environ.get("PHASE5_S3_ENDPOINT"):
        return "object_backup=skipped"
    os.environ["PHASE5_OBJECT_STORE"] = "s3"
    from perchpoint.phase5_files import delete_object, ensure_bucket, read_object, write_object

    ensure_bucket()
    payload = b"phase5-object-backup"
    key = "org/00000000-0000-4000-8000-0000000000a1/accepted/aabbccddeeff00112233445566778899"
    copy = "org/00000000-0000-4000-8000-0000000000a1/exports/aabbccddeeff00112233445566778899"
    write_object(key, payload)
    write_object(copy, read_object(key))
    delete_object(key)
    restored = read_object(copy)
    delete_object(copy)
    if restored != payload or hashlib.sha256(restored).hexdigest() != hashlib.sha256(payload).hexdigest():
        raise SystemExit("object restore mismatch")
    return f"object_backup_ok bytes={len(payload)} sha256={hashlib.sha256(payload).hexdigest()}"


if __name__ == "__main__":
    main()
