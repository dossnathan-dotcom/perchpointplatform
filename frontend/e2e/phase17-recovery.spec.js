const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

function localPassword() {
  const text = fs.readFileSync(path.join(__dirname, "../../backend/.env.demo.local"), "utf8");
  const line = text.split(/\r?\n/).find((row) => row.startsWith("PERCHPOINT_LOCAL_DEMO_PASSWORD="));
  if (!line) throw new Error("local demo password file is missing the expected key");
  return line.split("=").slice(1).join("=").trim();
}

test("apartment and house listings use matching exteriors", async ({ page }) => {
  await page.goto("/rentals?home_type=apartment");
  await expect(page.getByRole("status")).toContainText(/homes match/);
  const apartments = page.locator("img[src*='apartment-exterior.jpg']");
  await expect(apartments.first()).toBeVisible();
  await expect(page.locator("img[src*='house-exterior.jpg']")).toHaveCount(0);
  await page.goto("/rentals?home_type=house");
  await expect(page.locator("img[src*='house-exterior.jpg']").first()).toBeVisible();
  await expect(page.locator("img[src*='apartment-exterior.jpg']")).toHaveCount(0);
});

test("technician assignments open in the shared workspace", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("technician@demo.perchpoint.invalid");
  await page.getByRole("textbox", { name: "Password" }).fill(localPassword());
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/access\/vendor-access/);
  await expect(page.getByRole("navigation", { name: "Workspace" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Assignments" })).toBeVisible();
  await expect(page.getByRole("link", { name: "History", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Users and Access" })).toHaveCount(0);
  await expect(page.getByRole("combobox", { name: "Vendor", exact: true })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Property", exact: true })).toBeVisible();
  await expect(page.getByLabel("Vendor relationship ID")).toHaveCount(0);
  await expect(page.getByLabel("Proposal ID")).toHaveCount(0);
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.goto("/access/users-access");
  await expect(page.getByText("This workspace does not include that area.")).toBeVisible();
  await page.goto("/owner");
  await expect(page.getByText("This session is not the owner.")).toBeVisible();
});

test("operations opens resident accounts and the charge form", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("operations@demo.perchpoint.invalid");
  await page.getByRole("textbox", { name: "Password" }).fill(localPassword());
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("link", { name: "Accounts" }).click();
  await expect(page).toHaveURL(/\/ledger/);
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Household" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Publish a payable charge" })).toBeVisible();
});

test("operations selects a named vendor instead of a raw id", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("operations@demo.perchpoint.invalid");
  await page.getByRole("textbox", { name: "Password" }).fill(localPassword());
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/leasing-desk/);
  await page.goto("/access/vendor-access");
  const vendor = page.getByRole("combobox", { name: "Vendor", exact: true });
  await expect(vendor).toBeVisible();
  await expect(vendor.locator("option")).toContainText(["Synthetic Phase 6 Vendor"]);
  await expect(page.getByLabel("Vendor relationship ID")).toHaveCount(0);
});
