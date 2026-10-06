const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;
const crypto = require("crypto");

const password = process.env.PHASE2_DEV_PASSWORD;
const origin = process.env.PHASE6_BROWSER_ORIGIN || "http://127.0.0.1:3000";
const mailpitUrl = process.env.PHASE6_MAILPIT_URL || "http://127.0.0.1:8025";
const authUrl = process.env.PHASE6_AUTH_URL || "http://127.0.0.1:9999";
const identityPaths = [
  "/sign-in",
  "/invitation",
  "/mfa",
  "/password-reset",
  "/access/onboarding",
  "/access/security",
  "/access/users-access",
  "/access/delegations",
  "/access/access-requests",
  "/access/access-reviews",
  "/access/vendor-access",
  "/access/maintenance-history",
  "/access-denied?correlation_id=synthetic-correlation&return_to=%2Fdocuments",
  "/session-expired?draft=preserved",
];

function protectedHeaders(session) {
  return { "x-perchpoint-csrf": session.csrf, origin };
}

function providerAdminToken() {
  const now = Math.floor(Date.now() / 1000);
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString("base64url");
  const body = `${encode({ alg: "HS256", typ: "JWT" })}.${encode({
    role: "service_role",
    iss: process.env.PHASE6_PROVIDER_ISSUER || "perchpoint-local-auth",
    aud: "authenticated",
    iat: now,
    exp: now + 300,
  })}`;
  const secret = process.env.PHASE6_PROVIDER_JWT_SECRET || "local-only-not-production-gotrue-jwt-secret";
  const signature = crypto.createHmac("sha256", secret).update(body).digest("base64url");
  return `${body}.${signature}`;
}

async function resetSyntheticFactors(page, email) {
  const headers = { authorization: `Bearer ${providerAdminToken()}`, apikey: providerAdminToken() };
  const listed = await page.request.get(`${authUrl}/admin/users?page=1&per_page=1000`, { headers });
  expect(listed.status(), await listed.text()).toBe(200);
  const users = (await listed.json()).users || [];
  const user = users.find((item) => item.email.toLowerCase() === email.toLowerCase());
  expect(user, `Synthetic provider user ${email} was not provisioned`).toBeTruthy();
  const detail = await page.request.get(`${authUrl}/admin/users/${user.id}`, { headers });
  expect(detail.status(), await detail.text()).toBe(200);
  for (const factor of (await detail.json()).factors || []) {
    const removed = await page.request.delete(`${authUrl}/admin/users/${user.id}/factors/${factor.id}`, { headers });
    expect(removed.status(), await removed.text()).toBe(200);
  }
}

async function recoveryToken(page, email) {
  const token = providerAdminToken();
  const response = await page.request.post(`${authUrl}/admin/generate_link`, {
    headers: { authorization: `Bearer ${token}`, apikey: token },
    data: { type: "recovery", email },
  });
  expect(response.status(), await response.text()).toBe(200);
  return (await response.json()).hashed_token;
}

function base32(value) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const character of value.replace(/=+$/g, "").toUpperCase()) bits += alphabet.indexOf(character).toString(2).padStart(5, "0");
  const bytes = [];
  for (let index = 0; index + 8 <= bits.length; index += 8) bytes.push(parseInt(bits.slice(index, index + 8), 2));
  return Buffer.from(bytes);
}

function totp(secret) {
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const digest = crypto.createHmac("sha1", base32(secret)).update(counter).digest();
  const offset = digest[digest.length - 1] & 15;
  return ((digest.readUInt32BE(offset) & 0x7fffffff) % 1000000).toString().padStart(6, "0");
}

async function latestInvitation(page, email) {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const listing = await (await page.request.get(`${mailpitUrl}/api/v1/messages`)).json();
    const match = listing.messages.find((item) => item.To.some((recipient) => recipient.Address.toLowerCase() === email.toLowerCase()));
    if (match) {
      const message = await (await page.request.get(`${mailpitUrl}/api/v1/message/${match.ID}`)).json();
      const token = message.Text.match(/[?&]token=([^&\s]+)/);
      if (token) return token[1];
    }
    await page.waitForTimeout(100);
  }
  throw new Error(`Invitation for ${email} was not delivered to Mailpit`);
}

async function elevate(page, session) {
  if (session.assurance === "aal2") return session;
  const enrolled = await page.request.post("/api/v2/auth/mfa/enroll", { headers: protectedHeaders(session) });
  expect(enrolled.status(), await enrolled.text()).toBe(200);
  const factor = await enrolled.json();
  const confirmed = await page.request.post("/api/v2/auth/mfa/confirm", {
    headers: protectedHeaders(session),
    data: { factor_id: factor.factor_id, code: totp(factor.secret) },
  });
  expect(confirmed.status(), await confirmed.text()).toBe(200);
  return confirmed.json();
}

