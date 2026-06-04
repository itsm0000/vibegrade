"""
grader.py — Color science engine for VibeGrade
All presets are implemented as composable color transforms on float32 [0,1] RGB arrays.
"""

import numpy as np
from PIL import Image
import io


# ─────────────────────────────────────────────
# Preset metadata (shown in the UI)
# ─────────────────────────────────────────────

PRESET_META = {
    "cinematic": {
        "name": "Cinematic",
        "emoji": "🎬",
        "description": "Teal & orange split tones, lifted blacks, rich midtone contrast",
        "palette": ["#1a3a3a", "#c86030", "#f0d090"],
    },
    "retro_film": {
        "name": "Retro Film",
        "emoji": "📷",
        "description": "Kodak warmth, faded shadows, halation glow, 35mm grain",
        "palette": ["#3d2b1a", "#c8a060", "#fff0d0"],
    },
    "cyberpunk": {
        "name": "Cyberpunk",
        "emoji": "🌆",
        "description": "Neon cyan & magenta, crushed blacks, electric highlights",
        "palette": ["#050512", "#00ffee", "#ff00cc"],
    },
    "futuristic_warm": {
        "name": "Futuristic Warm",
        "emoji": "🌅",
        "description": "Golden hour glow, clean airy highlights, soft warm mids",
        "palette": ["#2a1a0a", "#e8a030", "#fff8e0"],
    },
    "moody_dark": {
        "name": "Moody Dark",
        "emoji": "🌑",
        "description": "Desaturated, lifted blacks, deep cool shadows, filmic silence",
        "palette": ["#1a1a2a", "#607080", "#d0d8e0"],
    },
    "your_style": {
        "name": "Your Style",
        "emoji": "\u2728",
        "description": "Upload your favourite edited photos — AI matches your personal look",
        "palette": ["#6030c0", "#c060f0", "#f0c0ff"],
    },
    # ── New presets ──
    "golden_hour": {
        "name": "Golden Hour",
        "emoji": "\u2600\ufe0f",
        "description": "Amber warmth, glowing skin tones, silky lifted highlights",
        "palette": ["#3a1a00", "#e8820a", "#fff4c0"],
    },
    "noir": {
        "name": "Noir",
        "emoji": "\U0001f5a4",
        "description": "High-contrast B&W, crushed blacks, dramatic chiaroscuro shadows",
        "palette": ["#000000", "#505050", "#ffffff"],
    },
    "pastel_dream": {
        "name": "Pastel Dream",
        "emoji": "\U0001f338",
        "description": "Soft pink & lavender wash, airy highlights, dreamy lifted shadows",
        "palette": ["#e8d0e8", "#d0b8e0", "#fff0f8"],
    },
    "forest_earth": {
        "name": "Forest & Earth",
        "emoji": "\U0001f333",
        "description": "Desaturated organic greens, earthy shadows, natural grounded tones",
        "palette": ["#1a2010", "#607840", "#d8d0b0"],
    },
    "blue_hour": {
        "name": "Blue Hour",
        "emoji": "\U0001f303",
        "description": "Twilight cool blues, clean midtones, calm cinematic atmosphere",
        "palette": ["#0a0a2a", "#3060a0", "#b0c8e8"],
    },
    "airy_clean": {
        "name": "Airy & Clean",
        "emoji": "\u2601\ufe0f",
        "description": "Bright lifted exposure, minimal contrast, pure white highlights",
        "palette": ["#d0d8e0", "#e8eef4", "#ffffff"],
    },
    "matte_bronze": {
        "name": "Matte Bronze",
        "emoji": "\U0001f7e4",
        "description": "Copper & bronze cast, lifted matte blacks, rich travel tones",
        "palette": ["#2a1808", "#a06020", "#e8c880"],
    },
    "vintage_polaroid": {
        "name": "Vintage Polaroid",
        "emoji": "\U0001f4f8",
        "description": "Faded green-yellow cast, washed whites, instant camera nostalgia",
        "palette": ["#303820", "#a0a858", "#f8f4d0"],
    },
}


