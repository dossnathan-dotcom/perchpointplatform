const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

for (const width of [320, 768, 1024, 1440]) {
  test(`discovery search stays usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/rentals");
    await expect(page.getByRole("heading", { name: "Rentals" })).toBeVisible();
    const city = page.getByRole("textbox", { name: "City" });
    await city.fill("Cincinnati");
    await city.focus();
    await expect(city).toBeFocused();
    await page.getByRole("button", { name: "Search approved listings" }).click();
    await expect(page.getByText(/approved listings match|No listings match|temporarily unavailable/)).toBeVisible();
    const results = await new AxeBuilder({ page }).include("#main").analyze();
    expect(results.violations).toEqual([]);
  });
}
