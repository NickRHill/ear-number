#!/usr/bin/env python3
"""Rebuild the Ear Number table (earnumber-v1.json) from the NHANES public-use files and
print its evaluation (also written to build/results.md; aggregates only).

Usage (after python3 build/fetch_nhanes.py):
  python3 build/build_table.py [--weighting loss|population|equal|70plus] [--nhanes DIR]
                               [--out FILE] [--results FILE]
  python3 build/build_table.py --check      # build afresh, compare with the shipped JSON

Needs numpy and pandas (see requirements.txt). Self-contained: it does not import earnumber.py.
The shipped table is trained on a random half of the persons in each age band (fixed seed) and
evaluated on the other half; the same ears and seeds give the same table.
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

FREQS = [500, 1000, 2000, 3000, 4000, 6000, 8000]
BAND_WEIGHTS = {250: 0.0617, 500: 0.1671, 1000: 0.2373, 2000: 0.2648, 4000: 0.2142, 8000: 0.0549}
LO, HI = -10.0, 100.0
EDGE_NONE_HZ = 16000.0
BANDS = ["6-19", "20-69", "70+"]
# Ages each cycle's audiometry covered (inclusive; RIDAGEYR is top-coded at 80), and the years
# each cycle spans. Following NCHS guidance for combining cycles, each person's MEC weight is
# multiplied by their cycle's years / the total years of the cycles covering their age, so all
# ears together represent the US population aged 6 and over once.
COVERAGE = {"2009-10": [(12, 19), (70, 80)], "2011-12": [(20, 69)], "2015-16": [(20, 69)],
            "2017-Mar 2020": [(6, 19), (70, 80)]}
YEARS = {"2009-10": 2.0, "2011-12": 2.0, "2015-16": 2.0, "2017-Mar 2020": 3.2}
# Hearing loss for the loss weighting (WHO 2021, applied per ear): mean of 0.5, 1, 2, 4 kHz >= 20 dB HL.
LOSS_DB = 20.0
AGE_CENTRE, AGE_SCALE = 45.0, 25.0     # z = (age - 45) / 25 in the prevalence curve
WEIGHTINGS = ["loss", "population", "equal", "70plus"]
CYCLES = [  # name, AUX, DEMO, AUQ, MEC weight, general-hearing self-report variable
    ("2009-10", "AUX_F", "DEMO_F", "AUQ_F", "WTMEC2YR", "AUQ131"),
    ("2011-12", "AUX_G", "DEMO_G", "AUQ_G", "WTMEC2YR", "AUQ054"),
    ("2015-16", "AUX_I", "DEMO_I", "AUQ_I", "WTMEC2YR", "AUQ054"),
    ("2017-Mar 2020", "P_AUX", "P_DEMO", "P_AUQ", "WTMECPRP", "AUQ054"),
]
SUF = {500: "500", 1000: "1K1", 2000: "2K", 3000: "3K", 4000: "4K", 6000: "6K", 8000: "8K"}
SEED_SPLIT, SEED_KM, SEED_NOISE, RESTARTS = 1, 7, 2, 30
MIN_EFFECTIVE = 10     # every shape must rest on at least this many effective training ears (Kish)
SR_NAMES = ["excellent", "good", "a little trouble", "moderate trouble", "a lot of trouble", "deaf"]
LADDER_NAMES = {6: "excellent or good", 5: "hears a whisper", 4: "hears a normal voice",
                3: "hears a shout", 2: "hears loud speech into the ear", 1: "none of these"}


# ------------------------------------------------------------------ helpers
def wpercentile(x, w, qs):
    """Weighted percentiles (qs in 0-100), linear interpolation on the weighted CDF."""
    x = np.asarray(x, float); w = np.asarray(w, float)
    o = np.argsort(x, kind="stable"); x = x[o]; w = w[o]
    cw = (np.cumsum(w) - 0.5 * w) / w.sum()
    return np.interp(np.asarray(qs) / 100.0, cw, x)


def wpct(x, w, q):
    return float(wpercentile(x, w, [q])[0])


def edge_hz(t, drop=20.0):
    """Frequency where the threshold first reaches t(1 kHz)+drop, going up from 1 kHz, by
    log-frequency interpolation between measured points; inf if never. t is given at FREQS."""
    t = np.asarray(t, float)
    tgt = t[1] + drop
    lf = np.log(FREQS)
    for i in range(1, len(FREQS) - 1):
        if t[i + 1] >= tgt:
            if t[i + 1] == t[i]:
                return float(FREQS[i + 1])
            frac = (tgt - t[i]) / (t[i + 1] - t[i])
            frac = min(max(frac, 0.0), 1.0)
            return float(math.exp(lf[i] + frac * (lf[i + 1] - lf[i])))
    return float("inf")


def inner_point_hz(edge):
    e = EDGE_NONE_HZ if (edge is None or edge == float("inf")) else min(max(float(edge), 1000.0), EDGE_NONE_HZ)
    return min(e / 2 if e >= 4000 else math.sqrt(1000 * e), 4000.0)


# ------------------------------------------------------------------ data
def load_ears(d):
    """One row per ear with a complete 7-frequency audiogram and a valid exam
    (AUAEXSTS 1 complete or 2 partial). 666 (no response) -> 110, 888 -> missing.
    Also the self-report and (2017-20 only) the four functional questions."""
    rows = []
    for cyc, aux, demo, auq, wt, sr in CYCLES:
        X = pd.read_sas(os.path.join(d, aux + ".xpt")); D = pd.read_sas(os.path.join(d, demo + ".xpt"))
        Q = pd.read_sas(os.path.join(d, auq + ".xpt"))
        extra = [c for c in ("AUQ060", "AUQ070", "AUQ080", "AUQ090") if c in Q.columns and cyc.startswith("2017")]
        m = D[["SEQN", "RIDAGEYR", wt]].merge(X, on="SEQN").merge(Q[["SEQN", sr] + extra], on="SEQN", how="left")
        m = m[(m.RIDAGEYR >= 6) & m.AUAEXSTS.isin([1, 2]) & (m[wt] > 0)]
        s = m[sr].astype(float).where(m[sr].between(1, 6))
        # functional ladder (2017-20): 6 best .. 1 worst; see the paper for the wording
        lad = np.full(len(m), np.nan)
        if extra:
            q = {c: m[c].to_numpy(float) for c in extra}; g = s.to_numpy()
            lad[g <= 2] = 6
            t = g >= 3
            lad[t & (q["AUQ060"] == 1)] = 5
            lad[t & (q["AUQ060"] == 2) & (q["AUQ070"] == 1)] = 4
            lad[t & (q["AUQ070"] == 2) & (q["AUQ080"] == 1)] = 3
            lad[t & (q["AUQ080"] == 2) & (q["AUQ090"] == 1)] = 2
            lad[t & (q["AUQ090"] == 2)] = 1
        for side in "RL":
            T = np.column_stack([m[f"AUXU{SUF[f]}{side}"].astype(float).to_numpy() for f in FREQS])
            T[T == 888] = np.nan; T[T == 666] = 110.0
            ok = ~np.isnan(T).any(1)
            T2k = m[f"AUXU1K2{side}"].astype(float).to_numpy().copy()   # second 1 kHz reading (repeat)
            T2k[T2k == 888] = np.nan; T2k[T2k == 666] = 110.0
            rows.append(pd.DataFrame({
                "pkey": [f"{cyc}:{int(i)}" for i in m.SEQN[ok]], "cycle": cyc, "side": side,
                "age": m.RIDAGEYR.to_numpy()[ok], "w": m[wt].to_numpy()[ok].astype(float),
                "sr": s.to_numpy()[ok], "lad": lad[ok],
                **{f"t{f}": np.minimum(T[ok, k], HI) for k, f in enumerate(FREQS)},
                "t1k2": T2k[ok]}))
    E = pd.concat(rows, ignore_index=True)
    E["band"] = np.where(E.age < 20, "6-19", np.where(E.age < 70, "20-69", "70+"))
    covered = lambda cyc, age: any(a <= age <= b for a, b in COVERAGE[cyc])
    assert all(covered(c, a) for c, a in zip(E.cycle, E.age)), "ear outside its cycle's declared ages"
    years = E.age.map(lambda a: sum(YEARS[c] for c in COVERAGE if covered(c, a)))
    E["w"] = E.w * E.cycle.map(YEARS) / years      # US residents represented, cycles combined
    # hold out half the persons of each band (fixed seed)
    rng = np.random.default_rng(SEED_SPLIT); test = {}
    for b in BANDS:
        keys = np.array(sorted(E.pkey[E.band == b].unique())); rng.shuffle(keys)
        test.update({k: True for k in keys[: len(keys) // 2]})
    E["test"] = E.pkey.map(lambda k: test.get(k, False))
    return E


def band_norm(w, band, mask):
    """Weights renormalised to sum 1 within each band over `mask`."""
    out = np.zeros(len(w))
    for b in BANDS:
        m = mask & (band == b)
        out[m] = w[m] / w[m].sum()
    return out


def loss_flag(T):
    """Hearing loss per ear (WHO): mean threshold over 0.5, 1, 2, 4 kHz >= 20 dB HL."""
    return T[:, [0, 1, 2, 4]].mean(1) >= LOSS_DB


def prevalence_fit(age, loss, w, iters=50):
    """Survey-weighted logistic regression of hearing loss on age, log-odds quadratic in
    z = (age - 45) / 25. Returns the three coefficients."""
    z = (np.asarray(age, float) - AGE_CENTRE) / AGE_SCALE; X = np.column_stack([np.ones_like(z), z, z * z])
    y = np.asarray(loss, float); w = np.asarray(w, float) / np.mean(w); b = np.zeros(3)
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ b)); W = w * p * (1 - p)
        b = b + np.linalg.solve(X.T @ (W[:, None] * X), X.T @ (w * (y - p)))
    return np.round(b, 6)


def prevalence(age, b):
    z = (np.asarray(age, float) - AGE_CENTRE) / AGE_SCALE
    return 1 / (1 + np.exp(-(b[0] + b[1] * z + b[2] * z * z)))


# ------------------------------------------------------------------ coder (numpy twin of earnumber.py)
def Hval(T):
    W = BAND_WEIGHTS   # 250 uses the 500 Hz value
    return np.round(W[250] * T[:, 0] + W[500] * T[:, 0] + W[1000] * T[:, 1] + W[2000] * T[:, 2]
                    + W[4000] * T[:, 4] + W[8000] * T[:, 6], 6)


class Coder:
    def __init__(self, C): self.C = np.asarray(C, float)
    def level(self, T): return (19 - np.clip(np.floor(Hval(T) / 5), 0, 19)).astype(int)
    def shape(self, T):
        """Nearest shape (raw: ignores the reserved number 000)."""
        R = T - Hval(T)[:, None]
        return ((R[:, None, :] - self.C[None]) ** 2).sum(2).argmin(1)
    def code(self, T):
        """As earnumber.py: 000 is reserved for 100 dB at every frequency (no hearing), so at
        level 0 shape 0 is never chosen (the next nearest is taken)."""
        T = np.asarray(T, float); lv = self.level(T); R = T - Hval(T)[:, None]
        D = ((R[:, None, :] - self.C[None]) ** 2).sum(2)
        D[lv == 0, 0] = np.inf
        return np.where((T >= HI).all(1), 0, lv * 50 + D.argmin(1))
    def decode(self, N):
        N = np.asarray(N); centre = (19 - N // 50 + 0.5) * 5
        out = np.clip(centre[:, None] + self.C[N % 50], LO, HI)
        out[N == 0] = HI
        return out


def wkmeans(X, w, k, seed, iters=150):
    rng = np.random.default_rng(seed); w = w / w.sum()
    idx = [rng.choice(len(X), p=w)]; d2 = ((X - X[idx[0]]) ** 2).sum(1)
    for _ in range(k - 1):
        p = w * d2; i = rng.choice(len(X), p=p / p.sum()); idx.append(i); d2 = np.minimum(d2, ((X - X[i]) ** 2).sum(1))
    C = X[idx].copy()
    for _ in range(iters):
        a = ((X[:, None, :] - C[None]) ** 2).sum(2).argmin(1); N = C.copy()
        for j in range(k):
            m = a == j
            if w[m].sum() > 0: N[j] = (X[m] * w[m, None]).sum(0) / w[m].sum()
        done = np.abs(N - C).max() < 1e-6; C = N
        if done: break
    D = ((X[:, None, :] - C[None]) ** 2).sum(2).min(1)
    return C, float((w * D).sum())


def order_shapes(C):
    """Higher index = higher cutoff: sort by the edge frequency of the residual curve (no edge
    = highest); ties and no-edge shapes by mean residual over 4-8 kHz, larger (more treble
    loss) first, so less treble loss = higher index."""
    edge = np.array([edge_hz(c) for c in C]); edge = np.where(np.isinf(edge), 1e9, edge)
    treble = C[:, [4, 5, 6]].mean(1)
    return np.lexsort((-treble, edge)), edge, treble


def effective_min(X, w, C):
    """Smallest Kish effective sample size, (sum w)^2 / sum w^2, over the shapes' members."""
    a = ((X[:, None, :] - C[None]) ** 2).sum(2).argmin(1)
    return min(w[a == j].sum() ** 2 / max((w[a == j] ** 2).sum(), 1e-300) for j in range(len(C)))


