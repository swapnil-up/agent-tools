#!/usr/bin/env python3
"""Draw saved boxes back onto the original image for visual verification.

The marker tool (mark_boxes.py) stores box coordinates in original-image
pixels ('px'). This draws those boxes onto the SAME image the user marked, so
the overlay exactly matches what they pointed at (no dpi/pt round-trip).

Usage: overlay_boxes.py <image.png> <boxes.json> [out.png]

Mirrors racps/invitation-generator: keep everything in original pixel space.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from util import require_module, require_file

Image = require_module('PIL.Image', 'Pillow')
ImageDraw = require_module('PIL.ImageDraw', 'Pillow')

COLORS = ['#ff0000', '#ff8800', '#ffff00', '#00ff00', '#00ffff',
          '#4488ff', '#ff44ff', '#ff4488', '#88ff44', '#44ff88',
          '#aa44ff', '#44aaff']


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Draw saved boxes onto the original image for verification',
    )
    parser.add_argument('image', help='Path to the original image')
    parser.add_argument('boxes', help='Path to the boxes JSON file')
    parser.add_argument('-o', '--output', default='overlay.png',
                        help='Output image path (default: overlay.png)')
    args = parser.parse_args(argv)

    require_file(args.image, 'image file')
    require_file(args.boxes, 'boxes JSON')

    img = Image.open(args.image).convert('RGB')
    draw = ImageDraw.Draw(img)
    data = json.load(open(args.boxes))
    boxes = data['boxes'] if isinstance(data, dict) and 'boxes' in data else data
    for i, b in enumerate(boxes):
        left, top, right, bottom = b['px']
        label = b.get('label', f'b{i+1}')
        color = COLORS[i % len(COLORS)]
        draw.rectangle([left, top, right, bottom], outline=color, width=3)
        draw.text((left + 6, top + 2), label, fill=color)
    img.save(args.output)
    print(f'{len(boxes)} boxes drawn on {args.image} (orig px) -> {args.output} ({img.size[0]}x{img.size[1]})')


if __name__ == '__main__':
    main()
