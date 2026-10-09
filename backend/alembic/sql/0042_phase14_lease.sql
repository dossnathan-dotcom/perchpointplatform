-- Phase 14 consumes an approved Phase 13 handoff. It does not rewrite screening history,
-- post a ledger, collect money, or call a live signature provider.

CREATE TABLE lease_deals (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  public_reference text NOT NULL,
  state text NOT NULL CHECK (state IN ('reserved', 'approved', 'signing', 'executed', 'activated', 'canceled')),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  package_hash text NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor >= 0),
  PRIMARY KEY (organization_id, id),
  UNIQUE (public_reference),
  FOREIGN KEY (organization_id, case_id) REFERENCES screening_cases (organization_id, id)
);

CREATE UNIQUE INDEX lease_one_active_case
  ON lease_deals (organization_id, case_id)
  WHERE state <> 'canceled';

CREATE TABLE lease_packages (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  deal_id uuid NOT NULL,
  content_hash text NOT NULL,
  state text NOT NULL CHECK (state IN ('rendered', 'sent', 'executed')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, deal_id) REFERENCES lease_deals (organization_id, id)
);

CREATE TABLE lease_package_documents (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  package_id uuid NOT NULL,
  document_code text NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, package_id) REFERENCES lease_packages (organization_id, id)
);

CREATE TABLE lease_approvals (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  deal_id uuid NOT NULL,
  package_hash text NOT NULL,
  human_confirmed boolean NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, deal_id) REFERENCES lease_deals (organization_id, id),
  CHECK (human_confirmed)
);

CREATE TABLE lease_capabilities (
  organization_id uuid NOT NULL,
  token_hash text NOT NULL,
  deal_id uuid NOT NULL,
  expires_at timestamptz NOT NULL,
  revoked boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, token_hash)
);

CREATE TABLE lease_intake_keys (
  organization_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  fingerprint text NOT NULL,
  public_reference text NOT NULL,
  PRIMARY KEY (organization_id, idempotency_key)
);

CREATE TABLE signature_requests (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  deal_id uuid NOT NULL,
  state text NOT NULL CHECK (state IN ('active', 'executed', 'declined')),
  idempotency_key text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, deal_id),
  FOREIGN KEY (organization_id, deal_id) REFERENCES lease_deals (organization_id, id)
);

CREATE TABLE signature_inbox (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  request_id uuid NOT NULL,
  event_hash text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, request_id, event_hash),
  FOREIGN KEY (organization_id, request_id) REFERENCES signature_requests (organization_id, id)
);

CREATE TABLE deposit_obligations (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  deal_id uuid NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor >= 0),
  state text NOT NULL CHECK (state IN ('due', 'satisfied', 'failed')),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, deal_id),
  FOREIGN KEY (organization_id, deal_id) REFERENCES lease_deals (organization_id, id)
);

CREATE TABLE lease_activations (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  deal_id uuid NOT NULL,
  manifest_hash text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, deal_id),
  FOREIGN KEY (organization_id, deal_id) REFERENCES lease_deals (organization_id, id)
);

CREATE TABLE resident_households (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  deal_id uuid NOT NULL,
  state text NOT NULL CHECK (state IN ('active')),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, deal_id),
  FOREIGN KEY (organization_id, deal_id) REFERENCES lease_deals (organization_id, id)
);

CREATE TABLE lease_source_documents (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  source_code text NOT NULL,
  review_state text NOT NULL CHECK (review_state IN ('uploaded', 'human_verified', 'blocked')),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE lease_clause_versions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  clause_code text NOT NULL,
  review_state text NOT NULL CHECK (review_state IN ('draft', 'approved', 'blocked')),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE lease_template_versions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  template_code text NOT NULL,
  review_state text NOT NULL CHECK (review_state IN ('draft', 'approved', 'blocked')),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE lease_recipients (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  deal_id uuid NOT NULL,
  role_name text NOT NULL,
  recipient_state text NOT NULL CHECK (recipient_state IN ('pending_order', 'completed', 'declined')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, deal_id) REFERENCES lease_deals (organization_id, id)
);

CREATE TABLE signature_events (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  deal_id uuid NOT NULL,
  event_code text NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, deal_id) REFERENCES lease_deals (organization_id, id)
);

