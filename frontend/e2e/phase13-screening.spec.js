const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

for (const width of [320, 768, 1024, 1440]) {
  test(`screening review stays usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/screening");
    await expect(page.getByRole("heading", { name: "Screening review" })).toBeVisible();
    const reference = page.getByRole("textbox", { name: "Application reference" });
    await reference.fill("synthetic-reference");
    await reference.focus();
    await expect(reference).toBeFocused();
    await page.getByRole("button", { name: "Review case" }).click();
    await expect(page.getByText(/could not be accepted|authorized person/)).toBeVisible();
    const results = await new AxeBuilder({ page }).include("#main").analyze();
    expect(results.violations).toEqual([]);
  });
}
