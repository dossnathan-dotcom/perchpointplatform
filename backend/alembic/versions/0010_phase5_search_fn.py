"""Organization-scoped search functions that can use the trigram and text indexes."""
from pathlib import Path

from alembic import op

revision = "0010_phase5_search_fn"
down_revision = "0009_phase5_job_source"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0010_phase5_search_fn.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP FUNCTION IF EXISTS perchpoint.search_rows(text, text, text, text);
        DROP FUNCTION IF EXISTS perchpoint.search_facets(text, text, text, text);
        """
    )
