"""The generated web pages must match their sources (web-src/), and every language file must
have exactly the English keys. Run: python3 -m unittest discover -s tests"""
import os
import subprocess
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


class WebPages(unittest.TestCase):
    def test_pages_are_up_to_date(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "build", "build_web.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
