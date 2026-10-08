-- Phase 12 applications, households, and documents. No screening, lease, or payment table is created.

CREATE TABLE application_policies (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  draft_days integer NOT NULL DEFAULT 30 CHECK (draft_days = 30),
  zone_name text NOT NULL DEFAULT 'America/New_York',
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE applications (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  prospect_id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  listing_slug text NOT NULL,
  snapshot_id uuid,
  application_type text NOT NULL CHECK (application_type IN ('residential', 'commercial')),
  state text NOT NULL CHECK (state IN ('draft', 'submitted', 'withdrawn', 'ready_for_screening')),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  public_reference text NOT NULL,
  policy_version integer NOT NULL DEFAULT 1,
  fee_state text NOT NULL DEFAULT 'not_collected' CHECK (fee_state = 'not_collected'),
  showing_reference text NOT NULL DEFAULT '',
  PRIMARY KEY (organization_id, id),
  UNIQUE (public_reference),
  FOREIGN KEY (organization_id, inquiry_id) REFERENCES leasing_inquiries (organization_id, id)
);

CREATE UNIQUE INDEX applications_one_active_target
  ON applications (organization_id, prospect_id, listing_slug)
  WHERE state <> 'withdrawn';

CREATE TABLE application_participants (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  application_id uuid NOT NULL,
  role_name text NOT NULL CHECK (role_name IN ('primary', 'co_applicant', 'adult_occupant', 'minor_occupant', 'guarantor', 'representative')),
  preferred_name text NOT NULL DEFAULT '',
  legal_name text NOT NULL DEFAULT '',
  contact_email text NOT NULL DEFAULT '',
  attested boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, application_id) REFERENCES applications (organization_id, id),
  CHECK (length(preferred_name) <= 120 AND length(legal_name) <= 120)
);

CREATE TABLE application_answers (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  application_id uuid NOT NULL,
  participant_id uuid NOT NULL,
  field_code text NOT NULL,
  field_value text NOT NULL,
  origin text NOT NULL CHECK (origin IN ('applicant', 'staff_assisted')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, application_id) REFERENCES applications (organization_id, id),
  FOREIGN KEY (organization_id, participant_id) REFERENCES application_participants (organization_id, id),
  CHECK (length(field_value) <= 500 AND position('<' in field_value) = 0)
);

CREATE TABLE application_disclosures (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  application_id uuid NOT NULL,
  purpose text NOT NULL CHECK (purpose IN ('application_processing', 'document_processing')),
  content_hash text NOT NULL,
  acknowledged boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, application_id) REFERENCES applications (organization_id, id)
);

CREATE TABLE application_documents (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  application_id uuid NOT NULL,
  participant_id uuid NOT NULL,
  document_class text NOT NULL CHECK (document_class IN ('income_evidence', 'rental_evidence', 'commercial_evidence')),
  display_name text NOT NULL,
  object_key text NOT NULL,
  content_hash text NOT NULL,
  byte_size integer NOT NULL CHECK (byte_size BETWEEN 1 AND 5000000),
  scan_state text NOT NULL CHECK (scan_state IN ('quarantine', 'clean', 'rejected')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, application_id) REFERENCES applications (organization_id, id),
  FOREIGN KEY (organization_id, participant_id) REFERENCES application_participants (organization_id, id)
);

CREATE TABLE application_invitations (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  application_id uuid NOT NULL,
  role_name text NOT NULL,
  token_hash text NOT NULL,
  destination_email text NOT NULL,
  state text NOT NULL CHECK (state IN ('pending', 'accepted', 'revoked', 'expired')),
  expires_at timestamptz NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, token_hash),
  FOREIGN KEY (organization_id, application_id) REFERENCES applications (organization_id, id)
);

CREATE TABLE application_submissions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  application_id uuid NOT NULL,
  snapshot_hash text NOT NULL,
  schema_version integer NOT NULL DEFAULT 1,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, application_id),
  FOREIGN KEY (organization_id, application_id) REFERENCES applications (organization_id, id)
);

