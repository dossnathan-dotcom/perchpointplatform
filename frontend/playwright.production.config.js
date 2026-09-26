const { defineConfig, devices } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./e2e",
  testMatch: /phase4-production\.spec\.js/,
  timeout: 90000,
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000", locale: "en-US", timezoneId: "America/New_York" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
