#!/usr/bin/env python3
"""Check that every hosted PDF is named so the site will actually link it.

The site reveals a link only when the file exists at the exact path
tools/documents.json gives it, so a misspelled filename fails silently: the
upload succeeds and no link ever appears. This turns that into a loud failure
that names the correct filename.

Run it yourself with `python3 tools/check_pdfs.py`; CI runs it on every push.
"""

import json
import os
import sys
import difflib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    config = json.load(open(os.path.join(ROOT, "tools/documents.json"), encoding="utf-8"))
    problems, summary = [], []

    for folder, key in (("posters", "posters"), ("papers", "papers")):
        expected = {p["slug"] + ".pdf": p for p in config[key]}
        d = os.path.join(ROOT, folder)
        present = sorted(f for f in os.listdir(d) if f.lower().endswith(".pdf"))

        for name in present:
            if name in expected:
                continue
            close = difflib.get_close_matches(name, expected, n=1, cutoff=0.6)
            if close:
                problems.append(
                    "%s/%s will not be linked.\n"
                    "    Rename it to:  %s\n"
                    "    (that is the filename tools/documents.json gives it)"
                    % (folder, name, close[0]))
            else:
                problems.append(
                    "%s/%s does not match anything in tools/documents.json.\n"
                    "    Either rename it to one of the expected filenames, or add\n"
                    "    an entry for it and rerun tools/unbundle.py."
                    % (folder, name))

        linked = [n for n in present if n in expected]
        summary.append((folder, len(present), linked, len(expected) - len(linked)))

    cv_path = os.path.join(ROOT, config["cv"])
    cv_dir = os.path.dirname(cv_path)
    for name in os.listdir(cv_dir):
        if name.lower().endswith(".pdf") and name != os.path.basename(cv_path):
            problems.append("cv/%s will not be linked.\n    Rename it to:  %s"
                            % (name, os.path.basename(cv_path)))

    for folder, n, linked, missing in summary:
        print("%s/: %d present, %d correctly named" % (folder, n, len(linked)))
        for name in linked:
            print("   linked: %s" % name)
        if missing:
            print("   %d not uploaded yet: these simply show nothing" % missing)

    if problems:
        print("\n%d problem%s found:\n" % (len(problems), "" if len(problems) == 1 else "s"))
        for p in problems:
            print("  * %s\n" % p)
        return 1

    print("\nEvery hosted PDF is named correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
