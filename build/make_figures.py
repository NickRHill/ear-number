#!/usr/bin/env python3
"""Draw the figures in figures/ (SVG, white background).

Usage: python3 build/make_figures.py
Needs matplotlib and numpy. codes-by-age.svg also needs the NHANES files (build/nhanes/, see
fetch_nhanes.py) and pandas; without them that one figure is skipped. Aggregates only.
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import earnumber as EN

OUT = os.path.join(ROOT, "figures")
BLUE, ORANGE, GREY, DARK = "#0072B2", "#D55E00", "#888888", "#222222"
plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
                     "font.size": 10, "axes.edgecolor": DARK, "axes.labelcolor": DARK, "text.color": DARK,
                     "xtick.color": DARK, "ytick.color": DARK, "svg.fonttype": "none",
                     "axes.spines.top": False, "axes.spines.right": False})
TABLE = EN.load()
FREQS = TABLE["shape_freqs_hz"]
XT = [250, 500, 1000, 2000, 4000, 8000]


def audio_axes(ax):
    ax.set_xscale("log", base=2)
    ax.set_xticks(XT); ax.set_xticklabels(["0.25", "0.5", "1", "2", "4", "8"])
    ax.minorticks_off()


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), format="svg", metadata={"Date": None})
    plt.close(fig)
    print("wrote figures/" + name)


def shapes():
    fig, axs = plt.subplots(5, 10, figsize=(14, 7.4), sharex=True, sharey=True)
    for i, ax in enumerate(axs.flat):
        r = TABLE["shape_residuals_db"][i]
        ax.axhline(0, color=GREY, lw=0.6)
        ax.plot(FREQS, r, color=BLUE, lw=1.5)
        ax.set_xscale("log", base=2); ax.set_xticks([500, 2000, 8000]); ax.set_xticklabels(["0.5", "2", "8"])
        ax.minorticks_off(); ax.set_ylim(60, -45)
        ax.set_title(f"{i:02d}", fontsize=9, pad=2, loc="left")
        ax.tick_params(labelsize=7, length=2)
    fig.supxlabel("Frequency (kHz)"); fig.supylabel("Residual from the mean threshold H (dB, down = worse)")
    fig.suptitle("The 50 shapes: audiogram minus H, ordered by cutoff (low index = treble loss starts at a low frequency)", y=0.995)
    fig.tight_layout()
    save(fig, "shapes.svg")


def levels():
    who = [("Normal", -10, 20), ("Mild", 20, 35), ("Moderate", 35, 50), ("Moderately\nsevere", 50, 65),
           ("Severe", 65, 80), ("Profound", 80, 95), ("Complete", 95, 110)]
    shade = ["#ffffff", "#f1f1f1"]
    fig, ax = plt.subplots(figsize=(8, 6))
    for k, (name, lo, hi) in enumerate(who):
        ax.axvspan(lo, hi, color=shade[k % 2], zorder=0)
        ax.text((lo + hi) / 2, 20.35, name, ha="center", va="bottom", fontsize=8)
    for q in range(20):
        hlo = 5 * (19 - q); hhi = hlo + 5
        lo = -10 if q == 19 else hlo; hi = 110 if q == 0 else hhi
        ax.barh(q, hi - lo, left=lo, height=0.72, color=BLUE, alpha=0.9, zorder=2)
        ax.text(hi + 1 if q else hlo - 1, q, f"{q * 50:03d}-{q * 50 + 49:03d}", va="center", fontsize=7.5,
                ha="left" if q else "right")
    ax.set_xlim(-10, 110); ax.set_ylim(-0.7, 20.2)
    ax.set_yticks(range(20)); ax.tick_params(axis="y", labelsize=8)
    ax.set_xlabel("Mean threshold H (dB HL, importance-weighted over 0.25-8 kHz)")
    ax.set_ylabel("Quality level q (code = 50 q + shape)")
    ax.set_title("Quality levels against H, with WHO hearing-loss grades (approximate)", pad=22)
    fig.text(0.01, 0.005, "WHO grades are defined on the better-ear average of 0.5, 1, 2 and 4 kHz; "
             "H weights the bands differently, so the alignment is approximate.", fontsize=7.5)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    save(fig, "levels.svg")


EXAMPLES = [
    ("Normal, young", {250: 5, 500: 5, 1000: 0, 2000: 0, 3000: 0, 4000: 5, 6000: 5, 8000: 10}),
    ("Mild, sloping", {250: 10, 500: 10, 1000: 15, 2000: 20, 3000: 30, 4000: 40, 6000: 45, 8000: 50}),
    ("Moderate, flat", {250: 45, 500: 45, 1000: 45, 2000: 50, 3000: 50, 4000: 50, 6000: 55, 8000: 55}),
    ("Severe, sloping", {250: 40, 500: 45, 1000: 55, 2000: 70, 3000: 80, 4000: 85, 6000: 90, 8000: 95}),
]


def examples():
    fig, axs = plt.subplots(1, 4, figsize=(14, 3.9), sharey=True)
    for ax, (title, aud) in zip(axs, EXAMPLES):
        n = EN.encode(aud); dec = EN.decode(n)
        fs = sorted(aud)
        ax.plot(fs, [aud[f] for f in fs], "o-", color=DARK, lw=1.4, ms=5, label="audiogram")
        ax.plot(list(dec), list(dec.values()), "s--", color=ORANGE, lw=1.4, ms=4, label="decoded")
        audio_axes(ax); ax.set_ylim(100, -10); ax.grid(alpha=0.25)
        ax.set_title(f"{title}\nEar Number {n:03d}", fontsize=10)
        ax.set_xlabel("Frequency (kHz)")
    axs[0].set_ylabel("Threshold (dB HL)"); axs[0].legend(loc="lower left", fontsize=8, frameon=False)
    fig.suptitle("Four invented audiograms and what their Ear Numbers decode to", y=1.0)
    fig.tight_layout()
    save(fig, "examples.svg")


def codes_by_age():
    try:
        import build_table as B
    except ImportError as ex:
        print("skipping codes-by-age.svg:", ex); return
    nh = os.path.join(HERE, "nhanes")
    if not os.path.exists(os.path.join(nh, "AUX_F.xpt")):
        print("skipping codes-by-age.svg: NHANES files not found in build/nhanes"); return
    E = B.load_ears(nh)
    T = E[[f"t{f}" for f in B.FREQS]].to_numpy()
    N = B.Coder(TABLE["shape_residuals_db"]).code(T)
    groups = [(6, 11), (12, 19), (20, 29), (30, 39), (40, 49), (50, 59), (60, 69), (70, 79), (80, 150)]
    labels = ["6-11", "12-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
    pct = {q: [] for q in (5, 25, 50, 75, 95)}; keep = []
    for i, (lo, hi) in enumerate(groups):
        m = ((E.age >= lo) & (E.age <= hi)).to_numpy()
        if m.sum() < 100: continue
        keep.append(labels[i])
        for q in pct: pct[q].append(B.wpct(N[m], E.w.to_numpy()[m], q))
    x = np.arange(len(keep))
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.fill_between(x, pct[5], pct[95], color=BLUE, alpha=0.18, label="5th-95th percentile")
    ax.fill_between(x, pct[25], pct[75], color=BLUE, alpha=0.40, label="25th-75th percentile")
    ax.plot(x, pct[50], "o-", color=BLUE, lw=2, label="median")
    ax.set_xticks(x); ax.set_xticklabels(keep); ax.set_ylim(0, 1000)
    ax.set_xlabel("Age (years)"); ax.set_ylabel("Ear Number (per ear)")
    ax.set_title("Ear Numbers by age, US population (NHANES 2009-2020, survey-weighted)")
    ax.grid(axis="y", alpha=0.25); ax.legend(loc="lower left", frameon=False)
    fig.text(0.01, 0.005, "NHANES audiometry covers 6-11 only in 2017-20 and 12-19 and 70+ in 2009-10; aggregates only.", fontsize=7.5)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    save(fig, "codes-by-age.svg")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    shapes(); levels(); examples(); codes_by_age()
