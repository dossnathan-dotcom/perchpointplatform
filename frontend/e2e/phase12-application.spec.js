const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

for (const width of [320, 768, 1024, 1440]) {
  test(`application start stays usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/applications");
    await expect(page.getByRole("heading", { name: "Rental application" })).toBeVisible();
    const receipt = page.getByRole("textbox", { name: "Inquiry receipt" });
    await receipt.fill("synthetic-receipt");
    await receipt.focus();
    await expect(receipt).toBeFocused();
    await page.getByRole("button", { name: "Continue application" }).click();
    await expect(page.getByText(/could not be accepted|temporarily unavailable|draft application was saved|existing application was resumed/)).toBeVisible();
    const results = await new AxeBuilder({ page }).include("#main").analyze();
    expect(results.violations).toEqual([]);
  });
}
