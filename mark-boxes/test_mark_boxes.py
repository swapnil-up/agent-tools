#!/usr/bin/env python3
"""Tests for mark-boxes: coordinate math + CLI edge cases."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from mark_boxes import compute_box, compute_factor


# ---------------------------------------------------------------------------
# compute_box: pure coordinate math
# ---------------------------------------------------------------------------

class TestComputeBox:
    def test_identity(self):
        """factor=1, scale=1.0 → px == display coords"""
        box = compute_box((10, 20, 100, 200), box_number=1, factor=1, scale_px_to_pt=1.0)
        assert box['label'] == 'b1'
        assert box['px'] == [10, 20, 100, 200]
        assert box['pt'] == [10.0, 20.0, 100.0, 200.0]

    def test_scaled_factor(self):
        """factor=2 → original px = display * 2"""
        box = compute_box((10, 20, 100, 200), box_number=1, factor=2, scale_px_to_pt=1.0)
        assert box['px'] == [20, 40, 200, 400]

    def test_pt_conversion(self):
        """pt = px * (72 / dpi). For dpi=200, scale=0.36"""
        scale = 72.0 / 200
        box = compute_box((0, 0, 100, 100), box_number=1, factor=1, scale_px_to_pt=scale)
        assert box['pt'] == [0.0, 0.0, 36.0, 36.0]

    def test_pt_rounding(self):
        """pt values are rounded to 1 decimal"""
        scale = 72.0 / 300  # 0.24
        box = compute_box((0, 0, 10, 10), box_number=1, factor=1, scale_px_to_pt=scale)
        # 10 * 0.24 = 2.4
        assert box['pt'] == [0.0, 0.0, 2.4, 2.4]

    def test_labels_sequential(self):
        """Boxes get labels b1, b2, b3..."""
        for n in [1, 2, 3, 10]:
            box = compute_box((0, 0, 1, 1), box_number=n, factor=1, scale_px_to_pt=1.0)
            assert box['label'] == f'b{n}'

    def test_drag_upleft(self):
        """Dragging up-left still produces [left, top, right, bottom] in order"""
        box = compute_box((100, 100, 10, 10), box_number=1, factor=1, scale_px_to_pt=1.0)
        assert box['px'] == [10, 10, 100, 100]

    def test_scaled_and_pt(self):
        """factor=2, dpi=100 → px doubled, pt = display * 2 * (72/100)"""
        scale = 72.0 / 100
        box = compute_box((50, 50, 150, 200), box_number=2, factor=2, scale_px_to_pt=scale)
        assert box['px'] == [100, 100, 300, 400]
        assert box['pt'] == [72.0, 72.0, 216.0, 288.0]


# ---------------------------------------------------------------------------
# compute_factor
# ---------------------------------------------------------------------------

class TestComputeFactor:
    def test_small_image(self):
        """Image fits on screen → factor=1"""
        assert compute_factor(800, 600, 1920, 1080) == 1

    def test_large_image(self):
        """Image larger than screen → factor > 1"""
        f = compute_factor(3840, 2160, 1920, 1080)
        assert f == 2

    def test_very_large(self):
        """Very large image → factor scales down"""
        f = compute_factor(7680, 4320, 1920, 1080)
        assert f == 4

    def test_one_dimension_large(self):
        """Only width is too large"""
        f = compute_factor(3840, 600, 1920, 1080)
        assert f == 2


# ---------------------------------------------------------------------------
# CLI: argument parsing via subprocess
# ---------------------------------------------------------------------------

MARK_BOXES = str(Path(__file__).parent / 'mark_boxes.py')


class TestCLI:
    def test_no_args(self):
        """No args → exit code 2 (argparse error)"""
        result = subprocess.run([sys.executable, MARK_BOXES],
                                capture_output=True, text=True)
        assert result.returncode == 2
        assert 'required' in result.stderr.lower() or 'arguments' in result.stderr.lower()

    def test_missing_image(self):
        """Non-existent image → exit code 1"""
        result = subprocess.run([sys.executable, MARK_BOXES, '/tmp/no_such_file.png', '300'],
                                capture_output=True, text=True)
        assert result.returncode == 1
        assert 'not found' in result.stderr.lower()

    def test_bad_dpi(self, tmp_path):
        """Zero dpi → exit code 1 (our validation, not argparse)"""
        img = tmp_path / 'test.png'
        img.write_bytes(b'\x89PNG\r\n\x1a\n')  # fake PNG header
        result = subprocess.run([sys.executable, MARK_BOXES, str(img), '0'],
                                capture_output=True, text=True)
        assert result.returncode == 1
        assert 'positive' in result.stderr.lower()

    def test_negative_dpi(self):
        """Negative dpi → argparse rejects it"""
        result = subprocess.run([sys.executable, MARK_BOXES, '/tmp/fake.png', '-5'],
                                capture_output=True, text=True)
        assert result.returncode != 0

    def test_help(self):
        """--help exits 0 and shows usage"""
        result = subprocess.run([sys.executable, MARK_BOXES, '--help'],
                                capture_output=True, text=True)
        assert result.returncode == 0
        assert 'image' in result.stdout.lower()


# ---------------------------------------------------------------------------
# Integration: write JSON and read it back (no tkinter)
# ---------------------------------------------------------------------------

class TestJsonContract:
    def test_output_structure(self, tmp_path):
        """Verify the JSON format matches what overlay_boxes.py expects"""
        # Simulate what on_key writes
        from mark_boxes import compute_box
        boxes = [
            compute_box((10, 20, 100, 200), 1, factor=2, scale_px_to_pt=0.36),
            compute_box((50, 60, 150, 250), 2, factor=2, scale_px_to_pt=0.36),
        ]
        data = {
            'image': 'test.png', 'dpi': 200, 'px_per_pt': 0.36,
            'factor': 2, 'boxes': boxes,
        }
        out_file = tmp_path / 'boxes.json'
        out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

        loaded = json.loads(out_file.read_text())
        assert loaded['image'] == 'test.png'
        assert loaded['dpi'] == 200
        assert len(loaded['boxes']) == 2
        assert loaded['boxes'][0]['label'] == 'b1'
        assert 'px' in loaded['boxes'][0]
        assert 'pt' in loaded['boxes'][0]
