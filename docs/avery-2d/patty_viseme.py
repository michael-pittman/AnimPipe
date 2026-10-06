"""Cel mouth cards for the Patty Patties front head.

The linked shot never runs app handlers, so each card is a transparent
sprite whose material alpha is a driver on ``GEO_AVERY_HEAD`` shape keys.
At 0 the painted neutral mouth shows through. At 1 the card covers only
the lips.

These are painted sprites. They are not crops of the expression-row busts.
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np
from PIL import Image, ImageDraw

# Spec section 2 / the viseme brief. Upper-lip shade and the lower-lip
# highlight are mixes of these, so the two-tone cel read stays in family.
LIP = (201, 120, 98, 255)       # #C97862
LIP_LINE = (139, 74, 58, 255)   # #8B4A3A
TEETH = (240, 237, 232, 255)    # #F0EDE8
INTERIOR = (107, 61, 69, 255)   # #6B3D45
SKIN = (210, 132, 105, 255)     # #D28469
INK = (30, 37, 52, 255)         # #1E2534

UPPER = (
    int(0.55 * LIP[0] + 0.45 * LIP_LINE[0]),
    int(0.55 * LIP[1] + 0.45 * LIP_LINE[1]),
    int(0.55 * LIP[2] + 0.45 * LIP_LINE[2]),
    255,
)

SPRITE_W = 256
VISEMES = [f"VISEME_{c}" for c in "ABCDEFGHX"]
EXPRESSIONS = ["EXP_smile", "EXP_frown", "EXP_surprise"]
MOUTH_KEYS = VISEMES + EXPRESSIONS

# Open speech shapes. Closed B / C / X do not force the expression cards off;
# the brief's smile expression yields to A D E F G H.
_OPEN_EXPR = "1.0 - min(1.0, a+d+e+f+g+h)"
_OPEN_VARS = [
    ("a", "VISEME_A"),
    ("d", "VISEME_D"),
    ("e", "VISEME_E"),
    ("f", "VISEME_F"),
    ("g", "VISEME_G"),
    ("h", "VISEME_H"),
]

MOUTH_ALPHA: dict[str, str] = {f"VISEME_{c}": c.lower() for c in "ABCDEFGH"}
MOUTH_ALPHA["VISEME_X"] = "0"
MOUTH_VARS: dict[str, list[tuple[str, str]]] = {
    f"VISEME_{c}": [(c.lower(), f"VISEME_{c}")] for c in "ABCDEFGH"
}
MOUTH_VARS["VISEME_X"] = []
for _key, _var in (("EXP_smile", "smile"), ("EXP_frown", "frown"), ("EXP_surprise", "surprise")):
    MOUTH_ALPHA[_key] = f"{_var} * ({_OPEN_EXPR})"
    MOUTH_VARS[_key] = [(_var, _key), *_OPEN_VARS]


def _components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    found: list[list[tuple[int, int]]] = []
    ys, xs = np.where(mask)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        queue: deque[tuple[int, int]] = deque([(y0, x0)])
        seen[y0, x0] = True
        pts = [(y0, x0)]
        while queue:
            y, x = queue.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((ny, nx))
                        pts.append((ny, nx))
        found.append(pts)
    return found


def _lip_pixels(head: Image.Image) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """Dark rose seam, flooded out to the lip body. Returns mask and inclusive box."""
    arr = np.asarray(head.convert("RGBA"))
    height, width = arr.shape[:2]
    red = arr[:, :, 0].astype(np.int16)
    green = arr[:, :, 1].astype(np.int16)
    blue = arr[:, :, 2].astype(np.int16)
    alpha = arr[:, :, 3]
    seam = (alpha > 180) & (red > 80) & (red < 200) & (green < 48) & (blue < 80) & ((red - green) > 70)
    best: list[tuple[int, int]] | None = None
    best_n = 0
    min_count = max(10, int(width * height * 0.00035))
    for pts in _components(seam):
        if len(pts) < min_count:
            continue
        ys = [p[0] for p in pts]
        xs = [p[1] for p in pts]
        bw = max(xs) - min(xs) + 1
        bh = max(ys) - min(ys) + 1
        cx = (sum(xs) / len(xs)) / width
        cy = (sum(ys) / len(ys)) / height
        # The seam is a short horizontal stroke under the nose, not a hair curl.
        if bw < bh or not (0.28 < cx < 0.75 and 0.58 < cy < 0.90):
            continue
        if len(pts) > best_n:
            best_n = len(pts)
            best = pts
    if best is None:
        x0, x1 = int(width * 0.40), int(width * 0.62)
        y0, y1 = int(height * 0.68), int(height * 0.78)
        mask = np.zeros((height, width), dtype=bool)
        mask[y0:y1, x0:x1] = True
        return mask, (x0, y0, x1 - 1, y1 - 1)

    ys = [p[0] for p in best]
    xs = [p[1] for p in best]
    sx0, sy0, sx1, sy1 = min(xs), min(ys), max(xs), max(ys)
    body = (
        (alpha > 160)
        & (red > 90)
        & (red < 210)
        & (green < 88)
        & (blue < 105)
        & ((red - green) > 48)
        & ((red - blue) > 30)
    )
    window = np.zeros((height, width), dtype=bool)
    pad_x = max(4, int(width * 0.08))
    pad_up = max(3, int(height * 0.035))
    pad_dn = max(4, int(height * 0.055))
    window[
        max(0, sy0 - pad_up) : min(height, sy1 + pad_dn + 1),
        max(0, sx0 - pad_x) : min(width, sx1 + pad_x + 1),
    ] = True
    allow = body & window
    seen = np.zeros((height, width), dtype=bool)
    queue = deque()
    for y, x in best:
        if 0 <= y < height and 0 <= x < width:
            seen[y, x] = True
            queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width and not seen[ny, nx] and allow[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
    ys, xs = np.where(seen)
    return seen, (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def measure_mouth(head: Image.Image) -> dict[str, float]:
    """Lip center and size as fractions of ``head`` (y grows downward).

    ``nh`` is the lip thickness, not the lower face.
    """
    _mask, (x0, y0, x1, y1) = _lip_pixels(head)
    width, height = head.size
    return {
        "nx": float((x0 + x1 + 1) / 2.0 / width),
        "ny": float((y0 + y1 + 1) / 2.0 / height),
        "nw": float((x1 - x0 + 1) / width),
        "nh": float((y1 - y0 + 1) / height),
    }


def _pixel_box(head: Image.Image, mouth: dict[str, float]) -> tuple[int, int, int, int]:
    width, height = head.size
    pw = mouth["nw"] * width
    ph = mouth["nh"] * height
    cx = mouth["nx"] * width
    cy = mouth["ny"] * height
    x0 = int(round(cx - pw / 2.0))
    y0 = int(round(cy - ph / 2.0))
    x1 = int(round(x0 + pw))
    y1 = int(round(y0 + ph))
    return x0, y0, x1, y1


def mouth_place_from_head(head_place: dict, head_image: Image.Image) -> dict[str, float]:
    """Map the measured mouth onto the head card. Meters, world center and size.

    Image y grows downward and world z grows upward, so
    ``local z = (0.5 - ny) * head_h``.
    """
    mouth = measure_mouth(head_image)
    head_w = float(head_place["w"])
    head_h = float(head_place["h"])
    local_x = (mouth["nx"] - 0.5) * head_w
    local_z = (0.5 - mouth["ny"]) * head_h
    return {
        "x": float(head_place["x"]) + local_x,
        "z": float(head_place["z"]) + local_z,
        "w": float(mouth["nw"] * head_w),
        "h": float(mouth["nh"] * head_h),
    }


def _resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Downscale RGBA without a dark fringe (premultiplied)."""
    arr = np.asarray(image.convert("RGBA"), dtype=np.float32)
    alpha = arr[:, :, 3:4] / 255.0
    premul = np.empty_like(arr)
    premul[:, :, :3] = arr[:, :, :3] * alpha
    premul[:, :, 3] = arr[:, :, 3]
    small = np.asarray(
        Image.fromarray(np.clip(premul, 0, 255).astype(np.uint8), "RGBA").resize(
            size, Image.Resampling.LANCZOS
        ),
        dtype=np.float32,
    )
    scale = small[:, :, 3:4] / 255.0
    rgb = np.zeros_like(small[:, :, :3])
    mask = scale[:, :, 0] > 1e-3
    rgb[mask] = small[:, :, :3][mask] / scale[mask]
    out = np.zeros_like(small)
    out[:, :, :3] = np.clip(rgb, 0, 255)
    out[:, :, 3] = small[:, :, 3]
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def _sample_skin(head: Image.Image, mask: np.ndarray) -> tuple[int, int, int, int]:
    """Median of the skin ring just outside the lips."""
    arr = np.asarray(head.convert("RGBA"))
    dilated = mask.copy()
    for _ in range(3):
        grown = dilated.copy()
        grown[1:] |= dilated[:-1]
        grown[:-1] |= dilated[1:]
        grown[:, 1:] |= dilated[:, :-1]
        grown[:, :-1] |= dilated[:, 1:]
        dilated = grown
    ring = dilated & ~mask & (arr[:, :, 3] > 200)
    red = arr[:, :, 0].astype(np.int16)
    green = arr[:, :, 1].astype(np.int16)
    blue = arr[:, :, 2].astype(np.int16)
    skin = ring & (red > 160) & (green > 80) & (green < 170) & (blue < 140) & ((red - blue) > 40)
    if int(skin.sum()) < 8:
        return SKIN
    sample = arr[skin][:, :3]
    med = np.median(sample, axis=0)
    return int(med[0]), int(med[1]), int(med[2]), 255


