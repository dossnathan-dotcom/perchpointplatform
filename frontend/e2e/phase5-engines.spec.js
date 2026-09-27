const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

const password = process.env.PHASE2_DEV_PASSWORD;

test("phase 5 centers sign in, announce status, and stay inside the viewport", async ({ page }) => {
  await page.goto("/perchpoint/leasing/phase5/documents");
  await expect(page.getByTestId("phase5-title")).toHaveText("Document Center");
  await page.locator("input[name='phase5-email']").fill("ann.synthetic@example.com");
  await page.locator("input[name='phase5-password']").fill(password);
  await page.getByTestId("phase5-sign-in").click();
  await expect(page.getByTestId("phase5-status")).toContainText(/Signed in|denied|did not respond|records/);
  await page.getByTestId("phase5-nav-quality").click();
  await expect(page.getByTestId("phase5-title")).toHaveText("Data Quality Center");
  await page.getByTestId("phase5-nav-imports").click();
  await expect(page.getByTestId("phase5-title")).toHaveText("Import Reconciliation");
  await page.getByTestId("phase5-nav-audit").click();
  await expect(page.getByTestId("phase5-title")).toHaveText("Audit Explorer");
  await page.getByTestId("phase5-nav-saved").click();
  await expect(page.getByTestId("phase5-saved-query")).toBeVisible();
  await page.keyboard.press("Tab");
  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  }
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter((item) => ["critical", "serious"].includes(item.impact));
  expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
});

test("applicant phase 5 route stays unavailable", async ({ page }) => {
  await page.goto("/perchpoint/applicant/phase5/documents");
  await expect(page.getByTestId("phase5-denied")).toBeVisible();
});
