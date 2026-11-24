# photopainter

A lightweight, pure-Python companion for the [Waveshare RPi Zero PhotoPainter](https://www.waveshare.com/wiki/RPi_Zero_PhotoPainter) — a 7.3" six-color (Spectra 6) e-paper photo frame built around a Raspberry Pi Zero W.

It's a smaller alternative to [InkyPi](https://github.com/fatihak/InkyPi): InkyPi's AI-image plugin pulls in `openai`/`pydantic`, which has to compile a large Rust extension from source on this board's original single-core Pi Zero W — that compile alone can take hours and risks crashing the device from disk/memory pressure. Everything here is plain Python with no compiled dependencies beyond Pillow.

## Hardware note

This board wires the panel's power-enable line to **GPIO27**, not GPIO18 like Waveshare's generic e-Paper HAT driver assumes. Without that fix applied to `epdconfig.py` in the main [e-Paper SDK](https://github.com/waveshare/e-Paper), the panel never powers on and the screen stays blank with no error.

## Features

- **Web upload page** (`webupload.py`) — open it from any phone browser:
  - Drag-to-position crop (via Cropper.js) instead of a blind center-crop, so you choose what's kept
  - Live-adjustable saturation/contrast/brightness/sharpness sliders with real-time preview, tuned for how washed-out a 6-color dithered panel makes photos look otherwise
  - Thumbnail gallery with per-photo "Show on frame now", "Rotate 90°", and "Remove"
  - Upload progress bar
- **Automatic rotation** (`display_next.py`) — cycles through the photo folder on a schedule (e.g. daily via cron), remembering its place across runs
- **Widgets**, triggerable from the same page:
  - `clock_widget.py` — current time/date
  - `weather_widget.py` — current conditions via OpenWeatherMap
  - `comic_widget.py` — today's XKCD comic, letterboxed so nothing gets cropped

## Requirements

- Raspberry Pi Zero W (or similar) running the PhotoPainter board, with the Waveshare e-Paper SDK's `epd7in3e` driver available (patched for `PWR_PIN = 27`, see above)
- Python 3 with `Pillow` and `Flask` (`sudo apt-get install python3-flask`)

## Setup

1. Copy this folder onto the Pi, as a sibling of the e-Paper SDK's `RaspberryPi_JetsonNano/python/lib` directory (the scripts locate the driver relative to their own path).
2. Install the systemd service so the upload page survives reboots:
   ```bash
   sudo cp photopainter-upload.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now photopainter-upload.service
   ```
3. Schedule automatic rotation, e.g. once daily at 8am:
   ```bash
   (crontab -l 2>/dev/null; echo '0 8 * * * /usr/bin/python3 /path/to/photopainter/display_next.py /path/to/photos_ready') | crontab -
   ```
4. For the weather widget, create `~/.photopainter_weather.json` (kept out of this repo on purpose):
   ```json
   {"api_key": "YOUR_OPENWEATHERMAP_KEY", "city": "London"}
   ```

## Files

| File | Purpose |
|---|---|
| `webupload.py` | Flask app: upload/crop/enhance UI, photo list, widget buttons |
| `prep_photos.py` | Batch crop/resize/enhance a folder of photos (run from a Mac/PC before copying to the Pi) |
| `display_next.py` | Displays the next photo in rotation, advancing a persisted index |
| `display_one.py` | Displays one specific photo immediately |
| `clock_widget.py`, `weather_widget.py`, `comic_widget.py` | Render and (optionally) display a widget |
| `photopainter-upload.service` | systemd unit for the web upload page |