def _cover(mask: np.ndarray, box: tuple[int, int, int, int], color: tuple[int, int, int, int], size: tuple[int, int]) -> Image.Image:
    """Skin-colored lip silhouette so a smaller shape still hides the painted mouth."""
    x0, y0, x1, y1 = box
    crop = mask[y0 : y1 + 1, x0 : x1 + 1]
    dilated = crop.copy()
    dilated[1:] |= crop[:-1]
    dilated[:-1] |= crop[1:]
    dilated[:, 1:] |= crop[:, :-1]
    dilated[:, :-1] |= crop[:, 1:]
    plate = Image.fromarray(np.where(dilated, 255, 0).astype(np.uint8), "L")
    plate = plate.resize(size, Image.Resampling.NEAREST)
    sprite = Image.new("RGBA", size, (0, 0, 0, 0))
    sprite.paste(Image.new("RGBA", size, color), mask=plate)
    return sprite


def _quad(p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float], steps: int = 28) -> list[tuple[float, float]]:
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        pts.append((
            u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
        ))
    return pts


def _ellipse(cx: float, cy: float, rx: float, ry: float, steps: int = 56) -> list[tuple[float, float]]:
    return [
        (cx + rx * math.cos(t), cy + ry * math.sin(t))
        for t in (i * 2.0 * math.pi / steps for i in range(steps))
    ]


