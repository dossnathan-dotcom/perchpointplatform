# Information architecture

Public routes remain `/`, `/rentals/:listingId`, and `/property/:propertyId`.

Authenticated previews remain `/perchpoint/:roleId/:viewId`. The role in the URL is a preview label. It is not authorization.

Unknown roles and unknown views render the unavailable workspace. Extra path segments render the not-found page.

Context, theme, and density preferences store only those UI values. Canonical search is feature-flagged off until Phase 5. The command palette states that limitation.

Breadcrumbs are reserved for later hierarchical records. Public and resident pages do not use them.
