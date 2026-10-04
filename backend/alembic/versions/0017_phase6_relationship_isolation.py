"""Enforce household, vendor, and worker assignment relationship isolation."""
from pathlib import Path

from alembic import op

revision = "0017_phase6_rel_isolation"
down_revision = "0016_phase6_invitation_binding"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0017_phase6_relationship_isolation.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP FUNCTION IF EXISTS perchpoint.can_read_household(uuid);
        DROP FUNCTION IF EXISTS perchpoint.current_role();
        DROP TABLE IF EXISTS worker_assignments, vendor_relationships;
        """
    )
