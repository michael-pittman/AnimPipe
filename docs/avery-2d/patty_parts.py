"""Cut the Patty Patties style sheet into bone-aligned sprites.

Boxes were measured on the 480×360 sheet and scale with the master image,
so the 1448×1086 sheet and the smaller reference both work.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# 480×360 sheet coordinates. Scale by the opened image size.
SHEET_VIEWS = {
    "front": (14, 40, 84, 270),
    "three_quarter": (86, 40, 154, 270),
    "side": (156, 40, 210, 270),
    "back": (214, 40, 278, 270),
}
EXPR_HEADS = (276, 58, 472, 112)
EXPR_PANELS = 4
EXPR_NAMES = ("smile", "focus", "open", "surprise")

# World span of the tight front figure. Feet sit on the rig floor; the hair
# clears the head bone (tail z=1.76). Midline is the face, not the bbox,
# because the hip bag and tablet pull the crop off-center.
FIG_HEIGHT = 1.88
FIG_FLOOR = 0.02
FIG_MID_X = 0.50
FIG_WIDTH = 0.62


def scaled_box(box: tuple[int, int, int, int], size: tuple[int, int]) -> tuple[int, int, int, int]:
    sx = size[0] / 480.0
    sy = size[1] / 360.0
    x0, y0, x1, y1 = box
    return int(x0 * sx), int(y0 * sy), int(x1 * sx), int(y1 * sy)


def _key_figure(patch: Image.Image) -> Image.Image:
    """Drop the pale grid paper. Keep shirt, sneaker, and badge whites."""
    from collections import deque

    arr = np.array(patch.convert("RGBA")).copy()
    h, w = arr.shape[:2]
    rgb = arr[:, :, :3].astype(np.float32)
    lum = rgb.mean(axis=2)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    sat = (mx - mn) / (mx + 1.0)
    barrier = (lum < 175.0) | (sat > 0.18)
    pale = (lum > 188.0) & (sat < 0.14)
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
    trans = alpha == 0
    neighbor = trans.copy()
    neighbor[1:, :] |= trans[:-1, :]
    neighbor[:-1, :] |= trans[1:, :]
    neighbor[:, 1:] |= trans[:, :-1]
    neighbor[:, :-1] |= trans[:, 1:]
    alpha[pale & neighbor] = 0
    arr[:, :, 3] = alpha
    return Image.fromarray(arr)


def load_master(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def load_views(path: Path) -> dict[str, Image.Image]:
    master = load_master(path)
    return {name: master.crop(scaled_box(box, master.size)) for name, box in SHEET_VIEWS.items()}


def tight_crop(image: Image.Image, pad: int = 2) -> tuple[Image.Image, tuple[int, int, int, int]]:
    arr = np.array(image)
    ys, xs = np.where(arr[:, :, 3] > 16)
    if len(xs) == 0:
        return image, (0, 0, image.size[0], image.size[1])
    x0 = max(0, int(xs.min()) - pad)
    y0 = max(0, int(ys.min()) - pad)
    x1 = min(image.size[0], int(xs.max()) + 1 + pad)
    y1 = min(image.size[1], int(ys.max()) + 1 + pad)
    return image.crop((x0, y0, x1, y1)), (x0, y0, x1, y1)


def _classify(nx: float, ny: float) -> str | None:
    """Front-figure normalized coordinate → part id.

    Image-left is the character's left (bone .L, world −X) when the camera
    sits on −Y. The hip bag stays on the pelvis; the tablet stays on hand.R.
    Hair above the shoulders is always the head, never an arm.
    """
    if ny < 0.205 and 0.04 < nx < 0.86:
        return "HEAD"
    if ny > 0.855:
        if nx < 0.56:
            return "SHOE_L"
        if nx > 0.60:
            return "SHOE_R"
        return None
    if nx < 0.15 and 0.30 < ny < 0.64:
        return "BAG"
    if 0.45 < ny < 0.60 and nx > 0.62:
        return "TABLET"
    if 0.20 < ny < 0.58 and nx < 0.34:
        return "ARM_L"
    if 0.20 < ny < 0.62 and nx > 0.72:
        return "ARM_R"
    if ny > 0.50:
        if nx < 0.505:
            return "THIGH_L" if ny < 0.71 else "SHIN_L"
        return "THIGH_R" if ny < 0.71 else "SHIN_R"
    if 0.175 < ny <= 0.52 and 0.16 < nx < 0.84:
        return "TORSO"
    return None


# Extra overlap so joints do not split open when a bone rotates.
OVERLAP = {
    "THIGH_L": ("SHIN_L", 0.68, 0.74),
    "THIGH_R": ("SHIN_R", 0.68, 0.74),
    "SHIN_L": ("THIGH_L", 0.68, 0.74),
    "SHIN_R": ("THIGH_R", 0.68, 0.74),
    "TORSO": ("THIGH_L", 0.48, 0.54),
    "HEAD": ("TORSO", 0.18, 0.23),
}


def split_front(fig: Image.Image) -> dict[str, Image.Image]:
    """Return full-figure-sized RGBA layers. Empty pixels stay transparent."""
    arr = np.array(fig.convert("RGBA"))
    h, w = arr.shape[:2]
    ids = [name for name in (
        "HEAD", "TORSO", "ARM_L", "ARM_R", "BAG", "TABLET",
        "THIGH_L", "THIGH_R", "SHIN_L", "SHIN_R", "SHOE_L", "SHOE_R",
    )]
    masks = {name: np.zeros((h, w), dtype=bool) for name in ids}
    opaque = arr[:, :, 3] > 16
    ys, xs = np.where(opaque)
    for y, x in zip(ys.tolist(), xs.tolist()):
        name = _classify(x / w, y / h)
        if name:
            masks[name][y, x] = True
    # Duplicate a band across the knee and the waist so the cards overlap.
    for y, x in zip(ys.tolist(), xs.tolist()):
        ny = y / h
        nx = x / w
        if 0.68 <= ny <= 0.74 and nx < 0.505:
            masks["THIGH_L"][y, x] = True
            masks["SHIN_L"][y, x] = True
        elif 0.68 <= ny <= 0.74 and nx >= 0.505:
            masks["THIGH_R"][y, x] = True
            masks["SHIN_R"][y, x] = True
        if 0.48 <= ny <= 0.54 and 0.20 < nx < 0.80:
            masks["TORSO"][y, x] = True
        if 0.185 <= ny <= 0.225 and 0.22 < nx < 0.78:
            masks["HEAD"][y, x] = True
            masks["TORSO"][y, x] = True
    layers = {}
    for name, mask in masks.items():
        layer = np.zeros_like(arr)
        layer[mask] = arr[mask]
        layers[name] = Image.fromarray(layer)
    return layers


def world_from_norm(nx: float, ny: float) -> tuple[float, float]:
    x = (nx - FIG_MID_X) * FIG_WIDTH
    z = FIG_FLOOR + (1.0 - ny) * FIG_HEIGHT
    return x, z


def layer_bbox(image: Image.Image) -> tuple[float, float, float, float] | None:
    arr = np.array(image)
    ys, xs = np.where(arr[:, :, 3] > 16)
    if len(xs) == 0:
        return None
    h, w = arr.shape[:2]
    return xs.min() / w, ys.min() / h, (xs.max() + 1) / w, (ys.max() + 1) / h


def card_placement(image: Image.Image) -> dict[str, float] | None:
    """Center, size, and bone-pivot hint in meters for one full-figure layer."""
    box = layer_bbox(image)
    if not box:
        return None
    nx0, ny0, nx1, ny1 = box
    x0, z1 = world_from_norm(nx0, ny0)
    x1, z0 = world_from_norm(nx1, ny1)
    return {
        "x": (x0 + x1) * 0.5,
        "z": (z0 + z1) * 0.5,
        "w": max(0.02, x1 - x0),
        "h": max(0.02, z1 - z0),
        "nx0": nx0,
        "ny0": ny0,
        "nx1": nx1,
        "ny1": ny1,
    }


def _keep_large_islands(image: Image.Image, min_area: int = 80) -> Image.Image:
    """Drop hair-curl specks that would inflate a limb's bounding box."""
    from collections import deque

    arr = np.array(image.convert("RGBA"))
    h, w = arr.shape[:2]
    opaque = arr[:, :, 3] > 16
    seen = np.zeros((h, w), dtype=bool)
    keep = np.zeros((h, w), dtype=bool)
    ys, xs = np.where(opaque)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        queue: deque[tuple[int, int]] = deque([(y0, x0)])
        seen[y0, x0] = True
        comp = [(y0, x0)]
        while queue:
            y, x = queue.popleft()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and opaque[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
                    comp.append((ny, nx))
        if len(comp) >= min_area:
            for y, x in comp:
                keep[y, x] = True
    arr[:, :, 3] = np.where(keep, arr[:, :, 3], 0)
    return Image.fromarray(arr)


def trim_pale_fringe(image: Image.Image, passes: int = 2) -> Image.Image:
    """Drop the paper halo on a card edge so EEVEE does not draw a pale rectangle."""
    arr = np.array(image.convert("RGBA"))
    rgb = arr[:, :, :3].astype(np.int16)
    lum = rgb.mean(axis=2)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    pale = (lum > 176) & (sat < 36)
    alpha = arr[:, :, 3] > 16
    for _ in range(passes):
        trans = ~alpha
        neighbor = np.zeros_like(trans)
        neighbor[1:] |= trans[:-1]
        neighbor[:-1] |= trans[1:]
        neighbor[:, 1:] |= trans[:, :-1]
        neighbor[:, :-1] |= trans[:, 1:]
        alpha[pale & neighbor] = False
    arr[:, :, 3] = np.where(alpha, arr[:, :, 3], 0)
    return Image.fromarray(arr)


def crop_alpha(image: Image.Image, pad: int = 0) -> Image.Image:
    cleaned = trim_pale_fringe(_keep_large_islands(image))
    cropped, _ = tight_crop(cleaned, pad)
    return cropped


def _key_alpha_panel(patch: Image.Image) -> Image.Image:
    """Key a bust that may include a pale caption margin."""
    return _key_figure(patch)


def expression_panels(path: Path) -> dict[str, Image.Image]:
    master = load_master(path)
    x0, y0, x1, y1 = scaled_box(EXPR_HEADS, master.size)
    row = master.crop((x0, y0, x1, y1))
    w = row.size[0] // EXPR_PANELS
    panels = {}
    for i, name in enumerate(EXPR_NAMES):
        panels[name] = _key_alpha_panel(row.crop((i * w, 0, (i + 1) * w, row.size[1])))
    return panels


def _mouth_crop(panel: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    w, h = panel.size
    x0, y0, x1, y1 = box
    return panel.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1)))


