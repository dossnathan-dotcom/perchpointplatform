const esbuild = require("esbuild");
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const outfile = path.join(root, "build", "prerender.cjs");

function defineValue(name, fallback) {
  return JSON.stringify(process.env[name] || fallback);
}

async function main() {
await esbuild.build({
  absWorkingDir: root,
  entryPoints: [path.join(__dirname, "prerender-entry.jsx")],
  bundle: true,
  platform: "node",
  format: "cjs",
  outfile,
  jsx: "automatic",
  loader: { ".js": "jsx" },
  define: {
    "process.env.NODE_ENV": '"production"',
    "process.env.REACT_APP_SHOW_DEMO_LABELS": defineValue("REACT_APP_SHOW_DEMO_LABELS", "true"),
    "process.env.REACT_APP_ENABLE_SEEDED_PREVIEWS": defineValue("REACT_APP_ENABLE_SEEDED_PREVIEWS", "true"),
    "process.env.REACT_APP_PHASE3_ENVIRONMENT": defineValue("REACT_APP_PHASE3_ENVIRONMENT", "local"),
    "process.env.REACT_APP_SENTRY_DSN": defineValue("REACT_APP_SENTRY_DSN", ""),
    "process.env.REACT_APP_RELEASE": defineValue("REACT_APP_RELEASE", ""),
  },
  alias: { "@": path.join(root, "src") },
  plugins: [{
    name: "asset-stubs",
    setup(build) {
      build.onResolve({ filter: /\.(css|svg|png|jpg|jpeg|webp|avif|gif)$/ }, (args) => ({ path: args.path, namespace: "asset-stub" }));
      build.onLoad({ filter: /.*/, namespace: "asset-stub" }, () => ({ contents: "module.exports = {}", loader: "js" }));
    },
  }],
  logLevel: "warning",
});

const { renderHome } = require(outfile);
const htmlPath = path.join(root, "build", "index.html");
const html = fs.readFileSync(htmlPath, "utf8");
const shell = html.replace(/<div id="root">[\s\S]*?<\/div>/, '<div id="root"></div>');
fs.writeFileSync(path.join(root, "build", "shell.html"), shell);
const markup = renderHome();
if (!markup.includes("A better place to rent") || (markup.match(/<h1[\s>]/g) || []).length !== 1) {
  console.error("prerender did not produce one stable hero heading");
  process.exit(1);
}
const rendered = html.replace(/<div id="root">[\s\S]*?<\/div>/, `<div id="root" data-hydrate="home">${markup}</div>`);
const scriptMatch = rendered.match(/<script defer="defer" src="(\/static\/js\/main\.[^"]+\.js)"><\/script>/);
if (!scriptMatch) {
  console.error("prerender could not find the homepage script");
  process.exit(1);
}
const mainSrc = scriptMatch[1];
const booted = rendered.replace(scriptMatch[0], `<script defer="defer" src="/boot.js"></script>`);
fs.writeFileSync(htmlPath, booted);
fs.writeFileSync(path.join(root, "build", "boot.js"), `(function () {\n  var started = false;\n  function start() {\n    if (started) return;\n    started = true;\n    var script = document.createElement("script");\n    script.src = ${JSON.stringify(mainSrc)};\n    document.body.appendChild(script);\n  }\n  requestAnimationFrame(function () {\n    requestAnimationFrame(start);\n  });\n})();\n`);
fs.rmSync(outfile, { force: true });
console.log(`prerendered homepage ${markup.length} characters`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