def _scale_pts(pts: list[tuple[float, float]], scale: int) -> list[tuple[float, float]]:
    return [(x * scale, y * scale) for x, y in pts]


class _Pen:
    """Draw in sprite pixels; the canvas is supersampled."""

    def __init__(self, width: int, height: int, scale: int = 4):
        self.width = width
        self.height = height
        self.scale = scale
        self.image = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)
        # Hairline ink once the sprite is scaled onto the head's lip box.
        # Keep the outline thinner than the lip fill so a small card
        # does not collapse into a black bar.
        self.ink = max(2, int(round(0.16 * (width / 27.0) * scale)))
        self.seam = max(2, int(round(0.22 * (width / 27.0) * scale)))

    def poly(self, pts: list[tuple[float, float]], fill, outline=None, width: int = 0) -> None:
        scaled = _scale_pts(pts, self.scale)
        if outline is None or width <= 0:
            self.draw.polygon(scaled, fill=fill)
        else:
            self.draw.polygon(scaled, fill=fill, outline=outline, width=width)

    def line(self, pts: list[tuple[float, float]], fill, width: int) -> None:
        self.draw.line(_scale_pts(pts, self.scale), fill=fill, width=width, joint="curve")

    def finish(self) -> Image.Image:
        return _resize(self.image, (self.width, self.height))


