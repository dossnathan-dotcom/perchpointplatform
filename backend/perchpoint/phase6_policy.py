"""Phase 6 authorization policy. The identity provider does not decide business authority."""
from __future__ import annotations

import hmac
import hashlib
import struct
import time
from dataclasses import dataclass

COMMON_PASSWORDS = {
    "passwordpassword",
    "correcthorsebatterystaple",
    "hawthornhomes1234",
}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    authority: str
    assurance: str
    policy_version: str = "phase6-1"


def password_problem(password: str) -> str | None:
    if len(password) < 15:
        return "password_too_short"
    if len(password) > 64:
        return "password_too_long"
    if password.lower() in COMMON_PASSWORDS:
        return "password_common"
    return None


def approval_authority(amount_minor: int, monthly_rent_minor: int | None, *, capital: bool, emergency: bool) -> str:
    if capital or amount_minor > 120_000 or (monthly_rent_minor is not None and amount_minor > monthly_rent_minor):
        return "owner"
    if emergency and amount_minor <= 120_000:
        return "operations_emergency"
    if amount_minor >= 50_000:
        return "operations"
    return "routine"


def authorize(
    *,
    capability: str,
    role_name: str,
    actor_id: str,
    target_id: str | None = None,
    assurance: str = "aal1",
    reauthenticated_age_seconds: float | None = None,
    self_grant: bool = False,
    self_approval: bool = False,
    delegated: bool = False,
    delegation_active: bool = False,
    suspended: bool = False,
    privileged: bool = False,
) -> Decision:
    if suspended:
        return Decision(False, "suspended", "none", assurance)
    if self_grant or (target_id is not None and actor_id == target_id and capability.startswith("membership.")):
        return Decision(False, "self_grant", "none", assurance)
    if self_approval:
        return Decision(False, "self_approval", "none", assurance)
    if delegated and not delegation_active:
        return Decision(False, "delegation_inactive", "none", assurance)
    if delegated and capability == "delegation.grant":
        return Decision(False, "delegation_non_transitive", "none", assurance)
    if privileged and (assurance != "aal2" or reauthenticated_age_seconds is None or reauthenticated_age_seconds > 300):
        return Decision(False, "step_up_required", role_name, assurance)
    if role_name == "platform_admin" and capability in {"approval.owner", "lease.approve", "expense.approve"}:
        return Decision(False, "technical_role_is_not_business_authority", role_name, assurance)
    if role_name == "owner" and capability in {"platform.secrets", "platform.database"}:
        return Decision(False, "owner_is_not_technical_operator", role_name, assurance)
    if role_name == "leasing" and capability in {"platform.secrets", "audit.delete", "platform.deploy"}:
        return Decision(False, "operations_boundary", role_name, assurance)
    return Decision(True, "allowed", role_name, assurance)


def hotp(secret: bytes, counter: int) -> str:
    digest = hmac.new(secret, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1_000_000:06d}"


def totp(secret: bytes, moment: float | None = None, step: int = 30) -> str:
    return hotp(secret, int((time.time() if moment is None else moment) // step))


def totp_matches(secret: bytes, code: str, moment: float | None = None) -> bool:
    now = time.time() if moment is None else moment
    return any(hmac.compare_digest(totp(secret, now + offset), code) for offset in (-30, 0, 30))
