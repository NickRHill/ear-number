import * as EN from "./earnumber.js";

const FREQS = [500, 1000, 2000, 3000, 4000, 6000, 8000];
const OPTIONAL = new Set([3000, 6000]);
const FLABEL = { 500: "500", 1000: "1k", 2000: "2k", 3000: "3k", 4000: "4k", 6000: "6k", 8000: "8k" };
const EARS = ["left", "right"];
const EXAMPLE = "668 726 3";          // "Typical at 70", one of the example buttons
const STEP = 5;                         // dB, as audiometers step
const DRAG_MIN = -10, DRAG_MAX = 100;   // the encoder's range
// Chart geometry (SVG user units)
const W = 378, H = 326, ML = 48, MR = 76, MT = 38, MB = 10;
const Y_MIN = -10, Y_MAX = 110;
const BANDS = [ // WHO grades of the average threshold, for the chart's background
  [-10, 20, "chart_normal"], [20, 35, "chart_mild"], [35, 50, "chart_moderate"], [50, 65, "chart_modsevere"],
  [65, 80, "chart_severe"], [80, 95, "chart_profound"], [95, 110, "chart_complete"]];
const NUMBER_BANDS = [[800, "band_normal"], [650, "band_mild"], [500, "band_moderate"],
  [350, "band_modsevere"], [200, "band_severe"], [50, "band_profound"], [1, "band_little"]];

// Phrases for the page's language, written into the page by build/build_web.py.
const T = (() => {
  try { return JSON.parse(document.getElementById("i18n").textContent); } catch { return {}; }
})();
// On right-to-left pages each inserted value is wrapped in a first-strong isolate: a number or
// "30–35 dB" stays left to right (not reordered into "dB 35–30"), Arabic text stays right to left.
const RTL = document.documentElement.dir === "rtl";
const iso = (v) => (RTL ? "\u2068" + v + "\u2069" : String(v));
const t = (key, vars = {}) => (T[key] ?? key).replace(/\{(\w+)\}/g, (m, k) => (k in vars ? iso(vars[k]) : m));
const tr = (key) => t(key);
// Shrink a chart label that is wider than the room beside the chart (long words in some languages).
function fitText(node, room) {
  const w = node.getComputedTextLength();
  if (w > room) node.style.fontSize = (11.5 * room / w).toFixed(1) + "px";   // inline style: CSS would override an attribute
}
const earName = (ear) => t(ear === "left" ? "left_ear" : "right_ear");

const $ = (s, el = document) => el.querySelector(s);
const svgNS = "http://www.w3.org/2000/svg";
const xOf = (f) => ML + (Math.log2(f / 500) / 4) * (W - ML - MR);
const yOf = (db) => MT + ((db - Y_MIN) / (Y_MAX - Y_MIN)) * (H - MT - MB);
const dbOf = (y) => Y_MIN + ((y - MT) / (H - MT - MB)) * (Y_MAX - Y_MIN);
const snap = (db) => Math.min(DRAG_MAX, Math.max(DRAG_MIN, Math.round(db / STEP) * STEP));
const fmtDb = (v) => (v === null || v === undefined ? "" : String(Math.round(v * 10) / 10));

const state = {
  points: { left: {}, right: {} },     // {Hz: dB HL or null}: what the visitor sees and drags
  number: { left: null, right: null },
  suffix: { left: "", right: "" },
  touched: false,                      // the drag cue shows until the visitor first uses a chart
};
const ui = {};

