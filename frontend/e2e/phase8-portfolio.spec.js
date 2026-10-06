const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

for (const width of [320, 768, 1024, 1440]) {
  test(`portfolio administration stays usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/perchpoint/operations/listing-administration");
    await expect(page.getByRole("heading", { name: "Portfolio administration" })).toBeVisible();
    await page.getByRole("textbox", { name: "Space reference" }).fill("synthetic-space");
    await page.getByRole("textbox", { name: "Amount in cents" }).fill("150000");
    const reason = page.getByRole("textbox", { name: "Reason" });
    await reason.fill("Synthetic routine review.");
    await reason.focus();
    await expect(reason).toBeFocused();
    await page.getByRole("button", { name: "Review on the server" }).click();
    await expect(page.getByRole("status")).toContainText("server");
    const results = await new AxeBuilder({ page }).include("#main").analyze();
    expect(results.violations).toEqual([]);
  });
}
