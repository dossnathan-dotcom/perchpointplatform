/** Authoritative Phase 4 tokens. CSS custom properties in index.css must match these names. */

export const brand = {
  obsidian: "#0d1117",
  obsidianCard: "#161b22",
  linen: "#faf8f5",
  copper: "#a64b23",
  copperDark: "#873c1b",
  gold: "#f2ad78",
};

export const semantic = {
  text: "var(--pp-text)",
  textMuted: "var(--pp-text-muted)",
  surface: "var(--pp-surface)",
  surfaceRaised: "var(--pp-surface-raised)",
  border: "var(--pp-border)",
  focus: "var(--pp-focus)",
  danger: "var(--pp-danger)",
  success: "var(--pp-success)",
  warning: "var(--pp-warning)",
};

export const spacing = [0, 4, 8, 12, 16, 24, 32, 40, 48, 64, 80];

export const radius = { none: "0px", sm: "2px", md: "4px", lg: "8px" };

export const elevation = {
  none: "none",
  raised: "0 1px 2px rgb(13 17 23 / 0.12)",
};

export const breakpoints = [320, 480, 768, 1024, 1280, 1440, 1920];

export const zIndex = { base: 0, sticky: 20, overlay: 40, dialog: 50 };

export const density = {
  comfortable: { control: 44, page: 32 },
  compact: { control: 36, page: 16 },
};

export const fontFamilies = {
  display: '"Iowan Old Style", "Palatino Linotype", Palatino, serif',
  operational: '"Segoe UI", system-ui, sans-serif',
};

export const requiredCssVariables = [
  "--pp-text",
  "--pp-text-muted",
  "--pp-surface",
  "--pp-surface-raised",
  "--pp-border",
  "--pp-focus",
  "--pp-danger",
  "--pp-success",
  "--pp-warning",
  "--pp-obsidian",
  "--pp-linen",
  "--pp-copper",
  "--pp-gold",
];

function channel(hex) {
  const value = hex.replace("#", "");
  return [0, 2, 4].map((index) => parseInt(value.slice(index, index + 2), 16) / 255);
}

function luminance(hex) {
  const linear = channel(hex).map((item) => (item <= 0.03928 ? item / 12.92 : ((item + 0.055) / 1.055) ** 2.4));
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

export function contrastRatio(foreground, background) {
  const lighter = Math.max(luminance(foreground), luminance(background));
  const darker = Math.min(luminance(foreground), luminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

export const contrastPairs = [
  [brand.linen, brand.obsidian],
  [brand.obsidian, brand.linen],
  [brand.linen, brand.copper],
  [brand.obsidian, brand.gold],
];