def _closed_lips(pen: _Pen, *, smile: float, press: float) -> None:
    """Closed lip silhouette. ``smile`` > 0 lifts the corners."""
    w, h = pen.width, pen.height
    cx, cy = w * 0.50, h * 0.52
    half_w = w * (0.46 - 0.06 * press)
    half_h = h * (0.38 - 0.10 * press)
    lift = h * 0.18 * smile
    left = (cx - half_w, cy - lift)
    right = (cx + half_w, cy - lift)
    upper = _quad(left, (cx, cy - half_h * 0.95 - lift * 0.25), right)
    lower = _quad(right, (cx, cy + half_h * 1.05), left)
    seam_l = (cx - half_w * 0.90, cy - lift * 0.72 + h * 0.02)
    seam_r = (cx + half_w * 0.90, cy - lift * 0.72 + h * 0.02)
    seam_c = (cx, cy + h * 0.05 + lift * 0.15)
    seam = _quad(seam_l, seam_c, seam_r)
    outer = upper + lower
    pen.poly(outer, UPPER)
    pen.poly(seam + lower, LIP)
    pen.line(seam, LIP_LINE, pen.seam)
    pen.poly(outer, None, INK, pen.ink)


def _teeth_band(pen: _Pen, cx: float, top: float, band_w: float, band_h: float) -> None:
    """One merged upper pill. No pegs, no gaps, no lower arch."""
    scale = pen.scale
    x0 = (cx - band_w / 2.0) * scale
    y0 = top * scale
    x1 = (cx + band_w / 2.0) * scale
    y1 = (top + band_h) * scale
    if x1 - x0 < 4 or y1 - y0 < 3:
        return
    radius = max(1.0, min((y1 - y0) / 2.0, (x1 - x0) / 2.0))
    pen.draw.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=TEETH)


