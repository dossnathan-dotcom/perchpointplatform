import { contrastPairs, contrastRatio, requiredCssVariables, spacing } from "./tokens";
import { CANONICAL_SEARCH_ENABLED, ROUTES, privilegedFallback } from "./routes";
import { track } from "./analytics";
import { adaptOutcome } from "./forms";
import { STATE_CATALOGUE } from "./states";
import { applyDocumentTheme, storePreference } from "./theme";

test("semantic tokens meet contrast and spacing rules", () => {
  contrastPairs.forEach(([foreground, background]) => {
    expect(contrastRatio(foreground, background)).toBeGreaterThanOrEqual(4.5);
  });
  expect(new Set(requiredCssVariables).size).toBe(requiredCssVariables.length);
  expect(spacing.every((value, index) => index === 0 || value > spacing[index - 1])).toBe(true);
});

test("route registry does not authorize and keeps search flagged off", () => {
  expect(CANONICAL_SEARCH_ENABLED).toBe(false);
  expect(ROUTES.every((route) => route.capability === "presentation-only")).toBe(true);
  expect(privilegedFallback("not-a-role")).toBeNull();
  expect(privilegedFallback("owner")).toBe("owner");
  expect(ROUTES.some((route) => route.featureFlag === "phase5-canonical-search" && route.searchVisible === false)).toBe(true);
});

test("analytics rejects sensitive payloads and does not deliver events", () => {
  expect(track("listing_viewed", { listing: "public-id" })).toEqual({ accepted: true, delivered: false });
  expect(track("inquiry_submitted", { email: "person@example.com" }).accepted).toBe(false);
  expect(track("session_replay", {}).accepted).toBe(false);
});

test("form adapter preserves conflict and denial meanings", () => {
  expect(adaptOutcome(409, {}).kind).toBe("conflict");
  expect(adaptOutcome(403, {}).kind).toBe("denied");
  expect(adaptOutcome(400, { detail: { message: "Enter a message." } }).kind).toBe("invalid");
});

test("every universal state explains outcome and recovery", () => {
  expect(STATE_CATALOGUE.length).toBe(19);
  STATE_CATALOGUE.forEach((item) => {
    expect(item.happened.length).toBeGreaterThan(5);
    expect(item.saved.length).toBeGreaterThan(2);
    expect(item.next.length).toBeGreaterThan(5);
  });
});

test("theme preferences reject unknown values", () => {
  document.documentElement.removeAttribute("data-theme");
  expect(storePreference("pp-theme", "neon", ["light", "dark", "system"])).toBe(false);
  expect(storePreference("pp-density", "compact", ["comfortable", "compact"])).toBe(true);
  window.history.pushState({}, "", "/");
  expect(applyDocumentTheme("/").theme).toBe("hawkvision");
  window.history.pushState({}, "", "/perchpoint/owner");
  const internal = applyDocumentTheme("/perchpoint/owner");
  expect(internal.theme).toBe("dark");
  expect(internal.density).toBe("compact");
});
