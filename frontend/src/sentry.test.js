import { sentryConfig } from "./sentry";

test("missing DSN disables Sentry", () => {
  expect(sentryConfig({ REACT_APP_PHASE3_ENVIRONMENT: "local" })).toBeNull();
});

test("production rejects a local DSN", () => {
  expect(sentryConfig({
    REACT_APP_PHASE3_ENVIRONMENT: "production",
    REACT_APP_SENTRY_DSN: "http://localhost/1",
  })).toBeNull();
});

test("a supplied DSN keeps PII and replay disabled", () => {
  const config = sentryConfig({
    REACT_APP_PHASE3_ENVIRONMENT: "local",
    REACT_APP_SENTRY_DSN: "https://public@telemetry.invalid/1",
    REACT_APP_RELEASE: "abc",
  });
  expect(config.sendDefaultPii).toBe(false);
  expect(config.replaysSessionSampleRate).toBe(0);
  expect(config.release).toBe("abc");
});
