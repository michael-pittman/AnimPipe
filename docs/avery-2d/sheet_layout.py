"""World placement for sheet-cut parts (assembled front silhouette)."""

from __future__ import annotations

# Rig-aligned figure span (meters, Z up) — matches proxy rest pose feet→crown.
FOOT_Z = 0.08
FIGURE_HEIGHT = 1.46
FIGURE_WIDTH = 0.52


def ny_to_z(ny: float) -> float:
    return FOOT_Z + (1.0 - ny) * FIGURE_HEIGHT


def nx_to_x(nx: float) -> float:
    return (nx - 0.5) * FIGURE_WIDTH


def part_plane(bbox: tuple[float, float, float, float]) -> tuple[tuple[float, float], tuple[float, float]]:
    x0, y0, x1, y1 = bbox
    cx = nx_to_x((x0 + x1) * 0.5)
    cz = ny_to_z((y0 + y1) * 0.5)
    w = max(0.02, (x1 - x0) * FIGURE_WIDTH)
    h = max(0.02, (y1 - y0) * FIGURE_HEIGHT)
    return (cx, cz), (w, h)


# Same normalized boxes as sheet_art.PART_FRONT for placement.
from sheet_art import PART_FRONT

LAYOUT: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {
    name: part_plane(box) for name, box in PART_FRONT.items()
}

# Per-object layout keys (mesh object → texture / layout key).
OBJECT_LAYOUT_KEY = {
    "GEO_AVERY_HEAD": "TEX_HEAD_SKIN",
    "GEO_AVERY_NECK": "TEX_NECK",
    "GEO_AVERY_TORSO": "TEX_ANATOMY_HIDDEN",
    "GEO_AVERY_SHIRT": "TEX_SHIRT",
    "GEO_AVERY_JACKET_BACK": "TEX_JACKET_BACK",
    "GEO_AVERY_JACKET.L": "TEX_JACKET_L",
    "GEO_AVERY_JACKET.R": "TEX_JACKET_R",
    "GEO_AVERY_TROUSERS": "TEX_TROUSERS",
    "GEO_AVERY_BELT": "TEX_BELT",
    "GEO_AVERY_SHOE.L": "TEX_SHOE",
    "GEO_AVERY_SHOE.R": "TEX_SHOE",
    "GEO_AVERY_HAIR_BACK": "TEX_HAIR_BACK",
    "GEO_AVERY_HAIR_FRONT": "TEX_HAIR_FRONT",
    "GEO_AVERY_GLASSES": "TEX_GLASSES",
    "GEO_AVERY_LANYARD": "TEX_LANYARD",
    "GEO_AVERY_BADGE": "TEX_BADGE",
    "GEO_AVERY_PATCH.L": "TEX_PATCH",
    "GEO_AVERY_PATCH.R": "TEX_PATCH",
    "GEO_AVERY_MOUTH": "TEX_MOUTH",
    "GEO_AVERY_MOUTH_INTERIOR": "TEX_MOUTH_INTERIOR",
    "GEO_AVERY_TEETH": "TEX_TEETH",
    "GEO_AVERY_EYE.L": "TEX_EYE_L",
    "GEO_AVERY_EYE.R": "TEX_EYE_R",
    "GEO_AVERY_PUPIL.L": "TEX_PUPIL",
    "GEO_AVERY_PUPIL.R": "TEX_PUPIL",
    "GEO_AVERY_EYELID.L": "TEX_EYELID",
    "GEO_AVERY_EYELID.R": "TEX_EYELID",
    "GEO_AVERY_BROW.L": "TEX_BROW_L",
    "GEO_AVERY_BROW.R": "TEX_BROW_R",
}

for side in ("L", "R"):
    OBJECT_LAYOUT_KEY[f"GEO_AVERY_UPPER_ARM.{side}"] = "TEX_UPPER_ARM"
    OBJECT_LAYOUT_KEY[f"GEO_AVERY_FOREARM.{side}"] = "TEX_FOREARM"
    OBJECT_LAYOUT_KEY[f"GEO_AVERY_HAND.{side}"] = "TEX_HAND"
    OBJECT_LAYOUT_KEY[f"GEO_AVERY_THIGH.{side}"] = "TEX_TROUSERS"
    OBJECT_LAYOUT_KEY[f"GEO_AVERY_SHIN.{side}"] = "TEX_TROUSERS"
    OBJECT_LAYOUT_KEY[f"GEO_AVERY_FOOT.{side}"] = "TEX_ANATOMY_HIDDEN"


