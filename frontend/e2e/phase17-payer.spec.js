const { test, expect, request: playwrightRequest } = require("@playwright/test");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const webhookSecret = "local-only-not-production-phase17-webhook";
let worker;

function workerEnv() {
  return {
    ...process.env,
    PYTHONUNBUFFERED: "1",
    PHASE3_ENVIRONMENT: "local",
    PHASE2_LOCAL_AUTH: "development",
    PHASE2_ADMIN_URL: "postgresql+psycopg://postgres:local-only-not-production@127.0.0.1:54339/postgres",
    PHASE2_MIGRATOR_URL: "postgresql+psycopg://perchpoint_migrator:local-only-not-production@127.0.0.1:54339/perchpoint_phase2",
    PHASE2_RUNTIME_URL: "postgresql+psycopg://perchpoint_runtime:local-only-not-production@127.0.0.1:54339/perchpoint_phase2",
    PHASE2_JWT_SECRET: "local-only-not-production-jwt-secret-32-plus",
    PHASE2_DEV_PASSWORD: "local-only-not-production-password",
    PHASE2_WEBHOOK_SECRET: "local-only-not-production-webhook",
    PHASE6_SESSION_KEY: "local-only-not-production-phase6-session-encryption-key",
    PHASE6_PROVIDER_JWT_SECRET: "local-only-not-production-gotrue-jwt-secret",
    PHASE6_AUTH_URL: "http://127.0.0.1:9998",
    PHASE6_MAILPIT_URL: "http://127.0.0.1:8125",
    PHASE6_SMTP_HOST: "127.0.0.1",
    PHASE6_SMTP_PORT: "1125",
    PHASE6_ALLOWED_ORIGINS: "http://127.0.0.1:3000,http://localhost:3000",
  };
}

test.beforeAll(async () => {
  worker = spawn("python", ["-m", "perchpoint.phase17_worker"], {
    cwd: path.join(__dirname, "../../backend"),
    env: workerEnv(),
    stdio: ["ignore", "pipe", "pipe"],
  });
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("worker did not become ready")), 20000);
    let ready = false;
    worker.stdout.on("data", (chunk) => {
      if (!ready && String(chunk).includes("phase17-worker-ready")) {
        ready = true;
        clearTimeout(timer);
        resolve();
      }
    });
    worker.on("exit", (code) => {
      if (!ready) reject(new Error(`worker exited ${code}`));
    });
  });
});

test.afterAll(() => {
  if (worker && !worker.killed) worker.kill();
});

function localPassword() {
  const text = fs.readFileSync(path.join(__dirname, "../../backend/.env.demo.local"), "utf8");
  const line = text.split(/\r?\n/).find((row) => row.startsWith("PERCHPOINT_LOCAL_DEMO_PASSWORD="));
  if (!line) throw new Error("local demo password file is missing the expected key");
  return line.split("=").slice(1).join("=").trim();
}

const payerPassword = "Synthetic invitation password 2046!";

function csrfHeaders(cookies) {
  const token = cookies.find((item) => item.name === "pp_csrf");
  return {
    origin: "http://127.0.0.1:3000",
    "x-perchpoint-csrf": token ? token.value : "",
  };
}

