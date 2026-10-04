const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

const password = process.env.PHASE2_DEV_PASSWORD;

test("unified sign-in keeps the provider credential off the browser", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ann.synthetic@example.com");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("status")).toContainText("Signed in.");
  const stored = await page.evaluate(() => `${JSON.stringify(localStorage)}${JSON.stringify(sessionStorage)}`);
  expect(stored).not.toMatch(/refresh|eyJ|pp_session/i);
  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  }
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter((item) => ["critical", "serious"].includes(item.impact));
  expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
});
