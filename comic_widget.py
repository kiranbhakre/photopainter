#!/usr/bin/env python3
"""Fetch today's XKCD comic and render it as an 800x480 PNG ready for the
PhotoPainter panel (fit-within + white letterbox, not cropped, so punchlines
don't get cut off), and optionally display it immediately.

Usage: python3 comic_widget.py <output_path> [--show]
"""
import subprocess
import sys
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

PANEL_W, PANEL_H = 800, 480
XKCD_LATEST_URL = "https://xkcd.com/info.0.json"
BG_COLOR = (255, 255, 255)
REQUEST_TIMEOUT_S = 15


def fetch_comic_image() -> Image.Image:
    with urllib.request.urlopen(XKCD_LATEST_URL, timeout=REQUEST_TIMEOUT_S) as resp:
        import json

        meta = json.load(resp)
    with urllib.request.urlopen(meta["img"], timeout=REQUEST_TIMEOUT_S) as resp:
        return Image.open(BytesIO(resp.read())).convert("RGB")


def render_comic() -> Image.Image:
    comic = fetch_comic_image()
    comic.thumbnail((PANEL_W, PANEL_H), Image.LANCZOS)

    canvas = Image.new("RGB", (PANEL_W, PANEL_H), BG_COLOR)
    offset = ((PANEL_W - comic.width) // 2, (PANEL_H - comic.height) // 2)
    canvas.paste(comic, offset)

    return canvas.rotate(180)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <output_path> [--show]")
        sys.exit(1)
    output_path = Path(sys.argv[1])
    render_comic().save(output_path)
    print(f"saved {output_path}")
    if "--show" in sys.argv:
        subprocess.run(["python3", str(Path(__file__).parent / "display_one.py"), str(output_path)], check=True)
