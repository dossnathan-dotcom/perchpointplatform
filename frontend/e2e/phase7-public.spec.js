const { test, expect } = require("@playwright/test");

test("visitors can read published pages and recover from a missing address", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByTestId("about-page")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("About");
  await expect(page.getByText("9999")).toHaveCount(0);
  await page.goto("/maintenance");
  await expect(page.getByTestId("maintenance-page")).toContainText("not an emergency-monitored channel");
  await page.goto("/apply");
  await expect(page.getByTestId("apply-guide")).toContainText("not a complete application");
  await page.goto("/contact");
  await expect(page.getByTestId("contact-page")).toBeVisible();
  await page.goto("/missing-public-page");
  await expect(page.getByTestId("not-found-page")).toBeVisible();
  await page.getByTestId("not-found-home-link").click();
  await expect(page).toHaveURL(/\/$/);
});
