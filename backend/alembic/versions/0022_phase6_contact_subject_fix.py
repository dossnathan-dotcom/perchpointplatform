"""Disambiguate provider-subject parameters in identity lookup functions."""
from pathlib import Path

from alembic import op

revision = "0022_phase6_contact_subject"
down_revision = "0021_phase6_contact_identity"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0022_phase6_contact_subject_fix.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    pass