def train_shapes(T, wtrain):
    """Lowest-inertia k-means restart among those in which every shape has at least
    MIN_EFFECTIVE effective training ears (so no shape rests on a few heavily weighted ears)."""
    m = wtrain > 0; X = (T - Hval(T)[:, None])[m]; w = wtrain[m]
    best = None
    for r in range(RESTARTS):
        C, inertia = wkmeans(X, w, 50, SEED_KM + r)
        if effective_min(X, w, C) >= MIN_EFFECTIVE and (best is None or inertia < best[1]): best = (C, inertia)
    if best is None:
        sys.exit(f"no restart gave every shape {MIN_EFFECTIVE} effective ears; raise RESTARTS")
    C, inertia = best
    order, _, _ = order_shapes(C)
    return np.round(C[order], 1), inertia


# ------------------------------------------------------------------ quick-test regression
def quad(Z):
    cols = [np.ones(len(Z))] + [Z[:, i] for i in range(3)] + [Z[:, i] ** 2 for i in range(3)] \
        + [Z[:, i] * Z[:, j] for i in range(3) for j in range(i + 1, 3)]
    return np.column_stack(cols)


def quick_features(T):
    E = np.array([edge_hz(t) for t in T]); E = np.where(np.isinf(E), EDGE_NONE_HZ, E)
    E = np.clip(E, 1000.0, EDGE_NONE_HZ)
    F3 = np.array([inner_point_hz(e) for e in E]); lf = np.log2(FREQS)
    t3 = np.array([np.interp(np.log2(f), lf, t) for t, f in zip(T, F3)])
    return {"inner_point": np.column_stack([T[:, 1], np.log2(E), t3]),
            "hz8k": np.column_stack([T[:, 1], np.log2(E), T[:, 6]])}


