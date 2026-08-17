#!/usr/bin/env python3
"""
Anki .apkg deck builder with image support.

Generates Anki packages (.apkg) from CSV/JSON data with embedded images.
Uses genanki under the hood with the correct image handling pattern.

Usage:
    # From CSV (pipe-delimited): name|party|constituency|role|image_path
    python apkg_builder.py --csv members.csv --output deck.apkg --deck-name "My Deck"

    # From JSON
    python apkg_builder.py --json members.json --output deck.apkg

    # With image download from API
    python apkg_builder.py --csv members.csv --image-url-pattern "https://example.com/photos/{name}.jpg" --output deck.apkg

    # Two-way cards (basic and reverse)
    python apkg_builder.py --csv members.csv --output deck.apkg --reverse

CSV columns (pipe-delimited):
    name | party | constituency | role | image_path_or_url

JSON format:
    [
        {"name": "John Doe", "party": "Party A", "constituency": "District 1", "role": "MP", "image": "path/to/photo.jpg"},
        ...
    ]
"""

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.request
import ssl
from pathlib import Path
from typing import Optional

try:
    import genanki
except ImportError:
    print("Error: genanki not installed. Run: pip install genanki", file=sys.stderr)
    sys.exit(1)


# Stable IDs for model and deck (derived from name)
def make_id(name: str) -> int:
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def create_model(deck_name: str, reverse: bool = False) -> genanki.Model:
    """Create an Anki model with proper image support."""
    model_id = make_id(f"{deck_name}-model")

    fields = [
        {'name': 'Name'},
        {'name': 'Photo'},
        {'name': 'Party'},
        {'name': 'Constituency'},
        {'name': 'Role'},
    ]

    templates = [
        {
            'name': 'Card 1',
            'qfmt': '<div style="text-align:center; font-size:24px;">{{Name}}</div>',
            'afmt': '{{FrontSide}}<hr id="answer"><div style="text-align:center;">{{Photo}}<br><b>{{Party}}</b><br>{{Constituency}}{{#Role}}<br><i>{{Role}}</i>{{/Role}}</div>',
        },
    ]

    if reverse:
        templates.append({
            'name': 'Card 2',
            'qfmt': '<div style="text-align:center;">{{Photo}}<br><b>{{Party}}</b><br>{{Constituency}}</div>',
            'afmt': '{{FrontSide}}<hr id="answer"><div style="text-align:center; font-size:24px;">{{Name}}{{#Role}}<br><i>{{Role}}</i>{{/Role}}</div>',
        })

    return genanki.Model(
        model_id,
        f'{deck_name} Model',
        fields=fields,
        templates=templates,
        css='.card { font-family: arial; text-align: center; }'
    )


def create_deck(deck_name: str) -> genanki.Deck:
    """Create an Anki deck."""
    deck_id = make_id(f"{deck_name}-deck")
    return genanki.Deck(deck_id, deck_name)


def resolve_image(image_ref: str, tmp_dir: str, image_url_pattern: Optional[str] = None) -> Optional[str]:
    """
    Resolve an image reference to a local file.
    
    Returns the local filename (for the note field) or None.
    Copies the image to tmp_dir.
    """
    if not image_ref:
        return None

    # If it's a URL, download it
    if image_ref.startswith(('http://', 'https://')):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            # Extract filename from URL
            url_path = image_ref.split('?')[0]
            ext = url_path.split('.')[-1] if '.' in url_path.split('/')[-1] else 'jpg'
            safe_name = hashlib.md5(image_ref.encode()).hexdigest()[:12]
            local_filename = f"{safe_name}.{ext}"
            dst_path = os.path.join(tmp_dir, local_filename)

            req = urllib.request.Request(image_ref, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx) as response:
                with open(dst_path, 'wb') as f:
                    f.write(response.read())

            return local_filename
        except Exception as e:
            print(f"  Warning: Failed to download {image_ref}: {e}", file=sys.stderr)
            return None

    # If it's a local file path, copy it
    if os.path.exists(image_ref):
        ext = image_ref.split('.')[-1]
        safe_name = os.path.basename(image_ref).replace(' ', '_')
        dst_path = os.path.join(tmp_dir, safe_name)
        shutil.copy2(image_ref, dst_path)
        return safe_name

    # If it's just a filename, assume it exists in the image directory
    return image_ref


