"""Phase 5 canonical records, documents, and search."""
from pathlib import Path

from alembic import op

revision = "0007_phase5_canonical"
down_revision = "0006_activity_index"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0007_phase5_canonical.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP FUNCTION IF EXISTS perchpoint.public_search(text);
        DROP TABLE IF EXISTS
          quality_findings, import_rows, import_batches, saved_searches, search_documents,
          retention_policies, legal_holds, document_versions, documents, property_issues,
          property_facts, parcels, property_addresses, party_relationships, parties, audit_digests
        CASCADE;
        """
    )
