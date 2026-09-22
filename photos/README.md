# photos/

Full-size originals for the five-photo strip in About. The strip itself shows
the 520px square crops that come out of Claude Design; clicking one opens the
photo large. If the original is in this folder, that is what opens, uncropped.
If not, the square does. Nothing breaks either way.

The filename has to match the thumbnail exactly: all lowercase, `.jpg`.

| Photo | Filename |
|---|---|
| White Coat Ceremony | `white-coat-ceremony.jpg` |
| Hike to Silver Lake, Utah | `silver-lake-utah.jpg` |
| Frog pose in yoga class | `yoga.jpg` |
| Biking through Paris | `paris.jpg` |
| Rainbow Mountain, Peru | `rainbow-mountain-peru.jpg` |

A photo added to the strip in Claude Design takes the name `tools/unbundle.py`
gives it in `assets/img/`; its original goes here under that same name.

Before uploading:

- **Size.** About 2000px on the long side is plenty. A photo straight off a
  phone is 4-8 MB and loads slowly on a phone.
- **Location.** Phone photos carry the GPS position they were taken at. Strip
  it before posting anything taken near home.
- **Format.** Export HEIC as JPG; most browsers cannot show HEIC.

`tools/check_pdfs.py` (run by CI on every push) flags a file here whose name
will not be picked up, and names the one it should have.
