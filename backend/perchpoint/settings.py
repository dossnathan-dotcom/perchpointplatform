"""Local Phase 2 settings. Refuses any non-development mode."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Phase2ConfigurationError(RuntimeError):
    pass


KNOWN_ENVIRONMENTS = {"local", "test", "ci", "staging", "production"}
HOSTED_ENVIRONMENTS = {"staging", "production"}
DISPOSABLE_MARKERS = ("replace-", "changeme", "local-only-not-production", "ci-only-not-production")


def configured_session_keys() -> list[str]:
    raw = os.environ.get("PHASE6_SESSION_KEYS") or os.environ.get(
        "PHASE6_SESSION_KEY",
        "local-only-not-production-session-key",
    )
    keys = [item.strip() for item in raw.split(",") if item.strip()]
    if not keys:
        raise Phase2ConfigurationError("Missing session encryption key")
    return keys


def use_psycopg(url: str) -> str:
    """The supported driver is psycopg 3. A bare postgresql:// URL selects psycopg2."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


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
        if environment not in KNOWN_ENVIRONMENTS:
            raise Phase2ConfigurationError("Unknown PHASE3_ENVIRONMENT")
        mode = os.environ.get("PHASE2_LOCAL_AUTH", "")
        values = {
            "admin_url": os.environ.get("PHASE2_ADMIN_URL", ""),
            "migrator_url": os.environ.get("PHASE2_MIGRATOR_URL", ""),
            "runtime_url": os.environ.get("PHASE2_RUNTIME_URL", ""),
            "jwt_secret": os.environ.get("PHASE2_JWT_SECRET", ""),
            "dev_password": os.environ.get("PHASE2_DEV_PASSWORD", ""),
            "webhook_secret": os.environ.get("PHASE2_WEBHOOK_SECRET", ""),
        }
        if environment in HOSTED_ENVIRONMENTS:
            reasons = []
            if mode == "development":
                reasons.append("local-development auth")
            if os.environ.get("PHASE3_SYNTHETIC_CREDENTIALS") == "1":
                reasons.append("synthetic credentials")
            if os.environ.get("PHASE3_PERMISSIVE_ORIGINS") == "1":
                reasons.append("permissive origins")
            if os.environ.get("PHASE6_ALLOW_DEV_JWT") == "1":
                reasons.append("development JWT")
            if os.environ.get("PHASE3_DEBUG_IDENTITY_BOOTSTRAP") == "1":
                reasons.append("debug identity bootstrap")
            for name, value in values.items():
                lowered = value.lower()
                if not value or any(marker in lowered for marker in DISPOSABLE_MARKERS) or lowered in {"development", "secret", "password"}:
                    reasons.append(name)
            if os.environ.get("PHASE4_ABUSE_PROVIDER", "") == "":
                reasons.append("distributed abuse protection")
            session_keys = configured_session_keys()
            if any(
                len(key) < 32
                or any(marker in key.lower() for marker in DISPOSABLE_MARKERS)
                for key in session_keys
            ):
                reasons.append("session encryption keys")
            provider_secret = os.environ.get("PHASE6_PROVIDER_JWT_SECRET", "")
            if len(provider_secret) < 32 or any(marker in provider_secret.lower() for marker in DISPOSABLE_MARKERS):
                reasons.append("identity provider secret")
            provider_url = os.environ.get("PHASE6_AUTH_URL", "")
            if not provider_url.startswith("https://") or "localhost" in provider_url or "127.0.0.1" in provider_url:
                reasons.append("identity provider")
            origins = [item.strip() for item in os.environ.get("PHASE6_ALLOWED_ORIGINS", "").split(",") if item.strip()]
            if not origins or any(origin == "*" or not origin.startswith("https://") for origin in origins):
                reasons.append("identity origin allowlist")
            redirects = [item.strip() for item in os.environ.get("PHASE6_REDIRECT_ALLOWLIST", "").split(",") if item.strip()]
            if not redirects or any(redirect == "*" or not redirect.startswith("https://") for redirect in redirects):
                reasons.append("identity redirect allowlist")
            if provider_secret and provider_secret in session_keys:
                reasons.append("separate identity and session keys")
            process_role = os.environ.get("PHASE6_PROCESS_ROLE", "api")
            worker_name = os.environ.get("PHASE6_WORKER_NAME", "")
            worker_credential = os.environ.get("PHASE6_WORKER_CREDENTIAL", "")
            if process_role == "worker":
                if not worker_name:
                    reasons.append("worker name")
                if (
                    len(worker_credential) < 32
                    or any(
                        marker in worker_credential.lower()
                        for marker in DISPOSABLE_MARKERS
                    )
                ):
                    reasons.append("worker credential")
                if worker_credential in {
                    *session_keys,
                    provider_secret,
                    values["jwt_secret"],
                    values["webhook_secret"],
                }:
                    reasons.append("separate worker credential")
            elif worker_credential:
                reasons.append("worker credential exposed to non-worker process")
            if reasons:
                raise Phase2ConfigurationError(environment.capitalize() + " startup refused: " + ", ".join(reasons))
        elif mode != "development":
            raise Phase2ConfigurationError("PHASE2_LOCAL_AUTH must be development; Phase 2 local auth is not production identity")
        missing = [name for name, value in values.items() if not value or value.startswith("replace-")]
        if missing:
            raise Phase2ConfigurationError("Missing local Phase 2 settings: " + ", ".join(missing))
        for name in ("admin_url", "migrator_url", "runtime_url"):
            values[name] = use_psycopg(values[name])
        return cls(local_auth=mode, **values)
