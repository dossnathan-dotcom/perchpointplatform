"""Expose the current organization directory through a narrow policy function."""
from pathlib import Path

from alembic import op

revision = "0018_phase6_auth_directory"
down_revision = "0017_phase6_rel_isolation"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0018_phase6_authorized_directory.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute("DROP FUNCTION IF EXISTS perchpoint.access_directory()")