async function signIn(page, email, password) {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(email);
  await page.getByRole("textbox", { name: "Password" }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

async function mailToken(email, subject, previous = "") {
  for (let attempt = 0; attempt < 25; attempt += 1) {
    const listing = await fetch("http://127.0.0.1:8125/api/v1/messages").then((response) => response.json());
    const matches = (listing.messages || []).filter((item) => (
      item.Subject === subject
      && (item.To || []).some((recipient) => (recipient.Address || "").toLowerCase() === email.toLowerCase())
    )).sort((left, right) => new Date(right.Created) - new Date(left.Created));
    for (const match of matches) {
      const message = await fetch(`http://127.0.0.1:8125/api/v1/message/${match.ID}`).then((response) => response.json());
      const text = String(message.Text || "").replace(/=\r?\n/g, "");
      const found = text.match(/token=([A-Za-z0-9_\-]+)/);
      if (found && found[1] !== previous) return found[1];
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error("local delivery did not include the expected invitation");
}

async function staffSummary(page, tenancy) {
  const response = await page.request.get(`/api/v2/payments/summary?tenancy_code=${encodeURIComponent(tenancy)}`);
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}

async function deliverProcessing(page, organization, tenancy, amount) {
  const summary = await staffSummary(page, tenancy);
  const payment = [...summary.payments].reverse().find((row) => row.state === "processing" && row.amount_minor === amount);
  if (!payment) throw new Error("no processing payment was available to confirm");
  const payload = {
    id: `evt-${payment.public_reference}`,
    organization_id: organization,
    type: "payment.succeeded",
    effect_key: payment.public_reference,
    amount_minor: amount,
    environment: "local_fake",
  };
  const raw = JSON.stringify(payload);
  const signature = crypto.createHmac("sha256", webhookSecret).update(raw).digest("hex");
  const posted = await page.request.post("/api/v2/payments/provider-events", {
    headers: { "content-type": "application/json", "x-perchpoint-provider-signature": signature },
    data: raw,
  });
  expect(posted.ok(), await posted.text()).toBeTruthy();
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const current = await staffSummary(page, tenancy);
    const row = current.payments.find((item) => item.public_reference === payment.public_reference);
    if (row && row.state === "succeeded") return { summary: current, payload, raw, signature };
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("worker did not confirm the payment");
}

async function acceptIdentity(page, email, token) {
  await page.goto("/invitation");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Invitation token").fill(token);
  await page.getByLabel("Create password").fill(payerPassword);
  await page.getByRole("button", { name: "Accept invitation" }).click();
  await expect(page.getByText("Invitation accepted")).toBeVisible();
}

test("resident invitation and additional payer pay the remainder", async ({ browser }) => {
  const stamp = Date.now().toString(36);
  const tenancy = `payer-scenario-${stamp}`;
  const other = `payer-hidden-${stamp}`;
  const residentEmail = `resident.${stamp}@example.com`;
  const payerEmail = `payer.${stamp}@example.com`;
  const operations = await browser.newContext();
  const resident = await browser.newContext();
  const payer = await browser.newContext();
  const opsPage = await operations.newPage();
  const residentPage = await resident.newPage();
  const payerPage = await payer.newPage();

  await signIn(opsPage, "operations@demo.perchpoint.invalid", localPassword());
  await expect(opsPage.getByRole("link", { name: "Accounts" })).toBeVisible();
  const opsHeaders = csrfHeaders(await operations.cookies());
  for (const [email, role] of [[residentEmail, "resident"], [payerEmail, "additional_payer"]]) {
    const invited = await opsPage.request.post("/api/v2/auth/invitations", {
      headers: opsHeaders,
      data: { email, role_name: role, purpose: "Disposable payer scenario", staff: false },
    });
    expect(invited.ok(), await invited.text()).toBeTruthy();
  }
  await acceptIdentity(residentPage, residentEmail, await mailToken(residentEmail, "Your synthetic PerchPoint invitation"));
  await acceptIdentity(payerPage, payerEmail, await mailToken(payerEmail, "Your synthetic PerchPoint invitation"));

  await opsPage.getByRole("link", { name: "Accounts" }).click();
  await expect(opsPage.getByRole("heading", { name: "Publish a payable charge" })).toBeVisible();
  await opsPage.getByLabel("Tenancy code").fill(tenancy);
  await opsPage.getByLabel("Amount in dollars").fill("1000");
  await opsPage.getByLabel("Description").fill("Disposable payer scenario charge");
  await opsPage.getByRole("button", { name: "Publish charge" }).click();
  await expect(opsPage.getByText("The charge is payable.")).toBeVisible();
  const linkedResident = await opsPage.request.post("/api/v2/payments/charges/resident", {
    headers: csrfHeaders(await operations.cookies()),
    data: { tenancy_code: tenancy, email: residentEmail },
  });
  expect(linkedResident.ok(), await linkedResident.text()).toBeTruthy();
  await expect(opsPage.getByText("Remaining $1,000.00")).toBeVisible();
  const hidden = await opsPage.request.post("/api/v2/payments/charges", {
    headers: csrfHeaders(await operations.cookies()),
    data: {
      tenancy_code: other,
      amount_minor: 50000,
      category: "fee",
      description: "A charge the additional payer must not see",
      idempotency_key: `hidden-${stamp}`,
    },
  });
  expect(hidden.ok(), await hidden.text()).toBeTruthy();
  await opsPage.getByLabel("Amount to record").fill("400");
  await opsPage.getByRole("button", { name: "Record synthetic collection" }).click();
  await expect(opsPage.getByText("Collection is processing.")).toBeVisible();
  await expect(opsPage.getByText("Processing $400.00")).toBeVisible();
  await expect(opsPage.getByText("Remaining $600.00")).toBeVisible();
  const organization = (await (await opsPage.request.get("/api/v2/auth/me")).json()).organization_id;
  await deliverProcessing(opsPage, organization, tenancy, 40000);

  await signIn(residentPage, residentEmail, payerPassword);
  await expect(residentPage.getByRole("heading", { name: "Household payments" })).toBeVisible();
  await residentPage.getByRole("link", { name: "Payments", exact: true }).click();
  await residentPage.getByLabel("Household code").fill(tenancy);
  await residentPage.getByRole("button", { name: "Open household" }).click();
  await expect(residentPage.getByRole("heading", { name: "Additional payer" })).toBeVisible();
  await residentPage.getByLabel("Email").fill(payerEmail);
  await residentPage.getByRole("button", { name: "Send invitation" }).click();
  await expect(residentPage.getByText("The invitation was sent.")).toBeVisible();
  const grantToken = await mailToken(payerEmail, "Your synthetic PerchPoint payment invitation");

  const residentDenied = await residentPage.request.post("/api/v2/payments/payers/accept", {
    headers: csrfHeaders(await resident.cookies()),
    data: { invitation_token: grantToken },
  });
  expect(residentDenied.status()).toBe(403);

  await signIn(payerPage, payerEmail, payerPassword);
  await expect(payerPage).toHaveURL(/\/pay$/);
  await expect(payerPage.getByRole("heading", { name: "Granted payments" })).toBeVisible();
  await payerPage.goto(`/pay?token=${encodeURIComponent(grantToken)}`);
  await payerPage.getByRole("button", { name: "Accept invitation" }).click();
  await expect(payerPage.getByText("You can pay the granted charges.")).toBeVisible();
  await expect(payerPage.getByText("Remaining $600.00")).toBeVisible();
  await expect(payerPage.getByText("$400.00")).toHaveCount(0);

  await payerPage.getByLabel("Amount to pay").fill("1000");
  await payerPage.getByRole("button", { name: "Pay $1,000.00" }).click();
  await expect(payerPage.getByText("That amount is more than the eligible balance.")).toBeVisible();
  await payerPage.getByLabel("Amount to pay").fill("600");
  await payerPage.getByRole("button", { name: "Pay $600.00" }).click();
  await expect(payerPage.getByText("Payment is processing.")).toBeVisible();
  await deliverProcessing(opsPage, organization, tenancy, 60000);
  await payerPage.reload();
  const summary = await payerPage.request.get(`/api/v2/payments/summary?tenancy_code=${encodeURIComponent(tenancy)}`);
  expect(summary.ok()).toBeTruthy();
  const payerSummary = await summary.json();
  expect(payerSummary.payments.map((row) => row.amount_minor)).toEqual([60000]);
  expect(payerSummary.obligations[0].remaining_minor).toBe(0);
  expect(payerSummary.ledger).toBeFalsy();
  await expect(payerPage.getByText("Remaining $0.00")).toBeVisible();
  await expect(payerPage.getByRole("cell", { name: "$600.00" })).toBeVisible();
  await expect(payerPage.getByText("$400.00")).toHaveCount(0);

  const hiddenSummary = await payerPage.request.get(`/api/v2/payments/summary?tenancy_code=${encodeURIComponent(other)}`);
  expect(hiddenSummary.ok()).toBeTruthy();
  expect((await hiddenSummary.json()).obligations).toEqual([]);
  const replay = await payerPage.request.post("/api/v2/payments/payers/accept", {
    headers: csrfHeaders(await payer.cookies()),
    data: { invitation_token: grantToken },
  });
  expect(replay.status()).toBe(409);

  await residentPage.getByRole("button", { name: "Send invitation" }).click();
  await expect(residentPage.getByText("The invitation was sent.")).toBeVisible();
  const secondToken = await mailToken(payerEmail, "Your synthetic PerchPoint payment invitation", grantToken);
  const second = await payerPage.request.post("/api/v2/payments/payers/accept", {
    headers: csrfHeaders(await payer.cookies()),
    data: { invitation_token: secondToken },
  });
  expect(second.status()).toBe(409);

  await residentPage.getByRole("button", { name: "Revoke additional payer" }).click();
  await expect(residentPage.getByText("The additional payer can no longer start a payment.")).toBeVisible();
  const stale = await payerPage.request.post("/api/v2/payments/checkout", {
    headers: csrfHeaders(await payer.cookies()),
    data: {
      obligation_reference: payerSummary.obligations[0].reference,
      amount_minor: 100,
      method: "card",
      idempotency_key: `stale-${stamp}`,
    },
  });
  expect([403, 404]).toContain(stale.status());

  await operations.close();
  await resident.close();
  await payer.close();
});

async function postOk(api, headers, url, data) {
  const response = await api.post(url, { headers, data });
  if (!response.ok()) throw new Error(`${url} returned ${response.status()} ${await response.text()}`);
  return response.json();
}

async function prepareLinkedAccount(api, headers, stamp) {
  const key = (name) => `${name}-${stamp}`;
  const label = `P17 ${stamp} Synthetic Court`;
  const property = await postOk(api, headers, "/api/v2/properties", { name: label, property_type: "mixed_use", idempotency_key: key("prop") });
  const building = await postOk(api, headers, "/api/v2/buildings", { property_id: property.id, name: "Primary", allowed_uses: ["residential"], idempotency_key: key("bldg") });
  const space = await postOk(api, headers, "/api/v2/spaces", { property_id: property.id, building_id: building.id, label, use: "residential", square_feet: 900, idempotency_key: key("space") });
  const listing = await postOk(api, headers, "/api/v2/listings", { space_id: space.id, property_name: label, label, use: "residential", municipality: "Cincinnati", state: "OH", amount_minor: 100000, currency: "USD", idempotency_key: key("listing") });
  for (const [availability, day, name] of [["coming_soon", "2026-10-01", "soon"], ["available", "2026-10-15", "open"]]) {
    await postOk(api, headers, "/api/v2/portfolio/availability", { space_id: space.id, availability, effective_on: day, confidence: "exact", source: "manager_confirmation", reason: "Synthetic payer account availability.", idempotency_key: key(name) });
  }
  await postOk(api, headers, "/api/v2/portfolio/prices", { space_id: space.id, amount_minor: 100000, currency: "USD", period: "monthly", effective_on: "2026-10-01", reason: "Synthetic asking rent.", idempotency_key: key("price") });
  await postOk(api, headers, "/api/v2/portfolio/media", { space_id: space.id, content: "JFIF-synthetic-front", signature: "JFIF", declared_mime: "image/jpeg", alt_text: "Synthetic front of the home", rights_state: "licensed", idempotency_key: key("media") });
  const published = await postOk(api, headers, "/api/v2/portfolio/snapshots", { listing_id: listing.id, expected_version: 1, public_slug: `p17-${stamp}`, description: "EXAMPLE ONLY. Synthetic listing facts.", idempotency_key: key("publish") });
  await postOk(api, headers, "/api/v2/discovery/project", { snapshot_id: published.id, bedrooms: 2, idempotency_key: key("project") });
  const applicant = `casey.${stamp}@example.com`;
  const inquiry = await postOk(api, null, "/api/v2/public/leasing/inquiries", { name: "Casey Synthetic", email: applicant, message: "Synthetic portal interest.", disclosure: true, public_slug: `p17-${stamp}`, idempotency_key: key("intake") });
  const started = await postOk(api, null, "/api/v2/public/applications", { receipt: inquiry.receipt, disclosure: true, preferred_name: "Casey", legal_name: "Casey Synthetic", email: applicant, idempotency_key: key("start") });
  const saved = await postOk(api, null, "/api/v2/public/applications/answers", { capability: started.capability, field_code: "income_status", field_value: "employed", expected_version: 1 });
  await postOk(api, null, "/api/v2/public/applications/documents", { capability: started.capability, document_class: "income_evidence", display_name: "pay.txt", content: "JFIF-synthetic-pay", magic: "JFIF" });
  const submitted = await postOk(api, null, "/api/v2/public/applications/submit", { capability: started.capability, idempotency_key: key("submit"), expected_version: saved.version, attestation: true });
  await postOk(api, headers, "/api/v2/leasing/applications/handoff", { reference: submitted.reference });
  const screening = await postOk(api, headers, "/api/v2/leasing/screening/cases", { application_reference: submitted.reference, idempotency_key: key("case") });
  await postOk(api, null, "/api/v2/public/screening/authorization", { capability: screening.capability });
  await postOk(api, null, "/api/v2/public/screening/orders", { capability: screening.capability, product: "credit", idempotency_key: key("credit") });
  const coverage = JSON.stringify({ coverage: "complete" });
  const screeningSignature = crypto.createHmac("sha256", "local-only-not-production-webhook").update(coverage).digest("hex");
  const screened = await api.post("/api/v2/public/screening/results", {
    data: coverage,
    headers: { "content-type": "application/json", "x-perchpoint-capability": screening.capability, "x-perchpoint-coverage": "complete", "x-perchpoint-signature": screeningSignature },
  });
  if (!screened.ok()) throw new Error(`/api/v2/public/screening/results returned ${screened.status()}`);
  await postOk(api, headers, "/api/v2/leasing/screening/decisions", { reference: screening.reference, outcome: "approved", human_confirmed: true });
  await postOk(api, headers, "/api/v2/leasing/screening/handoff", { reference: screening.reference });
  const deal = await postOk(api, headers, "/api/v2/leasing/leases/deals", { screening_reference: screening.reference, idempotency_key: key("deal") });
  await postOk(api, headers, "/api/v2/leasing/leases/approvals", { reference: deal.reference, human_confirmed: true });
  await postOk(api, null, "/api/v2/public/leases/signatures", { capability: deal.capability, idempotency_key: key("sign") });
  const leaseSignature = crypto.createHmac("sha256", "local-only-not-production-webhook").update(coverage).digest("hex");
  const signed = await api.post("/api/v2/public/leases/signatures/events", {
    data: coverage,
    headers: { "content-type": "application/json", "x-perchpoint-capability": deal.capability, "x-perchpoint-signature": leaseSignature },
  });
  if (!signed.ok()) throw new Error(`/api/v2/public/leases/signatures/events returned ${signed.status()}`);
  await postOk(api, headers, "/api/v2/leasing/leases/deposits", { reference: deal.reference });
  await postOk(api, headers, "/api/v2/leasing/leases/activations", { reference: deal.reference, idempotency_key: key("activate") });
  const membership = await postOk(api, headers, "/api/v2/leasing/portal/memberships", { reference: deal.reference, idempotency_key: key("portal") });
  await postOk(api, null, "/api/v2/public/portal/invitations", { capability: membership.capability, idempotency_key: key("accept") });
  const account = await postOk(api, headers, "/api/v2/leasing/ledger/accounts", { reference: membership.reference, idempotency_key: key("account") });
  return { tenancy: deal.reference, account: account.reference };
}

test("linked household charge settles through the worker", async ({ browser }) => {
  test.setTimeout(360000);
  const stamp = Date.now().toString(36);
  const residentEmail = `resident.linked.${stamp}@example.com`;
  const payerEmail = `payer.linked.${stamp}@example.com`;
  const operations = await browser.newContext();
  const resident = await browser.newContext();
  const payer = await browser.newContext();
  const opsPage = await operations.newPage();
  const residentPage = await resident.newPage();
  const payerPage = await payer.newPage();
  await signIn(opsPage, "operations@demo.perchpoint.invalid", localPassword());
  await expect(opsPage).toHaveURL(/leasing-desk/);
  const setup = await playwrightRequest.newContext({ baseURL: "http://127.0.0.1:3000" });
  const session = await setup.post("/api/v2/session", {
    data: { email: "ann.synthetic@example.com", password: "local-only-not-production-password" },
  });
  expect(session.ok(), await session.text()).toBeTruthy();
  const linked = await prepareLinkedAccount(setup, {
    Authorization: `Bearer ${(await session.json()).token}`,
    origin: "http://127.0.0.1:3000",
  }, stamp);
  await setup.dispose();
  const headers = csrfHeaders(await operations.cookies());
  for (const [email, role] of [[residentEmail, "resident"], [payerEmail, "additional_payer"]]) {
    const invited = await opsPage.request.post("/api/v2/auth/invitations", {
      headers,
      data: { email, role_name: role, purpose: "Linked payer scenario", staff: false },
    });
    expect(invited.ok(), await invited.text()).toBeTruthy();
  }
  await acceptIdentity(residentPage, residentEmail, await mailToken(residentEmail, "Your synthetic PerchPoint invitation"));
  await acceptIdentity(payerPage, payerEmail, await mailToken(payerEmail, "Your synthetic PerchPoint invitation"));
  await opsPage.getByRole("link", { name: "Accounts" }).click();
  await opsPage.getByLabel("Tenancy code").fill(linked.tenancy);
  await opsPage.getByLabel("Ledger account").fill(linked.account);
  await opsPage.locator("form", { hasText: "Publish a payable charge" }).getByLabel("Amount in dollars").fill("1000");
  await opsPage.getByLabel("Description").fill("Linked household rent charge");
  await opsPage.getByRole("button", { name: "Publish charge" }).click();
  await expect(opsPage.getByText("The charge is payable.")).toBeVisible();
  const linkedResident = await opsPage.request.post("/api/v2/payments/charges/resident", {
    headers,
    data: { tenancy_code: linked.tenancy, email: residentEmail },
  });
  expect(linkedResident.ok(), await linkedResident.text()).toBeTruthy();
  const organization = (await (await opsPage.request.get("/api/v2/auth/me")).json()).organization_id;
  let ledger = await staffSummary(opsPage, linked.tenancy);
  expect(ledger.ledger.due_minor).toBe(100000);
  expect(ledger.ledger.charge_count).toBe(1);
  expect(ledger.ledger.settlement_count).toBe(0);
  expect(ledger.obligations[0].due_on).toBe(new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date()));
  await opsPage.getByLabel("Amount to record").fill("400");
  await opsPage.getByRole("button", { name: "Record synthetic collection" }).click();
  await expect(opsPage.getByText("Collection is processing.")).toBeVisible();
  expect((await staffSummary(opsPage, linked.tenancy)).ledger.due_minor).toBe(100000);
  const first = await deliverProcessing(opsPage, organization, linked.tenancy, 40000);
  expect(first.summary.ledger.due_minor).toBe(60000);
  expect(first.summary.ledger.settlement_count).toBe(1);
  await signIn(residentPage, residentEmail, payerPassword);
  await residentPage.getByLabel("Household code").fill(linked.tenancy);
  await residentPage.getByRole("button", { name: "Open household" }).click();
  await residentPage.getByLabel("Email").fill(payerEmail);
  await residentPage.getByRole("button", { name: "Send invitation" }).click();
  await expect(residentPage.getByText("The invitation was sent.")).toBeVisible();
  const grantToken = await mailToken(payerEmail, "Your synthetic PerchPoint payment invitation");
  await signIn(payerPage, payerEmail, payerPassword);
  await expect(payerPage).toHaveURL(/\/pay$/);
  await payerPage.goto(`/pay?token=${encodeURIComponent(grantToken)}`);
  await payerPage.getByRole("button", { name: "Accept invitation" }).click();
  await expect(payerPage.getByText("You can pay the granted charges.")).toBeVisible();
  await payerPage.getByLabel("Amount to pay").fill("1000");
  await payerPage.getByRole("button", { name: "Pay $1,000.00" }).click();
  await expect(payerPage.getByText("That amount is more than the eligible balance.")).toBeVisible();
  expect((await staffSummary(opsPage, linked.tenancy)).ledger.settlement_count).toBe(1);
  await payerPage.getByLabel("Amount to pay").fill("600");
  await payerPage.getByRole("button", { name: "Pay $600.00" }).click();
  await expect(payerPage.getByText("Payment is processing.")).toBeVisible();
  expect((await staffSummary(opsPage, linked.tenancy)).ledger.due_minor).toBe(60000);
  const second = await deliverProcessing(opsPage, organization, linked.tenancy, 60000);
  expect(second.summary.ledger.due_minor).toBe(0);
  expect(second.summary.ledger.settlement_count).toBe(2);
  expect(second.summary.ledger.charge_count).toBe(1);
  const replay = await opsPage.request.post("/api/v2/payments/provider-events", {
    headers: { "content-type": "application/json", "x-perchpoint-provider-signature": first.signature },
    data: first.raw,
  });
  expect(replay.ok()).toBeTruthy();
  expect((await replay.json()).duplicate).toBe(true);
  expect((await staffSummary(opsPage, linked.tenancy)).ledger.settlement_count).toBe(2);
  await payerPage.reload();
  const payerSummary = await (await payerPage.request.get(`/api/v2/payments/summary?tenancy_code=${encodeURIComponent(linked.tenancy)}`)).json();
  expect(payerSummary.payments.map((row) => row.amount_minor)).toEqual([60000]);
  expect(payerSummary.obligations[0].remaining_minor).toBe(0);
  expect(payerSummary.ledger).toBeFalsy();
  await operations.close();
  await resident.close();
  await payer.close();
});

test("scheduled autopay finishes after the browser closes", async ({ browser }) => {
  const stamp = Date.now().toString(36);
  const setup = await playwrightRequest.newContext({ baseURL: "http://127.0.0.1:3000" });
  const session = await setup.post("/api/v2/session", {
    data: { email: "ann.synthetic@example.com", password: "local-only-not-production-password" },
  });
  expect(session.ok(), await session.text()).toBeTruthy();
  const sessionBody = await session.json();
  const headers = { Authorization: `Bearer ${sessionBody.token}`, origin: "http://127.0.0.1:3000" };
  const linked = await prepareLinkedAccount(setup, headers, `auto${stamp}`);
  const obligation = await postOk(setup, headers, "/api/v2/payments/charges", {
    tenancy_code: linked.tenancy,
    amount_minor: 100000,
    category: "rent",
    description: "Autopay remainder after the browser closes",
    account_reference: linked.account,
    rent_basis_minor: 100000,
    idempotency_key: `publish-auto-${stamp}`,
  });
  await postOk(setup, headers, "/api/v2/payments/checkout", {
    obligation_reference: obligation.reference,
    amount_minor: 40000,
    method: "card",
    scenario: "succeeded",
    idempotency_key: `pay-auto-${stamp}`,
  });
  await postOk(setup, headers, "/api/v2/payments/autopay", {
    tenancy_code: linked.tenancy,
    cap_minor: 100000,
    day_of_month: 15,
  });
  const operations = await browser.newContext();
  const opsPage = await operations.newPage();
  await signIn(opsPage, "operations@demo.perchpoint.invalid", localPassword());
  await expect(opsPage).toHaveURL(/leasing-desk/);
  await opsPage.getByRole("link", { name: "Accounts" }).click();
  await opsPage.getByLabel("Tenancy code").fill(linked.tenancy);
  await opsPage.getByLabel("Tenancy code").blur();
  await expect(opsPage.getByText("Remaining $600.00")).toBeVisible();
  await expect(opsPage.getByText(/Next collection/)).toBeVisible();
  await operations.close();

  const scheduled = spawn("python", ["-m", "perchpoint.phase17_worker"], {
    cwd: path.join(__dirname, "../../backend"),
    env: { ...workerEnv(), PHASE17_CLOCK: "2026-10-15T12:00:00-04:00", PHASE17_AUTOPAY_SCENARIO: "callback" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  try {
    await expect.poll(async () => {
      const summary = await setup.get(`/api/v2/payments/summary?tenancy_code=${encodeURIComponent(linked.tenancy)}`, { headers });
      const body = await summary.json();
      return (body.payments || []).some((row) => row.state === "processing" && row.amount_minor === 60000);
    }, { timeout: 20000 }).toBeTruthy();
    const processing = await (await setup.get(`/api/v2/payments/summary?tenancy_code=${encodeURIComponent(linked.tenancy)}`, { headers })).json();
    expect(processing.ledger.settlement_count).toBe(1);
    expect(processing.ledger.due_minor).toBe(60000);
    const payment = processing.payments.find((row) => row.amount_minor === 60000);
    const payload = {
      id: `evt-browser-${payment.public_reference}`,
      organization_id: sessionBody.organization_id,
      type: "payment.succeeded",
      effect_key: payment.public_reference,
      amount_minor: 60000,
      environment: "local_fake",
    };
    const raw = JSON.stringify(payload);
    const signature = crypto.createHmac("sha256", webhookSecret).update(raw).digest("hex");
    const posted = await setup.post("/api/v2/payments/provider-events", {
      headers: { "content-type": "application/json", "x-perchpoint-provider-signature": signature },
      data: raw,
    });
    expect(posted.ok(), await posted.text()).toBeTruthy();
    await expect.poll(async () => {
      const summary = await setup.get(`/api/v2/payments/summary?tenancy_code=${encodeURIComponent(linked.tenancy)}`, { headers });
      const body = await summary.json();
      return Boolean(body.ledger && body.ledger.due_minor === 0 && body.ledger.settlement_count === 2);
    }, { timeout: 20000 }).toBeTruthy();
  } finally {
    if (!scheduled.killed) scheduled.kill();
    await setup.dispose();
  }

  const reopened = await browser.newContext();
  const reopenedPage = await reopened.newPage();
  await signIn(reopenedPage, "operations@demo.perchpoint.invalid", localPassword());
  await expect(reopenedPage).toHaveURL(/leasing-desk/);
  await reopenedPage.getByRole("link", { name: "Accounts" }).click();
  await reopenedPage.getByLabel("Tenancy code").fill(linked.tenancy);
  await reopenedPage.getByLabel("Tenancy code").blur();
  await expect(reopenedPage.getByText("Remaining $0.00")).toBeVisible();
  await expect(reopenedPage.getByText(/Latest 2026-10: collected/)).toBeVisible();
  await expect(reopenedPage.getByRole("cell", { name: "$600.00" })).toBeVisible();
  const visible = await reopenedPage.request.get(`/api/v2/payments/summary?tenancy_code=${encodeURIComponent(linked.tenancy)}`);
  expect(visible.ok()).toBeTruthy();
  const body = await visible.json();
  expect(body.ledger.charge_count).toBe(1);
  expect(body.ledger.settlement_count).toBe(2);
  expect(body.ledger.due_minor).toBe(0);
  await reopened.close();
});

test("staff records a ledger settlement and reversal from Accounts", async ({ browser }) => {
  const stamp = Date.now().toString(36);
  const setup = await playwrightRequest.newContext({ baseURL: "http://127.0.0.1:3000" });
  const session = await setup.post("/api/v2/session", {
    data: { email: "ann.synthetic@example.com", password: "local-only-not-production-password" },
  });
  expect(session.ok(), await session.text()).toBeTruthy();
  const linked = await prepareLinkedAccount(setup, {
    Authorization: `Bearer ${(await session.json()).token}`,
    origin: "http://127.0.0.1:3000",
  }, stamp);
  await setup.dispose();

  const operations = await browser.newContext();
  const page = await operations.newPage();
  await signIn(page, "operations@demo.perchpoint.invalid", localPassword());
  await page.getByRole("link", { name: "Accounts" }).click();
  await page.getByLabel("Tenancy code").fill(linked.tenancy);
  await page.getByLabel("Ledger account").fill(linked.account);
  await page.getByLabel("Amount in dollars").first().fill("1000");
  await page.getByLabel("Description").fill("Linked household rent charge");
  await page.getByRole("button", { name: "Publish charge" }).click();
  await expect(page.getByText("The charge is payable.")).toBeVisible();

  const settlement = page.locator("form", { has: page.getByRole("button", { name: "Record settlement" }) });
  await settlement.getByLabel("Amount in dollars").fill("100");
  await settlement.getByRole("button", { name: "Record settlement" }).click();
  await expect(page.getByText("Settlement recorded. Amount due $900.00. No money has moved.")).toBeVisible();

  const reversal = page.locator("form", { has: page.getByRole("button", { name: "Reverse charge" }) });
  await reversal.getByLabel("Charge").selectOption({ index: 1 });
  await reversal.getByRole("button", { name: "Reverse charge" }).click();
  await expect(page.getByText("The charge was reversed with a new entry. The original lines were not edited.")).toBeVisible();

  const summary = await page.request.get(`/api/v2/payments/summary?tenancy_code=${encodeURIComponent(linked.tenancy)}`);
  expect(summary.ok(), await summary.text()).toBeTruthy();
  const body = await summary.json();
  expect(body.ledger.account_reference).toBe(linked.account);
  expect(body.ledger.journals.filter((row) => row.kind === "charge")).toHaveLength(1);
  expect(body.ledger.journals.filter((row) => row.kind === "settlement").length).toBeGreaterThan(0);
  expect(body.ledger.journals.filter((row) => row.kind === "reversal")).toHaveLength(1);
  await operations.close();
});

test("owner approves one exact refund from the owner workspace", async ({ browser }) => {
  const stamp = Date.now().toString(36);
  const tenancy = `owner-exception-${stamp}`;
  const operations = await browser.newContext();
  const owner = await browser.newContext();
  const opsPage = await operations.newPage();
  const ownerPage = await owner.newPage();
  await signIn(opsPage, "operations@demo.perchpoint.invalid", localPassword());
  await expect(opsPage.getByRole("link", { name: "Accounts" })).toBeVisible();
  const headers = csrfHeaders(await operations.cookies());
  const charge = await opsPage.request.post("/api/v2/payments/charges", {
    headers,
    data: {
      tenancy_code: tenancy,
      amount_minor: 200000,
      category: "rent",
      description: "Disposable owner exception rent",
      rent_basis_minor: 100000,
      idempotency_key: `owner-charge-${stamp}`,
    },
  });
  expect(charge.ok(), await charge.text()).toBeTruthy();
  const paid = await opsPage.request.post("/api/v2/payments/checkout", {
    headers,
    data: {
      obligation_reference: (await charge.json()).reference,
      amount_minor: 200000,
      method: "card",
      scenario: "succeeded",
      idempotency_key: `owner-pay-${stamp}`,
    },
  });
  expect(paid.ok(), await paid.text()).toBeTruthy();
  await opsPage.getByRole("link", { name: "Accounts" }).click();
  await opsPage.getByLabel("Tenancy code").fill(tenancy);
  await opsPage.getByLabel("Tenancy code").blur();
  const refund = opsPage.locator("form", { has: opsPage.getByRole("button", { name: "Submit refund" }) });
  await refund.getByLabel("Source payment").selectOption({ index: 1 });
  await refund.getByLabel("Amount in dollars").fill("1200");
  await refund.getByLabel("Internal explanation").fill("Resident asked for a larger refund.");
  await refund.getByLabel("Resident-facing explanation").fill("We are reviewing this refund.");
  await refund.getByRole("button", { name: "Submit refund" }).click();
  await expect(opsPage.getByText("Refund owner_decision_required. No money has moved.")).toBeVisible();

  await signIn(ownerPage, "dossnathan@gmail.com", localPassword());
  await expect(ownerPage.getByRole("heading", { name: "Owner workspace" })).toBeVisible();
  await expect(ownerPage.getByText(tenancy)).toBeVisible();
  await ownerPage.getByLabel("Reason for an exact exception").fill("Exact owner approval for this refund.");
  const decision = ownerPage.getByRole("listitem").filter({ hasText: tenancy });
  await decision.getByRole("button", { name: "Approve exact amount" }).click();
  await expect(ownerPage.getByText("The exact exception was recorded. The ordinary cap was not reset.")).toBeVisible();
  await operations.close();
  await owner.close();
});
