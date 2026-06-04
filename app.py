"""
VibeGrade - AI Color Grading for Sony ZV-E10 RAW Photos
Flask backend: reads ARW files, applies color grade presets, handles style matching
"""

import os
import io
import json
import uuid
import traceback
import numpy as np
import rawpy
import imageio.v3 as iio
from PIL import Image, ImageFilter
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from pathlib import Path
import threading

from grader import apply_preset, apply_style_reference, get_available_presets, PRESET_META

app = Flask(__name__, static_folder="static")
CORS(app)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
REFERENCE_DIR = Path("references")

for d in [UPLOAD_DIR, OUTPUT_DIR, REFERENCE_DIR]:
    d.mkdir(exist_ok=True)

# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/presets", methods=["GET"])
def get_presets():
    return jsonify(get_available_presets())

@app.route("/api/upload", methods=["POST"])
def upload_photo():
    """Accept one or more RAW/image files, return job IDs."""
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400

    results = []
    for f in request.files.getlist("files"):
        job_id = str(uuid.uuid4())[:8]
        ext = Path(f.filename).suffix.lower()
        save_path = UPLOAD_DIR / f"{job_id}{ext}"
        f.save(str(save_path))

        # Generate a quick JPEG preview
        try:
            preview_path = UPLOAD_DIR / f"{job_id}_preview.jpg"
            raw_to_preview(str(save_path), str(preview_path))
            preview_url = f"/api/preview/{job_id}_preview.jpg"
        except Exception as e:
            preview_url = None

        results.append({
            "job_id": job_id,
            "filename": f.filename,
            "ext": ext,
            "preview_url": preview_url,
        })

    return jsonify({"files": results})


@app.route("/api/preview/<filename>")
def serve_preview(filename):
    return send_from_directory(str(UPLOAD_DIR), filename)


@app.route("/api/output/<filename>")
def serve_output(filename):
    return send_from_directory(str(OUTPUT_DIR), filename)


@app.route("/api/upload_reference", methods=["POST"])
def upload_reference():
    """Upload reference images for 'your style' matching."""
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400
    paths = []
    for f in request.files.getlist("files"):
        fname = f"ref_{uuid.uuid4().hex[:6]}{Path(f.filename).suffix}"
        p = REFERENCE_DIR / fname
        f.save(str(p))
        paths.append(str(p))
    return jsonify({"count": len(paths), "message": f"Loaded {len(paths)} reference image(s)"})


@app.route("/api/grade", methods=["POST"])
def grade():
    """
    Grade one or more uploaded files.
    Body JSON:
      {
        "jobs": ["job_id1", "job_id2"],
        "preset": "cinematic",       // or "your_style"
        "strength": 0.8,             // 0.0 – 1.0
        "grain": true,
        "format": "jpg"              // jpg | tiff | png
      }
    """
    data = request.get_json()
    jobs = data.get("jobs", [])
    preset = data.get("preset", "cinematic")
    strength = float(data.get("strength", 0.85))
    add_grain = bool(data.get("grain", False))
    out_format = data.get("format", "jpg").lower()

    if not jobs:
        return jsonify({"error": "No jobs provided"}), 400

    outputs = []
    errors = []

    for job_id in jobs:
        # Find the uploaded file
        candidates = list(UPLOAD_DIR.glob(f"{job_id}.*"))
        candidates = [c for c in candidates if "_preview" not in c.name]
        if not candidates:
            errors.append({"job_id": job_id, "error": "File not found"})
            continue

        src_path = candidates[0]
        out_name = f"{job_id}_{preset}.{out_format}"
        out_path = OUTPUT_DIR / out_name

        try:
            # Load RAW (or regular image)
            img_arr = load_image(str(src_path))

            # Apply grade
            if preset == "your_style":
                ref_images = load_references()
                if not ref_images:
                    raise ValueError("No reference images uploaded yet. Upload some of your favourite edited photos first.")
                graded = apply_style_reference(img_arr, ref_images, strength)
            else:
                graded = apply_preset(img_arr, preset, strength, add_grain)

            # Save output
            save_image(graded, str(out_path), out_format)

            outputs.append({
                "job_id": job_id,
                "output_url": f"/api/output/{out_name}",
                "filename": out_name,
            })

        except Exception as e:
            traceback.print_exc()
            errors.append({"job_id": job_id, "error": str(e)})

    return jsonify({"outputs": outputs, "errors": errors})


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def raw_to_preview(src: str, dst: str, max_size: int = 1200):
    """Convert a RAW file to a small JPEG preview."""
    ext = Path(src).suffix.lower()
    if ext in (".arw", ".cr2", ".cr3", ".nef", ".dng", ".raf", ".orf", ".rw2"):
        with rawpy.imread(src) as raw:
            arr = raw.postprocess(
                use_camera_wb=True,
                half_size=True,
                output_bps=8,
                no_auto_bright=False,
            )
    else:
        img = Image.open(src).convert("RGB")
        arr = np.array(img)

    img = Image.fromarray(arr)
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    img.save(dst, "JPEG", quality=82)


def load_image(src: str) -> np.ndarray:
    """Load a RAW or regular image and return a float32 [0,1] RGB array."""
    ext = Path(src).suffix.lower()
    if ext in (".arw", ".cr2", ".cr3", ".nef", ".dng", ".raf", ".orf", ".rw2"):
        with rawpy.imread(src) as raw:
            arr = raw.postprocess(
                use_camera_wb=True,
                half_size=False,
                output_bps=16,
                no_auto_bright=False,
                bright=1.0,
            )
        arr = arr.astype(np.float32) / 65535.0
    else:
        img = Image.open(src).convert("RGB")
        arr = np.array(img).astype(np.float32) / 255.0

    return arr


def save_image(arr: np.ndarray, dst: str, fmt: str):
    """Save a float32 [0,1] image array to disk."""
    arr_clipped = np.clip(arr, 0.0, 1.0)
    if fmt == "tiff":
        arr_16 = (arr_clipped * 65535).astype(np.uint16)
        iio.imwrite(dst, arr_16)
    else:
        arr_8 = (arr_clipped * 255).astype(np.uint8)
        img = Image.fromarray(arr_8)
        quality = 95 if fmt == "jpg" else None
        img.save(dst, quality=quality)


def load_references() -> list:
    """Load all reference images from the references folder."""
    refs = []
    for p in REFERENCE_DIR.iterdir():
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".arw", ".cr2", ".nef"):
            try:
                refs.append(load_image(str(p)))
            except Exception:
                pass
    return refs


if __name__ == "__main__":
    print("VibeGrade starting on http://localhost:5000")
    app.run(debug=True, port=5000, threaded=True)
