"""Remember the scanned filename and index audit actions."""
from pathlib import Path

from alembic import op

revision = "0009_phase5_job_source"
down_revision = "0008_phase5_closeout"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0009_phase5_job_source.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS audit_events_org_action;
        ALTER TABLE document_jobs DROP COLUMN IF EXISTS media_type;
        ALTER TABLE document_jobs DROP COLUMN IF EXISTS source_name;
        """
    )
