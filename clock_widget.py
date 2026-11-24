#!/usr/bin/env python3
"""Render a simple clock face (time + date) as an 800x480 PNG ready for the
PhotoPainter panel, and optionally display it immediately.

Usage: python3 clock_widget.py <output_path> [--show]
"""
import datetime
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PANEL_W, PANEL_H = 800, 480
FONT_PATH = Path(__file__).parent.parent / "RaspberryPi_JetsonNano" / "python" / "pic" / "Font.ttc"
BG_COLOR = (255, 255, 255)
TEXT_COLOR = (0, 0, 0)


def render_clock(now: datetime.datetime | None = None) -> Image.Image:
    now = now or datetime.datetime.now()
    img = Image.new("RGB", (PANEL_W, PANEL_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    time_font = ImageFont.truetype(str(FONT_PATH), 140)
    date_font = ImageFont.truetype(str(FONT_PATH), 36)

    time_text = now.strftime("%H:%M")
    date_text = now.strftime("%A, %d %B %Y")

    time_bbox = draw.textbbox((0, 0), time_text, font=time_font)
    time_w, time_h = time_bbox[2] - time_bbox[0], time_bbox[3] - time_bbox[1]
    draw.text(((PANEL_W - time_w) / 2, (PANEL_H - time_h) / 2 - 40), time_text, font=time_font, fill=TEXT_COLOR)

    date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
    date_w, date_h = date_bbox[2] - date_bbox[0], date_bbox[3] - date_bbox[1]
    draw.text(((PANEL_W - date_w) / 2, PANEL_H / 2 + 80), date_text, font=date_font, fill=TEXT_COLOR)

    return img.rotate(180)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <output_path> [--show]")
        sys.exit(1)
    output_path = Path(sys.argv[1])
    render_clock().save(output_path)
    print(f"saved {output_path}")
    if "--show" in sys.argv:
        subprocess.run(["python3", str(Path(__file__).parent / "display_one.py"), str(output_path)], check=True)