def build_face_textures(panels: dict[str, Image.Image]) -> dict[str, Image.Image]:
    """Mouth and lid crops. Neutral speech uses the open / smile / focus busts."""
    smile, focus, opened, surprise = (panels[n] for n in EXPR_NAMES)
    mouth = (0.30, 0.52, 0.70, 0.78)
    textures = {
        "MOUTH_SMILE": _mouth_crop(opened, mouth),
        "MOUTH_CLOSED": _mouth_crop(smile, (0.32, 0.55, 0.68, 0.74)),
        "MOUTH_FOCUS": _mouth_crop(focus, (0.32, 0.56, 0.68, 0.74)),
        "MOUTH_SURPRISE": _mouth_crop(surprise, (0.34, 0.52, 0.66, 0.76)),
        "MOUTH_OPEN": _mouth_crop(opened, (0.28, 0.50, 0.72, 0.80)),
        "EXPR_SMILE": smile,
        "EXPR_FOCUS": focus,
        "EXPR_OPEN": opened,
        "EXPR_SURPRISE": surprise,
    }
    textures["MOUTH_A"] = textures["MOUTH_OPEN"]
    textures["MOUTH_B"] = textures["MOUTH_CLOSED"]
    textures["MOUTH_C"] = textures["MOUTH_FOCUS"]
    textures["MOUTH_D"] = textures["MOUTH_OPEN"]
    textures["MOUTH_E"] = textures["MOUTH_SMILE"]
    textures["MOUTH_F"] = textures["MOUTH_SMILE"]
    textures["MOUTH_G"] = textures["MOUTH_SURPRISE"]
    textures["MOUTH_H"] = textures["MOUTH_SURPRISE"]
    textures["MOUTH_X"] = textures["MOUTH_CLOSED"]
    return textures