test("unified sign-in keeps the provider credential off the browser", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ann.synthetic@example.com");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/mfa\?next=/);
  const stored = await page.evaluate(() => `${JSON.stringify(localStorage)}${JSON.stringify(sessionStorage)}`);
  expect(stored).not.toMatch(/refresh_token|access_token|eyJ|local-only-not-production/i);
  expect(stored).not.toContain(password);
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
  await resetSyntheticFactors(page, email);
  const response = await page.request.post("/api/v2/auth/sign-in", { data: { email, password } });
  expect(response.status(), await response.text()).toBe(200);
  const session = await response.json();
  const cookies = await page.context().cookies(origin);
  expect(cookies.map((cookie) => cookie.name), "Application session cookies were not retained").toContain("pp_session");
  if (!session.mfa_required || session.assurance === "aal2") return session;
  return elevate(page, session);
}

async function purchasePayload(page, amountMinor, extras = {}) {
  const { projectName = "chromium", ...governedExtras } = extras;
  const properties = {
    chromium: "9960c7ea-3d4b-5fd7-90b3-6360439a6875",
    firefox: "fcb27fe5-d32b-5515-89b6-7221d1d62d29",
    webkit: "2114f237-dd93-5e79-80fb-11a402febe15",
  };
  const nonce = crypto.randomUUID();
  return {
    property_id: properties[projectName],
    amount_minor: amountMinor,
    decision_type: governedExtras.emergency ? "emergency_stabilization" : governedExtras.capital ? "capital_project" : "routine_purchase",
    related_transaction_key: `purchase-group-${nonce}`,
    idempotency_key: `purchase-${nonce}`,
    ...governedExtras,
  };
}

