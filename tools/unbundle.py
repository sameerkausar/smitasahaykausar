#!/usr/bin/env python3
"""Rebuild the site from a Claude Design export.

Claude Design exports the page as one self-extracting HTML file: every image and
font is base64 inside a JSON manifest, and the markup sits inside an <x-dc>
element that a bundled React runtime renders at load time. That file cannot be
served or edited sensibly, so this script unpacks it into plain static files and
re-applies everything the export does not carry:

  * the PDF links on each publication card, from tools/papers.json
  * the CV links on the hero and contact buttons
  * the <link> to assets/css/custom.css, which is hand-maintained
  * page title, description, canonical and Open Graph tags

Usage:
    python3 tools/unbundle.py path/to/export.html

Writes index.html, assets/css/site.css, assets/fonts/, assets/img/.
Never touches assets/css/custom.css, papers/, cv/ or tools/.
"""

import base64
import gzip
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SITE_URL = "https://smitasahaykausar.com/"
PAGE_TITLE = "Smita Sahay-Kausar, M.D. Candidate, Ph.D."
PAGE_DESC = (
    "Smita Sahay-Kausar, M.D. candidate and Ph.D. in neuroscience at the University "
    "of Toledo College of Medicine and Life Sciences. Physician-scientist in training "
    "pursuing otolaryngology-head and neck surgery."
)

# Stable names for the photographs, keyed by their alt text in the export. An
# image whose alt text is not listed here keeps a name derived from that text.
IMG_NAMES = {
    "Smita Sahay-Kausar": "portrait.jpg",
    "White Coat Ceremony": "white-coat-ceremony.jpg",
    "Hike to Silver Lake in Utah": "silver-lake-utah.jpg",
    "Frog pose in yoga class": "yoga.jpg",
    "Biking through Paris": "paris.jpg",
    "Top of Rainbow Mountain, Peru": "rainbow-mountain-peru.jpg",
}

# Defaults declared by the export's design-component props block. The runtime
# substitutes these; without it they have to be baked in.
PORTRAIT_PAD = "115%"
PORTRAIT_STYLE = (
    "position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;"
    "object-position:62% 36%;transform:scale(1);transform-origin:62% 36%;display:block"
)

REVEAL_SCRIPT = """<script>
/* Publication and CV links ship hidden and reveal themselves only once the file
   is really in the repo, so a paper that has not been uploaded yet shows no link
   instead of a broken one. To add a paper: put the PDF in papers/ under the name
   tools/papers.json gives it, commit, and the link appears by itself. */
(function () {
  var links = document.querySelectorAll('[data-pdf]');
  if (!links.length || typeof fetch !== 'function') { return; }
  Array.prototype.forEach.call(links, function (el) {
    var a = el.tagName === 'A' ? el : el.querySelector('a');
    fetch(a.getAttribute('href'), { method: 'HEAD' })
      .then(function (r) {
        var type = r.headers.get('content-type') || '';
        if (r.ok && type.indexOf('html') === -1) { el.hidden = false; }
      })
      .catch(function () { /* missing or offline: leave it hidden */ });
  });
})();
</script>"""


def fail(msg):
    sys.exit("error: " + msg)


def read_bundle(path):
    html = open(path, encoding="utf-8").read()

    def grab(kind):
        m = re.search(r'<script type="__bundler/%s">(.*?)</script>' % kind, html, re.S)
        if not m:
            fail(
                "%s is not a Claude Design export (no __bundler/%s block). Export the "
                "page again with Download, not Copy." % (path, kind)
            )
        return json.loads(m.group(1))

    return grab("manifest"), grab("template")


def asset_bytes(manifest, uuid):
    entry = manifest[uuid]
    raw = base64.b64decode(entry["data"])
    if str(entry.get("compressed")).lower() == "true":
        raw = gzip.decompress(raw)
    return raw


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "image"


def write_images(manifest, template):
    out = os.path.join(ROOT, "assets/img")
    os.makedirs(out, exist_ok=True)
    count = 0
    for uuid, alt in re.findall(r'<img src="([0-9a-f-]{36})"[^>]*alt="([^"]*)"', template):
        if uuid not in manifest:
            continue
        name = IMG_NAMES.get(alt, slugify(alt) + ".jpg")
        open(os.path.join(out, name), "wb").write(asset_bytes(manifest, uuid))
        template = template.replace(uuid, "assets/img/" + name)
        count += 1
    return template, count


