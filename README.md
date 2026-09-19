# smitasahaykausar.com

Personal academic site for Smita Sahay-Kausar, M.D. candidate and Ph.D. in
neuroscience, University of Toledo College of Medicine and Life Sciences.

Plain static HTML, CSS, fonts and images — no build step, no framework, no
dependencies. GitHub Pages serves it directly.

```
index.html              the page            (generated — do not hand-edit)
assets/css/site.css     design system       (generated — do not hand-edit)
assets/css/custom.css   our own CSS + the reader  (hand-maintained)
assets/fonts/           Barlow + Barlow Condensed, self-hosted
assets/img/             portrait, photo strip, favicon
posters/                posters and slide decks  -> posters/README.md
papers/                 manuscript PDFs          -> papers/README.md
cv/                     smita-sahay-kausar-cv.pdf
tools/documents.json    which PDF belongs to which card or row
tools/unbundle.py       rebuilds the site from a Claude Design export
tools/check_pdfs.py     flags a PDF that is named wrong
```

## Adding a PDF

Two folders, because the rules differ:

- **`posters/`** — posters, conference abstracts and slide decks. Hers outright, so
  anything can go up. This is the main one. Adds a **View poster** link to the
  matching row in Talks and Posters.
- **`papers/`** — manuscripts. Only where the journal's licence allows it; see
  [`papers/README.md`](papers/README.md). Everything else stays a DOI link, which
  is what the cards already do. Adds a **Read paper** button to the card.

Either way:

1. Name the file exactly as that folder's README lists it.
2. Put it in the folder — dragging it in on github.com works fine.
3. Commit.

The card or row wires itself up. `index.html` never has to change.

Clicking it opens the PDF full screen over the site, so a reviewer can read the
whole thing without being navigated away. Esc, the Close button or a click on the
backdrop returns them exactly where they were. On a phone the PDF opens in the
browser's own viewer instead: mobile browsers render PDFs in an embedded frame
unreliably, and their native viewers are better. The same happens on a desktop
browser that has inline PDF viewing turned off, usually by enterprise policy —
better than a reader with an empty frame in it.

All of this ships hidden. A short script at the bottom of `index.html` asks the
server whether each file exists before revealing anything, so a paper that has not
been uploaded shows no button, no link, and no clickable card — never a dead end.
The CV buttons work the same way.

If a filename is wrong the upload still succeeds and no link appears — silent and
confusing. `tools/check_pdfs.py` exists to catch exactly that, and CI runs it on
every push, so a typo shows up as a failed check that names the correct filename.
Run it yourself any time:

```sh
python3 tools/check_pdfs.py
```

The reader's markup, styling and behaviour live in `tools/unbundle.py` and
`assets/css/custom.css`, so a fresh export from Claude Design gets them back
automatically.

### Adding something that is not in the list yet

Add an entry to [`tools/documents.json`](tools/documents.json) under `posters` or
`papers` — `slug` is the filename, `match` is a distinctive phrase from the title
as it appears on the page — then rerun `tools/unbundle.py` (below). It wires the link and regenerates
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
and leaves `custom.css`, `posters/`, `papers/`, `cv/` and `tools/` alone. Check what changed
with `git diff`, preview locally, then commit.

So: **design changes go through Claude Design and a rebuild. Styling fixes go in
`custom.css`. Never edit `index.html` or `site.css` by hand** — the next rebuild
discards them.

## Publishing with GitHub Pages

1. **Settings → Pages**.
2. **Source: Deploy from a branch**, branch `main`, folder `/ (root)`. Save.
3. A minute later the site is live at
   `https://sameerkausar.github.io/smitasahaykausar/`.

### Using the smitasahaykausar.com domain

The footer and social-preview tags already point there, and the `CNAME` file at
the repo root claims the domain for this repo. What is left is DNS and the
Pages setting.

The domain is registered at Squarespace. In **Squarespace → Domains →
smitasahaykausar.com → DNS → DNS Settings**, delete the parking records
Squarespace adds by default (the `@` A records pointing at Squarespace and any
`www` CNAME pointing at a Squarespace host), then add:

| Host  | Type    | Value                  |
| ----- | ------- | ---------------------- |
| `@`   | `A`     | `185.199.108.153`      |
| `@`   | `A`     | `185.199.109.153`      |
| `@`   | `A`     | `185.199.110.153`      |
| `@`   | `A`     | `185.199.111.153`      |
| `@`   | `AAAA`  | `2606:50c0:8000::153`  |
| `@`   | `AAAA`  | `2606:50c0:8001::153`  |
| `@`   | `AAAA`  | `2606:50c0:8002::153`  |
| `@`   | `AAAA`  | `2606:50c0:8003::153`  |
| `www` | `CNAME` | `sameerkausar.github.io.` |

Leave the `MX` and any mail-related records alone — they are email, not the
website.

Then in **Settings → Pages → Custom domain** enter `smitasahaykausar.com`,
Save, and once GitHub finishes the DNS check and issues the certificate, tick
**Enforce HTTPS**. GitHub redirects `www` to the apex on its own.

Propagation is usually minutes and occasionally a few hours. Until the
certificate is issued, HTTPS will warn — that is normal, not a misconfiguration.

## Previewing locally

```sh
python3 -m http.server 8000
```

Open `http://localhost:8000`. Use the server rather than double-clicking
`index.html` — PDF links only reveal themselves over `http://`, not `file://`.
