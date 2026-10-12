"""Phase 18 owned required returns stay distinct from discretionary refunds."""

from pathlib import Path

from alembic import op

revision = "0063_phase18_required_return"
down_revision = "0062_phase18_resident_receipt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(Path(__file__).resolve().parents[1].joinpath("sql", "0063_phase18_required_return.sql").read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 18 required-return migration is forward-only")
