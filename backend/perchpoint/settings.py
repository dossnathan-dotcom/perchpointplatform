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
        environment = os.environ.get("PHASE3_ENVIRONMENT", "local")
        mode = os.environ.get("PHASE2_LOCAL_AUTH", "")
        values = {
            "admin_url": os.environ.get("PHASE2_ADMIN_URL", ""),
            "migrator_url": os.environ.get("PHASE2_MIGRATOR_URL", ""),
            "runtime_url": os.environ.get("PHASE2_RUNTIME_URL", ""),
            "jwt_secret": os.environ.get("PHASE2_JWT_SECRET", ""),
            "dev_password": os.environ.get("PHASE2_DEV_PASSWORD", ""),
            "webhook_secret": os.environ.get("PHASE2_WEBHOOK_SECRET", ""),
        }
        if environment == "production":
            reasons = []
            if mode == "development":
                reasons.append("local-development auth")
            if os.environ.get("PHASE3_SYNTHETIC_CREDENTIALS") == "1":
                reasons.append("synthetic credentials")
            if os.environ.get("PHASE3_PERMISSIVE_ORIGINS") == "1":
                reasons.append("permissive origins")
            for name, value in values.items():
                lowered = value.lower()
                if not value or "replace-" in lowered or "changeme" in lowered or lowered in {"development", "secret", "password"}:
                    reasons.append(name)
            if reasons:
                raise Phase2ConfigurationError("Production startup refused: " + ", ".join(reasons))
        elif mode != "development":
            raise Phase2ConfigurationError("PHASE2_LOCAL_AUTH must be development; Phase 2 local auth is not production identity")
        missing = [name for name, value in values.items() if not value or value.startswith("replace-")]
        if missing:
            raise Phase2ConfigurationError("Missing local Phase 2 settings: " + ", ".join(missing))
        return cls(local_auth=mode, **values)
