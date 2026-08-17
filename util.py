"""Shared helpers for agent-tools: dependency guards, file checks, CLI validation."""
import importlib
import shutil
import sys
from pathlib import Path


def require_module(name, pip_name=None, exit_code=1):
    """Import a module or exit with an install hint.

    Args:
        name: Module name to import (e.g. 'markdown', 'PIL.Image')
        pip_name: pip package name (defaults to name)
        exit_code: Exit code on failure (default 1)

    Returns:
        The imported module.

    Usage:
        markdown = require_module('markdown')
        markdown.markdown(...)
    """
    try:
        return importlib.import_module(name)
    except ImportError:
        pkg = pip_name or name
        print(f"Error: '{name}' package not installed.", file=sys.stderr)
        print(f"Run: pip install {pkg}", file=sys.stderr)
        sys.exit(exit_code)


def require_cli(name, install_hint=None, exit_code=1):
    """Check that a CLI tool exists on PATH, or exit with an install hint.

    Args:
        name: Command name (e.g. 'ebook-convert')
        install_hint: Install instructions (e.g. 'apt install calibre')
        exit_code: Exit code on failure (default 1)

    Returns:
        The path to the tool (same as shutil.which).

    Usage:
        require_cli('ebook-convert', 'apt install calibre')
    """
    path = shutil.which(name)
    if path:
        return path
    print(f"Error: '{name}' not found on PATH.", file=sys.stderr)
    if install_hint:
        print(f"Install: {install_hint}", file=sys.stderr)
    sys.exit(exit_code)


def require_file(path, label=None):
    """Check that a file exists, or exit with an error message.

    Args:
        path: Path to check (str or Path)
        label: Human-readable name for the file (default: filename)

    Returns:
        Resolved Path object.

    Usage:
        require_file(args.input, 'input file')
    """
    p = Path(path)
    if p.exists():
        return p
    lbl = label or 'File'
    print(f"Error: {lbl} not found: {p}", file=sys.stderr)
    sys.exit(1)
