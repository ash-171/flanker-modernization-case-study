#!/usr/bin/env python3
"""
Compare two characterization JSON documents produced by characterize.py.

Exit 0  -> identical (ignoring the informational "_env" block)
Exit 1  -> differences found; a structural diff is printed
"""

import json
import sys


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    doc.pop("_env", None)
    return doc


def walk(a, b, path, diffs):
    if type(a) is not type(b):
        diffs.append("%s: type %s != %s" % (path or ".", type(a).__name__, type(b).__name__))
        return
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                diffs.append("%s/%s: only in MODERN" % (path, k))
            elif k not in b:
                diffs.append("%s/%s: only in BASELINE" % (path, k))
            else:
                walk(a[k], b[k], "%s/%s" % (path, k), diffs)
    elif isinstance(a, list):
        if len(a) != len(b):
            diffs.append("%s: list length %d != %d" % (path, len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, "%s[%d]" % (path, i), diffs)
    else:
        if a != b:
            diffs.append("%s: %r != %r" % (path, a, b))


def main():
    if len(sys.argv) != 3:
        print("usage: compare.py BASELINE.json MODERN.json", file=sys.stderr)
        sys.exit(2)
    baseline = load(sys.argv[1])
    modern = load(sys.argv[2])
    diffs = []
    walk(baseline, modern, "", diffs)
    if not diffs:
        print("IDENTICAL - modernized flanker matches baseline on the full corpus")
        sys.exit(0)
    print("DIFFERENCES (%d):" % len(diffs))
    for d in diffs[:200]:
        print("  " + d)
    if len(diffs) > 200:
        print("  ... %d more" % (len(diffs) - 200))
    sys.exit(1)


if __name__ == "__main__":
    main()
