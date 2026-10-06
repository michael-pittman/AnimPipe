"""Inked cel textures derived from the Patty style reference + spec palette."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

P = {
    "NAVY_PRIMARY": "#0E274A",
    "TEAL_SECONDARY": "#088D94",
    "ELECTRIC_BLUE_ACCENT": "#0A7FFF",
    "MAGENTA_ACCENT": "#F51496",
    "SILVER_NEUTRAL": "#BCBBCA",
    "GRAPHITE_NEUTRAL": "#424348",
    "SOFT_WHITE_NEUTRAL": "#F7F7FF",
    "INK_OUTLINE": "#1E2534",
    "INK_INTERIOR": "#2B2D41",
    "SKIN_BASE": "#D28469",
    "SKIN_SHADOW": "#A8756A",
    "SKIN_HIGHLIGHT": "#E8A88C",
    "HAIR_BLACK": "#1F0710",
    "HAIR_MAGENTA_STREAK": "#E986B4",
    "EYE_IRIS": "#7D4A35",
    "EYE_PUPIL": "#2A1810",
    "EYE_SCLERA": "#F5ECE8",
    "LIP_NEUTRAL": "#C97862",
    "LIP_LINE": "#8B4A3A",
    "TEETH_BAND": "#F0EDE8",
    "MOUTH_INTERIOR": "#6B3D45",
    "GLASSES_LENS": "#E8EDF5",
    "LANYARD_STRAP": "#0A7FFF",
    "BADGE_HEADER": "#0E274A",
    "JACKET_NAVY_FILL": "#2B2D41",
    "TROUSER_NAVY_FILL": "#0E274A",
    "CARGO_POCKET": "#152A4A",
    "SNEAKER_WHITE": "#E1E8F5",
    "SNEAKER_EBLUE": "#0A7FFF",
    "SNEAKER_MAGENTA": "#F51496",
}


def rgba_hex(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = hex_color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha


def load_front_figure(reference: Path) -> Image.Image:
    """Isolate the front turnaround figure (no footer palette/UI)."""
    ref = Image.open(reference).convert("RGBA")
    # 480×360 style sheet — front column upper body only.
    figure = ref.crop((22, 98, 122, 292))
    figure = figure.resize((320, 640), Image.Resampling.LANCZOS)
    figure = ImageEnhance.Contrast(figure).enhance(1.06)
    figure = ImageEnhance.Color(figure).enhance(1.08)
    return figure


def sample_tint(figure: Image.Image, box: tuple[float, float, float, float]) -> tuple[int, int, int]:
    w, h = figure.size
    x0, y0, x1, y1 = box
    patch = figure.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))).convert("RGB")
    pixels = list(patch.getdata())
    if not pixels:
        return rgba_hex(P["JACKET_NAVY_FILL"])[:3]
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    return r, g, b


def draw_cel_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    shadow: str | None = None,
    outline: int = 3,
) -> None:
    if shadow:
        sx0, sy0, sx1, sy1 = box
        draw.rounded_rectangle((sx0 + 4, sy0 + 6, sx1 + 4, sy1 + 6), radius=10, fill=rgba_hex(shadow))
    draw.rounded_rectangle(box, radius=10, fill=rgba_hex(fill))
    draw.rounded_rectangle(box, radius=10, outline=rgba_hex(P["INK_OUTLINE"]), width=outline)


def ref_patch(figure: Image.Image, box: tuple[float, float, float, float], out_size: tuple[int, int]) -> Image.Image:
    w, h = figure.size
    x0, y0, x1, y1 = box
    patch = figure.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))).resize(out_size, Image.Resampling.LANCZOS)
    return patch.convert("RGBA")


def draw_hair_updo(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.pieslice((int(w * 0.05), int(h * 0.02), int(w * 0.95), int(h * 0.52)), 200, 340, fill=rgba_hex(P["HAIR_BLACK"]))
    for i in range(10):
        cx = int(w * (0.10 + i * 0.08))
        cy = int(h * (0.04 + (i % 3) * 0.04))
        if cy < int(h * 0.38):
            draw.ellipse((cx, cy, cx + int(w * 0.09), cy + int(h * 0.10)), fill=rgba_hex(P["HAIR_MAGENTA_STREAK"], 190))
    draw.arc((int(w * 0.05), int(h * 0.02), int(w * 0.95), int(h * 0.55)), 200, 340, fill=rgba_hex(P["INK_OUTLINE"]), width=max(3, w // 64))
    return canvas


def draw_hair_fringe(size: tuple[int, int]) -> Image.Image:
    """Forecurls only — transparent over brow/glasses zone."""
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.pieslice((int(w * 0.10), int(h * 0.02), int(w * 0.90), int(h * 0.72)), 200, 340, fill=rgba_hex(P["HAIR_BLACK"]))
    for i in range(4):
        cx = int(w * (0.12 + i * 0.22))
        draw.ellipse((cx, int(h * 0.08), cx + int(w * 0.07), int(h * 0.28)), fill=rgba_hex(P["HAIR_MAGENTA_STREAK"], 170))
    draw.arc((int(w * 0.10), int(h * 0.02), int(w * 0.90), int(h * 0.72)), 200, 340, fill=rgba_hex(P["INK_OUTLINE"]), width=3)
    return canvas


def draw_glasses(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    lw = max(4, w // 48)
    gap = int(w * 0.08)
    ew = int(w * 0.42)
    eh = int(h * 0.72)
    y0 = int(h * 0.14)
    draw.rounded_rectangle((0, y0, ew, y0 + eh), radius=int(w * 0.08), outline=rgba_hex(P["GRAPHITE_NEUTRAL"]), width=lw)
    draw.rounded_rectangle((ew + gap, y0, ew + gap + ew, y0 + eh), radius=int(w * 0.08), outline=rgba_hex(P["GRAPHITE_NEUTRAL"]), width=lw)
    draw.line([(ew, y0 + eh // 2), (ew + gap, y0 + eh // 2)], fill=rgba_hex(P["GRAPHITE_NEUTRAL"]), width=lw)
    draw.rounded_rectangle(
        (int(w * 0.04), y0 + int(h * 0.08), ew - int(w * 0.04), y0 + eh - int(h * 0.08)),
        radius=int(w * 0.06),
        fill=rgba_hex(P["GLASSES_LENS"], 8),
    )
    draw.rounded_rectangle(
        (ew + gap + int(w * 0.04), y0 + int(h * 0.08), ew + gap + ew - int(w * 0.04), y0 + eh - int(h * 0.08)),
        radius=int(w * 0.06),
        fill=rgba_hex(P["GLASSES_LENS"], 8),
    )
    return canvas


def draw_eye(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((2, 4, w - 2, h - 4), fill=rgba_hex(P["EYE_SCLERA"]))
    draw.ellipse((int(w * 0.22), int(h * 0.22), int(w * 0.78), int(h * 0.78)), fill=rgba_hex(P["EYE_IRIS"]))
    draw.ellipse((int(w * 0.38), int(h * 0.38), int(w * 0.62), int(h * 0.62)), fill=rgba_hex(P["EYE_PUPIL"]))
    for lx, ly in ((int(w * 0.28), int(h * 0.30)), (int(w * 0.52), int(h * 0.28)), (int(w * 0.70), int(h * 0.32))):
        draw.line([(lx, ly), (lx + int(w * 0.06), ly - int(h * 0.12))], fill=rgba_hex(P["INK_OUTLINE"]), width=2)
    draw.ellipse((2, 4, w - 2, h - 4), outline=rgba_hex(P["INK_OUTLINE"]), width=2)
    return canvas


def draw_pupil(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((int(w * 0.15), int(h * 0.15), int(w * 0.85), int(h * 0.85)), fill=rgba_hex(P["EYE_PUPIL"]))
    return canvas


def draw_brow(size: tuple[int, int], side: str) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    if side == "L":
        draw.line([(0, int(h * 0.65)), (int(w * 0.75), int(h * 0.25)), (w, int(h * 0.45))], fill=rgba_hex(P["HAIR_BLACK"]), width=max(5, h // 5))
    else:
        draw.line([(0, int(h * 0.45)), (int(w * 0.25), int(h * 0.25)), (w, int(h * 0.65))], fill=rgba_hex(P["HAIR_BLACK"]), width=max(5, h // 5))
    return canvas


def draw_eyelid(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.pieslice((0, -h, w, h * 2), 180, 360, fill=rgba_hex(P["SKIN_BASE"]))
    draw.arc((0, -h, w, h * 2), 180, 360, fill=rgba_hex(P["INK_OUTLINE"]), width=2)
    return canvas


def draw_mouth_closed(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.chord((int(w * 0.08), int(h * 0.25), int(w * 0.92), int(h * 0.82)), 0, 180, fill=rgba_hex(P["LIP_NEUTRAL"]))
    draw.line([(int(w * 0.12), int(h * 0.52)), (int(w * 0.88), int(h * 0.52))], fill=rgba_hex(P["LIP_LINE"]), width=2)
    draw.arc((int(w * 0.08), int(h * 0.25), int(w * 0.92), int(h * 0.82)), 0, 180, fill=rgba_hex(P["INK_OUTLINE"]), width=2)
    return canvas


def draw_teeth_band(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((int(w * 0.06), int(h * 0.28), int(w * 0.94), int(h * 0.72)), radius=8, fill=rgba_hex(P["TEETH_BAND"]))
    draw.line([(int(w * 0.1), int(h * 0.5)), (int(w * 0.9), int(h * 0.5))], fill=rgba_hex(P["LIP_LINE"], 70), width=1)
    draw.rounded_rectangle((int(w * 0.06), int(h * 0.28), int(w * 0.94), int(h * 0.72)), radius=8, outline=rgba_hex(P["INK_OUTLINE"]), width=2)
    return canvas


def draw_face_skin(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((int(w * 0.08), int(h * 0.12), int(w * 0.92), int(h * 0.92)), fill=rgba_hex(P["SKIN_BASE"]))
    draw.ellipse((int(w * 0.14), int(h * 0.18), int(w * 0.86), int(h * 0.86)), fill=rgba_hex(P["SKIN_HIGHLIGHT"], 60))
    draw.ellipse((int(w * 0.18), int(h * 0.48), int(w * 0.38), int(h * 0.62)), fill=rgba_hex(P["SKIN_SHADOW"], 80))
    draw.ellipse((int(w * 0.62), int(h * 0.48), int(w * 0.82), int(h * 0.62)), fill=rgba_hex(P["SKIN_SHADOW"], 80))
    draw.arc((int(w * 0.08), int(h * 0.12), int(w * 0.92), int(h * 0.92)), 200, 340, fill=rgba_hex(P["INK_OUTLINE"]), width=3)
    return canvas


def draw_shirt(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw_cel_rect(draw, (int(w * 0.22), int(h * 0.02), int(w * 0.78), int(h * 0.98)), P["TEAL_SECONDARY"])
    draw.rounded_rectangle((int(w * 0.38), int(h * 0.04), int(w * 0.62), int(h * 0.22)), radius=8, fill=rgba_hex(P["SOFT_WHITE_NEUTRAL"]))
    draw.line([(int(w * 0.5), int(h * 0.22)), (int(w * 0.5), int(h * 0.55))], fill=rgba_hex(P["SOFT_WHITE_NEUTRAL"]), width=int(w * 0.08))
    return canvas


def draw_jacket_flap(size: tuple[int, int], side: str) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    if side == "L":
        box = (int(w * 0.35), int(h * 0.02), int(w * 0.98), int(h * 0.98))
    else:
        box = (int(w * 0.02), int(h * 0.02), int(w * 0.65), int(h * 0.98))
    draw_cel_rect(draw, box, P["JACKET_NAVY_FILL"], P["NAVY_PRIMARY"])
    cuff_y = int(h * 0.72)
    draw.rounded_rectangle((box[0] + 8, cuff_y, box[2] - 8, box[3] - 12), radius=8, fill=rgba_hex(P["TEAL_SECONDARY"]))
    draw.line([(box[0] + 12, int(h * 0.35)), (box[2] - 12, int(h * 0.42))], fill=rgba_hex(P["INK_INTERIOR"]), width=2)
    return canvas


def draw_jacket_back(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw_cel_rect(draw, (int(w * 0.08), int(h * 0.05), int(w * 0.92), int(h * 0.95)), P["JACKET_NAVY_FILL"], P["NAVY_PRIMARY"])
    draw.rectangle((int(w * 0.46), int(h * 0.06), int(w * 0.54), int(h * 0.18)), fill=rgba_hex(P["MAGENTA_ACCENT"]))
    cx, cy = w // 2, int(h * 0.38)
    draw.polygon(
        [
            (cx, cy - 50),
            (cx + 70, cy - 10),
            (cx + 45, cy + 15),
            (cx + 60, cy + 45),
            (cx, cy + 25),
            (cx - 60, cy + 45),
            (cx - 45, cy + 15),
            (cx - 70, cy - 10),
        ],
        fill=rgba_hex(P["SILVER_NEUTRAL"]),
        outline=rgba_hex(P["INK_INTERIOR"]),
    )
    return canvas


def draw_trousers(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw_cel_rect(draw, (int(w * 0.12), int(h * 0.02), int(w * 0.88), int(h * 0.98)), P["TROUSER_NAVY_FILL"], P["CARGO_POCKET"])
    draw.rounded_rectangle((int(w * 0.18), int(h * 0.22), int(w * 0.42), int(h * 0.38)), radius=6, fill=rgba_hex(P["CARGO_POCKET"]))
    draw.rounded_rectangle((int(w * 0.58), int(h * 0.22), int(w * 0.82), int(h * 0.38)), radius=6, fill=rgba_hex(P["CARGO_POCKET"]))
    draw.line([(int(w * 0.5), int(h * 0.04)), (int(w * 0.5), int(h * 0.12))], fill=rgba_hex(P["MAGENTA_ACCENT"]), width=4)
    return canvas


def draw_sneaker(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((int(w * 0.05), int(h * 0.35), int(w * 0.95), int(h * 0.88)), radius=18, fill=rgba_hex(P["SNEAKER_WHITE"]))
    draw.rounded_rectangle((int(w * 0.05), int(h * 0.58), int(w * 0.95), int(h * 0.88)), radius=14, fill=rgba_hex(P["NAVY_PRIMARY"]))
    draw.ellipse((int(w * 0.12), int(h * 0.42), int(w * 0.38), int(h * 0.72)), fill=rgba_hex(P["SNEAKER_EBLUE"], 230))
    draw.ellipse((int(w * 0.62), int(h * 0.42), int(w * 0.88), int(h * 0.72)), fill=rgba_hex(P["SNEAKER_MAGENTA"], 220))
    draw.rounded_rectangle((int(w * 0.05), int(h * 0.35), int(w * 0.95), int(h * 0.88)), radius=18, outline=rgba_hex(P["INK_OUTLINE"]), width=3)
    return canvas


def draw_hand(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((int(w * 0.18), int(h * 0.28), int(w * 0.82), int(h * 0.88)), radius=16, fill=rgba_hex(P["SKIN_BASE"]))
    for i in range(4):
        fx = int(w * (0.22 + i * 0.14))
        draw.rounded_rectangle((fx, int(h * 0.08), fx + int(w * 0.10), int(h * 0.42)), radius=6, fill=rgba_hex(P["SKIN_BASE"]))
    draw.rounded_rectangle((int(w * 0.18), int(h * 0.28), int(w * 0.82), int(h * 0.88)), radius=16, outline=rgba_hex(P["INK_OUTLINE"]), width=3)
    draw.rounded_rectangle((int(w * 0.62), int(h * 0.48), int(w * 0.88), int(h * 0.62)), radius=4, fill=rgba_hex(P["GRAPHITE_NEUTRAL"]))
    return canvas


def draw_sleeve(size: tuple[int, int], part: str) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw_cel_rect(draw, (int(w * 0.12), int(h * 0.02), int(w * 0.88), int(h * 0.98)), P["JACKET_NAVY_FILL"], P["NAVY_PRIMARY"])
    if part == "forearm":
        draw.rounded_rectangle((int(w * 0.18), int(h * 0.02), int(w * 0.82), int(h * 0.18)), radius=8, fill=rgba_hex(P["TEAL_SECONDARY"]))
    return canvas


def draw_neck(size: tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((int(w * 0.28), int(h * 0.05), int(w * 0.72), int(h * 0.95)), radius=10, fill=rgba_hex(P["SKIN_BASE"]))
    draw.rounded_rectangle((int(w * 0.28), int(h * 0.05), int(w * 0.72), int(h * 0.95)), radius=10, outline=rgba_hex(P["INK_OUTLINE"]), width=2)
    return canvas


def transparent(size: tuple[int, int]) -> Image.Image:
    return Image.new("RGBA", size, (0, 0, 0, 0))


def generate_art_textures(reference: Path) -> dict[str, Image.Image]:
    _figure = load_front_figure(reference)
    textures: dict[str, Image.Image] = {}

    textures["TEX_HEAD_SKIN"] = draw_face_skin((512, 512))
    textures["TEX_HAIR_BACK"] = draw_hair_updo((512, 512))
    textures["TEX_HAIR_FRONT"] = draw_hair_fringe((512, 160))
    textures["TEX_GLASSES"] = draw_glasses((512, 128))
    textures["TEX_EYE_L"] = draw_eye((192, 128))
    textures["TEX_EYE_R"] = ImageOps.mirror(textures["TEX_EYE_L"])
    textures["TEX_PUPIL"] = draw_pupil((64, 64))
    textures["TEX_BROW_L"] = draw_brow((192, 64), "L")
    textures["TEX_BROW_R"] = draw_brow((192, 64), "R")
    textures["TEX_EYELID"] = draw_eyelid((192, 80))
    textures["TEX_MOUTH"] = draw_mouth_closed((256, 128))
    mouth_in = Image.new("RGBA", (256, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(mouth_in)
    draw.ellipse((88, 44, 168, 92), fill=rgba_hex(P["MOUTH_INTERIOR"], 240))
    draw.ellipse((88, 44, 168, 92), outline=rgba_hex(P["INK_OUTLINE"]), width=2)
    textures["TEX_MOUTH_INTERIOR"] = mouth_in
    textures["TEX_TEETH"] = draw_teeth_band((256, 64))
    textures["TEX_NECK"] = draw_neck((128, 128))

    textures["TEX_SHIRT"] = draw_shirt((256, 384))
    textures["TEX_JACKET_L"] = draw_jacket_flap((256, 384), "L")
    textures["TEX_JACKET_R"] = draw_jacket_flap((256, 384), "R")
    textures["TEX_JACKET_BACK"] = draw_jacket_back((512, 512))
    textures["TEX_TROUSERS"] = draw_trousers((320, 512))
    textures["TEX_SHOE"] = draw_sneaker((320, 160))
    textures["TEX_HAND"] = draw_hand((192, 192))
    textures["TEX_FOREARM"] = draw_sleeve((192, 256), "forearm")
    textures["TEX_UPPER_ARM"] = draw_sleeve((192, 256), "upper")

    textures["TEX_LANYARD"] = Image.new("RGBA", (64, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(textures["TEX_LANYARD"])
    draw.line([(32, 0), (32, 240)], fill=rgba_hex(P["LANYARD_STRAP"]), width=12)
    textures["TEX_BADGE"] = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(textures["TEX_BADGE"])
    draw.rounded_rectangle((12, 20, 116, 116), radius=8, fill=rgba_hex(P["SOFT_WHITE_NEUTRAL"]))
    draw.rectangle((12, 20, 116, 44), fill=rgba_hex(P["BADGE_HEADER"]))
    draw.rounded_rectangle((12, 20, 116, 116), radius=8, outline=rgba_hex(P["INK_OUTLINE"]), width=2)
    textures["TEX_PATCH"] = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(textures["TEX_PATCH"])
    draw.ellipse((16, 16, 112, 112), fill=rgba_hex(P["SILVER_NEUTRAL"]))
    draw.text((44, 46), "US", fill=rgba_hex(P["NAVY_PRIMARY"]))
    textures["TEX_BELT"] = Image.new("RGBA", (256, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(textures["TEX_BELT"])
    draw_cel_rect(draw, (16, 20, 240, 44), P["GRAPHITE_NEUTRAL"])
    draw.rounded_rectangle((108, 16, 148, 48), radius=4, fill=rgba_hex(P["SILVER_NEUTRAL"]))

    textures["TEX_ANATOMY_HIDDEN"] = transparent((128, 256))
    textures["TEX_PROXY_CHARACTER"] = textures["TEX_JACKET_L"]
    textures["TEX_WATCH"] = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(textures["TEX_WATCH"])
    draw.rounded_rectangle((8, 20, 56, 48), radius=6, fill=rgba_hex(P["GRAPHITE_NEUTRAL"]))
    draw.rounded_rectangle((8, 20, 56, 48), radius=6, outline=rgba_hex(P["INK_OUTLINE"]), width=2)
    return textures
