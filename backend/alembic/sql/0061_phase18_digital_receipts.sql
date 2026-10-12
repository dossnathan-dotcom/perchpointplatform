-- Phase 18 digital receipts and housing-assistance schedules.
-- Local synthetic evidence only. Physical intake stays closed. No money moves.

DO $$
DECLARE constraint_name text;
BEGIN
  SELECT conname INTO constraint_name FROM pg_constraint
  WHERE conrelid = 'payment_orders'::regclass AND contype = 'c'
    AND pg_get_constraintdef(oid) LIKE '%''card''%';
  IF constraint_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE payment_orders DROP CONSTRAINT %I', constraint_name);
  END IF;
  SELECT conname INTO constraint_name FROM pg_constraint
  WHERE conrelid = 'payment_instruments'::regclass AND contype = 'c'
    AND pg_get_constraintdef(oid) LIKE '%''card''%';
  IF constraint_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE payment_instruments DROP CONSTRAINT %I', constraint_name);
  END IF;
END $$;

ALTER TABLE payment_orders ADD CONSTRAINT payment_orders_method_check
  CHECK (method IN ('card', 'ach', 'cash_app'));
ALTER TABLE payment_instruments ADD CONSTRAINT payment_instruments_method_check
  CHECK (method IN ('card', 'ach', 'cash_app'));

CREATE TABLE assistance_determinations (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  tenancy_code text NOT NULL,
  account_reference text,
  program_kind text NOT NULL CHECK (program_kind = 'hcv'),
  agency_name text NOT NULL,
  service_period text NOT NULL CHECK (service_period ~ '^[0-9]{4}-[0-9]{2}$'),
  version integer NOT NULL CHECK (version > 0),
  rent_to_owner_minor integer NOT NULL CHECK (rent_to_owner_minor > 0),
  resident_minor integer NOT NULL CHECK (resident_minor >= 0),
  agency_minor integer NOT NULL CHECK (agency_minor >= 0),
  utility_allowance_minor integer NOT NULL DEFAULT 0 CHECK (utility_allowance_minor >= 0),
  utility_reimbursement_minor integer NOT NULL DEFAULT 0 CHECK (utility_reimbursement_minor >= 0),
  agency_received_minor integer NOT NULL DEFAULT 0 CHECK (agency_received_minor >= 0),
  obligation_reference text,
  state text NOT NULL CHECK (state IN ('approved', 'superseded')),
  supersedes uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, tenancy_code, service_period, version),
  CHECK (rent_to_owner_minor = resident_minor + agency_minor),
  CHECK (agency_received_minor <= agency_minor)
);

CREATE UNIQUE INDEX assistance_determinations_one_approved
  ON assistance_determinations (organization_id, tenancy_code, service_period)
  WHERE state = 'approved';

CREATE TABLE digital_receipts (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  source text NOT NULL CHECK (source IN ('stripe', 'business_bank', 'agency_remittance', 'zelle_evidence', 'historical_import')),
  economic_key text NOT NULL,
  method text NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor > 0),
  currency_code text NOT NULL CHECK (currency_code = 'USD'),
  tenancy_code text,
  service_period text,
  purpose text NOT NULL CHECK (purpose IN ('rent_assistance', 'utility_reimbursement', 'historical')),
  effect_class text NOT NULL CHECK (effect_class IN ('agency_cash', 'no_resident_settlement', 'resident_settlement', 'historical')),
  state text NOT NULL CHECK (state IN ('pending', 'confirmed', 'staged', 'reversed')),
  application_state text NOT NULL CHECK (application_state IN ('unmatched', 'queued', 'review', 'applied', 'excluded', 'batch')),
  journal_reference text,
  batch_reference text,
  environment text NOT NULL CHECK (environment = 'local_fake'),
  money_moved boolean NOT NULL CHECK (money_moved = false),
  real_values_activated boolean NOT NULL CHECK (real_values_activated = false),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, source, economic_key),
  CHECK (
    source = 'historical_import'
    OR method NOT IN ('cash', 'check', 'money_order', 'money-order')
  )
);