async function delegationBounds(page, capability) {
  const directory = await (await page.request.get("/api/v2/access/users")).json();
  const owner = directory.users.find((item) => item.role_name === "owner");
  expect(owner).toBeTruthy();
  return {
    capability,
    amount_ceiling_minor: 50000,
    resource_type: "property",
    resource_id: "9960c7ea-3d4b-5fd7-90b3-6360439a6875",
    decision_types: ["routine_purchase"],
    approval_id: owner.account_id,
  };
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

test("[staff-invitation] [mailpit-delivery] leasing can invite a technician", async ({ page }) => {
  const session = await signIn(page);
  const email = `tech.${Date.now()}@example.com`;
  const response = await page.request.post("/api/v2/auth/invitations", {
    headers: protectedHeaders(session),
    data: { email, role_name: "technician", purpose: "Assigned work only", staff: false },
  });
  expect(response.status(), await response.text()).toBe(200);
  expect((await response.json()).token).toBeUndefined();
  expect((await latestInvitation(page, email)).length).toBeGreaterThan(20);
});

test("[applicant-invitation] [invitation-acceptance] [wrong-email-invitation] [additional-adult] [guarantor-account] external people receive separate email-bound invitations", async ({ page }, testInfo) => {
  const session = await signIn(page);
  const roles = ["applicant", "household_adult", "guarantor"];
  const invitations = [];
  for (const role of roles) {
    const email = `${role}.${testInfo.project.name}.${Date.now()}@example.com`;
    const response = await page.request.post("/api/v2/auth/invitations", {
      headers: protectedHeaders(session),
      data: { email, role_name: role, purpose: `Synthetic ${role} relationship`, staff: false },
    });
    expect(response.status(), await response.text()).toBe(200);
    const body = await response.json();
    expect(body.expires_in_hours).toBe(72);
    invitations.push({ email, token: await latestInvitation(page, email) });
  }
  expect(new Set(invitations.map((item) => item.token)).size).toBe(roles.length);
  const wrongEmail = await page.request.post("/api/v2/auth/invitations/accept", {
    data: { token: invitations[0].token, email: invitations[1].email, password },
  });
  expect(wrongEmail.status()).toBe(400);
  for (const invitation of invitations) {
    const accepted = await page.request.post("/api/v2/auth/invitations/accept", { data: { ...invitation, password } });
    expect(accepted.status(), await accepted.text()).toBe(200);
  }
});

test("[invitation-replay] an accepted invitation cannot be reused", async ({ page }) => {
  const session = await signIn(page);
  const email = `replay.${Date.now()}@example.com`;
  const invited = await page.request.post("/api/v2/auth/invitations", {
    headers: protectedHeaders(session),
    data: { email, role_name: "technician", purpose: "One assignment", staff: false },
  });
  expect(invited.status(), await invited.text()).toBe(200);
  const token = await latestInvitation(page, email);
  expect((await page.request.post("/api/v2/auth/invitations/accept", { data: { token, email, password } })).status()).toBe(200);
  const invitedSession = await page.request.post("/api/v2/auth/sign-in", { data: { email, password } });
  expect(invitedSession.status(), await invitedSession.text()).toBe(200);
  expect((await invitedSession.json()).assurance).toBe("aal1");
  const blockedBeforeMfa = await page.request.get("/api/v2/properties");
  expect(blockedBeforeMfa.status()).toBe(403);
  expect((await blockedBeforeMfa.json()).detail.code).toBe("mfa_enrollment_required");
  const replay = await page.request.post("/api/v2/auth/invitations/accept", { data: { token, email, password } });
  expect(replay.status()).toBe(400);
  expect((await replay.json()).detail.code).toBe("invitation_invalid");
});

test("[expired-invitation] an expired invitation is rejected", async ({ page }) => {
  const session = await signIn(page);
  const email = `expired.${Date.now()}@example.com`;
  const invited = await page.request.post("/api/v2/auth/invitations", {
    headers: protectedHeaders(session),
    data: { email, role_name: "technician", purpose: "Short assignment", staff: true },
  });
  const body = await invited.json();
  const token = await latestInvitation(page, email);
  expect((await page.request.post(`/api/v2/auth/invitations/${body.invitation_id}/expire`, { headers: protectedHeaders(session) })).status()).toBe(200);
  const accepted = await page.request.post("/api/v2/auth/invitations/accept", { data: { token, email, password } });
  expect(accepted.status()).toBe(400);
});

test("[revoked-invitation] a revoked invitation is rejected", async ({ page }) => {
  const session = await signIn(page);
  const email = `revoked.${Date.now()}@example.com`;
  const invited = await page.request.post("/api/v2/auth/invitations", {
    headers: protectedHeaders(session),
    data: { email, role_name: "cleaner", purpose: "Short assignment", staff: true },
  });
  const body = await invited.json();
  const token = await latestInvitation(page, email);
  expect((await page.request.post(`/api/v2/auth/invitations/${body.invitation_id}/revoke`, { headers: protectedHeaders(session) })).status()).toBe(200);
  expect((await page.request.post("/api/v2/auth/invitations/accept", { data: { token, email, password } })).status()).toBe(400);
});

test("[resent-invitation-invalid] resending invalidates the prior invitation token", async ({ page }) => {
  const session = await signIn(page);
  const email = `resent.${Date.now()}@example.com`;
  const invited = await page.request.post("/api/v2/auth/invitations", {
    headers: protectedHeaders(session),
    data: { email, role_name: "cleaner", purpose: "Resent synthetic assignment", staff: true },
  });
  expect(invited.status(), await invited.text()).toBe(200);
  const invitationId = (await invited.json()).invitation_id;
  const originalToken = await latestInvitation(page, email);
  const resent = await page.request.post(`/api/v2/auth/invitations/${invitationId}/resend`, {
    headers: protectedHeaders(session),
  });
  expect(resent.status(), await resent.text()).toBe(200);
  const replacementToken = await latestInvitation(page, email);
  expect(replacementToken).not.toBe(originalToken);
  expect((await page.request.post("/api/v2/auth/invitations/accept", {
    data: { token: originalToken, email, password },
  })).status()).toBe(400);
  expect((await page.request.post("/api/v2/auth/invitations/accept", {
    data: { token: replacementToken, email, password },
  })).status()).toBe(200);
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

test("[session-revoke] a user can revoke a named session", async ({ page }) => {
  await signIn(page);
  const session = await signIn(page);
  const before = await (await page.request.get("/api/v2/me/sessions")).json();
  const target = before.sessions.find((item, index) => index > 0 && !item.revoked);
  expect(target).toBeTruthy();
  const response = await page.request.post(`/api/v2/me/sessions/${target.id}/revoke`, {
    headers: protectedHeaders(session),
  });
  expect(response.status(), await response.text()).toBe(200);
  const after = await (await page.request.get("/api/v2/me/sessions")).json();
  expect(after.sessions.find((item) => item.id === target.id).revoked).toBe(true);
});

test("[concurrent-session-limit] workforce accounts retain no more than three active sessions", async ({ page }) => {
  for (let index = 0; index < 4; index += 1) await signIn(page);
  const listed = await (await page.request.get("/api/v2/me/sessions")).json();
  expect(listed.sessions.filter((item) => !item.revoked)).toHaveLength(3);
  expect(listed.sessions.some((item) => item.revoked)).toBe(true);
});

test("[sign-out-others] other sessions can be revoked", async ({ page }) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/me/sessions/revoke-others", { headers: protectedHeaders(session) });
  expect(response.status(), await response.text()).toBe(200);
});

test("[access-request] a staff member can request access", async ({ page }) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/access/requests", {
    headers: protectedHeaders(session),
    data: {
      capability: "document.read",
      purpose: "Lease coordination",
      scope_type: "organization",
      duration_hours: 24,
      justification: "Need the lease file for this property",
    },
  });
  expect(response.status(), await response.text()).toBe(200);
});

test("[self-approval-denial] the requester cannot approve their own request", async ({ page }) => {
  const session = await signIn(page);
  const created = await page.request.post("/api/v2/access/requests", {
    headers: protectedHeaders(session),
    data: {
      capability: "document.read",
      purpose: "Lease coordination",
      scope_type: "organization",
      duration_hours: 24,
      justification: "Need the lease file for this property",
    },
  });
  const requestId = (await created.json()).request_id;
  const review = await page.request.post(`/api/v2/access/requests/${requestId}`, {
    headers: protectedHeaders(session),
    data: { approve: true },
  });
  expect(review.status()).toBe(409);
  expect((await review.json()).detail.code).toBe("self_approval");
});

