"""Split Patty's arm cards so the elbow and wrist can hinge.

At rest each joint overlaps by about 8% of that arm's own length (upper sleeve
over the forearm at the elbow, forearm over the hand at the wrist), so the
cards stack back into the front pose without a hole. UPPER_ARM_L/R follow
upper_arm.L/R, FOREARM_L/R follow forearm.L/R, and HAND_L/R follow hand.L/R.
HAND_R carries the tablet. The hip bag stays off the arm.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from patty_parts import _keep_large_islands, tight_crop, trim_pale_fringe

# Shared band at each joint, as a fraction of that arm's arc length.
OVERLAP_FRAC = 0.08

# Filled in by split_arms: (elbow, wrist) arc-length fractions, shoulder = 0
# and fingertips = 1. The overlap band is centered on each of these.
SPLIT_FRACTIONS: dict[str, tuple[float, float]] = {}

ELBOW_PARTS = [
    ("UPPER_ARM_L", "GEO_AVERY_UPPER_ARM.L", "upper_arm.L", -0.118),
    ("UPPER_ARM_R", "GEO_AVERY_UPPER_ARM.R", "upper_arm.R", -0.119),
    ("FOREARM_L", "GEO_AVERY_FOREARM.L", "forearm.L", -0.124),
    ("FOREARM_R", "GEO_AVERY_FOREARM.R", "forearm.R", -0.125),
    ("HAND_L", "GEO_AVERY_HAND.L", "hand.L", -0.130),
    ("HAND_R", "GEO_AVERY_HAND.R", "hand.R", -0.132),
]


def split_arms(textures: dict) -> dict[str, Image.Image]:
    """Cut ARM_L/ARM_R/TABLET full layers into sleeve, forearm, and hand cards.

    ``textures`` is the dict from ``patty_parts.build_all``. Full-canvas layers
    keep the front-figure origin. Tight crops are the textures a card maps
    over its bounding box.
    """
    full = textures.get("ARM_L_FULL") or textures.get("FRONT_FULL")
    if full is None:
        raise KeyError("split_arms needs ARM_L_FULL or FRONT_FULL")
    width, height = full.size
    out: dict[str, Image.Image] = {}
    out.update(_split_left(textures, width, height))
    out.update(_split_right(textures, width, height))
    return out


def _split_left(textures: dict, width: int, height: int) -> dict[str, Image.Image]:
    arm = _full(textures, "ARM_L_FULL", width, height)
    bag = _full(textures, "BAG_FULL", width, height)
    alpha = arm[:, :, 3] > 16
    bag_a = bag[:, :, 3] > 16
    ny, nx = _norm(height, width)
    skin = _skin(arm) | _skin(bag)

    # The hip-bag box swallows the outer sleeve and the bent forearm. Take
    # those pixels back. The bag body itself starts under the hand and stays out.
    stolen = bag_a & (ny < 0.455) & (nx < 0.18)
    stolen |= skin & bag_a & (ny < 0.49) & (nx < 0.24)
    source = (alpha & (ny < 0.50)) | stolen
    source &= ~(_pale(arm) & (nx > 0.27) & (ny < 0.42) & ~skin)

    # The sleeve is the band in from the outer silhouette. A horizontal slice
    # of the jacket column beside it is the torso, not the elbow.
    thickness = max(32, int(round(0.20 * width)))
    outer = _row_min(source)
    ys, xs = np.where(source)
    limb = np.zeros(source.shape, dtype=bool)
    if len(xs):
        limb[ys, xs] = xs <= outer[ys] + thickness
    limb |= source & (ny < 0.26) & (nx < 0.36)
    hip_skin = skin & (ny > 0.36) & (ny < 0.48) & (nx < 0.40)
    limb |= hip_skin
    watch = (_dark(arm) | _dark(bag)) & _dilate(hip_skin, 8)
    limb |= watch & (ny < 0.48) & (nx < 0.36)
    # The pocket and the pants continue below the fingers. Stop at the last
    # real row of the hand, not a one-pixel speck.
    counts = hip_skin.sum(axis=1)
    solid = np.where(counts >= 8)[0]
    if len(solid):
        # Below the fingers the outer-silhouette band is the pocket and the
        # pants, not the hand. Keep a few pixels of cuff around the skin.
        limb &= ny <= (int(solid.max()) + 3) / float(height)
        halo = _dilate(hip_skin, 3)
        limb &= (ny < 0.44) | halo | hip_skin

    shoulder = _centroid(limb & (ny < 0.25), (0.22 * width, 0.23 * height))
    mid = _centroid(limb & (ny > 0.26) & (ny < 0.34), (0.12 * width, 0.30 * height))
    elbow = _centroid(limb & (ny > 0.34) & (ny < 0.42) & ~skin, (0.11 * width, 0.38 * height))
    wrist = _centroid(skin & limb & (nx < 0.22) & (ny > 0.37), (0.16 * width, 0.42 * height))
    tips = _centroid(skin & limb & (nx >= 0.20), (0.28 * width, 0.43 * height))
    line = np.stack([shoulder, mid, elbow, wrist, tips])
    elbow_t = _vertex_t(line, 2)
    wrist_t = _vertex_t(line, 3)
    SPLIT_FRACTIONS["L"] = (round(elbow_t, 3), round(wrist_t, 3))
    radius = max(24.0, 0.18 * width)
    upper, fore, hand = _segment(limb, line, radius, elbow_t, wrist_t)
    return _pack("L", arm, bag, upper, fore, hand, width, height)


def _split_right(textures: dict, width: int, height: int) -> dict[str, Image.Image]:
    arm = _full(textures, "ARM_R_FULL", width, height)
    tablet = _full(textures, "TABLET_FULL", width, height)
    alpha = arm[:, :, 3] > 16
    tab_a = tablet[:, :, 3] > 16
    ny, nx = _norm(height, width)
    skin = _skin(arm) | _skin(tablet)
    # Pants nub under the tablet is a separate blob past the fingertips.
    sleeve = alpha & (ny < 0.60)
    sleeve = _largest(sleeve)

    shoulder = _centroid(sleeve & (ny < 0.28), (0.78 * width, 0.24 * height))
    # Elbow height is the outer bulge; the point sits in the sleeve, not on the edge.
    bulge = _outer_bulge(sleeve, ny, 0.34, 0.46, (0.86 * width, 0.40 * height))
    elbow_y = int(np.clip(round(float(bulge[1])), 0, height - 1))
    elbow_cols = np.where(sleeve[elbow_y])[0]
    elbow_x = float(elbow_cols.mean()) if len(elbow_cols) else float(bulge[0])
    elbow = np.array([elbow_x, elbow_y], dtype=np.float64)
    # The watch is the gap in the skin between the forearm and the fingers.
    wrist_y = _skin_dip(skin & (nx > 0.72), int(0.49 * height), int(0.56 * height))
    wrist_cols = np.where(skin[wrist_y] & (np.arange(width) > int(0.75 * width)))[0]
    if len(wrist_cols) < 4:
        wrist_cols = np.where(sleeve[min(height - 1, wrist_y)] | skin[min(height - 1, max(0, wrist_y - 6))])[0]
    wrist_x = float(wrist_cols.mean()) if len(wrist_cols) else 0.88 * width
    wrist = np.array([wrist_x, wrist_y], dtype=np.float64)
    tips = _centroid(skin & (ny > (wrist_y + 8) / height), (0.86 * width, 0.58 * height))
    watch = (
        _dark(tablet)
        & (np.abs(np.arange(height)[:, None] - wrist_y) <= 14)
        & (nx > 0.78)
        & (ny < 0.58)
    )
    line = np.stack([shoulder, elbow, wrist, tips])
    elbow_t = _vertex_t(line, 1)
    wrist_t = _vertex_t(line, 2)
    SPLIT_FRACTIONS["R"] = (round(elbow_t, 3), round(wrist_t, 3))
    radius = max(20.0, 0.16 * width)
    limb = sleeve | (skin & (nx > 0.70))
    upper, fore, hand = _segment(limb, line, radius, elbow_t, wrist_t)
    # The tablet is one object in the hand, including where it overlaps the forearm.
    device = _tablet_device(tablet, tab_a, skin)
    hand |= device
    hand |= watch
    fore |= watch
    # Keep forearm skin that the radius missed, without swallowing the hand.
    pad = max(6, int(round(OVERLAP_FRAC * 0.5 * max(40.0, float(wrist_y - elbow_y)))))
    fore |= skin & (np.arange(height)[:, None] >= elbow_y - pad) & (np.arange(height)[:, None] <= wrist_y + pad) & (nx > 0.72)
    hand |= skin & (np.arange(height)[:, None] >= wrist_y - pad) & (nx > 0.72)
    fore &= ~device
    upper &= ~device
    return _pack("R", arm, tablet, upper, fore, hand, width, height)


def _segment(mask, line, radius, elbow_t, wrist_t):
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return mask, mask, mask
    pts = np.stack([xs, ys], axis=1).astype(np.float64)
    t, dist = _project(pts, line.astype(np.float64))
    half = OVERLAP_FRAC * 0.5
    near = dist <= radius
    upper = np.zeros(mask.shape, dtype=bool)
    fore = np.zeros(mask.shape, dtype=bool)
    hand = np.zeros(mask.shape, dtype=bool)
    sel = near & (t <= elbow_t + half)
    upper[ys[sel], xs[sel]] = True
    sel = near & (t >= elbow_t - half) & (t <= wrist_t + half)
    fore[ys[sel], xs[sel]] = True
    sel = near & (t >= wrist_t - half)
    hand[ys[sel], xs[sel]] = True
    return upper, fore, hand


def _tablet_device(tablet: np.ndarray, alpha: np.ndarray, skin: np.ndarray) -> np.ndarray:
    """Gray slab plus the bezel inside its bounds. Pants beside the slab stay out."""
    face = (_pale(tablet) | _gray(tablet)) & alpha & ~skin
    if int(face.sum()) < 30:
        return np.zeros(alpha.shape, dtype=bool)
    face = _largest(face)
    ys, xs = np.where(face)
    y0 = max(0, int(ys.min()) - 2)
    y1 = min(alpha.shape[0], int(ys.max()) + 3)
    x0 = max(0, int(xs.min()) - 2)
    x1 = min(alpha.shape[1], int(xs.max()) + 3)
    box = np.zeros(alpha.shape, dtype=bool)
    box[y0:y1, x0:x1] = True
    return (alpha & ~skin & box) | face


def _pack(side, primary, secondary, upper, fore, hand, width, height):
    """Paint masks from the source canvases. Hand wins ties, then forearm."""
    base = primary.copy()
    sec_a = secondary[:, :, 3] > 16
    base[sec_a] = secondary[sec_a]
    layers = {}
    # Draw upper first, then forearm, then hand, so overlap shows the front card.
    # Each mask still keeps the pixels the segment owns, including the overlap.
    order = (("UPPER_ARM", upper), ("FOREARM", fore), ("HAND", hand))
    for name, mask in order:
        sheet = np.zeros((height, width, 4), dtype=np.uint8)
        sheet[mask] = base[mask]
        image = trim_pale_fringe(Image.fromarray(sheet))
        image = _keep_large_islands(image, min_area=40)
        layers[f"{name}_{side}_FULL"] = image
        layers[f"{name}_{side}"] = _crop(image)
    return layers


def _crop(image: Image.Image) -> Image.Image:
    cleaned = trim_pale_fringe(image)
    cropped, _ = tight_crop(cleaned, 0)
    return cropped


def _full(textures: dict, key: str, width: int, height: int) -> np.ndarray:
    image = textures.get(key)
    if image is None:
        return np.zeros((height, width, 4), dtype=np.uint8)
    image = image.convert("RGBA")
    if image.size != (width, height):
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.alpha_composite(image)
        image = canvas
    return np.array(image)


def _norm(height: int, width: int):
    ny = np.arange(height, dtype=np.float64)[:, None] / height
    nx = np.arange(width, dtype=np.float64)[None, :] / width
    return ny, nx


def _skin(image: np.ndarray) -> np.ndarray:
    rgb = image[:, :, :3].astype(np.int16)
    alpha = image[:, :, 3] > 16
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    return alpha & (r > 118) & (r > b + 20) & (r > g + 6) & (g > 42) & (b < 155)


def _pale(image: np.ndarray) -> np.ndarray:
    rgb = image[:, :, :3].astype(np.int16)
    alpha = image[:, :, 3] > 16
    lum = rgb.mean(axis=2)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    return alpha & (lum > 168) & (sat < 40)


def _gray(image: np.ndarray) -> np.ndarray:
    rgb = image[:, :, :3].astype(np.int16)
    alpha = image[:, :, 3] > 16
    lum = rgb.mean(axis=2)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    return alpha & (lum > 90) & (lum <= 190) & (sat < 42)


def _dark(image: np.ndarray) -> np.ndarray:
    rgb = image[:, :, :3].astype(np.int16)
    alpha = image[:, :, 3] > 16
    return alpha & (rgb.mean(axis=2) < 52)


def _skin_dip(mask: np.ndarray, y0: int, y1: int) -> int:
    """Row where the arm's skin thins out at the watch."""
    y0 = max(0, y0)
    y1 = min(mask.shape[0], max(y0 + 1, y1))
    counts = mask.sum(axis=1)
    return y0 + int(np.argmin(counts[y0:y1]))


