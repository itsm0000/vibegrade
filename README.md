# VibeGrade — AI Color Grading for Sony ZV-E10

> Drop your RAW photos. Pick a vibe. Get stunning color-graded exports. Runs 100% locally.

---

## Features

- **Drag & drop** `.ARW` (Sony), `.CR2`, `.NEF`, `.DNG`, `.JPG` support
- **6 built-in AI-crafted presets**: Cinematic, Retro Film, Cyberpunk, Futuristic Warm, Moody Dark
- **Your Style mode**: Upload 3–10 of your favourite edited photos → AI learns your color fingerprint → applies it to all new shots
- **Adjustable strength** (0–100%)
- **Film grain** toggle
- **Export as** JPG, PNG, or 16-bit TIFF
- **Batch processing** — grade many photos at once
- Runs 100% locally, never uploads to any server

---

## Setup (one time)

### 1. Create a virtual environment

```powershell
cd C:\Users\MT\Projects\colorgrading
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

> If you hit issues with `rawpy` on Windows, install via:
> ```powershell
> pip install rawpy --only-binary=rawpy
> ```

---

## Run the app

You can run VibeGrade in two ways:

### 1. Using Desktop Shortcuts (Recommended)
We've created two convenient shortcuts on your Windows Desktop:
- 🚀 **`VibeGrade`**: Double-click this shortcut to start the server silently in the background and automatically open the application in your web browser. No command prompt windows will clutter your screen!
- 🛑 **`Stop VibeGrade`**: Double-click this red power button shortcut to silently terminate the background server and release port 5000.

### 2. Manually via Terminal
If you prefer running it from the command line:
```powershell
# From the colorgrading folder, with venv active:
python app.py
```
Then open your browser at: **http://localhost:5000**

---

## How to use

1. **Drop your RAW files** into the upload zone (or click to browse)
2. **Pick a vibe** — click any preset card
3. *(Optional)* If you picked **Your Style**, drop 3–10 of your favourite edited photos as references
4. **Adjust strength** with the slider — lower = more subtle
5. **Toggle film grain** if you want that analogue feel
6. **Choose export format** (JPG for sharing, TIFF for print/editing)
7. Hit **Grade My Photos** — results appear below for download

---

## Presets explained

| Preset | Look |
|---|---|
| 🎬 **Cinematic** | Teal & orange split tones, lifted blacks, Hollywood contrast |
| 📷 **Retro Film** | Kodak warmth, faded matte shadows, analogue grain-friendly |
| 🌆 **Cyberpunk** | Crushed blacks, electric cyan & magenta, neon punch |
| 🌅 **Futuristic Warm** | Golden hour glow, airy clean highlights, warm mids |
| 🌑 **Moody Dark** | Desaturated cool tones, lifted blacks, cinematic silence |
| ✨ **Your Style** | AI-powered reference matching to YOUR personal look |

---

## Your Style — how it works

The **Your Style** mode uses the `color-matcher` library (MKL algorithm) to:

1. Analyse the color distribution of your reference photos
2. Compute a mathematical transform from your RAW to your edited look
3. Apply that same transform to all new photos

The more consistent your references (same general style), the better the result.

---

## Folder structure

```
colorgrading/
├── app.py              # Flask backend
├── grader.py           # Color science engine
├── requirements.txt    # Python deps
├── static/
│   ├── index.html      # UI
│   ├── style.css       # Styles
│   └── app.js          # Frontend logic
├── uploads/            # Temp: uploaded RAWs (auto-created)
├── outputs/            # Graded exports (auto-created)
└── references/         # Your style reference photos (auto-created)
```

---

## Upgrade: NeuralPreset AI (GPU-accelerated style transfer)

For even more powerful style matching using deep learning:

```powershell
# Install PyTorch with CUDA (check pytorch.org for your CUDA version)
pip install torch torchvision

# Clone NeuralPreset
git clone https://github.com/ZHKKKe/NeuralPreset.git

# Download pretrained weights from the repo README
```

Then modify `grader.py` to use NeuralPreset for the `your_style` preset.

---

*Built with: rawpy, Flask, Pillow, color-matcher, NumPy*