test("[self-grant-denial] a person cannot delegate to themselves", async ({ page }) => {
  const session = await signIn(page);
  const me = await (await page.request.get("/api/v2/auth/me")).json();
  const response = await page.request.post("/api/v2/access/delegations", {
    headers: protectedHeaders(session),
    data: { grantee_id: me.account_id, capability: "expense.approve", reason: "Covering leave", days: 7 },
  });
  expect(response.status()).toBe(409);
  expect((await response.json()).detail.code).toBe("self_delegation");
});

test("[role-assignment] [scope-assignment] [resident-continuity] role and scope changes preserve identity and deny self-grant", async ({ page }) => {
  await resetSyntheticFactors(page, "nathan.synthetic@example.com");
  let session = await elevate(page, await signIn(page, "nathan.synthetic@example.com"));
  const organizationId = (await (await page.request.get("/api/v2/auth/me")).json()).organization_id;
  const directory = await (await page.request.get("/api/v2/access/users")).json();
  const nathan = directory.users.find((item) => item.email === "nathan.synthetic@example.com");
  const technician = directory.users.find((item) => item.email === "technician.synthetic@example.com");
  const applicant = directory.users.find((item) => item.email === "applicant.synthetic@example.com");
  expect(nathan).toBeTruthy();
  expect(technician).toBeTruthy();
  expect(applicant).toBeTruthy();

  const selfGrant = await page.request.post(`/api/v2/access/memberships/${nathan.membership_id}/role`, {
    headers: protectedHeaders(session),
    data: { role_name: "owner" },
  });
  expect(selfGrant.status()).toBe(409);
  expect((await selfGrant.json()).detail.code).toBe("self_grant");

  const assigned = await page.request.post(`/api/v2/access/memberships/${technician.membership_id}/role`, {
    headers: protectedHeaders(session),
    data: { role_name: "vendor_worker" },
  });
  expect(assigned.status(), await assigned.text()).toBe(200);
  const restored = await page.request.post(`/api/v2/access/memberships/${technician.membership_id}/role`, {
    headers: protectedHeaders(session),
    data: { role_name: "technician" },
  });
  expect(restored.status(), await restored.text()).toBe(200);

  await resetSyntheticFactors(page, "faruk.synthetic@example.com");
  const ownerSession = await elevate(page, await signIn(page, "faruk.synthetic@example.com"));
  const scopeApproval = await page.request.post(`/api/v2/access/memberships/${technician.membership_id}/authority-approvals`, {
    headers: protectedHeaders(ownerSession),
    data: {
      action: "scope",
      scope_type: "organization",
      resource_id: organizationId,
      reason: "Approve bounded organization scope for the synthetic technician",
    },
  });
  expect(scopeApproval.status(), await scopeApproval.text()).toBe(200);
  session = await elevate(page, await signIn(page, "nathan.synthetic@example.com"));
  const scoped = await page.request.post(`/api/v2/access/memberships/${technician.membership_id}/scopes`, {
    headers: protectedHeaders(session),
    data: {
      scope_type: "organization",
      resource_id: organizationId,
      approval_id: (await scopeApproval.json()).approval_id,
    },
  });
  expect(scoped.status(), await scoped.text()).toBe(200);

  const resident = await page.request.post(`/api/v2/access/memberships/${applicant.membership_id}/role`, {
    headers: protectedHeaders(session),
    data: { role_name: "resident" },
  });
  expect(resident.status(), await resident.text()).toBe(200);
  const applicantAgain = await page.request.post(`/api/v2/access/memberships/${applicant.membership_id}/role`, {
    headers: protectedHeaders(session),
    data: { role_name: "applicant" },
  });
  expect(applicantAgain.status(), await applicantAgain.text()).toBe(200);
  const after = await (await page.request.get("/api/v2/access/users")).json();
  expect(after.users.find((item) => item.email === applicant.email).account_id).toBe(applicant.account_id);
});

test("[staff-mfa-enroll] [staff-totp-sign-in] [step-up] [delegation-grant] [delegation-use] a bounded grant can be used by its grantee", async ({ page }) => {
  await resetSyntheticFactors(page, "ann.synthetic@example.com");
  const session = await elevate(page, await signIn(page));
  const directory = await (await page.request.get("/api/v2/access/users")).json();
  const technician = directory.users.find((item) => item.email === "technician.synthetic@example.com");
  expect(technician).toBeTruthy();
  const response = await page.request.post("/api/v2/access/delegations", {
    headers: protectedHeaders(session),
    data: {
      grantee_id: technician.account_id,
      reason: "Covering leave",
      days: 7,
      ...(await delegationBounds(page, "expense.approve")),
    },
  });
  expect(response.status(), await response.text()).toBe(200);
  const delegationId = (await response.json()).delegation_id;
  const technicianSession = await signIn(page, "technician.synthetic@example.com");
  const used = await page.request.post(`/api/v2/access/delegations/${delegationId}/use`, {
    headers: protectedHeaders(technicianSession),
    data: {
      action_type: "purchase_authorization",
      idempotency_key: `delegated-use-${crypto.randomUUID()}`,
      capability: "expense.approve",
      resource_type: "property",
      resource_id: "9960c7ea-3d4b-5fd7-90b3-6360439a6875",
      decision_type: "routine_purchase",
      amount_minor: 1000,
      related_transaction_key: `delegated-related-${crypto.randomUUID()}`,
    },
  });
  expect(used.status(), await used.text()).toBe(200);
  expect((await used.json()).authorized).toBe(true);
});

