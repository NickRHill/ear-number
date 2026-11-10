"""Tests for earnumber.py (synthetic audiograms only).
Run from the package folder: python3 -m unittest discover -s tests"""
import math
import os
import random
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
import earnumber as EN

ALL = (250, 500, 1000, 2000, 3000, 4000, 6000, 8000)
REQ = (500, 1000, 2000, 4000, 8000)


def flat(x, freqs=ALL):
    return {f: x for f in freqs}


def clipped(n):
    return any(v in (EN.CLIP_LO, EN.CLIP_HI) for v in EN.decode(n).values())


def synthetic(rng):
    base, slope = rng.uniform(-5, 80), rng.uniform(-5, 40)
    return {f: base + slope * max(0.0, math.log2(f / 1000)) / 3 + rng.gauss(0, 4) for f in REQ}


class RoundTrip(unittest.TestCase):
    def test_unclipped_codes_round_trip(self):
        bad = [n for n in range(1000) if not clipped(n) and EN.encode(EN.decode(n)) != n]
        self.assertEqual(bad, [])

    def test_failures_are_clipped_codes(self):
        fail = [n for n in range(1000) if EN.encode(EN.decode(n)) != n]
        self.assertTrue(all(clipped(n) for n in fail))

    def test_level_and_shape_split(self):
        for n in range(1000):
            self.assertEqual(EN.quality_level(n) * 50 + EN.shape_index(n), n)


class Bounds(unittest.TestCase):
    def test_range_and_type(self):
        rng = random.Random(3)
        for _ in range(500):
            t = {f: rng.uniform(-15, 120) for f in REQ}
            n = EN.encode(t)
            self.assertIsInstance(n, int)
            self.assertTrue(0 <= n <= 999)

    def test_extremes_and_boundaries(self):
        self.assertEqual(EN.quality_level(EN.encode(flat(-10))), 19)
        self.assertEqual(EN.quality_level(EN.encode(flat(120))), 0)
        self.assertEqual(EN.quality_level(EN.encode(flat(20))), 15)   # H = 20 starts level 15
        self.assertEqual(EN.quality_level(EN.encode(flat(19))), 16)

    def test_decode_output(self):
        for n in range(1000):
            d = EN.decode(n)
            self.assertEqual(sorted(d), [250, 500, 1000, 2000, 3000, 4000, 6000, 8000])
            self.assertTrue(all(EN.CLIP_LO <= v <= EN.CLIP_HI for v in d.values()))
            self.assertEqual(d[250], d[500])

    def test_invalid_numbers(self):
        for bad in (-1, 1000, 1.5, True):
            with self.assertRaises(ValueError):
                EN.decode(bad)

    def test_missing_required_frequency(self):
        with self.assertRaises(ValueError):
            EN.encode({500: 10, 1000: 10, 2000: 10, 4000: 10})

    def test_string_keys_and_optional_points(self):
        t = {500: 10, 1000: 10, 2000: 20, 4000: 40, 8000: 60}
        self.assertEqual(EN.encode(t), EN.encode({str(k): v for k, v in t.items()}))

    def test_supplied_250_hz_is_ignored(self):
        t = {500: 20, 1000: 20, 2000: 25, 4000: 30, 8000: 35}
        for v in (-10, 0, 80, 100):
            self.assertEqual(EN.encode(t), EN.encode({**t, 250: v}))
        self.assertEqual(EN.complete({**t, 250: 80})[250], 20)


class Monotonic(unittest.TestCase):
    def test_worse_hearing_never_raises_the_level(self):
        rng = random.Random(5)
        for _ in range(300):
            t = synthetic(rng)
            worse = {f: v + rng.uniform(0, 15) for f, v in t.items()}
            self.assertLessEqual(EN.quality_level(EN.encode(worse)), EN.quality_level(EN.encode(t)))

    def test_flat_levels_step_down_every_5_db(self):
        levels = [EN.quality_level(EN.encode(flat(x))) for x in range(-10, 101, 5)]
        self.assertEqual(levels, sorted(levels, reverse=True))
        self.assertEqual(levels[0], 19)
        self.assertEqual(levels[-1], 0)

    def test_shape_order_follows_cutoff(self):
        # a loss that starts at low frequency has a lower shape index than one that starts high
        low = EN.shape_index(EN.encode({500: 10, 1000: 10, 2000: 40, 4000: 70, 8000: 80}))
        high = EN.shape_index(EN.encode({500: 10, 1000: 10, 2000: 10, 4000: 10, 8000: 40}))
        self.assertLess(low, high)


class Pairs(unittest.TestCase):
    def test_zero_padding(self):
        self.assertEqual(EN.format_pair(0, 7, check=False), "000 007")
        self.assertEqual(EN.format_pair(742, 49, check=False), "742 049")
        self.assertEqual(EN.format_pair(999, 100, check=False), "999 100")
        self.assertEqual(EN.format_pair(0, 7), f"000 007 {EN.check_digit(0, 7)}")

    def test_pair_from_audiograms(self):
        left, right = flat(10), flat(60)
        l, r = EN.encode(left), EN.encode(right)
        self.assertEqual(EN.encode_pair(left, right), f"{l:03d} {r:03d} {EN.check_digit(l, r)}")
        self.assertEqual(EN.encode_pair(left, right, check=False), f"{l:03d} {r:03d}")
        self.assertGreater(EN.encode(left), EN.encode(right))

    def test_pair_rejects_bad_numbers(self):
        with self.assertRaises(ValueError):
            EN.format_pair(1000, 1)


