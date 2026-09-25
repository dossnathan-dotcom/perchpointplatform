const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

const password = process.env.PHASE2_DEV_PASSWORD;

async function signIn(page, email) {
  await page.goto("/perchpoint/leasing/operations-console");
  await page.locator("input[name='dev-email']").fill(email);
  await page.locator("input[name='dev-password']").fill(password);
  await page.getByTestId("phase2-sign-in").click();
  await expect(page.getByTestId("phase2-status")).toContainText("Signed in as");
}

test("public listing and inquiry persist without a duplicate", async ({ page, request }) => {
  await page.goto("/");
  const card = page.getByTestId("public-listing-card").first();
  await expect(card).toBeVisible();
  await expect(card).toContainText("Example Elm Court");
  await card.getByRole("link", { name: /View this listing/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Example Elm Court");
  await page.locator("input[name='guest-name']").fill("Browser Guest");
  await page.locator("input[name='guest-email']").fill("browser-guest@example.com");
  await page.locator("textarea[name='guest-message']").fill("Browser showing request");
  await page.getByTestId("public-inquiry-submit").click();
  await expect(page.getByTestId("public-inquiry-status")).toContainText("Inquiry received");
  const first = await page.getByTestId("public-inquiry-status").textContent();
  await page.getByTestId("public-inquiry-submit").click();
  await expect(page.getByTestId("public-inquiry-status")).toHaveText(first);
  const session = await request.post("http://127.0.0.1:8000/api/v2/session", {
    data: { email: "ann.synthetic@example.com", password },
  });
  expect(session.ok()).toBeTruthy();
  const token = (await session.json()).token;
  const queue = await request.get("http://127.0.0.1:8000/api/v2/inquiries", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const inquiries = (await queue.json()).inquiries;
  expect(inquiries.some((item) => item.name === "Browser Guest")).toBeTruthy();
});

test("leasing workspace creates a published space and handles a stale edit", async ({ page }) => {
  const stamp = Date.now().toString().slice(-6);
  await signIn(page, "ann.synthetic@example.com");
  await page.locator("input[name='property-name']").fill(`Browser Court ${stamp}`);
  await page.getByTestId("phase2-save-property").click();
  await expect(page.getByTestId("phase2-status")).toContainText("Property saved");
  await page.locator("input[name='building-name']").fill(`House ${stamp}`);
  await page.getByTestId("phase2-create-building").click();
  await expect(page.getByTestId("phase2-status")).toContainText("Building saved");
  await page.locator("input[name='space-label']").fill(`Unit ${stamp}`);
  await page.getByTestId("phase2-create-space").click();
  await expect(page.getByTestId("phase2-status")).toContainText("space saved");
  await page.getByTestId("phase2-offer-space").click();
  await expect(page.getByTestId("phase2-status")).toContainText("offerable");
  await page.getByTestId("phase2-create-listing").click();
  await expect(page.getByTestId("phase2-status")).toContainText("unpublished");
  await page.getByTestId("phase2-publish").click();
  await expect(page.getByTestId("phase2-status")).toContainText("published");
  await expect(page.getByTestId("phase2-activity")).toContainText("property.created");
  await page.locator("input[name='property-name']").fill(`Browser Court ${stamp} renamed`);
  await page.getByTestId("phase2-save-property").click();
  await expect(page.getByTestId("phase2-status")).toContainText("Property name saved");
  await page.locator("input[name='expected-version']").fill("1");
  await page.locator("input[name='property-name']").fill(`Browser Court ${stamp} stale`);
  await page.getByTestId("phase2-save-property").click();
  await expect(page.getByTestId("phase2-status")).toContainText("changed");
  await page.goto("/");
  await expect(page.getByTestId("public-listing-grid")).toContainText(`Browser Court ${stamp}`);
});

test("inquiry note stays off the public page", async ({ page }) => {
  await signIn(page, "ann.synthetic@example.com");
  await page.getByRole("button", { name: /Browser Guest/ }).first().click();
  await page.getByTestId("phase2-assign").click();
  await expect(page.getByTestId("phase2-status")).toContainText("assigned");
  await page.getByTestId("phase2-triage").click();
  await expect(page.getByTestId("phase2-status")).toContainText("contacted");
  await page.locator("textarea[name='inquiry-note']").fill("Internal callback note");
  await page.getByTestId("phase2-add-note").click();
  await expect(page.getByTestId("phase2-notes")).toContainText("Internal callback note");
  await page.goto("/");
  await expect(page.locator("body")).not.toContainText("Internal callback note");
});

test("preview and expired access do not gain authority", async ({ page }) => {
  await page.goto("/perchpoint/owner");
  await expect(page.getByTestId("owner-preview-boundary")).toBeVisible();
  await expect(page.getByTestId("phase2-sign-in")).toHaveCount(0);
  await page.goto("/perchpoint/leasing/operations-console");
  await expect(page.getByTestId("phase2-save-property")).toHaveCount(0);
  await page.locator("input[name='dev-email']").fill("expired.synthetic@example.com");
  await page.locator("input[name='dev-password']").fill(password);
  await page.getByTestId("phase2-sign-in").click();
  await expect(page.getByTestId("phase2-status")).toContainText("cannot sign in");
  await signIn(page, "isolation.synthetic@example.com");
  await expect(page.getByTestId("phase2-property-list")).not.toContainText("Example Elm Court");
});

test("keyboard submits a public inquiry and assigns an inquiry", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("public-listing-card").first().getByRole("link", { name: /View this listing/ }).click();
  await page.locator("input[name='guest-name']").focus();
  await page.keyboard.type("Keyboard Guest");
  await page.keyboard.press("Tab");
  await page.keyboard.type("keyboard-guest@example.com");
  await page.keyboard.press("Tab");
  await page.keyboard.type("Keyboard showing request");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("public-inquiry-status")).toContainText("Inquiry received");
  await signIn(page, "ann.synthetic@example.com");
  await page.getByRole("button", { name: /Keyboard Guest/ }).first().focus();
  await page.keyboard.press("Enter");
  await page.getByTestId("phase2-assign").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("phase2-status")).toContainText("assigned");
});

test("homepage has no serious accessibility violations", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("public-listing-card").first()).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter((item) => ["critical", "serious", "moderate"].includes(item.impact));
  expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
});

test("platform administration can see synthetic delivery status", async ({ page }) => {
  await page.goto("/perchpoint/super-admin/system-overview");
  await page.locator("input[name='dev-password']").fill(password);
  await page.getByTestId("phase2-sign-in").click();
  await expect(page.getByTestId("phase2-status")).toContainText("platform_admin");
  await page.getByTestId("phase2-deliver").click();
  await expect(page.getByTestId("phase2-status")).toContainText(/delivery|No pending/);
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter((item) => ["critical", "serious", "moderate"].includes(item.impact));
  expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
});

for (const width of [320, 768, 1024, 1440]) {
  test(`homepage does not overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page.getByTestId("public-listing-card").first()).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
  test(`leasing workspace does not overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await signIn(page, "ann.synthetic@example.com");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
}
