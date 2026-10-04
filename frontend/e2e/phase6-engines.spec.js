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
  const blocking = results.violations.filter((item) => ["critical", "serious", "moderate"].includes(item.impact));
  expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
});

async function signIn(page, email = "ann.synthetic@example.com") {
  const response = await page.request.post("/api/v2/auth/sign-in", { data: { email, password } });
  expect(response.status(), await response.text()).toBe(200);
  return response.json();
}

test("[public-browse] listings omit internal identifiers", async ({ page }) => {
  const response = await page.request.get("/api/v2/listings");
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.listings.length).toBeGreaterThan(0);
  for (const listing of body.listings) {
    expect(listing.organization_id).toBeUndefined();
    expect(listing.space_id).toBeUndefined();
  }
});

test("[prospect-inquiry] an inquiry does not require an account", async ({ page }) => {
  const listings = await (await page.request.get("/api/v2/listings")).json();
  const response = await page.request.post("/api/v2/inquiries", {
    data: {
      listing_id: listings.listings[0].listing_id,
      name: "Synthetic Prospect",
      email: "prospect.synthetic@example.com",
      intent: "tour",
      message: "Asking about the published listing",
      idempotency_key: `prospect-${Date.now()}`,
    },
  });
  expect(response.status(), await response.text()).toBe(201);
  const body = await response.json();
  expect(body.organization_id).toBeUndefined();
});

test("[staff-invitation] leasing can invite a technician", async ({ page }) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/auth/invitations", {
    headers: { "x-perchpoint-csrf": session.csrf },
    data: { email: `tech.${Date.now()}@example.com`, role_name: "technician", purpose: "Assigned work only", staff: false },
  });
  expect(response.status(), await response.text()).toBe(200);
  expect((await response.json()).token.length).toBeGreaterThan(20);
});

test("[invitation-replay] an accepted invitation cannot be reused", async ({ page }) => {
  const session = await signIn(page);
  const invited = await page.request.post("/api/v2/auth/invitations", {
    headers: { "x-perchpoint-csrf": session.csrf },
    data: { email: `replay.${Date.now()}@example.com`, role_name: "technician", purpose: "One assignment", staff: false },
  });
  const token = (await invited.json()).token;
  expect((await page.request.post("/api/v2/auth/invitations/accept", { data: { token } })).status()).toBe(200);
  const replay = await page.request.post("/api/v2/auth/invitations/accept", { data: { token } });
  expect(replay.status()).toBe(400);
  expect((await replay.json()).detail.code).toBe("invitation_invalid");
});

test("[expired-invitation] an expired invitation is rejected", async ({ page }) => {
  const session = await signIn(page);
  const invited = await page.request.post("/api/v2/auth/invitations", {
    headers: { "x-perchpoint-csrf": session.csrf },
    data: { email: `expired.${Date.now()}@example.com`, role_name: "technician", purpose: "Short assignment", staff: true },
  });
  const body = await invited.json();
  expect((await page.request.post(`/api/v2/auth/invitations/${body.invitation_id}/expire`, { headers: { "x-perchpoint-csrf": session.csrf } })).status()).toBe(200);
  const accepted = await page.request.post("/api/v2/auth/invitations/accept", { data: { token: body.token } });
  expect(accepted.status()).toBe(400);
});

test("[revoked-invitation] a revoked invitation is rejected", async ({ page }) => {
  const session = await signIn(page);
  const invited = await page.request.post("/api/v2/auth/invitations", {
    headers: { "x-perchpoint-csrf": session.csrf },
    data: { email: `revoked.${Date.now()}@example.com`, role_name: "cleaner", purpose: "Short assignment", staff: true },
  });
  const body = await invited.json();
  expect((await page.request.post(`/api/v2/auth/invitations/${body.invitation_id}/revoke`, { headers: { "x-perchpoint-csrf": session.csrf } })).status()).toBe(200);
  expect((await page.request.post("/api/v2/auth/invitations/accept", { data: { token: body.token } })).status()).toBe(400);
});

test("[csrf-rejection] a mutation without the session token is rejected", async ({ page }) => {
  await signIn(page);
  const response = await page.request.post("/api/v2/auth/sign-out");
  expect(response.status()).toBe(403);
  expect((await response.json()).detail.code).toBe("csrf_rejected");
});

test("[session-list] the session inventory does not reveal the cookie value", async ({ page }) => {
  await signIn(page);
  const response = await page.request.get("/api/v2/me/sessions");
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.sessions.length).toBeGreaterThan(0);
  expect(JSON.stringify(body)).not.toMatch(/pp_session|refresh_token/);
});

test("[sign-out-others] other sessions can be revoked", async ({ page }) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/me/sessions/revoke-others", { headers: { "x-perchpoint-csrf": session.csrf } });
  expect(response.status(), await response.text()).toBe(200);
});

