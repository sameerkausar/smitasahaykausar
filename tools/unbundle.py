#!/usr/bin/env python3
"""Rebuild the site from a Claude Design export.

Claude Design exports the page as one self-extracting HTML file: every image and
font is base64 inside a JSON manifest, and the markup sits inside an <x-dc>
element that a bundled React runtime renders at load time. That file cannot be
served or edited sensibly, so this script unpacks it into plain static files and
re-applies everything the export does not carry:

  * the PDF links on each publication card, from tools/documents.json
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
import html
import datetime
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SITE_URL = "https://smitasahaykausar.com/"
PAGE_TITLE = "Smita Sahay-Kausar, Ph.D."
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

READER_MARKUP = """
<!-- Full-screen reader for a paper, opened from a publication card. Injected by
     tools/unbundle.py; styled in assets/css/custom.css. -->
<div class="reader" id="reader" hidden role="dialog" aria-modal="true" aria-labelledby="reader-title">
  <div class="reader-bar">
    <div class="reader-heading">
      <p class="reader-venue" id="reader-venue"></p>
      <h2 class="reader-title" id="reader-title"></h2>
    </div>
    <div class="reader-actions">
      <a class="reader-btn" id="reader-tab" target="_blank" rel="noopener">Open in new tab</a>
      <a class="reader-btn" id="reader-download" download>Download</a>
      <button class="reader-btn reader-close" id="reader-close" type="button">Close</button>
    </div>
  </div>
  <div class="reader-body">
    <iframe class="reader-frame" id="reader-frame" title="" src="about:blank"></iframe>
  </div>
</div>"""

REVEAL_SCRIPT = """<script>
/* Two jobs.

   1. Reveal. Every PDF link and every card's reader affordance ships hidden.
      Each distinct file is probed once with a HEAD request and revealed only if
      it is really there, so a paper that has not been uploaded yet shows no
      link and no clickable card instead of a dead end. To add a paper: put the
      PDF in papers/ under the name tools/documents.json gives it, commit, done.

   2. The reader. A card whose PDF exists opens it full screen, so a reviewer
      can read the whole paper without being thrown out to another site.
      On a narrow screen the PDF opens natively instead: phone browsers render
      PDFs in an iframe unreliably, and their built-in viewers are better. */
