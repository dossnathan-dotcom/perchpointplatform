export function sentryConfig(env = process.env) {
  const dsn = env.REACT_APP_SENTRY_DSN || "";
  const environment = env.REACT_APP_PHASE3_ENVIRONMENT || "local";
  if (!dsn || dsn.includes("replace-") || dsn.includes("example")) return null;
  if (environment === "production" && (dsn.startsWith("http://") || dsn.includes("localhost"))) return null;
  return {
    dsn,
    environment,
    release: env.REACT_APP_RELEASE || undefined,
    sendDefaultPii: false,
    tracesSampleRate: 0,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
  };
}

export function startSentry() {
  const config = sentryConfig();
  if (!config) return;
  import("@sentry/react")
    .then((Sentry) => Sentry.init(config))
    .catch(() => {});
}
