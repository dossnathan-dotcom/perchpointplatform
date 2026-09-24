"""Local Phase 2 settings. Refuses any non-development mode."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Phase2ConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    local_auth: str
    admin_url: str
    migrator_url: str
    runtime_url: str
    jwt_secret: str
    dev_password: str
    webhook_secret: str

    @classmethod
    def load(cls) -> "Settings":
        mode = os.environ.get("PHASE2_LOCAL_AUTH", "")
        if mode != "development":
            raise Phase2ConfigurationError("PHASE2_LOCAL_AUTH must be development; Phase 2 local auth is not production identity")
        values = {
            "admin_url": os.environ.get("PHASE2_ADMIN_URL", ""),
            "migrator_url": os.environ.get("PHASE2_MIGRATOR_URL", ""),
            "runtime_url": os.environ.get("PHASE2_RUNTIME_URL", ""),
            "jwt_secret": os.environ.get("PHASE2_JWT_SECRET", ""),
            "dev_password": os.environ.get("PHASE2_DEV_PASSWORD", ""),
            "webhook_secret": os.environ.get("PHASE2_WEBHOOK_SECRET", ""),
        }
        missing = [name for name, value in values.items() if not value or value.startswith("replace-")]
        if missing:
            raise Phase2ConfigurationError("Missing local Phase 2 settings: " + ", ".join(missing))
        return cls(local_auth=mode, **values)
