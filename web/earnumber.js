// Ear Number version 1: JavaScript port of earnumber.py (encode, decode, check digit, and
// writing and reading a person's pair). No dependencies; runs in browsers and in Node >= 19.
// Conformance: tests/js/earnumber.test.mjs reproduces earnumber-v1-vectors.json.
// Not ported: estimate_from_quick (the self-test estimator).
//
// Load the table once before use:
//   await loadTableUrl("earnumber-v1.json")      // browser
//   await loadTableBytes(bytes)                  // any Uint8Array, e.g. from fs.readFile
// Both check the bytes against the published SHA-256 when Web Crypto is available.

export const V1_SHA256 = "479155629f5a377a2de0dbc82d1ad83908692ce78cf505ef75e1ec9687f6c97d";
export const NO_HEARING = 0;
// Suffix letters: upper case, avoiding letters that look like digits. E and N are defined in
// version 1; the others are reserved.
export const SUFFIX_LETTERS = "ACEFHJKMNPRVWXY";
export const SUFFIXES = {
  E: "estimated by a self-test on an uncalibrated device",
  N: "not measured on this ear; value assumed (copied from the other ear, or a default)",
};
const DAMM = ["0317598642", "7092154863", "4206871359", "1750983426", "6123045978",
  "3674209581", "5869720134", "8945362017", "9438617205", "2581436790"];

export const BAND_WEIGHTS = { 250: 0.0617, 500: 0.1671, 1000: 0.2373, 2000: 0.2648, 4000: 0.2142, 8000: 0.0549 };
const WEIGHT_FREQS = [250, 500, 1000, 2000, 4000, 8000];   // summed in this order, as the reference
export const CLIP_LO = -10, CLIP_HI = 100;
export const SHAPE_FREQS = [500, 1000, 2000, 3000, 4000, 6000, 8000];
export const DECODE_FREQS = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000];
export const REQUIRED_FREQS = [500, 1000, 2000, 4000, 8000];

export class EarNumberError extends Error {
  constructor(message) { super(message); this.name = "EarNumberError"; }
}

let T = null;

