const { defineConfig } = require("@playwright/test");
const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "../backend/.env") });

module.exports = defineConfig({
  testDir: "./e2e",
  timeout: 90000,
  expect: { timeout: 15000 },
  fullyParallel: false,
  workers: 1,
  use: { baseURL: "http://127.0.0.1:3000", trace: "off" },
  webServer: {
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
});