CREATE TABLE remittance_batches (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  economic_key text NOT NULL,
  gross_minor integer NOT NULL CHECK (gross_minor >= 0),
  recoupment_minor integer NOT NULL CHECK (recoupment_minor >= 0),
  adjustment_minor integer NOT NULL,
  net_minor integer NOT NULL CHECK (net_minor >= 0),
  receipt_reference text,
  state text NOT NULL CHECK (state IN ('preview', 'applied', 'partial')),
  unexplained_minor integer NOT NULL CHECK (unexplained_minor >= 0),
  environment text NOT NULL CHECK (environment = 'local_fake'),
  money_moved boolean NOT NULL CHECK (money_moved = false),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, economic_key),
  CHECK (gross_minor - recoupment_minor + adjustment_minor = net_minor)
);

CREATE TABLE remittance_rows (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  batch_id uuid NOT NULL,
  tenancy_code text,
  service_period text,
  gross_minor integer NOT NULL CHECK (gross_minor > 0),
  state text NOT NULL CHECK (state IN ('open', 'applied', 'excluded')),
  journal_reference text,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, batch_id) REFERENCES remittance_batches (organization_id, id)
);

CREATE TABLE transfer_reports (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  tenancy_code text NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor > 0),
  reference_text text NOT NULL,
  explanation text NOT NULL,
  state text NOT NULL CHECK (state IN ('reported', 'matched', 'rejected')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE assistance_exceptions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  tenancy_code text NOT NULL,
  service_period text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('resident_overpayment', 'agency_delay', 'review')),
  amount_minor integer NOT NULL CHECK (amount_minor >= 0),
  detail text NOT NULL,
  state text NOT NULL CHECK (state IN ('open', 'resolved')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

ALTER TABLE assistance_determinations ENABLE ROW LEVEL SECURITY;
ALTER TABLE assistance_determinations FORCE ROW LEVEL SECURITY;
ALTER TABLE digital_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE digital_receipts FORCE ROW LEVEL SECURITY;
ALTER TABLE remittance_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE remittance_batches FORCE ROW LEVEL SECURITY;
ALTER TABLE remittance_rows ENABLE ROW LEVEL SECURITY;
ALTER TABLE remittance_rows FORCE ROW LEVEL SECURITY;
ALTER TABLE transfer_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE transfer_reports FORCE ROW LEVEL SECURITY;
ALTER TABLE assistance_exceptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE assistance_exceptions FORCE ROW LEVEL SECURITY;

CREATE POLICY assistance_determinations_scope ON assistance_determinations
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.read') OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.charge'));

CREATE POLICY digital_receipts_scope ON digital_receipts
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.read') OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.charge'));

CREATE POLICY remittance_batches_scope ON remittance_batches
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.read') OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.charge'));

CREATE POLICY remittance_rows_scope ON remittance_rows
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.read') OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.charge'));

CREATE POLICY transfer_reports_scope ON transfer_reports
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.read') OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.pay') OR perchpoint.has_capability('payment.charge')
  ));

CREATE POLICY assistance_exceptions_scope ON assistance_exceptions
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.read') OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.charge'));

CREATE POLICY resident_accounts_assistance_read ON resident_accounts
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('payment.charge')
    AND EXISTS (
      SELECT 1 FROM assistance_determinations determination
      WHERE determination.organization_id = resident_accounts.organization_id
        AND determination.account_reference = resident_accounts.public_reference
    )
  );

CREATE POLICY journal_transactions_assistance_read ON journal_transactions
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND kind = 'subsidy'
    AND tenancy_code IS NOT NULL
    AND perchpoint.has_capability('payment.charge')
  );

CREATE POLICY journal_transactions_assistance_insert ON journal_transactions
  FOR INSERT
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND money_moved = false
    AND kind = 'subsidy'
    AND tenancy_code IS NOT NULL
    AND perchpoint.has_capability('payment.charge')
  );

CREATE POLICY journal_lines_assistance_insert ON journal_lines
  FOR INSERT
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('payment.charge')
    AND EXISTS (
      SELECT 1 FROM journal_transactions posted
      WHERE posted.id = transaction_id
        AND posted.organization_id = journal_lines.organization_id
        AND posted.money_moved = false
        AND posted.kind = 'subsidy'
    )
  );

GRANT SELECT, INSERT, UPDATE ON assistance_determinations, digital_receipts, remittance_batches,
  remittance_rows, transfer_reports, assistance_exceptions
  TO perchpoint_runtime, perchpoint_definer;

CREATE FUNCTION perchpoint.assistance_apply_scopes()
RETURNS TABLE (organization_id uuid, principal_id uuid)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  target uuid;
BEGIN
  FOR target IN
    SELECT DISTINCT receipt.organization_id
    FROM digital_receipts receipt
    WHERE receipt.application_state = 'queued'
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
