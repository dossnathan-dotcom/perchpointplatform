const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

function localPassword() {
  const text = fs.readFileSync(path.join(__dirname, "../../backend/.env.demo.local"), "utf8");
  const line = text.split(/\r?\n/).find((row) => row.startsWith("PERCHPOINT_LOCAL_DEMO_PASSWORD="));
  if (!line) throw new Error("local demo password file is missing the expected key");
  return line.split("=").slice(1).join("=").trim();
}

test("operations reaches the charge form through Accounts", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("operations@demo.perchpoint.invalid");
  await page.getByRole("textbox", { name: "Password" }).fill(localPassword());
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("link", { name: "Accounts" }).click();
  await expect(page.getByRole("heading", { name: "Resident accounts" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Publish a payable charge" })).toBeVisible();
  await expect(page.getByLabel("Household")).toBeVisible();
  await expect(page.getByLabel("Household").locator("option")).toHaveCount(20);
  await expect(page.getByRole("heading", { name: "Autopay" })).toBeVisible();
});
