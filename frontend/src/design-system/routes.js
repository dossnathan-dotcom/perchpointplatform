/** Presentation route registry. It does not authorize access. */

export const CANONICAL_SEARCH_ENABLED = false;

const surfaces = [
  ["public-home", "public", "/", "HawkVision Homes", null, "public", "none", false, false, false, false, true],
  ["public-rentals", "public", "/rentals/:listingId", "Rental", "public-home", "public", "property", false, false, false, false, true],
  ["public-property", "public", "/property/:propertyId", "Property", "public-home", "public", "property", false, false, false, false, true],
  ["applicant-overview", "applicant", "/perchpoint/applicant", "Overview", null, "applicant", "none", false, false, true, true, false],
  ["resident-home", "resident", "/perchpoint/resident", "Home", null, "resident", "household", false, false, true, true, false],
  ["leasing-today", "leasing", "/perchpoint/leasing", "Today", null, "leasing", "portfolio", true, false, false, false, false],
  ["maintenance-triage", "maintenance", "/perchpoint/maintenance", "Triage", null, "maintenance", "assignment", true, false, true, false, false],
  ["accounting-overview", "accounting", "/perchpoint/accounting", "Overview", null, "accounting", "portfolio", true, false, false, false, false],
  ["vendor-assignments", "vendor", "/perchpoint/subcontractor", "Assignments", null, "vendor", "assignment", false, false, true, true, false],
  ["owner-today", "owner", "/perchpoint/owner", "Today", null, "owner", "portfolio", true, true, false, false, false],
  ["platform-organizations", "platform-admin", "/perchpoint/super-admin", "Organizations", null, "platform-admin", "organization", true, false, false, false, false],
  ["foundation", "reference", "/foundation", "Foundation", null, "staff", "none", false, false, false, false, false],
  ["reference-kernel", "reference", "/reference", "Reference operations", null, "staff", "none", false, false, false, false, false],
];

export const ROUTES = surfaces.map(([id, surface, path, label, parent, group, context, breadcrumb, search, preview, mobile, indexable]) => ({
  id,
  surface,
  path,
  label,
  parent,
  group,
  capability: "presentation-only",
  context,
  breadcrumb,
  searchVisible: search && CANONICAL_SEARCH_ENABLED,
  featureFlag: search ? "phase5-canonical-search" : null,
  previewOnly: preview,
  mobilePriority: mobile,
  analytics: indexable ? "public_navigation" : "portal_navigation",
}));

export function routeById(id) {
  return ROUTES.find((route) => route.id === id) || null;
}

export function privilegedFallback(roleId) {
  const known = ["owner", "super-admin", "leasing", "accounting", "maintenance", "subcontractor", "resident", "applicant"];
  return known.includes(roleId) ? roleId : null;
}