(function () {
  'use strict';

  /* ---- 1. reveal what actually exists ---- */
  var pending = {};
  Array.prototype.forEach.call(document.querySelectorAll('[data-pdf]'), function (el) {
    var a = el.tagName === 'A' ? el : el.querySelector('a');
    var href = a && a.getAttribute('href');
    if (!href) { return; }
    (pending[href] = pending[href] || []).push(el);
  });

  Object.keys(pending).forEach(function (href) {
    if (typeof fetch !== 'function') { return; }
    fetch(href, { method: 'HEAD' })
      .then(function (r) {
        var type = r.headers.get('content-type') || '';
        if (!r.ok || type.indexOf('html') !== -1) { return; }
        pending[href].forEach(function (el) {
          el.hidden = false;
          var card = el.closest('[data-paper-pdf]');
          if (card) { card.setAttribute('data-paper-ready', ''); }
        });
      })
      .catch(function () { /* missing or offline: leave it hidden */ });
  });

  /* ---- 2. the reader ---- */
  var reader = document.getElementById('reader');
  if (!reader) { return; }
  var frame = document.getElementById('reader-frame');
  var titleEl = document.getElementById('reader-title');
  var venueEl = document.getElementById('reader-venue');
  var tabLink = document.getElementById('reader-tab');
  var dlLink = document.getElementById('reader-download');
  var lastFocus = null;

  function nativeInstead() {
    /* Phone-sized viewports get the browser's own PDF viewer: phone browsers
       render PDFs in an iframe unreliably and their native viewers are better.
       Some desktop browsers also have inline PDF viewing switched off, often by
       enterprise policy, and would show an empty frame — send those out too,
       rather than opening a reader with nothing in it. */
    if (window.matchMedia('(max-width: 700px)').matches) { return true; }
    return navigator.pdfViewerEnabled === false;
  }

  function open(card) {
    var pdf = card.getAttribute('data-paper-pdf');
    /* Posters open in a new tab rather than the reader: a poster is one big
       landscape sheet a reader wants to zoom around, which the browser's own
       viewer does better than an iframe. Papers keep the reader. */
    if (card.classList.contains('talk-row') || nativeInstead()) {
      window.open(pdf, '_blank', 'noopener');
      return;
    }

    lastFocus = document.activeElement;
    titleEl.textContent = card.getAttribute('data-paper-title') || 'Paper';
    venueEl.textContent = card.getAttribute('data-paper-venue') || '';
    tabLink.href = pdf;
    dlLink.href = pdf;
    frame.title = titleEl.textContent;
    frame.src = pdf;
    reader.hidden = false;
    document.documentElement.classList.add('reader-open');
    document.getElementById('reader-close').focus();
  }

  function close() {
    if (reader.hidden) { return; }
    reader.hidden = true;
    frame.src = 'about:blank';      /* stop rendering and free the plugin */
    document.documentElement.classList.remove('reader-open');
    if (lastFocus && lastFocus.focus) { lastFocus.focus(); }
  }

  document.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest('#reader-close')) { close(); return; }
    /* The backdrop is the dialog itself; clicks on the bar or frame are inside. */
    if (e.target === reader) { close(); return; }

    var trigger = e.target.closest && e.target.closest('[data-paper-ready]');
    if (!trigger) { return; }
    /* Let real links inside the card do their own thing. */
    if (e.target.closest('a')) { return; }
    e.preventDefault();
    open(trigger);
  });

  document.addEventListener('keydown', function (e) {
    if (reader.hidden) { return; }
    if (e.key === 'Escape') { close(); return; }
    if (e.key !== 'Tab') { return; }
    /* Keep focus inside the dialog while it is open. */
    var f = reader.querySelectorAll('a[href], button');
    if (!f.length) { return; }
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
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


ROW_MARKER = '<div style="display:grid;grid-template-columns:86px 1fr'


def _element_end(text, start):
    """Index just past the <div> opening at `start`, matching nesting."""
    depth = 0
    for m in re.finditer(r"<div\b|</div>", text[start:]):
        depth += 1 if m.group(0) != "</div>" else -1
        if depth == 0:
            return start + m.end()
    return None


def wire_posters(body, posters):
    """Attach a hidden poster PDF to each talks-and-posters row named in the config.

    Same contract as the publication cards: the row carries the reader's data
    attributes and an affordance that stays hidden until the reveal probe
    confirms the file is really there.
    """
    used, count = set(), 0
    edits = []          # (start, end, new_text), applied back to front

    pos = 0
    while True:
        start = body.find(ROW_MARKER, pos)
        if start < 0:
            break
        end = _element_end(body, start)
        if end is None:
            break
        pos = end
        row = body[start:end]

        m = re.search(r'font-size:16px;line-height:1\.45">([^<]*)<', row)
        if not m:
            continue
        title = html.unescape(m.group(1)).strip()

        # Two rows can carry the same title -- "Purinergic System Perturbations
        # in Schizophrenia" is both an invited talk at the University of Toledo
        # and a poster at the Graduate Research Annual Forum. Matching on title
        # alone attached the poster to whichever came first, which was the talk,
        # and left the real poster row unwired. The venue in documents.json
        # settles it: the row's venue line has to appear in the entry's venue.
        vm = re.search(r'color:var\(--color-neutral-700\);margin-top:2px">([^<]*)<', row)
        row_venue = html.unescape(vm.group(1)).strip().lower() if vm else ""

        def fits(p):
            venue = p.get("venue", "").lower()
            return not (venue and row_venue) or row_venue in venue

        entry = next((p for p in posters
                      if p["match"].lower() in title.lower()
                      and p["slug"] not in used and fits(p)), None)
        if not entry:
            continue
        used.add(entry["slug"])
        count += 1
        pdf = "posters/%s.pdf" % entry["slug"]

        affordance = ('<div class="poster-actions" data-pdf hidden>'
                      '<a href="%s" class="poster-a" target="_blank" rel="noopener noreferrer">View poster</a></div>' % pdf)
        # The row is [date cell][content cell]; put the affordance at the end of
        # the content cell so it sits under the venue rather than in the gutter.
        insert_at = row.rindex("</div>", 0, row.rindex("</div>"))
        new_row = row[:insert_at] + affordance + row[insert_at:]
        new_row = new_row.replace(
            ROW_MARKER,
            '<div class="talk-row" data-paper-pdf="%s" data-paper-title="%s" '
            'data-paper-venue="%s" style="display:grid;grid-template-columns:86px 1fr'
            % (pdf, html.escape(title, quote=True),
               html.escape(entry.get("venue", ""), quote=True)),
            1)
        edits.append((start, end, new_row))

    for start, end, new_row in reversed(edits):
        body = body[:start] + new_row + body[end:]

    for p in posters:
        if p["slug"] not in used:
            print("   warning: poster entry %r matched no row on the page" % p["slug"])
    return body, count


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
            pdf = "papers/%s.pdf" % entry["slug"]

            # Two affordances: a button that opens the paper in the full-screen
            # reader, and a plain link to the file itself. Both ship hidden and
            # are revealed only once the PDF is really in the repo.
            block = ('<div class="paper-actions" data-pdf hidden>'
                     '<button class="paper-read" type="button">Read paper</button>'
                     '<a href="%s" class="pdf-a" download>PDF</a>'
                     '</div>' % pdf)
            i = card.rindex("</div>")          # closes the card-meta line
            card = card[:i] + block + card[i:]

            # The card becomes the click target for the reader. It stays inert
            # until the reveal probe confirms the file exists.
            card = card.replace(
                '<article class="card"',
                '<article class="card" data-paper-pdf="%s" data-paper-title="%s" '
                'data-paper-venue="%s"'
                % (pdf, html.escape(title, quote=True),
                   html.escape(entry.get("venue", ""), quote=True)),
                1)
        elif title:
            print("   note: no documents.json entry for card %r" % title[:64])
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


def regroup_row_links(body):
    """Put a talk row's abstract link beside its poster link, under the venue.

    The export puts the published-record link ("Abstract", and on one row
    "Poster") in the date gutter, while wire_posters puts the hosted PDF link
    under the venue. A row offering both showed them in two different places
    in two different faces. This moves the gutter link down into a single
    actions row -- abstract first, then poster -- and gives it the same class
    the poster link wears so the two match.

    "Abstract" becomes "View abstract" to read alongside "View poster", and
    "Poster" becomes "View poster (DOI)": that one points at the published
    F1000Research record of a poster we also host, so the qualifier says
    which is the citation and which is the file.

    The poster half keeps its own hidden wrapper, so a row with an abstract
    and no uploaded poster shows one link and no empty gap.
    """
    GUTTER = re.compile(
        r'<div style="font-size:13\.5px;margin-top:4px">\s*'
        r'(<a\b[^>]*href="https?://[^"]*"[^>]*>)(.*?)</a>\s*</div>', re.S)

    moved = renamed = paired = 0
    out, pos = [], 0
    while True:
        start = body.find('<div class="talk-row"', pos)
        if start < 0:
            break
        end = _element_end(body, start)
        if end is None:
            break
        out.append(body[pos:start])
        row = body[start:end]
        pos = end

        m = GUTTER.search(row)
        poster = re.search(r'<div class="poster-actions".*?</div>\s*</div>', row, re.S)
        if not m or not poster:
            out.append(row)
            continue

        open_tag, label = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()

        # A gutter link labelled "Poster" points at the published record of the
        # same poster we host ourselves -- the F1000Research entry for the
        # Sex-Specific MDD row, which carries a citable DOI. On its own,
        # "Poster" next to "View poster" asks the reader to guess which is
        # which. The qualifier keeps the record and says what it is: the
        # citation lives there, the file is ours.
        if label.lower() == "poster":
            label = "View poster (DOI)"
            renamed += 1
        elif label.lower() == "abstract":
            label = "View abstract"
            renamed += 1
        # Drop the inline colour so .poster-a and the outbound-link rule win.
        open_tag = re.sub(r'\s*style="[^"]*"', "", open_tag)
        open_tag = open_tag.replace("<a ", '<a class="poster-a" ', 1)

        row = row[:m.start()] + row[m.end():]          # lift it out of the gutter
        poster = re.search(r'(<div class="poster-actions".*?</div>)', row, re.S)
        if not poster:
            out.append(row)
            continue
        paired += 1
        moved += 1
        row = (row[:poster.start(1)]
               + '<div class="talk-actions">%s%s</a>%s</div>'
                 % (open_tag, label, poster.group(1))
               + row[poster.end(1):])
        out.append(row)

    out.append(body[pos:])
    return "".join(out), moved, renamed


def open_links_in_new_tab(body):
    """Send every link that leaves the page to a new tab.

    Two kinds qualify. Anything on another origin -- the DOI line on a
    publication card, the Abstract and Poster records under talks, the
    articles, the profile links -- and the two CV buttons, which point at a
    PDF that would otherwise replace the site with a document and leave no
    way back but the back button.

    rel="noopener noreferrer" goes on with it. Without noopener the opened
    page gets a handle on ours through window.opener and can navigate it
    somewhere else while the reader is looking away, which is worth closing
    off even for a DOI resolver.

    Not touched: in-page anchors, and the "View poster" and "PDF" links,
    which the reader and the download attribute already handle.

    Done here rather than in custom.css because target is an attribute and
    CSS cannot set one, and index.html is regenerated from each export --
    a hand edit would not survive the next rebuild.
    """
    n = 0

    def add(m):
        nonlocal n
        attrs = m.group(1)
        if "target=" in attrs:
            return m.group(0)
        href = re.search(r'href="([^"]*)"', attrs)
        if not href:
            return m.group(0)
        target = href.group(1)
        external = target.startswith(("http://", "https://"))
        is_cv = target.startswith("cv/")
        if not (external or is_cv):
            return m.group(0)
        n += 1
        return "<a%s target=\"_blank\" rel=\"noopener noreferrer\">" % attrs.rstrip()

    body = re.sub(r"<a\b([^>]*)>", add, body)
    return body, n


def person_schema(body):
    """Describe the person behind the page in schema.org terms.

    A name query is an entity question before it is a keyword one: Google has
    to decide that this domain and the Smita Sahay-Kausar with an ORCID, a
    Scholar profile and a LinkedIn are one person. sameAs is how a site claims
    that, and it only counts when the profiles point back -- see the SEO notes
    in README.md.

    The profile URLs are read out of the page rather than hard-coded here, so
    they cannot drift from what the contact section actually links to.
    """
    def find(host):
        m = re.search(r'href="(https?://[^"]*%s[^"]*)"' % re.escape(host), body)
        return m.group(1) if m else None

    same = [u for u in (find("linkedin.com/in/"),
                        find("scholar.google.com/citations"),
                        find("orcid.org/")) if u]
    orcid = find("orcid.org/")

    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": "Smita Sahay-Kausar",
        "givenName": "Smita",
        "familyName": "Sahay-Kausar",
        "url": SITE_URL,
        "image": SITE_URL + "assets/img/portrait.jpg",
        "jobTitle": "M.D. Candidate, Ph.D.",
        "description": PAGE_DESC,
        "alumniOf": {
            "@type": "CollegeOrUniversity",
            "name": "University of Toledo College of Medicine and Life Sciences",
        },
        "affiliation": {
            "@type": "CollegeOrUniversity",
            "name": "University of Toledo College of Medicine and Life Sciences",
        },
        "knowsAbout": [
            "Neuroscience", "Bioinformatics", "Psychiatry",
            "Otolaryngology-Head and Neck Surgery", "Physician-scientist training",
        ],
    }
    if orcid:
        data["identifier"] = {"@type": "PropertyValue",
                              "propertyID": "ORCID", "value": orcid}
    if same:
        data["sameAs"] = same
    return ('<script type="application/ld+json">%s</script>'
            % json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def write_sitemap():
    """One URL, because it is one page. Written here so lastmod tracks rebuilds."""
    today = datetime.date.today().isoformat()
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           '  <url>\n'
           '    <loc>%s</loc>\n'
           '    <lastmod>%s</lastmod>\n'
           '  </url>\n'
           '</urlset>\n' % (SITE_URL, today))
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(xml)
    return today


def build_document(sticky, body, schema):
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
<meta property="og:image:alt" content="Smita Sahay-Kausar">
<meta property="og:site_name" content="Smita Sahay-Kausar">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{url}assets/img/portrait.jpg">

{schema}

<link rel="preload" href="assets/fonts/barlow-400-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="assets/fonts/barlow-condensed-600-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/css/site.css">
<link rel="stylesheet" href="assets/css/custom.css">
{sticky}
</head>
<body>

{body}
{reader}

{reveal}
</body>
</html>
""".format(title=PAGE_TITLE, desc=PAGE_DESC, url=SITE_URL, sticky=sticky,
           schema=schema, body=body, reader=READER_MARKUP, reveal=REVEAL_SCRIPT)


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

> This file is generated from `tools/documents.json` by `tools/unbundle.py`.
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

    config = json.load(open(os.path.join(ROOT, "tools/documents.json"), encoding="utf-8"))
    papers, posters, cv_path = config["papers"], config["posters"], config["cv"]

    manifest, template = read_bundle(export)
    template, n_img = write_images(manifest, template)
    template, n_font = write_fonts(manifest, template)
    n_css = write_css(template)
    sticky, body = carve_body(template)
    body, n_pdf, n_cv = wire_pdf_links(body, papers, cv_path)
    body, n_poster = wire_posters(body, posters)
    body, n_moved, n_renamed = regroup_row_links(body)
    body, n_tab = open_links_in_new_tab(body)

    if "x-dc" in body or "__bundler" in body:
        fail("bundler scaffolding survived into the page body")

    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(
        build_document(sticky, body, person_schema(body)))
    write_papers_readme(papers)
    stamp = write_sitemap()

    print("rebuilt index.html")
    print("  %2d images   -> assets/img/" % n_img)
    print("  %2d fonts    -> assets/fonts/" % n_font)
    print("  %2d bytes    -> assets/css/site.css" % n_css)
    print("  %2d paper slots, %d poster slots, %d CV buttons"
          % (n_pdf, n_poster, n_cv))
    print("  %2d links open in a new tab" % n_tab)
    print("  %2d abstract links moved beside their poster link (%d relabelled)"
          % (n_moved, n_renamed))
    print("  regenerated papers/README.md")
    print("     Person schema in the head, sitemap.xml lastmod %s" % stamp)
    print("\ncustom.css, papers/ and cv/ were left untouched.")


if __name__ == "__main__":
    main()
