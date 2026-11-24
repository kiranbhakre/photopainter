#!/usr/bin/env python3
"""Lightweight web page for uploading photos to the PhotoPainter from a phone
browser. Shows a crop preview (fixed 800x480 aspect ratio, drag to position)
before saving, so you choose what's kept instead of a blind center-crop.
Also lets you push a specific photo to the panel immediately.

Usage: python3 webupload.py <photo_dir> [port]
"""
import subprocess
import sys
import time
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, send_from_directory, url_for
from PIL import Image, ImageEnhance
from werkzeug.utils import secure_filename

PANEL_W, PANEL_H = 800, 480
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


def enhance_for_panel(img: Image.Image, saturation: float, contrast: float, brightness: float, sharpness: float) -> Image.Image:
    img = ImageEnhance.Color(img).enhance(saturation)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Sharpness(img).enhance(sharpness)
    return img


def read_enhance_value(form, field: str, default: float, lo: float, hi: float) -> float:
    try:
        value = float(form.get(field, default))
    except ValueError:
        return default
    return max(lo, min(hi, value))


MAX_UPLOAD_BYTES = 25 * 1024 * 1024
DISPLAY_SCRIPT = Path(__file__).parent / "display_one.py"
DISPLAY_LOCK = Path("/tmp/photopainter_display.lock")
WIDGET_SCRIPTS = {
    "clock": Path(__file__).parent / "clock_widget.py",
    "weather": Path(__file__).parent / "weather_widget.py",
    "comic": Path(__file__).parent / "comic_widget.py",
}
WIDGET_OUTPUT = Path("/tmp/photopainter_widget.png")


def display_lock_busy() -> bool:
    return DISPLAY_LOCK.exists() and (time.time() - DISPLAY_LOCK.stat().st_mtime) < 120

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
PHOTO_DIR: Path

