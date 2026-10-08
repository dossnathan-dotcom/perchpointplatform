const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

for (const width of [320, 768, 1024, 1440]) {
  test(`showing times stay usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/showings");
    await expect(page.getByRole("heading", { name: "Schedule a showing" })).toBeVisible();
    const receipt = page.getByRole("textbox", { name: "Showing receipt" });
    await receipt.fill("synthetic-receipt");
    await receipt.focus();
    await expect(receipt).toBeFocused();
    await page.getByRole("button", { name: "Show times" }).click();
    await expect(page.getByText(/could not be accepted|temporarily unavailable|America\/New_York|No open time/)).toBeVisible();
    const results = await new AxeBuilder({ page }).include("#main").analyze();
    expect(results.violations).toEqual([]);
  });
}
