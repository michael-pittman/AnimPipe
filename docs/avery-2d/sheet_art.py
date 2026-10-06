"""Textures cut from patty-patties-style.png (no procedural body/face drawing)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# Master sheet pixel crops — exclude title, palette, footer UI.
# Measured on the 480×360 sheet: front | 3/4 | side | back, with a paper margin
# so the figure key can flood from the crop edge without eating the white shirt.
SHEET_VIEWS = {
    "front": (14, 40, 84, 270),
    "three_quarter": (86, 40, 154, 270),
    "side": (156, 40, 210, 270),
    "back": (214, 40, 278, 270),
}

VIEW_CHAR_BOUNDS = {
    "front": None,
    "side": None,
    "back": None,
}

# Four bust portraits (top-right row); exclude turnaround shoulder sliver and caption band below.
EXPR_HEADS = (276, 58, 472, 112)
EXPR_PANELS = 4

# Action-pose column on patty-patties-style.png (arm extended / present).
SHEET_ACTION_ARM_OUT = (292, 122, 350, 266)
SHEET_ACTION_POINT = (362, 122, 420, 266)

PART_FRONT: dict[str, tuple[float, float, float, float]] = {
    "TEX_HAIR_BACK": (0.12, 0.00, 0.88, 0.14),
    "TEX_HAIR_FRONT": (0.10, 0.02, 0.90, 0.16),
    "TEX_HEAD_SKIN": (0.18, 0.08, 0.82, 0.175),
    "TEX_BROW_L": (0.22, 0.11, 0.46, 0.145),
    "TEX_BROW_R": (0.54, 0.11, 0.78, 0.145),
    "TEX_EYE_L": (0.24, 0.125, 0.46, 0.175),
    "TEX_EYE_R": (0.54, 0.125, 0.76, 0.175),
    "TEX_PUPIL": (0.42, 0.13, 0.58, 0.17),
    "TEX_EYELID": (0.20, 0.12, 0.80, 0.18),
    "TEX_GLASSES": (0.20, 0.12, 0.80, 0.185),
    "TEX_MOUTH": (0.38, 0.158, 0.62, 0.178),
    "TEX_TEETH": (0.40, 0.156, 0.60, 0.170),
    "TEX_MOUTH_INTERIOR": (0.39, 0.155, 0.61, 0.180),
    "TEX_NECK": (0.34, 0.18, 0.66, 0.24),
    "TEX_SHIRT": (0.30, 0.22, 0.70, 0.44),
    "TEX_JACKET_L": (0.00, 0.20, 0.38, 0.48),
    "TEX_JACKET_R": (0.62, 0.20, 0.90, 0.48),
    "TEX_JACKET_BACK": (0.08, 0.20, 0.92, 0.52),
    "TEX_TROUSERS": (0.14, 0.42, 0.86, 0.88),
    "TEX_BELT": (0.16, 0.40, 0.84, 0.44),
    "TEX_HAND": (0.00, 0.36, 0.20, 0.52),
    "TEX_HAND_R": (0.76, 0.32, 0.94, 0.54),
    "TEX_FOREARM": (0.00, 0.30, 0.22, 0.42),
    "TEX_UPPER_ARM": (0.00, 0.22, 0.26, 0.34),
    "TEX_SHOE": (0.12, 0.825, 0.88, 0.915),
    "TEX_LANYARD": (0.38, 0.24, 0.62, 0.58),
    "TEX_BADGE": (0.40, 0.44, 0.60, 0.54),
    "TEX_PATCH": (0.72, 0.24, 0.86, 0.33),
    "TEX_ANATOMY_HIDDEN": (0.0, 0.0, 0.01, 0.01),
    "TEX_PROXY_CHARACTER": (0.00, 0.20, 0.38, 0.48),
}

SIDE_OVERRIDES = {
    "TEX_JACKET_L": (0.02, 0.34, 0.55, 0.62),
    "TEX_JACKET_R": (0.45, 0.34, 0.98, 0.62),
    "TEX_TROUSERS": (0.20, 0.52, 0.80, 0.92),
    "TEX_SHOE": (0.25, 0.84, 0.75, 0.99),
    "TEX_HAND": (0.35, 0.46, 0.65, 0.58),
    "TEX_HEAD_SKIN": (0.30, 0.12, 0.75, 0.42),
    "TEX_HAIR_BACK": (0.15, 0.00, 0.85, 0.28),
}

BACK_OVERRIDES = {
    "TEX_JACKET_BACK": (0.08, 0.32, 0.92, 0.65),
    "TEX_JACKET_L": (0.08, 0.32, 0.92, 0.65),
    "TEX_JACKET_R": (0.08, 0.32, 0.92, 0.65),
    "TEX_TROUSERS": (0.18, 0.52, 0.82, 0.90),
    "TEX_SHOE": (0.20, 0.86, 0.80, 0.99),
    "TEX_HAIR_BACK": (0.10, 0.00, 0.90, 0.24),
    "TEX_SHIRT": (0.28, 0.22, 0.72, 0.44),
}


def _load_views(reference: Path) -> dict[str, Image.Image]:
    master = Image.open(reference).convert("RGBA")
    return {name: master.crop(box) for name, box in SHEET_VIEWS.items()}


def _char_bounds(view: Image.Image, pad: int = 2) -> tuple[int, int, int, int]:
    arr = np.array(view.convert("RGBA"))
    rgb = arr[:, :, :3].astype(np.int16)
    w, h = view.size
    lum = np.sum(rgb, axis=2)
    mask = (lum < 720) & (lum > 120)
    x_mid = w // 2
    col = mask[:, max(0, x_mid - 12) : min(w, x_mid + 12)]
    ys_c, xs_c = np.where(col)
    if len(ys_c) == 0:
        ys, xs = np.where(mask)
        if len(xs) == 0:
            return int(w * 0.04), int(h * 0.02), int(w * 0.96), int(h * 0.98)
        y0, y1 = int(ys.min()), int(ys.max())
        x0, x1 = int(xs.min()), int(xs.max())
    else:
        y0, y1 = int(ys_c.min()), int(ys_c.max())
        sub = mask[y0 : y1 + 1]
        ys, xs = np.where(sub)
        x0, x1 = int(xs.min()), int(xs.max())
    return max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)


def _proximity_mask(ink_core: np.ndarray, radius: int) -> np.ndarray:
    from collections import deque

    h, w = ink_core.shape
    dist = np.full((h, w), radius + 1, dtype=np.int16)
    queue: deque[tuple[int, int]] = deque()
    for y, x in zip(*np.where(ink_core)):
        dist[y, x] = 0
        queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        d = dist[y, x]
        if d >= radius:
            continue
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and dist[ny, nx] > d + 1:
                dist[ny, nx] = d + 1
                queue.append((ny, nx))
    return dist <= radius


def _key_figure(patch: Image.Image) -> Image.Image:
    """Cut a turnaround figure out of the pale sheet grid.

    Flood only pale paper that can reach the crop edge without crossing ink.
    Interior whites (shirt, sneakers, badge) stay. Specks and a 1px paper
    fringe are dropped so the card reads as the drawing, not a shaded blob.
    """
    from collections import deque

    arr = np.array(patch.convert("RGBA")).copy()
    h, w = arr.shape[:2]
    if h < 2 or w < 2:
        return Image.fromarray(arr)
    rgb = arr[:, :, :3].astype(np.float32)
    lum = rgb.mean(axis=2)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    sat = (mx - mn) / (mx + 1.0)
    barrier = (lum < 175.0) | (sat > 0.18)
    pale = (lum > 188.0) & (sat < 0.14)
    # Close 1px gaps in the ink so the flood cannot leak through antialiasing.
    closed = barrier.copy()
    closed[1:, :] |= barrier[:-1, :]
    closed[:-1, :] |= barrier[1:, :]
    closed[:, 1:] |= barrier[:, :-1]
    closed[:, :-1] |= barrier[:, 1:]
    removed = np.zeros((h, w), dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    def consider(y: int, x: int) -> None:
        if removed[y, x] or closed[y, x] or not pale[y, x]:
            return
        removed[y, x] = True
        queue.append((y, x))

    for x in range(w):
        consider(0, x)
        consider(h - 1, x)
    for y in range(h):
        consider(y, 0)
        consider(y, w - 1)
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                consider(ny, nx)
    alpha = np.where(removed, 0, 255).astype(np.uint8)
    # Eat the pale halo sitting on the outer silhouette.
    pale_u8 = pale
    trans = alpha == 0
    neighbor_trans = trans.copy()
    neighbor_trans[1:, :] |= trans[:-1, :]
    neighbor_trans[:-1, :] |= trans[1:, :]
    neighbor_trans[:, 1:] |= trans[:, :-1]
    neighbor_trans[:, :-1] |= trans[:, 1:]
    alpha[pale_u8 & neighbor_trans] = 0
    alpha = _drop_specks(alpha, min_area=36)
    arr[:, :, 3] = alpha
    _drop_leg_gap(arr)
    return Image.fromarray(arr)


def _drop_leg_gap(arr: np.ndarray) -> None:
    """Clear the sheet showing between the legs when the shoes seal it off from the edge."""
    from collections import deque

    h, w = arr.shape[:2]
    rgb = arr[:, :, :3].astype(np.int16)
    alpha = arr[:, :, 3]
    paper = (alpha > 0) & (rgb.min(axis=2) > 228) & (np.abs(rgb[:, :, 0] - rgb[:, :, 2]) < 18)
    seen = np.zeros((h, w), dtype=bool)
    ys, xs = np.where(paper)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        queue: deque[tuple[int, int]] = deque([(y0, x0)])
        seen[y0, x0] = True
        comp: list[tuple[int, int]] = [(y0, x0)]
        y_min = y_max = y0
        while queue:
            y, x = queue.popleft()
            y_min = min(y_min, y)
            y_max = max(y_max, y)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and paper[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
                    comp.append((ny, nx))
        height = y_max - y_min
        y_center = (y_min + y_max) * 0.5
        if height > h * 0.12 and y_center > h * 0.5:
            for y, x in comp:
                alpha[y, x] = 0


def _drop_specks(alpha: np.ndarray, min_area: int) -> np.ndarray:
    """Keep the figure; drop grid crumbs and shoe-floor specks."""
    from collections import deque

    h, w = alpha.shape
    opaque = alpha > 0
    seen = np.zeros((h, w), dtype=bool)
    out = np.zeros((h, w), dtype=np.uint8)
    ys, xs = np.where(opaque)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        queue: deque[tuple[int, int]] = deque([(y0, x0)])
        seen[y0, x0] = True
        comp: list[tuple[int, int]] = [(y0, x0)]
        while queue:
            y, x = queue.popleft()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and opaque[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
                    comp.append((ny, nx))
        if len(comp) < min_area:
            continue
        for y, x in comp:
            out[y, x] = 255
    return out


def _key_alpha(patch: Image.Image, tol: float = 42.0) -> Image.Image:
    """Keep pixels within a short walk of dark ink; everything else is transparent."""
    from collections import deque

    arr = np.array(patch.convert("RGBA")).copy()
    h, w = arr.shape[:2]
    if h < 2 or w < 2:
        return Image.fromarray(arr)
    rgb = arr[:, :, :3].astype(np.float32)
    lum = rgb.mean(axis=2)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    sat = (mx - mn) / (mx + 1.0)
    ink_core = (lum < 108) | ((sat > 0.15) & (lum < 220))
    radius = max(4, min(12, int(max(h, w) * 0.055)))
    keep = _proximity_mask(ink_core, radius)
    edge_samples = np.concatenate([rgb[0, :], rgb[-1, :], rgb[:, 0], rgb[:, -1]], axis=0)
    bg = np.median(edge_samples, axis=0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    paper = (dist < tol) | ((lum > 208) & (sat < 0.16))
    paper &= ~ink_core
    removed = np.zeros((h, w), dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if paper[y, x]:
                removed[y, x] = True
                queue.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if paper[y, x] and not removed[y, x]:
                removed[y, x] = True
                queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and paper[ny, nx] and not removed[ny, nx]:
                removed[ny, nx] = True
                queue.append((ny, nx))
    keep &= ~removed
    arr[:, :, 3] = np.where(keep, 255, 0).astype(np.uint8)
    return Image.fromarray(arr)


def _crop_norm(
    view: Image.Image,
    bbox: tuple[float, float, float, float],
    out_min: int = 64,
    view_name: str = "front",
) -> Image.Image:
    manual = VIEW_CHAR_BOUNDS.get(view_name)
    x0, y0, x1, y1 = manual if manual else _char_bounds(view)
    cw, ch = x1 - x0, y1 - y0
    nx0, ny0, nx1, ny1 = bbox
    px0 = int(x0 + nx0 * cw)
    px1 = int(x0 + nx1 * cw)
    py0 = int(y0 + ny0 * ch)
    py1 = int(y0 + ny1 * ch)
    if px1 <= px0 + 2 or py1 <= py0 + 2:
        return Image.new("RGBA", (out_min, out_min), (0, 0, 0, 0))
    patch = view.crop((px0, py0, px1, py1))
    long_side = max(patch.size)
    scale = max(out_min, long_side)
    if long_side < out_min:
        patch = patch.resize(
            (max(1, int(patch.size[0] * scale / long_side)), max(1, int(patch.size[1] * scale / long_side))),
            Image.Resampling.LANCZOS,
        )
    return _key_alpha(patch.convert("RGBA"))


def _expr_panels(reference: Path) -> list[Image.Image]:
    master = Image.open(reference).convert("RGBA")
    x0, y0, x1, y1 = EXPR_HEADS
    row = master.crop((x0, y0, x1, y1))
    w = row.size[0] // EXPR_PANELS
    return [_key_alpha(row.crop((i * w, 0, (i + 1) * w, row.size[1]))) for i in range(EXPR_PANELS)]


def _panel_crop(panel: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    w, h = panel.size
    x0, y0, x1, y1 = box
    return panel.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1)))


def _flip_lr(im: Image.Image) -> Image.Image:
    return im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)


def _scale_min_height(im: Image.Image, min_height: int) -> Image.Image:
    w, h = im.size
    if h >= min_height:
        return im
    scale = min_height / h
    return im.resize((max(1, int(w * scale)), min_height), Image.Resampling.LANCZOS)


def _ink_bounds(im: Image.Image, pad: int = 2) -> tuple[int, int, int, int]:
    arr = np.array(im.convert("RGBA"))
    mask = arr[:, :, 3] > 12
    if not mask.any():
        return (0, 0, im.size[0], im.size[1])
    ys, xs = np.where(mask)
    return (
        max(0, int(xs.min()) - pad),
        max(0, int(ys.min()) - pad),
        min(im.size[0], int(xs.max()) + pad + 1),
        min(im.size[1], int(ys.max()) + pad + 1),
    )


def _hero_figure(view: Image.Image) -> Image.Image:
    """Intact turnaround card: keyed drawing, trimmed, scaled for the rest pose."""
    keyed = _key_figure(view.convert("RGBA"))
    x0, y0, x1, y1 = _ink_bounds(keyed, pad=1)
    keyed = keyed.crop((x0, y0, x1, y1))
    return _scale_min_height(keyed, 1400)


def _panel_face(panel: Image.Image) -> Image.Image:
    """Head + upper bust from an expression-row portrait (exclude captions/gesture low)."""
    w, h = panel.size
    return panel.crop((int(0.04 * w), int(0.0), int(0.96 * w), int(0.88 * h)))


def _fit_square(im: Image.Image, size: int, bg: tuple[int, int, int, int] = (22, 27, 34, 255)) -> Image.Image:
    im = im.convert("RGBA")
    w, h = im.size
    # Fixed bust frame — ink bounds split hair bun from face on keyed portraits.
    crop = im.crop((0, 0, w, max(1, int(h * 0.96))))
    cw, ch = crop.size
    scale = min(size / cw, size / ch) * 0.92
    nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
    crop = crop.resize((nw, nh), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (size, size), bg)
    out.paste(crop, ((size - nw) // 2, (size - nh) // 2), crop)
    return out


def _paste_box(base: Image.Image, overlay: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    out = base.copy()
    w, h = out.size
    x0, y0, x1, y1 = box
    px0, py0, px1, py1 = int(w * x0), int(h * y0), int(w * x1), int(h * y1)
    ow, oh = max(1, px1 - px0), max(1, py1 - py0)
    layer = overlay.convert("RGBA").resize((ow, oh), Image.Resampling.LANCZOS)
    out.paste(layer, (px0, py0), layer)
    return out


def _median_skin_and_lash(panel: Image.Image) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    cheek = np.array(_panel_crop(panel, (0.22, 0.42, 0.78, 0.58)).convert("RGB"))
    lum = cheek.mean(axis=2)
    skin_px = cheek[(lum > 90) & (lum < 210)]
    skin = tuple(int(v) for v in np.median(skin_px, axis=0)) if len(skin_px) else (196, 152, 128)
    brow = np.array(_panel_crop(panel, (0.20, 0.24, 0.80, 0.31)).convert("RGB"))
    bl = brow.mean(axis=2)
    lash_px = brow[bl < 95]
    lash = tuple(int(v) for v in np.median(lash_px, axis=0)) if len(lash_px) else (72, 52, 44)
    lash = tuple(max(48, min(120, c)) for c in lash)
    return skin, lash


def _eye_centers_norm(panel: Image.Image) -> list[tuple[float, float]]:
    centers: list[tuple[float, float]] = []
    for box in ((0.26, 0.30, 0.46, 0.40), (0.54, 0.30, 0.74, 0.40)):
        crop = _panel_crop(panel, box)
        arr = np.array(crop)[:, :, 3]
        ys, xs = np.where(arr > 24)
        if len(xs) == 0:
            continue
        cw, ch = crop.size
        cx = box[0] + (xs.mean() / cw) * (box[2] - box[0])
        cy = box[1] + (ys.mean() / ch) * (box[3] - box[1]) + 0.028
        centers.append((cx, cy))
    if len(centers) < 2:
        centers = [(0.355, 0.355), (0.645, 0.355)]
    return centers


def _portrait_eye_centers(panel: Image.Image) -> list[tuple[float, float]]:
    return [(0.362, 0.380), (0.638, 0.380)]


# Normalized on 512×512 `_fit_square` smile bust (iris centers from expr NEUTRAL cell).
BLINK_LID_ELLIPSES = (
    (0.262, 0.400, 0.470, 0.490),
    (0.530, 0.376, 0.746, 0.462),
)


def _blink_lid_boxes(panel: Image.Image) -> list[tuple[float, float, float, float]]:
    """Iris-centered lid ellipses on a 512×512 `_fit_square` bust (not raw panel)."""
    arr = np.array(panel.convert("RGBA"))
    h, w = arr.shape[:2]
    boxes: list[tuple[float, float, float, float]] = []
    for x0f, x1f in ((0.26, 0.50), (0.50, 0.76)):
        y0s, y1s = int(h * 0.39), int(h * 0.50)
        x0s, x1s = int(w * x0f), int(w * x1f)
        sl = arr[y0s:y1s, x0s:x1s]
        lum = sl[:, :, :3].astype(np.float32).mean(axis=2)
        dark = (sl[:, :, 3] > 32) & (lum < 72)
        if not dark.any():
            continue
        ys, xs = np.where(dark)
        cx = (xs.mean() + x0s) / w
        cy = (ys.mean() + y0s) / h + 0.006
        hw, hh = 0.112, 0.062
        boxes.append((cx - hw, cy - hh, cx + hw, cy + hh))
    if len(boxes) < 2:
        boxes = list(BLINK_LID_ELLIPSES)
    return boxes


def _blink_portrait(
    panel: Image.Image,
    centers: list[tuple[float, float]] | None = None,
    skin_source: Image.Image | None = None,
    lid_boxes: list[tuple[float, float, float, float]] | None = None,
) -> Image.Image:
    """Closed lids: skin-filled ellipses over irises + lash arcs (no bars)."""
    out = panel.convert("RGBA").copy()
    w, h = out.size
    skin, lash = _median_skin_and_lash(skin_source or panel)
    draw = ImageDraw.Draw(out)
    ellipses = lid_boxes or list(BLINK_LID_ELLIPSES)
    for nx0, ny0, nx1, ny1 in ellipses:
        px0, py0, px1, py1 = int(w * nx0), int(h * ny0), int(w * nx1), int(h * ny1)
        draw.ellipse((px0, py0, px1, py1), fill=skin + (255,))
        lw = max(2, int(h * 0.004))
        draw.arc((px0, py0, px1, py1), 200, 340, fill=lash + (255,), width=lw)
    arr = np.array(out)
    skin_arr = np.array(skin, dtype=np.uint8)
    for nx0, ny0, nx1, ny1 in ellipses:
        px0, py0, px1, py1 = int(w * nx0), int(h * ny0), int(w * nx1), int(h * ny1)
        cx, cy = (px0 + px1) // 2, (py0 + py1) // 2
        rx, ry = max(1, (px1 - px0) // 2), max(1, (py1 - py0) // 2)
        yy, xx = np.ogrid[py0:py1, px0:px1]
        mask = ((xx - cx) ** 2 / max(1, rx**2) + (yy - cy) ** 2 / max(1, ry**2)) <= 1.08
        sub = arr[py0:py1, px0:px1]
        lum = sub[:, :, :3].mean(axis=2)
        sub[mask, :3] = skin_arr
        sub[mask, 3] = 255
        # Cover any remaining dark iris/pupil ink inside the lid ellipse.
        iris = (sub[:, :, 3] > 32) & (sub[:, :, :3].mean(axis=2) < 130)
        sub[iris & mask, :3] = skin_arr
        sub[iris & mask, 3] = 255
        arr[py0:py1, px0:px1] = sub
    return Image.fromarray(arr)


# Normalized regions on the front turnaround (same space as PART_FRONT).
FRONT_ARM_L = (0.00, 0.22, 0.26, 0.56)
FRONT_ARM_R = (0.70, 0.22, 0.98, 0.56)
FRONT_HEAD = (0.08, 0.0, 0.92, 0.178)
FRONT_LEGS = (0.12, 0.52, 0.88, 0.92)
FRONT_LEG_L = (0.12, 0.52, 0.48, 0.92)
FRONT_LEG_R = (0.52, 0.52, 0.88, 0.92)
TORSO_FILL_L = (0.28, 0.24, 0.52, 0.48)
TORSO_FILL_R = (0.48, 0.24, 0.72, 0.48)
NECK_FILL = (0.34, 0.16, 0.66, 0.26)
SHOULDER_L = (0.36, 0.22)
SHOULDER_R = (0.64, 0.22)
NECK_PIVOT = (0.50, 0.168)


def _norm_crop(img: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    w, h = img.size
    x0, y0, x1, y1 = box
    return img.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1)))


def _paste_rotated_alpha(
    base: Image.Image,
    piece: Image.Image,
    anchor: tuple[int, int],
    angle_deg: float,
    origin_in_piece: tuple[int, int],
) -> Image.Image:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ax, ay = anchor
    ox, oy = origin_in_piece
    layer.paste(piece.convert("RGBA"), (ax - ox, ay - oy), piece)
    layer = layer.rotate(
        angle_deg,
        center=(ax, ay),
        resample=Image.Resampling.BICUBIC,
        expand=False,
        fillcolor=(0, 0, 0, 0),
    )
    return Image.alpha_composite(base.convert("RGBA"), layer)


def _arm_piece(hero: Image.Image, arm_box: tuple[float, float, float, float]) -> tuple[Image.Image, tuple[int, int]]:
    arm = _norm_crop(hero, arm_box)
    x0, y0, x1, y1 = _ink_bounds(arm, pad=1)
    arm = arm.crop((x0, y0, x1, y1))
    origin = (arm.size[0] // 2, 0)
    return arm, origin


def _roll_region(
    hero: Image.Image,
    box: tuple[float, float, float, float],
    dx: int,
    dy: int,
) -> Image.Image:
    """Roll pixels inside a hero limb box (attached motion, no empty holes)."""
    out = np.array(hero.convert("RGBA"), copy=True)
    w, h = hero.size
    x0, y0, x1, y1 = box
    px0, py0, px1, py1 = int(w * x0), int(h * y0), int(w * x1), int(h * y1)
    region = out[py0:py1, px0:px1]
    if dy:
        region = np.roll(region, -dy, axis=0)
    if dx:
        region = np.roll(region, -dx, axis=1)
    out[py0:py1, px0:px1] = region
    return Image.fromarray(out)


def _rotate_region(
    hero: Image.Image,
    box: tuple[float, float, float, float],
    angle_deg: float,
    pivot_norm: tuple[float, float],
) -> Image.Image:
    out = hero.convert("RGBA").copy()
    w, h = out.size
    patch = _norm_crop(out, box)
    px, py = int(w * pivot_norm[0]), int(h * pivot_norm[1])
    bx0 = int(w * box[0])
    by0 = int(h * box[1])
    origin = (px - bx0, py - by0)
    rotated = patch.rotate(angle_deg, center=origin, resample=Image.Resampling.BICUBIC, expand=False)
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    layer.paste(rotated, (bx0, by0), rotated)
    return Image.alpha_composite(out, layer)


def _clear_norm_alpha(img: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    arr = np.array(img.convert("RGBA"), copy=True)
    w, h = img.size
    x0, y0, x1, y1 = box
    px0, py0, px1, py1 = int(w * x0), int(h * y0), int(w * x1), int(h * y1)
    arr[py0:py1, px0:px1, 3] = 0
    return Image.fromarray(arr)


def _composite_arm(hero: Image.Image, side: str, angle_deg: float) -> Image.Image:
    """One keyed arm strip from the front hero, rotated at the shoulder."""
    arm_box = FRONT_ARM_L if side == "L" else FRONT_ARM_R
    shoulder = SHOULDER_L if side == "L" else SHOULDER_R
    piece = _key_alpha(_norm_crop(hero, arm_box))
    x0, y0, x1, y1 = _ink_bounds(piece, pad=2)
    piece = piece.crop((x0, y0, x1, y1))
    w, h = hero.size
    ax, ay = int(w * shoulder[0]), int(h * shoulder[1])
    ox = max(2, piece.size[0] - 5) if side == "L" else min(piece.size[0] - 2, 5)
    oy = 2
    return _paste_rotated_alpha(hero, piece, (ax, ay), angle_deg, (ox, oy))


def _tilt_hero(hero: Image.Image, angle_deg: float) -> Image.Image:
    w, h = hero.size
    pivot = (w // 2, int(h * NECK_PIVOT[1]))
    return hero.convert("RGBA").rotate(
        angle_deg,
        center=pivot,
        resample=Image.Resampling.BICUBIC,
        expand=False,
    )


def _bob_hero(hero: Image.Image, dy_norm: float) -> Image.Image:
    w, h = hero.size
    dy = int(h * dy_norm)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(hero, (0, dy), hero)
    return out


ACTION_CELL_SIZE = (360, 480)


def _fit_action_cell(hero: Image.Image, cw: int = 360, ch: int = 480) -> Image.Image:
    scale = min(cw / hero.width, ch / hero.height) * 0.88
    nw, nh = max(1, int(hero.width * scale)), max(1, int(hero.height * scale))
    img = hero.resize((nw, nh), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    out.paste(img, ((cw - nw) // 2, (ch - nh) // 2), img)
    return out


def _figure_bbox(cell: Image.Image) -> tuple[int, int, int, int]:
    arr = np.array(cell.convert("RGBA"))
    mask = arr[:, :, 3] > 48
    if not mask.any():
        w, h = cell.size
        return (0, 0, w, h)
    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _jacket_palette(cell: Image.Image) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    arr = np.array(cell.convert("RGBA"))
    x0, y0, x1, y1 = _figure_bbox(cell)
    fh, fw = y1 - y0, x1 - x0
    patch = arr[y0 + int(fh * 0.22) : y0 + int(fh * 0.38), x0 + int(fw * 0.18) : x0 + int(fw * 0.82), :3]
    rgb = patch.reshape(-1, 3).astype(np.float32)
    lum = rgb.mean(axis=1)
    sat = rgb.max(axis=1) - rgb.min(axis=1)
    navy_px = rgb[(lum < 95) & (sat < 90)]
    mag_px = rgb[(rgb[:, 0] > 120) & (rgb[:, 1] < 95) & (rgb[:, 2] > 95)]
    navy = tuple(int(v) for v in np.median(navy_px, axis=0)) if len(navy_px) else (43, 45, 65)
    magenta = tuple(int(v) for v in np.median(mag_px, axis=0)) if len(mag_px) else (229, 20, 150)
    outline = (max(0, navy[0] - 18), max(0, navy[1] - 18), max(0, navy[2] - 18))
    return navy, magenta, outline


def _draw_stroke_arm(
    cell: Image.Image,
    points: list[tuple[int, int]],
    width: int,
    navy: tuple[int, int, int],
    magenta: tuple[int, int, int],
    outline: tuple[int, int, int],
) -> None:
    draw = ImageDraw.Draw(cell)
    draw.line(points, fill=outline + (255,), width=width + 5, joint="curve")
    draw.line(points, fill=navy + (255,), width=width, joint="curve")
    draw.line(points, fill=magenta + (255,), width=max(3, width // 4), joint="curve")


def _paste_sheet_arm(
    cell: Image.Image,
    hero: Image.Image,
    side: str,
    angle_deg: float,
    scale: float = 1.35,
) -> None:
    """Keyed turnaround arm scaled up, rotated at shoulder, composited in front."""
    arm_box = FRONT_ARM_L if side == "L" else FRONT_ARM_R
    shoulder = SHOULDER_L if side == "L" else SHOULDER_R
    piece = _key_alpha(_norm_crop(hero, arm_box))
    x0, y0, x1, y1 = _ink_bounds(piece, pad=2)
    piece = piece.crop((x0, y0, x1, y1))
    nw, nh = max(1, int(piece.width * scale)), max(1, int(piece.height * scale))
    piece = piece.resize((nw, nh), Image.Resampling.LANCZOS)
    fx0, fy0, fx1, fy1 = _figure_bbox(cell)
    fw, fh = fx1 - fx0, fy1 - fy0
    ax = fx0 + int(fw * shoulder[0])
    ay = fy0 + int(fh * shoulder[1])
    ox = max(2, piece.size[0] - 6) if side == "L" else min(piece.size[0] - 2, 6)
    layer = Image.new("RGBA", cell.size, (0, 0, 0, 0))
    layer.paste(piece, (ax - ox, ay - 2), piece)
    layer = layer.rotate(
        angle_deg,
        center=(ax, ay),
        resample=Image.Resampling.BICUBIC,
        expand=False,
        fillcolor=(0, 0, 0, 0),
    )
    return Image.alpha_composite(cell.convert("RGBA"), layer)


def _draw_action_arm(
    cell: Image.Image,
    hero: Image.Image,
    pose: str,
) -> Image.Image:
    out = cell.copy()
    x0, y0, x1, y1 = _figure_bbox(out)
    fw, fh = x1 - x0, y1 - y0
    navy, magenta, outline = _jacket_palette(out)
    stroke = max(18, int(fh * 0.072))
    face_x0 = x0 + int(fw * 0.26)
    face_x1 = x1 - int(fw * 0.26)
    if pose == "wave":
        # Right shoulder → up/out beside head (stroke stays outside face band).
        margin = stroke // 2 + 6
        sh = (x1 - int(fw * 0.06), y0 + int(fh * 0.23))
        mid = (x1 + int(fw * 0.12), y0 + int(fh * 0.18))
        hand = (max(face_x1 + margin, x1 + int(fw * 0.34)), y0 - int(fh * 0.05))
        _draw_stroke_arm(out, [sh, mid, hand], stroke, navy, magenta, outline)
    elif pose == "point_left":
        sh = (x0 + int(fw * 0.14), y0 + int(fh * 0.22))
        el = (x0 - int(fw * 0.10), y0 + int(fh * 0.20))
        hand = (x0 - int(fw * 0.44), y0 + int(fh * 0.18))
        _draw_stroke_arm(out, [sh, el, hand], stroke, navy, magenta, outline)
    elif pose == "gesture_present":
        sh = (x1 - int(fw * 0.14), y0 + int(fh * 0.22))
        el = (x1 + int(fw * 0.10), y0 + int(fh * 0.17))
        hand = (max(face_x1 + int(fw * 0.06), x1 + int(fw * 0.38)), y0 + int(fh * 0.15))
        _draw_stroke_arm(out, [sh, el, hand], stroke, navy, magenta, outline)
    return out


def _bob_action_cell(cell: Image.Image, frac: float) -> Image.Image:
    """Vertical bob as a fraction of the action cell height (~8% for walk)."""
    cw, ch = cell.size
    dy = int(ch * frac)
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    out.paste(cell, (0, dy), cell)
    return out


def _tilt_action_cell(cell: Image.Image, angle_deg: float) -> Image.Image:
    x0, y0, x1, y1 = _figure_bbox(cell)
    pivot = ((x0 + x1) // 2, y0 + int((y1 - y0) * 0.12))
    return cell.rotate(
        angle_deg,
        center=pivot,
        resample=Image.Resampling.BICUBIC,
        expand=False,
        fillcolor=(0, 0, 0, 0),
    )


def compose_action_sheet(
    textures: dict[str, Image.Image],
    reference: Path | None = None,
) -> list[tuple[str, Image.Image]]:
    """Action QA: intact hero in cell + visible foreground arm / bob / tilt."""
    _ = reference
    hero = textures["TEX_HERO_FRONT"].copy()
    base = _fit_action_cell(hero.copy(), *ACTION_CELL_SIZE)
    rows: list[tuple[str, Image.Image]] = [
        ("idle_neutral_loop f24", base.copy()),
        ("walk_cycle f7", _bob_action_cell(base.copy(), -0.080)),
        ("walk_cycle f19", _bob_action_cell(base.copy(), 0.080)),
        ("gesture_present f18", _draw_action_arm(base.copy(), hero, "gesture_present")),
        ("wave f18", _draw_action_arm(base.copy(), hero, "wave")),
        ("point_left f16", _draw_action_arm(base.copy(), hero, "point_left")),
        ("head_nod f10", _tilt_action_cell(base.copy(), -11)),
        ("head_shake f12", _tilt_action_cell(base.copy(), 11)),
    ]
    return rows


def _shift_paste(base: Image.Image, patch: Image.Image, dx: float, dy: float) -> Image.Image:
    """Paste a same-size patch shifted by normalized offsets (fraction of width/height)."""
    out = base.copy()
    w, h = out.size
    px = int(w * dx)
    py = int(h * dy)
    layer = patch.convert("RGBA")
    if layer.size != (w, h):
        layer = layer.resize((w, h), Image.Resampling.LANCZOS)
    out.paste(layer, (px, py), layer)
    return out


def compose_qa_face_sheets(textures: dict[str, Image.Image]) -> tuple[list[tuple[str, Image.Image]], list[tuple[str, Image.Image]]]:
    """Readable expression + viseme cells from sheet expression row (not tiny 3D crops)."""
    p_smile = _scale_min_height(textures["TEX_EXPR_PANEL_SMILE"], 640)
    p_focus = _scale_min_height(textures["TEX_EXPR_PANEL_FOCUS"], 640)
    p_open = _scale_min_height(textures["TEX_EXPR_PANEL_OPEN"], 640)
    p_surprise = _scale_min_height(textures["TEX_EXPR_PANEL_SURPRISE"], 640)
    size = 512
    smile_sq = _fit_square(p_smile, size)
    expr = [
        ("NEUTRAL", smile_sq),
        (
            "BLINK",
            _blink_portrait(
                smile_sq,
                skin_source=p_smile,
                lid_boxes=_blink_lid_boxes(smile_sq),
            ),
        ),
        ("BROW_UP", _fit_square(p_surprise, size)),
        ("BROW_DOWN", _fit_square(p_focus, size)),
        ("SMILE", _fit_square(p_open, size)),
        ("FROWN", _fit_square(p_focus, size)),
        ("SURPRISE", _fit_square(p_surprise, size)),
        ("LOOK_L", _fit_square(p_focus, size)),
        ("LOOK_R", _fit_square(p_open, size)),
    ]

    mouth_frame = (0.08, 0.38, 0.92, 0.88)
    mouth_sources = {
        "VISEME_A": p_open,
        "VISEME_B": p_focus,
        "VISEME_C": p_focus,
        "VISEME_D": p_open,
        "VISEME_E": p_open,
        "VISEME_F": p_smile,
        "VISEME_G": p_surprise,
        "VISEME_H": p_surprise,
        "VISEME_X": p_focus,
    }
    visemes = []
    for name in (
        "VISEME_A",
        "VISEME_B",
        "VISEME_C",
        "VISEME_D",
        "VISEME_E",
        "VISEME_F",
        "VISEME_G",
        "VISEME_H",
        "VISEME_X",
    ):
        src = mouth_sources[name]
        w, h = src.size
        mouth = src.crop(
            (
                int(w * mouth_frame[0]),
                int(h * mouth_frame[1]),
                int(w * mouth_frame[2]),
                int(h * mouth_frame[3]),
            )
        )
        visemes.append((name, _fit_square(_scale_min_height(mouth, 420), 420)))
    return expr, visemes


def generate_art_textures(reference: Path) -> dict[str, Image.Image]:
    views = _load_views(reference)
    front, side, back = views["front"], views["side"], views["back"]
    textures: dict[str, Image.Image] = {}

    textures["TEX_HERO_FRONT"] = _hero_figure(front)
    textures["TEX_HERO_THREE_QUARTER"] = _hero_figure(views["three_quarter"])
    textures["TEX_HERO_SIDE"] = _hero_figure(side)
    textures["TEX_HERO_BACK"] = _hero_figure(back)
    textures["TEX_PROXY_CHARACTER"] = textures["TEX_HERO_FRONT"]

    for key, bbox in PART_FRONT.items():
        if key in ("TEX_ANATOMY_HIDDEN", "TEX_PROXY_CHARACTER"):
            if key == "TEX_ANATOMY_HIDDEN":
                textures[key] = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            continue
        textures[key] = _crop_norm(front, bbox, view_name="front")

    for key, bbox in PART_FRONT.items():
        if key in ("TEX_ANATOMY_HIDDEN", "TEX_PROXY_CHARACTER"):
            continue
        sb = SIDE_OVERRIDES.get(key, bbox)
        textures[f"{key}__side"] = _crop_norm(side, sb, view_name="side")
        bb = BACK_OVERRIDES.get(key, bbox)
        textures[f"{key}__back"] = _crop_norm(back, bb, view_name="back")

    panels = _expr_panels(reference)
    p_smile, p_focus, p_open, p_surprise = panels

    textures["TEX_MOUTH"] = _crop_norm(front, (0.40, 0.158, 0.60, 0.172), view_name="front")
    textures["TEX_MOUTH_SMILE"] = _key_alpha(_panel_crop(p_smile, (0.30, 0.55, 0.70, 0.78)))
    textures["TEX_MOUTH_FROWN"] = _key_alpha(_panel_crop(p_focus, (0.32, 0.58, 0.68, 0.74)))
    textures["TEX_MOUTH_OPEN"] = _key_alpha(_panel_crop(p_open, (0.28, 0.52, 0.72, 0.80)))
    textures["TEX_MOUTH_SURPRISE"] = _key_alpha(_panel_crop(p_surprise, (0.34, 0.54, 0.66, 0.78)))
    textures["TEX_TEETH"] = _key_alpha(_panel_crop(p_open, (0.34, 0.56, 0.66, 0.68)))
    textures["TEX_TEETH_SMILE"] = _key_alpha(_panel_crop(p_smile, (0.36, 0.58, 0.64, 0.68)))
    textures["TEX_MOUTH_INTERIOR"] = Image.new("RGBA", textures["TEX_MOUTH_OPEN"].size, (0, 0, 0, 0))

    textures["TEX_EYELID_CLOSED"] = _key_alpha(
        _panel_crop(p_smile, (0.16, 0.28, 0.84, 0.38))
    )
    textures["TEX_EYE_CLOSED"] = textures["TEX_EYELID_CLOSED"]
    textures["TEX_EYELID"] = Image.new("RGBA", textures["TEX_EYELID_CLOSED"].size, (0, 0, 0, 0))

    textures["TEX_BROW_NEUTRAL_L"] = textures["TEX_BROW_L"]
    textures["TEX_BROW_NEUTRAL_R"] = textures["TEX_BROW_R"]
    textures["TEX_BROW_UP_L"] = _key_alpha(_panel_crop(p_surprise, (0.14, 0.22, 0.48, 0.36)))
    textures["TEX_BROW_UP_R"] = _flip_lr(textures["TEX_BROW_UP_L"])
    textures["TEX_BROW_DOWN_L"] = _key_alpha(_panel_crop(p_focus, (0.14, 0.34, 0.48, 0.44)))
    textures["TEX_BROW_DOWN_R"] = _flip_lr(textures["TEX_BROW_DOWN_L"])

    textures["TEX_PUPIL_CENTER"] = textures["TEX_PUPIL"]
    textures["TEX_PUPIL_LOOK_L"] = _crop_norm(front, (0.38, 0.132, 0.54, 0.168), view_name="front")
    textures["TEX_PUPIL_LOOK_R"] = _crop_norm(front, (0.46, 0.132, 0.62, 0.168), view_name="front")

    mouth_neutral = textures["TEX_MOUTH"]
    mouth_smile = textures["TEX_MOUTH_SMILE"]
    mouth_frown = textures["TEX_MOUTH_FROWN"]
    mouth_open = textures["TEX_MOUTH_OPEN"]
    mouth_surprise = textures["TEX_MOUTH_SURPRISE"]
    viseme_mouths = {
        "VISEME_A": mouth_open,
        "VISEME_B": mouth_neutral,
        "VISEME_C": _key_alpha(_panel_crop(p_focus, (0.30, 0.58, 0.70, 0.72))),
        "VISEME_D": _key_alpha(_panel_crop(p_open, (0.26, 0.52, 0.74, 0.78))),
        "VISEME_E": _key_alpha(_panel_crop(p_open, (0.32, 0.56, 0.68, 0.74))),
        "VISEME_F": mouth_smile,
        "VISEME_G": mouth_surprise,
        "VISEME_H": _key_alpha(_panel_crop(p_surprise, (0.32, 0.54, 0.68, 0.78))),
        "VISEME_X": mouth_frown,
    }
    for name, img in viseme_mouths.items():
        textures[f"TEX_MOUTH_{name}"] = img

    textures["TEX_HAND_R"] = _crop_norm(front, PART_FRONT["TEX_HAND_R"], view_name="front")
    shoe = PART_FRONT["TEX_SHOE"]
    sx0, sy0, sx1, sy1 = shoe
    smid = (sx0 + sx1) * 0.5
    textures["TEX_SHOE_L"] = _crop_norm(front, (sx0, sy0, smid, sy1), view_name="front")
    textures["TEX_SHOE_R"] = _crop_norm(front, (smid, sy0, sx1, sy1), view_name="front")
    textures["TEX_SHOE_L__side"] = _crop_norm(side, (0.12, 0.84, 0.48, 0.99), view_name="side")
    textures["TEX_SHOE_R__side"] = _crop_norm(side, (0.52, 0.84, 0.88, 0.99), view_name="side")
    textures["TEX_SHOE_L__back"] = _crop_norm(back, (0.12, 0.86, 0.48, 0.99), view_name="back")
    textures["TEX_SHOE_R__back"] = _crop_norm(back, (0.52, 0.86, 0.88, 0.99), view_name="back")

    textures["TEX_EYE_R"] = textures["TEX_EYE_L"].transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    textures["TEX_BROW_R"] = textures["TEX_BROW_L"].transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    textures["TEX_EXPR_PANEL_SMILE"] = _scale_min_height(_key_alpha(p_smile), 512)
    textures["TEX_EXPR_PANEL_FOCUS"] = _scale_min_height(_key_alpha(p_focus), 512)
    textures["TEX_EXPR_PANEL_OPEN"] = _scale_min_height(_key_alpha(p_open), 512)
    textures["TEX_EXPR_PANEL_SURPRISE"] = _scale_min_height(_key_alpha(p_surprise), 512)

    return textures


def write_turnaround_previews(reference: Path, out_dir: Path) -> None:
    """Studio frames of the keyed turnaround. No Blender — same cards the rest pose uses."""
    views = _load_views(reference)
    names = {
        "front": "front.png",
        "three_quarter": "three-quarter.png",
        "side": "side.png",
        "back": "back.png",
    }
    wall = (232, 230, 226, 255)
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, filename in names.items():
        hero = _hero_figure(views[key])
        frame = Image.new("RGBA", (960, 1200), wall)
        max_h = 1080
        max_w = 860
        scale = min(max_w / hero.size[0], max_h / hero.size[1])
        nw, nh = max(1, int(hero.size[0] * scale)), max(1, int(hero.size[1] * scale))
        sprite = hero.resize((nw, nh), Image.Resampling.LANCZOS)
        x = (frame.size[0] - nw) // 2
        y = (frame.size[1] - nh) // 2 + 20
        frame.paste(sprite, (x, y), sprite)
        frame.save(out_dir / filename)
