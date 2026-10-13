-- Phase 19 bank and payout observations. These rows do not post resident or subsidy journals.

CREATE TABLE reconciliation_sources (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  label text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('processor', 'bank')),
  refresh_state text NOT NULL CHECK (refresh_state IN ('current', 'stale')),
  environment text NOT NULL CHECK (environment = 'local_fake'),
  money_moved boolean NOT NULL CHECK (money_moved = false),
  real_values_activated boolean NOT NULL CHECK (real_values_activated = false),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE reconciliation_lines (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  source_reference text NOT NULL,
  external_id text NOT NULL,
  kind text NOT NULL CHECK (kind IN (
    'processor_charge', 'processor_fee', 'processor_refund', 'bank_deposit',
    'internal_transfer', 'unknown', 'assistance_evidence', 'historical_observation', 'residual'
  )),
  amount_minor integer NOT NULL CHECK (amount_minor >= 0),
  matched_minor integer NOT NULL DEFAULT 0 CHECK (matched_minor >= 0 AND matched_minor <= amount_minor),
  currency_code text NOT NULL CHECK (currency_code = 'USD'),
  status text NOT NULL CHECK (status IN ('pending', 'posted')),
  link_reference text,
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  owner_actor uuid,
  environment text NOT NULL CHECK (environment = 'local_fake'),
  money_moved boolean NOT NULL CHECK (money_moved = false),
  real_values_activated boolean NOT NULL CHECK (real_values_activated = false),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, source_reference, external_id)
);

CREATE TABLE reconciliation_matches (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  line_id uuid NOT NULL,
  target_reference text NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor > 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, line_id) REFERENCES reconciliation_lines (organization_id, id)
);

CREATE TABLE reconciliation_snapshots (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  body jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE reconciliation_acknowledgements (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  snapshot_reference text NOT NULL,
  actor_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE reconciliation_closes (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  snapshot_reference text NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  state text NOT NULL CHECK (state IN ('draft', 'issued')),
  preparer_actor uuid NOT NULL,
  reviewer_actor uuid,
  packet jsonb NOT NULL,
  packet_sha text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, snapshot_reference, version),
  CHECK (reviewer_actor IS NULL OR reviewer_actor <> preparer_actor)
);

ALTER TABLE reconciliation_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_sources FORCE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_lines FORCE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_matches FORCE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_snapshots FORCE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_acknowledgements ENABLE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_acknowledgements FORCE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_closes ENABLE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_closes FORCE ROW LEVEL SECURITY;

CREATE POLICY reconciliation_sources_scope ON reconciliation_sources
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.read') OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.charge'));

CREATE POLICY reconciliation_lines_scope ON reconciliation_lines
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.read') OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.charge'));

CREATE POLICY reconciliation_matches_scope ON reconciliation_matches
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.read') OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.charge'));

CREATE POLICY reconciliation_snapshots_scope ON reconciliation_snapshots
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.read') OR perchpoint.has_capability('payment.charge')
  ));

CREATE POLICY reconciliation_acknowledgements_scope ON reconciliation_acknowledgements
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.read'));

CREATE POLICY reconciliation_closes_scope ON reconciliation_closes
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.read') OR perchpoint.has_capability('payment.charge') OR perchpoint.has_capability('payment.exception')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND (
    (state = 'draft' AND perchpoint.has_capability('payment.charge'))
    OR (state = 'issued' AND perchpoint.has_capability('payment.exception'))
  ));

GRANT SELECT, INSERT, UPDATE ON reconciliation_sources, reconciliation_lines TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT, INSERT ON reconciliation_matches, reconciliation_snapshots, reconciliation_acknowledgements, reconciliation_closes
  TO perchpoint_runtime, perchpoint_definer;