function el(name, attrs = {}, parent) {
  const e = document.createElementNS(svgNS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

// ------------------------------------------------------------------ charts
function buildChart(ear) {
  const svg = ui[ear].svg;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  el("rect", { class: "bg", x: ML, y: MT, width: W - ML - MR, height: H - MT - MB }, svg);
  BANDS.forEach(([a, b, name], i) => {
    if (i % 2 === 1) el("rect", { class: "band", x: ML, y: yOf(a), width: W - ML - MR, height: yOf(b) - yOf(a) }, svg);
    const lab = el("text", { class: "bandlab", x: W - MR + 6, y: (yOf(a) + yOf(b)) / 2 + 3.5 }, svg);
    lab.textContent = tr(name);
    fitText(lab, MR - 8);
  });
  for (let db = Y_MIN; db <= Y_MAX; db += 10) {
    el("line", { class: "gl" + (db % 20 === 0 ? " major" : ""), x1: ML, x2: W - MR, y1: yOf(db), y2: yOf(db) }, svg);
    if (db % 20 === 0) {
      const lab = el("text", { x: ML - 6, y: yOf(db) + 3.5, "text-anchor": "end" }, svg);
      lab.textContent = db;
    }
  }
  for (const f of FREQS) {
    el("line", { class: "gl" + (OPTIONAL.has(f) ? "" : " major"), x1: xOf(f), x2: xOf(f), y1: MT, y2: H - MB }, svg);
    const lab = el("text", { x: xOf(f), y: MT - 8, "text-anchor": "middle" }, svg);
    lab.textContent = FLABEL[f];
  }
  const unit = el("text", { x: 11, y: (MT + H - MB) / 2, "text-anchor": "middle",
    transform: `rotate(-90 11 ${(MT + H - MB) / 2})` }, svg);
  unit.textContent = t("axis");
  const hz = el("text", { x: W - MR + 6, y: MT - 8 }, svg);
  hz.textContent = "Hz";
  ui[ear].dyn = el("g", {}, svg);
  ui[ear].overlay = el("g", {}, svg);
  attachPointer(ear);
}

function drawChart(ear) {
  const g = ui[ear].dyn;
  // Redrawing replaces the point elements; keep keyboard focus on the same pitch.
  const focusedF = g.contains(document.activeElement) ? document.activeElement.dataset.f : null;
  g.replaceChildren();
  const n = state.number[ear];
  if (n !== null) {
    const d = EN.decode(n);
    const pts = FREQS.map((f) => `${xOf(f).toFixed(1)},${yOf(d[f]).toFixed(1)}`).join(" ");
    el("polyline", { class: "decoded", points: pts }, g);
    el("polyline", { class: "decoded-core", points: pts }, g);
  }
  for (const f of FREQS) {
    const v = state.points[ear][f];
    if (v === null || v === undefined) {
      if (!OPTIONAL.has(f)) {
        const lab = el("text", { class: "missing", x: xOf(f), y: H - MB - 6, "text-anchor": "middle" }, g);
        lab.textContent = "?";
      }
      continue;
    }
    const x = xOf(f), y = yOf(Math.min(v, Y_MAX));
    const p = el("g", {
      class: "pt", tabindex: "0", role: "slider", "data-f": f,
      "aria-label": t("point_aria", { ear: earName(ear), freq: FLABEL[f] + "Hz" }),
      "aria-valuemin": DRAG_MIN, "aria-valuemax": DRAG_MAX, "aria-valuenow": Math.round(v),
      "aria-valuetext": `${fmtDb(v)} dB HL`,
    }, g);
    el("circle", { class: "ring", cx: x, cy: y, r: 10 }, p);
    if (ear === "left") el("path", { class: "sym", d: `M${x - 5.5} ${y - 5.5}L${x + 5.5} ${y + 5.5}M${x + 5.5} ${y - 5.5}L${x - 5.5} ${y + 5.5}` }, p);
    else el("circle", { class: "sym", cx: x, cy: y, r: 6 }, p);
    el("circle", { class: "hit", cx: x, cy: y, r: 16 }, p);
    if (!state.touched && ear === "left" && f === 4000) drawCue(g, x, y);
  }
  if (tip.ear === ear) drawTip(g, ear, tip.f);
  if (focusedF) g.querySelector(`.pt[data-f="${focusedF}"]`)?.focus({ preventScroll: true });
}

// ------------------------------------------------------------------ value tooltip
// While a point is dragged, and for a moment after a keyboard move or a click, a label shows
// its pitch and value in large type, for reading off and copying down.
const tip = { ear: null, f: null, timer: 0 };

function showTip(ear, f, { hold = false, ms = 2500 } = {}) {
  clearTimeout(tip.timer);
  const prev = tip.ear;
  tip.ear = ear;
  tip.f = f;
  if (!hold) tip.timer = setTimeout(hideTip, ms);
  if (prev && prev !== ear) drawChart(prev);
  drawChart(ear);
}

function releaseTip(ms = 1500) {
  clearTimeout(tip.timer);
  if (tip.ear) tip.timer = setTimeout(hideTip, ms);
}

function hideTip() {
  clearTimeout(tip.timer);
  const ear = tip.ear;
  tip.ear = null;
  if (ear) drawChart(ear);
}

function drawTip(g, ear, f) {
  const v = state.points[ear][f];
  if (v === null || v === undefined) return;
  const x = xOf(f), y = yOf(Math.min(v, Y_MAX));
  const label = `${FLABEL[f]}Hz \u00b7 ${fmtDb(v)} dB HL`;
  const box = el("g", { class: "tip", "aria-hidden": "true", "pointer-events": "none" }, g);
  const rect = el("rect", { rx: 7 }, box);
  const arrow = el("path", {}, box);
  const text = el("text", { "text-anchor": "middle" }, box);
  text.textContent = label;
  const w = (text.getComputedTextLength() || label.length * 8.8) + 20, h = 30;
  const above = y - 18 - h >= 2;
  const top = above ? y - 18 - h : y + 18;
  const left = Math.min(Math.max(x - w / 2, 2), W - w - 2);
  rect.setAttribute("x", left); rect.setAttribute("y", top);
  rect.setAttribute("width", w); rect.setAttribute("height", h);
  arrow.setAttribute("d", above ? `M${x - 6} ${top + h}L${x} ${top + h + 6}L${x + 6} ${top + h}Z`
                                : `M${x - 6} ${top}L${x} ${top - 6}L${x + 6} ${top}Z`);
  text.setAttribute("x", left + w / 2); text.setAttribute("y", top + 20.5);
}

// A pulsing ring and a "drag" label on one point, so the charts look movable at first sight.
function drawCue(g, x, y) {
  const c = el("g", { class: "cue", "aria-hidden": "true", "pointer-events": "none" }, g);
  el("circle", { class: "cue-ring", cx: x, cy: y, r: 9 }, c);
}

// ------------------------------------------------------------------ first-visit demonstration
// A hand drags the left ear's 4 kHz point down, up and back, so the number visibly changes.
const HAND = "M9 15V3.2a1.8 1.8 0 0 1 3.6 0V10a1.6 1.6 0 0 1 3.2 0v1a1.6 1.6 0 0 1 3.2 0v5" +
  "c0 3.5-2.5 6-6 6h-1.5c-2.5 0-4-1.2-5.2-3.2L4 14.6a1.5 1.5 0 0 1 2.4-1.8L9 15z";
const HAND_SCALE = 2.1, TIP_X = 10.8, TIP_Y = 1.4;
const DEMO = { ear: "left", f: 4000 };
let demo = null;

function placeHand(hand, db) {
  const x = xOf(DEMO.f) - TIP_X * HAND_SCALE, y = yOf(db) - TIP_Y * HAND_SCALE + 3;
  hand.setAttribute("transform", `translate(${x.toFixed(1)} ${y.toFixed(1)}) scale(${HAND_SCALE})`);
}

function runDemo() {
  const orig = state.points[DEMO.ear][DEMO.f];
  if (state.touched || orig === null || orig === undefined) return;
  const hand = el("g", { class: "demo-hand", "aria-hidden": "true" }, ui[DEMO.ear].overlay);
  el("path", { d: HAND }, hand);
  placeHand(hand, orig);
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  demo = { orig, hand, raf: 0, timer: 0 };
  showTip(DEMO.ear, DEMO.f, { hold: true });
  const finish = () => {
    releaseTip(600);
    hand.classList.add("gone");
    setTimeout(() => hand.remove(), 500);
  };
  if (reduce) {                       // no movement: show the hand on the point for a moment
    demo.timer = setTimeout(() => { finish(); demo = null; }, 3000);
    return;
  }
  // keyframes: [time ms, offset dB]
  const K = [[0, 0], [600, 0], [1100, 20], [1900, -12], [2400, 0]];
  const ease = (u) => u * u * (3 - 2 * u);
  let t0 = null, last = null;
  const step = (now) => {
    if (!demo) return;
    t0 ??= now;
    const t = now - t0;
    let off = 0;
    for (let i = 1; i < K.length; i++) {
      if (t <= K[i][0]) {
        const [ta, a] = K[i - 1], [tb, b] = K[i];
        off = a + (b - a) * ease((t - ta) / (tb - ta));
        break;
      }
    }
    const v = t >= K.at(-1)[0] ? orig : snap(orig + off);
    placeHand(hand, orig + off);
    if (v !== last) {
      last = v;
      state.points[DEMO.ear][DEMO.f] = v;
      recompute(DEMO.ear);
      render({ fromPoints: true });
    }
    if (t < K.at(-1)[0]) demo.raf = requestAnimationFrame(step);
    else { finish(); demo = null; }
  };
  demo.raf = requestAnimationFrame(step);
}

function stopDemo() {
  if (!demo) return;
  cancelAnimationFrame(demo.raf);
  clearTimeout(demo.timer);
  demo.hand.remove();
  hideTip();
  state.points[DEMO.ear][DEMO.f] = demo.orig;
  recompute(DEMO.ear);
  demo = null;
  render({ fromPoints: true });
}

function touch() {
  stopDemo();
  if (state.touched) return;
  state.touched = true;
  for (const ear of EARS) ui[ear].dyn.querySelector(".cue")?.remove();
}

function svgPoint(svg, e) {
  const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(svg.getScreenCTM().inverse());
  return { x: pt.x, y: pt.y };
}

// A clicked or dragged point takes keyboard focus, so the arrow keys and Tab carry on from it.
function focusPoint(ear, f) {
  ui[ear].svg.querySelector(`.pt[data-f="${f}"]`)?.focus({ preventScroll: true });
}

// The first Tab on a fresh page goes to the left ear's first point; later Tabs follow the page.
function firstTabToChart(e) {
  document.removeEventListener("keydown", firstTabToChart, true);
  if (e.key !== "Tab" || e.shiftKey) return;
  if (document.activeElement && document.activeElement !== document.body) return;
  if (!ui.left.svg.querySelector(".pt")) return;
  e.preventDefault();
  touch();                                         // may redraw the chart, so look the point up after
  const pt = ui.left.svg.querySelector(".pt");
  pt.focus();
  showTip("left", Number(pt.dataset.f));
}

function nearestFreq(x) {
  let best = FREQS[0];
  for (const f of FREQS) if (Math.abs(xOf(f) - x) < Math.abs(xOf(best) - x)) best = f;
  return best;
}

function attachPointer(ear) {
  const svg = ui[ear].svg;
  let drag = null;   // {f, id, live}: live = moving with the pointer
  svg.addEventListener("pointerdown", (e) => {
    if (e.button !== 0 || !tableReady) return;
    touch();
    const p = svgPoint(svg, e);
    const onPoint = e.target.closest(".pt");
    const f = onPoint ? Number(onPoint.dataset.f) : nearestFreq(p.x);
    // On touch, a press on empty chart may be the start of a scroll: place the point on release.
    const live = Boolean(onPoint) || e.pointerType !== "touch";
    drag = { f, id: e.pointerId, live, y: p.y };
    if (live) {
      svg.setPointerCapture(e.pointerId);
      svg.classList.add("dragging");
      tip.ear = ear; tip.f = f; clearTimeout(tip.timer);
      setPoint(ear, f, snap(dbOf(p.y)));
      showTip(ear, f, { hold: true });
      focusPoint(ear, f);
      e.preventDefault();
    }
  });
  svg.addEventListener("pointermove", (e) => {
    if (!drag || drag.id !== e.pointerId || !drag.live) return;
    setPoint(ear, drag.f, snap(dbOf(svgPoint(svg, e).y)));
  });
  const end = (e, cancelled) => {
    if (!drag || drag.id !== e.pointerId) return;
    if (!drag.live && !cancelled) {
      setPoint(ear, drag.f, snap(dbOf(svgPoint(svg, e).y)));
      showTip(ear, drag.f);
      focusPoint(ear, drag.f);
    } else if (drag.live) releaseTip();
    drag = null;
    svg.classList.remove("dragging");
    commit();
  };
  svg.addEventListener("pointerup", (e) => end(e, false));
  svg.addEventListener("pointercancel", (e) => end(e, true));
  svg.addEventListener("focusin", (e) => {       // Tab onto a point shows its value
    const pt = e.target.closest(".pt");
    if (!pt || !e.target.matches(":focus-visible")) return;
    const f = Number(pt.dataset.f);
    if (tip.ear !== ear || tip.f !== f) showTip(ear, f);
  });
  svg.addEventListener("keydown", (e) => {
    const pt = e.target.closest(".pt");
    if (!pt) return;
    touch();
    const f = Number(pt.dataset.f);
    const v = state.points[ear][f] ?? 0;
    const delta = { ArrowUp: -STEP, ArrowDown: STEP, PageUp: -20, PageDown: 20 }[e.key];
    if (delta === undefined) return;
    e.preventDefault();
    tip.ear = ear; tip.f = f;
    setPoint(ear, f, snap(v + delta));
    showTip(ear, f);
    commit();
  });
}

// ------------------------------------------------------------------ state changes
function setPoint(ear, f, db) {
  if (state.points[ear][f] === db) return;
  state.points[ear][f] = db;
  recompute(ear);
  render({ fromPoints: true });
}

function recompute(ear) {
  try {
    state.number[ear] = EN.encode(state.points[ear]);
  } catch {
    state.number[ear] = null;
  }
}

function setFromPair(parsed) {
  for (const ear of EARS) {
    const n = parsed[ear];
    const d = EN.decode(n);
    state.number[ear] = n;
    state.points[ear] = Object.fromEntries(FREQS.map((f) => [f, Math.round(d[f] * 10) / 10]));
    state.suffix[ear] = parsed[ear + "_suffix"] || "";
  }
  ui.estimated.checked = EARS.every((ear) => state.suffix[ear].includes("E"));
}

function pairText() {
  const { left, right } = state.number;
  if (left === null || right === null) return null;
  return EN.formatPair(left, right, true, state.suffix.left, state.suffix.right);
}

const linkFragment = (text) => text.replace(/ /g, "-");

// After a change made on the charts or grid: show the pair in the field (live), and write it to
// the address when the change is finished (not on every drag step: Safari limits how often a
// page may rewrite its address).
function updateField() {
  const text = pairText();
  if (text && document.activeElement !== ui.pair) {
    ui.pair.value = text;
    ui.pair.removeAttribute("aria-invalid");
  }
}

function commit() {
  const text = pairText();
  if (text) history.replaceState(null, "", "#" + linkFragment(text));
}

// ------------------------------------------------------------------ rendering
function bandName(n) {
  return t(NUMBER_BANDS.find(([lo]) => n >= lo)[1]);
}

function render({ fromPoints = false } = {}) {
  for (const ear of EARS) {
    drawChart(ear);
    const n = state.number[ear];
    const u = ui[ear];
    u.num.textContent = n === null ? "–" : String(n).padStart(3, "0") + state.suffix[ear];
    if (n === null) u.band.textContent = "";
    else if (n === 0) u.band.textContent = t("no_hearing");
    else {
      const q = Math.floor(n / 50), lo = (19 - q) * 5;
      const avg = q === 19 ? t("avg_under5") : q === 0 ? t("avg_95") : t("avg_range", { lo, hi: lo + 5 });
      u.band.textContent = t("band_line", { band: bandName(n), avg });
    }
    renderNote(ear);
  }
  renderGrid();
  renderShare();
  if (fromPoints) {
    updateField();
    setStatus("");
  }
}

function shareUrl(text) {
  return location.origin + location.pathname.replace(/index\.html$/, "") + "#" + linkFragment(text);
}

// The share row shows the link itself: the address in grey, then the numbers in bold.
function renderShare() {
  const text = pairText();
  const [host, path] = shortAddress();
  ui.pfxHost.textContent = host;
  ui.pfxPath.textContent = path;
  ui.prefix.title = text ? shareUrl(text) : "";      // hover shows the full link
  markClipped();
  for (const b of [ui.copyNumber, ui.copyLink]) {
    b.disabled = !text;
    resetCopied(b);
  }
  const plain = text ? text.replace(/[A-Z]/g, "") : "";
  for (const b of document.querySelectorAll(".examples button")) {
    b.setAttribute("aria-pressed", String(plain === b.dataset.pair));
  }
  renderSocial(text);
}

// The address in front of the number only suggests the link (the Link button copies the real
// one): the site's last two name parts, "…" for any folder, and the language folder if there is
// one. nickrhill.github.io/ear-number/ shows as "…github.io/…/#", its Spanish page
// /ear-number/es/ as "…github.io/…/es/#", and earnumber.org/ as "earnumber.org/#".
const LANG_DIR = /^[a-z]{2}(-[a-z]{2,4})?$/i;   // a language folder: es, hi, zh-hans, pt-br

function shortAddress() {
  const labels = location.hostname.split(".");
  // keep three parts when the second-last is a short suffix part, as in example.co.uk
  const keep = labels.length >= 3 && labels.at(-2).length <= 3 ? 3 : 2;
  const host = labels.length > keep ? "\u2026" + labels.slice(-keep).join(".") : location.hostname;
  const parts = location.pathname.replace(/index\.html$/, "").split("/").filter(Boolean);
  const lang = parts.length && LANG_DIR.test(parts.at(-1)) ? parts.pop() : null;
  return [host, (parts.length ? "/\u2026" : "") + (lang ? "/" + lang : "") + "/#"];
}

// Fade the left edge of the address only when it is too long to show whole.
function markClipped() {
  const pre = ui.pfxHost.closest(".prefix");
  pre.classList.toggle("clipped", pre.querySelector(".pfx").getBoundingClientRect().width > pre.clientWidth + 1);
}

// Plain share links: nothing from these services loads on the page.
function shareMessage(text) {
  return t("share_message", { pair: text });
}

const NETWORKS = {
  whatsapp: (m, u) => `https://wa.me/?text=${encodeURIComponent(m + " " + u)}`,
  x: (m, u) => `https://x.com/intent/post?text=${encodeURIComponent(m)}&url=${encodeURIComponent(u)}`,
  facebook: (m, u) => `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(u)}`,
  bluesky: (m, u) => `https://bsky.app/intent/compose?text=${encodeURIComponent(m + " " + u)}`,
  linkedin: (m, u) => `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(u)}`,
  reddit: (m, u) => `https://www.reddit.com/submit?url=${encodeURIComponent(u)}&title=${encodeURIComponent(m)}`,
  email: (m, u) => `mailto:?subject=${encodeURIComponent(t("share_subject"))}&body=${encodeURIComponent(m + "\n" + u)}`,
};

function renderSocial(text) {
  ui.social.hidden = !text;
  if (!text) return;
  const m = shareMessage(text), u = shareUrl(text);
  for (const a of ui.social.querySelectorAll("a[data-net]")) a.href = NETWORKS[a.dataset.net](m, u);
}

function renderNote(ear) {
  const u = ui[ear], p = state.points[ear], n = state.number[ear];
  u.note.replaceChildren();
  const missing = EN.REQUIRED_FREQS.filter((f) => p[f] === null || p[f] === undefined);
  if (missing.length === 1 && missing[0] === 8000 && p[6000] !== null && p[6000] !== undefined) {
    u.note.append(t("note_no8k", { v: fmtDb(p[6000]) }));
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = t("copy_6k", { v: fmtDb(p[6000]) });
    b.addEventListener("click", () => { setPoint(ear, 8000, p[6000]); commit(); });
    u.note.append(document.createElement("br"), b);
  } else if (missing.length) {
    u.note.textContent = t("note_needs", { freqs: missing.map((f) => FLABEL[f] + "Hz").join(", ") });
  } else if (n !== null && n !== 0 && EN.encode(EN.decode(n)) !== n) {
    u.note.textContent = t("note_unreal");
  }
}

function buildGrid() {
  const head = $(".grid thead tr");
  for (const f of FREQS) {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = FLABEL[f] + "Hz";
    if (OPTIONAL.has(f)) {
      const o = document.createElement("span");
      o.className = "opt";
      o.textContent = t("optional");
      th.append(o);
    }
    head.append(th);
  }
  for (const ear of EARS) {
    const row = $(`.grid tr[data-ear="${ear}"]`);
    for (const f of FREQS) {
      const td = document.createElement("td");
      const inp = document.createElement("input");
      Object.assign(inp, { type: "number", step: "5", min: "-10", max: "120", inputMode: "numeric" });
      inp.dataset.ear = ear;
      inp.dataset.f = f;
      inp.setAttribute("aria-label", t("point_aria", { ear: earName(ear), freq: FLABEL[f] + "Hz" }) + ", dB HL");
      inp.addEventListener("input", () => {
        const raw = inp.value.trim();
        const v = raw === "" ? null : Number(raw);
        if (v !== null && !Number.isFinite(v)) return;
        state.points[ear][f] = v;
        recompute(ear);
        render({ fromPoints: true });
        commit();
      });
      td.append(inp);
      row.append(td);
    }
  }
}

function renderGrid() {
  for (const inp of document.querySelectorAll(".grid input")) {
    if (inp === document.activeElement) continue;
    inp.value = fmtDb(state.points[inp.dataset.ear][Number(inp.dataset.f)]);
  }
}

function setStatus(text, kind = "") {
  ui.status.textContent = text;
  ui.status.className = "status" + (kind ? " " + kind : "");
}

// ------------------------------------------------------------------ the number field and the address
function applyText(text, { fromAddress = false } = {}) {
  stopDemo();
  let parsed;
  try {
    parsed = EN.parsePair(text);
  } catch (err) {
    ui.pair.setAttribute("aria-invalid", "true");
    const digits = text.replace(/\D/g, "").length;
    if (/check digit/.test(err.message)) setStatus(t("st_check_bad"), "bad");
    else if (/suffix/.test(err.message)) setStatus(t("st_suffix_bad"), "bad");
    else if (fromAddress || digits >= 6) setStatus(t("st_not_pair"), "bad");
    else setStatus(t("st_type_six"));
    return false;
  }
  ui.pair.removeAttribute("aria-invalid");
  setFromPair(parsed);
  render();
  const canonical = pairText();
  if (parsed.check === null) setStatus(t("st_no_check", { c: EN.checkDigit(parsed.left, parsed.right) }));
  else setStatus(t("st_check_ok"), "ok");
  history.replaceState(null, "", "#" + linkFragment(canonical));
  return true;
}

function readAddress() {
  const hash = decodeURIComponent(location.hash.replace(/^#/, "")).trim();
  const query = new URLSearchParams(location.search).get("ear");
  const text = hash || (query ? query.trim() : "");
  return text || null;
}

function loadFromAddress() {
  const text = readAddress();
  if (text) {
    ui.pair.value = text;
    if (applyText(text, { fromAddress: true })) ui.pair.value = pairText();
  } else {
    ui.pair.value = EXAMPLE;
    setFromPair(EN.parsePair(EXAMPLE));
    render();
  }
}

// Copy buttons: the icon turns to a tick and the word to "Copied" for a moment.
function resetCopied(btn) {
  clearTimeout(btn._timer);
  btn.classList.remove("copied");
  const w = btn.querySelector(".copy-word");
  w.textContent = w.dataset.word;
}

async function copyValue(btn, value) {
  try {
    await navigator.clipboard.writeText(value);
  } catch {
    setStatus(t("st_copy_this", { v: value }));
    return;
  }
  resetCopied(btn);
  btn.classList.add("copied");
  btn.querySelector(".copy-word").textContent = t("copied");
  btn._timer = setTimeout(() => resetCopied(btn), 2500);
}

// ------------------------------------------------------------------ start
let tableReady = false;

async function start() {
  ui.pair = $("#pair");
  ui.status = $("#status");
  ui.estimated = $("#estimated");
  ui.copyNumber = $("#copy-number");
  ui.copyLink = $("#copy-link");
  ui.social = $("#social");
  ui.pfxHost = $(".pfx-host");
  ui.pfxPath = $(".pfx-path");
  ui.prefix = $(".prefix");
  new ResizeObserver(markClipped).observe(ui.prefix);
  // Clicking the grey address (not the number) copies the full link, with a one-second "Copied".
  ui.prefix.dataset.copied = "\u2713 " + t("copied");
  ui.prefix.addEventListener("click", async () => {
    const text = pairText();
    if (!text) return;
    history.replaceState(null, "", "#" + linkFragment(text));
    try { await navigator.clipboard.writeText(shareUrl(text)); } catch { return; }
    ui.prefix.classList.add("copied");
    clearTimeout(ui.prefix._timer);
    ui.prefix._timer = setTimeout(() => ui.prefix.classList.remove("copied"), 1000);
  });
  for (const ear of EARS) {
    const fig = $(`.ear[data-ear="${ear}"]`);
    ui[ear] = { svg: $("svg", fig), num: $(".ear-num", fig), band: $(".ear-band", fig), note: $(".ear-note", fig) };
    buildChart(ear);
  }
  buildGrid();

  try {
    await EN.loadTableUrl(new URL("earnumber-v1.json", import.meta.url));  // beside this script, for every language folder
  } catch (err) {
    setStatus(t("st_table_failed", { msg: err.message }), "bad");
    ui.pair.disabled = true;
    return;
  }
  tableReady = true;
  loadFromAddress();
  setTimeout(runDemo, 400);

  ui.pair.addEventListener("input", () => applyText(ui.pair.value));
  ui.pair.addEventListener("blur", () => {
    const text = pairText();
    if (text && !ui.pair.hasAttribute("aria-invalid")) ui.pair.value = text;
  });
  ui.copyNumber.addEventListener("click", () => { const t = pairText(); if (t) copyValue(ui.copyNumber, t); });
  // Language menu and the EN link keep the numbers: they carry the current # along.
  $("#lang")?.addEventListener("change", (e) => {
    const u = new URL(e.target.value, location.href);
    u.hash = location.hash;
    location.href = u.href;
  });
  $(".lang-en")?.addEventListener("click", (e) => {
    e.preventDefault();
    const u = new URL(e.currentTarget.getAttribute("href"), location.href);
    u.hash = location.hash;
    location.href = u.href;
  });
  ui.copyLink.addEventListener("click", () => {
    const t = pairText();
    if (!t) return;
    history.replaceState(null, "", "#" + linkFragment(t));
    copyValue(ui.copyLink, shareUrl(t));
  });
  document.addEventListener("keydown", firstTabToChart, true);
  const native = $("#native-share");
  if (navigator.share) {
    native.hidden = false;
    native.addEventListener("click", () => {
      const text = pairText();
      if (text) navigator.share({ title: "Ear Number", text: shareMessage(text), url: shareUrl(text) }).catch(() => {});
    });
  }
  $("#theme").addEventListener("click", () => {
    const root = document.documentElement;
    const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch { /* private mode: not remembered */ }
  });
  for (const b of document.querySelectorAll(".examples button")) {
    b.addEventListener("click", () => {
      stopDemo();
      ui.pair.value = b.dataset.pair;
      applyText(b.dataset.pair);
      setStatus("");
    });
  }
  window.addEventListener("hashchange", () => {
    const text = readAddress();
    if (text && text.replace(/[\s,;-]/g, "") !== (pairText() || "").replace(/[\s,;-]/g, "")) {
      ui.pair.value = text;
      applyText(text, { fromAddress: true });
    }
  });

  for (const r of document.querySelectorAll('input[name="source"]')) {
    r.addEventListener("change", () => {
      for (const g of document.querySelectorAll(".guide")) g.hidden = g.dataset.source !== r.value;
      if (r.value === "phone" && !ui.estimated.checked) {
        ui.estimated.checked = true;
        ui.estimated.dispatchEvent(new Event("change"));
      }
    });
  }
  ui.estimated.addEventListener("change", () => {
    for (const ear of EARS) {
      const s = state.suffix[ear].replace(/E/g, "");
      state.suffix[ear] = ui.estimated.checked ? s + "E" : s;
    }
    render({ fromPoints: true });
    commit();
  });
  $("#clear").addEventListener("click", () => {
    for (const ear of EARS) {
      state.points[ear] = Object.fromEntries(FREQS.map((f) => [f, null]));
      state.number[ear] = null;
      state.suffix[ear] = ui.estimated.checked ? "E" : "";
    }
    ui.pair.value = "";
    history.replaceState(null, "", location.pathname);
    setStatus(t("st_clear"));
    render();
  });
}

start();