CREATE TABLE readiness_items (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  deal_id uuid NOT NULL,
  item_code text NOT NULL,
  item_state text NOT NULL CHECK (item_state IN ('pending', 'satisfied', 'waived', 'blocked')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, deal_id) REFERENCES lease_deals (organization_id, id)
);

CREATE TABLE condition_items (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  deal_id uuid NOT NULL,
  item_code text NOT NULL,
  item_state text NOT NULL CHECK (item_state IN ('draft', 'finalized')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, deal_id) REFERENCES lease_deals (organization_id, id)
);

CREATE INDEX lease_deals_queue ON lease_deals (organization_id, state, public_reference);
CREATE INDEX lease_packages_deal ON lease_packages (organization_id, deal_id);
CREATE INDEX lease_recipients_deal ON lease_recipients (organization_id, deal_id);
CREATE INDEX signature_events_deal ON signature_events (organization_id, deal_id);
CREATE INDEX readiness_items_deal ON readiness_items (organization_id, deal_id);
CREATE INDEX condition_items_deal ON condition_items (organization_id, deal_id);
CREATE INDEX deposit_obligations_deal ON deposit_obligations (organization_id, deal_id);

ALTER TABLE lease_deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE lease_deals FORCE ROW LEVEL SECURITY;
ALTER TABLE lease_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE lease_packages FORCE ROW LEVEL SECURITY;
ALTER TABLE lease_package_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE lease_package_documents FORCE ROW LEVEL SECURITY;
ALTER TABLE lease_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE lease_approvals FORCE ROW LEVEL SECURITY;
ALTER TABLE lease_capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE lease_capabilities FORCE ROW LEVEL SECURITY;
ALTER TABLE lease_intake_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE lease_intake_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE signature_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE signature_requests FORCE ROW LEVEL SECURITY;
ALTER TABLE signature_inbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE signature_inbox FORCE ROW LEVEL SECURITY;
ALTER TABLE deposit_obligations ENABLE ROW LEVEL SECURITY;
ALTER TABLE deposit_obligations FORCE ROW LEVEL SECURITY;
ALTER TABLE lease_activations ENABLE ROW LEVEL SECURITY;
ALTER TABLE lease_activations FORCE ROW LEVEL SECURITY;
ALTER TABLE resident_households ENABLE ROW LEVEL SECURITY;
ALTER TABLE resident_households FORCE ROW LEVEL SECURITY;
ALTER TABLE lease_source_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE lease_source_documents FORCE ROW LEVEL SECURITY;
ALTER TABLE lease_clause_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE lease_clause_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE lease_template_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE lease_template_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE lease_recipients ENABLE ROW LEVEL SECURITY;
ALTER TABLE lease_recipients FORCE ROW LEVEL SECURITY;
ALTER TABLE signature_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE signature_events FORCE ROW LEVEL SECURITY;
ALTER TABLE readiness_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE readiness_items FORCE ROW LEVEL SECURITY;
ALTER TABLE condition_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE condition_items FORCE ROW LEVEL SECURITY;

CREATE POLICY lease_deals_scope ON lease_deals
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY lease_packages_scope ON lease_packages
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY lease_package_documents_scope ON lease_package_documents
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY lease_approvals_scope ON lease_approvals
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY lease_capabilities_scope ON lease_capabilities
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY lease_intake_keys_scope ON lease_intake_keys
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY signature_requests_scope ON signature_requests
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY signature_inbox_scope ON signature_inbox
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY deposit_obligations_scope ON deposit_obligations
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY lease_activations_scope ON lease_activations
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY resident_households_scope ON resident_households
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY lease_source_documents_scope ON lease_source_documents
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY lease_clause_versions_scope ON lease_clause_versions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY lease_template_versions_scope ON lease_template_versions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY lease_recipients_scope ON lease_recipients
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY signature_events_scope ON signature_events
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY readiness_items_scope ON readiness_items
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY condition_items_scope ON condition_items
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));

