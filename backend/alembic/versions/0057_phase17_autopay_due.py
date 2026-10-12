"""Skip autopay enrollments that already finished the current period.

The worker lists due enrollments on every scan. A finished occurrence does
not need another claim. Scheduled and not-yet-recorded periods stay eligible.
"""
from alembic import op

revision = "0057_phase17_autopay_due"
down_revision = "0056_phase17_worker_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION perchpoint.due_autopay_claims(day_number integer, period_code text)
        RETURNS TABLE (organization_id uuid, tenancy_code text, payer_account_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
          SELECT enrollment.organization_id, enrollment.tenancy_code, enrollment.payer_account_id
          FROM autopay_enrollments enrollment
          WHERE enrollment.state = 'active'
            AND enrollment.day_of_month = day_number
            AND length(btrim(coalesce(period_code, ''))) = 7
            AND NOT EXISTS (
              SELECT 1 FROM autopay_occurrences occurrence
              WHERE occurrence.enrollment_id = enrollment.id
                AND occurrence.period_code = btrim(period_code)
                AND occurrence.state IN ('collected', 'skipped', 'action_required')
            )
        $$;
        ALTER FUNCTION perchpoint.due_autopay_claims(integer, text) OWNER TO perchpoint_definer;
        REVOKE ALL ON FUNCTION perchpoint.due_autopay_claims(integer, text) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION perchpoint.due_autopay_claims(integer, text) TO perchpoint_runtime;
        DROP FUNCTION perchpoint.due_autopay_claims(integer);
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 autopay due claims are forward-only")
