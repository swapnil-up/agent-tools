#!/usr/bin/env python3
"""
Markdown → EPUB builder with a working table of contents.

Converts a Markdown document to a phone-readable EPUB. The key trick that makes
headings show up in the reader's TOC: render Markdown to HTML with the Python
`markdown` library, then hand the HTML to calibre's `ebook-convert` and tell it
which heading levels form the TOC. Feeding the .md directly to `ebook-convert`
produces an EPUB whose TOC has no chapter entries.

Usage:
    python epub_builder.py input.md
    python epub_builder.py input.md --output out.epub
    python epub_builder.py input.md --title "My Book" --author "Me"
    python epub_builder.py input.md --toc-levels 2 3   # use h2/h3 as TOC entries

Dependencies:
    - Python: pip install markdown
    - calibre: ebook-convert (apt install calibre, or from calibre-ebook.com)

Exit code is 0 on success, 1 on any error (missing input, missing deps).
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def markdown_to_html(md_path: Path, title: str, author: str) -> str:
    """Render a Markdown file to a standalone HTML document."""
    try:
        import markdown
    except ImportError:
        print("Error: python 'markdown' package not installed.", file=sys.stderr)
        print("Run: pip install markdown", file=sys.stderr)
        sys.exit(1)

    body = markdown.markdown(
        md_path.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "toc"],
    )
    title_escaped = title.replace("&", "&amp;").replace("<", "&lt;")
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title_escaped}</title>
</head>
<body>
{body}
</body>
</html>"""


def build_epub(
    html_path: Path,
    output_path: Path,
    title: str,
    author: str,
    toc_levels: list,
) -> None:
    """Run ebook-convert on an HTML file, mapping heading levels to the TOC."""
    if not shutil.which("ebook-convert"):
        print("Error: 'ebook-convert' (calibre) not found on PATH.", file=sys.stderr)
        print("Install calibre: https://calibre-ebook.com/download", file=sys.stderr)
        sys.exit(1)

    cmd = ["ebook-convert", str(html_path), str(output_path)]
    for i, level in enumerate(toc_levels, start=1):
        cmd.append(f"--level{i}-toc=//h:h{level}")
    if author:
        cmd += ["--authors", author]
    if title:
        cmd += ["--title", title]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ebook-convert failed:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Build a phone-friendly EPUB from Markdown with a working TOC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="Input .md file")
    parser.add_argument("--output", "-o", help="Output .epub path (default: <input>.epub)")
    parser.add_argument("--title", help="Book title (default: from first heading or filename)")
    parser.add_argument("--author", help="Book author (optional)")
    parser.add_argument(
        "--toc-levels",
        nargs="+",
        type=int,
        default=[2, 3],
        help="Heading levels that become TOC entries (default: 2 3)",
    )
    args = parser.parse_args()

    md_path = Path(args.input)
    if not md_path.exists():
        print(f"Error: input file not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    title = args.title or md_path.stem.replace("-", " ").replace("_", " ").title()
    output_path = Path(args.output) if args.output else md_path.with_suffix(".epub")

    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "document.html"
        html_path.write_text(
            markdown_to_html(md_path, title=title, author=args.author or ""),
            encoding="utf-8",
        )
        build_epub(
            html_path=html_path,
            output_path=output_path,
            title=title,
            author=args.author or "",
            toc_levels=args.toc_levels,
        )

    print(f"EPUB written to {output_path}")


if __name__ == "__main__":
    main()