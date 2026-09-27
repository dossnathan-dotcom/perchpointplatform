CREATE OR REPLACE FUNCTION perchpoint.search_rows(query text, needle text, prefix text, contains text)
RETURNS TABLE (resource_type text, resource_id uuid, title text, classification text, rank integer)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT resource_type, resource_id, title, classification, max(arm_rank)::integer
  FROM (
    SELECT resource_type, resource_id, title, classification, 100 AS arm_rank
    FROM search_documents
    WHERE organization_id = perchpoint.current_org()
      AND perchpoint.actor_in_org(perchpoint.current_org())
      AND resource_id::text = query
    UNION ALL
    SELECT resource_type, resource_id, title, classification, 80
    FROM search_documents
    WHERE organization_id = perchpoint.current_org()
      AND perchpoint.actor_in_org(perchpoint.current_org())
      AND title ILIKE needle
    UNION ALL
    SELECT resource_type, resource_id, title, classification, 60
    FROM search_documents
    WHERE organization_id = perchpoint.current_org()
      AND perchpoint.actor_in_org(perchpoint.current_org())
      AND title ILIKE prefix
    UNION ALL
    SELECT resource_type, resource_id, title, classification, 40
    FROM search_documents
    WHERE organization_id = perchpoint.current_org()
      AND perchpoint.actor_in_org(perchpoint.current_org())
      AND search_vector @@ websearch_to_tsquery('simple', query)
    UNION ALL
    SELECT resource_type, resource_id, title, classification, 20
    FROM search_documents
    WHERE organization_id = perchpoint.current_org()
      AND perchpoint.actor_in_org(perchpoint.current_org())
      AND title ILIKE contains
  ) matches
  GROUP BY resource_type, resource_id, title, classification
  ORDER BY max(arm_rank) DESC, title
  LIMIT 20
$$;

CREATE OR REPLACE FUNCTION perchpoint.search_facets(query text, needle text, prefix text, contains text)
RETURNS TABLE (resource_type text, total bigint)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT resource_type, count(*)
  FROM (
    SELECT resource_type, resource_id FROM search_documents
    WHERE organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()) AND resource_id::text = query
    UNION
    SELECT resource_type, resource_id FROM search_documents
    WHERE organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()) AND title ILIKE needle
    UNION
    SELECT resource_type, resource_id FROM search_documents
    WHERE organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()) AND title ILIKE prefix
    UNION
    SELECT resource_type, resource_id FROM search_documents
    WHERE organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()) AND search_vector @@ websearch_to_tsquery('simple', query)
    UNION
    SELECT resource_type, resource_id FROM search_documents
    WHERE organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()) AND title ILIKE contains
  ) matches
  GROUP BY resource_type
$$;

REVOKE ALL ON FUNCTION perchpoint.search_rows(text, text, text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.search_facets(text, text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.search_rows(text, text, text, text) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.search_facets(text, text, text, text) TO perchpoint_runtime;
ALTER FUNCTION perchpoint.search_rows(text, text, text, text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.search_facets(text, text, text, text) OWNER TO perchpoint_definer;
