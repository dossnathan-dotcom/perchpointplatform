const { test, expect } = require("@playwright/test");

async function settle(page, path) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addStyleTag({ content: "*, *::before, *::after { animation: none !important; caret-color: transparent !important; transition: none !important; }" });
  if (path.includes("/perchpoint/")) await expect(page.getByTestId("portal-active-page-title")).toBeVisible();
  else if (path.includes("/design-system")) await expect(page.getByTestId("component-laboratory")).toBeVisible();
  else await expect(page.getByTestId("public-hero")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

async function shot(page, name) {
  await expect(page).toHaveScreenshot(`${name}.png`, { animations: "disabled" });
}

const pages = [
  ["public-home-desktop", "/", 1440, 900],
  ["public-home-mobile", "/", 390, 844],
  ["rental-discovery", "/#rentals", 1280, 900],
  ["applicant-shell", "/perchpoint/applicant", 1280, 900],
  ["resident-shell", "/perchpoint/resident", 1280, 900],
  ["operations-shell", "/perchpoint/leasing", 1440, 900],
  ["maintenance-recommendation", "/perchpoint/maintenance/recommendations", 1280, 900],
  ["accounting-shell", "/perchpoint/accounting", 1280, 900],
  ["vendor-mobile", "/perchpoint/subcontractor", 390, 844],
  ["owner-command", "/perchpoint/owner", 1440, 900],
  ["platform-admin", "/perchpoint/super-admin", 1440, 900],
  ["component-laboratory", "/design-system", 1280, 900],
  ["public-320", "/", 320, 700],
  ["portal-768", "/perchpoint/owner", 768, 900],
];

for (const [name, path, width, height] of pages) {
  test(name, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await page.goto(path);
    await settle(page, path);
    if (path.includes("#")) await page.locator(path.slice(path.indexOf("#"))).scrollIntoViewIfNeeded();
    await shot(page, name);
  });
}

test("listing-detail", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/");
  await settle(page, "/");
  await page.getByTestId("public-listing-card").first().getByRole("link", { name: /View this listing/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await shot(page, "listing-detail");
});

test("internal-light-comfortable", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("pp-theme", "light");
    localStorage.setItem("pp-density", "comfortable");
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/perchpoint/accounting");
  await settle(page, "/perchpoint/accounting");
  await shot(page, "accounting-light-comfortable");
});

test("internal-dark-compact", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("pp-theme", "dark");
    localStorage.setItem("pp-density", "compact");
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/perchpoint/owner");
  await settle(page, "/perchpoint/owner");
  await shot(page, "owner-dark-compact");
});

for (const state of ["loading", "empty", "error", "denied", "conflict"]) {
  test(`owner-${state}`, async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/perchpoint/owner");
    await settle(page, "/perchpoint/owner");
    await page.getByTestId("portal-state-select").selectOption(state);
    await expect(page.getByTestId(`portal-state-${state}`)).toBeVisible();
    await shot(page, `owner-${state}`);
  });
}