def get_available_presets():
    return [{"id": k, **v} for k, v in PRESET_META.items()]


# ─────────────────────────────────────────────
# Core color math helpers
# ─────────────────────────────────────────────

def rgb_to_lab(img: np.ndarray) -> np.ndarray:
    """Convert [0,1] RGB to LAB (using PIL for simplicity)."""
    pil = Image.fromarray((img * 255).astype(np.uint8), mode="RGB")
    lab = pil.convert("LAB")
    return np.array(lab).astype(np.float32)


def apply_tone_curve(arr: np.ndarray, blacks: float = 0.0, shadows: float = 0.5,
                     midtones: float = 0.5, highlights: float = 0.5, whites: float = 1.0) -> np.ndarray:
    """
    5-point S-curve via cubic Bezier approximation.
    All values in [0,1] space.
    """
    x = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    y = np.array([blacks, shadows, midtones, highlights, whites])
    lut = np.interp(np.linspace(0, 1, 256), x, y)
    lut = np.clip(lut, 0, 1)
    idx = (arr * 255).astype(np.int32).clip(0, 255)
    return lut[idx]


def apply_color_wheel(arr: np.ndarray,
                      shadows_rgb=(0.0, 0.0, 0.0),
                      midtones_rgb=(0.0, 0.0, 0.0),
                      highlights_rgb=(0.0, 0.0, 0.0)) -> np.ndarray:
    """
    3-way color wheel (DaVinci-style).
    shadows/midtones/highlights_rgb: float offsets [-1, 1] per channel.
    """
    # Luminance mask
    lum = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    shadow_mask = np.clip(1.0 - lum * 3.0, 0, 1)[..., np.newaxis]
    highlights_mask = np.clip((lum - 0.67) * 3.0, 0, 1)[..., np.newaxis]
    midtones_mask = np.clip(1.0 - shadow_mask - highlights_mask, 0, 1)

    result = arr.copy()
    for ch, (s, m, h) in enumerate(zip(shadows_rgb, midtones_rgb, highlights_rgb)):
        result[..., ch] = arr[..., ch] + shadow_mask[..., 0] * s + midtones_mask[..., 0] * m + highlights_mask[..., 0] * h

    return np.clip(result, 0, 1)


def adjust_hsl(arr: np.ndarray, hue_shift: float = 0.0,
               saturation: float = 1.0, lightness: float = 0.0) -> np.ndarray:
    """Adjust HSL of entire image."""
    pil = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    hsv = np.array(pil.convert("HSV")).astype(np.float32)
    hsv[..., 0] = (hsv[..., 0] + hue_shift * 255 / 360) % 256
    hsv[..., 1] = np.clip(hsv[..., 1] * saturation, 0, 255)
    hsv[..., 2] = np.clip(hsv[..., 2] + lightness * 255, 0, 255)
    result = Image.fromarray(hsv.astype(np.uint8), mode="HSV").convert("RGB")
    return np.array(result).astype(np.float32) / 255.0


def add_film_grain(arr: np.ndarray, amount: float = 0.03, size: int = 1) -> np.ndarray:
    """Add luminance-weighted film grain."""
    grain = np.random.normal(0, amount, arr.shape).astype(np.float32)
    # Grain is stronger in shadows (film property)
    lum = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    shadow_boost = np.clip(1.5 - lum * 2, 0.5, 1.5)[..., np.newaxis]
    return np.clip(arr + grain * shadow_boost, 0, 1)


def adjust_vibrance(arr: np.ndarray, vibrance: float = 0.0) -> np.ndarray:
    """Selective saturation — boosts less-saturated colours more (like Lightroom vibrance)."""
    pil = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    hsv = np.array(pil.convert("HSV")).astype(np.float32)
    # Pixels with low saturation get boosted more
    sat = hsv[..., 1] / 255.0
    boost = (1.0 - sat) * vibrance
    hsv[..., 1] = np.clip(hsv[..., 1] + boost * 255, 0, 255)
    result = Image.fromarray(hsv.astype(np.uint8), mode="HSV").convert("RGB")
    return np.array(result).astype(np.float32) / 255.0