def paint_blink_lids(head: Image.Image) -> Image.Image:
    """Skin-colored lids over the eye band of the front head crop."""
    arr = np.array(head.convert("RGBA"))
    h, w = arr.shape[:2]
    # Eyes sit just above the middle of the head+hair card.
    y0, y1 = int(h * 0.48), int(h * 0.62)
    band = arr[y0:y1]
    rgb = band[:, :, :3].astype(np.int16)
    # Skin sample: warm pixels that are not hair-dark and not the white shirt.
    skin = (
        (band[:, :, 3] > 16)
        & (rgb[:, :, 0] > 140)
        & (rgb[:, :, 1] > 80)
        & (rgb[:, :, 1] < 190)
        & (rgb[:, :, 2] < 170)
    )
    if int(skin.sum()) < 8:
        color = (210, 132, 105, 255)
    else:
        sample = rgb[skin]
        color = tuple(int(np.median(sample[:, i])) for i in range(3)) + (255,)
    lids = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(lids)
    # Two lids, left and right eye, as rounded bars.
    draw.rounded_rectangle((int(w * 0.22), int(h * 0.50), int(w * 0.46), int(h * 0.60)), radius=8, fill=color)
    draw.rounded_rectangle((int(w * 0.54), int(h * 0.50), int(w * 0.78), int(h * 0.60)), radius=8, fill=color)
    return lids


