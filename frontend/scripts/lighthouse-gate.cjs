const fs = require("fs");
const path = require("path");
const chromeLauncher = require("chrome-launcher");

const target = process.argv[2] || "http://127.0.0.1:8080/";
const runsPerProfile = Number(process.env.LIGHTHOUSE_RUNS || "3");

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function variance(values) {
  const mid = median(values);
  return values.reduce((sum, value) => sum + ((value - mid) ** 2), 0) / values.length;
}

async function run() {
  process.env.TZ = process.env.TZ || "America/New_York";
  const { default: lighthouse } = await import("lighthouse");
  const { default: desktopConfig } = await import("lighthouse/core/config/desktop-config.js");
  const origin = new URL(target).origin;
  await fetch(target);
  const listingResponse = await fetch(`${origin}/api/v2/listings`);
  const listing = listingResponse.ok ? (await listingResponse.json()).listings?.[0] : null;
  const routes = [
    ["public-desktop", target, desktopConfig, { performance: 90, accessibility: 100, "best-practices": 95, seo: 95, lcp: 2500, cls: 0.1, tbt: 200 }],
    ["public-mobile", target, undefined, { performance: 85, accessibility: 100, "best-practices": 95, seo: 95, lcp: 2500, cls: 0.1, tbt: 200 }],
    ["listing", listing ? `${origin}/rentals/${listing.listing_id}` : target, undefined, { performance: 85, accessibility: 100, "best-practices": 95, seo: 95, lcp: 2500, cls: 0.1, tbt: 200 }],
    ["internal", `${origin}/perchpoint/leasing`, desktopConfig, { accessibility: 100, "best-practices": 95, cls: 0.1 }],
    ["owner", `${origin}/perchpoint/owner`, desktopConfig, { accessibility: 100, "best-practices": 95, cls: 0.1 }],
  ];
  const out = path.join(__dirname, "..", "lighthouse-reports");
  fs.mkdirSync(out, { recursive: true });
  const chrome = await chromeLauncher.launch({
    chromePath: process.env.CHROME_PATH || undefined,
    chromeFlags: ["--headless=new", "--no-sandbox", "--lang=en-US"],
  });
  const failures = [];
  const summary = {};
  try {
    for (const [name, url, config, gates] of routes) {
      const samples = [];
      for (let index = 1; index <= runsPerProfile; index += 1) {
        const result = await lighthouse(url, {
          port: chrome.port,
          output: ["json", "html"],
          logLevel: "error",
          onlyCategories: ["performance", "accessibility", "best-practices", "seo"],
        }, config);
        const report = result.lhr;
        const sample = {
          scores: Object.fromEntries(Object.entries(report.categories).map(([key, value]) => [key, Math.round((value.score || 0) * 100)])),
          lcp: report.audits["largest-contentful-paint"].numericValue,
          cls: report.audits["cumulative-layout-shift"].numericValue,
          tbt: report.audits["total-blocking-time"].numericValue,
          lcpElement: report.audits["largest-contentful-paint-element"]?.details?.items?.[0]?.items?.[0]?.node?.snippet || "",
          longTasks: (report.audits["long-tasks"]?.details?.items || []).map((item) => ({ duration: item.duration, start: item.startTime })),
        };
        samples.push(sample);
        const html = Array.isArray(result.report) ? result.report[1] : "";
        fs.writeFileSync(path.join(out, `${name}-${index}.json`), JSON.stringify(sample, null, 2));
        if (html) fs.writeFileSync(path.join(out, `${name}-${index}.html`), html);
        console.log(name, index, sample.scores, "LCP", Math.round(sample.lcp), "CLS", sample.cls, "TBT", Math.round(sample.tbt), sample.lcpElement);
      }
      const ordered = [...samples].sort((a, b) => a.scores.performance - b.scores.performance);
      const chosen = ordered[Math.floor(ordered.length / 2)];
      const stats = {
        chosen,
        performance: { values: samples.map((item) => item.scores.performance), median: median(samples.map((item) => item.scores.performance)), min: Math.min(...samples.map((item) => item.scores.performance)), max: Math.max(...samples.map((item) => item.scores.performance)) },
        lcp: { values: samples.map((item) => item.lcp), median: median(samples.map((item) => item.lcp)) },
        cls: { values: samples.map((item) => item.cls), median: median(samples.map((item) => item.cls)) },
        tbt: { values: samples.map((item) => item.tbt), median: median(samples.map((item) => item.tbt)) },
      };
      stats.performance.variance = variance(stats.performance.values);
      summary[name] = stats;
      console.log(name, "median", { performance: stats.performance.median, lcp: Math.round(stats.lcp.median), cls: stats.cls.median, tbt: Math.round(stats.tbt.median), min: stats.performance.min, max: stats.performance.max, variance: stats.performance.variance });
      const score = chosen.scores;
      if (gates.performance !== undefined && score.performance < gates.performance) failures.push(`${name} performance ${score.performance} < ${gates.performance}`);
      if (score.accessibility < gates.accessibility) failures.push(`${name} accessibility ${score.accessibility} < ${gates.accessibility}`);
      if (score["best-practices"] < gates["best-practices"]) failures.push(`${name} best-practices ${score["best-practices"]} < ${gates["best-practices"]}`);
      if (gates.seo !== undefined && score.seo < gates.seo) failures.push(`${name} seo ${score.seo} < ${gates.seo}`);
      if (gates.lcp !== undefined && chosen.lcp > gates.lcp) failures.push(`${name} LCP ${Math.round(chosen.lcp)} > ${gates.lcp}`);
      if (chosen.cls > gates.cls) failures.push(`${name} CLS ${chosen.cls} > ${gates.cls}`);
      if (gates.tbt !== undefined && chosen.tbt > gates.tbt) failures.push(`${name} TBT ${Math.round(chosen.tbt)} > ${gates.tbt}`);
    }
  } finally {
    fs.writeFileSync(path.join(out, "summary.json"), JSON.stringify(summary, null, 2));
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
