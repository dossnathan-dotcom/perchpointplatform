const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

for (const width of [320, 768, 1024, 1440]) {
  test(`leasing inquiry stays usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/rentals");
    await expect(page.getByRole("heading", { name: "Rentals" })).toBeVisible();
    const name = page.getByRole("textbox", { name: "Name" });
    await name.fill("Casey Synthetic");
    await name.focus();
    await expect(name).toBeFocused();
    await page.getByRole("textbox", { name: "Email" }).fill("casey.synthetic@example.com");
    await page.getByRole("textbox", { name: "Message" }).fill("Synthetic interest in a HawkVision home.");
    await page.getByRole("checkbox", { name: /use this message to respond/ }).check();
    await page.getByRole("button", { name: "Send inquiry" }).click();
    await expect(page.getByText(/Inquiry received|could not be accepted|temporarily unavailable/)).toBeVisible();
    const results = await new AxeBuilder({ page }).include("#main").analyze();
    expect(results.violations).toEqual([]);
    await page.goto("/leasing-desk");
    await expect(page.getByRole("heading", { name: "Leasing queue" })).toBeVisible();
    await page.getByRole("button", { name: "Refresh queue" }).focus();
    await expect(page.getByRole("button", { name: "Refresh queue" })).toBeFocused();
    await page.getByRole("button", { name: "Refresh queue" }).click();
    await expect(page.getByText(/not available for the current session|temporarily unavailable|No open inquiries|Loading the queue/)).toBeVisible();
  });
}
