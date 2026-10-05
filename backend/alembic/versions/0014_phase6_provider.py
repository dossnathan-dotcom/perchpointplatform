"""Move TOTP seeds out of PerchPoint and add access-governance tables."""
from pathlib import Path

from alembic import op

revision = "0014_phase6_provider"
down_revision = "0013_phase6_bootstrap"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0014_phase6_provider.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP FUNCTION IF EXISTS perchpoint.list_memberships(uuid);
        DROP FUNCTION IF EXISTS perchpoint.note_auth_attempt(text);
        DROP FUNCTION IF EXISTS perchpoint.account_id_for_email(text);
        DROP FUNCTION IF EXISTS perchpoint.record_provider_session(uuid, text, uuid, text, text, text, text, timestamp with time zone, timestamp with time zone, integer, text, text);
        DROP TABLE IF EXISTS auth_attempts, access_review_items, access_review_campaigns, privileged_recoveries,
          service_credentials, membership_scope_assignments, authorization_scopes, role_bundle_capabilities, role_bundles, capabilities;
        """
    )