def blend(original: np.ndarray, graded: np.ndarray, strength: float) -> np.ndarray:
    """Blend graded result with original based on strength (0=original, 1=full grade)."""
    return original * (1.0 - strength) + graded * strength


def lift_blacks(arr: np.ndarray, lift: float = 0.0) -> np.ndarray:
    """Lift shadows (matte/faded look) or crush them."""
    return np.clip(arr + lift, 0, 1)


# ─────────────────────────────────────────────
# PRESETS
# ─────────────────────────────────────────────

def preset_cinematic(arr: np.ndarray) -> np.ndarray:
    """
    Teal & orange: classic Hollywood blockbuster grade.
    - Crushed blacks with teal push in shadows
    - Orange/warm push in midtones/skin
    - Slightly desaturated greens
    - Lifted contrast S-curve
    """
    # Tone curve — contrasty S
    r = apply_tone_curve(arr[..., 0:1], blacks=0.02, shadows=0.18, midtones=0.52, highlights=0.82, whites=0.98)
    g = apply_tone_curve(arr[..., 1:2], blacks=0.01, shadows=0.16, midtones=0.50, highlights=0.80, whites=0.97)
    b = apply_tone_curve(arr[..., 2:3], blacks=0.04, shadows=0.22, midtones=0.48, highlights=0.78, whites=0.95)
    graded = np.concatenate([r, g, b], axis=-1)

    # 3-way: teal shadows, warm highlights
    graded = apply_color_wheel(
        graded,
        shadows_rgb=(-0.04, 0.02, 0.06),     # teal push in shadows
        midtones_rgb=(0.02, 0.00, -0.01),     # slight warm mid
        highlights_rgb=(0.06, 0.02, -0.04),   # orange/warm highlights
    )

    # Slight vibrance boost
    graded = adjust_vibrance(graded, vibrance=0.15)
    return graded


def preset_retro_film(arr: np.ndarray) -> np.ndarray:
    """
    Kodak/Fuji analogue warmth.
    - Faded lifted shadows (matte)
    - Warm midtones, halation in highlights
    - Slight green-yellow in shadows (aged film)
    - Reduced blue channel
    """
    # Lift blacks (matte/faded)
    arr = lift_blacks(arr, 0.05)

    # Warm tone curve per channel
    r = apply_tone_curve(arr[..., 0:1], blacks=0.06, shadows=0.25, midtones=0.58, highlights=0.85, whites=0.99)
    g = apply_tone_curve(arr[..., 1:2], blacks=0.04, shadows=0.20, midtones=0.52, highlights=0.80, whites=0.96)
    b = apply_tone_curve(arr[..., 2:3], blacks=0.02, shadows=0.14, midtones=0.42, highlights=0.72, whites=0.90)
    graded = np.concatenate([r, g, b], axis=-1)

    # Colour wheel — warm everything
    graded = apply_color_wheel(
        graded,
        shadows_rgb=(0.02, 0.04, -0.03),      # warm green-yellow shadow
        midtones_rgb=(0.04, 0.01, -0.03),      # warm mids
        highlights_rgb=(0.05, 0.02, -0.05),    # amber highlights (halation)
    )

    # Slight desaturation for analogue feel
    graded = adjust_hsl(graded, saturation=0.85, lightness=0.01)
    return graded


