# smitasahaykausar.com

Personal academic site for Smita Sahay-Kausar, M.D. candidate and Ph.D. in
neuroscience, University of Toledo College of Medicine and Life Sciences.

Plain static HTML, CSS, fonts and images. No build step, no framework, no
dependencies — open `index.html` and it works.

```
index.html              the whole page
assets/css/site.css     design tokens + all styling
assets/fonts/           Barlow and Barlow Condensed (self-hosted .woff2)
assets/img/             portrait, photo strip, favicon
papers/                 manuscript PDFs  -> see papers/README.md
cv/                     smita-sahay-kausar-cv.pdf
```

## Adding a paper PDF

1. Name the file exactly as listed in [`papers/README.md`](papers/README.md).
2. Drop it into `papers/`.
3. Commit and push.

A **PDF** link appears under that paper's journal line on its own. Nothing in
`index.html` needs to change — ever.

This works because every PDF link ships hidden and a short script at the bottom of
`index.html` asks the server whether the file exists before revealing it. A paper
that has not been uploaded yet simply shows no link, so the site never has a broken
link on it. The CV buttons work the same way.

### Adding a paper the site does not know about yet

If a new publication card is added to the Research section, give it a PDF slot by
pasting this just before that card's closing `</div>` in its `card-meta` line:

```html
<div class="pdf-link" data-pdf hidden style="margin-top:8px"><a href="papers/YEAR-short-name.pdf" class="pdf-a">PDF</a></div>
```

## Publishing with GitHub Pages

1. In this repo on GitHub: **Settings → Pages**.
2. **Source: Deploy from a branch**, branch `main`, folder `/ (root)`. Save.
3. A minute later the site is live at
   `https://<username>.github.io/smitasahaykausar/`.

### Using the smitasahaykausar.com domain

The footer and the social-preview tags already point at `smitasahaykausar.com`.
To make that real:

1. At the domain registrar, add these DNS records:
   - `A` records for `@` → `185.199.108.153`, `185.199.109.153`,
     `185.199.110.153`, `185.199.111.153`
   - `CNAME` for `www` → `<username>.github.io`
2. Add a file named `CNAME` at the root of this repo containing one line:
   `smitasahaykausar.com`
3. **Settings → Pages → Custom domain**, enter the domain, and tick
   **Enforce HTTPS** once the certificate is issued.

## Previewing locally

```sh
python3 -m http.server 8000
```

Then open `http://localhost:8000`. Use the server rather than double-clicking
`index.html` — the PDF links only reveal themselves over `http://`, not `file://`.

## Known issues

- The page scrolls sideways slightly on narrow phones (~390px). Several elements
  use `white-space: nowrap`, which forces the layout wider than the screen. This
  came over from the original design and is a styling fix, not a structural one.