def _vertex_t(line: np.ndarray, index: int) -> float:
    lengths = np.linalg.norm(np.diff(line, axis=0), axis=1)
    total = float(lengths.sum()) or 1.0
    return float(lengths[:index].sum() / total)


def _row_min(mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    outer = np.full(height, width, dtype=np.int32)
    ys, xs = np.where(mask)
    for y, x in zip(ys.tolist(), xs.tolist()):
        if x < outer[y]:
            outer[y] = x
    return outer


def _centroid(mask: np.ndarray, fallback: tuple[float, float]) -> np.ndarray:
    ys, xs = np.where(mask)
    if len(xs) < 8:
        return np.array(fallback, dtype=np.float64)
    return np.array([float(xs.mean()), float(ys.mean())], dtype=np.float64)


def _outer_bulge(mask, ny, ny0, ny1, fallback):
    """Point on the +X silhouette where the hanging sleeve bends."""
    band = mask & (ny >= ny0) & (ny <= ny1)
    ys, xs = np.where(band)
    if len(xs) < 8:
        return np.array(fallback, dtype=np.float64)
    best = None
    for y in np.unique(ys):
        row = xs[ys == y]
        tip = int(row.max())
        score = tip
        if best is None or score > best[0]:
            best = (score, tip, int(y))
    return np.array([best[1], best[2]], dtype=np.float64)


def _largest(mask: np.ndarray) -> np.ndarray:
    from collections import deque

    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    best = []
    ys, xs = np.where(mask)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        queue: deque[tuple[int, int]] = deque([(y0, x0)])
        seen[y0, x0] = True
        comp = [(y0, x0)]
        while queue:
            y, x = queue.popleft()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx_ = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx_ < w and mask[ny, nx_] and not seen[ny, nx_]:
                    seen[ny, nx_] = True
                    queue.append((ny, nx_))
                    comp.append((ny, nx_))
        if len(comp) > len(best):
            best = comp
    out = np.zeros((h, w), dtype=bool)
    for y, x in best:
        out[y, x] = True
    return out


def _dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0 or not mask.any():
        return mask
    h, w = mask.shape
    ys, xs = np.where(mask)
    out = mask.copy()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dy * dy + dx * dx > radius * radius:
                continue
            yy = ys + dy
            xx = xs + dx
            ok = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
            out[yy[ok], xx[ok]] = True
    return out


def _project(points: np.ndarray, line: np.ndarray):
    """Arc-length fraction and distance from each point to a polyline."""
    best_d = np.full(len(points), np.inf)
    best_t = np.zeros(len(points))
    lengths = np.linalg.norm(np.diff(line, axis=0), axis=1)
    total = float(lengths.sum()) or 1.0
    acc = 0.0
    for start, end, length in zip(line[:-1], line[1:], lengths):
        if length < 1e-3:
            continue
        ab = end - start
        ap = points - start
        u = np.clip((ap @ ab) / (length * length), 0.0, 1.0)
        proj = start + u[:, None] * ab
        dist = np.linalg.norm(points - proj, axis=1)
        closer = dist < best_d
        best_d[closer] = dist[closer]
        best_t[closer] = (acc + u[closer] * length) / total
        acc += float(length)
    return best_t, best_d


def _preview():
    from patty_parts import build_all

    ref = Path("/workspace/media/reference/patty-patties-style-hires.png")
    textures = build_all(ref)
    parts = split_arms(textures)
    full = textures["FRONT_FULL"]
    gray = (150, 150, 154, 255)
    canvas = Image.new("RGBA", full.size, gray)
    for name in (
        "UPPER_ARM_L",
        "UPPER_ARM_R",
        "FOREARM_L",
        "FOREARM_R",
        "HAND_L",
        "HAND_R",
    ):
        canvas.alpha_composite(parts[f"{name}_FULL"])
    canvas.convert("RGB").save("/tmp/elbow-preview.png")
    for side, path in (("L", "/tmp/elbow-L.png"), ("R", "/tmp/elbow-R.png")):
        tiles = [parts[f"{name}_{side}"] for name in ("UPPER_ARM", "FOREARM", "HAND")]
        gap = 12
        height = max(tile.size[1] for tile in tiles)
        width = sum(tile.size[0] for tile in tiles) + gap * (len(tiles) - 1)
        row = Image.new("RGBA", (width, height), gray)
        x = 0
        for tile in tiles:
            row.alpha_composite(tile, (x, (height - tile.size[1]) // 2))
            x += tile.size[0] + gap
        row.convert("RGB").save(path)
    for key, _obj, bone, depth in ELBOW_PARTS:
        image = parts[key]
        print(f"{key:14} {image.size} bone={bone} depth={depth}")
    print("fractions", SPLIT_FRACTIONS, "overlap", OVERLAP_FRAC)


if __name__ == "__main__":
    _preview()