def _mirror_x(box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = box
    return (1.0 - x1, y0, 1.0 - x0, y1)


def _split_lr(box: tuple[float, float, float, float], side: str) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = box
    mid = (x0 + x1) * 0.5
    if side == "L":
        return (x0, y0, mid, y1)
    return (mid, y0, x1, y1)


def layout_for_object(name: str) -> tuple[tuple[float, float], tuple[float, float]]:
    key = OBJECT_LAYOUT_KEY.get(name, "TEX_ANATOMY_HIDDEN")
    box = PART_FRONT.get(key, (0, 0, 0.01, 0.01))
    side = "R" if name.endswith(".R") else "L" if name.endswith(".L") else None

    if name == "GEO_AVERY_JACKET.R":
        box = PART_FRONT["TEX_JACKET_R"]
    elif name == "GEO_AVERY_JACKET.L":
        box = PART_FRONT["TEX_JACKET_L"]
    elif name in ("GEO_AVERY_SHOE.L", "GEO_AVERY_SHOE.R"):
        box = _split_lr(PART_FRONT["TEX_SHOE"], side or "L")
    elif name == "GEO_AVERY_HAND.R":
        box = PART_FRONT["TEX_HAND_R"]
    elif name == "GEO_AVERY_HAND.L":
        box = PART_FRONT["TEX_HAND"]
    elif name == "GEO_AVERY_FOREARM.R":
        box = _mirror_x(PART_FRONT["TEX_FOREARM"])
    elif name == "GEO_AVERY_FOREARM.L":
        box = PART_FRONT["TEX_FOREARM"]
    elif name == "GEO_AVERY_UPPER_ARM.L":
        box = PART_FRONT["TEX_UPPER_ARM"]
    elif name == "GEO_AVERY_UPPER_ARM.R":
        box = _mirror_x(PART_FRONT["TEX_UPPER_ARM"])
    elif name == "GEO_AVERY_PATCH.L":
        box = _mirror_x(PART_FRONT["TEX_PATCH"])
    elif name == "GEO_AVERY_PATCH.R":
        box = PART_FRONT["TEX_PATCH"]
    elif name in ("GEO_AVERY_THIGH.L", "GEO_AVERY_SHIN.L"):
        box = _split_lr(PART_FRONT["TEX_TROUSERS"], "L")
    elif name in ("GEO_AVERY_THIGH.R", "GEO_AVERY_SHIN.R"):
        box = _split_lr(PART_FRONT["TEX_TROUSERS"], "R")
    elif name == "GEO_AVERY_EYE.R":
        box = PART_FRONT["TEX_EYE_R"] if "TEX_EYE_R" in PART_FRONT else _mirror_x(PART_FRONT["TEX_EYE_L"])
    elif name == "GEO_AVERY_BROW.R":
        box = PART_FRONT["TEX_BROW_R"] if "TEX_BROW_R" in PART_FRONT else _mirror_x(PART_FRONT["TEX_BROW_L"])
    elif name in ("GEO_AVERY_PUPIL.L", "GEO_AVERY_PUPIL.R"):
        eye_box = PART_FRONT["TEX_EYE_L"] if side == "L" else PART_FRONT.get("TEX_EYE_R", _mirror_x(PART_FRONT["TEX_EYE_L"]))
        x0, y0, x1, y1 = eye_box
        cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
        box = (cx - 0.04, cy - 0.03, cx + 0.04, cy + 0.03)
    elif name in ("GEO_AVERY_EYELID.L", "GEO_AVERY_EYELID.R"):
        box = PART_FRONT["TEX_EYE_L"] if side == "L" else PART_FRONT.get("TEX_EYE_R", _mirror_x(PART_FRONT["TEX_EYE_L"]))
    elif name in ("GEO_AVERY_EYE.L", "GEO_AVERY_BROW.L"):
        box = PART_FRONT[key]

    return part_plane(box)
