"""Create the isolated local database and roles. Does not open a cloud account."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from .db import engine_for
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
        connection.execute(text("GRANT USAGE, CREATE ON SCHEMA perchpoint TO perchpoint_definer"))
        connection.execute(text("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA perchpoint TO perchpoint_definer"))
        for name in (
            "actor_in_org(uuid)",
            "published_listings()",
            "login_material(text)",
            "current_membership(uuid)",
            "submit_public_inquiry(uuid, text, text, text, text, text, text, uuid)",
            "claim_outbox(text)",
            "finish_outbox(uuid, boolean)",
            "public_search(text)",
            "claim_document_job(text)",
            "search_rows(text, text, text, text)",
            "search_facets(text, text, text, text)",
            "reject_held_mutation()",
            "resolve_session(text)",
            "record_session(uuid, text, uuid, text, text, text, text, timestamp with time zone, timestamp with time zone)",
            "claim_invitation(text)",
            "accept_invitation(text, text)",
            "resolve_session(text)",
            "record_provider_session(uuid, text, uuid, text, text, text, text, timestamp with time zone, timestamp with time zone, integer, text, text)",
            "account_id_for_email(text)",
            "note_auth_attempt(text)",
            "list_memberships(uuid)",
            "revoke_account_sessions(uuid, text)",
            "recovery_code_material(uuid)",
            "consume_recovery_code(uuid, uuid)",
            "current_role()",
            "can_read_household(uuid)",
            "access_directory()",
            "active_org_member(uuid)",
            "activate_invitation(text, text, text, text)",
            "account_id_for_subject(text)",
            "sync_provider_email(text, text)",
            "activate_vendor_worker(uuid, text)",
            "set_identity_lifecycle(uuid, uuid, uuid, text, text)",
            "recovery_provider_subject(uuid, uuid, uuid)",
            "resolve_authority_context(uuid, uuid, uuid)",
            "role_for_account(uuid)",
            "has_capability(text)",
            "scope_allows(text, uuid)",
            "authorized_for(text, text, uuid)",
            "property_authority_fact(uuid)",
            "worker_assignment_allows(uuid, uuid)",
            "search_resource_allowed(text, uuid, text)",
            "rebuild_search_projection(uuid)",
            "authenticate_service_credential(text, text, text)",
            "schedule_access_review(uuid, text)",
            "quarterly_access_reviews()",
            "note_material_access_change()",
            "validate_invitation_activation()",
            "record_privileged_recovery_event()",
            "validate_delegation_bounds()",
            "published_page(text)",
            "published_navigation()",
            "accept_public_submission(text, jsonb, text, text, text, text, text, text, text, uuid)",
            "guard_content_publication()",
            "published_redirect(text)",
            "record_public_analytics(text, text, jsonb)",
            "published_listing_snapshot(text)",
            "search_discovery(jsonb)",
            "published_discovery_listing(text)",
            "discovery_sitemap()",
            "record_discovery_event(text, text, text, text, text, text, text, boolean)",
        ):
            connection.execute(text(f"ALTER FUNCTION perchpoint.{name} OWNER TO perchpoint_definer"))
        connection.execute(
            text(
                "REVOKE INSERT, UPDATE, DELETE ON privileged_recovery_events "
                "FROM perchpoint_runtime"
            )
        )
        connection.execute(
            text(
                "REVOKE UPDATE, DELETE ON privileged_recovery_events "
                "FROM perchpoint_definer"
            )
        )
        connection.execute(
            text(
                "GRANT INSERT ON privileged_recovery_events "
                "TO perchpoint_definer"
            )
        )
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
