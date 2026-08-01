#!/usr/bin/env python3
"""Draw saved boxes back onto the original image for visual verification.

The marker tool (mark_boxes.py) stores box coordinates in original-image
pixels ('px'). This draws those boxes onto the SAME image the user marked, so
the overlay exactly matches what they pointed at (no dpi/pt round-trip).

Usage: overlay_boxes.py <image.png> <boxes.json> [out.png]

Mirrors racps/invitation-generator: keep everything in original pixel space.
"""
import json
import sys
from PIL import Image, ImageDraw

IMG = sys.argv[1]
BOXES = sys.argv[2]
OUT = sys.argv[3] if len(sys.argv) > 3 else 'overlay.png'
COLORS = ['#ff0000', '#ff8800', '#ffff00', '#00ff00', '#00ffff',
          '#4488ff', '#ff44ff', '#ff4488', '#88ff44', '#44ff88',
          '#aa44ff', '#44aaff']


def main():
    img = Image.open(IMG).convert('RGB')
    draw = ImageDraw.Draw(img)
    data = json.load(open(BOXES))
    boxes = data['boxes'] if isinstance(data, dict) and 'boxes' in data else data
    for i, b in enumerate(boxes):
        left, top, right, bottom = b['px']
        label = b.get('label', f'b{i+1}')
        color = COLORS[i % len(COLORS)]
        draw.rectangle([left, top, right, bottom], outline=color, width=3)
        draw.text((left + 6, top + 2), label, fill=color)
    img.save(OUT)
    print(f'{len(boxes)} boxes drawn on {IMG} (orig px) -> {OUT} ({img.size[0]}x{img.size[1]})')


if __name__ == '__main__':
    main()