CREATE TABLE application_supplements (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  application_id uuid NOT NULL,
  reason text NOT NULL,
  snapshot_hash text NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, application_id) REFERENCES applications (organization_id, id),
  CHECK (length(reason) <= 300)
);

CREATE TABLE application_requests (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  application_id uuid NOT NULL,
  field_code text NOT NULL,
  due_at timestamptz NOT NULL,
  state text NOT NULL CHECK (state IN ('open', 'answered')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, application_id) REFERENCES applications (organization_id, id)
);

CREATE TABLE application_capabilities (
  organization_id uuid NOT NULL,
  token_hash text NOT NULL,
  application_id uuid NOT NULL,
  expires_at timestamptz NOT NULL,
  revoked boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, token_hash)
);

CREATE TABLE application_intake_keys (
  organization_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  fingerprint text NOT NULL,
  public_reference text NOT NULL,
  PRIMARY KEY (organization_id, idempotency_key)
);

CREATE TABLE application_events (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  application_id uuid NOT NULL,
  event_kind text NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, application_id) REFERENCES applications (organization_id, id)
);

CREATE TABLE application_legal_holds (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  application_id uuid NOT NULL,
  reason text NOT NULL,
  released boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, application_id) REFERENCES applications (organization_id, id)
);

ALTER TABLE application_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_policies FORCE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications FORCE ROW LEVEL SECURITY;
ALTER TABLE application_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_participants FORCE ROW LEVEL SECURITY;
ALTER TABLE application_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_answers FORCE ROW LEVEL SECURITY;
ALTER TABLE application_disclosures ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_disclosures FORCE ROW LEVEL SECURITY;
ALTER TABLE application_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_documents FORCE ROW LEVEL SECURITY;
ALTER TABLE application_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_invitations FORCE ROW LEVEL SECURITY;
ALTER TABLE application_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_submissions FORCE ROW LEVEL SECURITY;
ALTER TABLE application_supplements ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_supplements FORCE ROW LEVEL SECURITY;
ALTER TABLE application_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_requests FORCE ROW LEVEL SECURITY;
ALTER TABLE application_capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_capabilities FORCE ROW LEVEL SECURITY;
ALTER TABLE application_intake_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_intake_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE application_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_events FORCE ROW LEVEL SECURITY;
ALTER TABLE application_legal_holds ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_legal_holds FORCE ROW LEVEL SECURITY;

CREATE POLICY application_policies_scope ON application_policies
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY applications_scope ON applications
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY application_participants_scope ON application_participants
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY application_answers_scope ON application_answers
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY application_disclosures_scope ON application_disclosures
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY application_documents_scope ON application_documents
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY application_invitations_scope ON application_invitations
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY application_submissions_scope ON application_submissions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY application_supplements_scope ON application_supplements
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY application_requests_scope ON application_requests
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY application_capabilities_scope ON application_capabilities
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY application_intake_keys_scope ON application_intake_keys
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY application_events_scope ON application_events
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY application_legal_holds_scope ON application_legal_holds
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));

GRANT SELECT, INSERT, UPDATE, DELETE ON application_policies, applications, application_participants, application_answers,
  application_disclosures, application_documents, application_invitations, application_submissions, application_supplements,
  application_requests, application_capabilities, application_intake_keys, application_events, application_legal_holds
  TO perchpoint_runtime, perchpoint_definer;

CREATE INDEX applications_queue ON applications (organization_id, state, public_reference);

