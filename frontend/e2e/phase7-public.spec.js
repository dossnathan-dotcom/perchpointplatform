const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

test("visitors can read published pages and recover from a missing address", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByTestId("about-page")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("About");
  await expect(page.getByText("9999")).toHaveCount(0);
  await page.goto("/maintenance");
  await expect(page.getByTestId("maintenance-page")).toContainText("not an emergency-monitored channel");
  await page.goto("/apply");
  await expect(page.getByTestId("apply-guide")).toContainText("not a complete application");
  await page.goto("/contact");
  await expect(page.getByTestId("contact-page")).toBeVisible();
  await page.goto("/missing-public-page");
  await expect(page.getByTestId("not-found-page")).toBeVisible();
  await page.getByTestId("not-found-home-link").click();
  await expect(page).toHaveURL(/\/$/);
});

test("public guidance, status pages, and rentals stay reachable", async ({ page }) => {
  for (const [path, testId] of [
    ["/privacy", "privacy-page"],
    ["/terms", "terms-page"],
    ["/faq", "faq-page"],
    ["/resources", "resources-page"],
    ["/rentals", "rentals-index"],
    ["/status/410", "gone-page"],
    ["/status/429", "limited-page"],
    ["/status/503", "unavailable-page"],
    ["/staff/content", "content-studio"],
  ]) {
    await page.goto(path);
    await expect(page.getByTestId(testId)).toBeVisible();
    await expect(page.getByText("9999")).toHaveCount(0);
  }
  await page.goto("/contact");
  await expect(page.getByRole("combobox", { name: "Purpose" })).toBeVisible();
  await page.getByRole("button", { name: "Send" }).focus();
  await expect(page.getByRole("button", { name: "Send" })).toBeFocused();
});

test("published pages have no critical accessibility violations and reflow at narrow widths", async ({ page }) => {
  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/about");
    await expect(page.getByTestId("about-page")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(overflow).toBe(false);
  }
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter((item) => ["critical", "serious"].includes(item.impact));
  expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
});