GRANT SELECT, INSERT, UPDATE, DELETE ON lease_deals, lease_packages, lease_package_documents, lease_approvals,
  lease_capabilities, lease_intake_keys, signature_requests, signature_inbox, deposit_obligations, lease_activations,
  resident_households, lease_source_documents, lease_clause_versions, lease_template_versions, lease_recipients,
  signature_events, readiness_items, condition_items
  TO perchpoint_runtime, perchpoint_definer;

CREATE FUNCTION perchpoint.place_lease_signature(token_hash text, idempotency_key text, fingerprint text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  lease_deal uuid;
  current_state text;
  existing_fp text;
  existing_ref text;
  reference text;
BEGIN
  SELECT capability.organization_id, capability.deal_id INTO org, lease_deal
  FROM lease_capabilities capability
  WHERE capability.token_hash = place_lease_signature.token_hash
    AND capability.revoked = false AND capability.expires_at > now();
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext(org::text || lease_deal::text));
  SELECT lease_intake_keys.fingerprint, lease_intake_keys.public_reference
    INTO existing_fp, existing_ref
  FROM lease_intake_keys
  WHERE organization_id = org AND lease_intake_keys.idempotency_key = place_lease_signature.idempotency_key;
  IF existing_fp IS NOT NULL THEN
    IF existing_fp <> fingerprint THEN
      RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
    END IF;
    RETURN jsonb_build_object('accepted', true, 'reference', existing_ref, 'replayed', true, 'state', 'signing');
  END IF;
  SELECT state, public_reference INTO current_state, reference
  FROM lease_deals WHERE organization_id = org AND id = lease_deal FOR UPDATE;
  IF current_state <> 'approved' THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
  END IF;
  INSERT INTO signature_requests (organization_id, id, deal_id, state, idempotency_key)
  VALUES (org, gen_random_uuid(), lease_deal, 'active', idempotency_key);
  UPDATE lease_deals SET state = 'signing', version = version + 1
  WHERE organization_id = org AND id = lease_deal;
  INSERT INTO lease_intake_keys (organization_id, idempotency_key, fingerprint, public_reference)
  VALUES (org, place_lease_signature.idempotency_key, fingerprint, reference);
  RETURN jsonb_build_object('accepted', true, 'reference', reference, 'replayed', false, 'state', 'signing');
END $$;

CREATE FUNCTION perchpoint.apply_lease_signature(token_hash text, event_hash text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  lease_deal uuid;
  signature_request uuid;
BEGIN
  SELECT capability.organization_id, capability.deal_id INTO org, lease_deal
  FROM lease_capabilities capability
  WHERE capability.token_hash = apply_lease_signature.token_hash
    AND capability.revoked = false AND capability.expires_at > now();
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT id INTO signature_request FROM signature_requests
  WHERE organization_id = org AND deal_id = lease_deal;
  IF signature_request IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
  END IF;
  IF EXISTS (
    SELECT 1 FROM signature_inbox
    WHERE organization_id = org AND request_id = signature_request AND signature_inbox.event_hash = apply_lease_signature.event_hash
  ) THEN
    RETURN jsonb_build_object('accepted', true, 'replayed', true, 'state', 'executed');
  END IF;
  INSERT INTO signature_inbox (organization_id, id, request_id, event_hash)
  VALUES (org, gen_random_uuid(), signature_request, event_hash);
  UPDATE signature_requests SET state = 'executed'
  WHERE organization_id = org AND id = signature_request;
  UPDATE lease_packages SET state = 'executed'
  WHERE organization_id = org AND deal_id = lease_deal;
  UPDATE lease_deals SET state = 'executed', version = version + 1
  WHERE organization_id = org AND id = lease_deal AND state = 'signing';
  RETURN jsonb_build_object('accepted', true, 'replayed', false, 'state', 'executed');
END $$;

REVOKE ALL ON FUNCTION perchpoint.place_lease_signature(text, text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.apply_lease_signature(text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.place_lease_signature(text, text, text) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.apply_lease_signature(text, text) TO perchpoint_runtime, perchpoint_definer;
ALTER FUNCTION perchpoint.place_lease_signature(text, text, text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.apply_lease_signature(text, text) OWNER TO perchpoint_definer;
