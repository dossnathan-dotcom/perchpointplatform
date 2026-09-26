const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const build = path.join(__dirname, "..", "build", "static");
const limits = { main: 250 * 1024, chunk: 200 * 1024, css: 60 * 1024 };

function gzipSize(file) {
  return zlib.gzipSync(fs.readFileSync(file)).length;
}

const jsDir = path.join(build, "js");
const cssDir = path.join(build, "css");
const scripts = fs.readdirSync(jsDir).filter((name) => name.endsWith(".js"));
const styles = fs.readdirSync(cssDir).filter((name) => name.endsWith(".css"));
const measured = {
  scripts: scripts.map((name) => ({ name, gzip: gzipSize(path.join(jsDir, name)) })),
  styles: styles.map((name) => ({ name, gzip: gzipSize(path.join(cssDir, name)) })),
};
const main = measured.scripts.find((item) => item.name.startsWith("main."));
const css = measured.styles.reduce((sum, item) => sum + item.gzip, 0);
const failures = [];
if (!main || main.gzip > limits.main) failures.push(`main js ${main ? main.gzip : "missing"} exceeds ${limits.main}`);
measured.scripts.forEach((item) => {
  if (item.gzip > limits.chunk) failures.push(`${item.name} ${item.gzip} exceeds ${limits.chunk}`);
});
if (css > limits.css) failures.push(`css ${css} exceeds ${limits.css}`);
console.log(JSON.stringify({ main: main && main.gzip, css, scripts: measured.scripts, styles: measured.styles }));
if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
