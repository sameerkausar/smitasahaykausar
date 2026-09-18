# posters/

Posters, conference abstracts and slide decks — the presentations Smita made
herself. **These are hers, so anything here can go up**, unlike the manuscripts in
`../papers/`, which are governed by each journal's licence.

Drop a PDF in and the matching row in **Talks and Posters** becomes clickable: it
opens full screen over the site, so a reviewer reads the poster without being sent
anywhere else. Nothing in `index.html` changes.

## How to add one

1. Find the row's filename in [`../tools/documents.json`](../tools/documents.json)
   under `posters` — the `slug`, plus `.pdf`.
2. Put the file here with exactly that name.
3. Commit.

Then run `python3 ../tools/check_pdfs.py` (or just let CI do it) — a filename that
does not match is the one mistake that fails silently, so the check exists to name
it for you.

All 21 presentations on the page already have a slot. Fill in whichever you have;
a row with no file shows nothing at all, so there is never a dead link.

## A note on scans

A poster photographed or scanned to PDF works, but a PDF exported straight from
PowerPoint, Illustrator or Keynote stays sharp when zoomed and is usually a much
smaller file. Prefer the export where you still have the original.

Large-format posters are often 30-60MB. GitHub warns over 50MB and refuses over
100MB, and a reviewer on hotel wifi has to download the whole thing before seeing
anything. If one is very large, export it again at screen resolution (150 dpi is
plenty) before committing.
