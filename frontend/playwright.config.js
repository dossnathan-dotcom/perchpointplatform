const { defineConfig, devices } = require("@playwright/test");
const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "../backend/.env") });

const skipWebServer = process.env.PLAYWRIGHT_SKIP_WEBSERVER === "1";

module.exports = defineConfig({
  testDir: "./e2e",
  timeout: 90000,
  expect: { timeout: 15000, toHaveScreenshot: { maxDiffPixelRatio: 0.01, animations: "disabled" } },
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000",
    trace: "off",
    locale: "en-US",
    timezoneId: "America/New_York",
  },
  webServer: skipWebServer ? undefined : {
    command: "corepack yarn start",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: true,
    timeout: 180000,
    env: {
      BROWSER: "none",
      CI: "true",
      REACT_APP_SHOW_DEMO_LABELS: "true",
      REACT_APP_ENABLE_SEEDED_PREVIEWS: "true",
    },
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] }, testIgnore: /phase4-production\.spec\.js/ },
    { name: "firefox", use: { ...devices["Desktop Firefox"] }, testMatch: /engines\.spec\.js/ },
    { name: "webkit", use: { ...devices["Desktop Safari"] }, testMatch: /engines\.spec\.js/ },
  ],
});
