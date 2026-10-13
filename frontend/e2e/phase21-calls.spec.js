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

test("operations can record a call note without treating a phone link as a connection", async ({ page }) => {
  await signIn(page, "operations@demo.perchpoint.invalid");
  await page.goto("/calls");
  await expect(page.getByRole("heading", { name: "Calls" })).toBeVisible();
  await expect(page.getByText("does not record audio")).toBeVisible();
  const said = `Synthetic callback ${Date.now()}`;
  await page.getByLabel("What was said?").fill(said);
  await page.getByRole("button", { name: "Save call note" }).click();
  const status = page.getByRole("status").filter({ hasText: "not proof of a connection" });
  await expect(status).toBeVisible();
  const reference = ((await status.textContent()) || "").split(" ")[0];
  await expect(page.getByRole("listitem").filter({ hasText: reference })).toContainText("Duration unknown.");
});
