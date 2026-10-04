"""Add vendor worker proposal, approval, invitation, and activation workflow."""
from pathlib import Path

from alembic import op

revision = "0026_phase6_vendor_workers"
down_revision = "0025_phase6_maintenance_history"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0026_phase6_vendor_workers.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP FUNCTION IF EXISTS perchpoint.activate_vendor_worker(uuid, text);
        DROP TABLE IF EXISTS vendor_worker_proposals;
        """
    )