def _open_mouth(
    pen: _Pen,
    *,
    outer: tuple[float, float],
    inner: tuple[float, float],
    teeth: float = 0.0,
    teeth_frac: float = 0.72,
    cy_shift: float = 0.0,
) -> None:
    """Oval opening. ``outer`` / ``inner`` are (rx, ry) as fractions of the sprite.

    ``teeth`` is the band height as a fraction of the inner opening. 0 hides teeth.
    ``teeth_frac`` is the band width as a fraction of the inner width (D stays ≤ 0.5).
    """
    w, h = pen.width, pen.height
    cx, cy = w * 0.50, h * (0.52 + cy_shift)
    orx, ory = outer[0] * w, outer[1] * h
    irx, iry = inner[0] * w, inner[1] * h
    outer_pts = _ellipse(cx, cy, orx, ory)
    inner_pts = _ellipse(cx, cy, irx, iry)
    pen.poly(outer_pts, LIP, INK, pen.ink)
    # Upper half of the lip ring reads darker, like the sheet.
    upper_clip = [p for p in outer_pts if p[1] <= cy + ory * 0.05]
    if len(upper_clip) >= 3:
        pen.poly(upper_clip + [(cx + orx, cy), (cx - orx, cy)], UPPER)
    pen.poly(outer_pts, None, INK, pen.ink)
    pen.poly(inner_pts, INTERIOR)
    if teeth > 0:
        # Flush with the upper lip: one cap, no dark gutter above it.
        top = cy - iry
        band_h = max(h * 0.05, iry * 2.0 * teeth)
        band_w = max(4.0, irx * 2.0 * teeth_frac)
        _teeth_band(pen, cx, top, band_w, band_h)
    pen.poly(inner_pts, None, LIP_LINE, max(2, pen.ink // 3))


def _purse(pen: _Pen) -> None:
    """Tight round pucker. A circle in pixels, not a wide almond."""
    w, h = pen.width, pen.height
    cx, cy = w * 0.50, h * 0.50
    radius = h * 0.40
    pen.poly(_ellipse(cx, cy, radius, radius), UPPER)
    pen.poly(_ellipse(cx, cy, radius * 0.72, radius * 0.72), LIP)
    pen.poly(_ellipse(cx, cy, radius * 0.34, radius * 0.36), INTERIOR)
    pen.poly(_ellipse(cx, cy, radius, radius), None, INK, pen.ink)


def _frown(pen: _Pen) -> None:
    """Corners down, and thick enough to survive the lip-sized card.

    The center of the lower lip stays above the corners so the shape is
    not a pushed-out pout.
    """
    w, h = pen.width, pen.height
    cx, cy = w * 0.50, h * 0.50
    half_w = w * 0.42
    left_u = (cx - half_w, cy + h * 0.08)
    right_u = (cx + half_w, cy + h * 0.08)
    left_l = (cx - half_w, cy + h * 0.30)
    right_l = (cx + half_w, cy + h * 0.30)
    upper = _quad(left_u, (cx, cy - h * 0.34), right_u)
    lower = _quad(right_l, (cx, cy - h * 0.02), left_l)
    seam = _quad(
        (cx - half_w * 0.78, cy + h * 0.16),
        (cx, cy - h * 0.16),
        (cx + half_w * 0.78, cy + h * 0.16),
    )
    pen.poly(upper + lower, UPPER)
    pen.poly(seam + lower, LIP)
    pen.line(seam, LIP_LINE, pen.seam)
    pen.poly(upper + lower, None, INK, pen.ink)


def _paint(width: int, height: int, kind: str) -> Image.Image:
    pen = _Pen(width, height)
    # outer/inner are (rx, ry) as fractions of sprite width and height.
    # The canvas is about 1.9:1, so a vertical oval keeps rx small and ry large.
    if kind == "VISEME_A":
        _open_mouth(pen, outer=(0.24, 0.48), inner=(0.12, 0.34), teeth=0.13, teeth_frac=0.72)
    elif kind == "VISEME_B":
        _closed_lips(pen, smile=0.0, press=0.55)
    elif kind == "VISEME_C":
        _purse(pen)
    elif kind == "VISEME_D":
        # Wide "eh". Band width stays under half the opening.
        _open_mouth(pen, outer=(0.46, 0.42), inner=(0.34, 0.22), teeth=0.16, teeth_frac=0.46)
    elif kind == "VISEME_E":
        _open_mouth(pen, outer=(0.47, 0.34), inner=(0.36, 0.12), teeth=0.28, teeth_frac=0.40, cy_shift=-0.02)
    elif kind == "VISEME_F":
        # Lower lip up under a single upper edge. Almost no interior.
        _open_mouth(pen, outer=(0.46, 0.40), inner=(0.30, 0.12), teeth=0.72, teeth_frac=0.86)
    elif kind == "VISEME_G":
        _open_mouth(pen, outer=(0.40, 0.44), inner=(0.26, 0.24), teeth=0.14, teeth_frac=0.68)
    elif kind == "VISEME_H":
        _open_mouth(pen, outer=(0.47, 0.47), inner=(0.36, 0.32), teeth=0.12, teeth_frac=0.78)
    elif kind == "VISEME_X":
        _closed_lips(pen, smile=0.32, press=0.06)
    elif kind == "EXP_smile":
        _closed_lips(pen, smile=0.82, press=0.0)
    elif kind == "EXP_frown":
        _frown(pen)
    elif kind == "EXP_surprise":
        _open_mouth(pen, outer=(0.16, 0.44), inner=(0.07, 0.26), teeth=0.0)
    else:
        raise KeyError(kind)
    return pen.finish()


def build_mouth_textures(head: Image.Image) -> dict[str, Image.Image]:
    """Same-size RGBA lip sprites, transparent outside the mouth."""
    mouth = measure_mouth(head)
    mask, box = _lip_pixels(head)
    x0, y0, x1, y1 = _pixel_box(head, mouth)
    # Prefer the detector box; the fraction round-trip matches it.
    box = (x0, y0, x1 - 1, y1 - 1)
    pw = max(1, x1 - x0)
    ph = max(1, y1 - y0)
    height = max(48, int(round(SPRITE_W * ph / pw)))
    skin = _sample_skin(head, mask)
    base = _cover(mask, box, skin, (SPRITE_W, height))
    textures: dict[str, Image.Image] = {}
    for name in MOUTH_KEYS:
        sprite = base.copy()
        sprite.alpha_composite(_paint(SPRITE_W, height, name))
        textures[name] = sprite
    return textures


def _head_card(reference: str) -> Image.Image:
    """Top ~21% of the keyed front figure: the head card the brief measures."""
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from patty_parts import _key_figure, load_views, tight_crop

    views = load_views(Path(reference))
    keyed = _key_figure(views["front"])
    figure, _box = tight_crop(keyed, 1)
    cut = int(round(figure.size[1] * 0.205))
    return figure.crop((0, 0, figure.size[0], cut))


def _composite(head: Image.Image, sprite: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    x0, y0, x1, y1 = box
    scaled = _resize(sprite, (max(1, x1 - x0), max(1, y1 - y0)))
    out = head.convert("RGBA").copy()
    out.alpha_composite(scaled, (x0, y0))
    return out


def _write_previews(reference: str) -> dict[str, float]:
    head = _head_card(reference)
    mouth = measure_mouth(head)
    textures = build_mouth_textures(head)
    x0, y0, x1, y1 = _pixel_box(head, mouth)
    marked = head.convert("RGBA").copy()
    draw = ImageDraw.Draw(marked)
    draw.rectangle((x0, y0, x1 - 1, y1 - 1), outline=(0, 220, 70, 255), width=1)
    marked.resize((marked.size[0] * 3, marked.size[1] * 3), Image.Resampling.NEAREST).save("/tmp/mouth-on-head.png")

    names = ["neutral", "VISEME_A", "VISEME_B", "VISEME_E", "EXP_smile", "EXP_surprise", "EXP_frown"]
    cells = []
    for name in names:
        if name == "neutral":
            cell = head.convert("RGBA")
        else:
            cell = _composite(head, textures[name], (x0, y0, x1, y1))
        cell = cell.resize((cell.size[0] * 3, cell.size[1] * 3), Image.Resampling.NEAREST)
        labeled = Image.new("RGBA", (cell.size[0], cell.size[1] + 28), (246, 244, 240, 255))
        labeled.paste(cell, (0, 0))
        ImageDraw.Draw(labeled).text((8, cell.size[1] + 6), name, fill=(20, 24, 32, 255))
        cells.append(labeled)
    strip = Image.new("RGBA", (sum(c.size[0] for c in cells), cells[0].size[1]), (246, 244, 240, 255))
    cursor = 0
    for cell in cells:
        strip.paste(cell, (cursor, 0))
        cursor += cell.size[0]
    strip.save("/tmp/mouth-strip.png")

    # Sprite sheet plus a tight mouth zoom, so the lip shapes can be checked
    # without the rest of the head.
    sample = next(iter(textures.values()))
    sw, sh = sample.size
    sheet = Image.new("RGBA", (sw * len(MOUTH_KEYS), sh + 22), (40, 44, 52, 255))
    pen = ImageDraw.Draw(sheet)
    for i, name in enumerate(MOUTH_KEYS):
        sheet.paste(textures[name], (i * sw, 0), textures[name])
        pen.text((i * sw + 4, sh + 4), name.replace("VISEME_", "").replace("EXP_", ""), fill=(240, 236, 230, 255))
    zoom_h = (y1 - y0) * 10
    zoom_w = (x1 - x0) * 10
    zoom = Image.new("RGBA", (zoom_w * len(names), zoom_h + 18), (40, 44, 52, 255))
    zpen = ImageDraw.Draw(zoom)
    for i, name in enumerate(names):
        cell = head.convert("RGBA") if name == "neutral" else _composite(head, textures[name], (x0, y0, x1, y1))
        crop = cell.crop((x0, y0, x1, y1)).resize((zoom_w, zoom_h), Image.Resampling.NEAREST)
        zoom.paste(crop, (i * zoom_w, 0))
        zpen.text((i * zoom_w + 4, zoom_h + 2), name, fill=(240, 236, 230, 255))
    preview = Image.new("RGBA", (max(sheet.size[0], zoom.size[0]), sheet.size[1] + zoom.size[1] + 12), (40, 44, 52, 255))
    preview.paste(sheet, (0, 0))
    preview.paste(zoom, (0, sheet.size[1] + 12))
    preview.save("/tmp/mouth-preview.png")
    return mouth


if __name__ == "__main__":
    measured = _write_previews("/workspace/media/reference/patty-patties-style-hires.png")
    sample = build_mouth_textures(_head_card("/workspace/media/reference/patty-patties-style-hires.png"))
    size = next(iter(sample.values())).size
    print("measure", {k: round(v, 4) for k, v in measured.items()})
    print("sprite", size, "keys", list(sample))
    print("alpha", MOUTH_ALPHA)
