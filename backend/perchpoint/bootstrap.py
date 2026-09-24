"""Create the isolated local database and roles. Does not open a cloud account."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from .db import admin_connection, engine_for
from .settings import Settings

ROOT = Path(__file__).resolve().parents[1]


def bootstrap(settings: Settings | None = None) -> None:
    settings = settings or Settings.load()
    admin = engine_for(settings.admin_url)
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        _role(connection, "perchpoint_migrator", _password(settings.migrator_url), bypass=False)
        _role(connection, "perchpoint_runtime", _password(settings.runtime_url), bypass=False)
        _role(connection, "perchpoint_definer", None, bypass=True, login=False)
        exists = connection.execute(text("SELECT 1 FROM pg_database WHERE datname = 'perchpoint_phase2'")).scalar()
        if not exists:
            connection.execute(text("CREATE DATABASE perchpoint_phase2"))
        connection.execute(text("GRANT CONNECT ON DATABASE perchpoint_phase2 TO perchpoint_migrator, perchpoint_runtime"))
    admin.dispose()
    database_admin = settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2"
    owner = engine_for(database_admin)
    with owner.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("GRANT CREATE ON DATABASE perchpoint_phase2 TO perchpoint_migrator"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO perchpoint_migrator"))
        connection.execute(text("GRANT perchpoint_definer TO perchpoint_migrator"))
    owner.dispose()
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True)
    with owner.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO perchpoint_definer"))
        connection.execute(text("GRANT USAGE ON SCHEMA perchpoint TO perchpoint_definer"))
        connection.execute(text("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA perchpoint TO perchpoint_definer"))
        for name in (
            "actor_in_org(uuid)",
            "published_listings()",
            "login_material(text)",
            "current_membership(uuid)",
            "submit_public_inquiry(uuid, text, text, text, text, text, text, uuid)",
            "claim_outbox(text)",
            "finish_outbox(uuid, boolean)",
        ):
            connection.execute(text(f"ALTER FUNCTION perchpoint.{name} OWNER TO perchpoint_definer"))
    owner.dispose()


def _password(url: str) -> str:
    return url.split("://", 1)[1].split("@", 1)[0].split(":", 1)[1]


def _role(connection, name: str, password: str | None, bypass: bool, login: bool = True) -> None:
    exists = connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": name}).scalar()
    login_sql = "LOGIN" if login else "NOLOGIN"
    bypass_sql = "BYPASSRLS" if bypass else "NOBYPASSRLS"
    if exists:
        return
    if password:
        escaped = password.replace("'", "''")
        connection.execute(text(f"CREATE ROLE {name} {login_sql} {bypass_sql} NOSUPERUSER PASSWORD '{escaped}'"))
    else:
        connection.execute(text(f"CREATE ROLE {name} {login_sql} {bypass_sql} NOSUPERUSER"))


if __name__ == "__main__":
    bootstrap()
