const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

function localPassword() {
  const text = fs.readFileSync(path.join(__dirname, "../../backend/.env.demo.local"), "utf8");
  const line = text.split(/\r?\n/).find((row) => row.startsWith("PERCHPOINT_LOCAL_DEMO_PASSWORD="));
  if (!line) throw new Error("local demo password file is missing the expected key");
  return line.split("=").slice(1).join("=").trim();
}

async function signIn(page, email) {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(email);
  await page.getByRole("textbox", { name: "Password" }).fill(localPassword());
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
}

test("a resident can report, operations can see the queue, and a stale request cannot repaint the next case", async ({ browser }) => {
  const viewport = test.info().project.use.viewport;
  const resident = await browser.newContext({ viewport });
  const operations = await browser.newContext({ viewport });
  const residentPage = await resident.newPage();
  const operationsPage = await operations.newPage();
  await signIn(residentPage, "dossnathan2@gmail.com");
  await residentPage.goto("/portal/report");
  await expect(residentPage.getByRole("heading", { name: "Report a problem" })).toBeVisible();
  await expect(residentPage.getByText("911")).toBeVisible();
  const place = `Synthetic faucet ${Date.now()}`;
  await residentPage.getByLabel("Where is it?").fill(place);
  await residentPage.getByLabel("What is happening?").fill("The kitchen faucet drips into the sink.");
  await residentPage.getByRole("button", { name: "Submit report" }).click();
  await expect(residentPage.getByRole("status")).toContainText("Received");
  await residentPage.goto("/portal/requests");
  await expect(residentPage.getByRole("heading", { name: "My requests" })).toBeVisible();

  await signIn(operationsPage, "operations@demo.perchpoint.invalid");
  await operationsPage.goto("/maintenance");
  await expect(operationsPage.getByRole("heading", { name: "Maintenance" })).toBeVisible();
  await expect(operationsPage.getByText(place)).toBeVisible();

  const requests = residentPage.getByRole("button", { name: /Received/ });
  await expect(requests.nth(1)).toBeVisible();
  const latestPlace = (await requests.first().innerText()).split("·")[1].trim();
  let releaseFirst;
  const gate = new Promise((resolve) => { releaseFirst = resolve; });
  let seen = 0;
  await residentPage.route("**/api/v2/maintenance/mine/*", async (route) => {
    seen += 1;
    if (seen === 1) await gate;
    if (seen === 1) await route.fulfill({ status: 403, contentType: "application/json", body: "{\"detail\":{\"message\":\"denied\"}}" });
    else await route.continue();
  });
  await requests.nth(1).click();
  await requests.first().click();
  releaseFirst();
  await expect(residentPage.locator("section")).toContainText(latestPlace);
  await expect(residentPage.locator("section")).toContainText("Nobody is marked on the way.");
  await resident.close();
  await operations.close();
});
