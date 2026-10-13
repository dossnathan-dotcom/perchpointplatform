-- Phase 21 stores call metadata and staff notes. It does not store audio or transcripts.

SET LOCAL ROLE perchpoint_definer;
INSERT INTO capabilities (code, family, description)
VALUES ('calls.coordinate', 'calls', 'Coordinate call metadata and callbacks')
ON CONFLICT (code) DO NOTHING;

INSERT INTO role_bundle_capabilities (bundle_id, capability)
SELECT bundle.id, 'calls.coordinate'
FROM role_bundles bundle
WHERE bundle.name IN (
  'maintenance_coordinator', 'operations_manager', 'owner', 'project_manager'
)
ON CONFLICT DO NOTHING;
RESET ROLE;

CREATE TABLE call_provider_accounts (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  account_sid text NOT NULL,
  environment text NOT NULL DEFAULT 'local',
  PRIMARY KEY (organization_id, id),
  UNIQUE (account_sid, environment)
);

CREATE TABLE call_routes (
  organization_id uuid NOT NULL PRIMARY KEY,
  ann_destination text NOT NULL DEFAULT 'ann-handset',
  emergency_digit text NOT NULL DEFAULT '9',
  edges jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE call_interactions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  mode text NOT NULL CHECK (mode IN ('integrated', 'unintegrated')),
  direction text NOT NULL CHECK (direction IN ('inbound', 'outbound', 'manual')),
  root_sid text,
  caller_hint text,
  caller_status text NOT NULL CHECK (caller_status IN ('unverified', 'matched', 'withheld', 'ambiguous')),
  subject_kind text NOT NULL DEFAULT 'unclassified' CHECK (subject_kind IN ('unclassified', 'leasing', 'payments', 'maintenance', 'other')),
  case_reference text,
  terminal_outcome text,
  human_acknowledged boolean NOT NULL DEFAULT false,
  acknowledged_by uuid,
  duration_seconds integer,
  duration_kind text CHECK (duration_kind IS NULL OR duration_kind IN ('ringing', 'connected', 'billed', 'manual')),
  duration_source text CHECK (duration_source IS NULL OR duration_source IN ('provider', 'manual', 'unknown')),
  callback_due_at timestamptz,
  latest_sequence integer NOT NULL DEFAULT 0,
  repeat_count integer NOT NULL DEFAULT 1,
  environment text NOT NULL DEFAULT 'local',
  money_moved boolean NOT NULL DEFAULT false CHECK (money_moved = false),
  real_values_activated boolean NOT NULL DEFAULT false CHECK (real_values_activated = false),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, root_sid)
);

CREATE TABLE call_legs (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  interaction_id uuid NOT NULL,
  parent_leg_id uuid,
  provider_leg_id text NOT NULL,
  destination_label text NOT NULL,
  outcome text,
  ringing_seconds integer,
  connected_seconds integer,
  billed_seconds integer,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, provider_leg_id),
  FOREIGN KEY (organization_id, interaction_id) REFERENCES call_interactions (organization_id, id)
);

CREATE TABLE call_events (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  interaction_id uuid NOT NULL,
  provider_event_id text NOT NULL,
  event_name text NOT NULL,
  sequence integer NOT NULL,
  occurred_at timestamptz NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, provider_event_id)
);

CREATE TABLE call_callbacks (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  interaction_id uuid NOT NULL,
  owner_actor uuid NOT NULL,
  due_at timestamptz NOT NULL,
  state text NOT NULL CHECK (state IN ('open', 'done', 'escalated')),
  reason text NOT NULL,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE call_notes (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  interaction_id uuid NOT NULL,
  author_actor uuid NOT NULL,
  body text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE call_rejections (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  interaction_id uuid,
  field_name text NOT NULL,
  reason text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE call_commands (
  organization_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  fingerprint text NOT NULL,
  public_reference text NOT NULL,
  PRIMARY KEY (organization_id, actor_id, idempotency_key)
);

ALTER TABLE call_provider_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_provider_accounts FORCE ROW LEVEL SECURITY;
ALTER TABLE call_routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_routes FORCE ROW LEVEL SECURITY;
ALTER TABLE call_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_interactions FORCE ROW LEVEL SECURITY;
ALTER TABLE call_legs ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_legs FORCE ROW LEVEL SECURITY;
ALTER TABLE call_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_events FORCE ROW LEVEL SECURITY;
ALTER TABLE call_callbacks ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_callbacks FORCE ROW LEVEL SECURITY;
ALTER TABLE call_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_notes FORCE ROW LEVEL SECURITY;
ALTER TABLE call_rejections ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_rejections FORCE ROW LEVEL SECURITY;
ALTER TABLE call_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_commands FORCE ROW LEVEL SECURITY;

CREATE POLICY call_provider_accounts_scope ON call_provider_accounts
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'));

CREATE POLICY call_routes_scope ON call_routes
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'));

CREATE POLICY call_interactions_scope ON call_interactions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'));

CREATE POLICY call_legs_scope ON call_legs
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'));

CREATE POLICY call_events_scope ON call_events
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'));

CREATE POLICY call_callbacks_scope ON call_callbacks
  USING (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('calls.coordinate') OR perchpoint.has_capability('outbox.deliver')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('calls.coordinate') OR perchpoint.has_capability('outbox.deliver')
    )
  );

CREATE POLICY call_notes_scope ON call_notes
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'));

CREATE POLICY call_rejections_scope ON call_rejections
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('calls.coordinate'));

CREATE POLICY call_commands_scope ON call_commands
  USING (organization_id = perchpoint.current_org() AND actor_id = perchpoint.current_actor())
  WITH CHECK (organization_id = perchpoint.current_org() AND actor_id = perchpoint.current_actor());

GRANT SELECT, INSERT, UPDATE ON
  call_provider_accounts, call_routes, call_interactions, call_legs, call_events,
  call_callbacks, call_notes, call_rejections
  TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT, INSERT ON call_commands TO perchpoint_runtime, perchpoint_definer;
