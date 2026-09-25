"""Synthetic restore between two disposable databases. Does not touch perchpoint_phase2."""
import os
import subprocess
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()
from perchpoint.db import engine_for
from perchpoint.settings import Settings

SOURCE = "perchpoint_phase3_drill_source"
RECOVERY = "perchpoint_phase3_drill_recovery"


def main() -> None:
    settings = Settings.load()
    root = settings.admin_url.rsplit("/", 1)[0]
    admin = engine_for(root + "/postgres")
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        for name in (SOURCE, RECOVERY):
            connection.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))
            connection.execute(text(f"CREATE DATABASE {name}"))
    source = engine_for(root + "/" + SOURCE)
    with source.begin() as connection:
        connection.execute(text("CREATE TABLE control_total (id integer PRIMARY KEY, marker text)"))
        connection.execute(text("INSERT INTO control_total VALUES (1, 'synthetic'), (2, 'synthetic'), (3, 'synthetic')"))
        expected = connection.execute(text("SELECT count(*), min(marker) FROM control_total")).one()
    source.dispose()
    parsed = urlparse(settings.admin_url)
    dump = os.environ.get("TEMP", "/tmp") + "\\perchpoint-phase3-drill.dump"
    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password or ""
    pg = r"C:\Program Files\PostgreSQL\16\bin"
    subprocess.run([os.path.join(pg, "pg_dump.exe"), "-h", parsed.hostname or "127.0.0.1", "-p", str(parsed.port or 5432), "-U", parsed.username or "postgres", "-d", SOURCE, "-Fc", "-f", dump], check=True, env=env)
    subprocess.run([os.path.join(pg, "pg_restore.exe"), "-h", parsed.hostname or "127.0.0.1", "-p", str(parsed.port or 5432), "-U", parsed.username or "postgres", "-d", RECOVERY, "--no-owner", dump], check=True, env=env)
    os.remove(dump)
    recovery = engine_for(root + "/" + RECOVERY)
    with recovery.connect() as connection:
        actual = connection.execute(text("SELECT count(*), min(marker) FROM control_total")).one()
    recovery.dispose()
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        for name in (SOURCE, RECOVERY):
            connection.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))
        left = connection.execute(text("SELECT count(*) FROM pg_database WHERE datname IN (:source, :recovery)"), {"source": SOURCE, "recovery": RECOVERY}).scalar()
        elm = engine_for(root + "/perchpoint_phase2").connect().execute(text("SELECT count(*) FROM properties WHERE id = '9960c7ea-3d4b-5fd7-90b3-6360439a6875'")).scalar()
    admin.dispose()
    if expected != actual or left != 0 or elm != 1:
        raise SystemExit(f"restore mismatch expected={expected} actual={actual} left={left} elm={elm}")
    print(f"restore_ok count={expected[0]} marker={expected[1]} disposable_left={left} elm={elm}")


if __name__ == "__main__":
    main()
