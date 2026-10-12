const { test, expect, request: playwrightRequest } = require("@playwright/test");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

function localPassword() {
  const text = fs.readFileSync(path.join(__dirname, "../../backend/.env.demo.local"), "utf8");
  const line = text.split(/\r?\n/).find((row) => row.startsWith("PERCHPOINT_LOCAL_DEMO_PASSWORD="));
  if (!line) throw new Error("local demo password file is missing the expected key");
  return line.split("=").slice(1).join("=").trim();
}

async function signIn(page, email, password = localPassword()) {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(email);
  await page.getByRole("textbox", { name: "Password" }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("operations can open assistance and a resident cannot match a receipt", async ({ browser }) => {
  const operations = await browser.newContext();
  const resident = await browser.newContext();
  const opsPage = await operations.newPage();
  const residentPage = await resident.newPage();

  await signIn(opsPage, "operations@demo.perchpoint.invalid");
  await expect(opsPage.getByRole("button", { name: "Sign out" })).toBeVisible();
  await opsPage.goto("/payments/assistance");
  await expect(opsPage.getByRole("heading", { name: "Digital payments and assistance" })).toBeVisible();
  await opsPage.getByLabel("Find a household").fill("Nia");
  await opsPage.getByRole("button", { name: "Search" }).click();
  await opsPage.getByRole("button", { name: "Open the operations queue" }).click();
  await expect(opsPage.getByText(/Nothing is waiting|Apply match|Awaiting verification|transfer report|resident overpayment|required return/).first()).toBeVisible();

  await signIn(residentPage, "dossnathan2@gmail.com");
  await expect(residentPage.getByRole("button", { name: "Sign out" })).toBeVisible();
  await residentPage.goto("/payments/assistance");
  await expect(residentPage.getByRole("heading", { name: "Digital payments and assistance" })).toBeVisible();
  await residentPage.getByRole("button", { name: "Open the operations queue" }).click();
  await expect(residentPage.getByRole("status")).toContainText(/not authorized|operations task|not available|does not allow this action/i);
  await operations.close();
  await resident.close();
});

function workerEnv() {
  return {
    ...process.env,
    PYTHONUNBUFFERED: "1",
    PHASE3_ENVIRONMENT: "local",
    PHASE2_LOCAL_AUTH: "development",
    PHASE18_WORKER_ONCE: "1",
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

function csrfHeaders(cookies) {
  const token = cookies.find((item) => item.name === "pp_csrf");
  return { origin: "http://127.0.0.1:3000", "x-perchpoint-csrf": token ? token.value : "" };
}

async function postOk(api, headers, url, data) {
  const response = await api.post(url, { headers, data });
  if (!response.ok()) throw new Error(`${url} returned ${response.status()} ${await response.text()}`);
  return response.json();
}

async function mailToken(email) {
  for (let attempt = 0; attempt < 25; attempt += 1) {
    const listing = await fetch("http://127.0.0.1:8125/api/v1/messages").then((response) => response.json());
    const matches = (listing.messages || []).filter((item) => (
      item.Subject === "Your synthetic PerchPoint invitation"
      && (item.To || []).some((recipient) => (recipient.Address || "").toLowerCase() === email.toLowerCase())
    )).sort((left, right) => new Date(right.Created) - new Date(left.Created));
    if (matches[0]) {
      const message = await fetch(`http://127.0.0.1:8125/api/v1/message/${matches[0].ID}`).then((response) => response.json());
      const text = String(message.Text || "").replace(/=\r?\n/g, "");
      const found = text.match(/token=([A-Za-z0-9_\-]+)/);
      if (found) return found[1];
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error("local delivery did not include the expected invitation");
}

async function acceptIdentity(page, email, token) {
  await page.goto("/invitation");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Invitation token").fill(token);
  await page.getByLabel("Create password").fill("Synthetic invitation password 2046!");
  await page.getByRole("button", { name: "Accept invitation" }).click();
  await expect(page.getByText("Invitation accepted")).toBeVisible();
}

async function openDisposableBooks(api, headers, stamp) {
  const key = (name) => `${name}-${stamp}`;
  const label = `P18 ${stamp} Synthetic Court`;
  const property = await postOk(api, headers, "/api/v2/properties", { name: label, property_type: "mixed_use", idempotency_key: key("prop") });
  const building = await postOk(api, headers, "/api/v2/buildings", { property_id: property.id, name: "Primary", allowed_uses: ["residential"], idempotency_key: key("bldg") });
  const space = await postOk(api, headers, "/api/v2/spaces", { property_id: property.id, building_id: building.id, label, use: "residential", square_feet: 900, idempotency_key: key("space") });
  const listing = await postOk(api, headers, "/api/v2/listings", { space_id: space.id, property_name: label, label, use: "residential", municipality: "Cincinnati", state: "OH", amount_minor: 150000, currency: "USD", idempotency_key: key("listing") });
  for (const [availability, day, name] of [["coming_soon", "2026-10-01", "soon"], ["available", "2026-10-15", "open"]]) {
    await postOk(api, headers, "/api/v2/portfolio/availability", { space_id: space.id, availability, effective_on: day, confidence: "exact", source: "manager_confirmation", reason: "Synthetic assistance availability.", idempotency_key: key(name) });
  }
  await postOk(api, headers, "/api/v2/portfolio/prices", { space_id: space.id, amount_minor: 150000, currency: "USD", period: "monthly", effective_on: "2026-10-01", reason: "Synthetic asking rent.", idempotency_key: key("price") });
  await postOk(api, headers, "/api/v2/portfolio/media", { space_id: space.id, content: "JFIF-synthetic-front", signature: "JFIF", declared_mime: "image/jpeg", alt_text: "Synthetic front of the home", rights_state: "licensed", idempotency_key: key("media") });
  const published = await postOk(api, headers, "/api/v2/portfolio/snapshots", { listing_id: listing.id, expected_version: 1, public_slug: `p18-${stamp}`, description: "EXAMPLE ONLY. Synthetic listing facts.", idempotency_key: key("publish") });
  await postOk(api, headers, "/api/v2/discovery/project", { snapshot_id: published.id, bedrooms: 2, idempotency_key: key("project") });
  const applicant = `casey.${stamp}@example.com`;
  const inquiry = await postOk(api, null, "/api/v2/public/leasing/inquiries", { name: "Casey Synthetic", email: applicant, message: "Synthetic portal interest.", disclosure: true, public_slug: `p18-${stamp}`, idempotency_key: key("intake") });
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

async function chooseHousehold(page, label) {
  const select = page.getByRole("combobox", { name: "Household", exact: true });
  const option = select.locator("option", { hasText: label });
  await expect(option).toBeAttached();
  await select.selectOption(await option.getAttribute("value"));
}

function dueAmount(page, name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return page.locator("div").filter({ hasText: new RegExp(`^${escaped}\\$`) }).getByRole("definition");
}

async function runWorkerOnce() {
  const child = spawn("python", ["-m", "perchpoint.phase17_worker"], {
    cwd: path.join(__dirname, "../../backend"),
    env: workerEnv(),
    stdio: ["ignore", "pipe", "pipe"],
  });
  let output = "";
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`worker did not finish: ${output}`)), 30000);
    child.stdout.on("data", (chunk) => {
      output += String(chunk);
      if (output.includes("phase18-worker-once")) {
        clearTimeout(timer);
        resolve();
      }
    });
    child.on("exit", (code) => {
      if (!output.includes("phase18-worker-once")) {
        clearTimeout(timer);
        reject(new Error(`worker exited ${code}: ${output}`));
      }
    });
  });
  return output;
}

test("resident transfer is matched once and the worker posts the resident portion", async ({ browser }) => {
  test.setTimeout(360000);
  const stamp = Date.now().toString(36);
  const label = `Nia Disposable ${stamp}`;
  const residentEmail = `resident.p18.${stamp}@example.com`;
  const bankReference = `bank-${stamp}`;
  const operations = await browser.newContext();
  const resident = await browser.newContext();
  const stranger = await browser.newContext();
  const opsPage = await operations.newPage();
  const residentPage = await resident.newPage();
  const strangerPage = await stranger.newPage();

  await signIn(opsPage, "operations@demo.perchpoint.invalid");
  await expect(opsPage.getByRole("button", { name: "Sign out" })).toBeVisible();
  const headers = csrfHeaders(await operations.cookies());
  const setup = await playwrightRequest.newContext({ baseURL: "http://127.0.0.1:3000" });
  const session = await setup.post("/api/v2/session", {
    data: { email: "ann.synthetic@example.com", password: "local-only-not-production-password" },
  });
  expect(session.ok(), await session.text()).toBeTruthy();
  const books = await openDisposableBooks(setup, {
    Authorization: `Bearer ${(await session.json()).token}`,
    origin: "http://127.0.0.1:3000",
  }, stamp);
  await setup.dispose();
  const invited = await opsPage.request.post("/api/v2/auth/invitations", {
    headers,
    data: { email: residentEmail, role_name: "resident", purpose: "Disposable assistance resident", staff: false },
  });
  expect(invited.ok(), await invited.text()).toBeTruthy();
  await acceptIdentity(residentPage, residentEmail, await mailToken(residentEmail));
  const determination = await opsPage.request.post("/api/v2/payments/assistance/determinations", {
    headers,
    data: {
      tenancy_code: books.tenancy,
      account_reference: books.account,
      household_label: label,
      resident_email: residentEmail,
      program_kind: "hcv",
      agency_name: "Synthetic housing agency",
      service_period: "2026-11",
      rent_to_owner_minor: 150000,
      resident_minor: 40000,
      agency_minor: 110000,
      idempotency_key: `determination-${stamp}`,
    },
  });
  expect(determination.ok(), await determination.text()).toBeTruthy();
  const enrolled = await opsPage.request.post("/api/v2/payments/autopay", {
    headers,
    data: { tenancy_code: books.tenancy, cap_minor: 40000, day_of_month: 1 },
  });
  expect(enrolled.ok(), await enrolled.text()).toBeTruthy();

  await opsPage.goto("/payments/assistance");
  await opsPage.getByLabel("Find a household").fill(label);
  await opsPage.getByRole("button", { name: "Search" }).click();
  await chooseHousehold(opsPage, label);
  await expect(dueAmount(opsPage, "Your portion")).toHaveText("$400.00");
  await expect(dueAmount(opsPage, "Agency portion")).toHaveText("$1,100.00");
  await expect(dueAmount(opsPage, "Amount due from you")).toHaveText("$400.00");

  await signIn(residentPage, residentEmail, "Synthetic invitation password 2046!");
  await expect(residentPage.getByRole("button", { name: "Sign out" })).toBeVisible();
  await residentPage.goto("/payments");
  await residentPage.getByLabel("Find a household").fill(label);
  await chooseHousehold(residentPage, label);
  await expect(residentPage.getByRole("status")).toContainText("Your portion for 2026-11 is $400.00");
  await expect(residentPage.getByRole("status")).toContainText("Agency assistance of $1,100.00 is not added");
  await residentPage.goto("/payments/assistance");
  await residentPage.getByLabel("Find a household").fill(label);
  await residentPage.getByRole("button", { name: "Search" }).click();
  await chooseHousehold(residentPage, label);
  await expect(dueAmount(residentPage, "Amount due from you")).toHaveText("$400.00");
  await residentPage.getByLabel("Amount you sent").fill("400.00");
  await residentPage.getByLabel("Reference").fill(`transfer-${stamp}`);
  await residentPage.getByLabel("Date sent").fill("2026-11-02");
  await residentPage.getByLabel("What should we know").fill("Already sent the resident portion");
  await residentPage.getByRole("button", { name: "Submit report" }).click();
  await expect(residentPage.getByRole("status")).toContainText("Awaiting verification. This report is not a payment.");
  await expect(residentPage.getByText("Awaiting verification · $400.00")).toBeVisible();

  await opsPage.getByRole("button", { name: "Open the operations queue" }).click();
  const report = opsPage.locator("li").filter({ hasText: label });
  await report.getByLabel("Bank reference").fill(bankReference);
  await report.getByRole("button", { name: "Confirm bank evidence" }).click();
  await expect(opsPage.getByRole("status")).toContainText("Verified transfer processing");
  const skipped = await opsPage.request.post("/api/v2/payments/autopay/run", {
    headers: csrfHeaders(await operations.cookies()),
    data: { tenancy_code: books.tenancy, period_code: "2026-11" },
  });
  expect(skipped.ok(), await skipped.text()).toBeTruthy();
  expect((await skipped.json()).reason).toBe("nothing_due");
  await residentPage.reload();
  await chooseHousehold(residentPage, label);
  await expect(residentPage.getByText("Verified transfer processing $400.00")).toBeVisible();
  await expect(dueAmount(residentPage, "Amount due from you")).toHaveText("$400.00");

  const workerOutput = await runWorkerOnce();
  expect(workerOutput).toContain("phase18-worker-once");
  await residentPage.reload();
  await chooseHousehold(residentPage, label);
  await expect(dueAmount(residentPage, "Amount due from you")).toHaveText("$0.00");
  await expect(dueAmount(residentPage, "Agency still expected")).toHaveText("$1,100.00");
  await expect(residentPage.getByText("Verified transfer processing")).toHaveCount(0);

  await opsPage.reload();
  await opsPage.getByRole("button", { name: "Open the operations queue" }).click();
  const replay = opsPage.locator("li").filter({ hasText: label });
  await expect(replay).toHaveCount(0);
  const again = await opsPage.request.post("/api/v2/payments/assistance/receipts", {
    headers: csrfHeaders(await operations.cookies()),
    data: {
      source: "business_bank",
      external_id: bankReference,
      method: "bank_transfer",
      purpose: "resident_rent",
      amount_minor: 40000,
      tenancy_code: books.tenancy,
      service_period: "2026-11",
      idempotency_key: `replay-${stamp}`,
    },
  });
  expect(again.ok(), await again.text()).toBeTruthy();
  expect((await again.json()).replayed).toBe(true);
  await residentPage.reload();
  await chooseHousehold(residentPage, label);
  await expect(dueAmount(residentPage, "Amount due from you")).toHaveText("$0.00");

  await signIn(strangerPage, "dossnathan2@gmail.com");
  await expect(strangerPage.getByRole("button", { name: "Sign out" })).toBeVisible();
  await strangerPage.goto("/payments/assistance");
  await strangerPage.getByLabel("Find a household").fill(label);
  const hiddenSearch = strangerPage.waitForResponse((response) => response.url().includes("/payments/assistance/households?q="));
  await strangerPage.getByRole("button", { name: "Search" }).click();
  await hiddenSearch;
  await expect(strangerPage.getByRole("combobox", { name: "Household", exact: true }).locator("option", { hasText: label })).toHaveCount(0);
  const hidden = await strangerPage.request.get(`/api/v2/payments/assistance/household?tenancy_code=${encodeURIComponent(books.tenancy)}`);
  expect(hidden.status()).toBe(403);

  await operations.close();
  await resident.close();
  await stranger.close();
});

test("a revised resident portion completes one required return", async ({ browser }) => {
  test.setTimeout(360000);
  const stamp = Date.now().toString(36);
  const label = `Nia Return ${stamp}`;
  const residentEmail = `resident.return.${stamp}@example.com`;
  const evidence = `bank-return-${stamp}ok`;
  const operations = await browser.newContext();
  const resident = await browser.newContext();
  const opsPage = await operations.newPage();
  const residentPage = await resident.newPage();

  await signIn(opsPage, "operations@demo.perchpoint.invalid");
  await expect(opsPage.getByRole("button", { name: "Sign out" })).toBeVisible();
  const headers = csrfHeaders(await operations.cookies());
  const setup = await playwrightRequest.newContext({ baseURL: "http://127.0.0.1:3000" });
  const session = await setup.post("/api/v2/session", {
    data: { email: "ann.synthetic@example.com", password: "local-only-not-production-password" },
  });
  expect(session.ok(), await session.text()).toBeTruthy();
  const books = await openDisposableBooks(setup, {
    Authorization: `Bearer ${(await session.json()).token}`,
    origin: "http://127.0.0.1:3000",
  }, stamp);
  await setup.dispose();
  const invited = await opsPage.request.post("/api/v2/auth/invitations", {
    headers,
    data: { email: residentEmail, role_name: "resident", purpose: "Disposable return resident", staff: false },
  });
  expect(invited.ok(), await invited.text()).toBeTruthy();
  await acceptIdentity(residentPage, residentEmail, await mailToken(residentEmail));
  const determination = await opsPage.request.post("/api/v2/payments/assistance/determinations", {
    headers,
    data: {
      tenancy_code: books.tenancy,
      account_reference: books.account,
      household_label: label,
      resident_email: residentEmail,
      program_kind: "hcv",
      agency_name: "Synthetic housing agency",
      service_period: "2026-11",
      rent_to_owner_minor: 150000,
      resident_minor: 40000,
      agency_minor: 110000,
      idempotency_key: `return-determination-${stamp}`,
    },
  });
  expect(determination.ok(), await determination.text()).toBeTruthy();
  const paid = await opsPage.request.post("/api/v2/payments/checkout", {
    headers,
    data: {
      obligation_reference: (await determination.json()).resident_obligation,
      amount_minor: 40000,
      method: "card",
      scenario: "succeeded",
      idempotency_key: `return-pay-${stamp}`,
    },
  });
  expect(paid.ok(), await paid.text()).toBeTruthy();
  const revised = await opsPage.request.post("/api/v2/payments/assistance/determinations", {
    headers,
    data: {
      tenancy_code: books.tenancy,
      account_reference: books.account,
      household_label: label,
      service_period: "2026-11",
      rent_to_owner_minor: 150000,
      resident_minor: 30000,
      agency_minor: 120000,
      idempotency_key: `return-revision-${stamp}`,
    },
  });
  expect(revised.ok(), await revised.text()).toBeTruthy();
  const household = await opsPage.request.get(`/api/v2/payments/assistance/household?tenancy_code=${encodeURIComponent(books.tenancy)}`);
  expect(household.ok(), await household.text()).toBeTruthy();
  const overpayment = (await household.json()).exceptions.find((item) => item.kind === "resident_overpayment");
  const refused = await opsPage.request.post("/api/v2/payments/assistance/returns", {
    headers,
    data: {
      exception_reference: overpayment.public_reference,
      recipient: "agency",
      idempotency_key: `return-agency-${stamp}`,
    },
  });
  expect(refused.status()).toBe(409);

  await signIn(residentPage, residentEmail, "Synthetic invitation password 2046!");
  await expect(residentPage.getByRole("button", { name: "Sign out" })).toBeVisible();
  await residentPage.goto("/payments/assistance");
  await residentPage.getByLabel("Find a household").fill(label);
  await residentPage.getByRole("button", { name: "Search" }).click();
  await chooseHousehold(residentPage, label);
  await expect(dueAmount(residentPage, "Your portion")).toHaveText("$300.00");
  await expect(dueAmount(residentPage, "Agency still expected")).toHaveText("$1,200.00");
  await expect(dueAmount(residentPage, "Amount due from you")).toHaveText("$0.00");
  await expect(residentPage.getByText("resident overpayment $100.00")).toBeVisible();

  await opsPage.goto("/payments/assistance");
  await opsPage.getByRole("button", { name: "Open the operations queue" }).click();
  const row = opsPage.locator("li").filter({ hasText: label }).filter({ hasText: "resident overpayment" });
  await row.getByRole("button", { name: "Open required return" }).click();
  await expect(opsPage.getByRole("status")).toContainText("open and unpaid");
  const completion = opsPage.locator("li").filter({ hasText: label }).filter({ hasText: "required return" });
  await completion.getByLabel("Verified bank evidence").fill(evidence);
  await completion.getByRole("button", { name: "Record verified completion" }).click();
  await expect(opsPage.getByRole("status")).toContainText("completed synthetic settlement");
  await expect(opsPage.locator("li").filter({ hasText: label }).getByRole("button", { name: "Open required return" })).toHaveCount(0);

  await residentPage.reload();
  await chooseHousehold(residentPage, label);
  const viewed = await residentPage.request.get(`/api/v2/payments/assistance/household?tenancy_code=${encodeURIComponent(books.tenancy)}`);
  expect(viewed.ok(), await viewed.text()).toBeTruthy();
  const viewedBody = await viewed.json();
  expect(viewedBody.resident_returned_minor, JSON.stringify({
    received: viewedBody.resident_received_minor,
    returned: viewedBody.resident_returned_minor,
    net: viewedBody.resident_net_minor,
    due: viewedBody.due_minor,
  })).toBe(10000);
  await expect(residentPage.locator("main")).toContainText("returned $100.00");
  await expect(dueAmount(residentPage, "Your portion")).toHaveText("$300.00");
  await expect(dueAmount(residentPage, "Amount due from you")).toHaveText("$0.00");
  await expect(dueAmount(residentPage, "Agency still expected")).toHaveText("$1,200.00");

  await operations.close();
  await resident.close();
});

test("an agency remittance keeps the offset and each resident balance", async ({ browser }) => {
  test.setTimeout(480000);
  const stamp = Date.now().toString(36);
  const operations = await browser.newContext();
  const operationsPage = await operations.newPage();
  await signIn(operationsPage, "operations@demo.perchpoint.invalid");
  await expect(operationsPage.getByRole("button", { name: "Sign out" })).toBeVisible();
  const headers = csrfHeaders(await operations.cookies());
  const setup = await playwrightRequest.newContext({ baseURL: "http://127.0.0.1:3000" });
  const session = await setup.post("/api/v2/session", {
    data: { email: "ann.synthetic@example.com", password: "local-only-not-production-password" },
  });
  expect(session.ok(), await session.text()).toBeTruthy();
  const staff = {
    Authorization: `Bearer ${(await session.json()).token}`,
    origin: "http://127.0.0.1:3000",
  };
  const lines = [
    ["Hap Cedar", 110000, "1100.00", "a"],
    ["Hap Birch", 90000, "900.00", "b"],
    ["Hap Alder", 80000, "800.00", "c"],
  ];
  for (const [name, agency, , suffix] of lines) {
    const label = `${name} ${stamp}`;
    const opened = await openDisposableBooks(setup, staff, `${stamp}-${suffix}`);
    await postOk(operationsPage.request, headers, "/api/v2/payments/assistance/determinations", {
      tenancy_code: opened.tenancy,
      account_reference: opened.account,
      service_period: "2026-11",
      household_label: label,
      program_kind: "hcv",
      agency_name: "Synthetic housing agency",
      rent_to_owner_minor: 10000 + agency,
      resident_minor: 10000,
      agency_minor: agency,
      idempotency_key: `hap-${suffix}-${stamp}`,
    });
  }
  await setup.dispose();
  await operationsPage.goto("/payments/assistance");
  await operationsPage.getByRole("heading", { name: "Digital payments and assistance" }).waitFor();
  await operationsPage.getByLabel("Remittance reference").fill(`hap-${stamp}`);
  await operationsPage.getByLabel("Bank deposit reference").fill(`cash-${stamp}`);
  await operationsPage.getByLabel("Prior-period offset").fill("200.00");
  for (const [index, [name, , dollars]] of lines.entries()) {
    const select = operationsPage.getByRole("combobox", { name: `Household line ${index + 1}` });
    const option = select.locator("option", { hasText: `${name} ${stamp}` });
    await expect(option).toBeAttached({ timeout: 20000 });
    await select.selectOption(await option.getAttribute("value"));
    await operationsPage.getByLabel(`Gross assistance line ${index + 1}`).fill(dollars);
  }
  await operationsPage.getByRole("button", { name: "Preview remittance" }).click();
  await expect(operationsPage.getByRole("heading", { name: "Proposed remittance" })).toBeVisible();
  await expect(dueAmount(operationsPage, "Gross assistance")).toHaveText("$2,800.00");
  await expect(dueAmount(operationsPage, "Prior-period offset")).toHaveText("$200.00");
  await expect(dueAmount(operationsPage, "Net confirmed cash")).toHaveText("$2,600.00");
  await expect(operationsPage.getByText("Not posted")).toBeVisible();
  await operationsPage.getByRole("button", { name: "Apply eligible rows" }).click();
  await expect(operationsPage.getByRole("status")).toContainText("unexplained remainder is $0.00");
  await expect(dueAmount(operationsPage, "Unexplained remainder")).toHaveText("$0.00");
  for (const [name] of lines) {
    await chooseHousehold(operationsPage, `${name} ${stamp}`);
    await expect(dueAmount(operationsPage, "Amount due from you")).toHaveText("$100.00");
    await expect(dueAmount(operationsPage, "Agency still expected")).toHaveText("$0.00");
  }
  await operations.close();
});