CREATE FUNCTION perchpoint.start_application(intake jsonb, idempotency_key text, fingerprint text, token_hash text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  inquiry uuid;
  prospect uuid;
  slug text;
  snap uuid;
  existing_fp text;
  existing_ref text;
  reference text := replace(gen_random_uuid()::text, '-', '');
  application uuid := gen_random_uuid();
  participant uuid := gen_random_uuid();
  app_type text := COALESCE(intake->>'application_type', 'residential');
BEGIN
  IF intake ? 'ssn' OR intake ? 'credit_score' OR intake ? 'criminal_history' OR intake ? 'screening' OR intake ? 'lease' OR intake ? 'payment_token' OR intake ? 'organization_id' THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  IF COALESCE(intake->>'disclosure', '') <> 'true' OR app_type NOT IN ('residential', 'commercial') THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT leasing.organization_id, leasing.id, leasing.prospect_id, interest.public_slug, interest.snapshot_id
    INTO org, inquiry, prospect, slug, snap
  FROM leasing_inquiries leasing
  JOIN leasing_interests interest ON interest.organization_id = leasing.organization_id AND interest.inquiry_id = leasing.id
  JOIN discovery_projections projection ON projection.public_slug = interest.public_slug AND projection.current AND projection.eligibility = 'eligible'
  WHERE leasing.public_receipt = intake->>'receipt'
  ORDER BY interest.public_slug
  LIMIT 1;
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT application_intake_keys.fingerprint, application_intake_keys.public_reference INTO existing_fp, existing_ref
  FROM application_intake_keys
  WHERE organization_id = org AND application_intake_keys.idempotency_key = start_application.idempotency_key;
  IF existing_fp IS NOT NULL THEN
    IF existing_fp <> fingerprint THEN
      RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
    END IF;
    RETURN jsonb_build_object('accepted', true, 'reference', existing_ref, 'replayed', true);
  END IF;
  IF EXISTS (
    SELECT 1 FROM applications
    WHERE organization_id = org AND prospect_id = prospect AND listing_slug = slug AND state <> 'withdrawn'
  ) THEN
    SELECT public_reference INTO existing_ref FROM applications
    WHERE organization_id = org AND prospect_id = prospect AND listing_slug = slug AND state <> 'withdrawn';
    RETURN jsonb_build_object('accepted', true, 'reference', existing_ref, 'replayed', true, 'resumed', true);
  END IF;
  INSERT INTO application_policies (organization_id, id)
  SELECT org, gen_random_uuid()
  WHERE NOT EXISTS (SELECT 1 FROM application_policies WHERE organization_id = org);
  INSERT INTO applications (
    organization_id, id, prospect_id, inquiry_id, listing_slug, snapshot_id, application_type, state, public_reference, showing_reference
  ) VALUES (
    org, application, prospect, inquiry, slug, snap, app_type, 'draft', reference, COALESCE(intake->>'showing_reference', '')
  );
  INSERT INTO application_participants (organization_id, id, application_id, role_name, preferred_name, legal_name, contact_email)
  VALUES (org, participant, application, 'primary', COALESCE(intake->>'preferred_name', ''), COALESCE(intake->>'legal_name', ''), COALESCE(intake->>'email', ''));
  INSERT INTO application_disclosures (organization_id, id, application_id, purpose, content_hash, acknowledged)
  VALUES (org, gen_random_uuid(), application, 'application_processing', md5('application-processing-v1'), true);
  INSERT INTO application_capabilities (organization_id, token_hash, application_id, expires_at)
  VALUES (org, token_hash, application, now() + interval '2 days');
  INSERT INTO application_events (organization_id, id, application_id, event_kind)
  VALUES (org, gen_random_uuid(), application, 'started');
  INSERT INTO application_intake_keys (organization_id, idempotency_key, fingerprint, public_reference)
  VALUES (org, start_application.idempotency_key, fingerprint, reference);
  RETURN jsonb_build_object('accepted', true, 'reference', reference, 'replayed', false, 'state', 'draft');
END $$;

CREATE FUNCTION perchpoint.save_application_answer(token_hash text, field_code text, field_value text, expected_version integer)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  application uuid;
  participant uuid;
  current_version integer;
  current_state text;
BEGIN
  IF field_code IN ('ssn', 'credit_score', 'criminal_history', 'tenant_quality') OR position('<' in field_value) > 0 THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT capability.organization_id, capability.application_id INTO org, application
  FROM application_capabilities capability
  WHERE capability.token_hash = save_application_answer.token_hash AND capability.revoked = false AND capability.expires_at > now();
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT version, state INTO current_version, current_state FROM applications WHERE organization_id = org AND id = application FOR UPDATE;
  IF current_state <> 'draft' OR current_version <> expected_version THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
  END IF;
  SELECT id INTO participant FROM application_participants
  WHERE organization_id = org AND application_id = application AND role_name = 'primary';
  INSERT INTO application_answers (organization_id, id, application_id, participant_id, field_code, field_value, origin)
  VALUES (org, gen_random_uuid(), application, participant, field_code, left(field_value, 500), 'applicant');
  UPDATE applications SET version = version + 1 WHERE organization_id = org AND id = application;
  RETURN jsonb_build_object('accepted', true, 'version', current_version + 1);
END $$;

CREATE FUNCTION perchpoint.finalize_application_document(token_hash text, document_class text, display_name text, content_hash text, byte_size integer, magic text, suspicious boolean)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  application uuid;
  participant uuid;
  scan text := 'clean';
BEGIN
  IF document_class NOT IN ('income_evidence', 'rental_evidence', 'commercial_evidence') OR magic NOT IN ('JFIF', 'PDF') THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT capability.organization_id, capability.application_id INTO org, application
  FROM application_capabilities capability
  WHERE capability.token_hash = finalize_application_document.token_hash AND capability.revoked = false AND capability.expires_at > now();
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT id INTO participant FROM application_participants
  WHERE organization_id = org AND application_id = application AND role_name = 'primary';
  IF suspicious THEN
    scan := 'rejected';
  END IF;
  INSERT INTO application_documents (
    organization_id, id, application_id, participant_id, document_class, display_name, object_key, content_hash, byte_size, scan_state
  ) VALUES (
    org, gen_random_uuid(), application, participant, document_class, left(display_name, 80), replace(gen_random_uuid()::text, '-', ''),
    content_hash, byte_size, scan
  );
  RETURN jsonb_build_object('accepted', true, 'scan_state', scan);
END $$;

CREATE FUNCTION perchpoint.submit_application(token_hash text, idempotency_key text, fingerprint text, expected_version integer)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  application uuid;
  current_version integer;
  current_state text;
  reference text;
  slug text;
  clean_count integer;
  waived boolean;
  existing_fp text;
  existing_ref text;
  digest text;
BEGIN
  SELECT capability.organization_id, capability.application_id INTO org, application
  FROM application_capabilities capability
  WHERE capability.token_hash = submit_application.token_hash AND capability.revoked = false AND capability.expires_at > now();
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT application_intake_keys.fingerprint, application_intake_keys.public_reference INTO existing_fp, existing_ref
  FROM application_intake_keys
  WHERE organization_id = org AND application_intake_keys.idempotency_key = submit_application.idempotency_key;
  IF existing_fp IS NOT NULL THEN
    IF existing_fp <> fingerprint THEN
      RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
    END IF;
    RETURN jsonb_build_object('accepted', true, 'reference', existing_ref, 'replayed', true, 'state', 'submitted');
  END IF;
  SELECT version, state, public_reference, listing_slug INTO current_version, current_state, reference, slug
  FROM applications WHERE organization_id = org AND id = application FOR UPDATE;
  IF current_state <> 'draft' OR current_version <> expected_version THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM discovery_projections
    WHERE public_slug = slug AND current AND eligibility = 'eligible'
  ) THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'unavailable');
  END IF;
  SELECT count(*) INTO clean_count FROM application_documents
  WHERE organization_id = org AND application_id = application AND scan_state = 'clean';
  SELECT EXISTS (
    SELECT 1 FROM application_answers
    WHERE organization_id = org AND application_id = application AND field_code = 'income_status' AND field_value = 'not_applicable'
  ) INTO waived;
  IF clean_count < 1 AND NOT waived THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'incomplete');
  END IF;
  digest := md5(reference || ':' || current_version::text || ':' || clean_count::text);
  INSERT INTO application_submissions (organization_id, id, application_id, snapshot_hash)
  VALUES (org, gen_random_uuid(), application, digest);
  UPDATE applications SET state = 'submitted', version = version + 1 WHERE organization_id = org AND id = application;
  UPDATE application_participants SET attested = true
  WHERE organization_id = org AND application_id = application AND role_name = 'primary';
  INSERT INTO application_events (organization_id, id, application_id, event_kind)
  VALUES (org, gen_random_uuid(), application, 'submitted');
  INSERT INTO application_intake_keys (organization_id, idempotency_key, fingerprint, public_reference)
  VALUES (org, submit_application.idempotency_key, fingerprint, reference);
  RETURN jsonb_build_object('accepted', true, 'reference', reference, 'replayed', false, 'state', 'submitted', 'snapshot_hash', digest);
