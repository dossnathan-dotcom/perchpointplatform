-- Phase 13 screening cases, fake provider evidence, human decisions, notices, and disputes.
-- No lease, payment, or live provider table is created. Criminal products stay disabled.

CREATE TABLE screening_cases (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  application_id uuid NOT NULL,
  public_reference text NOT NULL,
  state text NOT NULL CHECK (state IN (
    'awaiting_authorization', 'ready_to_order', 'awaiting_results', 'ready_for_review', 'decided', 'withdrawn'
  )),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  jurisdiction_code text NOT NULL DEFAULT 'OH',
  profile_kind text NOT NULL DEFAULT 'production' CHECK (profile_kind IN ('production', 'test_only')),
  criminal_enabled boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, id),
  UNIQUE (public_reference),
  FOREIGN KEY (organization_id, application_id) REFERENCES applications (organization_id, id),
  CHECK (profile_kind <> 'production' OR criminal_enabled = false)
);

CREATE UNIQUE INDEX screening_one_active_application
  ON screening_cases (organization_id, application_id)
  WHERE state <> 'withdrawn';

CREATE TABLE screening_subjects (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  role_name text NOT NULL CHECK (role_name IN ('primary', 'co_applicant', 'guarantor')),
  authorization_state text NOT NULL CHECK (authorization_state IN ('pending', 'granted', 'withdrawn')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, case_id) REFERENCES screening_cases (organization_id, id)
);

CREATE TABLE screening_orders (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  product text NOT NULL CHECK (product IN ('credit', 'income', 'rental')),
  state text NOT NULL CHECK (state IN ('submitted', 'complete', 'unavailable')),
  idempotency_key text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, case_id, product),
  FOREIGN KEY (organization_id, case_id) REFERENCES screening_cases (organization_id, id)
);

CREATE TABLE screening_components (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  order_id uuid NOT NULL,
  component_code text NOT NULL,
  component_state text NOT NULL CHECK (component_state IN ('pending', 'complete', 'unavailable')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, order_id) REFERENCES screening_orders (organization_id, id)
);

CREATE TABLE screening_evidence (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  evidence_kind text NOT NULL,
  normalized_value text NOT NULL,
  source_name text NOT NULL DEFAULT 'fake_provider',
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, case_id) REFERENCES screening_cases (organization_id, id),
  CHECK (length(normalized_value) <= 200 AND position('ssn' in lower(normalized_value)) = 0)
);

CREATE TABLE screening_evaluations (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  criterion_code text NOT NULL,
  result_code text NOT NULL CHECK (result_code IN ('met', 'unresolved', 'not_applicable')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, case_id) REFERENCES screening_cases (organization_id, id)
);

CREATE TABLE screening_decisions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  outcome text NOT NULL CHECK (outcome IN (
    'approved', 'conditional', 'denied', 'withdrawn', 'unable_to_complete', 'expired', 'superseded'
  )),
  human_confirmed boolean NOT NULL,
  basis_code text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, case_id),
  FOREIGN KEY (organization_id, case_id) REFERENCES screening_cases (organization_id, id),
  CHECK (human_confirmed)
);

CREATE TABLE screening_notices (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  notice_kind text NOT NULL CHECK (notice_kind IN ('adverse_action', 'non_fcra')),
  content_hash text NOT NULL,
  delivery_state text NOT NULL CHECK (delivery_state IN ('queued', 'delivered', 'failed')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, case_id) REFERENCES screening_cases (organization_id, id)
);

CREATE TABLE screening_disputes (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  dispute_kind text NOT NULL,
  state text NOT NULL CHECK (state IN ('submitted', 'review', 'resolved')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, case_id) REFERENCES screening_cases (organization_id, id)
);

CREATE TABLE screening_handoffs (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  package_hash text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, case_id),
  FOREIGN KEY (organization_id, case_id) REFERENCES screening_cases (organization_id, id)
);

CREATE TABLE screening_capabilities (
  organization_id uuid NOT NULL,
  token_hash text NOT NULL,
  case_id uuid NOT NULL,
  expires_at timestamptz NOT NULL,
  revoked boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, token_hash)
);

CREATE TABLE screening_intake_keys (
  organization_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  fingerprint text NOT NULL,
  public_reference text NOT NULL,
  PRIMARY KEY (organization_id, idempotency_key)
);

CREATE TABLE screening_inbox (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  order_id uuid NOT NULL,
  event_hash text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, event_hash)
);

CREATE INDEX screening_cases_queue ON screening_cases (organization_id, state, public_reference);
CREATE INDEX screening_subjects_case ON screening_subjects (organization_id, case_id);
CREATE INDEX screening_orders_case ON screening_orders (organization_id, case_id);
CREATE INDEX screening_evaluations_case ON screening_evaluations (organization_id, case_id);

