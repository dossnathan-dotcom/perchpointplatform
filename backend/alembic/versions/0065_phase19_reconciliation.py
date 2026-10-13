"""Phase 19 bank and payout reconciliation observations."""

from pathlib import Path

from alembic import op

revision = "0065_phase19_reconciliation"
down_revision = "0064_phase18_return_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(Path(__file__).resolve().parents[1].joinpath("sql", "0065_phase19_reconciliation.sql").read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 19 reconciliation migration is forward-only")
