# mark-boxes

Let the user (or you) visually mark rectangles on an image and save their
coordinates for the agent to consume. The agent cannot view images, so this
is how it gets you to point at things on screen.

Scaling model (mirrors `racps/invitation-generator/pick_rect.py`):
- subsample the image by an integer `factor` so it fits the screen
  (`disp = img.subsample(factor)`, display width `= w // factor`)
- the actual factor is `factor = max(1, ceil(max(w/max_w, h/max_h)))`
- mapping display px -> original px is a **multiply** by that factor
  (`orig_px = display_px * factor`)
- `pt = orig_px * (72 / dpi)`

## Usage

```
python3 mark_boxes.py <image.png> <dpi> [out.json]
```

- Click and drag to draw a box. Each drag-release appends a box; boxes are
  auto-named `b1, b2, ...` in order.
- Press **any key** to save and quit. Output JSON contains the image path,
  dpi, `px_per_pt`, `factor`, and the `boxes` list (each with `label`, `px`
  in original pixels, and `pt` coordinates).

## Output format

```json
{
  "image": "page17-clean.png",
  "dpi": 200,
  "px_per_pt": 0.36,
  "factor": 2,
  "boxes": [
    { "label": "b1", "px": [108, 180, 800, 286], "pt": [38.9, 64.8, 288.0, 103.0] }
  ]
}
```

## Requirements

- `mark_boxes.py`: Python 3 + tkinter (included with most distro python3
  packages; on Debian install `python3-tk`).
- `overlay_boxes.py`: Python 3 + Pillow.

## Notes

- Images must be PNG; Tk's `PhotoImage` cannot read JPEGs.
- The window is sized to the subsampled image; a window manager that stretches
  windows (e.g. i3 tiling) can misalign coordinates, so the script forces
  `root.geometry()` to the exact display size.
- To verify the round-trip, run `overlay_boxes.py`: it draws the boxes onto the
  SAME image the user marked, using the stored original-pixel `px` values, so
  the overlay exactly matches what was pointed at (no dpi/pt round-trip).
