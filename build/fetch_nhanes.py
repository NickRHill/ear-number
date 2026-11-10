#!/usr/bin/env python3
"""Download the NHANES public-use audiometry, demographics and hearing-questionnaire files
used to build the Ear Number table into build/nhanes/, and verify them against
build/nhanes-sha256.txt. Files already present are not downloaded again.

Usage: python3 build/fetch_nhanes.py [--dest DIR]
Standard library only. Data: National Center for Health Statistics (NCHS), NHANES.
"""
import argparse
import hashlib
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{name}.xpt"
# cycle -> (first year of the cycle's directory, file names)
FILES = {
    "2009-10": ("2009", ["AUX_F", "DEMO_F", "AUQ_F"]),
    "2011-12": ("2011", ["AUX_G", "DEMO_G", "AUQ_G"]),
    "2015-16": ("2015", ["AUX_I", "DEMO_I", "AUQ_I"]),
    "2017-March 2020": ("2017", ["P_AUX", "P_DEMO", "P_AUQ"]),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def expected(path):
    out = {}
    with open(path) as f:
        for line in f:
            if line.strip():
                digest, name = line.split()
                out[name] = digest
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dest", default=os.path.join(HERE, "nhanes"))
    a = ap.parse_args()
    os.makedirs(a.dest, exist_ok=True)
    want = expected(os.path.join(HERE, "nhanes-sha256.txt"))
    bad = 0
    for cycle, (year, names) in FILES.items():
        for name in names:
            fn = name + ".xpt"
            path = os.path.join(a.dest, fn)
            if os.path.exists(path):
                state = "present"
            else:
                url = BASE.format(year=year, name=name)
                print(f"downloading {url}")
                tmp = path + ".part"
                with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                os.replace(tmp, path)
                state = "downloaded"
            ok = sha256(path) == want.get(fn)
            bad += not ok
            print(f"{cycle:16s} {fn:12s} {state:10s} checksum {'ok' if ok else 'MISMATCH'}")
    if bad:
        sys.exit(f"{bad} file(s) differ from build/nhanes-sha256.txt "
                 "(NCHS may have revised a file; the table was built from the listed versions)")


if __name__ == "__main__":
    main()