ALTER TABLE screening_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_cases FORCE ROW LEVEL SECURITY;
ALTER TABLE screening_subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_subjects FORCE ROW LEVEL SECURITY;
ALTER TABLE screening_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_orders FORCE ROW LEVEL SECURITY;
ALTER TABLE screening_components ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_components FORCE ROW LEVEL SECURITY;
ALTER TABLE screening_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_evidence FORCE ROW LEVEL SECURITY;
ALTER TABLE screening_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_evaluations FORCE ROW LEVEL SECURITY;
ALTER TABLE screening_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_decisions FORCE ROW LEVEL SECURITY;
ALTER TABLE screening_notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_notices FORCE ROW LEVEL SECURITY;
ALTER TABLE screening_disputes ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_disputes FORCE ROW LEVEL SECURITY;
ALTER TABLE screening_handoffs ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_handoffs FORCE ROW LEVEL SECURITY;
ALTER TABLE screening_capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_capabilities FORCE ROW LEVEL SECURITY;
ALTER TABLE screening_intake_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_intake_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE screening_inbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE screening_inbox FORCE ROW LEVEL SECURITY;

CREATE POLICY screening_cases_scope ON screening_cases
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY screening_subjects_scope ON screening_subjects
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY screening_orders_scope ON screening_orders
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY screening_components_scope ON screening_components
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY screening_evidence_scope ON screening_evidence
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY screening_evaluations_scope ON screening_evaluations
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY screening_decisions_scope ON screening_decisions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY screening_notices_scope ON screening_notices
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY screening_disputes_scope ON screening_disputes
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY screening_handoffs_scope ON screening_handoffs
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY screening_capabilities_scope ON screening_capabilities
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY screening_intake_keys_scope ON screening_intake_keys
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY screening_inbox_scope ON screening_inbox
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));

GRANT SELECT, INSERT, UPDATE, DELETE ON screening_cases, screening_subjects, screening_orders, screening_components,
  screening_evidence, screening_evaluations, screening_decisions, screening_notices, screening_disputes,
  screening_handoffs, screening_capabilities, screening_intake_keys, screening_inbox
  TO perchpoint_runtime, perchpoint_definer;