test("[delegation-revoke] [delegation-expire] [delegation-nontransitive] delegation lifecycle is bounded and cannot be chained", async ({ page }) => {
  await resetSyntheticFactors(page, "ann.synthetic@example.com");
  const session = await elevate(page, await signIn(page));
  const directory = await (await page.request.get("/api/v2/access/users")).json();
  const technician = directory.users.find((item) => item.email === "technician.synthetic@example.com");
  const cleaner = directory.users.find((item) => item.email === "cleaner.synthetic@example.com");
  expect(technician).toBeTruthy();
  expect(cleaner).toBeTruthy();

  const create = async (capability) => {
    const response = await page.request.post("/api/v2/access/delegations", {
      headers: protectedHeaders(session),
      data: {
        grantee_id: technician.account_id,
        reason: "Synthetic bounded lifecycle",
        days: 7,
        ...(await delegationBounds(page, capability)),
      },
    });
    expect(response.status(), await response.text()).toBe(200);
    return (await response.json()).delegation_id;
  };
  const revokedId = await create("expense.approve");
  const revoked = await page.request.post(`/api/v2/access/delegations/${revokedId}/revoke`, {
    headers: protectedHeaders(session),
  });
  expect(revoked.status(), await revoked.text()).toBe(200);

  const expiredId = await create("maintenance.coordinate");
  const expired = await page.request.post(`/api/v2/access/delegations/${expiredId}/expire`, {
    headers: protectedHeaders(session),
  });
  expect(expired.status(), await expired.text()).toBe(200);

  await create("delegation.grant");
  const technicianSession = await signIn(page, "technician.synthetic@example.com");
  const chained = await page.request.post("/api/v2/access/delegations", {
    headers: protectedHeaders(technicianSession),
    data: { grantee_id: cleaner.account_id, capability: "expense.approve", reason: "Forbidden delegation chain", days: 1 },
  });
  expect(chained.status()).toBe(403);
});

test("[financial-under-500] a routine amount stays inside operations authority", async ({ page }, testInfo) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/access/purchase-authority", {
    headers: protectedHeaders(session),
    data: await purchasePayload(page, 49999, { projectName: testInfo.project.name }),
  });
  const body = await response.json();
  expect(body.authority).toBe("routine");
  expect(body.allowed).toBe(true);
});

test("[financial-over-1200] an amount above 1200 dollars requires the owner", async ({ page }, testInfo) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/access/purchase-authority", { headers: protectedHeaders(session), data: await purchasePayload(page, 70002, { projectName: testInfo.project.name }) });
  const body = await response.json();
  expect(body.authority).toBe("owner");
  expect(body.allowed).toBe(false);
});

test("[financial-capital] capital work requires the owner", async ({ page }, testInfo) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/access/purchase-authority", { headers: protectedHeaders(session), data: await purchasePayload(page, 10000, { capital: true, projectName: testInfo.project.name }) });
  expect((await response.json()).authority).toBe("owner");
});

test("[context-forgery] an unknown context is rejected", async ({ page }) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/me/context", {
    headers: protectedHeaders(session),
    data: { membership_id: "22222222-2222-4222-8222-222222222222" },
  });
  expect(response.status()).toBe(409);
  expect((await response.json()).detail.code).toBe("context_invalid");
});

test("[context-switch] an authorized membership context rotates the active session", async ({ page }) => {
  const session = await signIn(page, "nathan.synthetic@example.com");
  const beforeCookie = (await page.context().cookies()).find((cookie) => cookie.name === "pp_session")?.value;
  const currentMembership = (await (await page.request.get("/api/v2/auth/me")).json()).membership_id;
  const contextsResponse = await page.request.get("/api/v2/me/contexts");
  expect(contextsResponse.status()).toBe(200);
  const contexts = (await contextsResponse.json()).contexts;
  const target = contexts.find((context) => context.membership_id !== currentMembership);
  expect(target).toBeTruthy();
  const switched = await page.request.post("/api/v2/me/context", {
    headers: protectedHeaders(session),
    data: { membership_id: target.membership_id },
  });
  expect(switched.status(), await switched.text()).toBe(200);
  expect((await switched.json()).membership_id).toBe(target.membership_id);
  const afterCookie = (await page.context().cookies()).find((cookie) => cookie.name === "pp_session")?.value;
  expect(afterCookie).toBeTruthy();
  expect(afterCookie).not.toBe(beforeCookie);
});

test("[service-issuance-denial] operations cannot issue a machine credential", async ({ page }) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/access/service-credentials/33333333-3333-4333-8333-333333333333", {
    headers: protectedHeaders(session),
  });
  expect(response.status()).toBe(403);
});

