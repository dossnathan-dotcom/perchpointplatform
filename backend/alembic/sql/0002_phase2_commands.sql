GRANT USAGE, CREATE ON SCHEMA perchpoint TO perchpoint_definer;
SET ROLE perchpoint_definer;
DROP FUNCTION IF EXISTS perchpoint.claim_outbox(text);

CREATE FUNCTION perchpoint.claim_outbox(worker text)
RETURNS TABLE (id uuid, organization_id uuid, attempts integer, payload jsonb)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp AS $$
DECLARE claimed record;
BEGIN
  SELECT o.id, o.organization_id, o.attempts, o.payload INTO claimed
  FROM outbox o
  WHERE o.status IN ('pending', 'claimed')
    AND o.available_at <= now()
    AND (o.lease_until IS NULL OR o.lease_until < now())
  ORDER BY o.available_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1;
  IF NOT FOUND THEN
    RETURN;
  END IF;
  IF claimed.attempts >= 5 THEN
    UPDATE outbox SET status = 'dead_letter', last_error = 'attempt limit' WHERE outbox.id = claimed.id;
    RETURN QUERY SELECT claimed.id, claimed.organization_id, claimed.attempts, claimed.payload;
    RETURN;
  END IF;
  UPDATE outbox
    SET status = 'claimed', claimed_by = worker, lease_until = now() + interval '30 seconds', attempts = outbox.attempts + 1
    WHERE outbox.id = claimed.id;
  RETURN QUERY SELECT claimed.id, claimed.organization_id, claimed.attempts + 1, claimed.payload;
END;
$$;

CREATE OR REPLACE FUNCTION perchpoint.accept_inbox(
  p_org uuid,
  p_provider text,
  p_account text,
  p_environment text,
  p_event_id text,
  p_payload jsonb,
  p_version integer
) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp AS $$
DECLARE
  current_version integer;
  inserted uuid;
BEGIN
  SELECT max(version) INTO current_version FROM inquiries WHERE organization_id = p_org;
  IF p_version IS NOT NULL AND current_version IS NOT NULL AND p_version < current_version THEN
    INSERT INTO inbox (organization_id, id, provider, account_name, environment, provider_event_id, payload, disposition, received_at)
    VALUES (p_org, gen_random_uuid(), p_provider, p_account, p_environment, p_event_id, p_payload, 'ignored_stale', now())
    ON CONFLICT (provider, account_name, environment, provider_event_id) DO NOTHING
    RETURNING id INTO inserted;
    IF inserted IS NULL THEN
      RETURN 'duplicate';
    END IF;
    RETURN 'ignored_stale';
  END IF;
  INSERT INTO inbox (organization_id, id, provider, account_name, environment, provider_event_id, payload, disposition, received_at)
  VALUES (p_org, gen_random_uuid(), p_provider, p_account, p_environment, p_event_id, p_payload, 'applied', now())
  ON CONFLICT (provider, account_name, environment, provider_event_id) DO NOTHING
  RETURNING id INTO inserted;
  IF inserted IS NULL THEN
    RETURN 'duplicate';
  END IF;
  RETURN 'applied';
END;
$$;

ALTER FUNCTION perchpoint.claim_outbox(text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.accept_inbox(uuid, text, text, text, text, jsonb, integer) OWNER TO perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.claim_outbox(text) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.accept_inbox(uuid, text, text, text, text, jsonb, integer) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.claim_outbox(text) TO perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.accept_inbox(uuid, text, text, text, text, jsonb, integer) TO perchpoint_definer;
