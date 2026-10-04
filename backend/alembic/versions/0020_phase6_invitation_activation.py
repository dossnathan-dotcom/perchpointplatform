"""Activate accepted invitations as provider-backed PerchPoint identities."""
from pathlib import Path

from alembic import op

revision = "0020_phase6_invite_activate"
down_revision = "0019_phase6_member_guard"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0020_phase6_invitation_activation.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP FUNCTION IF EXISTS perchpoint.activate_invitation(text, text, text, text);
        ALTER TABLE identity_accounts DROP COLUMN IF EXISTS mfa_required;
        """
    )