def preset_cyberpunk(arr: np.ndarray) -> np.ndarray:
    """
    Neon city: crushed blacks, electric cyan & magenta.
    """
    # Crush blacks hard
    r = apply_tone_curve(arr[..., 0:1], blacks=0.0, shadows=0.05, midtones=0.42, highlights=0.80, whites=0.98)
    g = apply_tone_curve(arr[..., 1:2], blacks=0.0, shadows=0.06, midtones=0.44, highlights=0.82, whites=0.99)
    b = apply_tone_curve(arr[..., 2:3], blacks=0.0, shadows=0.08, midtones=0.48, highlights=0.85, whites=0.99)
    graded = np.concatenate([r, g, b], axis=-1)

    # Neon: cyan shadows, magenta/pink highlights
    graded = apply_color_wheel(
        graded,
        shadows_rgb=(-0.06, 0.08, 0.10),       # cyan/teal shadows
        midtones_rgb=(-0.02, -0.02, 0.05),     # slight blue mid
        highlights_rgb=(0.08, -0.04, 0.10),    # magenta/violet highlights
    )

    # Boost saturation for neon punch
    graded = adjust_hsl(graded, saturation=1.4)
    return graded


def preset_futuristic_warm(arr: np.ndarray) -> np.ndarray:
    """
    Golden hour meets clean technology.
    - Warm golden glow throughout
    - Airy/clean lifted highlights
    - Soft shadow detail
    """
    r = apply_tone_curve(arr[..., 0:1], blacks=0.03, shadows=0.22, midtones=0.58, highlights=0.88, whites=1.0)
    g = apply_tone_curve(arr[..., 1:2], blacks=0.02, shadows=0.18, midtones=0.52, highlights=0.82, whites=0.97)
    b = apply_tone_curve(arr[..., 2:3], blacks=0.01, shadows=0.12, midtones=0.44, highlights=0.74, whites=0.92)
    graded = np.concatenate([r, g, b], axis=-1)

    graded = apply_color_wheel(
        graded,
        shadows_rgb=(0.03, 0.01, -0.02),
        midtones_rgb=(0.05, 0.02, -0.04),      # golden warm mids
        highlights_rgb=(0.04, 0.03, -0.03),    # golden airy highlights
    )

    graded = adjust_vibrance(graded, vibrance=0.2)
    graded = adjust_hsl(graded, lightness=0.02)
    return graded


def preset_moody_dark(arr: np.ndarray) -> np.ndarray:
    """
    Cinematic silence. Desaturated, dark, cool.
    """
    r = apply_tone_curve(arr[..., 0:1], blacks=0.05, shadows=0.14, midtones=0.46, highlights=0.76, whites=0.94)
    g = apply_tone_curve(arr[..., 1:2], blacks=0.05, shadows=0.15, midtones=0.46, highlights=0.76, whites=0.94)
    b = apply_tone_curve(arr[..., 2:3], blacks=0.07, shadows=0.18, midtones=0.50, highlights=0.78, whites=0.95)
    graded = np.concatenate([r, g, b], axis=-1)

    graded = apply_color_wheel(
        graded,
        shadows_rgb=(-0.02, -0.01, 0.05),      # cool blue shadows
        midtones_rgb=(-0.01, 0.00, 0.03),
        highlights_rgb=(0.00, 0.01, 0.03),
    )

    graded = adjust_hsl(graded, saturation=0.65, lightness=-0.01)
    return graded


# ─────────────────────────────────────────────
# NEW PRESETS (v2)
# ─────────────────────────────────────────────

def preset_golden_hour(arr: np.ndarray) -> np.ndarray:
    """
    Amber warmth — glowing skin tones, silky lifted highlights.
    Like the last 20 minutes before sunset.
    """
    r = apply_tone_curve(arr[..., 0:1], blacks=0.03, shadows=0.24, midtones=0.60, highlights=0.90, whites=1.0)
    g = apply_tone_curve(arr[..., 1:2], blacks=0.02, shadows=0.19, midtones=0.52, highlights=0.82, whites=0.97)
    b = apply_tone_curve(arr[..., 2:3], blacks=0.00, shadows=0.10, midtones=0.38, highlights=0.68, whites=0.88)
    graded = np.concatenate([r, g, b], axis=-1)

    graded = apply_color_wheel(
        graded,
        shadows_rgb=(0.04, 0.01, -0.04),       # warm amber shadows
        midtones_rgb=(0.07, 0.03, -0.06),      # deep golden mids
        highlights_rgb=(0.05, 0.04, -0.02),    # soft warm highlights
    )
    graded = adjust_vibrance(graded, vibrance=0.25)
    return graded


