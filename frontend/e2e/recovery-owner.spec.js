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
}

test("owner opens the past-due household statement", async ({ page }) => {
  await signIn(page, "dossnathan@gmail.com");
  await expect(page.getByRole("heading", { name: "Owner workspace" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Workspace" })).toBeVisible();
  await expect(page.getByText("$4,275.00")).toBeVisible();
  await page.screenshot({ path: "e2e/artifacts/owner-briefing.png", fullPage: true });
  await page.getByRole("link", { name: "Review Sycamore House" }).click();
  await expect(page.getByRole("heading", { name: "Reese Harper" })).toBeVisible();
  await expect(page.getByText("October 2026 rent")).toBeVisible();
  await page.screenshot({ path: "e2e/artifacts/owner-sycamore-account.png", fullPage: true });
  await page.getByRole("link", { name: "View sample lease" }).click();
  await expect(page.getByText("SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION").first()).toBeVisible();
  await expect(page.getByText("Sample signature: Reese Harper, resident.")).toBeVisible();
});

test("resident sees Maple Court and saves a contact request", async ({ page }) => {
  await signIn(page, "dossnathan2@gmail.com");
  await expect(page.locator("article").getByRole("heading", { name: "Avery Morgan" })).toBeVisible();
  await expect(page.getByText("Maple Court 101")).toBeVisible();
  await expect(page.getByText("$0.00").first()).toBeVisible();
  await page.screenshot({ path: "e2e/artifacts/resident-avery.png", fullPage: true });
  await page.getByLabel("What should staff update?").fill("Please update the daytime phone.");
  await page.getByRole("button", { name: "Submit request" }).click();
  await expect(page.getByText("Saved. Status: submitted.")).toBeVisible();
});
