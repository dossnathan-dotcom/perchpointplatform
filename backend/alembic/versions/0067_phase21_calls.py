"""Phase 21 call metadata without recording."""

from pathlib import Path

from alembic import op

revision = "0067_phase21_calls"
down_revision = "0066_phase20_maintenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(Path(__file__).resolve().parents[1].joinpath("sql", "0067_phase21_calls.sql").read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 21 call migration is forward-only")
