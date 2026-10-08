"""Phase 10 inquiry capture and leasing CRM. Forward-only."""
from pathlib import Path

from alembic import op

revision = "0038_phase10_inquiry"
down_revision = "0037_phase9_discovery"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0038_phase10_inquiry_crm.sql"


def upgrade() -> None:
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 10 inquiry CRM is forward-only")
