#!/usr/bin/env python3
"""Batch-prepare photos for the PhotoPainter 7.3" panel: center-crop to the
800x480 aspect ratio, resize, and rotate 180 degrees to match how the panel
is physically mounted in this frame. Run on the Mac, then copy dest_dir to
the Pi.

Usage: python3 prep_photos.py <source_dir> <dest_dir>
"""
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

PANEL_W, PANEL_H = 800, 480
SOURCE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# The panel only has 6 real colors, so every other shade is approximated with
# dithering. Muted, low-contrast photos need heavy dithering to represent all
# those in-between tones, which shows up as visible stippling/noise. Boosting
# saturation and contrast first means more pixels land close to one of the 6
# available colors, needing far less dithering to look right.
SATURATION_BOOST = 1.5
CONTRAST_BOOST = 1.2
# Dithering also softens fine detail, and the panel is reflective with no
# backlight, so photos read darker on it than on a screen.
SHARPNESS_BOOST = 1.5
BRIGHTNESS_BOOST = 1.1


def prepare_photo(src_path: Path, dst_path: Path) -> None:
    img = ImageOps.exif_transpose(Image.open(src_path)).convert("RGB")
    src_w, src_h = img.size
    target_ratio = PANEL_W / PANEL_H
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        img = img.crop((0, top, src_w, top + new_h))

    img = img.resize((PANEL_W, PANEL_H), Image.LANCZOS).rotate(180)
    img = ImageEnhance.Color(img).enhance(SATURATION_BOOST)
    img = ImageEnhance.Contrast(img).enhance(CONTRAST_BOOST)
    img = ImageEnhance.Brightness(img).enhance(BRIGHTNESS_BOOST)
    img = ImageEnhance.Sharpness(img).enhance(SHARPNESS_BOOST)
    img.save(dst_path)


def prepare_folder(source_dir: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted(
        p for p in source_dir.iterdir() if p.suffix.lower() in SOURCE_EXTENSIONS
    )
    for src_path in sources:
        dst_path = dest_dir / (src_path.stem + ".png")
        prepare_photo(src_path, dst_path)
        print(f"{src_path.name} -> {dst_path.name}")
    print(f"prepared {len(sources)} photo(s) in {dest_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <source_dir> <dest_dir>")
        sys.exit(1)
    prepare_folder(Path(sys.argv[1]), Path(sys.argv[2]))