def hero_card(view: Image.Image, max_side: int = 1100) -> Image.Image:
    keyed = _key_figure(view)
    tight, _ = tight_crop(keyed, 2)
    w, h = tight.size
    scale = max_side / max(w, h)
    if scale > 1.05:
        tight = tight.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    return tight


def build_all(reference: Path) -> dict[str, Image.Image]:
    views = load_views(reference)
    front_keyed = _key_figure(views["front"])
    front, _ = tight_crop(front_keyed, 1)
    layers = split_front(front)
    textures: dict[str, Image.Image] = {}
    for name, layer in layers.items():
        if name != "HEAD":
            layer = _keep_large_islands(layer, min_area=40 if name.startswith("SHOE") else 120)
        layer = trim_pale_fringe(layer)
        cropped = crop_alpha(layer, 0)
        if cropped.size[0] < 2 or cropped.size[1] < 2:
            continue
        if cropped.getbbox() is None:
            continue
        textures[name] = cropped
        textures[f"{name}_FULL"] = layer
    textures["FRONT_FULL"] = front
    for view_name in ("front", "three_quarter", "side", "back"):
        textures[f"HERO_{view_name.upper()}"] = hero_card(views[view_name])
    panels = expression_panels(reference)
    textures.update(build_face_textures(panels))
    if "HEAD" in textures:
        textures["BLINK_LIDS"] = paint_blink_lids(textures["HEAD"])
    return textures


def reassembly_preview(textures: dict[str, Image.Image]) -> Image.Image:
    full = textures["FRONT_FULL"]
    canvas = Image.new("RGBA", full.size, (232, 230, 226, 255))
    order = (
        "SHOE_L", "SHOE_R", "SHIN_L", "SHIN_R", "THIGH_L", "THIGH_R",
        "TORSO", "BAG", "ARM_L", "ARM_R", "TABLET", "HEAD",
    )
    for name in order:
        layer = textures.get(f"{name}_FULL")
        if layer:
            canvas.alpha_composite(layer)
    return canvas


if __name__ == "__main__":
    ref = Path("/workspace/media/reference/patty-patties-style-hires.png")
    tex = build_all(ref)
    out = Path("/tmp/patty-build")
    out.mkdir(exist_ok=True)
    reassembly_preview(tex).save(out / "reassembly.png")
    for name, image in sorted(tex.items()):
        if name.endswith("_FULL") or name.startswith("HERO") or name in {
            "HEAD", "TORSO", "ARM_L", "ARM_R", "BAG", "TABLET",
            "THIGH_L", "THIGH_R", "SHIN_L", "SHIN_R", "SHOE_L", "SHOE_R",
            "BLINK_LIDS", "MOUTH_SMILE", "MOUTH_SURPRISE", "MOUTH_OPEN",
        }:
            image.save(out / f"{name}.png")
            place = card_placement(tex[f"{name}_FULL"]) if f"{name}_FULL" in tex else None
            print(f"{name:16} {image.size} place={place}")
