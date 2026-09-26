const { defineConfig, devices } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "/work/frontend/e2e",
  testMatch: /phase4-visual\.spec\.js/,
  timeout: 90000,
  expect: { timeout: 15000, toHaveScreenshot: { maxDiffPixelRatio: 0.01, animations: "disabled" } },
  workers: 1,
  use: {
    baseURL: "http://host.docker.internal:3000",
    locale: "en-US",
    timezoneId: "America/New_York",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
