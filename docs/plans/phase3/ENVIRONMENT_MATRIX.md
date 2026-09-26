# Environment matrix

| Dimension | Disposition |
|---|---|
| Source and governance integrity | Must pass |
| Phase 3 Q1–Q174 traceability | Must pass |
| Local native development | Must pass |
| Local Docker clean-room | Must pass when Docker is available |
| CI/CD and GitHub security gates | Must pass |
| Container build and security scanning | Must pass |
| Local backup and restore | Must pass |
| Local migration rollback and forward recovery | Must pass |
| Sentry code-level readiness | Must pass without a DSN |
| Sentry live event proof | Owner-deferred until a DSN exists |
| Render hosted staging | Owner-deferred |
| Hosted pull-request preview | Owner-deferred |
| Supabase hosted database | Owner-deferred |
| Hosted PITR | Owner-deferred |
| Hosted backup and restore measurement | Owner-deferred |
| Paid monitoring | Owner-deferred |
| Production deployment | Prohibited |
| Real tenant data | Prohibited |
| Phase 4 implementation | Not part of this assignment |

Local and CI may use disposable credentials. Staging and production startup reject those values, local-development authentication, and unknown environment names. Sentry does not receive events unless a non-placeholder DSN is present, and health checks do not call Sentry.
