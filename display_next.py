#!/usr/bin/env python3
"""Display the next photo in rotation on the PhotoPainter panel. Run this
on the Pi (via cron, or at boot) pointed at a folder of photos already
prepared with prep_photos.py (800x480, already rotated for this mount).

Usage: python3 display_next.py <photo_dir> [state_file]
"""
import logging
import os
import sys
from pathlib import Path

LIBDIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    "RaspberryPi_JetsonNano",
    "python",
    "lib",
)
if os.path.exists(LIBDIR):
    sys.path.append(LIBDIR)

from PIL import Image
from waveshare_epd import epd7in3e

logging.basicConfig(level=logging.INFO)

DEFAULT_STATE_FILE = Path.home() / ".photopainter_index"


def read_index(state_file: Path) -> int:
    try:
        return int(state_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def write_index(state_file: Path, index: int) -> None:
    state_file.write_text(str(index))


def display_next(photo_dir: Path, state_file: Path) -> None:
    photos = sorted(
        p for p in photo_dir.iterdir() if p.suffix.lower() in (".png", ".bmp")
    )
    if not photos:
        logging.error("no photos found in %s", photo_dir)
        return

    index = read_index(state_file) % len(photos)
    photo_path = photos[index]
    logging.info("displaying %s (%d/%d)", photo_path.name, index + 1, len(photos))

    epd = epd7in3e.EPD()
    epd.init()
    epd.display(epd.getbuffer(Image.open(photo_path)))
    epd.sleep()

    write_index(state_file, (index + 1) % len(photos))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <photo_dir> [state_file]")
        sys.exit(1)
    photo_dir_arg = Path(sys.argv[1])
    state_file_arg = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_STATE_FILE
    display_next(photo_dir_arg, state_file_arg)