export async function sha256Hex(bytes) {
  const d = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(d), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Load the table from its bytes. Refuses bytes that are not the published version 1 table
 *  (checked when Web Crypto is available: https, localhost, Node). Returns the table. */
export async function loadTableBytes(bytes, { checkHash = true } = {}) {
  if (checkHash && globalThis.crypto?.subtle) {
    if (await sha256Hex(bytes) !== V1_SHA256) {
      throw new EarNumberError("the table is not the published version 1 table (SHA-256 mismatch)");
    }
  }
  return useTable(JSON.parse(new TextDecoder().decode(bytes)));
}

export async function loadTableUrl(url) {
  const r = await fetch(url);
  if (!r.ok) throw new EarNumberError(`could not fetch the table (${r.status})`);
  return loadTableBytes(new Uint8Array(await r.arrayBuffer()));
}

/** Validate a parsed table and make it current (no hash check). */
export function useTable(t) {
  if (String(t.version) !== "1") throw new EarNumberError(`table version must be '1'; got ${t.version}`);
  const w = t.band_weights_hz || {};
  const keys = Object.keys(w).map(Number).sort((a, b) => a - b);
  if (keys.join() !== WEIGHT_FREQS.join() || WEIGHT_FREQS.some((f) => w[f] !== BAND_WEIGHTS[f])) {
    throw new EarNumberError("table band weights do not match BAND_WEIGHTS");
  }
  if ((t.shape_freqs_hz || []).join() !== SHAPE_FREQS.join()) {
    throw new EarNumberError("table shape_freqs_hz does not match SHAPE_FREQS");
  }
  const s = t.shape_residuals_db;
  if (!Array.isArray(s) || s.length !== 50 || s.some((c) => !Array.isArray(c) || c.length !== 7)) {
    throw new EarNumberError("table must hold exactly 50 shapes of 7 numbers each");
  }
  T = t;
  return t;
}

function table() {
  if (!T) throw new EarNumberError("no table loaded: call loadTableUrl or loadTableBytes first");
  return T;
}

const clip = (x) => Math.min(Math.max(x, CLIP_LO), CLIP_HI);
const interpLog = (f, f0, t0, f1, t1) => t0 + (t1 - t0) * Math.log(f / f0) / Math.log(f1 / f0);

function toNumber(v, f) {
  const x = typeof v === "string" ? Number(v.trim()) : v;
  if (typeof x !== "number" || !Number.isFinite(x) || (typeof v === "string" && v.trim() === "")) {
    throw new EarNumberError(`threshold at ${f} Hz is not a number`);
  }
  return x;
}

/** Clip to -10..100 and fill gaps: 3000 and 6000 by log-frequency interpolation; 250 is
 *  always set to the 500 Hz value. Keys may be numbers or strings; null or undefined values
 *  count as missing. */
export function complete(thresholds) {
  const t = {};
  for (const [k, v] of Object.entries(thresholds)) {
    if (v === null || v === undefined) continue;
    t[Number(k)] = clip(toNumber(v, k));
  }
  for (const f of REQUIRED_FREQS) {
    if (!(f in t)) throw new EarNumberError(`threshold at ${f} Hz is required`);
  }
  if (!(3000 in t)) t[3000] = interpLog(3000, 2000, t[2000], 4000, t[4000]);
  if (!(6000 in t)) t[6000] = interpLog(6000, 4000, t[4000], 8000, t[8000]);
  t[250] = t[500];
  return t;
}

/** H in dB HL: importance-weighted mean threshold, rounded to 6 decimals as the reference. */
export function meanThreshold(t) {
  let h = 0;
  for (const f of WEIGHT_FREQS) h += BAND_WEIGHTS[f] * t[f];
  return Number(h.toFixed(6));
}

const level = (h) => 19 - Math.min(Math.max(Math.floor(h / 5), 0), 19);

/** Ear Number (0-999) for one ear. thresholds: {Hz: dB HL}; 500, 1000, 2000, 4000 and 8000
 *  required; 3000 and 6000 optional; a 250 Hz value is accepted and ignored. */
export function encode(thresholds) {
  const tb = table();
  const t = complete(thresholds);
  if (Object.values(t).every((v) => v >= CLIP_HI)) return NO_HEARING;
  const h = meanThreshold(t);
  const q = level(h);
  const res = SHAPE_FREQS.map((f) => t[f] - h);
  let best = null, bd = null;
  tb.shape_residuals_db.forEach((c, i) => {
    if (q === 0 && i === 0) return;               // 000 is reserved for no hearing
    let d = 0;
    for (let j = 0; j < 7; j++) { const e = res[j] - c[j]; d += e * e; }
    if (bd === null || d < bd) { best = i; bd = d; }
  });
  return q * 50 + best;
}

function check(n) {
  if (typeof n !== "number" || !Number.isInteger(n) || n < 0 || n > 999) {
    throw new EarNumberError("Ear Number must be an integer 0-999");
  }
  return n;
}

/** Level 0-19 (higher = better hearing; each level is 5 dB of mean threshold). */
export const qualityLevel = (n) => Math.floor(check(n) / 50);
export const shapeIndex = (n) => check(n) % 50;

/** Approximate audiogram {Hz: dB HL} at 250..8000 Hz; 250 equals 500. */
export function decode(n) {
  check(n);
  const out = {};
  if (n === NO_HEARING) {
    for (const f of DECODE_FREQS) out[f] = CLIP_HI;
    return out;
  }
  const centre = (19 - Math.floor(n / 50) + 0.5) * 5;
  const shape = table().shape_residuals_db[n % 50];
  SHAPE_FREQS.forEach((f, i) => { out[f] = clip(centre + shape[i]); });
  out[250] = out[500];
  return out;
}

/** Damm check digit (0-9) over the six digits LLLRRR. */
export function checkDigit(nLeft, nRight) {
  let i = 0;
  for (const ch of pad3(nLeft) + pad3(nRight)) i = Number(DAMM[i][Number(ch)]);
  return i;
}

const pad3 = (n) => String(check(n)).padStart(3, "0");

function suffix(s) {
  s = (s || "").toUpperCase();
  const bad = [...s].filter((c) => !SUFFIX_LETTERS.includes(c));
  if (bad.length) throw new EarNumberError(`suffix letters must be from ${SUFFIX_LETTERS}; got '${bad.join("")}'`);
  return s;
}

/** 'LLL RRR C' (check digit included by default), each ear followed by its suffix letters. */
export function formatPair(nLeft, nRight, withCheck = true, suffixLeft = "", suffixRight = "") {
  const s = `${pad3(nLeft)}${suffix(suffixLeft)} ${pad3(nRight)}${suffix(suffixRight)}`;
  return withCheck ? `${s} ${checkDigit(nLeft, nRight)}` : s;
}

export function encodePair(left, right, withCheck = true) {
  return formatPair(encode(left), encode(right), withCheck);
}

/** Read a written pair: 'LLL RRR', 'LLL RRR C', with or without spaces, commas, semicolons or
 *  hyphens, and suffix letters after either ear. Six digits: no check digit; seven: the last
 *  is the check digit, which must match. Returns {left, right, left_suffix, right_suffix,
 *  check} (check null when absent), the same keys as the reference. */
export function parsePair(text) {
  const s = String(text).replace(/[\s,;-]/g, "").toUpperCase();
  const m = /^(\d{3})([A-Z]*)(\d{3})([A-Z]*)(\d?)$/.exec(s);
  if (!m) throw new EarNumberError(`not an Ear Number pair: '${text}'`);
  const left = Number(m[1]), right = Number(m[3]);
  const ls = suffix(m[2]), rs = suffix(m[4]), c = m[5];
  if (c && Number(c) !== checkDigit(left, right)) {
    throw new EarNumberError(`check digit does not match: '${text}' (re-enter the number)`);
  }
  return { left, right, left_suffix: ls, right_suffix: rs, check: c ? Number(c) : null };
}