def write_fonts(manifest, template):
    """Name each font from the @font-face block that references it."""
    out = os.path.join(ROOT, "assets/fonts")
    os.makedirs(out, exist_ok=True)
    blocks = re.findall(r"/\*\s*([a-z-]+)\s*\*/\s*@font-face\s*\{(.*?)\}", template, re.S)
    count = 0
    for subset, body in blocks:
        url = re.search(r'url\("([0-9a-f-]{36})"\)', body)
        family = re.search(r"font-family:\s*'([^']+)'", body)
        weight = re.search(r"font-weight:\s*(\d+)", body)
        if not (url and family and weight):
            continue
        name = "%s-%s-%s.woff2" % (
            family.group(1).lower().replace(" ", "-"), weight.group(1), subset)
        open(os.path.join(out, name), "wb").write(asset_bytes(manifest, url.group(1)))
        # site.css lives in assets/css/, so fonts resolve one level up.
        template = template.replace(url.group(1), "../fonts/" + name)
        count += 1
    return template, count


def write_css(template):
    styles = re.findall(r"<style>(.*?)</style>", template, re.S)
    if len(styles) != 2:
        fail("expected 2 <style> blocks in the export, found %d" % len(styles))
    css = ("/* Generated by tools/unbundle.py — do not edit by hand.\n"
           "   Hand-maintained corrections belong in custom.css. */\n\n"
           "/* Design tokens and component classes. */\n" + styles[0].strip() +
           "\n\n/* Page-level styles. */\n" + styles[1].strip() + "\n")
    os.makedirs(os.path.join(ROOT, "assets/css"), exist_ok=True)
    open(os.path.join(ROOT, "assets/css/site.css"), "w", encoding="utf-8").write(css)
    return len(css)


def carve_body(template):
    m = re.search(r"</style>\s*(<script>\s*\(function\(\)\{.*?\}\)\(\);\s*</script>)\s*</helmet>",
                  template, re.S)
    if not m:
        fail("could not find the sticky-header script before </helmet>")
    sticky = m.group(1)

    if "</helmet>" not in template or "</x-dc>" not in template:
        fail("could not find the <x-dc> page wrapper in the export")
    body = template.split("</helmet>", 1)[1]
    body = body.split("</x-dc>", 1)[0].strip()

    body = body.replace("{{ portraitPad }}", PORTRAIT_PAD)
    body = body.replace("{{ portraitStyle }}", PORTRAIT_STYLE)
    leftover = re.findall(r"\{\{\s*(\w+)\s*\}\}", body)
    if leftover:
        fail("the export uses design-component variables this script does not know "
             "how to resolve: %s. Add them near PORTRAIT_STYLE in this file."
             % ", ".join(sorted(set(leftover))))
    return sticky, body


def wire_pdf_links(body, papers, cv_path):
    """Attach a hidden PDF link to each publication card named in papers.json."""
    cards = list(re.finditer(r'<article class="card".*?</article>', body, re.S))
    matched, used = [], set()

    def title_of(card):
        m = re.search(r'class="card-title"[^>]*>(.*?)</h3>', card, re.S)
        return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""

    out, cursor = [], 0
    for c in cards:
        card, title = c.group(0), title_of(c.group(0))
        entry = next((p for p in papers
                      if p["match"].lower() in title.lower() and p["slug"] not in used), None)
        if entry:
            used.add(entry["slug"])
            matched.append((entry["slug"], title))
            link = ('<div class="pdf-link" data-pdf hidden style="margin-top:8px">'
                    '<a href="papers/%s.pdf" class="pdf-a">PDF</a></div>' % entry["slug"])
            i = card.rindex("</div>")          # closes the card-meta line
            card = card[:i] + link + card[i:]
        elif title:
            print("   note: no papers.json entry for card %r" % title[:64])
        out.append(body[cursor:c.start()] + card)
        cursor = c.end()
    out.append(body[cursor:])
    body = "".join(out)

    for p in papers:
        if p["slug"] not in used:
            print("   warning: papers.json entry %r matched no card on the page"
                  % p["slug"])

    # The export leaves both CV buttons as href="#".
    n_cv = body.count('href="#"')
    body = body.replace('<a class="btn btn-primary" href="#"',
                        '<a class="btn btn-primary pdf-link" data-pdf hidden href="%s"' % cv_path)
    body = body.replace('<a class="btn btn-secondary" href="#"',
                        '<a class="btn btn-secondary pdf-link" data-pdf hidden href="%s"' % cv_path)
    if 'href="#"' in body:
        print("   warning: a placeholder href=\"#\" link is still unresolved")
    return body, len(matched), n_cv