def fit_quick(T, w):
    m = w > 0; sw = np.sqrt(w[m] / w[m].mean()); out = {}
    for name, Z in quick_features(T[m]).items():
        Xq = quad(Z); b, *_ = np.linalg.lstsq(Xq * sw[:, None], T[m] * sw[:, None], rcond=None)
        out[name] = b.T       # (7 targets, 10 coefficients)
    return out


def quick_estimate(T, coefs):
    return {name: np.clip(quad(Z) @ np.array(coefs[name]).T, LO, HI) for name, Z in quick_features(T).items()}


# ------------------------------------------------------------------ evaluation
def spearman(a, b):
    ra = pd.Series(np.asarray(a, float)).rank().to_numpy(); rb = pd.Series(np.asarray(b, float)).rank().to_numpy()
    return float(np.corrcoef(ra, rb)[0, 1])


def evaluate(E, T, C, coefs, prev):
    cd = Coder(C); te = E.test.to_numpy(); band = E.band.to_numpy()
    w = E.w.to_numpy()          # survey weights (US residents); percentiles and shares are scale-free
    wall = w
    N = cd.code(T); err = cd.decode(N) - T; rms = np.sqrt((err ** 2).mean(1))
    res = {"N": N}
    wl = w * prevalence(E.age, prev)                        # loss-weighted (the training target)
    res["rms_loss"] = (wpct(rms[te], wl[te], 50), wpct(rms[te], wl[te], 90))
    grade = np.digitize(T[:, [0, 1, 2, 4]].mean(1), [20, 35, 50, 65])
    res["rms_grade"] = [(wpct(rms[te & (grade == g)], w[te & (grade == g)], 50), int((te & (grade == g)).sum()))
                        for g in range(5)]
    r = {}
    for b in BANDS + ["all"]:
        m = te & ((band == b) if b != "all" else True)
        ww = w[m] if b != "all" else wall[m]
        r[b] = dict(med=wpct(rms[m], ww, 50), p90=wpct(rms[m], ww, 90), over10=float(ww[rms[m] > 10].sum() / ww.sum()), n=int(m.sum()))
    res["rms_stats"] = r
    # per-frequency decode RMS
    pf = {}
    for b in BANDS + ["all"]:
        m = te & ((band == b) if b != "all" else True); ww = w[m] if b != "all" else wall[m]
        pf[b] = np.sqrt((ww[:, None] * err[m] ** 2).sum(0) / ww.sum())
    res["freq_rms"] = pf
    # retest stability
    rn = np.random.default_rng(SEED_NOISE)
    T2 = np.clip(np.round((T + rn.normal(0, 4, T.shape) + rn.normal(0, 2, (len(T), 1))) / 5) * 5, LO, HI)
    mv = np.abs(cd.code(T2) // 50 - N // 50) >= 2
    res["retest"] = {b: float(w[te & (band == b)][mv[te & (band == b)]].sum() / w[te & (band == b)].sum()) for b in BANDS}
    res["retest"]["all"] = float(wall[te][mv[te]].sum() / wall[te].sum())
    # Spearman of the better ear's N with self-report (test-group persons with both ears)
    d = better_ear_table(E, N)
    d = d[d.test]; sp = {}
    for b in BANDS + ["all"]:
        s = d if b == "all" else d[d.band == b]
        s = s.dropna(subset=["sr"])
        sp[b] = (spearman(s.best, -s.sr) if len(s) > 20 else float("nan"), len(s))
    res["spearman"] = sp
    # N percentiles by band (test-group ears, survey-weighted)
    res["npct"] = {b: [wpct(N[te & (band == b)], w[te & (band == b)], q) for q in (5, 25, 50, 75, 95)] for b in BANDS}
    # round trip
    allN = np.arange(1000); back = cd.code(cd.decode(allN))
    res["roundtrip_fail"] = int((back != allN).sum()); res["roundtrip_level_fail"] = int((back // 50 != allN // 50).sum())
    res["roundtrip_000"] = bool(back[0] == 0)
    # quick-test path
    est = quick_estimate(T, coefs); qp = {}
    for name, Te in est.items():
        Ne = cd.code(Te); e = np.sqrt(((cd.decode(Ne) - T) ** 2).mean(1)); one = np.abs(Ne // 50 - N // 50) <= 1
        qp[name] = {}
        for b in BANDS + ["all"]:
            m = te & ((band == b) if b != "all" else True); ww = w[m] if b != "all" else wall[m]
            qp[name][b] = (wpct(e[m], ww, 50), wpct(e[m], ww, 90), float(ww[one[m]].sum() / ww.sum()))
    res["quick"] = qp
    # shape occupancy: ears (all, and training half) per shape
    sh = cd.shape(T); res["shape_counts"] = np.bincount(sh, minlength=50)
    res["shape_counts_train"] = np.bincount(sh[~te], minlength=50)
    res["level_counts"] = np.bincount(N // 50, minlength=20)
    return res


def better_ear_table(E, N):
    """One row per person with both ears: better ear's code, survey weight, band, self-report, ladder."""
    d = pd.DataFrame({"pkey": E.pkey, "side": E.side, "N": N, "w": E.w, "sr": E.sr, "lad": E.lad,
                      "band": E.band, "test": E.test})
    p = d.pivot_table(index="pkey", columns="side", values="N", aggfunc="first").dropna()
    g = d.groupby("pkey").agg(w=("w", "first"), sr=("sr", "first"), lad=("lad", "first"),
                              band=("band", "first"), test=("test", "first"))
    out = p.join(g, how="inner")
    out["best"] = out[["L", "R"]].max(axis=1)
    return out


def signify(E, N):
    """Better ear's code by self-report category and by the 2017-20 functional ladder:
    survey-weighted median and quartiles, n persons; cells with n < 10 are suppressed."""
    d = better_ear_table(E, N)
    d["wp"] = d.w                              # survey weights already represent the population
    sr_groups = [("70+", d[d.band == "70+"], "w"), ("20-69", d[d.band == "20-69"], "w"), ("all ages", d, "wp")]
    # the functional questions were asked of ages 6-19 and 70+ only
    lad_groups = [("70+", d[d.band == "70+"], "w"), ("6-19", d[d.band == "6-19"], "w"),
                  ("6-19 and 70+", d[d.band != "20-69"], "wp")]
    out = {}
    for kind, col, cats, groups in (("self-report", "sr", range(1, 7), sr_groups),
                                    ("ladder", "lad", range(6, 0, -1), lad_groups)):
        out[kind] = {}
        for gname, g, wc in groups:
            row = []
            for c in cats:
                s = g[g[col] == c]
                if len(s) < 10: row.append((len(s), None))
                else: row.append((len(s), tuple(wpct(s.best, s[wc], q) for q in (25, 50, 75))))
            out[kind][gname] = row
    return out


def f1(x): return f"{x:.1f}"


def blk(x):
    """A code as its block of 50, e.g. 795 -> 750-799."""
    b = int(x // 50) * 50
    return f"{b:03d}-{b + 49:03d}"


def design_report(ev):
    L = []; P = L.append
    P("\n## Where the error comes from (test group; median / 90th percentile in dB; loss-weighted, and 70+ population-weighted)\n")
    P("| Variant | loss-weighted | 70+ |\n|---|---|---|")
    for nm, s in ev["a"]:
        P(f"| {nm} | {f1(s['loss'][0])} / {f1(s['loss'][1])} | {f1(s['70+'][0])} / {f1(s['70+'][1])} |")
    P("\nThe typical shape of a level is the training-half loss-weighted mean residual of the ears at that level.\n")
    P("## Retest detail (simulated retest as in the stability section; test group)\n")
    P("| Group | level unchanged | moves one step | moves two or more | same shape | identical number |\n|---|---|---|---|---|---|")
    for r in ev["b"]:
        P(f"| {r[0]} | " + " | ".join(f"{x:.1%}" for x in r[1:]) + " |")
    n, sd, sh = ev["c"]
    P("\n## Real repeat of the 1 kHz reading (NHANES measures it twice)\n")
    P(f"Over all {n} ears where both readings are valid thresholds (neither a no-response 666, nor missing, nor at 100 dB or above): "
      f"standard deviation of the difference {sd:.2f} dB; share differing by 10 dB or more {sh:.1%}.\n")
    P("## Order of the numbers (400000 random pairs of test ears, drawn with loss weights; pairs with different numbers only)\n")
    P("| Gap between the two numbers | pairs | higher number has the lower H (ties count half) | same level |\n|---|---|---|---|")
    for nm, k, ok, sm in ev["d"]:
        P(f"| {nm} | {k} | {ok:.1%} | {sm:.1%} |")
    P("\n## Design comparisons (trained on the training half with loss weights; test group, loss-weighted)\n")
    P("| Design | codes | median / 90th percentile RMS (dB) | share of ears over 10 dB |\n|---|---|---|---|")
    for nm, k, (m, p9, o) in ev["e"]:
        P(f"| {nm} | {k} | {f1(m)} / {f1(p9)} | {o:.1%} |")
    P("\nk-means designs: 5 dB level, 3 restarts (seeds 7-9), lowest inertia kept. The LCH triad (Humes and Zapala 2024) is "
      "floor(mean threshold / 10), clipped 0-9, for L = 0.5, 1, 2 kHz, C = 3, 4, 6 kHz and H = 8 kHz.\n")
    P("| Code | pairs ordered as H when read as one number (triad: lower is better) | identical code on the simulated retest | distinct codes used by all ears |\n|---|---|---|---|")
    for nm, o, i, k in ev["e2"]:
        P(f"| {nm} | {o:.1%} | {i:.0%} | {k} |")
    P("\n## Self-test with input error (all test ears, population-weighted; RMS median / 90th percentile; level within 1 step)\n")
    P("| Input | 1 kHz, edge, inner point | 1 kHz, edge, 8 kHz |\n|---|---|---|")
    for cond, d in ev["f"].items():
        P(f"| {cond} | " + " | ".join(f"{f1(d[v][0])} / {f1(d[v][1])}; {d[v][2]:.0%}" for v in ("inner_point", "hz8k")) + " |")
    P("\nNoise model: independent N(0, 4 dB) on the 1 kHz value and on the third value; N(0, 0.15) octave on log2(edge), "
      "edge kept within 1000-16000 Hz; calibration offset N(0, 7 dB) common to both thresholds of the ear. Fixed seed.\n")
    lv, hc = ev["g"]
    P("## Ears per level and severe losses (all ears)\n")
    P("| Level | " + " | ".join(str(19 - i) for i in range(20)) + " |\n|---|" + "---|" * 20)
    P("| ears | " + " | ".join(str(x) for x in lv) + " |")
    P(f"\nEars with H of 50 dB or more: {hc[0]}; 65 dB or more: {hc[1]}; 80 dB or more: {hc[2]}.\n")
    return L


def report(E, res, C, weighting, prev, check_line=None):
    L = []; P = L.append; te = E.test.to_numpy()
    P(f"# Ear Number v1: build evaluation\n\nTable trained with the **{weighting}** weighting. Aggregates only; "
      "all error figures are on the test group (the half of persons not used for training) unless stated.\n")
    P("## Data (ears with a complete 7-frequency audiogram, valid exam)\n")
    P("| Cycle | 6-19 | 20-69 | 70+ |\n|---|---|---|---|")
    for cyc, *_ in CYCLES:
        P(f"| {cyc} | " + " | ".join(str(int(((E.cycle == cyc) & (E.band == b)).sum())) for b in BANDS) + " |")
    P("| all ears | " + " | ".join(str(int((E.band == b).sum())) for b in BANDS) + " |")
    P("| persons | " + " | ".join(str(E.pkey[E.band == b].nunique()) for b in BANDS) + " |")
    P("| test-group ears | " + " | ".join(str(int((te & (E.band == b)).sum())) for b in BANDS) + " |")
    b = prev
    P(f"\nWeights: each person's NHANES MEC weight x their cycle's years / total years of the cycles covering their age; "
      f"overall rows use these (US population aged 6+). Loss weighting multiplies them by p(age), the "
      f"prevalence of hearing loss per ear (WHO: mean of 0.5, 1, 2, 4 kHz >= 20 dB HL), fitted on the "
      f"training half: logit p = {b[0]:.4f} + {b[1]:.4f} z + {b[2]:.4f} z^2, z = (age - 45) / 25.\n")
    P("| Age | 6 | 10 | 20 | 30 | 40 | 50 | 60 | 70 | 80 |\n|---|---|---|---|---|---|---|---|---|---|")
    P("| p(age) | " + " | ".join(f"{prevalence(a, b):.1%}" for a in (6, 10, 20, 30, 40, 50, 60, 70, 80)) + " |\n")
    s = res["rms_stats"]
    P("## Decode RMS per ear over 0.5-8 kHz (dB; survey-weighted median / 90th percentile; share above 10 dB)\n")
    P("| 6-19 | 20-69 | 70+ | overall (population-weighted) |\n|---|---|---|---|")
    P("| " + " | ".join(f"{f1(s[b]['med'])} / {f1(s[b]['p90'])}; {s[b]['over10']:.1%}" for b in BANDS + ["all"]) + " |")
    P(f"\nLoss-weighted (ears counted in proportion to hearing loss at their age): median "
      f"{f1(res['rms_loss'][0])}, 90th percentile {f1(res['rms_loss'][1])}.\n")
    P("By WHO grade of the ear (mean of 0.5, 1, 2, 4 kHz; median RMS, test-group ears in brackets):\n")
    P("| under 20 | 20-34 | 35-49 | 50-64 | 65 and over |\n|---|---|---|---|---|")
    P("| " + " | ".join(f"{f1(m)} ({n})" for m, n in res["rms_grade"]) + " |")
    P("\n## Decode RMS per frequency (dB, across test-group ears)\n")
    P("| Band | " + " | ".join(f"{f/1000:g} kHz" for f in FREQS) + " |\n|---|" + "---|" * len(FREQS))
    for b in BANDS + ["all"]:
        P(f"| {b} | " + " | ".join(f1(x) for x in res["freq_rms"][b]) + " |")
    P("\n## Spearman rho of the better ear's code with the six-point self-report (test-group persons with both ears; n in brackets)\n")
    P("| 6-19 | 20-69 | 70+ | all |\n|---|---|---|---|")
    P("| " + " | ".join(f"{res['spearman'][b][0]:.3f} ({res['spearman'][b][1]})" for b in BANDS + ["all"]) + " |")
    P("\n## Retest stability: share of test-group ears whose level moves 2+ steps (4 dB per frequency + 2 dB common noise, 5 dB rounding)\n")
    P("| 6-19 | 20-69 | 70+ | overall |\n|---|---|---|---|")
    P("| " + " | ".join(f"{res['retest'][b]:.1%}" for b in BANDS + ["all"]) + " |")
    P("\n## Code by age band (test-group ears, survey-weighted percentiles 5 / 25 / 50 / 75 / 95)\n")
    P("| 6-19 | 20-69 | 70+ |\n|---|---|---|")
    P("| " + " | ".join(" / ".join(blk(x) for x in res["npct"][b]) for b in BANDS) + " |")
    P("\nWithin a block of 50 the last digits identify the shape and do not rank hearing.")
    P("\n## Quick-test path (estimated audiogram, then coded; RMS median / 90th pct; level within 1 step of the true level)\n")
    P("| Variant | 6-19 | 20-69 | 70+ | overall |\n|---|---|---|---|---|")
    for v, vn in (("inner_point", "1 kHz, edge, inner point"), ("hz8k", "1 kHz, edge, 8 kHz")):
        q = res["quick"][v]
        P(f"| {vn} | " + " | ".join(f"{f1(q[b][0])} / {f1(q[b][1])}; {q[b][2]:.0%}" for b in BANDS + ["all"]) + " |")
    P(f"\n## Round trip, encode(decode(n)) == n, over all 1000 codes\n\n{res['roundtrip_fail']} codes do not round-trip "
      f"(codes whose decoded audiogram is clipped at -10 or 100 dB); the level differs for {res['roundtrip_level_fail']}. "
      f"The reserved number 000 (100 dB at every frequency, no hearing) {'does' if res['roundtrip_000'] else 'does NOT'} round-trip.\n")
    sc, st = res["shape_counts"], res["shape_counts_train"]
    P("## Shape occupancy\n")
    P(f"Ears assigned to each shape (all {int(sc.sum())} ears): minimum {int(sc.min())} (shape {int(sc.argmin()):02d}), "
      f"median {int(np.median(sc))}, maximum {int(sc.max())}. Training half only: minimum {int(st.min())}.\n")
    P("## What the numbers signify\n")
    P("Better ear's code (higher = better hearing) for persons with both ears measured, by how they rate "
      "their own hearing (all persons, both halves; survey-weighted median and quartiles Q1 / median / Q3; "
      "n = persons; cells with n < 10 suppressed). Each code is shown as its block of 50; within a block the "
      "last digits identify the shape and do not rank hearing. The all-ages group is survey-weighted to the US population.\n")
    sig = res["signify"]
    cats = [("self-report", "Self-report (without aid)", SR_NAMES),
            ("ladder", "Functional ladder, 2017-20 (ages 6-19 and 70+ only)", [LADDER_NAMES[k] for k in range(6, 0, -1)])]
    for kind, title, names in cats:
        P(f"### {title}\n")
        P("| Category | " + " | ".join(f"{g}: Q1 / median / Q3 (n)" for g in sig[kind]) + " |\n|---|" + "---|" * len(sig[kind]))
        for i, nm in enumerate(names):
            cells = []
            for g in sig[kind]:
                n, v = sig[kind][g][i]
                cells.append("n<10" if v is None else f"{blk(v[0])} / {blk(v[1])} / {blk(v[2])} ({n})")
            P(f"| {nm} | " + " | ".join(cells) + " |")
        P("")
    if "design" in res: L += design_report(res["design"])
    if check_line: P(check_line)
    return "\n".join(L) + "\n"


def lloyd1d(x, wts, n, it=100):
    """1-D weighted Lloyd centres, started from weighted quantiles."""
    c = np.array([wpct(x, wts, (i + 0.5) * 100 / n) for i in range(n)])
    for _ in range(it):
        a = np.abs(x[:, None] - c[None]).argmin(1)
        c = np.array([(x[a == j] * wts[a == j]).sum() / wts[a == j].sum() if (a == j).any() else c[j] for j in range(n)])
    return np.sort(c)


def design_evidence(E, T, C, coefs, prev):
    """Evidence for the paper's claims (full build only): error breakdown, retest detail, real
    1 kHz repeat, ordering, alternative designs, self-test with input error, level counts."""
    cd = Coder(C); te = E.test.to_numpy(); tr = ~te; band = E.band.to_numpy(); w = E.w.to_numpy()
    wl = w * prevalence(E.age, prev); old = band == "70+"
    H = Hval(T); R = T - H[:, None]; N = cd.code(T); lvl = N // 50
    lv5 = cd.level(T); centre = (19 - lv5 + 0.5) * 5.0
    rms = lambda D: np.sqrt(((D - T) ** 2).mean(1))
    def st(e):          # loss-weighted and 70+ (median, 90th percentile), test group
        return {"loss": (wpct(e[te], wl[te], 50), wpct(e[te], wl[te], 90)),
                "70+": (wpct(e[te & old], w[te & old], 50), wpct(e[te & old], w[te & old], 90))}
    ev = {}
    # a. where the error comes from
    shp = cd.shape(T); ship = cd.decode(N)
    M = np.zeros((20, 7))
    for q in range(20):
        m = tr & (lv5 == q)
        if m.sum() and wl[m].sum() > 0: M[q] = (R[m] * wl[m, None]).sum(0) / wl[m].sum()
    lvonly = np.clip(centre[:, None] + M[lv5], LO, HI)
    ev["a"] = [("shipped (5 dB level, 50 shapes)", st(rms(ship))),
               ("exact level, nearest shape", st(rms(np.clip(H[:, None] + C[shp], LO, HI)))),
               ("5 dB level, exact shape (|level centre - H|)", st(np.abs(centre - H))),
               ("level only, plus the typical shape of that level", st(rms(lvonly))),
               ("worst single frequency, shipped", st(np.abs(ship - T).max(1))),
               ("worst single frequency, level only", st(np.abs(lvonly - T).max(1)))]
    # b. retest detail (same noise and seed as evaluate)
    rn = np.random.default_rng(SEED_NOISE)
    T2 = np.clip(np.round((T + rn.normal(0, 4, T.shape) + rn.normal(0, 2, (len(T), 1))) / 5) * 5, LO, HI)
    N2 = cd.code(T2); d = np.abs(N2 // 50 - lvl); rows = []
    for nm, m, ww in [(b, te & (band == b), w) for b in BANDS] + [("population", te, w), ("loss-weighted", te, wl)]:
        sh = lambda x: float(ww[m][x[m]].sum() / ww[m].sum())
        rows.append((nm, sh(d == 0), sh(d == 1), sh(d >= 2), sh(N2 % 50 == N % 50), sh(N2 == N)))
    ev["b"] = rows
    # c. real repeat of the 1 kHz reading (all ears: no training involved)
    a1 = E.t1000.to_numpy(); a2 = E.t1k2.to_numpy()
    ok = ~np.isnan(a2) & (a1 < HI) & (a2 < HI)
    dd = (a2 - a1)[ok]
    ev["c"] = (int(ok.sum()), float(dd.std(ddof=1)), float((np.abs(dd) >= 10).mean()))
    # d. ordering of random pairs of test ears (loss-weighted draw)
    rng = np.random.default_rng(5); idx = np.flatnonzero(te); p = wl[idx] / wl[idx].sum()
    pa = rng.choice(idx, 400000, p=p); pb = rng.choice(idx, 400000, p=p)
    def order_ok(code, higher_is_better):
        k = code[pa] != code[pb]; x, y = pa[k], pb[k]
        up = code[x] > code[y] if higher_is_better else code[x] < code[y]
        hi = np.where(up, x, y); lo = np.where(up, y, x)
        return (H[hi] < H[lo]) + 0.5 * (H[hi] == H[lo]), hi, lo
    ok_h, hi, lo = order_ok(N, True); gap = N[hi] - N[lo]; same = lvl[hi] == lvl[lo]
    rows = [("all pairs with different numbers", len(gap), float(ok_h.mean()), float(same.mean()))]
    for nm, a_, b_ in (("1-9", 1, 9), ("10-24", 10, 24), ("25-49", 25, 49), ("50 or more", 50, 999)):
        m = (gap >= a_) & (gap <= b_)
        rows.append((nm, int(m.sum()), float(ok_h[m].mean()), float(same[m].mean())))
    ev["d"] = rows
    # e. design comparisons (trained on the training half, loss weights)
    Xtr = R[tr]; wtr = wl[tr]
    def score(Dc):
        e = rms(Dc)
        return (wpct(e[te], wl[te], 50), wpct(e[te], wl[te], 90), float(wl[te][e[te] > 10].sum() / wl[te].sum()))
    def nearest(Ck): return ((R[:, None, :] - Ck[None]) ** 2).sum(2).argmin(1)
    designs = [("shipped, 50 shapes", 1000, score(ship))]
    for k in (10, 20, 100):
        best = None
        for sd in (7, 8, 9):
            Ck, inertia = wkmeans(Xtr, wtr.copy(), k, sd)
            if best is None or inertia < best[1]: best = (Ck, inertia)
        Ck = best[0]
        designs.append((f"{k} shapes (k-means)", 20 * k, score(np.clip(centre[:, None] + Ck[nearest(Ck)], LO, HI))))
    wn = wtr / wtr.sum(); mu = (Xtr * wn[:, None]).sum(0); Xc = Xtr - mu
    evl, V = np.linalg.eigh((Xc * wn[:, None]).T @ Xc); V = V[:, np.argsort(-evl)]
    P = Xc @ V[:, :2]
    g1 = lloyd1d(P[:, 0], wtr, 10); g2 = lloyd1d(P[:, 1], wtr, 5)
    Ck = mu + np.array([[x, y] for x in g1 for y in g2]) @ V[:, :2].T
    designs.append(("two-parameter formula: 10 x 5 lattice on two principal components", 1000,
                    score(np.clip(centre[:, None] + Ck[nearest(Ck)], LO, HI))))
    # LCH triad (Humes and Zapala 2024)
    dig = lambda x: np.clip(np.floor(x / 10), 0, 9).astype(int)
    def triad(Tx): return dig(Tx[:, [0, 1, 2]].mean(1)) * 100 + dig(Tx[:, [3, 4, 5]].mean(1)) * 10 + dig(Tx[:, 6])
    tc = triad(T); digs = np.column_stack([tc // 100, tc // 10 % 10, tc % 10])
    D_mid = (digs[:, [0, 0, 0, 1, 1, 1, 2]] * 10 + 5.0)
    D_best = D_mid.copy()
    for c in np.unique(tc[tr]):
        m = tr & (tc == c)
        if wl[m].sum() > 0: D_best[tc == c] = (T[m] * wl[m, None]).sum(0) / wl[m].sum()
    designs.append(("LCH triad, decoded to band midpoints", 1000, score(D_mid)))
    designs.append(("LCH triad, decoded to each triad's training mean audiogram", 1000, score(D_best)))
    ev["e"] = designs
    ok_t, _, _ = order_ok(tc, False)
    ident = lambda a, b: float(wl[te][(a == b)[te]].sum() / wl[te].sum())
    ev["e2"] = [("Ear Number", float(ok_h.mean()), ident(N2, N), len(np.unique(N))),
                ("LCH triad", float(ok_t.mean()), ident(triad(T2), tc), len(np.unique(tc)))]
    # f. self-test with input error
    rq = np.random.default_rng(11); n = len(T)
    n1 = rq.normal(0, 4, n); ne = rq.normal(0, 0.15, n); n3 = rq.normal(0, 4, n); off = rq.normal(0, 7, n)
    lo_e, hi_e = math.log2(1000.0), math.log2(EDGE_NONE_HZ)
    feats = quick_features(T); f = {}
    for cond, use_noise, use_off in (("error-free", False, False), ("test noise", True, False),
                                     ("test noise plus calibration offset", True, True)):
        f[cond] = {}
        for name, Z in feats.items():
            Zn = Z.copy()
            if use_noise:
                Zn[:, 0] += n1; Zn[:, 1] = np.clip(Zn[:, 1] + ne, lo_e, hi_e); Zn[:, 2] += n3
            if use_off: Zn[:, 0] += off; Zn[:, 2] += off
            Te = np.clip(quad(Zn) @ np.array(coefs[name]).T, LO, HI)
            Ne = cd.code(Te); e = rms(cd.decode(Ne)); one = np.abs(Ne // 50 - lvl) <= 1
            f[cond][name] = (wpct(e[te], w[te], 50), wpct(e[te], w[te], 90), float(w[te][one[te]].sum() / w[te].sum()))
    ev["f"] = f
    # g. level counts (all ears)
    ev["g"] = (np.bincount(lvl, minlength=20)[::-1].tolist(), [int((H >= x).sum()) for x in (50, 65, 80)])
    return ev


# ------------------------------------------------------------------ build
def build(nhanes, weighting):
    E = load_ears(nhanes); T = E[[f"t{f}" for f in FREQS]].to_numpy()
    band = E.band.to_numpy(); tr = ~E.test.to_numpy(); w = E.w.to_numpy()
    prev = prevalence_fit(E.age.to_numpy()[tr], loss_flag(T)[tr], w[tr])
    wb = band_norm(w, band, tr)
    wts = {"loss": w * prevalence(E.age, prev), "population": w, "equal": wb / 3.0,
           "70plus": np.where(band == "70+", wb, 0.0)}[weighting]
    wtrain = np.where(tr, wts, 0.0)
    C, inertia = train_shapes(T, wtrain)
    coefs = fit_quick(T[tr], wts[tr])
    table = {
        "name": "Ear Number", "version": "1", "licence": "CC BY 4.0",
        "source": "NCHS NHANES public-use files (audiometry AUX, demographics DEMO, hearing questionnaire AUQ), "
                  "cycles 2009-10, 2011-12, 2015-16 and 2017-March 2020 (pre-pandemic); https://www.cdc.gov/nchs/nhanes/",
        "attribution": "Nicholas Hill, Ear Number",
        "band_weights_hz": {str(f): w for f, w in BAND_WEIGHTS.items()},
        "band_weights_note": "ANSI S3.5 average-speech octave importance; the 250 Hz weight always applies to the 500 Hz value",
        "step_db": 5, "levels": 20, "shapes_per_level": 50, "clip_db": [LO, HI],
        "shape_freqs_hz": FREQS,
        "shape_order_rule": "ascending edge_hz of the residual curve (no edge = highest); ties and no-edge shapes by mean residual over 4, 6, 8 kHz descending",
        "shape_residuals_db": C.tolist(),
        "quick": {"features": "z = [t1k, log2(edge_hz capped 1000..16000), third]; design row = [1, z, z^2, z1z2, z1z3, z2z3]; one row of coefficients per target frequency",
                  "target_freqs_hz": FREQS,
                  "inner_point": {"third": "threshold at f3 = edge/2 if edge >= 4000 else sqrt(1000*edge), capped at 4000",
                                  "coef": np.round(coefs["inner_point"], 8).tolist()},
                  "hz8k": {"third": "threshold at 8 kHz", "coef": np.round(coefs["hz8k"], 8).tolist()}},
        "provenance": {"cycles": [c[0] for c in CYCLES], "ages": "6 and over (2009-10 audiometry started at 12)",
                       "exam_status": "AUAEXSTS 1 or 2", "unit": "ear, complete 7-frequency audiogram",
                       "weighting": weighting,
                       "survey_weights": "NHANES MEC weight x cycle years / total years of the cycles covering the person's age",
                       "coverage": COVERAGE, "cycle_years": YEARS,
                       "loss_prevalence": {"loss": "per ear, mean of 0.5, 1, 2, 4 kHz >= 20 dB HL (WHO)",
                                           "model": "logit p = b0 + b1 z + b2 z^2, z = (age - 45) / 25; "
                                                    "survey-weighted, training half",
                                           "coef": prev.tolist(),
                                           "used": weighting == "loss"},
                       "n_ears_trained_on": int((tr & (wts > 0)).sum()), "n_ears_total": int(len(E)),
                       "trained_on": "random half of persons in each band", "seed_split": SEED_SPLIT,
                       "seed_kmeans": SEED_KM, "restarts": RESTARTS, "min_effective_ears_per_shape": MIN_EFFECTIVE, "inertia": round(inertia, 4),
                       "built_by": "build/build_table.py",
                       "note": "Aggregate table only: no individual records are included."},
    }
    return E, T, C, coefs, prev, table


def max_diff(a, b, path=""):
    """Largest absolute numeric difference between two JSON structures; inf if the structure
    or any non-numeric value differs."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b): return float("inf"), f"keys differ at {path or '/'}"
        worst = (0.0, "")
        for k in a:
            worst = max(worst, max_diff(a[k], b[k], f"{path}/{k}"), key=lambda x: x[0])
        return worst
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): return float("inf"), f"length differs at {path}"
        worst = (0.0, "")
        for i, (x, y) in enumerate(zip(a, b)):
            worst = max(worst, max_diff(x, y, f"{path}[{i}]"), key=lambda x: x[0])
        return worst
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(a - b), path
    return (0.0, "") if a == b else (float("inf"), f"value differs at {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--weighting", choices=WEIGHTINGS, default="loss")
    ap.add_argument("--nhanes", default=os.path.join(HERE, "nhanes"))
    ap.add_argument("--out", default=os.path.join(ROOT, "earnumber-v1.json"))
    ap.add_argument("--results", default=os.path.join(HERE, "results.md"))
    ap.add_argument("--check", action="store_true", help="build afresh and compare with the JSON at --out; write nothing")
    a = ap.parse_args()
    if not os.path.exists(os.path.join(a.nhanes, "AUX_F.xpt")):
        sys.exit(f"NHANES files not found in {a.nhanes}; run python3 build/fetch_nhanes.py first")
    E, T, C, coefs, prev, table = build(a.nhanes, a.weighting)
    res = evaluate(E, T, C, coefs, prev)
    res["signify"] = signify(E, res["N"])
    if a.check:
        shipped = json.load(open(a.out))
        fresh = json.loads(json.dumps(table))     # same rounding/typing as a written file
        d, where = max_diff(fresh, shipped)
        print(f"maximum difference between a fresh build and {os.path.basename(a.out)}: {d:g}" + (f" ({where})" if d else ""))
        print(f"minimum ears assigned to any shape: {int(res['shape_counts'].min())}")
        sys.exit(0 if d == 0 else 1)
    with open(a.out, "w") as f:
        json.dump(table, f, indent=1); f.write("\n")
    res["design"] = design_evidence(E, T, C, coefs, prev)
    text = report(E, res, C, a.weighting, prev)
    with open(a.results, "w") as f: f.write(text)
    print(text)
    print(f"wrote {a.out} and {a.results}")


if __name__ == "__main__":
    main()
