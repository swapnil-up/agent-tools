#!/usr/bin/env python3
"""Mark boxes on an image, save original-pixel + pt coords, quit on any key.

Scaling model (mirrors racps/invitation-generator/pick_rect.py):
  - subsample the image by integer `factor` so it fits the screen:
        disp = img.subsample(factor)   -> width = w // factor
  - the actual factor used is `factor = w // disp_w` (rounding-safe)
  - mapping display px -> original px is a MULTIPLY by that factor:
        orig_px = display_px * factor
  - pt = orig_px * (72 / dpi)

Usage: mark_boxes.py <image.png> <dpi> [out.json]
  - Click and drag to draw a box. Every drag-release appends a box;
    boxes are auto-named b1, b2, ... in order.
  - Press ANY key to save and quit.
"""
import argparse
import json
import sys
from math import ceil


def compute_box(display_coords, box_number, factor, scale_px_to_pt):
    """Convert display-pixel drag coords to original-pixel + pt coords.

    Args:
        display_coords: (x1, y1, x2, y2) in display pixels
        box_number: 1-based index for the label
        factor: integer subsample factor (orig = display * factor)
        scale_px_to_pt: 72.0 / dpi

    Returns:
        dict with 'label', 'px', 'pt' keys
    """
    x1, y1, x2, y2 = display_coords
    ox1, oy1 = x1 * factor, y1 * factor
    ox2, oy2 = x2 * factor, y2 * factor
    left, right = min(ox1, ox2), max(ox1, ox2)
    top, bottom = min(oy1, oy2), max(oy1, oy2)
    return {
        'label': f'b{box_number}',
        'px': [left, top, right, bottom],
        'pt': [round(left * scale_px_to_pt, 1), round(top * scale_px_to_pt, 1),
               round(right * scale_px_to_pt, 1), round(bottom * scale_px_to_pt, 1)],
    }


def compute_factor(img_w, img_h, max_w, max_h):
    """Compute the integer subsample factor to fit image on screen."""
    return max(1, ceil(max(img_w / max_w, img_h / max_h)))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Mark boxes on an image, save coordinates for agent consumption',
    )
    parser.add_argument('image', help='Path to the image file (PNG)')
    parser.add_argument('dpi', type=float, help='DPI of the image')
    parser.add_argument('-o', '--output', default='boxes.json',
                        help='Output JSON path (default: boxes.json)')
    args = parser.parse_args(argv)

    try:
        import tkinter as tk
    except ImportError:
        print('Error: tkinter not available.', file=sys.stderr)
        print('Install: apt install python3-tk (Debian/Ubuntu)', file=sys.stderr)
        sys.exit(1)

    from pathlib import Path
    img_path = Path(args.image)
    if not img_path.exists():
        print(f'Error: image not found: {img_path}', file=sys.stderr)
        sys.exit(1)
    if args.dpi <= 0:
        print('Error: dpi must be positive', file=sys.stderr)
        sys.exit(1)

    dpi = args.dpi
    out = args.output
    scale_px_to_pt = 72.0 / dpi

    root = tk.Tk()
    root.title('Click and drag a box (repeat), press any key to save+quit')

    img_tk = tk.PhotoImage(file=str(img_path))
    w, h = img_tk.width(), img_tk.height()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    max_w, max_h = sw - 80, sh - 120
    factor = compute_factor(w, h, max_w, max_h)
    disp_w, disp_h = w // factor, h // factor
    if factor > 1:
        img_tk = img_tk.subsample(factor)
    print(f'screen={sw}x{sh} img={w}x{h} display={disp_w}x{disp_h} factor={factor}')

    canvas = tk.Canvas(root, width=disp_w, height=disp_h)
    canvas.pack()
    canvas.create_image(0, 0, anchor='nw', image=img_tk)
    root.geometry(f'{disp_w}x{disp_h}')

    boxes = []
    rect_id = None
    start = None

    def on_click(e):
        nonlocal start, rect_id
        start = (e.x, e.y)
        if rect_id:
            canvas.delete(rect_id)

    def on_drag(e):
        nonlocal rect_id
        if rect_id:
            canvas.delete(rect_id)
        rect_id = canvas.create_rectangle(start[0], start[1], e.x, e.y,
                                          outline='#00ff00', width=2)

    def on_release(e):
        nonlocal rect_id
        box = compute_box((start[0], start[1], e.x, e.y),
                          len(boxes) + 1, factor, scale_px_to_pt)
        boxes.append(box)
        rect_id = None
        left, top = box['px'][0], box['px'][1]
        canvas.create_text(left / factor + 4, top / factor + 2,
                           anchor='nw', text=box['label'], fill='yellow',
                           font=('DejaVu Sans', 11, 'bold'))
        print(f'{box["label"]}: display=({start[0]},{start[1]})-({e.x},{e.y})  '
              f'origpx=({box["px"][0]},{box["px"][1]})-({box["px"][2]},{box["px"][3]})  '
              f'pt=({box["pt"][0]},{box["pt"][1]})-({box["pt"][2]},{box["pt"][3]})')

    def on_key(e):
        data = {
            'image': str(img_path), 'dpi': dpi, 'px_per_pt': scale_px_to_pt,
            'factor': factor, 'boxes': boxes,
        }
        with open(out, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f'Saved {len(boxes)} boxes to {out}')
        root.destroy()

    canvas.bind('<ButtonPress-1>', on_click)
    canvas.bind('<B1-Motion>', on_drag)
    canvas.bind('<ButtonRelease-1>', on_release)
    root.bind('<Key>', on_key)
    root.mainloop()


if __name__ == '__main__':
    main()