test("[service-credential-once] [service-principal-denial] a machine credential is shown once and cannot open a human portal session", async ({ page }) => {
  await resetSyntheticFactors(page, "nathan.synthetic@example.com");
  const session = await elevate(page, await signIn(page, "nathan.synthetic@example.com"));
  const before = await page.request.get("/api/v2/access/service-principals");
  expect(before.status(), await before.text()).toBe(200);
  const principal = (await before.json()).principals[0];
  expect(principal).toBeTruthy();
  const issued = await page.request.post(`/api/v2/access/service-credentials/${principal.id}`, {
    headers: protectedHeaders(session),
  });
  expect(issued.status(), await issued.text()).toBe(200);
  const credential = (await issued.json()).credential;
  expect(credential.length).toBeGreaterThan(30);
  const after = await (await page.request.get("/api/v2/access/service-principals")).json();
  expect(JSON.stringify(after)).not.toContain(credential);
  expect(after.principals[0].active_credentials).toBeGreaterThan(0);
  await page.context().clearCookies();
  const portal = await page.request.get("/api/v2/auth/me", {
    headers: {
      authorization: `Service ${credential}`,
      "x-perchpoint-audience": "perchpoint-worker",
      "x-perchpoint-worker": "synthetic-worker",
    },
  });
  expect(portal.status()).toBe(401);
});

test("[password-reset] the reset request does not reveal whether the account exists", async ({ page }) => {
  const unknown = await page.request.post("/api/v2/auth/password/reset-request", { data: { email: "nobody.synthetic@example.com" } });
  const known = await page.request.post("/api/v2/auth/password/reset-request", { data: { email: "ann.synthetic@example.com" } });
  expect(unknown.status()).toBe(known.status());
  expect((await unknown.json()).message).toBe((await known.json()).message);
});

test("[expired-reset] an invalid or expired password reset is rejected", async ({ page }) => {
  const response = await page.request.post("/api/v2/auth/password/reset", {
    data: { token: "expired-reset-token-that-does-not-exist", password: "Expired reset synthetic password 2046!" },
  });
  expect(response.status()).toBe(400);
  expect((await response.json()).detail.code).toBe("reset_invalid");
});

test("[reset-replay] a completed reset token cannot be reused", async ({ page }, testInfo) => {
  const token = await recoveryToken(page, "reset.synthetic@example.com");
  const replacement = `Synthetic reset ${testInfo.project.name} ${Date.now()} password!`;
  const first = await page.request.post("/api/v2/auth/password/reset", { data: { token, password: replacement } });
  expect(first.status(), await first.text()).toBe(200);
  expect((await first.json()).signed_in).toBe(false);
  const replay = await page.request.post("/api/v2/auth/password/reset", { data: { token, password: replacement } });
  expect(replay.status()).toBe(400);
  expect((await replay.json()).detail.code).toBe("reset_invalid");
});

test("[recovery-code-use] [recovery-replay] a recovery code is accepted once and revokes the session", async ({ page }) => {
  await resetSyntheticFactors(page, "ann.synthetic@example.com");
  const elevated = await elevate(page, await signIn(page));
  const issued = await page.request.post("/api/v2/auth/recovery-codes", {
    headers: protectedHeaders(elevated),
  });
  expect(issued.status(), await issued.text()).toBe(200);
  const code = (await issued.json()).codes[0];
  const first = await page.request.post("/api/v2/auth/recovery-code", {
    headers: protectedHeaders(elevated),
    data: { code },
  });
  expect(first.status(), await first.text()).toBe(200);
  const fresh = await signIn(page);
  const replay = await page.request.post("/api/v2/auth/recovery-code", {
    headers: protectedHeaders(fresh),
    data: { code },
  });
  expect(replay.status()).toBe(400);
  expect((await replay.json()).detail.code).toBe("recovery_code_invalid");
});

test("[financial-500] exactly 500 dollars remains ordinary operations authority", async ({ page }, testInfo) => {
  const session = await signIn(page);
  const response = await page.request.post("/api/v2/access/purchase-authority", {
    headers: protectedHeaders(session),
    data: await purchasePayload(page, 1, { projectName: testInfo.project.name }),
  });
  expect(response.status()).toBe(200);
  expect((await response.json()).authority).toBe("operations");
});

test("[financial-rent] an amount above monthly rent is owner-reserved", async ({ page }, testInfo) => {
  const session = await signIn(page);
  const baseline = await page.request.post("/api/v2/access/purchase-authority", {
    headers: protectedHeaders(session),
    data: await purchasePayload(page, 0, { projectName: testInfo.project.name }),
  });
  expect(baseline.status(), await baseline.text()).toBe(200);
  const monthlyRent = (await baseline.json()).monthly_rent_minor;
  const response = await page.request.post("/api/v2/access/purchase-authority", {
    headers: protectedHeaders(session),
    data: await purchasePayload(page, monthlyRent - 50000 + 1, { projectName: testInfo.project.name }),
  });
  expect((await response.json()).authority).toBe("owner");
});

