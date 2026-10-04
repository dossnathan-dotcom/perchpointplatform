"""Local Supabase Auth client. PerchPoint does not verify passwords or TOTP seeds."""
from __future__ import annotations

import json
import os
import secrets
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

import jwt


class ProviderError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ProviderSession:
    subject: str
    email: str
    assurance: str
    access_token: str
    refresh_token: str
    provider_session_id: str | None


def auth_url() -> str:
    return os.environ.get("PHASE6_AUTH_URL", "http://127.0.0.1:9999").rstrip("/")


def _secret() -> str:
    return os.environ.get("PHASE6_PROVIDER_JWT_SECRET", "local-only-not-production-gotrue-jwt-secret")


def issuer() -> str:
    return os.environ.get("PHASE6_PROVIDER_ISSUER", "perchpoint-local-auth")


def _request(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    request = urllib.request.Request(auth_url() + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read().decode()
    except urllib.error.HTTPError as exc:
        if exc.code in {400, 401, 403, 422}:
            raise ProviderError("authentication_failed") from exc
        if exc.code == 429:
            raise ProviderError("rate_limited") from exc
        raise ProviderError("provider_unavailable") from exc
    except urllib.error.URLError as exc:
        raise ProviderError("provider_unavailable") from exc
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ProviderError("provider_unavailable")
    return parsed


def admin_token() -> str:
    now = int(time.time())
    token = jwt.encode(
        {"role": "service_role", "iss": issuer(), "aud": "authenticated", "iat": now, "exp": now + 3600},
        _secret(),
        algorithm="HS256",
    )
    return token if isinstance(token, str) else token.decode()


def verify_access_token(token: str) -> dict:
    try:
        claims = jwt.decode(token, _secret(), algorithms=["HS256"], audience="authenticated", issuer=issuer())
    except jwt.PyJWTError as exc:
        raise ProviderError("authentication_failed") from exc
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ProviderError("authentication_failed")
    assurance = claims.get("aal") if claims.get("aal") in {"aal1", "aal2"} else "aal1"
    return {"subject": subject, "assurance": assurance, "session_id": claims.get("session_id"), "email": claims.get("email")}


def _session_from(payload: dict) -> ProviderSession:
    access = payload.get("access_token")
    refresh = payload.get("refresh_token")
    if not isinstance(access, str) or not isinstance(refresh, str):
        raise ProviderError("authentication_failed")
    claims = verify_access_token(access)
    user_raw = payload.get("user")
    user = user_raw if isinstance(user_raw, dict) else {}
    email_raw = user.get("email")
    claim_email = claims.get("email")
    email = email_raw if isinstance(email_raw, str) else claim_email if isinstance(claim_email, str) else ""
    session_id = claims.get("session_id")
    return ProviderSession(
        subject=str(claims["subject"]),
        email=email,
        assurance=str(claims["assurance"]),
        access_token=access,
        refresh_token=refresh,
        provider_session_id=session_id if isinstance(session_id, str) else None,
    )


def password_grant(email: str, password: str) -> ProviderSession:
    return _session_from(_request("POST", "/token?grant_type=password", {"email": email, "password": password}))


def refresh_grant(refresh_token: str) -> ProviderSession:
    return _session_from(_request("POST", "/token?grant_type=refresh_token", {"refresh_token": refresh_token}))


def create_user(email: str, password: str) -> str:
    payload = _request(
        "POST",
        "/admin/users",
        {"email": email, "password": password, "email_confirm": True, "role": "authenticated"},
        admin_token(),
    )
    user_id = payload.get("id")
    if not isinstance(user_id, str):
        raise ProviderError("provider_unavailable")
    return user_id


def enroll_factor(access_token: str) -> dict:
    payload = _request(
        "POST",
        "/factors",
        {"factor_type": "totp", "friendly_name": "PerchPoint-" + secrets.token_hex(3), "issuer": "PerchPoint"},
        access_token,
    )
    factor_id = payload.get("id")
    totp_raw = payload.get("totp")
    totp = totp_raw if isinstance(totp_raw, dict) else {}
    secret = totp.get("secret")
    uri = totp.get("uri")
    if not isinstance(factor_id, str) or not isinstance(secret, str):
        raise ProviderError("provider_unavailable")
    return {"factor_id": factor_id, "secret": secret, "otpauth": uri if isinstance(uri, str) else ""}


def confirm_factor(access_token: str, factor_id: str, code: str) -> ProviderSession:
    challenge = _request("POST", f"/factors/{factor_id}/challenge", {}, access_token)
    challenge_id = challenge.get("id")
    if not isinstance(challenge_id, str):
        raise ProviderError("mfa_invalid")
    verified = _request("POST", f"/factors/{factor_id}/verify", {"challenge_id": challenge_id, "code": code}, access_token)
    return _session_from(verified)


def request_recovery(email: str) -> None:
    try:
        _request("POST", "/recover", {"email": email})
    except ProviderError as exc:
        if exc.code != "authentication_failed":
            raise


def recovery_link(email: str) -> str:
    payload = _request("POST", "/admin/generate_link", {"type": "recovery", "email": email}, admin_token())
    link = payload.get("action_link")
    if not isinstance(link, str) or "token=" not in link:
        raise ProviderError("provider_unavailable")
    return link.split("token=", 1)[1].split("&", 1)[0]


def complete_recovery(token: str, password: str) -> str:
    verified = _request("POST", "/verify", {"type": "recovery", "token": token})
    session = _session_from(verified)
    _request("PUT", "/user", {"password": password}, session.access_token)
    return session.email
