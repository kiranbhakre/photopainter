#!/usr/bin/env python3
"""Fetch current weather from OpenWeatherMap and render it as an 800x480 PNG
ready for the PhotoPainter panel, and optionally display it immediately.

Reads the API key and city from a config file (default
~/.photopainter_weather.json), kept off the Mac-side repo on purpose:
    {"api_key": "...", "city": "London"}

Usage: python3 weather_widget.py <output_path> [--show] [--config PATH]
"""
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PANEL_W, PANEL_H = 800, 480
FONT_PATH = Path(__file__).parent.parent / "RaspberryPi_JetsonNano" / "python" / "pic" / "Font.ttc"
BG_COLOR = (255, 255, 255)
TEXT_COLOR = (0, 0, 0)
DEFAULT_CONFIG_PATH = Path.home() / ".photopainter_weather.json"
OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
REQUEST_TIMEOUT_S = 15


def load_config(config_path: Path) -> dict:
    try:
        return json.loads(config_path.read_text())
    except FileNotFoundError:
        raise SystemExit(
            f"Missing config file {config_path}. Create it with:\n"
            '  {"api_key": "YOUR_OPENWEATHERMAP_KEY", "city": "London"}'
        )


def fetch_weather(api_key: str, city: str) -> dict:
    url = f"{OWM_URL}?q={urllib.parse.quote(city)}&appid={api_key}&units=metric"
    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_S) as resp:
        return json.load(resp)


def render_weather(data: dict, city: str) -> Image.Image:
    img = Image.new("RGB", (PANEL_W, PANEL_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    temp_font = ImageFont.truetype(str(FONT_PATH), 130)
    desc_font = ImageFont.truetype(str(FONT_PATH), 42)
    detail_font = ImageFont.truetype(str(FONT_PATH), 28)

    temp_text = f"{round(data['main']['temp'])}°C"
    desc_text = data["weather"][0]["description"].title()
    detail_text = (
        f"Feels like {round(data['main']['feels_like'])}°C"
        f"  •  Humidity {data['main']['humidity']}%"
    )

    temp_bbox = draw.textbbox((0, 0), temp_text, font=temp_font)
    temp_w, temp_h = temp_bbox[2] - temp_bbox[0], temp_bbox[3] - temp_bbox[1]
    draw.text(((PANEL_W - temp_w) / 2, 60), temp_text, font=temp_font, fill=TEXT_COLOR)

    city_bbox = draw.textbbox((0, 0), city, font=desc_font)
    draw.text(((PANEL_W - (city_bbox[2] - city_bbox[0])) / 2, 230), city, font=desc_font, fill=TEXT_COLOR)

    desc_bbox = draw.textbbox((0, 0), desc_text, font=desc_font)
    draw.text(((PANEL_W - (desc_bbox[2] - desc_bbox[0])) / 2, 290), desc_text, font=desc_font, fill=TEXT_COLOR)

    detail_bbox = draw.textbbox((0, 0), detail_text, font=detail_font)
    draw.text(((PANEL_W - (detail_bbox[2] - detail_bbox[0])) / 2, 360), detail_text, font=detail_font, fill=TEXT_COLOR)

    return img.rotate(180)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <output_path> [--show] [--config PATH]")
        sys.exit(1)
    output_path = Path(sys.argv[1])
    config_path = DEFAULT_CONFIG_PATH
    if "--config" in sys.argv:
        config_path = Path(sys.argv[sys.argv.index("--config") + 1])

    config = load_config(config_path)
    weather_data = fetch_weather(config["api_key"], config["city"])
    render_weather(weather_data, config["city"]).save(output_path)
    print(f"saved {output_path}")
    if "--show" in sys.argv:
        subprocess.run(["python3", str(Path(__file__).parent / "display_one.py"), str(output_path)], check=True)
