const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

for (const width of [320, 768, 1024, 1440]) {
  test(`resident household hub stays usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/portal");
    await expect(page.getByRole("heading", { name: "Resident household hub" })).toBeVisible();
    await expect(page.getByText("SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Demo Preview", exact: true })).toBeVisible();
    const reference = page.getByRole("textbox", { name: "Activation reference" });
    await reference.fill("synthetic-reference");
    await reference.focus();
    await expect(reference).toBeFocused();
    await page.getByRole("button", { name: "Open household" }).click();
    await expect(page.getByText(/could not be accepted|opens only after activation/)).toBeVisible();
    const results = await new AxeBuilder({ page }).include("#main").analyze();
    expect(results.violations).toEqual([]);
  });
}
