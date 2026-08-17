#!/usr/bin/env python3
"""
Nepal House of Representatives MP deck builder.

Fetches MP data and photos from the Nepal Parliament API and generates
an Anki deck with basic + reverse cards.

Usage:
    python nepal_hor.py --output nepal_hoR_mps.apkg

API: https://hr.parliament.gov.np/api/v1/members
"""

import argparse
import csv
import json
import os
import shutil
import ssl
import sys
import tempfile
import urllib.request
from pathlib import Path

try:
    import genanki
except ImportError:
    print("Error: genanki not installed. Run: pip install genanki", file=sys.stderr)
    sys.exit(1)


# Stable IDs
def make_id(name: str) -> int:
    import hashlib
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


API_URL = "https://hr.parliament.gov.np/api/v1/members?member_type=member&frontend_member_search=true&limit=300"
IMAGE_BASE = "https://hr.parliament.gov.np/uploads/images/"


def fetch_members():
    """Fetch all MPs from the Nepal Parliament API."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(API_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx) as response:
        data = json.loads(response.read())

    members = []
    for m in data['data']['data']:
        translations = m.get('parliament_member_translations', [])
        if not translations:
            continue

        name = translations[0].get('name', '')
        designation = translations[0].get('designation', '')

        party = m.get('political_party', {})
        party_name = party.get('party_name_en', '') if party else ''

        district = m.get('district', {})
        district_name = district.get('name_en', '') if district else ''

        election_area = m.get('election_area_no', 0)
        election_type = m.get('election_type', {})
        election_type_name = election_type.get('election_type_en', '') if election_type else ''

        if election_type_name == 'Direct' and district_name:
            constituency = f'{district_name} {election_area}'
        else:
            constituency = 'PR'

        member_type = m.get('member_type', '')
        if member_type == 'speaker':
            role = 'Speaker of the House'
        elif member_type == 'deputy_speaker':
            role = 'Deputy Speaker'
        elif designation:
            role = designation
        else:
            role = ''

        images = m.get('images', {})
        img_data = images.get('images', {})
        img_name = img_data.get('original', '')
        image_url = f'{IMAGE_BASE}{img_name}' if img_name else ''

        members.append({
            'name': name,
            'party': party_name,
            'constituency': constituency,
            'role': role,
            'image': image_url,
        })

    return members


def build_deck(members, output_path):
    """Build Anki deck from member data."""
    model = genanki.Model(
        make_id('nepal-hor-model'),
        'Nepal HoR MP',
        fields=[
            {'name': 'Name'},
            {'name': 'Photo'},
            {'name': 'Party'},
            {'name': 'Constituency'},
            {'name': 'Role'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': '<div style="text-align:center; font-size:24px;">{{Name}}</div>',
                'afmt': '{{FrontSide}}<hr id="answer"><div style="text-align:center;">{{Photo}}<br><b>{{Party}}</b><br>{{Constituency}}{{#Role}}<br><i>{{Role}}</i>{{/Role}}</div>',
            },
            {
                'name': 'Card 2',
                'qfmt': '<div style="text-align:center;">{{Photo}}<br><b>{{Party}}</b><br>{{Constituency}}</div>',
                'afmt': '{{FrontSide}}<hr id="answer"><div style="text-align:center; font-size:24px;">{{Name}}{{#Role}}<br><i>{{Role}}</i>{{/Role}}</div>',
            },
        ],
        css='.card { font-family: arial; text-align: center; }'
    )

    deck = genanki.Deck(make_id('nepal-hor-deck'), 'Nepal HoR MPs')

    tmp_img_dir = tempfile.mkdtemp(prefix='nepal_mp_')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    media_files = []
    downloaded = 0
    failed = 0

    print(f"Processing {len(members)} members...")

    for i, member in enumerate(members):
        name = member['name']
        image_url = member['image']

        photo_field = ''
        if image_url:
            try:
                safe_name = name.replace(' ', '_').replace('.', '').replace(',', '')
                ext = image_url.split('.')[-1].split('?')[0]
                local_filename = f'{safe_name}.{ext}'
                dst_path = os.path.join(tmp_img_dir, local_filename)

                req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, context=ctx) as response:
                    with open(dst_path, 'wb') as f:
                        f.write(response.read())

                photo_field = f'<img src="{local_filename}" width="200">'
                media_files.append(dst_path)
                downloaded += 1
            except Exception as e:
                print(f"  Warning: Failed to download image for {name}: {e}", file=sys.stderr)
                failed += 1
        else:
            failed += 1

        note = genanki.Note(
            model=model,
            fields=[name, photo_field, member['party'], member['constituency'], member['role']]
        )
        deck.add_note(note)

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/{len(members)} (downloaded: {downloaded}, failed: {failed})")

    package = genanki.Package(deck)
    package.media_files = media_files
    package.write_to_file(output_path)

    shutil.rmtree(tmp_img_dir, ignore_errors=True)

    print(f"\nCreated: {output_path}")
    print(f"  Cards: {len(members)} (x2 with reverse)")
    print(f"  Images: {downloaded} downloaded, {failed} failed")
    print(f"  Size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")


def main():
    parser = argparse.ArgumentParser(description='Build Nepal HoR MP Anki deck')
    parser.add_argument('--output', '-o', default='nepal_hoR_mps.apkg', help='Output .apkg file')
    parser.add_argument('--csv', help='Also export raw CSV data')
    args = parser.parse_args()

    print("Fetching MP data from Nepal Parliament API...")
    members = fetch_members()
    print(f"Found {len(members)} members")

    if args.csv:
        with open(args.csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'party', 'constituency', 'role', 'image'], delimiter='|')
            writer.writeheader()
            writer.writerows(members)
        print(f"CSV exported to {args.csv}")

    build_deck(members, args.output)


if __name__ == '__main__':
    main()
