"""Reject deletion of document bytes while a legal hold is active."""
from pathlib import Path

from alembic import op

revision = "0011_phase5_hold_guard"
down_revision = "0010_phase5_search_fn"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0011_phase5_hold_guard.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP TRIGGER IF EXISTS documents_hold_guard ON documents;
        DROP TRIGGER IF EXISTS document_versions_hold_guard ON document_versions;
        DROP TRIGGER IF EXISTS document_artifacts_hold_guard ON document_artifacts;
        DROP FUNCTION IF EXISTS perchpoint.reject_held_mutation();
        """
    )