PAGE = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PhotoPainter upload</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.2/cropper.min.css">
<style>
body { font-family: sans-serif; max-width: 480px; margin: 2rem auto; padding: 0 1rem; }
h1 { font-size: 1.3rem; }
.msg { padding: 0.6rem 1rem; border-radius: 6px; margin-bottom: 1rem; }
.msg.ok { background: #d8f5d8; }
.msg.err { background: #f8d8d8; }
input[type=file] { margin-bottom: 0.8rem; }
button, input[type=submit] { padding: 0.5rem 1rem; }
#crop-stage { display: none; margin-bottom: 1.5rem; }
#crop-image-wrap { max-height: 60vh; overflow: hidden; margin-bottom: 0.6rem; }
#crop-image-wrap img { max-width: 100%; display: block; }
#crop-actions { display: flex; gap: 0.5rem; }
#enhance-controls { margin-bottom: 0.8rem; }
#enhance-controls label { display: flex; align-items: center; gap: 0.6rem; font-size: 0.85rem; margin-bottom: 0.4rem; }
#enhance-controls input[type=range] { flex: 1; }
#enhance-controls span { width: 2.4rem; text-align: right; color: #555; }
progress#upload-progress { width: 100%; height: 1.2rem; margin-bottom: 1.5rem; display: none; }
h2 { font-size: 1rem; margin-bottom: 0.5rem; }
ul { list-style: none; padding: 0; }
li { display: flex; align-items: center; gap: 0.8rem; padding: 0.6rem 0; border-bottom: 1px solid #eee; }
li img { width: 72px; height: auto; border-radius: 4px; flex-shrink: 0; }
li .name { flex: 1; word-break: break-all; font-size: 0.85rem; }
li .actions { display: flex; flex-direction: column; gap: 0.3rem; }
button.show { background: none; border: 1px solid #369; color: #369; border-radius: 4px; padding: 0.2rem 0.6rem; }
button.rotate { background: none; border: 1px solid #888; color: #555; border-radius: 4px; padding: 0.2rem 0.6rem; }
button.del { background: none; border: 1px solid #c33; color: #c33; border-radius: 4px; padding: 0.2rem 0.6rem; }
#widgets { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
#widgets form { flex: 1; }
#widgets button { width: 100%; background: none; border: 1px solid #369; color: #369; border-radius: 4px; }
</style>
</head>
<body>
<h1>PhotoPainter photos</h1>
{% if message %}<div class="msg {{ 'ok' if ok else 'err' }}">{{ message }}</div>{% endif %}

<h2>Widgets</h2>
<div id="widgets">
  <form method="post" action="{{ url_for('show_widget', name='clock') }}"><button type="submit">Clock</button></form>
  <form method="post" action="{{ url_for('show_widget', name='weather') }}"><button type="submit">Weather</button></form>
  <form method="post" action="{{ url_for('show_widget', name='comic') }}"><button type="submit">Comic</button></form>
</div>

<h2>Upload a photo</h2>
<input type="file" id="file-input" accept="image/*">

<div id="crop-stage">
  <div id="crop-image-wrap"><img id="crop-image"></div>
  <div id="enhance-controls">
    <label>Saturation <input type="range" id="enh-saturation" min="0.5" max="2.5" step="0.1" value="{{ saturation }}"> <span id="enh-saturation-val">{{ saturation }}</span></label>
    <label>Contrast <input type="range" id="enh-contrast" min="0.5" max="2.0" step="0.1" value="{{ contrast }}"> <span id="enh-contrast-val">{{ contrast }}</span></label>
    <label>Brightness <input type="range" id="enh-brightness" min="0.5" max="2.0" step="0.1" value="{{ brightness }}"> <span id="enh-brightness-val">{{ brightness }}</span></label>
    <label>Sharpness <input type="range" id="enh-sharpness" min="0" max="3.0" step="0.1" value="{{ sharpness }}"> <span id="enh-sharpness-val">{{ sharpness }}</span></label>
  </div>
  <div id="crop-actions">
    <button id="crop-rotate" type="button">Rotate 90&deg;</button>
    <button id="crop-save" type="button">Save to frame</button>
    <button id="crop-cancel" type="button">Cancel</button>
  </div>
</div>
<progress id="upload-progress" value="0" max="100"></progress>

<h2>Rotation</h2>
<ul>
{% for name in photos %}
  <li>
    <img src="{{ url_for('photo_file', filename=name) }}" alt="">
    <span class="name">{{ name }}</span>
    <span class="actions">
      <form method="post" action="{{ url_for('display_now', filename=name) }}">
        <button class="show" type="submit">Show on frame</button>
      </form>
      <form method="post" action="{{ url_for('rotate', filename=name) }}">
        <button class="rotate" type="submit">Rotate 90&deg;</button>
      </form>
      <form method="post" action="{{ url_for('delete', filename=name) }}" onsubmit="return confirm('Remove this photo?')">
        <button class="del" type="submit">Remove</button>
      </form>
    </span>
  </li>
{% else %}
  <li>No photos yet.</li>
{% endfor %}
</ul>

<script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.2/cropper.min.js"></script>
<script>
const fileInput = document.getElementById('file-input');
const cropStage = document.getElementById('crop-stage');
const cropImage = document.getElementById('crop-image');
const progressBar = document.getElementById('upload-progress');
let cropper = null;

const enhanceSliders = ['saturation', 'contrast', 'brightness', 'sharpness'].map(function (name) {
  return { name: name, input: document.getElementById('enh-' + name), out: document.getElementById('enh-' + name + '-val') };
});

function applyPreviewFilter() {
  const sat = document.getElementById('enh-saturation').value;
  const con = document.getElementById('enh-contrast').value;
  const bri = document.getElementById('enh-brightness').value;
  cropImage.style.filter = 'saturate(' + sat + ') contrast(' + con + ') brightness(' + bri + ')';
}

enhanceSliders.forEach(function (s) {
  s.input.addEventListener('input', function () {
    s.out.textContent = s.input.value;
    applyPreviewFilter();
  });
});

fileInput.addEventListener('change', function () {
  const file = fileInput.files[0];
  if (!file) return;
  cropImage.src = URL.createObjectURL(file);
  cropStage.style.display = 'block';
  if (cropper) cropper.destroy();
  cropImage.onload = function () {
    applyPreviewFilter();
    cropper = new Cropper(cropImage, {
      aspectRatio: {{ panel_w }} / {{ panel_h }},
      viewMode: 1,
      autoCropArea: 1,
      background: false
    });
  };
});

document.getElementById('crop-rotate').addEventListener('click', function () {
  if (cropper) cropper.rotate(90);
});

document.getElementById('crop-cancel').addEventListener('click', function () {
  if (cropper) cropper.destroy();
  cropper = null;
  cropStage.style.display = 'none';
  fileInput.value = '';
});

document.getElementById('crop-save').addEventListener('click', function () {
  if (!cropper) return;
  cropper.getCroppedCanvas({ width: {{ panel_w }}, height: {{ panel_h }} }).toBlob(function (blob) {
    const data = new FormData();
    data.append('photo', blob, 'crop.png');
    enhanceSliders.forEach(function (s) { data.append(s.name, s.input.value); });
    const xhr = new XMLHttpRequest();
    xhr.open('POST', "{{ url_for('upload') }}");
    progressBar.style.display = 'block';
    progressBar.value = 0;
    xhr.upload.addEventListener('progress', function (evt) {
      if (evt.lengthComputable) progressBar.value = Math.round((evt.loaded / evt.total) * 100);
    });
    xhr.onload = function () { window.location = xhr.responseURL || '/'; };
    xhr.onerror = function () { progressBar.style.display = 'none'; alert('Upload failed'); };
    xhr.send(data);
  }, 'image/png');
});
</script>
</body>
</html>
"""


def list_photos() -> list[str]:
    return sorted(p.name for p in PHOTO_DIR.iterdir() if p.suffix.lower() in (".png", ".bmp"))


@app.route("/")
def index():
    message = request.args.get("message")
    ok = request.args.get("ok") == "1"
    return render_template_string(
        PAGE,
        photos=list_photos(),
        message=message,
        ok=ok,
        panel_w=PANEL_W,
        panel_h=PANEL_H,
        saturation=SATURATION_BOOST,
        contrast=CONTRAST_BOOST,
        brightness=BRIGHTNESS_BOOST,
        sharpness=SHARPNESS_BOOST,
    )


@app.route("/photo/<filename>")
def photo_file(filename: str):
    return send_from_directory(PHOTO_DIR, secure_filename(filename))


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("photo")
    if not file or not file.filename:
        return redirect(url_for("index", message="No file selected", ok=0))

    saturation = read_enhance_value(request.form, "saturation", SATURATION_BOOST, 0.5, 2.5)
    contrast = read_enhance_value(request.form, "contrast", CONTRAST_BOOST, 0.5, 2.0)
    brightness = read_enhance_value(request.form, "brightness", BRIGHTNESS_BOOST, 0.5, 2.0)
    sharpness = read_enhance_value(request.form, "sharpness", SHARPNESS_BOOST, 0.0, 3.0)

    dest_name = f"{int(time.time())}.png"
    dest_path = PHOTO_DIR / dest_name
    try:
        img = Image.open(file.stream).convert("RGB")
        img = img.resize((PANEL_W, PANEL_H), Image.LANCZOS).rotate(180)
        img = enhance_for_panel(img, saturation, contrast, brightness, sharpness)
        img.save(dest_path)
    except Exception as exc:
        return redirect(url_for("index", message=f"Could not process image: {exc}", ok=0))

    return redirect(url_for("index", message=f"Added {dest_name}", ok=1))


@app.route("/rotate/<filename>", methods=["POST"])
def rotate(filename: str):
    target = PHOTO_DIR / secure_filename(filename)
    if not target.exists():
        return redirect(url_for("index", message="Photo not found", ok=0))
    Image.open(target).rotate(-90, expand=True).save(target)
    return redirect(url_for("index", message=f"Rotated {filename} by 90°", ok=1))


@app.route("/delete/<filename>", methods=["POST"])
def delete(filename: str):
    target = PHOTO_DIR / secure_filename(filename)
    if target.exists() and target.parent == PHOTO_DIR:
        target.unlink()
        return redirect(url_for("index", message=f"Removed {filename}", ok=1))
    return redirect(url_for("index", message="Photo not found", ok=0))


@app.route("/display/<filename>", methods=["POST"])
def display_now(filename: str):
    target = PHOTO_DIR / secure_filename(filename)
    if not target.exists():
        return redirect(url_for("index", message="Photo not found", ok=0))

    if display_lock_busy():
        return redirect(url_for("index", message="Display busy, try again shortly", ok=0))

    DISPLAY_LOCK.write_text(str(time.time()))
    subprocess.Popen(
        ["python3", str(DISPLAY_SCRIPT), str(target)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return redirect(url_for("index", message=f"Showing {filename} on the frame now (~20s)", ok=1))


@app.route("/widget/<name>", methods=["POST"])
def show_widget(name: str):
    script = WIDGET_SCRIPTS.get(name)
    if not script:
        return redirect(url_for("index", message="Unknown widget", ok=0))

    if display_lock_busy():
        return redirect(url_for("index", message="Display busy, try again shortly", ok=0))

    DISPLAY_LOCK.write_text(str(time.time()))
    subprocess.Popen(
        ["python3", str(script), str(WIDGET_OUTPUT), "--show"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return redirect(url_for("index", message=f"Showing {name} on the frame now (~20s)", ok=1))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <photo_dir> [port]")
        sys.exit(1)
    PHOTO_DIR = Path(sys.argv[1])
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    app.run(host="0.0.0.0", port=port)