def load_csv(csv_path: str) -> list:
    """Load members from a pipe-delimited CSV file."""
    members = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        for row in reader:
            if len(row) < 4:
                continue
            name = row[0].strip()
            party = row[1].strip()
            constituency = row[2].strip()
            role = row[3].strip() if len(row) > 3 else ''
            image = row[4].strip() if len(row) > 4 else ''
            members.append({
                'name': name,
                'party': party,
                'constituency': constituency,
                'role': role,
                'image': image,
            })
    return members


def load_json(json_path: str) -> list:
    """Load members from a JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict) and 'members' in data:
        data = data['members']

    members = []
    for item in data:
        members.append({
            'name': item.get('name', ''),
            'party': item.get('party', ''),
            'constituency': item.get('constituency', ''),
            'role': item.get('role', ''),
            'image': item.get('image', item.get('photo', item.get('image_path', ''))),
        })
    return members


def build_deck(
    members: list,
    deck_name: str,
    output_path: str,
    reverse: bool = False,
    image_url_pattern: Optional[str] = None,
):
    """Build an .apkg file from member data."""
    model = create_model(deck_name, reverse)
    deck = create_deck(deck_name)

    tmp_img_dir = tempfile.mkdtemp(prefix='apkg_images_')
    media_files = []

    print(f"Processing {len(members)} members...")

    for i, member in enumerate(members):
        name = member['name']
        party = member['party']
        constituency = member['constituency']
        role = member.get('role', '')
        image_ref = member.get('image', '')

        # Apply URL pattern if provided
        if image_url_pattern and not image_ref:
            safe_name = name.replace(' ', '_').replace('.', '').replace(',', '')
            image_ref = image_url_pattern.format(name=safe_name, name_lower=safe_name.lower())

        # Resolve image
        photo_field = ''
        if image_ref:
            local_filename = resolve_image(image_ref, tmp_img_dir, image_url_pattern)
            if local_filename:
                # IMPORTANT: Field contains the full <img> tag, not just filename
                photo_field = f'<img src="{local_filename}" width="200">'
                media_files.append(os.path.join(tmp_img_dir, local_filename))

        # Create note
        note = genanki.Note(
            model=model,
            fields=[name, photo_field, party, constituency, role]
        )
        deck.add_note(note)

        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(members)}")

    # Build package
    package = genanki.Package(deck)
    package.media_files = media_files
    package.write_to_file(output_path)

    # Cleanup
    shutil.rmtree(tmp_img_dir, ignore_errors=True)

    print(f"Created: {output_path}")
    print(f"  Cards: {len(members)}" + (" (x2 with reverse)" if reverse else ""))
    print(f"  Images: {len([m for m in members if m.get('image')])}")
    print(f"  Size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Build Anki .apkg decks with image support',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--csv', help='Input CSV file (pipe-delimited)')
    parser.add_argument('--json', help='Input JSON file')
    parser.add_argument('--output', '-o', required=True, help='Output .apkg file path')
    parser.add_argument('--deck-name', default='My Deck', help='Name of the Anki deck')
    parser.add_argument('--reverse', action='store_true', help='Generate reverse cards (basic and reversed)')
    parser.add_argument('--image-url-pattern', help='URL pattern for images, e.g. https://example.com/{name}.jpg')

    args = parser.parse_args()

    if not args.csv and not args.json:
        parser.error("Must provide either --csv or --json")

    # Load data
    if args.csv:
        members = load_csv(args.csv)
    else:
        members = load_json(args.json)

    if not members:
        print("Error: No members found in input", file=sys.stderr)
        sys.exit(1)

    # Build deck
    build_deck(
        members=members,
        deck_name=args.deck_name,
        output_path=args.output,
        reverse=args.reverse,
        image_url_pattern=args.image_url_pattern,
    )


if __name__ == '__main__':
    main()
