// Conformance of web/earnumber.js against earnumber-v1-vectors.json.
// Run from the repository root: node --test tests/js/*.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as EN from "../../web/earnumber.js";

const root = fileURLToPath(new URL("../../", import.meta.url));
const V = JSON.parse(readFileSync(root + "earnumber-v1-vectors.json", "utf8"));
const tableBytes = readFileSync(root + "web/earnumber-v1.json");
await EN.loadTableBytes(new Uint8Array(tableBytes));

test("web table is the published version 1 table", async () => {
  assert.equal(await EN.sha256Hex(new Uint8Array(tableBytes)), EN.V1_SHA256);
  assert.equal(V.table_sha256, EN.V1_SHA256);
  assert.deepEqual(tableBytes, readFileSync(root + "earnumber-v1.json"));
});

test("a changed table is refused", async () => {
  const changed = new Uint8Array([...tableBytes, 10]);
  await assert.rejects(EN.loadTableBytes(changed), /not the published version 1 table/);
  await EN.loadTableBytes(new Uint8Array(tableBytes));
});

test("decode: all 1,000 numbers within 0.05 dB", () => {
  assert.equal(Object.keys(V.decode).length, 1000);
  for (const [key, expect] of Object.entries(V.decode)) {
    const got = EN.decode(Number(key));
    EN.DECODE_FREQS.forEach((f, i) => {
      assert.ok(Math.abs(got[f] - expect[i]) <= 0.05, `${key} at ${f} Hz: ${got[f]} vs ${expect[i]}`);
    });
  }
});

test("encode: every audiogram gives the expected number", () => {
  assert.ok(V.encode.length >= 250);
  for (const r of V.encode) {
    const n = EN.encode(r.thresholds);
    assert.equal(n, r.number, r.note);
    assert.deepEqual([EN.qualityLevel(n), EN.shapeIndex(n)], [r.level, r.shape], r.note);
  }
});

test("pairs: check digit and written form", () => {
  for (const r of V.pairs) {
    assert.equal(EN.checkDigit(r.left, r.right), r.check_digit);
    assert.equal(EN.formatPair(r.left, r.right, true, r.left_suffix, r.right_suffix), r.formatted);
  }
});

test("parse: accepted forms", () => {
  for (const r of V.parse) assert.deepEqual(EN.parsePair(r.text), r.expect, r.text);
});

test("parse: rejected forms", () => {
  for (const text of V.reject) assert.throws(() => EN.parsePair(text), EN.EarNumberError, JSON.stringify(text));
});

test("encode refuses a missing 8 kHz rather than estimating it", () => {
  assert.throws(() => EN.encode({ 500: 10, 1000: 10, 2000: 20, 4000: 30, 6000: 40 }), /8000 Hz is required/);
});
