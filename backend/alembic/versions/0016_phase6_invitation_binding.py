"""Bind invitation acceptance to the intended email and current inviter authority."""
from pathlib import Path

from alembic import op

revision = "0016_phase6_invitation_binding"
down_revision = "0015_phase6_governance"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0016_phase6_invitation_binding.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP FUNCTION IF EXISTS perchpoint.accept_invitation(text, text);
        """
    )
