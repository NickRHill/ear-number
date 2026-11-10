"""Ear Number: a 3-digit number 000-999 per ear (higher = better hearing) that decodes to an
approximate audiogram. Python standard library only.

N = q * 50 + s.
  q = quality level 0-19 = 19 - clip(floor(H / 5), 0, 19), H = importance-weighted mean
      threshold (dB HL, ANSI S3.5 average-speech octave weights; 250 Hz weight always applies to
      the 500 Hz value; a supplied 250 Hz is ignored). Each level is 5 dB.
  s = shape 0-49: nearest (squared distance) of 50 learnt residual curves, residual =
      audiogram minus H at 0.5, 1, 2, 3, 4, 6, 8 kHz. Shapes are numbered so that a higher
      index means a higher cutoff, then less treble loss.
Decode = level centre ((19 - q + 0.5) * 5 dB) + shape residual, clipped to -10..100 dB HL.
000 is reserved for no hearing or no ear on that side (every threshold at 100 dB HL).
Within a level (a block of 50 numbers) the shape index describes; it does not rank.
The table is earnumber-v1.json (CC BY 4.0), built by build/build_table.py.

A person is written 'LLL RRR C': left ear, right ear, Damm check digit (optional but
encouraged), with optional suffix letters after an ear (E = self-test estimate, N = not
measured, value assumed), e.g. '456E 456N 1'.

Command line:
  python3 earnumber.py encode 500=10 1000=15 2000=25 4000=45 8000=60
  python3 earnumber.py decode 705
  python3 earnumber.py check 705 688
"""
import hashlib
import json
import math
import os
import re

NO_HEARING = 0                 # reserved: no hearing or no ear on that side; decodes to 100 dB HL
# Suffix letters: upper case, avoiding letters that look like digits (I L O Q D Z S G T B) and U.
# Defined in version 1: E = estimated by a self-test (uncalibrated device); N = not measured on
# this ear, value assumed (copied from the other ear, or a system default). Others are reserved.
SUFFIX_LETTERS = "ACEFHJKMNPRVWXY"
SUFFIXES = {"E": "estimated by a self-test on an uncalibrated device",
            "N": "not measured on this ear; value assumed (copied from the other ear, or a default)"}
_DAMM = ("0317598642", "7092154863", "4206871359", "1750983426", "6123045978",
         "3674209581", "5869720134", "8945362017", "9438617205", "2581436790")

BAND_WEIGHTS = {250: 0.0617, 500: 0.1671, 1000: 0.2373, 2000: 0.2648, 4000: 0.2142, 8000: 0.0549}
CLIP_LO, CLIP_HI = -10.0, 100.0
EDGE_NONE_HZ = 16000.0
SHAPE_FREQS = (500, 1000, 2000, 3000, 4000, 6000, 8000)
DECODE_FREQS = (250, 500, 1000, 2000, 3000, 4000, 6000, 8000)
_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "earnumber-v1.json")
_T = None
# SHA-256 of the shipped earnumber-v1.json; ports should check the same value.
V1_SHA256 = "479155629f5a377a2de0dbc82d1ad83908692ce78cf505ef75e1ec9687f6c97d"