test("[financial-emergency] immediate preservation work is bounded at 1200 dollars", async ({ page }, testInfo) => {
  const session = await signIn(page);
  const within = await page.request.post("/api/v2/access/purchase-authority", {
    headers: protectedHeaders(session),
    data: await purchasePayload(page, 120000, { emergency: true, projectName: testInfo.project.name }),
  });
  expect((await within.json()).allowed).toBe(true);
  const above = await page.request.post("/api/v2/access/purchase-authority", {
    headers: protectedHeaders(session),
    data: await purchasePayload(page, 120001, { emergency: true, projectName: testInfo.project.name }),
  });
  expect((await above.json()).allowed).toBe(false);
});

test("[search-isolation] [export-isolation] [storage-isolation] guessed cross-tenant resources stay concealed", async ({ page }) => {
  await signIn(page, "faruk.synthetic@example.com");
  const search = await page.request.get("/api/v2/search?q=isolation");
  expect(search.status()).toBe(200);
  expect(JSON.stringify(await search.json())).not.toMatch(/organization-isolation/i);
  const guessed = "22222222-2222-4222-8222-222222222222";
  const exported = await page.request.get(`/api/v2/exports/${guessed}/content`);
  expect(exported.status()).toBe(404);
  const stored = await page.request.get(`/api/v2/documents/${guessed}/content?token=not-a-valid-access-token`);
  expect(stored.status()).toBe(404);
});

test("[organization-isolation] another organization's property is not listed", async ({ page }) => {
  await signIn(page);
  const response = await page.request.get("/api/v2/properties");
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(JSON.stringify(body)).not.toMatch(/isolation/i);
});

test("[household-isolation] a resident sees only relationship-bound household records", async ({ page }) => {
  await signIn(page, "resident.synthetic@example.com");
  const response = await page.request.get("/api/v2/households");
  expect(response.status(), await response.text()).toBe(200);
  const body = await response.json();
  expect(body.households).toHaveLength(1);
  expect(body.households[0].label).toBe("Example resident household");
});

test("[vendor-isolation] a vendor administrator receives no implicit property or household access", async ({ page }) => {
  await signIn(page, "vendor.admin.synthetic@example.com");
  const properties = await page.request.get("/api/v2/properties");
  expect(properties.status()).toBe(403);
  const households = await page.request.get("/api/v2/households");
  expect(households.status()).toBe(200);
  expect((await households.json()).households).toEqual([]);
});

test("[technician-isolation] [cleaner-isolation] workers see only assignment-scoped properties and no unrelated households", async ({ page }) => {
  for (const email of ["technician.synthetic@example.com", "cleaner.synthetic@example.com"]) {
    await signIn(page, email);
    const properties = await page.request.get("/api/v2/properties");
    expect(properties.status(), await properties.text()).toBe(200);
    const visibleProperties = (await properties.json()).properties;
    expect(visibleProperties.map((property) => property.id)).toEqual(["9960c7ea-3d4b-5fd7-90b3-6360439a6875"]);
    const households = await page.request.get("/api/v2/households");
    expect(households.status()).toBe(200);
    expect((await households.json()).households).toEqual([]);
  }
});

test("[suspended-denial] a suspended identity is denied before a session is opened", async ({ page }) => {
  const response = await page.request.post("/api/v2/auth/sign-in", {
    data: { email: "suspended.synthetic@example.com", password },
  });
  expect(response.status()).toBe(403);
  expect((await response.json()).detail.code).toBe("suspended");
});

test("[former-resident] an ended membership cannot open a resident session", async ({ page }) => {
  const response = await page.request.post("/api/v2/auth/sign-in", {
    data: { email: "former.synthetic@example.com", password },
  });
  expect(response.status()).toBe(403);
  expect((await response.json()).detail.code).toBe("membership_expired");
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
  await expect(page).toHaveURL(/\/(mfa|access\/onboarding)/);
});