def preset_noir(arr: np.ndarray) -> np.ndarray:
    """
    High-contrast B&W. Crushed shadows, bright highlights, zero colour.
    Classic film noir / Magnum photographers aesthetic.
    """
    # Desaturate fully first
    lum = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    bw = np.stack([lum, lum, lum], axis=-1)

    # Hard S-curve for drama
    r = apply_tone_curve(bw[..., 0:1], blacks=0.0, shadows=0.08, midtones=0.50, highlights=0.90, whites=1.0)
    g = apply_tone_curve(bw[..., 1:2], blacks=0.0, shadows=0.08, midtones=0.50, highlights=0.90, whites=1.0)
    b = apply_tone_curve(bw[..., 2:3], blacks=0.0, shadows=0.08, midtones=0.50, highlights=0.90, whites=1.0)
    graded = np.concatenate([r, g, b], axis=-1)

    # Tiny warm push in highlights (classic selenium tone)
    graded = apply_color_wheel(
        graded,
        shadows_rgb=(0.0, 0.0, 0.0),
        midtones_rgb=(0.0, 0.0, 0.0),
        highlights_rgb=(0.02, 0.01, -0.01),
    )
    return graded


def preset_pastel_dream(arr: np.ndarray) -> np.ndarray:
    """
    Soft pink/lavender wash. Airy, lifted, dreamy.
    Perfect for fashion, lifestyle, portrait.
    """
    arr = lift_blacks(arr, 0.08)

    r = apply_tone_curve(arr[..., 0:1], blacks=0.08, shadows=0.30, midtones=0.60, highlights=0.88, whites=0.97)
    g = apply_tone_curve(arr[..., 1:2], blacks=0.07, shadows=0.27, midtones=0.55, highlights=0.83, whites=0.95)
    b = apply_tone_curve(arr[..., 2:3], blacks=0.10, shadows=0.32, midtones=0.62, highlights=0.88, whites=0.98)
    graded = np.concatenate([r, g, b], axis=-1)

    graded = apply_color_wheel(
        graded,
        shadows_rgb=(0.04, 0.01, 0.06),        # lavender shadows
        midtones_rgb=(0.03, 0.00, 0.04),       # soft pink mids
        highlights_rgb=(0.02, 0.01, 0.02),     # warm white highlights
    )
    graded = adjust_hsl(graded, saturation=0.75, lightness=0.03)
    return graded


def preset_forest_earth(arr: np.ndarray) -> np.ndarray:
    """
    Organic desaturated greens, earthy shadows, grounded natural feel.
    Great for outdoor, nature, travel, portraits in nature.
    """
    r = apply_tone_curve(arr[..., 0:1], blacks=0.02, shadows=0.16, midtones=0.48, highlights=0.78, whites=0.95)
    g = apply_tone_curve(arr[..., 1:2], blacks=0.03, shadows=0.18, midtones=0.52, highlights=0.80, whites=0.96)
    b = apply_tone_curve(arr[..., 2:3], blacks=0.01, shadows=0.12, midtones=0.42, highlights=0.72, whites=0.90)
    graded = np.concatenate([r, g, b], axis=-1)

    graded = apply_color_wheel(
        graded,
        shadows_rgb=(-0.01, 0.03, -0.02),      # earthy green shadow
        midtones_rgb=(0.01, 0.02, -0.03),      # warm organic mid
        highlights_rgb=(0.02, 0.02, -0.02),    # slight amber highlight
    )
    graded = adjust_hsl(graded, saturation=0.80)
    return graded


