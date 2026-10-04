const { test, expect } = require("@playwright/test");

const password = process.env.PHASE2_DEV_PASSWORD;

test("unified sign-in keeps the provider credential off the browser", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ann.synthetic@example.com");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("status")).toContainText("Signed in.");
  const stored = await page.evaluate(() => `${JSON.stringify(localStorage)}${JSON.stringify(sessionStorage)}`);
  expect(stored).not.toMatch(/refresh|eyJ|pp_session/i);
});
