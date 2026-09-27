const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const COMPRESSIBLE = new Set([".html", ".js", ".css", ".svg", ".json", ".txt", ".map", ".xml"]);

function compressBuffer(raw) {
  return {
    gzip: zlib.gzipSync(raw, { level: 9 }),
    brotli: zlib.brotliCompressSync(raw, {
      params: { [zlib.constants.BROTLI_PARAM_QUALITY]: 11 },
    }),
  };
}

function walk(dir, files = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, files);
    else files.push(full);
  }
  return files;
}

function compressTree(buildDir) {
  const totals = { files: 0, raw: 0, gzip: 0, brotli: 0 };
  for (const file of walk(buildDir)) {
    const ext = path.extname(file).toLowerCase();
    if (!COMPRESSIBLE.has(ext) || file.endsWith(".gz") || file.endsWith(".br")) continue;
    const raw = fs.readFileSync(file);
    const encoded = compressBuffer(raw);
    if (encoded.gzip.length < raw.length) fs.writeFileSync(`${file}.gz`, encoded.gzip);
    if (encoded.brotli.length < raw.length) fs.writeFileSync(`${file}.br`, encoded.brotli);
    totals.files += 1;
    totals.raw += raw.length;
    totals.gzip += encoded.gzip.length;
    totals.brotli += encoded.brotli.length;
  }
  return totals;
}

if (require.main === module) {
  const build = path.join(__dirname, "..", "build");
  console.log(JSON.stringify(compressTree(build)));
}

module.exports = { compressBuffer, compressTree };
