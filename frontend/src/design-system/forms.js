/** Maps backend outcomes into field, form, and recovery states. It does not invent a second domain schema. */

export function adaptOutcome(status, body = {}) {
  const message = body.detail?.message || body.message || "The request was not accepted.";
  if (status === 409) {
    return { kind: "conflict", message: "This record changed. Reload it and try again.", retryable: true, fields: {} };
  }
  if (status === 401) return { kind: "signed-out", message: "Sign in again to continue.", retryable: false, fields: {} };
  if (status === 403) return { kind: "denied", message: "You do not have access to that action.", retryable: false, fields: {} };
  if (status === 404) return { kind: "missing", message: "That record was not found.", retryable: false, fields: {} };
  if (status === 422 || status === 400) {
    return { kind: "invalid", message, retryable: false, fields: body.fields || {} };
  }
  if (status === 429) return { kind: "rate-limited", message: "Too many requests were sent. Wait and try again.", retryable: true, fields: {} };
  if (status >= 500 || status === 0) return { kind: "unavailable", message: "That action is unavailable right now.", retryable: true, fields: {} };
  return { kind: "saved", message: "Saved.", retryable: false, fields: {} };
}
