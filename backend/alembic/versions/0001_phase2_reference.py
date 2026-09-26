"""Phase 2 reference schema. No earlier PostgreSQL revision exists in this repository."""
from pathlib import Path

from alembic import op

revision = "0001_phase2_reference"
down_revision = None
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0001_phase2_reference.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP SCHEMA IF EXISTS perchpoint CASCADE;
        DROP TABLE IF EXISTS idempotency_keys, inbox, outbox, audit_events, activity, inquiries,
          listings, space_states, portal_access, households, memberships, accounts,
          management_relationships, ownership_relationships, spaces, buildings, properties,
          legal_entities, organizations CASCADE;
        """
    )
