"""Phase 12 application, household, and document collection. Forward-only."""
from pathlib import Path

from alembic import op

revision = "0040_phase12_application"
down_revision = "0039_phase11_showing"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0040_phase12_application.sql"


def upgrade() -> None:
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 12 application collection is forward-only")
