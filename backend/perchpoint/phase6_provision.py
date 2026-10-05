"""Provision synthetic local Auth users after the disposable provider is ready."""
from __future__ import annotations

import time
import urllib.request
from uuid import uuid4

from sqlalchemy import text

from .db import engine_for
from .phase6_provider import ProviderError, auth_url, create_user, find_user_by_email
from .settings import Settings


def main() -> None:
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(auth_url() + "/health", timeout=3) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(2)
    else:
        raise SystemExit("local Auth provider did not become ready")
    settings = Settings.load()
    subjects: dict[str, str] = {}
    for email in (
        "ann.synthetic@example.com",
        "nathan.synthetic@example.com",
        "faruk.synthetic@example.com",
        "accounting.synthetic@example.com",
        "maintenance.synthetic@example.com",
        "resident.synthetic@example.com",
        "vendor.admin.synthetic@example.com",
        "technician.synthetic@example.com",
        "cleaner.synthetic@example.com",
        "applicant.synthetic@example.com",
        "guarantor.synthetic@example.com",
        "former.synthetic@example.com",
        "suspended.synthetic@example.com",
        "reset.synthetic@example.com",
    ):
        while True:
            try:
                subjects[email] = create_user(email, settings.dev_password)
                break
            except ProviderError as exc:
                if exc.code == "authentication_failed":
                    subject = find_user_by_email(email)
                    if subject is None:
                        raise
                    subjects[email] = subject
                    break
                if exc.code != "provider_unavailable" or time.time() >= deadline:
                    raise
                time.sleep(1)
    admin = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with admin.begin() as connection:
        account_id = connection.execute(
            text("SELECT id FROM accounts WHERE lower(email) = :email"),
            {"email": "suspended.synthetic@example.com"},
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO identity_accounts (
                  id, account_id, provider_subject, status, email_verified
                ) VALUES (:id, :account, :subject, 'suspended', true)
                ON CONFLICT (account_id) DO UPDATE
                SET provider_subject = EXCLUDED.provider_subject, status = 'suspended'
                """
            ),
            {
                "id": uuid4(),
                "account": account_id,
                "subject": subjects["suspended.synthetic@example.com"],
            },
        )
    admin.dispose()
    print("phase6 synthetic Auth users ready")


if __name__ == "__main__":
    main()
