"""Downgrade and re-upgrade a disposable database. Does not change perchpoint_phase2."""
from __future__ import annotations

import os
import subprocess
import sys
import time

from sqlalchemy import text

from perchpoint.db import engine_for
from perchpoint.seed import seed
from perchpoint.settings import Settings

NAME = "perchpoint_phase3_rollback"


def main() -> None:
    settings = Settings.load()
    root = settings.admin_url.rsplit("/", 1)[0]
    admin = engine_for(root + "/postgres")
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {NAME} WITH (FORCE)"))
        connection.execute(text(f"CREATE DATABASE {NAME}"))
        connection.execute(text(f"GRANT CONNECT, CREATE ON DATABASE {NAME} TO perchpoint_migrator"))
        connection.execute(text(f"GRANT CONNECT ON DATABASE {NAME} TO perchpoint_runtime"))
    admin.dispose()
    database = engine_for(root + "/" + NAME)
    with database.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("GRANT ALL ON SCHEMA public TO perchpoint_migrator"))
    database.dispose()
    os.environ["PHASE2_MIGRATOR_URL"] = settings.migrator_url.rsplit("/", 1)[0] + "/" + NAME
    started = time.perf_counter()
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    subprocess.run([sys.executable, "-m", "alembic", "downgrade", "-1"], check=True)
    with database.connect() as connection:
        index_gone = connection.execute(text("SELECT count(*) FROM pg_indexes WHERE indexname = 'activity_resource_time'")).scalar()
        prior = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        properties = connection.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_name = 'properties'")).scalar()
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    database = engine_for(root + "/" + NAME)
    rolled_back = False
    try:
        with database.begin() as connection:
            connection.execute(text("CREATE TABLE half_applied (id integer)"))
            connection.execute(text("THIS IS NOT SQL"))
    except Exception:
        rolled_back = True
    with database.connect() as connection:
        half = connection.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_name = 'half_applied'")).scalar()
        head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        index_back = connection.execute(text("SELECT count(*) FROM pg_indexes WHERE indexname = 'activity_resource_time'")).scalar()
    seed(database=NAME)
    seed(database=NAME)
    with database.connect() as connection:
        elm = connection.execute(text("SELECT count(*) FROM properties WHERE name LIKE 'Example Elm Court%'")).scalar()
    database.dispose()
    duration = round(time.perf_counter() - started, 3)
    admin = engine_for(root + "/postgres")
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {NAME} WITH (FORCE)"))
        left = connection.execute(text("SELECT count(*) FROM pg_database WHERE datname = :name"), {"name": NAME}).scalar()
        primary = engine_for(root + "/perchpoint_phase2").connect().execute(text("SELECT version_num FROM alembic_version")).scalar()
    admin.dispose()
    print(
        f"rollback_ok prior={prior} head={head} index_after_downgrade={index_gone} "
        f"properties_remain={properties} index_after_upgrade={index_back} half_applied={half} "
        f"rolled_back={rolled_back} elm={elm} disposable_left={left} primary_head={primary} duration_s={duration}"
    )
    if not (prior == "0005_listing_notes" and head == "0006_activity_index" and index_gone == 0 and properties == 1 and index_back == 1 and half == 0 and rolled_back and elm == 1 and left == 0 and primary == "0006_activity_index"):
        raise SystemExit("rollback drill failed")


if __name__ == "__main__":
    main()
