-- Reapply worker-assignment property visibility.
-- Databases that applied an earlier property policy still hide or widen technician
-- access until this forward migration replaces that policy.

DROP POLICY IF EXISTS property_capability_scope ON properties;
CREATE POLICY property_capability_scope ON properties
  USING (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.authorized_for('property.read', 'property', id)
      OR perchpoint.worker_assignment_allows(NULL, id)
    )
  )
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.authorized_for('property.manage', 'property', id));

DROP POLICY IF EXISTS building_capability_scope ON buildings;
CREATE POLICY building_capability_scope ON buildings
  USING (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.authorized_for('property.read', 'property', property_id)
      OR perchpoint.worker_assignment_allows(NULL, property_id)
    )
  )
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.authorized_for('property.manage', 'property', property_id));

DROP POLICY IF EXISTS space_capability_scope ON spaces;
CREATE POLICY space_capability_scope ON spaces
  USING (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.authorized_for('property.read', 'property', property_id)
      OR perchpoint.worker_assignment_allows(NULL, property_id)
    )
  )
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.authorized_for('property.manage', 'property', property_id));