test("[access-request] a staff member can request access", async ({ page }) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/access/requests", {
    headers: { "x-perchpoint-csrf": session.csrf },
    data: { capability: "document.read", justification: "Need the lease file for this property" },
  });
  expect(response.status(), await response.text()).toBe(200);
});

test("[self-approval-denial] the requester cannot approve their own request", async ({ page }) => {
  const session = await signIn(page);
  const created = await page.request.post("/api/v2/access/requests", {
    headers: { "x-perchpoint-csrf": session.csrf },
    data: { capability: "document.read", justification: "Need the lease file for this property" },
  });
  const requestId = (await created.json()).request_id;
  const review = await page.request.post(`/api/v2/access/requests/${requestId}`, {
    headers: { "x-perchpoint-csrf": session.csrf },
    data: { approve: true },
  });
  expect(review.status()).toBe(409);
  expect((await review.json()).detail.code).toBe("self_approval");
});

test("[self-grant-denial] a person cannot delegate to themselves", async ({ page }) => {
  const session = await signIn(page);
  const me = await (await page.request.get("/api/v2/auth/me")).json();
  const response = await page.request.post("/api/v2/access/delegations", {
    headers: { "x-perchpoint-csrf": session.csrf },
    data: { grantee_id: me.account_id, capability: "expense.approve", reason: "Covering leave", days: 7 },
  });
  expect(response.status()).toBe(409);
  expect((await response.json()).detail.code).toBe("self_delegation");
});

test("[delegation-grant] a bounded grant to someone else is recorded", async ({ page }) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/access/delegations", {
    headers: { "x-perchpoint-csrf": session.csrf },
    data: { grantee_id: "11111111-1111-4111-8111-111111111111", capability: "expense.approve", reason: "Covering leave", days: 7, amount_ceiling_minor: 50000 },
  });
  expect(response.status(), await response.text()).toBe(200);
});

test("[financial-under-500] a routine amount stays inside operations authority", async ({ page }) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/access/purchase-authority", {
    headers: { "x-perchpoint-csrf": session.csrf },
    data: { amount_minor: 49999, monthly_rent_minor: 200000 },
  });
  const body = await response.json();
  expect(body.authority).toBe("routine");
  expect(body.allowed).toBe(true);
});

test("[financial-over-1200] an amount above 1200 dollars requires the owner", async ({ page }) => {
  await signIn(page);
  const response = await page.request.post("/api/v2/access/purchase-authority", { data: { amount_minor: 120001, monthly_rent_minor: 200000 } });
  const body = await response.json();
  expect(body.authority).toBe("owner");
  expect(body.allowed).toBe(false);
});

test("[financial-capital] capital work requires the owner", async ({ page }) => {
  await signIn(page);
  const response = await page.request.post("/api/v2/access/purchase-authority", { data: { amount_minor: 10000, monthly_rent_minor: 200000, capital: true } });
  expect((await response.json()).authority).toBe("owner");
});

test("[context-forgery] an unknown context is rejected", async ({ page }) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/me/context", {
    headers: { "x-perchpoint-csrf": session.csrf },
    data: { membership_id: "22222222-2222-4222-8222-222222222222" },
  });
  expect(response.status()).toBe(409);
  expect((await response.json()).detail.code).toBe("context_invalid");
});

test("[service-principal-denial] operations cannot issue a machine credential", async ({ page }) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/access/service-credentials/33333333-3333-4333-8333-333333333333", {
    headers: { "x-perchpoint-csrf": session.csrf },
  });
  expect(response.status()).toBe(403);
});

test("[password-reset] the reset request does not reveal whether the account exists", async ({ page }) => {
  const unknown = await page.request.post("/api/v2/auth/password/reset-request", { data: { email: "nobody.synthetic@example.com" } });
  const known = await page.request.post("/api/v2/auth/password/reset-request", { data: { email: "ann.synthetic@example.com" } });
  expect(unknown.status()).toBe(known.status());
  expect((await unknown.json()).message).toBe((await known.json()).message);
});

test("[organization-isolation] another organization's property is not listed", async ({ page }) => {
  await signIn(page);
  const response = await page.request.get("/api/v2/properties");
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(JSON.stringify(body)).not.toMatch(/isolation/i);
});

test("[keyboard-sign-in] the sign-in form can be completed from the keyboard", async ({ page }) => {
  await page.goto("/sign-in");
  const email = page.getByLabel("Email");
  await email.waitFor();
  await email.focus();
  await page.keyboard.type("ann.synthetic@example.com");
  await page.keyboard.press("Tab");
  await page.keyboard.type(password);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toContainText("Signed in.");
});