def build_document(sticky, body):
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="author" content="Smita Sahay-Kausar">
<link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml">
<link rel="canonical" href="{url}">

<meta property="og:type" content="profile">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{url}assets/img/portrait.jpg">
<meta name="twitter:card" content="summary_large_image">

<link rel="preload" href="assets/fonts/barlow-400-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="assets/fonts/barlow-condensed-600-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/css/site.css">
<link rel="stylesheet" href="assets/css/custom.css">
{sticky}
</head>
<body>

{body}

{reveal}
</body>
</html>
""".format(title=PAGE_TITLE, desc=PAGE_DESC, url=SITE_URL,
           sticky=sticky, body=body, reveal=REVEAL_SCRIPT)


def write_papers_readme(papers):
    """Regenerate papers/README.md so the filename list can never drift."""
    guidance = {
        "open": "Open access — post the published PDF.",
        "restricted": "Subscription journal — accepted manuscript only, check the policy.",
        "pending": "Not accepted yet — post nothing.",
    }
    rows = "\n".join(
        "| %s | `%s` | `%s.pdf` | %s |" % (p["label"], p["venue"], p["slug"], guidance[p["access"]])
        for p in papers)
    text = """# papers/

Drop manuscript PDFs in this folder. A **PDF** link appears on the matching card in
the Research section as soon as the file is here — no HTML editing, ever.

The filename has to match exactly: all lowercase, hyphens, `.pdf`.

> This file is generated from `tools/papers.json` by `tools/unbundle.py`.
> To add a paper, add an entry there rather than editing this table.

| Publication | Venue | Filename | Posting it |
|---|---|---|---|
%s

The CV is separate: it goes in `../cv/` as `smita-sahay-kausar-cv.pdf`, and drives
the "CV (PDF)" and "Download CV" buttons.

## Which version of a PDF you are allowed to post

Worth two minutes, since the site is public and program directors read it.

- **Open access (CC BY)** — the published PDF is fine. That covers the MDPI titles
  (*Biology*, *IJMS*, *Brain Sciences*, *Cells*), *Tracheostomy Journal*, and
  *Journal of Bioinformatics & Systems Biology*.
- **Subscription journals** — usually the author-accepted manuscript rather than the
  typeset PDF. That is the case for both *Molecular Psychiatry* papers; Springer
  Nature generally allows the accepted manuscript on a personal site after a
  six-month embargo. Confirm on [Sherpa Romeo](https://v2.sherpa.ac.uk/romeo/).
- **Under review** — nothing goes up until it is accepted, unless it is already on a
  preprint server. The DOI link carries it in the meantime.
- **The dissertation** is hers and already public on OhioLINK. Safe to post.

When in doubt the DOI link alone is always safe; the PDF is a convenience.
""" % rows
    open(os.path.join(ROOT, "papers/README.md"), "w", encoding="utf-8").write(text)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    export = sys.argv[1]
    if not os.path.isfile(export):
        fail("no such file: " + export)

    config = json.load(open(os.path.join(ROOT, "tools/papers.json"), encoding="utf-8"))
    papers, cv_path = config["papers"], config["cv"]

    manifest, template = read_bundle(export)
    template, n_img = write_images(manifest, template)
    template, n_font = write_fonts(manifest, template)
    n_css = write_css(template)
    sticky, body = carve_body(template)
    body, n_pdf, n_cv = wire_pdf_links(body, papers, cv_path)

    if "x-dc" in body or "__bundler" in body:
        fail("bundler scaffolding survived into the page body")

    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(
        build_document(sticky, body))
    write_papers_readme(papers)

    print("rebuilt index.html")
    print("  %2d images   -> assets/img/" % n_img)
    print("  %2d fonts    -> assets/fonts/" % n_font)
    print("  %2d bytes    -> assets/css/site.css" % n_css)
    print("  %2d PDF links wired, %d CV buttons" % (n_pdf, n_cv))
    print("  regenerated papers/README.md")
    print("\ncustom.css, papers/ and cv/ were left untouched.")


if __name__ == "__main__":
    main()
