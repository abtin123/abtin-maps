#!/usr/bin/env python3
"""Generate Abtin's glassmorphism POI sprite atlas.

The atlas keeps the MapLibre sprite contract used by the map styles:
20 icons, 32x32 logical pixels, 36px atlas step, with a 2x retina copy.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "sprites"
ICON_NAMES = [
    "abm-fuel", "abm-parking", "abm-hospital", "abm-pharmacy", "abm-police",
    "abm-school", "abm-restaurant", "abm-cafe", "abm-bank", "abm-hotel",
    "abm-supermarket", "abm-mosque", "abm-toilets", "abm-bus", "abm-airport",
    "abm-attraction", "abm-park", "abm-pitch", "abm-speed-camera", "abm-poi",
]
COLORS = [
    "#12BCEB", "#2D78E6", "#F0445A", "#20C77A", "#694DE0",
    "#7656E8", "#F09A12", "#9A5A38", "#238CDC", "#ED5267",
    "#20B96E", "#D49C18", "#4F6E83", "#308AD0", "#1BAAD0",
    "#F4AB20", "#2BB66E", "#45B93D", "#F06C2F", "#EA4268",
]


def font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def rgba(hex_color: str, alpha: int = 255):
    value = hex_color.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def line(draw, points, fill=(255, 255, 255, 255), width=2, joint="curve"):
    draw.line(points, fill=fill, width=width, joint=joint)


def ellipse(draw, box, fill, outline=None, width=1):
    draw.ellipse(box, fill=fill, outline=outline, width=width)


def polygon(draw, points, fill, outline=None, width=1):
    draw.polygon(points, fill=fill)
    if outline:
        draw.line(points + [points[0]], fill=outline, width=width, joint="curve")


def draw_fuel(d, c):
    white = (248, 252, 255, 255)
    rounded(d, (16, 18, 34, 43), 2, white)
    rounded(d, (19, 21, 31, 25), 1, rgba(c, 230))
    line(d, [(34, 22), (39, 22), (43, 27), (43, 40), (39, 40)], white, 3)
    line(d, [(38, 27), (42, 31)], white, 3)
    line(d, [(13, 44), (38, 44)], white, 3)


def draw_parking(d, c):
    d.text((32, 32), "P", font=font(36), anchor="mm", fill=(248, 252, 255, 255), stroke_width=0)


def draw_cross(d, c, medical=False):
    white = (248, 252, 255, 255)
    rounded(d, (24, 13, 40, 47), 3, white)
    rounded(d, (13, 24, 47, 40), 3, white)
    if medical:
        line(d, [(31, 18), (31, 43)], rgba(c, 150), 1)


def draw_police(d, c):
    white = (248, 252, 255, 255)
    polygon(d, [(31, 12), (45, 17), (42, 37), (31, 47), (20, 37), (17, 17)], white)
    polygon(d, [(31, 21), (34, 27), (41, 27), (36, 31), (38, 37), (31, 33), (24, 37), (26, 31), (21, 27), (28, 27)], rgba(c, 255))


def draw_school(d, c):
    white = (248, 252, 255, 255)
    polygon(d, [(13, 22), (31, 13), (49, 22), (31, 31)], white)
    line(d, [(18, 25), (18, 34), (31, 41), (44, 34), (44, 25)], white, 3)
    line(d, [(31, 31), (31, 42)], rgba(c, 255), 2)
    ellipse(d, (42, 35, 48, 41), white)
    line(d, [(45, 38), (45, 46)], white, 2)


def draw_restaurant(d, c):
    white = (248, 252, 255, 255)
    line(d, [(18, 15), (18, 47)], white, 3)
    for x in (14, 18, 22):
        line(d, [(x, 15), (x, 25)], white, 2)
    line(d, [(14, 15), (14, 21)], white, 2)
    line(d, [(22, 15), (22, 21)], white, 2)
    line(d, [(42, 15), (42, 47)], white, 3)
    line(d, [(42, 15), (36, 25), (48, 25)], white, 2)


def draw_cafe(d, c):
    white = (248, 252, 255, 255)
    rounded(d, (15, 25, 40, 39), 3, white)
    line(d, [(40, 28), (45, 28), (48, 33), (45, 38), (40, 38)], white, 3)
    line(d, [(13, 44), (45, 44)], white, 2)
    d.arc((20, 12, 29, 26), 180, 350, fill=white, width=2)
    d.arc((29, 10, 38, 25), 180, 350, fill=white, width=2)


def draw_bank(d, c):
    white = (248, 252, 255, 255)
    polygon(d, [(12, 22), (31, 13), (50, 22)], white)
    line(d, [(13, 24), (49, 24)], white, 2)
    for x in (18, 27, 36, 45):
        line(d, [(x, 26), (x, 42)], white, 3)
    line(d, [(12, 44), (50, 44)], white, 3)


def draw_hotel(d, c):
    white = (248, 252, 255, 255)
    line(d, [(15, 18), (15, 45)], white, 3)
    rounded(d, (18, 29, 46, 43), 2, white)
    rounded(d, (20, 25, 29, 34), 2, rgba(c, 255))
    line(d, [(15, 29), (47, 29)], rgba(c, 255), 2)
    line(d, [(13, 45), (49, 45)], white, 2)


def draw_supermarket(d, c):
    white = (248, 252, 255, 255)
    line(d, [(13, 17), (18, 17), (22, 39), (43, 39)], white, 3)
    rounded(d, (20, 23, 45, 37), 2, white)
    ellipse(d, (20, 42, 26, 48), white)
    ellipse(d, (40, 42, 46, 48), white)


def draw_mosque(d, c):
    white = (248, 252, 255, 255)
    polygon(d, [(14, 25), (31, 15), (48, 25)], white)
    rounded(d, (17, 25, 45, 42), 1, white)
    for x in (22, 31, 40):
        line(d, [(x, 27), (x, 41)], rgba(c, 255), 3)
    line(d, [(13, 44), (49, 44)], white, 3)
    line(d, [(47, 21), (47, 14)], white, 2)
    ellipse(d, (45, 12, 49, 16), white)


def draw_toilets(d, c):
    d.text((31, 30), "WC", font=font(18), anchor="mm", fill=(248, 252, 255, 255), stroke_width=0)


def draw_bus(d, c):
    white = (248, 252, 255, 255)
    rounded(d, (14, 15, 48, 42), 5, white)
    rounded(d, (18, 20, 44, 29), 2, rgba(c, 255))
    line(d, [(18, 34), (44, 34)], rgba(c, 255), 2)
    ellipse(d, (19, 39, 25, 45), white)
    ellipse(d, (37, 39, 43, 45), white)


def draw_airport(d, c):
    white = (248, 252, 255, 255)
    polygon(d, [(31, 11), (36, 27), (50, 37), (47, 41), (34, 35), (31, 49), (27, 35), (14, 41), (12, 37), (26, 27)], white)


def draw_attraction(d, c):
    white = (248, 252, 255, 255)
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        radius = 18 if i % 2 == 0 else 8
        pts.append((31 + math.cos(angle) * radius, 31 + math.sin(angle) * radius))
    polygon(d, pts, white)


def draw_park(d, c):
    white = (248, 252, 255, 255)
    ellipse(d, (17, 15, 38, 36), white)
    ellipse(d, (28, 13, 48, 36), white)
    ellipse(d, (12, 23, 35, 43), white)
    line(d, [(31, 34), (31, 49)], white, 4)
    line(d, [(23, 49), (39, 49)], white, 3)


def draw_pitch(d, c):
    white = (248, 252, 255, 255)
    ellipse(d, (14, 14, 48, 48), white, rgba(c, 255), 2)
    line(d, [(31, 15), (31, 47)], rgba(c, 255), 2)
    ellipse(d, (26, 26, 36, 36), rgba(c, 255), white, 1)
    polygon(d, [(31, 21), (37, 25), (35, 32), (27, 32), (25, 25)], rgba(c, 255))


def draw_speed_camera(d, c):
    white = (248, 252, 255, 255)
    rounded(d, (13, 23, 43, 41), 3, white)
    rounded(d, (20, 17, 34, 24), 2, white)
    ellipse(d, (18, 27, 28, 37), rgba(c, 255))
    line(d, [(43, 25), (50, 21)], white, 3)
    line(d, [(43, 31), (51, 31)], white, 3)
    line(d, [(43, 37), (50, 41)], white, 3)


def draw_poi(d, c):
    white = (248, 252, 255, 255)
    ellipse(d, (20, 12, 42, 34), white)
    polygon(d, [(20, 27), (42, 27), (31, 49)], white)
    ellipse(d, (27, 19, 35, 27), rgba(c, 255))

DRAWERS: list[Callable] = [
    draw_fuel, draw_parking, lambda d, c: draw_cross(d, c, False),
    lambda d, c: draw_cross(d, c, True), draw_police, draw_school,
    draw_restaurant, draw_cafe, draw_bank, draw_hotel, draw_supermarket,
    draw_mosque, draw_toilets, draw_bus, draw_airport, draw_attraction,
    draw_park, draw_pitch, draw_speed_camera, draw_poi,
]


def make_icon(index: int, scale: int) -> Image.Image:
    design_size = 64
    target_size = 32 * scale
    canvas = Image.new("RGBA", (design_size, design_size), (0, 0, 0, 0))
    c = COLORS[index]
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    ellipse(sd, (6, 8, 58, 60), (0, 0, 0, 105))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4.4))
    canvas = Image.alpha_composite(canvas, shadow)

    # Colored outer bloom, matching the neon halo in the supplied reference.
    bloom = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(bloom)
    ellipse(bd, (3, 3, 61, 61), rgba(c, 105))
    bloom = bloom.filter(ImageFilter.GaussianBlur(7.5))
    canvas = Image.alpha_composite(canvas, bloom)

    d = ImageDraw.Draw(canvas)
    ellipse(d, (6, 4, 58, 56), rgba(c, 190), (235, 251, 255, 245), 1)
    ellipse(d, (10, 8, 54, 52), None, (255, 255, 255, 105), 1)
    # A diagonal top-left frosting highlight makes the badge read as glass on dark maps.
    gloss = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(gloss)
    gd.ellipse((-8, -12, 38, 28), fill=(255, 255, 255, 42))
    gloss = gloss.filter(ImageFilter.GaussianBlur(4))
    canvas = Image.alpha_composite(canvas, gloss)
    d = ImageDraw.Draw(canvas)
    DRAWERS[index](d, c)
    # Keep a clean luminous circular edge on top after glyph rendering.
    d.ellipse((6, 4, 58, 56), outline=(255, 255, 255, 120), width=2)
    if target_size != design_size:
        canvas = canvas.resize((target_size, target_size), Image.Resampling.LANCZOS)
    return canvas


def atlas(scale: int) -> Image.Image:
    step = 36 * scale
    atlas_image = Image.new("RGBA", (180 * scale, 144 * scale), (0, 0, 0, 0))
    for index in range(len(ICON_NAMES)):
        x = (index % 5) * step
        y = (index // 5) * step
        atlas_image.alpha_composite(make_icon(index, scale), (x, y))
    return atlas_image


def metadata(scale: int):
    return {
        name: {
            "width": 32 * scale,
            "height": 32 * scale,
            "x": (index % 5) * 36 * scale,
            "y": (index // 5) * 36 * scale,
            "pixelRatio": scale,
        }
        for index, name in enumerate(ICON_NAMES)
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    atlas(1).save(OUT / "abtin.png", optimize=True)
    atlas(2).save(OUT / "abtin@2x.png", optimize=True)
    (OUT / "abtin.json").write_text(json.dumps(metadata(1), indent=2) + "\n", encoding="utf-8")
    (OUT / "abtin@2x.json").write_text(json.dumps(metadata(2), indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(ICON_NAMES)} glass POI icons in {OUT}")


if __name__ == "__main__":
    main()


def _unused():
    # Kept out of runtime; this file intentionally has no network dependencies.
    return None
