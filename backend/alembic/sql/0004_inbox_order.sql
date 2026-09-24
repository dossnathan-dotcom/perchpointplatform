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
  SELECT max((payload->>'aggregate_version')::integer) INTO current_version
  FROM inbox
  WHERE organization_id = p_org AND provider = p_provider AND account_name = p_account
    AND environment = p_environment AND disposition = 'applied';
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
GRANT EXECUTE ON FUNCTION perchpoint.accept_inbox(uuid, text, text, text, text, jsonb, integer) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.accept_inbox(uuid, text, text, text, text, jsonb, integer) TO perchpoint_definer;
