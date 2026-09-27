const assert = require("node:assert/strict");
const test = require("node:test");
const zlib = require("node:zlib");
const { compressBuffer } = require("./compress-build.cjs");

test("gzip and brotli decompress to the original bytes", () => {
  const raw = Buffer.from("HawkVision Homes public shell ".repeat(30));
  const encoded = compressBuffer(raw);
  assert.deepEqual(zlib.gunzipSync(encoded.gzip), raw);
  assert.deepEqual(zlib.brotliDecompressSync(encoded.brotli), raw);
  assert.ok(encoded.brotli.length < raw.length);
  assert.ok(encoded.gzip.length < raw.length);
});
