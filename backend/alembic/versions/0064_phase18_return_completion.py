"""Phase 18 household labels and one verified required-return completion."""

from pathlib import Path

from alembic import op

revision = "0064_phase18_return_completion"
down_revision = "0063_phase18_required_return"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(Path(__file__).resolve().parents[1].joinpath("sql", "0064_phase18_return_completion.sql").read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 18 return-completion migration is forward-only")
