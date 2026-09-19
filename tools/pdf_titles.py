#!/usr/bin/env python3
"""Stamp each hosted PDF with the title the page gives it.

A browser names a PDF tab from the file's own /Title, not from its filename.
Posters exported from PowerPoint arrive carrying the template's title and,
worse, the template author's name: "BMI PowerPoint Presentation 48x36" by
"Martin Cryer & Anthony Wong". Someone who opens a poster from the site sees
that in the tab, and anyone who checks the file properties sees a stranger
credited on Smita's work.

This rewrites /Title from tools/documents.json -- the same source the page
uses for the link text -- and sets /Author to her. Only the metadata changes;
the pages are copied through untouched.

    python3 tools/pdf_titles.py          # report what would change
    python3 tools/pdf_titles.py --write  # apply it

Run it after uploading a PDF. Nothing else needs it: the filename is what
wires the link up, and that is check_pdfs.py's job.
"""

import json
import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTHOR = "Smita Sahay-Kausar"


def wanted_titles():
    """slug.pdf -> the title the page shows, for posters, papers and the CV."""
    cfg = json.load(open(os.path.join(ROOT, "tools/documents.json"), encoding="utf-8"))
    page = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    out = {}
    for kind in ("posters", "papers"):
        for entry in cfg[kind]:
            rel = "%s/%s.pdf" % (kind, entry["slug"])
            # The page carries the full title on the row or card it wires up.
            m = re.search(r'data-paper-pdf="%s" data-paper-title="([^"]*)"'
                          % re.escape(rel), page)
            if m:
                import html as _html
                out[rel] = _html.unescape(m.group(1))
    out[cfg["cv"]] = "Smita Sahay-Kausar — Curriculum Vitae"
    return out


def main():
    write = "--write" in sys.argv[1:]
    try:
        import pypdf
    except ImportError:
        sys.exit("error: pypdf is required — pip install pypdf")

    changed = ok = 0
    for rel, title in sorted(wanted_titles().items()):
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            continue
        reader = pypdf.PdfReader(path)
        meta = dict(reader.metadata or {})
        now_title, now_author = meta.get("/Title"), meta.get("/Author")
        if now_title == title and now_author == AUTHOR:
            ok += 1
            continue
        changed += 1
        print("  %s" % rel)
        print("      title : %r -> %r" % (now_title, title))
        if now_author != AUTHOR:
            print("      author: %r -> %r" % (now_author, AUTHOR))
        if not write:
            continue

        writer = pypdf.PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        keep = {k: v for k, v in meta.items()
                if k not in ("/Title", "/Author", "/Subject")}
        writer.add_metadata({**keep, "/Title": title, "/Author": AUTHOR})
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        os.close(fd)
        try:
            with open(tmp, "wb") as fh:
                writer.write(fh)
            # Never ship a file we cannot read back with the same page count.
            after = pypdf.PdfReader(tmp)
            if len(after.pages) != len(reader.pages):
                raise RuntimeError("page count changed for %s" % rel)
            shutil.move(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    if not changed:
        print("Every hosted PDF already carries its own title.")
    elif write:
        print("\nRewrote %d file(s); %d were already correct." % (changed, ok))
    else:
        print("\n%d file(s) would change; %d are already correct."
              "\nRe-run with --write to apply." % (changed, ok))


if __name__ == "__main__":
    main()
