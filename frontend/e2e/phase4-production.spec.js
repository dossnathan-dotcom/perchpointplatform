const { test, expect } = require("@playwright/test");

test("production shell enforces CSP, fonts, images, and the owner preview", async ({ page }) => {
  const violations = [];
  page.on("console", (message) => {
    if (message.text().includes("Content Security Policy")) violations.push(message.text());
  });
  const home = await page.goto("/");
  expect(home.headers()["content-security-policy"]).toContain("style-src-attr 'none'");
  expect(home.headers()["content-security-policy"]).not.toContain("unsafe-inline");
  expect(home.headers()["x-frame-options"]).toBe("DENY");
  await expect(page.getByRole("link", { name: "Rentals" })).toBeVisible();
  const font = await page.request.get("/fonts/source-sans-3-400.woff2");
  expect(font.status()).toBe(200);
  const image = await page.request.get("/media/hero.avif");
  expect(image.status()).toBe(200);
  const listings = await page.request.get("/api/v2/listings");
  expect(listings.status()).toBe(200);
  const listingId = (await listings.json()).listings[0].listing_id;
  const inquiry = await page.request.post("/api/v2/inquiries", {
    data: {
      listing_id: listingId,
      name: "Docker Guest",
      email: "docker-guest@example.com",
      intent: "showing",
      message: "Docker smoke inquiry",
      idempotency_key: `docker-smoke-${Date.now()}`,
      company_website: "",
    },
  });
  expect(inquiry.status()).toBe(201);
  await page.goto("/perchpoint/owner");
  await expect(page.getByTestId("portal-active-page-title")).toHaveText("Today");
  await expect(page.getByTestId("synthetic-workflow-boundary")).toBeVisible();
  expect(violations).toEqual([]);
});
