const { defineConfig, devices } = require("@playwright/test");

const browsers = [
  ["chromium", "Desktop Chrome"],
  ["firefox", "Desktop Firefox"],
  ["webkit", "Desktop Safari"],
];
const widths = [320, 768, 1024, 1440];

module.exports = defineConfig({
  testDir: "./e2e",
  testMatch: /phase18-.*\.spec\.js/,
  timeout: 480000,
  expect: { timeout: 15000 },
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000",
    trace: "retain-on-failure",
    locale: "en-US",
    timezoneId: "America/New_York",
  },
  projects: browsers.flatMap(([name, device]) => widths.map((width) => ({
    name: `${name}-${width}`,
    use: {
      ...devices[device],
      viewport: { width, height: width < 768 ? 720 : 900 },
    },
  }))),
});
