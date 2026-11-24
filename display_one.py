#!/usr/bin/env python3
"""Display one specific photo on the PhotoPainter panel immediately, without
touching the rotation index. Used by the web upload page's "Display now".

Usage: python3 display_one.py <photo_path>
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

DISPLAY_LOCK = Path("/tmp/photopainter_display.lock")


def display_one(photo_path: Path) -> None:
    logging.info("displaying %s", photo_path.name)
    epd = epd7in3e.EPD()
    epd.init()
    epd.display(epd.getbuffer(Image.open(photo_path)))
    epd.sleep()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <photo_path>")
        sys.exit(1)
    try:
        display_one(Path(sys.argv[1]))
    finally:
        DISPLAY_LOCK.unlink(missing_ok=True)
