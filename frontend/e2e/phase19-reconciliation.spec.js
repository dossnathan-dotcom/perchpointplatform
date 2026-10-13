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

test("the owner sees one October briefing and a resident is denied", async ({ browser }) => {
  const viewport = test.info().project.use.viewport;
  const owner = await browser.newContext({ viewport });
  const resident = await browser.newContext({ viewport });
  const ownerPage = await owner.newPage();
  const residentPage = await resident.newPage();
  await signIn(ownerPage, "dossnathan@gmail.com");
  await ownerPage.goto("/payments/reconciliation");
  await expect(ownerPage.getByRole("heading", { name: "Reconciliation" })).toBeVisible();
  await expect(ownerPage.getByText("$4,275.00").first()).toBeVisible();
  await expect(ownerPage.getByText("Sycamore House")).toBeVisible();
  await expect(ownerPage.getByText("Brookside House")).toBeVisible();
  await expect(ownerPage.getByText("Avery Morgan at Maple Court 101")).toBeVisible();
  await expect(ownerPage.getByText("$0.00 due")).toBeVisible();
  await ownerPage.getByRole("button", { name: "Acknowledge this snapshot" }).click();
  await expect(ownerPage.getByRole("status").filter({ hasText: "not resolved" })).toBeVisible();

  await signIn(residentPage, "dossnathan2@gmail.com");
  await residentPage.goto("/payments/reconciliation");
  await expect(residentPage.getByRole("alert")).toContainText("not allowed");
  await owner.close();
  await resident.close();
});
