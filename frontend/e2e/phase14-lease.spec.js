const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

for (const width of [320, 768, 1024, 1440]) {
  test(`lease preparation stays usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/leases");
    await expect(page.getByRole("heading", { name: "Lease preparation" })).toBeVisible();
    const reference = page.getByRole("textbox", { name: "Screening reference" });
    await reference.fill("synthetic-reference");
    await reference.focus();
    await expect(reference).toBeFocused();
    await page.getByRole("button", { name: "Prepare lease" }).click();
    await expect(page.getByText(/could not be accepted|approves the lease/)).toBeVisible();
    const results = await new AxeBuilder({ page }).include("#main").analyze();
    expect(results.violations).toEqual([]);
  });
}
