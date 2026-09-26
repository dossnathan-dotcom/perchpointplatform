# Design system

HawkVision Homes is the public brand. PerchPoint is the product name inside authenticated shells. The active organization shown there is HawkVision Homes.

Tokens live in `frontend/src/design-system/tokens.js` and are exposed as `--pp-*` custom properties in `frontend/src/index.css`. Tailwind brand colors reference those variables.

Two font stacks are used, both local to the operating system: a display serif (`Iowan Old Style`, Palatino) and an operational sans (`Segoe UI`, `system-ui`). No remote font host is loaded. No third font family is shipped.

Public pages use the fixed `hawkvision` theme. Internal pages default to dark, and can switch to light or the system preference. Density is comfortable or compact. Only `pp-theme` and `pp-density` are stored.

Shared components live in `frontend/src/design-system/components.jsx`. The laboratory is `/design-system` in local and CI development servers and is omitted from the production route tree.

Status, money, operational time (`America/New_York`), addresses, tables, owner decisions, and maintenance recommendations use those components. Disabled actions say the workflow is unavailable. They do not pretend a payment, application, lease, or approval was processed.