def table_sha256(path=None):
    """SHA-256 (hex) of the bytes of a table file (default: earnumber-v1.json beside this module)."""
    with open(path or _PATH, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load(path=None):
    """(Re)load a table; called lazily on first use. path: JSON file (default: earnumber-v1.json
    beside this module, which must be byte-identical to the published version 1 table; a table
    given by explicit path is validated but not hash-checked). Returns the table dict.
    Raises ValueError if the table is not acceptable."""
    global _T
    if path is None and table_sha256() != V1_SHA256:
        raise ValueError("the table is not the published version 1 table (SHA-256 mismatch)")
    with open(path or _PATH) as f:
        t = json.load(f)
    if str(t.get("version")) != "1":
        raise ValueError(f"table version must be '1'; got {t.get('version')!r}")
    if {int(k): v for k, v in t["band_weights_hz"].items()} != BAND_WEIGHTS:
        raise ValueError("table band weights do not match BAND_WEIGHTS")
    if tuple(t["shape_freqs_hz"]) != SHAPE_FREQS:
        raise ValueError("table shape_freqs_hz does not match SHAPE_FREQS")
    shapes = t["shape_residuals_db"]
    if len(shapes) != 50 or any(len(c) != 7 for c in shapes):
        raise ValueError("table must hold exactly 50 shapes of 7 numbers each")
    _T = t
    return t


def _table():
    return _T if _T is not None else load()


def _clip(x):
    return min(max(float(x), CLIP_LO), CLIP_HI)


def _interp_log(f, f0, t0, f1, t1):
    return t0 + (t1 - t0) * math.log(f / f0) / math.log(f1 / f0)


def complete(thresholds):
    """Clip to -10..100 and fill gaps: 3000 and 6000 by log-frequency interpolation,
    250 is always set to the 500 Hz value (a supplied 250 Hz is ignored).
    Keys may be int or str."""
    t = {int(k): _clip(v) for k, v in thresholds.items()}
    for f in (500, 1000, 2000, 4000, 8000):
        if f not in t:
            raise ValueError(f"threshold at {f} Hz is required")
    if 3000 not in t:
        t[3000] = _interp_log(3000, 2000, t[2000], 4000, t[4000])
    if 6000 not in t:
        t[6000] = _interp_log(6000, 4000, t[4000], 8000, t[8000])
    t[250] = t[500]
    return t


def mean_threshold(t):
    """H in dB HL; t as returned by complete()."""
    h = sum(BAND_WEIGHTS[f] * t[f] for f in (250, 500, 1000, 2000, 4000, 8000))
    return round(h, 6)       # rounding keeps a flat 20 dB audiogram on the 20 dB boundary


def _level(h):
    return 19 - min(max(math.floor(h / 5), 0), 19)


def encode(thresholds):
    """Ear Number (int 0-999) for one ear.

    thresholds: {Hz: dB HL}; 500, 1000, 2000, 4000 and 8000 are required; 3000 and 6000 are
    optional (interpolated on a log-frequency axis); a 250 Hz value is accepted and ignored (the
    250 Hz band weight applies to the 500 Hz value). Values are clipped to -10..100 dB HL. Higher number = better hearing."""
    tb = _table()
    t = complete(thresholds)
    if all(v >= CLIP_HI for v in t.values()):
        return NO_HEARING
    h = mean_threshold(t)
    level = _level(h)
    res = [t[f] - h for f in SHAPE_FREQS]
    best, bd = None, None
    for i, c in enumerate(tb["shape_residuals_db"]):
        if level == 0 and i == 0:
            continue                      # 000 is reserved for no hearing
        d = sum((r - x) ** 2 for r, x in zip(res, c))
        if bd is None or d < bd:
            best, bd = i, d
    return level * 50 + best


def _check(n):
    if isinstance(n, bool) or int(n) != n or not 0 <= n <= 999:
        raise ValueError("Ear Number must be an integer 0-999")
    return int(n)


def quality_level(n):
    """Level 0-19 (higher = better hearing; each level is 5 dB of mean threshold)."""
    return _check(n) // 50


def shape_index(n):
    return _check(n) % 50


def decode(n):
    """Approximate audiogram {Hz: dB HL} at 250, 500, 1000, 2000, 3000, 4000, 6000, 8000.
    250 Hz equals the 500 Hz value (the training data has no 250 Hz)."""
    n = _check(n)
    if n == NO_HEARING:
        return {f: CLIP_HI for f in DECODE_FREQS}
    centre = (19 - n // 50 + 0.5) * 5
    shape = _table()["shape_residuals_db"][n % 50]
    out = {f: _clip(centre + r) for f, r in zip(SHAPE_FREQS, shape)}
    out[250] = out[500]
    return {f: out[f] for f in DECODE_FREQS}


def check_digit(n_left, n_right):
    """Damm check digit (0-9) over the six digits LLLRRR. It catches every single wrong digit
    and every swap of two adjacent digits. Suffixes are not included."""
    i = 0
    for ch in f"{_check(n_left):03d}{_check(n_right):03d}":
        i = int(_DAMM[i][int(ch)])
    return i


def _suffix(s):
    s = (s or "").upper()
    bad = [c for c in s if c not in SUFFIX_LETTERS]
    if bad:
        raise ValueError(f"suffix letters must be from {SUFFIX_LETTERS}; got {''.join(bad)!r}")
    return s


def format_pair(n_left, n_right, check=True, suffix_left="", suffix_right=""):
    """'LLL RRR C' (check digit included by default, as encouraged), each ear zero padded to
    3 digits and followed by its suffix letters if any, e.g. '456E 456N 1'."""
    s = f"{_check(n_left):03d}{_suffix(suffix_left)} {_check(n_right):03d}{_suffix(suffix_right)}"
    return f"{s} {check_digit(n_left, n_right)}" if check else s


def encode_pair(left, right, check=True):
    """'LLL RRR C' from two threshold dicts."""
    return format_pair(encode(left), encode(right), check)


def parse_pair(text):
    """Read a written pair: 'LLL RRR', 'LLL RRR C', with or without spaces, commas or hyphens
    ('7056884', '705,688,4'), and suffix letters after either ear ('456E 456N 1').
    Six digits mean no check digit; seven mean the last is the check digit, which must match.
    Returns {'left', 'right', 'left_suffix', 'right_suffix', 'check'} (check is None when
    absent). Raises ValueError on anything else, including a wrong check digit."""
    s = re.sub(r"[\s,;\-]", "", str(text)).upper()
    m = re.fullmatch(r"(\d{3})([A-Z]*)(\d{3})([A-Z]*)(\d?)", s)
    if not m:
        raise ValueError(f"not an Ear Number pair: {text!r}")
    left, ls, right, rs, c = int(m[1]), _suffix(m[2]), int(m[3]), _suffix(m[4]), m[5]
    if c and int(c) != check_digit(left, right):
        raise ValueError(f"check digit does not match: {text!r} (re-enter the number)")
    return {"left": left, "right": right, "left_suffix": ls, "right_suffix": rs,
            "check": int(c) if c else None}


def _edge(edge):
    if edge is None or edge == float("inf"):
        return EDGE_NONE_HZ
    return min(max(float(edge), 1000.0), EDGE_NONE_HZ)


def inner_point_hz(edge):
    """Frequency of the quick test's inner point: edge/2 if edge >= 4 kHz else
    sqrt(1000*edge), capped at 4 kHz."""
    e = _edge(edge)
    return min(e / 2 if e >= 4000 else math.sqrt(1000 * e), 4000.0)


def estimate_from_quick(t1k, edge_hz, third):
    """Estimate an audiogram {Hz: dB HL} (250..8000) from quick-test values already in dB HL.
    t1k: 1 kHz threshold. edge_hz: frequency where the threshold first rises 20 dB above
    the 1 kHz one (None or inf = no edge). third: (f3, t3), the threshold at the inner
    point (f3 must be within 10% of inner_point_hz(edge_hz)), or a plain number = the
    8 kHz threshold."""
    q = _table()["quick"]
    e = _edge(edge_hz)
    if isinstance(third, (tuple, list)):
        f3, t3 = third
        if abs(f3 / inner_point_hz(e) - 1) > 0.1:
            raise ValueError("f3 does not match the inner point for this edge")
        coef, z3 = q["inner_point"]["coef"], float(t3)
    else:
        coef, z3 = q["hz8k"]["coef"], float(third)
    z = [float(t1k), math.log2(e), z3]
    x = [1.0] + z + [v * v for v in z] + [z[0] * z[1], z[0] * z[2], z[1] * z[2]]
    est = {f: _clip(sum(c * v for c, v in zip(row, x))) for f, row in zip(q["target_freqs_hz"], coef)}
    est[250] = est[500]
    return {f: est[f] for f in DECODE_FREQS}


def _parse_thresholds(items):
    out = {}
    for item in items:
        try:
            f, v = item.split("=")
            out[int(f)] = float(v)
        except ValueError:
            raise SystemExit(f"bad threshold {item!r}; use HZ=DB, e.g. 1000=15")
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="earnumber.py", description="Ear Number encoder/decoder")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("encode", help="thresholds (HZ=DB ...) to a 3-digit number")
    e.add_argument("thresholds", nargs="+", metavar="HZ=DB")
    d = sub.add_parser("decode", help="number to an approximate audiogram")
    d.add_argument("number", type=int)
    c = sub.add_parser("check", help="add or verify the check digit of a pair, e.g. '705 688'")
    c.add_argument("pair", nargs="+")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "check":
            p = parse_pair(" ".join(a.pair))
            out = format_pair(p["left"], p["right"], True, p["left_suffix"], p["right_suffix"])
            print(out if p["check"] is None else f"{out}  (check digit correct)")
            return
        if a.cmd == "encode":
            print(f"{encode(_parse_thresholds(a.thresholds)):03d}")
        else:
            n = _check(a.number)
            print(f"Ear Number {n:03d}: level {quality_level(n)}, shape {shape_index(n)}")
            for f, v in decode(n).items():
                print(f"{f:5d} Hz  {v:6.1f} dB HL")
    except ValueError as ex:
        raise SystemExit(f"error: {ex}")


if __name__ == "__main__":
    main()
