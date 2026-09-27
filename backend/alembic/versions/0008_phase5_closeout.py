"""Phase 5 document processing, access, export, search, import, and replay."""
from pathlib import Path

from alembic import op

revision = "0008_phase5_closeout"
down_revision = "0007_phase5_canonical"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0008_phase5_closeout.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP FUNCTION IF EXISTS perchpoint.claim_document_job(text);
        DROP TABLE IF EXISTS import_effects, replay_runs, document_exports, document_access,
          document_artifacts, document_jobs CASCADE;
        ALTER TABLE quality_findings DROP COLUMN IF EXISTS source_evidence;
        ALTER TABLE quality_findings DROP COLUMN IF EXISTS assigned_to;
        ALTER TABLE import_batches DROP COLUMN IF EXISTS approved_by;
        ALTER TABLE import_batches DROP COLUMN IF EXISTS mapping_version;
        ALTER TABLE import_batches DROP CONSTRAINT IF EXISTS import_batches_status_check;
        ALTER TABLE import_batches ADD CONSTRAINT import_batches_status_check
          CHECK (status IN ('staged', 'approved', 'applied', 'rejected'));
        DROP POLICY IF EXISTS saved_search_read ON saved_searches;
        DROP POLICY IF EXISTS saved_search_write ON saved_searches;
        CREATE POLICY tenant_all ON saved_searches
          USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(organization_id))
          WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(organization_id));
        ALTER TABLE saved_searches DROP CONSTRAINT IF EXISTS saved_searches_name_check;
        ALTER TABLE saved_searches DROP CONSTRAINT IF EXISTS saved_searches_visibility_check;
        ALTER TABLE saved_searches DROP COLUMN IF EXISTS visibility;
        ALTER TABLE saved_searches DROP COLUMN IF EXISTS name;
        ALTER TABLE documents DROP COLUMN IF EXISTS published;
        ALTER TABLE documents DROP CONSTRAINT documents_lifecycle_check;
        ALTER TABLE documents ADD CONSTRAINT documents_lifecycle_check
          CHECK (lifecycle IN ('staged', 'scanning', 'available', 'quarantined', 'held'));
        """
    )
