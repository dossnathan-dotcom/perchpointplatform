"""Add a narrow active-membership guard for authorization commands."""
from pathlib import Path

from alembic import op

revision = "0019_phase6_member_guard"
down_revision = "0018_phase6_auth_directory"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0019_phase6_membership_guard.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute("DROP FUNCTION IF EXISTS perchpoint.active_org_member(uuid)")