def preset_blue_hour(arr: np.ndarray) -> np.ndarray:
    """
    Twilight coolness. Deep calm blues, clean midtones, cinematic atmosphere.
    Architecture, streets, dusk shooting.
    """
    r = apply_tone_curve(arr[..., 0:1], blacks=0.02, shadows=0.12, midtones=0.44, highlights=0.76, whites=0.93)
    g = apply_tone_curve(arr[..., 1:2], blacks=0.02, shadows=0.14, midtones=0.46, highlights=0.78, whites=0.94)
    b = apply_tone_curve(arr[..., 2:3], blacks=0.04, shadows=0.20, midtones=0.54, highlights=0.84, whites=0.98)
    graded = np.concatenate([r, g, b], axis=-1)

    graded = apply_color_wheel(
        graded,
        shadows_rgb=(-0.05, -0.02, 0.10),      # deep blue shadows
        midtones_rgb=(-0.02, 0.00, 0.06),      # blue-cool mids
        highlights_rgb=(0.00, 0.02, 0.04),     # clean cool highlights
    )
    graded = adjust_hsl(graded, saturation=0.90)
    return graded


def preset_airy_clean(arr: np.ndarray) -> np.ndarray:
    """
    Bright, overexposed-ish, pure whites, barely-there contrast.
    Lifestyle, product, editorial fashion.
    """
    arr = lift_blacks(arr, 0.06)

    r = apply_tone_curve(arr[..., 0:1], blacks=0.06, shadows=0.32, midtones=0.62, highlights=0.90, whites=1.0)
    g = apply_tone_curve(arr[..., 1:2], blacks=0.06, shadows=0.31, midtones=0.61, highlights=0.89, whites=1.0)
    b = apply_tone_curve(arr[..., 2:3], blacks=0.07, shadows=0.32, midtones=0.62, highlights=0.90, whites=1.0)
    graded = np.concatenate([r, g, b], axis=-1)

    graded = apply_color_wheel(
        graded,
        shadows_rgb=(0.02, 0.01, 0.01),
        midtones_rgb=(0.01, 0.01, 0.00),
        highlights_rgb=(0.01, 0.01, 0.01),
    )
    graded = adjust_hsl(graded, saturation=0.80, lightness=0.04)
    return graded


def preset_matte_bronze(arr: np.ndarray) -> np.ndarray:
    """
    Copper/bronze cast, lifted matte blacks, earthy richness.
    Travel, portraits, Instagram-ready warmth.
    """
    arr = lift_blacks(arr, 0.04)

    r = apply_tone_curve(arr[..., 0:1], blacks=0.05, shadows=0.26, midtones=0.58, highlights=0.86, whites=0.98)
    g = apply_tone_curve(arr[..., 1:2], blacks=0.03, shadows=0.18, midtones=0.48, highlights=0.76, whites=0.93)
    b = apply_tone_curve(arr[..., 2:3], blacks=0.02, shadows=0.12, midtones=0.38, highlights=0.66, whites=0.86)
    graded = np.concatenate([r, g, b], axis=-1)

    graded = apply_color_wheel(
        graded,
        shadows_rgb=(0.05, 0.02, -0.04),       # bronze shadow
        midtones_rgb=(0.06, 0.02, -0.05),      # copper mids
        highlights_rgb=(0.04, 0.03, -0.03),    # warm gold highlights
    )
    graded = adjust_hsl(graded, saturation=0.90)
    return graded


def preset_vintage_polaroid(arr: np.ndarray) -> np.ndarray:
    """
    Faded green-yellow cast, washed whites, instant camera nostalgia.
    Casual, social media, retro-casual aesthetic.
    """
    arr = lift_blacks(arr, 0.07)

    r = apply_tone_curve(arr[..., 0:1], blacks=0.07, shadows=0.24, midtones=0.54, highlights=0.82, whites=0.95)
    g = apply_tone_curve(arr[..., 1:2], blacks=0.08, shadows=0.26, midtones=0.57, highlights=0.84, whites=0.96)
    b = apply_tone_curve(arr[..., 2:3], blacks=0.04, shadows=0.16, midtones=0.42, highlights=0.70, whites=0.88)
    graded = np.concatenate([r, g, b], axis=-1)

    graded = apply_color_wheel(
        graded,
        shadows_rgb=(0.01, 0.04, -0.03),       # green-yellow shadow (aged)
        midtones_rgb=(0.02, 0.03, -0.03),      # warm faded mid
        highlights_rgb=(0.03, 0.03, -0.01),    # creamy warm highlight
    )
    graded = adjust_hsl(graded, saturation=0.75, lightness=0.01)
    return graded


