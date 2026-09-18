# smitasahaykausar.com

Personal academic site for Smita Sahay-Kausar, M.D. candidate and Ph.D. in
neuroscience, University of Toledo College of Medicine and Life Sciences.

Plain static HTML, CSS, fonts and images — no build step, no framework, no
dependencies. GitHub Pages serves it directly.

```
index.html              the page            (generated — do not hand-edit)
assets/css/site.css     design system       (generated — do not hand-edit)
assets/css/custom.css   our own CSS         (hand-maintained)
assets/fonts/           Barlow + Barlow Condensed, self-hosted
assets/img/             portrait, photo strip, favicon
papers/                 manuscript PDFs     -> papers/README.md
cv/                     smita-sahay-kausar-cv.pdf
tools/papers.json       which PDF belongs to which paper
tools/unbundle.py       rebuilds the site from a Claude Design export
tools/check_papers.py   flags a PDF that is named wrong
```

## Adding a paper PDF

1. Name the file exactly as [`papers/README.md`](papers/README.md) lists it.
2. Put it in `papers/` — dragging it into the folder on github.com works fine.
3. Commit.

The **PDF** link appears under that paper's journal line on its own. `index.html`
never has to change.

Every PDF link ships hidden, and a short script at the bottom of `index.html` asks
the server whether the file exists before revealing it. A paper that has not been
uploaded shows no link at all rather than a broken one, so the site is always safe
to hand to someone. The CV buttons work the same way.

If a filename is wrong the upload still succeeds and no link appears — silent and
confusing. `tools/check_papers.py` exists to catch exactly that, and CI runs it on
every push, so a typo shows up as a failed check that names the correct filename.
Run it yourself any time:

```sh
python3 tools/check_papers.py
```

### Adding a paper that is not in the list yet

Add an entry to [`tools/papers.json`](tools/papers.json) — `slug` is the filename,
`match` is a distinctive phrase from the publication's title as it appears on the
page — then rerun `tools/unbundle.py` (below). It wires the link and regenerates
`papers/README.md`.

## Updating the design

Smita builds the page in Claude Design. Each export is a single self-extracting
HTML file with every asset base64'd inside it and the markup wrapped in a React
runtime — not something that can be served or edited. `tools/unbundle.py` unpacks
an export into the files above and re-applies everything the export does not carry:
the PDF links, the CV links, the `custom.css` link, and the page metadata.

```sh
python3 tools/unbundle.py ~/Downloads/new-export.html
```

It rewrites `index.html`, `assets/css/site.css`, `assets/fonts/` and `assets/img/`,
and leaves `custom.css`, `papers/`, `cv/` and `tools/` alone. Check what changed
with `git diff`, preview locally, then commit.

So: **design changes go through Claude Design and a rebuild. Styling fixes go in
`custom.css`. Never edit `index.html` or `site.css` by hand** — the next rebuild
discards them.

## Publishing with GitHub Pages

1. **Settings → Pages**.
2. **Source: Deploy from a branch**, branch `main`, folder `/ (root)`. Save.
3. A minute later the site is live at
   `https://<username>.github.io/smitasahaykausar/`.

### Using the smitasahaykausar.com domain

The footer and social-preview tags already point there. To make it real:

1. At the registrar, add:
   - `A` records for `@` → `185.199.108.153`, `185.199.109.153`,
     `185.199.110.153`, `185.199.111.153`
   - `CNAME` for `www` → `<username>.github.io`
2. Add a file named `CNAME` at the repo root containing one line:
   `smitasahaykausar.com`
3. **Settings → Pages → Custom domain**, enter it, and tick **Enforce HTTPS**
   once the certificate is issued.

## Previewing locally

```sh
python3 -m http.server 8000
```

Open `http://localhost:8000`. Use the server rather than double-clicking
`index.html` — PDF links only reveal themselves over `http://`, not `file://`.
