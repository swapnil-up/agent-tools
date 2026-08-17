# Markdown → EPUB Builder

Convert a Markdown document into a phone-readable EPUB **with a working table
of contents** (chapter/subsection headings visible in the reader's TOC panel).

## Quick Start

```bash
python epub_builder.py notes.md
python epub_builder.py notes.md -o out.epub --title "My Book" --author "Me"
python epub_builder.py notes.md --toc-levels 2 3   # h2/h3 become TOC entries
```

Output defaults to `<input>.epub` next to the source file.

## Why this tool exists

Feeding a `.md` file straight into `ebook-convert` produces an EPUB whose TOC is
empty (no chapters). The reliable recipe is:

1. Render the Markdown to HTML with the Python `markdown` library
   (`tables`, `fenced_code`, `toc` extensions).
2. Give that HTML to `ebook-convert` and explicitly map heading levels to the
   TOC: `--level1-toc=//h:h2 --level2-toc=//h:h3`.

The script wraps both steps so you get headings that actually navigate.

## Dependencies

```bash
pip install markdown
# calibre (provides ebook-convert):
#   apt install calibre   or   https://calibre-ebook.com/download
```

## Options

| Flag | Default | Purpose |
|---|---|---|
| `input` | — | Markdown file to convert (positional) |
| `--output`, `-o` | `<input>.epub` | Output EPUB path |
| `--title` | derived from filename | Book title |
| `--author` | empty | Book author |
| `--toc-levels` | `2 3` | Heading levels used as TOC entries (space-separated ints) |

## Lessons Learned

See [LESSONS.md](LESSONS.md) for the TOC/encoding pitfalls encountered and how
this tool avoids them.