# ─────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────

PRESET_FUNCS = {
    "cinematic":        preset_cinematic,
    "retro_film":       preset_retro_film,
    "cyberpunk":        preset_cyberpunk,
    "futuristic_warm":  preset_futuristic_warm,
    "moody_dark":       preset_moody_dark,
    "golden_hour":      preset_golden_hour,
    "noir":             preset_noir,
    "pastel_dream":     preset_pastel_dream,
    "forest_earth":     preset_forest_earth,
    "blue_hour":        preset_blue_hour,
    "airy_clean":       preset_airy_clean,
    "matte_bronze":     preset_matte_bronze,
    "vintage_polaroid": preset_vintage_polaroid,
}


def apply_preset(arr: np.ndarray, preset_id: str, strength: float = 0.85,
                 add_grain: bool = False) -> np.ndarray:
    if preset_id not in PRESET_FUNCS:
        raise ValueError(f"Unknown preset: {preset_id}")

    graded = PRESET_FUNCS[preset_id](arr)

    if add_grain:
        graded = add_film_grain(graded, amount=0.025)

    return blend(arr, graded, strength)


def apply_style_reference(arr: np.ndarray, reference_images: list,
                          strength: float = 0.85) -> np.ndarray:
    """
    Apply 'your style' by matching color statistics from your reference images.
    Uses the color-matcher library (MKL method) for high-quality transfer.
    Falls back to histogram matching if not available.
    """
    # Average the references into one composite "style" image
    # (down-sample each to 512px for speed)
    def resize_arr(a):
        h, w = a.shape[:2]
        scale = min(512 / h, 512 / w, 1.0)
        nh, nw = int(h * scale), int(w * scale)
        pil = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
        pil = pil.resize((nw, nh), Image.LANCZOS)
        return np.array(pil).astype(np.float32) / 255.0

    refs_small = [resize_arr(r) for r in reference_images]

    # Build a composite reference by averaging
    target_h = min(r.shape[0] for r in refs_small)
    target_w = min(r.shape[1] for r in refs_small)
    composite = np.mean(
        [r[:target_h, :target_w] for r in refs_small], axis=0
    )

    try:
        from color_matcher import ColorMatcher
        from color_matcher.io_handler import load_img_file, save_img_file

        src_uint8 = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
        ref_uint8 = (composite * 255).astype(np.uint8)

        cm = ColorMatcher()
        graded_uint8 = cm.transfer(src=src_uint8, ref=ref_uint8, method="mkl")
        graded = graded_uint8.astype(np.float32) / 255.0

    except ImportError:
        # Fallback: per-channel histogram matching
        graded = histogram_match(arr, composite)

    return blend(arr, graded, strength)


def histogram_match(src: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Simple per-channel histogram matching fallback."""
    result = np.empty_like(src)
    for ch in range(3):
        s = src[..., ch].ravel()
        r = ref[..., ch].ravel()
        s_values, s_idx, s_counts = np.unique(s, return_inverse=True, return_counts=True)
        r_values, r_counts = np.unique(r, return_counts=True)
        s_cdf = np.cumsum(s_counts).astype(float) / s.size
        r_cdf = np.cumsum(r_counts).astype(float) / r.size
        interp = np.interp(s_cdf, r_cdf, r_values)
        result[..., ch] = interp[s_idx].reshape(src[..., ch].shape)
    return np.clip(result, 0, 1)
