"""The web page's copy of the table must be byte-identical to the published one."""
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


class WebTableCopy(unittest.TestCase):
    def test_web_copy_is_identical(self):
        with open(os.path.join(ROOT, "earnumber-v1.json"), "rb") as a, \
                open(os.path.join(ROOT, "web", "earnumber-v1.json"), "rb") as b:
            self.assertEqual(a.read(), b.read(), "copy earnumber-v1.json to web/ again")


if __name__ == "__main__":
    unittest.main()
