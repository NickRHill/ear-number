"""Checks that the reference implementation reproduces earnumber-v1-vectors.json and that the
default table is the published version 1 table. Run: python3 -m unittest discover -s tests"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
import earnumber as EN

with open(os.path.join(ROOT, "earnumber-v1-vectors.json")) as _f:
    V = json.load(_f)


class Vectors(unittest.TestCase):
    def test_decode(self):
        self.assertEqual(len(V["decode"]), 1000)
        for key, expect in V["decode"].items():
            got = [EN.decode(int(key))[f] for f in EN.DECODE_FREQS]
            for g, e in zip(got, expect):
                self.assertAlmostEqual(g, e, delta=0.05, msg=key)

    def test_encode(self):
        self.assertGreaterEqual(len(V["encode"]), 250)
        for r in V["encode"]:
            n = EN.encode(r["thresholds"])
            self.assertEqual(n, r["number"], r["note"])
            self.assertEqual((n // 50, n % 50), (r["level"], r["shape"]), r["note"])

    def test_pairs(self):
        for r in V["pairs"]:
            self.assertEqual(EN.check_digit(r["left"], r["right"]), r["check_digit"])
            self.assertEqual(EN.format_pair(r["left"], r["right"], True, r["left_suffix"],
                                            r["right_suffix"]), r["formatted"])

    def test_parse(self):
        for r in V["parse"]:
            self.assertEqual(EN.parse_pair(r["text"]), r["expect"], r["text"])

    def test_reject(self):
        for text in V["reject"]:
            with self.assertRaises(ValueError, msg=repr(text)):
                EN.parse_pair(text)


class TableIdentity(unittest.TestCase):
    def test_hash_matches(self):
        self.assertEqual(EN.table_sha256(), EN.V1_SHA256)
        self.assertEqual(V["table_sha256"], EN.V1_SHA256)
        self.assertEqual(V["version"], "1")

    def test_modified_default_table_is_refused(self):
        saved_path, saved_table = EN._PATH, EN._T
        with tempfile.TemporaryDirectory() as d:
            copy = os.path.join(d, "earnumber-v1.json")
            shutil.copy(saved_path, copy)
            with open(copy, "a") as f:
                f.write("\n")                      # one byte changed
            EN._PATH = copy                        # the default-path mechanism, pointed at the copy
            try:
                with self.assertRaisesRegex(ValueError, "not the published version 1 table"):
                    EN.load()
                self.assertIs(EN._T, saved_table)  # a refused load leaves the loaded table alone
                EN.load(copy)                      # an explicit path is not hash-checked
            finally:
                EN._PATH = saved_path
                EN._T = saved_table

    def test_bad_tables_raise_value_error(self):
        with open(EN._PATH) as f:
            good = json.load(f)
        saved = EN._T
        cases = {"version": lambda t: t.update(version="2"),
                 "weights": lambda t: t["band_weights_hz"].update({"500": 0.5}),
                 "freqs": lambda t: t.update(shape_freqs_hz=[500, 1000]),
                 "count": lambda t: t["shape_residuals_db"].pop(),
                 "width": lambda t: t["shape_residuals_db"][3].pop()}
        try:
            with tempfile.TemporaryDirectory() as d:
                for name, mutate in cases.items():
                    t = json.loads(json.dumps(good))
                    mutate(t)
                    p = os.path.join(d, name + ".json")
                    with open(p, "w") as f:
                        json.dump(t, f)
                    with self.assertRaises(ValueError, msg=name):
                        EN.load(p)
        finally:
            EN._T = saved


if __name__ == "__main__":
    unittest.main()
