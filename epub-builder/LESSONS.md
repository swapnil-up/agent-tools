# Lessons Learned: Building EPUBs from Markdown

Problems encountered while converting Markdown compendiums to phone-readable EPUBs, and the solutions the epub-builder encodes.

## Problem 1: No TOC entries when converting .md directly

**Symptom:** `ebook-convert input.md output.epub` succeeds, but the resulting EPUB's table of contents has no chapter entries. Verifying with `grep -c navPoint toc.ncx` shows only 2 entries ("index" + "Start").

**Root Cause:** calibre's Markdown input reader doesn't reliably map Markdown headings into EPUB TOC navigation points. The EPUB ends up as one undifferentiated text blob.

**Solution:** Convert the Markdown to HTML first with the Python `markdown` library, then feed the HTML to `ebook-convert` and pass explicit TOC mappings:
```bash
ebook-convert doc.html out.epub --level1-toc='//h:h2' --level2-toc='//h:h3'
```
This yields `navPoint` entries for every h2 (and h3) heading. Verified: 60 navPoints for a document that previously had 2.

---

## Problem 2: Default cover uses the filename as the title

**Symptom:** The generated cover page shows `anushka-shrestha-compendium` (with dashes) instead of a clean title.

**Root Cause:** With no `--title`, `ebook-convert` derives the title from the filename.

**Solution:** Pass `--title` (the epub-builder defaults it to a prettified stem: dashes/underscores → spaces, title-cased) and `--authors` when known.

---

## Problem 3: "Invalid profile" for phone output

**Symptom:** `--output-profile=phone` is rejected: `invalid choice: 'phone'`.

**Root Cause:** calibre has no "phone" profile; the closest options are the `tablet`, `galaxy`, or `kindle` profiles, but for EPUB the default profile already reflows cleanly on phones.

**Solution:** Omit `--output-profile` entirely. EPUB is reflowable text — readers handle phone rendering themselves. The important fix was the TOC, not the page profile.

---

## Problem 4: Malformed HTML breaks the conversion

**Symptom:** If a raw HTML fragment is passed through, `ebook-convert` may fail or produce broken output.

**Root Cause:** Unescaped `<`, `&`, etc. in title or content.

**Solution:** Escape the title (`&` → `&amp;`, `<` → `&lt;`) before injecting it into the HTML wrapper, and let the `markdown` library escape body content.

---

## Problem 5: Missing `ebook-convert` or `markdown`

**Symptom:** `Error: 'ebook-convert' (calibre) not found` or `ModuleNotFoundError: No module named 'markdown'`.

**Solution:** The tool fails with a clear message and exit code 1 naming the exact dependency and install command, so a future agent knows immediately what to install rather than debugging a vague traceback.

---

## Verification recipe

After building, confirm the TOC actually has entries:
```bash
unzip -o -q out.epub -d /tmp/verify && grep -c navPoint /tmp/verify/toc.ncx
```
Should be > 2 when the source has headings. (The default EPUB split may use `toc.ncx` or EPUB3 `nav.xhtml`; check both.)

## References

- [calibre ebook-convert documentation](https://manual.calibre-ebook.com/conversion.html)
- [Python-Markdown](https://python-markdown.github.io/)