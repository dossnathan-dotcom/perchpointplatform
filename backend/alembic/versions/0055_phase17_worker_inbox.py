"""Store and apply provider events as the restricted runtime role.

The worker lists organizations that have a received event, uses one
service principal per organization, and posts through row security.
It does not open a superuser session for the inbox.
"""
from alembic import op

revision = "0055_phase17_worker_inbox"
down_revision = "0054_phase17_worker_claim"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION perchpoint.store_provider_event(
          org uuid, event_id text, effect text, kind text, body jsonb
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
        DECLARE
          inserted uuid;
        BEGIN
          IF org IS NULL OR event_id IS NULL OR length(btrim(event_id)) = 0 THEN
            RETURN false;
          END IF;
          INSERT INTO provider_events (
            organization_id, id, provider_event_id, effect_key, state, payload_kind, payload
          ) VALUES (
            org, gen_random_uuid(), btrim(event_id),
            coalesce(nullif(btrim(effect), ''), btrim(event_id)),
            'received', left(coalesce(kind, 'unknown'), 80), coalesce(body, '{}'::jsonb)
          )
          ON CONFLICT (organization_id, provider_event_id) DO NOTHING
          RETURNING id INTO inserted;
          RETURN inserted IS NOT NULL;
        END $$;
        ALTER FUNCTION perchpoint.store_provider_event(uuid, text, text, text, jsonb) OWNER TO perchpoint_definer;
        REVOKE ALL ON FUNCTION perchpoint.store_provider_event(uuid, text, text, text, jsonb) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION perchpoint.store_provider_event(uuid, text, text, text, jsonb) TO perchpoint_runtime;

        CREATE FUNCTION perchpoint.payment_inbox_scopes()
        RETURNS TABLE (organization_id uuid, principal_id uuid)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
        DECLARE
          target uuid;
        BEGIN
          UPDATE provider_events event
          SET state = 'quarantined'
          WHERE event.state = 'received'
            AND NOT EXISTS (
              SELECT 1 FROM organizations organization WHERE organization.id = event.organization_id
            );
          FOR target IN
            SELECT DISTINCT event.organization_id
            FROM provider_events event
            WHERE event.state = 'received'
          LOOP
            INSERT INTO service_principals (organization_id, id, name, status, capabilities)
            SELECT target, gen_random_uuid(), 'phase17-payment-worker', 'active',
              ARRAY['payment.pay', 'payment.charge', 'payment.configure', 'payment.refund']::text[]
            WHERE NOT EXISTS (
              SELECT 1 FROM service_principals principal
              WHERE principal.organization_id = target
                AND principal.name = 'phase17-payment-worker'
                AND principal.status = 'active'
                AND principal.revoked_at IS NULL
            );
            organization_id := target;
            principal_id := (
              SELECT principal.id FROM service_principals principal
              WHERE principal.organization_id = target
                AND principal.name = 'phase17-payment-worker'
                AND principal.status = 'active'
                AND principal.revoked_at IS NULL
              ORDER BY principal.id
              LIMIT 1
            );
            RETURN NEXT;
          END LOOP;
        END $$;
        ALTER FUNCTION perchpoint.payment_inbox_scopes() OWNER TO perchpoint_definer;
        REVOKE ALL ON FUNCTION perchpoint.payment_inbox_scopes() FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION perchpoint.payment_inbox_scopes() TO perchpoint_runtime;

        CREATE POLICY resident_accounts_reconcile_read ON resident_accounts
          FOR SELECT
          USING (
            organization_id = perchpoint.current_org()
            AND perchpoint.has_capability('payment.configure')
            AND EXISTS (
              SELECT 1 FROM payment_obligations obligation
              WHERE obligation.organization_id = resident_accounts.organization_id
                AND obligation.account_reference = resident_accounts.public_reference
            )
          );
        CREATE POLICY resident_accounts_reconcile_update ON resident_accounts
          FOR UPDATE
          USING (
            organization_id = perchpoint.current_org()
            AND perchpoint.has_capability('payment.configure')
            AND EXISTS (
              SELECT 1 FROM payment_obligations obligation
              WHERE obligation.organization_id = resident_accounts.organization_id
                AND obligation.account_reference = resident_accounts.public_reference
            )
          )
          WITH CHECK (
            organization_id = perchpoint.current_org()
            AND perchpoint.has_capability('payment.configure')
          );
        CREATE POLICY accounting_periods_reconcile_read ON accounting_periods
          FOR SELECT
          USING (
            organization_id = perchpoint.current_org()
            AND perchpoint.has_capability('payment.configure')
          );
        CREATE POLICY accounting_periods_reconcile_insert ON accounting_periods
          FOR INSERT
          WITH CHECK (
            organization_id = perchpoint.current_org()
            AND perchpoint.has_capability('payment.configure')
          );
        CREATE POLICY journal_transactions_reconcile_read ON journal_transactions
          FOR SELECT
          USING (
            organization_id = perchpoint.current_org()
            AND perchpoint.has_capability('payment.configure')
            AND EXISTS (
              SELECT 1 FROM payment_obligations obligation
              JOIN resident_accounts account
                ON account.organization_id = obligation.organization_id
                AND account.public_reference = obligation.account_reference
              WHERE obligation.organization_id = journal_transactions.organization_id
                AND account.id = journal_transactions.account_id
            )
          );
        CREATE POLICY journal_lines_reconcile_read ON journal_lines
          FOR SELECT
          USING (
            organization_id = perchpoint.current_org()
            AND perchpoint.has_capability('payment.configure')
            AND EXISTS (
              SELECT 1 FROM journal_transactions posted
              WHERE posted.id = journal_lines.transaction_id
                AND posted.organization_id = journal_lines.organization_id
            )
          );
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 worker inbox is forward-only")