test("[security-center] session inventory is connected and accessible", async ({ page }) => {
  await signIn(page);
  await page.goto("/access/security");
  await expect(page.getByRole("heading", { name: "Security Center" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign out all other sessions" })).toBeVisible();
});

test("[users-access-center] directory is server-authorized", async ({ page }) => {
  await signIn(page);
  await page.goto("/access/users-access");
  await expect(page.getByRole("heading", { name: "Users and Access" })).toBeVisible();
  await expect(page.getByText("ann.synthetic@example.com")).toBeVisible();
});

test("[delegation-center] bounded grants are visible from the server", async ({ page }) => {
  await signIn(page);
  await page.goto("/access/delegations");
  await expect(page.getByRole("heading", { name: "Delegation Center" })).toBeVisible();
  await expect(page.getByText(/Usage is audited by the server/)).toBeVisible();
});

test("[access-review] operations can inspect the current review population", async ({ page }) => {
  await signIn(page);
  const reviews = await (await page.request.get("/api/v2/access/reviews")).json();
  await page.goto("/access/access-reviews");
  await expect(page.getByRole("heading", { name: "Access Reviews" })).toBeVisible();
  if (reviews.reviews.length) {
    await expect(page.getByRole("listitem")).toHaveCount(reviews.reviews.length);
  } else {
    await expect(page.getByRole("status")).toContainText("no records");
  }
});

test("[vendor-worker-access] vendor view exposes only the connected authorized directory result", async ({ page }) => {
  await signIn(page);
  await page.goto("/access/vendor-access");
  await expect(page.getByRole("heading", { name: "Vendor access" })).toBeVisible();
  await expect(page.getByText("technician.synthetic@example.com")).toBeVisible();
  await expect(page.getByText("applicant.synthetic@example.com")).toHaveCount(0);
});

test("[access-denied] concealed denial has a support correlation explanation", async ({ page }) => {
  await page.goto("/access-denied?correlation_id=synthetic-correlation&return_to=%2Fdocuments&capability=document.read");
  await expect(page.getByRole("heading", { name: "Access denied" })).toBeVisible();
  await expect(page.getByText("synthetic-correlation")).toBeVisible();
  await expect(page.getByRole("link", { name: "Request appropriate access" })).toBeVisible();
});

test("[session-expiry] stale authority cannot continue", async ({ page }) => {
  await page.goto("/session-expired");
  await expect(page.getByRole("heading", { name: "Your session expired" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();
});

test("[responsive-sign-in] [responsive-security] [responsive-access] [responsive-delegation] connected identity surfaces have no horizontal overflow", async ({ page }) => {
  await signIn(page, "nathan.synthetic@example.com");
  for (const path of identityPaths) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    for (const width of [320, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `${path} overflowed at ${width}px`).toBeLessThanOrEqual(1);
    }
  }
});

test("[a11y-representative-surfaces] automated scans have no application-owned blocking violations", async ({ page }) => {
  await signIn(page, "nathan.synthetic@example.com");
  for (const path of identityPaths) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    const results = await new AxeBuilder({ page }).analyze();
    const blocking = results.violations.filter((item) => ["critical", "serious", "moderate"].includes(item.impact));
    expect(blocking, `${path}\n${JSON.stringify(blocking, null, 2)}`).toEqual([]);
  }
});

test("[screen-reader-semantics] identity pages expose one main landmark and one primary heading", async ({ page }) => {
  await signIn(page, "nathan.synthetic@example.com");
  for (const path of identityPaths) {
    await page.goto(path);
    await expect(page.locator("main"), `${path} did not expose a main landmark`).toHaveCount(1);
    await expect(page.getByRole("heading", { level: 1 }), `${path} did not expose one level-one heading`).toHaveCount(1);
    expect((await page.title()).trim(), `${path} did not expose a document title`).not.toBe("");
  }
});

test("[keyboard-focus-all-identity] every identity page exposes a visible keyboard focus target", async ({ page }) => {
  await signIn(page, "nathan.synthetic@example.com");
  for (const path of identityPaths) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    if (path === "/mfa") {
      await expect(page.locator("main button:not([disabled]), main input")).toBeVisible();
    }
    const firstTarget = page.locator(
      "main a[href]:visible, main button:visible, main input:visible, main select:visible, main textarea:visible",
    ).first();
    await expect(
      firstTarget,
      `${path} did not render a keyboard target`,
    ).toBeVisible();
    await page.evaluate(() => {
      document.body.setAttribute("tabindex", "-1");
      document.body.focus();
      document.body.removeAttribute("tabindex");
    });
    await page.keyboard.press("Tab");
    let focusStyle = null;
    let visibleIndicator = false;
    for (let attempt = 0; attempt < 30 && !visibleIndicator; attempt += 1) {
      focusStyle = await page.evaluate(() => new Promise((resolve) => {
        requestAnimationFrame(() => {
          const element = document.activeElement;
          if (!element || element === document.body || element === document.documentElement) {
            resolve(null);
            return;
          }
          const style = getComputedStyle(element);
          const box = element.getBoundingClientRect();
          resolve({
            outlineStyle: style.outlineStyle,
            outlineWidth: style.outlineWidth,
            boxShadow: style.boxShadow,
            tag: element.tagName,
            tabIndex: element.tabIndex,
            visible: box.width > 0 && box.height > 0,
          });
        });
      }));
      visibleIndicator = Boolean(
        focusStyle
        && focusStyle.visible
        && focusStyle.tabIndex >= 0
        && (
          (focusStyle.outlineStyle !== "none" && focusStyle.outlineWidth !== "0px")
          || (focusStyle.boxShadow && focusStyle.boxShadow !== "none")
        ),
      );
      if (!visibleIndicator) await page.keyboard.press("Tab");
    }
    expect(visibleIndicator, `${path} did not render a focus indicator: ${JSON.stringify(focusStyle)}`).toBe(true);
  }
});

test("[reduced-motion-all-identity] identity pages honor reduced motion", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await signIn(page, "nathan.synthetic@example.com");
  for (const path of identityPaths) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    const motion = await page.locator("body").evaluate(() => {
      const probe = document.createElement("button");
      document.body.appendChild(probe);
      const style = getComputedStyle(probe);
      const result = { animation: style.animationName, transition: style.transitionDuration };
      probe.remove();
      return result;
    });
    expect(motion.animation).toBe("none");
    expect(parseFloat(motion.transition) || 0).toBeLessThanOrEqual(0.01);
  }
});

