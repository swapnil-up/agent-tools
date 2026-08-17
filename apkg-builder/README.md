# Anki .apkg Builder

Generate Anki packages (.apkg) with embedded images from CSV or JSON data.

## Quick Start

```bash
# From pipe-delimited CSV: name|party|constituency|role|image_path
python apkg_builder.py --csv members.csv --output deck.apkg --deck-name "Nepal HoR MPs" --reverse

# From JSON
python apkg_builder.py --json members.json --output deck.apkg --reverse

# With images downloaded from URL pattern
python apkg_builder.py --csv members.csv --output deck.apkg \
    --image-url-pattern "https://example.com/photos/{name}.jpg"
```

## Input Formats

### CSV (pipe-delimited)

```
Name|Party|Constituency|Role|Image
Balen Shah|Rastriya Swatantra Party|Jhapa 5|Prime Minister|/path/to/photo.jpg
Dol Prasad Aryal|RSP|Kathmandu 9|Speaker|https://example.com/dol.jpg
```

### JSON

```json
[
    {
        "name": "Balen Shah",
        "party": "Rastriya Swatantra Party",
        "constituency": "Jhapa 5",
        "role": "Prime Minister",
        "image": "/path/to/photo.jpg"
    }
]
```

Image field can be:
- Local file path: `/path/to/photo.jpg`
- URL: `https://example.com/photo.jpg`
- Just filename (if images are pre-staged): `photo.jpg`

## Card Types

### Basic (default)
- **Front:** Name
- **Back:** Photo + Party + Constituency + Role

### Basic + Reverse (`--reverse`)
- **Card 1 Front:** Name → **Back:** Photo + Party + Constituency
- **Card 2 Front:** Photo + Party + Constituency → **Back:** Name

## Dependencies

```bash
pip install genanki
```

## Lessons Learned

See [LESSONS.md](LESSONS.md) for the full list of problems encountered and solutions found while building this tool.
