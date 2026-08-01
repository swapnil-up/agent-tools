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
import json
import sys
import tkinter as tk
from math import ceil

IMG = sys.argv[1]
DPI = float(sys.argv[2])
OUT = sys.argv[3] if len(sys.argv) > 3 else 'boxes.json'
SCALE_PX_TO_PT = 72.0 / DPI

root = tk.Tk()
root.title('Click and drag a box (repeat), press any key to save+quit')

img_tk = tk.PhotoImage(file=IMG)
w, h = img_tk.width(), img_tk.height()
sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
max_w, max_h = sw - 80, sh - 120
factor = max(1, ceil(max(w / max_w, h / max_h)))
disp_w, disp_h = w // factor, h // factor
if factor > 1:
    img_tk = img_tk.subsample(factor)
print(f"screen={sw}x{sh} img={w}x{h} display={disp_w}x{disp_h} factor={factor}")

canvas = tk.Canvas(root, width=disp_w, height=disp_h)
canvas.pack()
canvas.create_image(0, 0, anchor='nw', image=img_tk)
root.geometry(f'{disp_w}x{disp_h}')

boxes = []
rect_id = None
start = None


def on_click(e):
    global start, rect_id
    start = (e.x, e.y)
    if rect_id:
        canvas.delete(rect_id)


def on_drag(e):
    global rect_id
    if rect_id:
        canvas.delete(rect_id)
    rect_id = canvas.create_rectangle(start[0], start[1], e.x, e.y,
                                      outline='#00ff00', width=2)


def on_release(e):
    x1, y1 = start
    x2, y2 = e.x, e.y
    # display px -> original px: MULTIPLY by factor
    ox1, oy1 = x1 * factor, y1 * factor
    ox2, oy2 = x2 * factor, y2 * factor
    left, right = min(ox1, ox2), max(ox1, ox2)
    top, bottom = min(oy1, oy2), max(oy1, oy2)
    name = f'b{len(boxes) + 1}'
    boxes.append({
        'label': name,
        'px': [left, top, right, bottom],
        'pt': [round(left * SCALE_PX_TO_PT, 1), round(top * SCALE_PX_TO_PT, 1),
               round(right * SCALE_PX_TO_PT, 1), round(bottom * SCALE_PX_TO_PT, 1)],
    })
    canvas.create_text(left / factor + 4, top / factor + 2,
                       anchor='nw', text=name, fill='yellow',
                       font=('DejaVu Sans', 11, 'bold'))
    print(f'{name}: display=({x1},{y1})-({x2},{y2})  origpx=({left},{top})-({right},{bottom})  '
          f'pt=({boxes[-1]["pt"][0]},{boxes[-1]["pt"][1]})-'
          f'({boxes[-1]["pt"][2]},{boxes[-1]["pt"][3]})')


def on_key(e):
    data = {
        'image': IMG, 'dpi': DPI, 'px_per_pt': SCALE_PX_TO_PT,
        'factor': factor, 'boxes': boxes,
    }
    with open(OUT, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'Saved {len(boxes)} boxes to {OUT}')
    root.destroy()


canvas.bind('<ButtonPress-1>', on_click)
canvas.bind('<B1-Motion>', on_drag)
canvas.bind('<ButtonRelease-1>', on_release)
root.bind('<Key>', on_key)
root.mainloop()
