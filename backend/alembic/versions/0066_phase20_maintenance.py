"""Phase 20 maintenance intake, triage, and field handoffs."""

from pathlib import Path

from alembic import op

revision = "0066_phase20_maintenance"
down_revision = "0065_phase19_reconciliation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(Path(__file__).resolve().parents[1].joinpath("sql", "0066_phase20_maintenance.sql").read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 20 maintenance migration is forward-only")
