const THEMES = ["light", "dark", "system"];
const DENSITIES = ["comfortable", "compact"];

export function readPreference(key, allowed, fallback) {
  try {
    const value = window.localStorage.getItem(key);
    if (allowed.includes(value)) return value;
  } catch {
    return fallback;
  }
  return fallback;
}

export function storePreference(key, value, allowed) {
  if (!allowed.includes(value)) return false;
  window.localStorage.setItem(key, value);
  return true;
}

export function isInternalPath(pathname) {
  return /^\/(perchpoint|foundation|reference|design-system)(\/|$)/.test(pathname || "");
}

export function resolveTheme(pathname) {
  if (!isInternalPath(pathname)) return "hawkvision";
  const stored = readPreference("pp-theme", THEMES, "dark");
  if (stored !== "system") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyDocumentTheme(pathname) {
  const theme = resolveTheme(pathname);
  const density = readPreference("pp-density", DENSITIES, "comfortable");
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.setAttribute("data-density", density);
  document.documentElement.style.colorScheme = theme === "dark" ? "dark" : "light";
  return { theme, density };
}

export { THEMES, DENSITIES };