CREATE FUNCTION perchpoint.open_screening_case(application_reference text, caller_org uuid, idempotency_key text, fingerprint text, token_hash text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  application uuid;
  app_state text;
  existing_fp text;
  existing_ref text;
  reference text := replace(gen_random_uuid()::text, '-', '');
  screening_case uuid := gen_random_uuid();
BEGIN
  SELECT application.organization_id, application.id, application.state
    INTO org, application, app_state
  FROM applications application
  WHERE application.public_reference = open_screening_case.application_reference
    AND application.organization_id = caller_org;
  IF org IS NULL OR app_state <> 'ready_for_screening' THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT screening_intake_keys.fingerprint, screening_intake_keys.public_reference
    INTO existing_fp, existing_ref
  FROM screening_intake_keys
  WHERE organization_id = org AND screening_intake_keys.idempotency_key = open_screening_case.idempotency_key;
  IF existing_fp IS NOT NULL THEN
    IF existing_fp <> fingerprint THEN
      RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
    END IF;
    RETURN jsonb_build_object('accepted', true, 'reference', existing_ref, 'replayed', true);
  END IF;
  IF EXISTS (
    SELECT 1 FROM screening_cases
    WHERE organization_id = org AND application_id = application AND state <> 'withdrawn'
  ) THEN
    SELECT public_reference INTO existing_ref FROM screening_cases
    WHERE organization_id = org AND application_id = application AND state <> 'withdrawn';
    RETURN jsonb_build_object('accepted', true, 'reference', existing_ref, 'replayed', true);
  END IF;
  INSERT INTO screening_cases (organization_id, id, application_id, public_reference, state)
  VALUES (org, screening_case, application, reference, 'awaiting_authorization');
  INSERT INTO screening_subjects (organization_id, id, case_id, role_name, authorization_state)
  VALUES (org, gen_random_uuid(), screening_case, 'primary', 'pending');
  INSERT INTO screening_capabilities (organization_id, token_hash, case_id, expires_at)
  VALUES (org, token_hash, screening_case, now() + interval '2 days');
  INSERT INTO screening_intake_keys (organization_id, idempotency_key, fingerprint, public_reference)
  VALUES (org, open_screening_case.idempotency_key, fingerprint, reference);
  RETURN jsonb_build_object('accepted', true, 'reference', reference, 'replayed', false, 'state', 'awaiting_authorization');
END $$;

CREATE FUNCTION perchpoint.grant_screening_authorization(token_hash text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  screening_case uuid;
BEGIN
  SELECT capability.organization_id, capability.case_id INTO org, screening_case
  FROM screening_capabilities capability
  WHERE capability.token_hash = grant_screening_authorization.token_hash
    AND capability.revoked = false AND capability.expires_at > now();
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  UPDATE screening_subjects SET authorization_state = 'granted'
  WHERE organization_id = org AND case_id = screening_case AND role_name = 'primary';
  UPDATE screening_cases SET state = 'ready_to_order', version = version + 1
  WHERE organization_id = org AND id = screening_case AND state = 'awaiting_authorization';
  RETURN jsonb_build_object('accepted', true, 'state', 'ready_to_order');
END $$;

CREATE FUNCTION perchpoint.place_screening_order(token_hash text, product text, idempotency_key text, fingerprint text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  screening_case uuid;
  current_state text;
  existing_fp text;
  existing_ref text;
  reference text;
BEGIN
  IF product IS NULL OR product NOT IN ('credit', 'income', 'rental') THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT capability.organization_id, capability.case_id INTO org, screening_case
  FROM screening_capabilities capability
  WHERE capability.token_hash = place_screening_order.token_hash
    AND capability.revoked = false AND capability.expires_at > now();
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext(org::text || screening_case::text));
  SELECT screening_intake_keys.fingerprint, screening_intake_keys.public_reference
    INTO existing_fp, existing_ref
  FROM screening_intake_keys
  WHERE organization_id = org AND screening_intake_keys.idempotency_key = place_screening_order.idempotency_key;
  IF existing_fp IS NOT NULL THEN
    IF existing_fp <> fingerprint THEN
      RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
    END IF;
    RETURN jsonb_build_object('accepted', true, 'reference', existing_ref, 'replayed', true, 'state', 'awaiting_results');
  END IF;
  SELECT state, public_reference INTO current_state, reference
  FROM screening_cases WHERE organization_id = org AND id = screening_case FOR UPDATE;
  IF current_state <> 'ready_to_order' THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
  END IF;
  INSERT INTO screening_orders (organization_id, id, case_id, product, state, idempotency_key)
  VALUES (org, gen_random_uuid(), screening_case, product, 'submitted', idempotency_key);
  UPDATE screening_cases SET state = 'awaiting_results', version = version + 1
  WHERE organization_id = org AND id = screening_case;
  INSERT INTO screening_intake_keys (organization_id, idempotency_key, fingerprint, public_reference)
  VALUES (org, place_screening_order.idempotency_key, fingerprint, reference);
  RETURN jsonb_build_object('accepted', true, 'reference', reference, 'replayed', false, 'state', 'awaiting_results', 'product', product);
END $$;

CREATE FUNCTION perchpoint.apply_screening_result(token_hash text, event_hash text, coverage text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  screening_case uuid;
  screening_order uuid;
BEGIN
  IF coverage NOT IN ('complete', 'unavailable') THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT capability.organization_id, capability.case_id INTO org, screening_case
  FROM screening_capabilities capability
  WHERE capability.token_hash = apply_screening_result.token_hash
    AND capability.revoked = false AND capability.expires_at > now();
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT id INTO screening_order FROM screening_orders
  WHERE organization_id = org AND case_id = screening_case
  ORDER BY id LIMIT 1;
  IF screening_order IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
  END IF;
  IF EXISTS (SELECT 1 FROM screening_inbox WHERE organization_id = org AND screening_inbox.event_hash = apply_screening_result.event_hash) THEN
    RETURN jsonb_build_object('accepted', true, 'replayed', true, 'state', 'ready_for_review');
  END IF;
  INSERT INTO screening_inbox (organization_id, id, order_id, event_hash)
  VALUES (org, gen_random_uuid(), screening_order, event_hash);
  UPDATE screening_orders SET state = CASE WHEN coverage = 'complete' THEN 'complete' ELSE 'unavailable' END
  WHERE organization_id = org AND id = screening_order;
  IF coverage = 'complete' THEN
    INSERT INTO screening_evidence (organization_id, id, case_id, evidence_kind, normalized_value)
    VALUES (org, gen_random_uuid(), screening_case, 'income', 'verified_recurring');
    INSERT INTO screening_evaluations (organization_id, id, case_id, criterion_code, result_code)
    VALUES (org, gen_random_uuid(), screening_case, 'ability_to_pay', 'met');
  ELSE
    INSERT INTO screening_evaluations (organization_id, id, case_id, criterion_code, result_code)
    VALUES (org, gen_random_uuid(), screening_case, 'ability_to_pay', 'unresolved');
  END IF;
  UPDATE screening_cases SET state = 'ready_for_review', version = version + 1
  WHERE organization_id = org AND id = screening_case AND state = 'awaiting_results';
  RETURN jsonb_build_object('accepted', true, 'replayed', false, 'state', 'ready_for_review');
END $$;

REVOKE ALL ON FUNCTION perchpoint.open_screening_case(text, uuid, text, text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.grant_screening_authorization(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.place_screening_order(text, text, text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.apply_screening_result(text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.open_screening_case(text, uuid, text, text, text) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.grant_screening_authorization(text) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.place_screening_order(text, text, text, text) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.apply_screening_result(text, text, text) TO perchpoint_runtime, perchpoint_definer;
ALTER FUNCTION perchpoint.open_screening_case(text, uuid, text, text, text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.grant_screening_authorization(text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.place_screening_order(text, text, text, text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.apply_screening_result(text, text, text) OWNER TO perchpoint_definer;
