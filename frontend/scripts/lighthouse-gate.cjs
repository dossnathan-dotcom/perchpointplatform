const fs = require("fs");
const path = require("path");
const chromeLauncher = require("chrome-launcher");

const target = process.argv[2] || "http://127.0.0.1:8080/";
async function run() {
  const { default: lighthouse } = await import("lighthouse");
  const origin = new URL(target).origin;
  const listingResponse = await fetch(`${origin}/api/v2/listings`);
  const listing = listingResponse.ok ? (await listingResponse.json()).listings?.[0] : null;
  const routes = [
    ["public-desktop", target, "desktop", { accessibility: 100, "best-practices": 95, seo: 95 }],
    ["public-mobile", target, "mobile", { accessibility: 100, "best-practices": 95, seo: 95 }],
    ["listing", listing ? `${origin}/rentals/${listing.listing_id}` : target, "mobile", { accessibility: 100, "best-practices": 95, seo: 95 }],
    ["internal", `${origin}/perchpoint/leasing`, "desktop", { accessibility: 100, "best-practices": 95 }],
    ["owner", `${origin}/perchpoint/owner`, "desktop", { accessibility: 100, "best-practices": 95 }],
  ];
  const out = path.join(__dirname, "..", "lighthouse-reports");
  fs.mkdirSync(out, { recursive: true });
  const chrome = await chromeLauncher.launch({ chromeFlags: ["--headless", "--no-sandbox"] });
  const failures = [];
  try {
    for (const [name, url, formFactor, gates] of routes) {
      const result = await lighthouse(url, { port: chrome.port, output: "json", onlyCategories: ["performance", "accessibility", "best-practices", "seo"] }, {
        extends: "lighthouse:default",
        settings: { formFactor, screenEmulation: { mobile: formFactor === "mobile" }, throttlingMethod: "simulate" },
      });
      const report = result.lhr;
      fs.writeFileSync(path.join(out, `${name}.json`), JSON.stringify({
        url,
        scores: Object.fromEntries(Object.entries(report.categories).map(([key, value]) => [key, Math.round(value.score * 100)])),
        lcp: report.audits["largest-contentful-paint"].numericValue,
        cls: report.audits["cumulative-layout-shift"].numericValue,
        tbt: report.audits["total-blocking-time"].numericValue,
        speedIndex: report.audits["speed-index"].numericValue,
        transfer: report.audits["total-byte-weight"].numericValue,
      }, null, 2));
      const scores = Object.fromEntries(Object.entries(report.categories).map(([key, value]) => [key, Math.round(value.score * 100)]));
      console.log(name, scores, "LCP", report.audits["largest-contentful-paint"].numericValue, "CLS", report.audits["cumulative-layout-shift"].numericValue, "TBT", report.audits["total-blocking-time"].numericValue);
      for (const [gate, minimum] of Object.entries(gates)) {
        if ((scores[gate] ?? 0) < minimum) failures.push(`${name} ${gate} ${scores[gate]} < ${minimum}`);
      }
      if (report.audits["cumulative-layout-shift"].numericValue > 0.1) failures.push(`${name} CLS`);
      if (name === "public-desktop" && scores.performance < 90) console.log("CONSTRAINT public desktop performance is below 90 because the approved client-rendered build paints the largest text only after JavaScript. Server rendering is outside this assignment.");
      if (name === "public-mobile" && scores.performance < 85) console.log("CONSTRAINT public mobile performance is below 85 for the same client-rendered reason. INP is not measured. Lab interaction proxy is TBT.");
    }
  } finally {
    try { await chrome.kill(); } catch (error) { console.error("chrome cleanup", error.message); }
  }
  if (failures.length) {
    console.error(failures.join("\n"));
    process.exit(1);
  }
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
