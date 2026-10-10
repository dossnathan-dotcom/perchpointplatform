const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

for (const width of [320, 768, 1024, 1440]) {
  test(`resident ledger stays usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/ledger");
    await expect(page.getByRole("heading", { name: "Resident ledger" })).toBeVisible();
    await expect(page.getByText("SYNTHETIC OPERATIONAL STATEMENT — NOT A TAX RETURN — NOT A FORMAL GENERAL LEDGER")).toBeVisible();
    await expect(page.getByRole("table")).toBeVisible();
    const reference = page.getByRole("textbox", { name: "Household reference" });
    await reference.fill("synthetic-reference");
    await reference.focus();
    await expect(reference).toBeFocused();
    await page.getByRole("button", { name: "Post charge" }).click();
    await expect(page.getByText(/could not be accepted|cannot type an authoritative balance/)).toBeVisible();
    const results = await new AxeBuilder({ page }).include("#main").analyze();
    expect(results.violations).toEqual([]);
  });
}
