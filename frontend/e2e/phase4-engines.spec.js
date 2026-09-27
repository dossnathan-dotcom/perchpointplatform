const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

const widths = [320, 375, 480, 768, 1024, 1280, 1440, 1920];
const shells = [
  ["/", "public"],
  ["/perchpoint/applicant", "applicant"],
  ["/perchpoint/resident", "resident"],
  ["/perchpoint/maintenance", "maintenance"],
  ["/perchpoint/subcontractor", "vendor"],
  ["/perchpoint/accounting", "accounting"],
  ["/perchpoint/owner", "owner"],
  ["/perchpoint/super-admin", "platform"],
];

async function noDocumentOverflow(page) {
  const box = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    client: document.documentElement.clientWidth,
  }));
  expect(box.scroll).toBeLessThanOrEqual(box.client + 1);
}

test("public homepage, discovery, listing, and inquiry", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Rentals" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Commercial" })).toBeVisible();
  await expect(page.getByTestId("nav-resident-login")).toBeVisible();
  await expect(page.getByTestId("nav-staff-login")).toBeVisible();
  await page.goto("/#rentals");
  const card = page.getByTestId("public-listing-card").first();
  await expect(card).toContainText("Example Elm Court");
  const listingLink = card.getByRole("link", { name: /View this listing/ });
  await listingLink.scrollIntoViewIfNeeded();
  await listingLink.click();
  if (!/\/rentals\//.test(page.url())) {
    await listingLink.click();
  }
  await expect(page).toHaveURL(/\/rentals\//);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Example Elm Court");
  await page.locator("input[name='guest-name']").fill("Engine Guest");
  await page.locator("input[name='guest-email']").fill("engine-guest@example.com");
  await page.locator("textarea[name='guest-message']").fill("Engine showing request");
  await page.getByTestId("public-inquiry-submit").click();
  await expect(page.getByTestId("public-inquiry-status")).toContainText("Inquiry received");
});

test("role shells expose approved destinations and synthetic boundary", async ({ page }) => {
  const expectations = [
    ["/perchpoint/applicant/household", "Household"],
    ["/perchpoint/applicant/status", "Status"],
    ["/perchpoint/resident/lease", "Lease"],
    ["/perchpoint/resident/messages", "Messages"],
    ["/perchpoint/leasing/leasing", "Leasing"],
    ["/perchpoint/maintenance/work-orders", "Work Orders"],
    ["/perchpoint/maintenance/parts-purchases", "Parts/Purchases"],
    ["/perchpoint/accounting/resident-ledgers", "Resident Ledgers"],
    ["/perchpoint/subcontractor/property-access", "Property Access"],
    ["/perchpoint/owner/financial-position", "Financial Position"],
    ["/perchpoint/super-admin/feature-flags", "Feature Flags"],
  ];
  for (const [path, title] of expectations) {
    await page.goto(path);
    await expect(page.getByTestId("portal-active-page-title")).toHaveText(title);
    await expect(page.getByTestId("synthetic-workflow-boundary")).toContainText("does not submit");
  }
});

test("dialog keyboard, theme, and density", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("nav-resident-login").click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.goto("/perchpoint/owner");
  await page.getByTestId("portal-theme-select").selectOption("light");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByTestId("portal-density-select").selectOption("compact");
  await expect(page.locator("html")).toHaveAttribute("data-density", "compact");
  await page.getByTestId("portal-notifications-btn").click();
  await expect(page.getByTestId("notification-example")).toContainText("Category: Maintenance");
  await expect(page.getByTestId("portal-context-summary")).toContainText("HawkVision Homes");
});

test("responsive widths, portrait, and landscape", async ({ page }) => {
  test.setTimeout(180000);
  for (const [path] of shells) {
    for (const width of widths) {
      await page.setViewportSize({ width, height: width < 800 ? 800 : 900 });
      await page.goto(path);
      await noDocumentOverflow(page);
    }
  }
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/perchpoint/resident");
  await noDocumentOverflow(page);
  await page.setViewportSize({ width: 812, height: 375 });
  await page.goto("/perchpoint/subcontractor");
  await noDocumentOverflow(page);
});

test("zoom reflow at 200 and 400 percent layout viewports", async ({ page }) => {
  await page.setViewportSize({ width: 640, height: 400 });
  await page.goto("/perchpoint/resident");
  await noDocumentOverflow(page);
  await expect(page.getByTestId("portal-active-page-title")).toBeVisible();
  await page.setViewportSize({ width: 320, height: 256 });
  await page.goto("/perchpoint/owner");
  await noDocumentOverflow(page);
  await expect(page.getByTestId("owner-decision-card")).toBeVisible();
});

test("forced colors and reduced motion keep controls available", async ({ page, browserName }) => {
  await page.emulateMedia({ reducedMotion: "reduce", forcedColors: "active" });
  await page.goto("/");
  await expect(page.getByTestId("hero-browse-rentals-btn")).toBeVisible();
  await page.goto("/perchpoint/maintenance/recommendations");
  await expect(page.getByRole("heading", { name: "Worker recommendation" })).toBeVisible();
  if (browserName === "chromium") {
    const results = await new AxeBuilder({ page }).disableRules(["color-contrast"]).analyze();
    const serious = results.violations.filter((item) => ["critical", "serious", "moderate"].includes(item.impact));
    expect(serious).toEqual([]);
  }
});

test("accessibility tree exposes language, landmarks, and names", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page).toHaveTitle(/HawkVision Homes/);
  const tree = await page.locator("body").ariaSnapshot();
  expect(tree).toContain("Rentals");
  expect(tree).toContain("main");
  await page.goto("/perchpoint/owner");
  const owner = await page.locator("main").ariaSnapshot();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("public hero paints without listings or a session", async ({ page }) => {
  const requests = [];
  let releaseListings = () => {};
  const pending = new Promise((resolve) => { releaseListings = resolve; });
  page.on("request", (request) => requests.push(request.url()));
  await page.route("**/api/v2/listings", async (route) => {
    await pending;
    await route.fulfill({ status: 200, contentType: "application/json", body: "{\"listings\":[]}" });
  });
  await page.goto("/");
  await expect(page.getByTestId("hero-active-heading")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
  expect(requests.some((url) => url.includes("/session"))).toBe(false);
  releaseListings();
});

test("listing failure keeps the public shell", async ({ page }) => {
  await page.route("**/api/v2/listings", (route) => route.fulfill({ status: 500, contentType: "application/json", body: "{}" }));
  await page.goto("/");
  await expect(page.getByTestId("hero-active-heading")).toBeVisible();
  await expect(page.getByText("Listings are unavailable.")).toBeVisible();
});

test("api content security policy rejects inline styles", async ({ request }) => {
  const response = await request.get("http://127.0.0.1:8000/api/v2/health/live");
  const policy = response.headers()["content-security-policy"];
  expect(policy).toContain("style-src 'self'");
  expect(policy).toContain("style-src-attr 'none'");
  expect(policy).not.toContain("unsafe-inline");
  expect(policy).not.toContain("unsafe-eval");
  expect(policy).toContain("frame-ancestors 'none'");
});
