"""Resolve provider subjects and synchronize provider-verified email changes."""
from pathlib import Path

from alembic import op

revision = "0021_phase6_contact_identity"
down_revision = "0020_phase6_invite_activate"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0021_phase6_contact_identity.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP FUNCTION IF EXISTS perchpoint.sync_provider_email(text, text);
        DROP FUNCTION IF EXISTS perchpoint.account_id_for_subject(text);
        """
    )
