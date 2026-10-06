"""Restart the scoped Phase 7 Postgres and prove the migrated database recovers."""
from __future__ import annotations

import json
import subprocess
import time

from sqlalchemy import create_engine, text

ADMIN = "postgresql+psycopg://postgres:local-only-not-production@127.0.0.1:54339/perchpoint_phase2"
CONTAINER = "perchpoint-phase7-accept-postgres-1"


def main() -> int:
    subprocess.run(["docker", "restart", CONTAINER], check=True)
    deadline = time.time() + 60
    version = None
    while time.time() < deadline:
        try:
            engine = create_engine(ADMIN)
            with engine.connect() as connection:
                version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                role = connection.execute(
                    text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'perchpoint_runtime'")
                ).one()
            engine.dispose()
            break
        except Exception:
            time.sleep(2)
    else:
        print(json.dumps({"recovered": False}))
        return 1
    payload = {
        "container": CONTAINER,
        "migration_head": version,
        "recovered": True,
        "runtime_bypassrls": bool(role[1]),
        "runtime_superuser": bool(role[0]),
    }
    print(json.dumps(payload))
    if version != "0035_phase7_property_visibility" or role[0] or role[1]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
