#!/usr/bin/env python3
"""Check that every PDF in papers/ is named so the site will actually link it.

The site reveals a paper's link only when papers/<slug>.pdf exists, so a
misspelled filename fails silently: the file uploads fine and no link ever
appears. This turns that into a loud failure with the correct name.

Run it yourself with `python3 tools/check_papers.py`; CI runs it on every push.
"""

import json
import os
import sys
import difflib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    config = json.load(open(os.path.join(ROOT, "tools/papers.json"), encoding="utf-8"))
    expected = {p["slug"] + ".pdf": p for p in config["papers"]}
    problems = []

    papers_dir = os.path.join(ROOT, "papers")
    present = sorted(f for f in os.listdir(papers_dir) if f.lower().endswith(".pdf"))

    for name in present:
        if name in expected:
            continue
        close = difflib.get_close_matches(name, expected, n=1, cutoff=0.6)
        if close:
            problems.append(
                "papers/%s will not be linked.\n"
                "    Rename it to:  %s\n"
                "    (that is the filename tools/papers.json gives this paper)"
                % (name, close[0]))
        else:
            problems.append(
                "papers/%s does not match any paper in tools/papers.json.\n"
                "    Either rename it to one of the expected filenames, or add an\n"
                "    entry for it in tools/papers.json and rerun tools/unbundle.py."
                % name)

    cv_path = os.path.join(ROOT, config["cv"])
    cv_dir = os.path.dirname(cv_path)
    stray = [f for f in os.listdir(cv_dir)
             if f.lower().endswith(".pdf") and f != os.path.basename(cv_path)]
    for name in stray:
        problems.append(
            "cv/%s will not be linked.\n"
            "    Rename it to:  %s" % (name, os.path.basename(cv_path)))

    linked = [n for n in present if n in expected]
    print("papers/: %d PDF%s present, %d correctly named"
          % (len(present), "" if len(present) == 1 else "s", len(linked)))
    for n in linked:
        print("   linked: %s" % n)
    missing = [s for s in expected if s not in present]
    if missing:
        print("   not uploaded yet (%d): these simply show no link" % len(missing))

    if problems:
        print("\n%d problem%s found:\n" % (len(problems), "" if len(problems) == 1 else "s"))
        for p in problems:
            print("  * %s\n" % p)
        return 1

    print("\nEverything in papers/ and cv/ is named correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
