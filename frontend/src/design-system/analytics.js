/** Provider-neutral analytics boundary. The implementation is a no-op. Session replay is not available. */

export const SESSION_REPLAY_ENABLED = false;

export const ALLOWED_CATEGORIES = [
  "public_navigation",
  "listing_viewed",
  "inquiry_started",
  "inquiry_submitted",
  "portal_navigation",
  "feature_unavailable",
  "validation_failure",
  "performance_metric",
];

const FORBIDDEN = /name|email|phone|address|lease|payment|screen|token|message|instruction|ssn|account/i;

export function track(category, payload = {}) {
  if (!ALLOWED_CATEGORIES.includes(category)) return { accepted: false, reason: "category" };
  const keys = Object.keys(payload);
  if (keys.some((key) => FORBIDDEN.test(key) || FORBIDDEN.test(String(payload[key])))) {
    return { accepted: false, reason: "sensitive" };
  }
  return { accepted: true, delivered: false };
}
