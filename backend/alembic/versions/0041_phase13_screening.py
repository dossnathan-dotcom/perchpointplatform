"""Phase 13 screening, review, decision, and dispute records. Forward-only."""
from pathlib import Path

from alembic import op

revision = "0041_phase13_screening"
down_revision = "0040_phase12_application"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0041_phase13_screening.sql"


def upgrade() -> None:
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 13 screening decisions are forward-only")
