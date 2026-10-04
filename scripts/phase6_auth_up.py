"""Start the local Auth service and Mailpit. Refuses production and prints no secrets."""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from perchpoint.settings import Settings  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402


def main() -> None:
    if os.environ.get("PHASE3_ENVIRONMENT") in {"staging", "production"}:
        raise SystemExit("refusing to start local identity services in a hosted environment")
    settings = Settings.load()
    admin = settings.admin_url
    quoted = admin.split("://", 1)[1]
    user_pass, host_db = quoted.split("@", 1)
    user, password = user_pass.split(":", 1)
    host = host_db.split("/", 1)[0]
    engine = create_engine(admin)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        exists = connection.execute(text("SELECT 1 FROM pg_database WHERE datname = 'perchpoint_auth'")).scalar()
        if not exists:
            connection.execute(text("CREATE DATABASE perchpoint_auth"))
    engine.dispose()
    auth_engine = create_engine(admin.rsplit("/", 1)[0] + "/perchpoint_auth")
    with auth_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
        connection.execute(text("ALTER DATABASE perchpoint_auth SET search_path TO auth, public"))
    auth_engine.dispose()
    database_url = f"postgres://{quote(user)}:{quote(password)}@host.docker.internal:{host.split(':')[-1]}/perchpoint_auth"
    secret = os.environ.get("PHASE6_PROVIDER_JWT_SECRET", "local-only-not-production-gotrue-jwt-secret")
    env = os.environ.copy()
    env["PHASE6_AUTH_DATABASE_URL"] = database_url
    env["PHASE6_PROVIDER_JWT_SECRET"] = secret
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.phase6.yml", "up", "-d"],
        cwd=ROOT,
        env=env,
        check=True,
    )
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:9999/health", timeout=2) as response:
                if response.status == 200:
                    _provision(settings)
                    print("phase6 auth ready")
                    return
        except Exception:
            time.sleep(2)
    raise SystemExit("local auth service did not become ready")


def _provision(settings: Settings) -> None:
    from perchpoint.phase6_provider import ProviderError, create_user

    emails = (
        "ann.synthetic@example.com",
        "nathan.synthetic@example.com",
        "faruk.synthetic@example.com",
    )
    for email in emails:
        try:
            create_user(email, settings.dev_password)
        except ProviderError as exc:
            if exc.code != "authentication_failed":
                raise
    auth_engine = create_engine(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_auth")
    with auth_engine.begin() as connection:
        connection.execute(text("UPDATE auth.users SET aud = 'authenticated', role = 'authenticated' WHERE aud IS NULL OR aud = ''"))
    auth_engine.dispose()


if __name__ == "__main__":
    main()
