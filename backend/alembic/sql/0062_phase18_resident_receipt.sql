-- Let a confirmed resident transfer share the Phase 17 collection reservation,
-- and let the payment worker post that settlement without reading every resident journal.

ALTER TABLE digital_receipts DROP CONSTRAINT digital_receipts_purpose_check;
ALTER TABLE digital_receipts ADD CONSTRAINT digital_receipts_purpose_check
  CHECK (purpose IN ('rent_assistance', 'utility_reimbursement', 'historical', 'resident_rent'));

ALTER TABLE digital_receipts DROP CONSTRAINT digital_receipts_application_state_check;
ALTER TABLE digital_receipts ADD CONSTRAINT digital_receipts_application_state_check
  CHECK (application_state IN ('unmatched', 'queued', 'claimed', 'review', 'applied', 'excluded', 'batch'));

ALTER TABLE digital_receipts ADD COLUMN claim_expires_at timestamptz;

CREATE OR REPLACE FUNCTION perchpoint.assistance_apply_scopes()
RETURNS TABLE (organization_id uuid, principal_id uuid)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  target uuid;
BEGIN
  FOR target IN
    SELECT DISTINCT receipt.organization_id
    FROM digital_receipts receipt
    WHERE receipt.application_state = 'queued'
       OR (
         receipt.application_state = 'claimed'
         AND receipt.claim_expires_at IS NOT NULL
         AND receipt.claim_expires_at < now()
       )
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

ALTER FUNCTION perchpoint.assistance_apply_scopes() OWNER TO perchpoint_definer;
REVOKE ALL ON FUNCTION perchpoint.assistance_apply_scopes() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.assistance_apply_scopes() TO perchpoint_runtime;

CREATE POLICY journal_transactions_resident_receipt_read ON journal_transactions
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND kind = 'settlement'
    AND tenancy_code IS NOT NULL
    AND perchpoint.has_capability('payment.pay')
    AND perchpoint.has_capability('payment.charge')
  );