class NoHearing(unittest.TestCase):
    def test_no_response_ear_is_000(self):
        self.assertEqual(EN.encode(flat(100)), 0)
        self.assertEqual(EN.encode(flat(120, REQ)), 0)
        self.assertEqual(set(EN.decode(0).values()), {EN.CLIP_HI})
        self.assertEqual(EN.encode(EN.decode(0)), 0)

    def test_000_only_for_no_hearing(self):
        rng = random.Random(5)
        for _ in range(3000):
            t = {f: rng.uniform(85, 100) for f in REQ}
            if not all(v >= 100 for v in EN.complete(t).values()):
                self.assertNotEqual(EN.encode(t), 0)


class CheckDigit(unittest.TestCase):
    def digits(self, s):
        return int(s[:3]), int(s[3:6])

    def test_damm_property(self):
        rng = random.Random(7)
        for _ in range(2000):
            l, r = rng.randrange(1000), rng.randrange(1000)
            i = 0
            for ch in f"{l:03d}{r:03d}{EN.check_digit(l, r)}":
                i = int(EN._DAMM[i][int(ch)])
            self.assertEqual(i, 0)

    def test_catches_single_digit_errors_and_adjacent_swaps(self):
        rng = random.Random(8)
        for _ in range(3000):
            s = f"{rng.randrange(10 ** 6):06d}"
            c = EN.check_digit(*self.digits(s))
            p = rng.randrange(6)
            wrong = s[:p] + str((int(s[p]) + rng.randrange(1, 10)) % 10) + s[p + 1:]
            self.assertNotEqual(EN.check_digit(*self.digits(wrong)), c)
            p = rng.randrange(5)
            if s[p] != s[p + 1]:
                swapped = s[:p] + s[p + 1] + s[p] + s[p + 2:]
                self.assertNotEqual(EN.check_digit(*self.digits(swapped)), c)


class Parse(unittest.TestCase):
    def test_formats(self):
        c = EN.check_digit(742, 688)
        for text in ("742 688", "742688", "742,688", f"742 688 {c}", f"742688{c}", f"742,688,{c}",
                     f" 742-688-{c} "):
            p = EN.parse_pair(text)
            self.assertEqual((p["left"], p["right"]), (742, 688))
            self.assertEqual(p["check"], c if text.strip().endswith(str(c)) and len(
                [ch for ch in text if ch.isdigit()]) == 7 else None)

    def test_suffixes(self):
        c = EN.check_digit(456, 456)
        p = EN.parse_pair(f"456e 456N {c}")
        self.assertEqual((p["left_suffix"], p["right_suffix"]), ("E", "N"))
        self.assertEqual(EN.parse_pair(f"456E456N{c}")["right"], 456)
        self.assertEqual(EN.format_pair(456, 456, True, "E", "N"), f"456E 456N {c}")
        self.assertEqual(EN.check_digit(456, 456), c)          # suffixes are not in the check

    def test_rejections(self):
        c = EN.check_digit(742, 688)
        for text in (f"742 688 {(c + 1) % 10}", "742 68", "742 6881 2", "742O 688", "742B 688",
                     "abc def", ""):
            with self.assertRaises(ValueError, msg=text):
                EN.parse_pair(text)
        with self.assertRaises(ValueError):
            EN.format_pair(1, 2, True, "S")


class Quick(unittest.TestCase):
    def test_estimate_shape_and_range(self):
        for third in (40, (EN.inner_point_hz(3000), 40)):
            est = EN.estimate_from_quick(10, 3000, third)
            self.assertEqual(sorted(est), [250, 500, 1000, 2000, 3000, 4000, 6000, 8000])
            self.assertTrue(all(EN.CLIP_LO <= v <= EN.CLIP_HI for v in est.values()))

    def test_flat_normal_hearing_is_estimated_as_good(self):
        est = EN.estimate_from_quick(5, None, 5)
        self.assertLess(max(est.values()), 20)
        self.assertGreaterEqual(EN.quality_level(EN.encode(est)), 16)

    def test_worse_quick_test_gives_worse_estimate(self):
        a = EN.encode(EN.estimate_from_quick(5, 6000, 10))
        b = EN.encode(EN.estimate_from_quick(40, 1500, 70))
        self.assertGreater(a // 50, b // 50)

    def test_inner_point_check(self):
        self.assertAlmostEqual(EN.inner_point_hz(None), 4000.0)
        self.assertAlmostEqual(EN.inner_point_hz(2000), math.sqrt(1000 * 2000))
        with self.assertRaises(ValueError):
            EN.estimate_from_quick(10, 3000, (500, 30))


class CommandLine(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, os.path.join(ROOT, "earnumber.py"), *args],
                              capture_output=True, text=True)

    def test_encode(self):
        r = self.run_cli("encode", "500=10", "1000=15", "2000=25", "4000=45", "8000=60")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), f"{EN.encode({500: 10, 1000: 15, 2000: 25, 4000: 45, 8000: 60}):03d}")

    def test_decode(self):
        r = self.run_cli("decode", "742")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("8000 Hz", r.stdout)
        self.assertIn("level 14", r.stdout)

    def test_check(self):
        c = EN.check_digit(742, 688)
        r = self.run_cli("check", "742", "688")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), f"742 688 {c}")
        self.assertIn("correct", self.run_cli("check", f"742688{c}").stdout)
        self.assertNotEqual(self.run_cli("check", f"742 688 {(c + 1) % 10}").returncode, 0)

    def test_errors_exit_nonzero(self):
        self.assertNotEqual(self.run_cli("decode", "1000").returncode, 0)
        self.assertNotEqual(self.run_cli("encode", "500=5").returncode, 0)
        self.assertNotEqual(self.run_cli("encode", "banana").returncode, 0)


if __name__ == "__main__":
    unittest.main()
