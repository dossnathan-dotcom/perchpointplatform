# Sentry

GitHub integration: Nathan reported that Sentry is integrated with GitHub. This repository does not contain a DSN, an auth token, or a recorded live event.

Runtime: the API and worker call `init_sentry` only when `SENTRY_DSN` is set and is not a placeholder or a local URL in staging or production. The browser calls `startSentry` only when `REACT_APP_SENTRY_DSN` passes the same kind of check. PII, replay, and request bodies stay off. A missing SDK or a Sentry outage does not fail startup or health checks.

Later source-map upload needs `SENTRY_AUTH_TOKEN` in a GitHub environment. That workflow is not active. Do not put the token in a `REACT_APP_` variable.

Alerts, when a DSN exists, go to Nathan first. Live-alert acceptance is a received staging event with secrets redacted. That evidence is owner-deferred.