END $$;

REVOKE ALL ON FUNCTION perchpoint.start_application(jsonb, text, text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.save_application_answer(text, text, text, integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.finalize_application_document(text, text, text, text, integer, text, boolean) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.submit_application(text, text, text, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.start_application(jsonb, text, text, text) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.save_application_answer(text, text, text, integer) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.finalize_application_document(text, text, text, text, integer, text, boolean) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.submit_application(text, text, text, integer) TO perchpoint_runtime, perchpoint_definer;
ALTER FUNCTION perchpoint.start_application(jsonb, text, text, text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.save_application_answer(text, text, text, integer) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.finalize_application_document(text, text, text, text, integer, text, boolean) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.submit_application(text, text, text, integer) OWNER TO perchpoint_definer;

CREATE FUNCTION perchpoint.withdraw_application(token_hash text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  application uuid;
  current_state text;
  reference text;
BEGIN
  SELECT capability.organization_id, capability.application_id INTO org, application
  FROM application_capabilities capability
  WHERE capability.token_hash = withdraw_application.token_hash AND capability.revoked = false AND capability.expires_at > now();
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT state, public_reference INTO current_state, reference FROM applications
  WHERE organization_id = org AND id = application FOR UPDATE;
  IF current_state NOT IN ('draft', 'submitted') THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
  END IF;
  UPDATE applications SET state = 'withdrawn', version = version + 1 WHERE organization_id = org AND id = application;
  INSERT INTO application_events (organization_id, id, application_id, event_kind)
  VALUES (org, gen_random_uuid(), application, 'withdrawn');
  RETURN jsonb_build_object('accepted', true, 'reference', reference, 'state', 'withdrawn');
END $$;

CREATE FUNCTION perchpoint.invite_application_participant(token_hash text, role_name text, destination_email text, invite_hash text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  application uuid;
BEGIN
  IF role_name = 'minor_occupant' OR role_name NOT IN ('co_applicant', 'adult_occupant', 'guarantor', 'representative') THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT capability.organization_id, capability.application_id INTO org, application
  FROM application_capabilities capability
  WHERE capability.token_hash = invite_application_participant.token_hash AND capability.revoked = false AND capability.expires_at > now();
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  INSERT INTO application_invitations (organization_id, id, application_id, role_name, token_hash, destination_email, state, expires_at)
  VALUES (org, gen_random_uuid(), application, role_name, invite_hash, destination_email, 'pending', now() + interval '2 days');
  RETURN jsonb_build_object('accepted', true, 'state', 'pending');
END $$;

REVOKE ALL ON FUNCTION perchpoint.withdraw_application(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.invite_application_participant(text, text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.withdraw_application(text) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.invite_application_participant(text, text, text, text) TO perchpoint_runtime, perchpoint_definer;
ALTER FUNCTION perchpoint.withdraw_application(text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.invite_application_participant(text, text, text, text) OWNER TO perchpoint_definer;
