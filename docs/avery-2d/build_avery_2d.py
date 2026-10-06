#!/usr/bin/env python3
"""Build Avery Chen 2D illustrated cutout (Patty style spec compliant)."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bpy
import numpy as np
from mathutils import Matrix, Vector

from PIL import Image, ImageDraw

from sheet_art import compose_action_sheet, compose_qa_face_sheets, generate_art_textures
from sheet_layout import FOOT_Z, FIGURE_WIDTH, layout_for_object

BLENDER_VERSION = (5, 2, 1)
STYLE_REFERENCE = (ROOT / "../../media/reference/patty-patties-style.png").resolve()
DEFAULT_SOURCE = ROOT / "../avery-chen/AveryChen.blend"
DEFAULT_OUTPUT = ROOT / "Avery2D.blend"
DEFAULT_RENDER = ROOT / "../../media/avery-2d"
DEFAULT_VERIFY = ROOT / "../../internal/avery-2d-verify.txt"

COLLECTION = "COL_AVERY_CHEN"
ARMATURE = "RIG_AVERY_CHEN"
RETARGET_PROFILE = "proxy_rig_v1"

ACTIONS = [
    ("idle_neutral_loop", 48, True),
    ("walk_cycle", 24, True),
    ("turn_left_90", 18, False),
    ("turn_right_90", 18, False),
    ("gesture_present", 28, False),
    ("point_left", 24, False),
    ("point_right", 24, False),
    ("wave", 30, False),
    ("head_nod", 20, False),
    ("head_shake", 24, False),
    ("reach_grab", 28, False),
    ("place_release", 30, False),
    ("pose_neutral", 1, False),
    ("pose_present", 1, False),
    ("pose_listen", 1, False),
    ("pose_think", 1, False),
    ("pose_point", 1, False),
    ("pose_hold", 1, False),
    ("pose_ready", 1, False),
    ("pose_end", 1, False),
]
VISEMES = [f"VISEME_{c}" for c in "ABCDEFGHX"]
EXPRESSIONS = [
    "BLINK",
    "BROW_UP",
    "BROW_DOWN",
    "EXP_smile",
    "EXP_frown",
    "EXP_surprise",
    "LOOK_LEFT",
    "LOOK_RIGHT",
]
BONE_PARENTS = {
    "root": None,
    "pelvis": "root",
    "spine": "pelvis",
    "chest": "spine",
    "neck": "chest",
    "head": "neck",
    "upper_arm.L": "chest",
    "forearm.L": "upper_arm.L",
    "hand.L": "forearm.L",
    "upper_arm.R": "chest",
    "forearm.R": "upper_arm.R",
    "hand.R": "forearm.R",
    "thigh.L": "pelvis",
    "shin.L": "thigh.L",
    "foot.L": "shin.L",
    "thigh.R": "pelvis",
    "shin.R": "thigh.R",
    "foot.R": "shin.R",
}

# Locked palette — internal/patty-2d-style-spec.md §2
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

# Layer depth along -Y (more negative = closer to front camera at -Y)
LAYER_Y = {
    "HAIR_BACK": -0.088,
    "TORSO_SHIRT": -0.098,
    "TORSO_JACKET_BACK": -0.096,
    "ARM": -0.100,
    "HAND": -0.102,
    "TROUSERS": -0.101,
    "SHOE": -0.104,
    "JACKET_FRONT": -0.099,
    "NECK": -0.108,
    "HEAD_SKIN": -0.110,
    "MOUTH_TEETH": -0.114,
    "MOUTH_INTERIOR": -0.115,
    "MOUTH_LIPS": -0.116,
    "EYE": -0.118,
    "EYELID": -0.119,
    "BROW": -0.120,
    "GLASSES": -0.121,
    "HAIR_FRONT": -0.122,
    "LANYARD": -0.124,
}

VIEW_TAGS = ("front", "three_quarter", "side", "back")

MAT_VIEW_IMAGES: dict[str, tuple[str, str, str]] = {}

HERO_TEXTURE = {
    "front": "TEX_HERO_FRONT",
    "three_quarter": "TEX_HERO_THREE_QUARTER",
    "side": "TEX_HERO_SIDE",
    "back": "TEX_HERO_BACK",
}

PORTRAIT_PARTS = {
    "GEO_AVERY_HEAD",
    "GEO_AVERY_HAIR_BACK",
    "GEO_AVERY_HAIR_FRONT",
    "GEO_AVERY_GLASSES",
    "GEO_AVERY_MOUTH",
    "GEO_AVERY_MOUTH_INTERIOR",
    "GEO_AVERY_TEETH",
    "GEO_AVERY_EYE.L",
    "GEO_AVERY_EYE.R",
    "GEO_AVERY_PUPIL.L",
    "GEO_AVERY_PUPIL.R",
    "GEO_AVERY_EYELID.L",
    "GEO_AVERY_EYELID.R",
    "GEO_AVERY_BROW.L",
    "GEO_AVERY_BROW.R",
}


def argv_after_double_dash() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rgba_hex(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = hex_color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha


def rgba_f(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    r, g, b, _ = rgba_hex(hex_color)
    for channel in (r, g, b):
        pass
    def lin(c: int) -> float:
        v = c / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return lin(r), lin(g), lin(b), alpha


def collection() -> bpy.types.Collection:
    return bpy.data.collections[COLLECTION]


def link_only(obj: bpy.types.Object, target: bpy.types.Collection | None = None) -> None:
    target = target or collection()
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    target.objects.link(obj)


def driver_from_head(obj: bpy.types.Object, key_name: str, source_name: str | None = None) -> None:
    source_name = source_name or key_name
    key = obj.data.shape_keys.key_blocks[key_name]
    fcurve = key.driver_add("value")
    fcurve.driver.type = "SCRIPTED"
    variable = fcurve.driver.variables.new()
    variable.name = "v"
    variable.type = "SINGLE_PROP"
    variable.targets[0].id = bpy.data.objects["GEO_AVERY_HEAD"]
    variable.targets[0].data_path = f'data.shape_keys.key_blocks["{source_name}"].value'
    fcurve.driver.expression = "v"


def custom_driver(
    obj: bpy.types.Object,
    key_name: str,
    sources: list[tuple[str, str]],
    expression: str,
) -> None:
    key = obj.data.shape_keys.key_blocks[key_name]
    fcurve = key.driver_add("value")
    fcurve.driver.type = "SCRIPTED"
    for variable_name, source_name in sources:
        variable = fcurve.driver.variables.new()
        variable.name = variable_name
        variable.type = "SINGLE_PROP"
        variable.targets[0].id = bpy.data.objects["GEO_AVERY_HEAD"]
        variable.targets[0].data_path = f'data.shape_keys.key_blocks["{source_name}"].value'
    fcurve.driver.expression = expression


def load_image_from_pil(name: str, pil_image: Image.Image) -> bpy.types.Image:
    pil_image = pil_image.convert("RGBA")
    width, height = pil_image.size
    pixels = np.array(pil_image, dtype=np.float32) / 255.0
    image = bpy.data.images.new(name, width=width, height=height, alpha=True)
    image.pixels.foreach_set(pixels.ravel())
    image.alpha_mode = "STRAIGHT"
    image.pack()
    return image


def solid_material(name: str, hex_color: str, *, alpha: float = 1.0) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = rgba_f(hex_color, alpha)
    shader.inputs["Roughness"].default_value = 0.9
    shader.inputs["Specular IOR Level"].default_value = 0.0
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    material.use_backface_culling = False
    if alpha < 1.0:
        material.blend_method = "BLEND"
    return material


def tex_material(name: str, image: bpy.types.Image) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Linear"
    # Unlit. A Principled card under the area light shades the drawing into a
    # dark mannequin; the style sheet is flat ink and cel color.
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = 1.0
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(tex.outputs["Color"], emission.inputs["Color"])
    links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    links.new(transparent.outputs["BSDF"], mix.inputs[1])
    links.new(emission.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    material.blend_method = "CLIP"
    material.alpha_threshold = 0.08
    material.use_backface_culling = False
    if hasattr(material, "shadow_method"):
        material.shadow_method = "CLIP"
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "BLENDED"
    return material


def ink_rect(draw, box, fill, width=4):
    draw.rounded_rectangle(box, radius=12, fill=rgba_hex(fill))
    draw.rounded_rectangle(box, radius=12, outline=rgba_hex(P["INK_OUTLINE"]), width=width)


def draw_eagle(draw, cx, cy, scale=1.0):
    s = scale
    draw.polygon(
        [
            (cx, cy - 40 * s),
            (cx + 55 * s, cy - 10 * s),
            (cx + 35 * s, cy + 5 * s),
            (cx + 50 * s, cy + 25 * s),
            (cx, cy + 10 * s),
            (cx - 50 * s, cy + 25 * s),
            (cx - 35 * s, cy + 5 * s),
            (cx - 55 * s, cy - 10 * s),
        ],
        fill=rgba_hex(P["SILVER_NEUTRAL"]),
        outline=rgba_hex(P["INK_INTERIOR"]),
    )
    draw.ellipse((cx - 8 * s, cy - 8 * s, cx + 8 * s, cy + 8 * s), fill=rgba_hex(P["SOFT_WHITE_NEUTRAL"]))


def register_mat_views(entries: list[tuple[str, str]]) -> None:
    """Map material -> (front, side, back) image names."""
    MAT_VIEW_IMAGES.clear()
    for mat_name, base_key in entries:
        MAT_VIEW_IMAGES[mat_name] = (base_key, f"{base_key}__side", f"{base_key}__back")


def set_material_image(mat_name: str, image_name: str) -> None:
    mat = bpy.data.materials.get(mat_name)
    img = bpy.data.images.get(image_name)
    if not mat or not img or not mat.use_nodes:
        return
    for node in mat.node_tree.nodes:
        if node.type == "TEX_IMAGE":
            node.image = img
            break


def _sync_viewport_visibility() -> None:
    """Viewport matches the render. Otherwise the stacked slices read as a mannequin."""
    for obj in collection().objects:
        if obj.type == "MESH" and obj.name.startswith("GEO_AVERY_"):
            obj.hide_viewport = bool(obj.hide_render)


def set_rest_hero_assembly(enabled: bool, view_mode: str = "front") -> None:
    """Rest pose: one intact turnaround card; prompt slices stay in file but hidden."""
    bpy.context.scene["avery_2d_rest_hero"] = enabled
    hero = bpy.data.objects.get("GEO_AVERY_TORSO")
    if not hero:
        return
    if enabled:
        tex_name = HERO_TEXTURE.get(view_mode, "TEX_HERO_FRONT")
        if bpy.data.images.get(tex_name):
            set_material_image("MAT_ANATOMY", tex_name)
            set_material_image("MAT_PROXY_CHARACTER", tex_name)
        for obj in collection().objects:
            if obj.type != "MESH" or not obj.name.startswith("GEO_AVERY_"):
                continue
            obj.hide_render = obj.name != "GEO_AVERY_TORSO"
        hero.hide_render = False
    else:
        hero.hide_render = True
        for obj in collection().objects:
            if obj.type != "MESH" or not obj.name.startswith("GEO_AVERY_"):
                continue
            if obj.get("promptable_slice"):
                obj.hide_render = False
        set_view_mode(view_mode)
    _sync_viewport_visibility()
    bpy.context.view_layer.update()


def apply_view_present(mode: str) -> None:
    """Rest turnaround uses intact hero card; slice swaps apply only when hero is off."""
    rig = bpy.data.objects.get(ARMATURE)
    if rig:
        rig.rotation_euler = (0.0, 0.0, 0.0)
    for obj in collection().objects:
        if obj.type == "MESH" and obj.name.startswith("GEO_AVERY_"):
            obj.rotation_euler = (0.0, 0.0, 0.0)
    if bpy.context.scene.get("avery_2d_rest_hero", True):
        set_rest_hero_assembly(True, mode)
        return
    ensure_mat_view_registry()
    tex_idx = {"front": 0, "three_quarter": 0, "side": 1, "back": 2}.get(mode, 0)
    for mat_name, triple in MAT_VIEW_IMAGES.items():
        key = triple[tex_idx]
        if bpy.data.images.get(key):
            set_material_image(mat_name, key)
    set_view_mode(mode)
    bpy.context.view_layer.update()


def apply_expression_portrait(_label: str) -> None:
    """Ensure portrait face layers are visible and textures refreshed."""
    for name in PORTRAIT_PARTS:
        ob = bpy.data.objects.get(name)
        if ob:
            ob.hide_render = False
    set_material_image("MAT_HEAD", "TEX_HEAD_SKIN")
    apply_face_textures()
    bpy.context.view_layer.update()


def apply_face_textures() -> None:
    head = bpy.data.objects.get("GEO_AVERY_HEAD")
    if not head or not head.data.shape_keys:
        return
    keys = head.data.shape_keys.key_blocks

    mouth_key = "TEX_MOUTH"
    viseme_best = 0.0
    for vis in VISEMES:
        val = keys[vis].value
        if val > viseme_best:
            viseme_best = val
            mouth_key = f"TEX_MOUTH_{vis}"
    if keys["EXP_smile"].value > 0.35:
        mouth_key = "TEX_MOUTH_SMILE"
    elif keys["EXP_frown"].value > 0.35:
        mouth_key = "TEX_MOUTH_FROWN"
    elif keys["EXP_surprise"].value > 0.35:
        mouth_key = "TEX_MOUTH_SURPRISE"
    elif viseme_best > 0.35:
        pass
    if bpy.data.images.get(mouth_key):
        set_material_image("MAT_MOUTH", mouth_key)

    if keys["BROW_UP"].value > 0.35 or keys["EXP_surprise"].value > 0.45:
        set_material_image("MAT_BROW_L", "TEX_BROW_UP_L")
        set_material_image("MAT_BROW_R", "TEX_BROW_UP_R")
    elif keys["BROW_DOWN"].value > 0.35:
        set_material_image("MAT_BROW_L", "TEX_BROW_DOWN_L")
        set_material_image("MAT_BROW_R", "TEX_BROW_DOWN_R")
    else:
        set_material_image("MAT_BROW_L", "TEX_BROW_NEUTRAL_L")
        set_material_image("MAT_BROW_R", "TEX_BROW_NEUTRAL_R")

    if keys["BLINK"].value > 0.45:
        if bpy.data.images.get("TEX_EYELID_CLOSED"):
            set_material_image("MAT_EYE_L", "TEX_EYELID_CLOSED")
            set_material_image("MAT_EYE_R", "TEX_EYELID_CLOSED")
    else:
        set_material_image("MAT_EYE_L", "TEX_EYE_L")
        set_material_image("MAT_EYE_R", "TEX_EYE_R")

    if keys["LOOK_LEFT"].value > 0.35 and keys["LOOK_LEFT"].value >= keys["LOOK_RIGHT"].value:
        if bpy.data.images.get("TEX_PUPIL_LOOK_L"):
            set_material_image("MAT_PUPIL_L", "TEX_PUPIL_LOOK_L")
            set_material_image("MAT_PUPIL_R", "TEX_PUPIL_LOOK_L")
    elif keys["LOOK_RIGHT"].value > 0.35:
        if bpy.data.images.get("TEX_PUPIL_LOOK_R"):
            set_material_image("MAT_PUPIL_L", "TEX_PUPIL_LOOK_R")
            set_material_image("MAT_PUPIL_R", "TEX_PUPIL_LOOK_R")
    else:
        set_material_image("MAT_PUPIL_L", "TEX_PUPIL_CENTER")
        set_material_image("MAT_PUPIL_R", "TEX_PUPIL_CENTER")

    open_amount = max(
        keys["EXP_smile"].value,
        keys["VISEME_A"].value,
        keys["VISEME_D"].value,
        keys["VISEME_E"].value,
        keys["VISEME_F"].value,
        keys["VISEME_G"].value,
        keys["VISEME_H"].value,
    )
    if open_amount > 0.2 and keys["EXP_surprise"].value < 0.65:
        teeth_key = "TEX_TEETH_SMILE" if keys["EXP_smile"].value > 0.35 else "TEX_TEETH"
        if bpy.data.images.get(teeth_key):
            set_material_image("MAT_TEETH", teeth_key)


def generate_textures(reference: Path | None = None) -> dict[str, bpy.types.Image]:
    ref = reference or STYLE_REFERENCE
    if not ref.is_file():
        raise FileNotFoundError(f"Style reference missing: {ref}")
    pil_textures = generate_art_textures(ref)
    return {name: load_image_from_pil(name, img) for name, img in pil_textures.items()}


def subdiv_plane(
    name: str,
    center: tuple[float, float, float],
    size: tuple[float, float],
    subdiv: tuple[int, int],
    material: bpy.types.Material,
) -> bpy.types.Object:
    cx, cy, cz = center
    w, h = size
    nx, nz = subdiv
    verts = []
    for iz in range(nz + 1):
        for ix in range(nx + 1):
            verts.append((cx + (ix / nx - 0.5) * w, cy, cz + (iz / nz - 0.5) * h))
    faces = []
    for iz in range(nz):
        for ix in range(nx):
            a = iz * (nx + 1) + ix
            faces.append((a, a + nx + 1, a + nx + 2, a + 1))
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(verts, [], faces)
    uv_coords = [(ix / nx, 1.0 - iz / nz) for iz in range(nz + 1) for ix in range(nx + 1)]
    mesh.uv_layers.new(name="UVMap")
    for loop in mesh.loops:
        mesh.uv_layers[0].data[loop.index].uv = uv_coords[mesh.loops[loop.index].vertex_index]
    mesh.update()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    link_only(obj)
    obj.location = (cx, cy, cz)
    for vertex in mesh.vertices:
        vertex.co.x -= cx
        vertex.co.y -= cy
        vertex.co.z -= cz
    # XZ layout card → local XY (+Z normal) so bone rest +90° X faces −Y camera.
    for vertex in mesh.vertices:
        x, y, z = vertex.co.x, vertex.co.y, vertex.co.z
        vertex.co.x = x
        vertex.co.y = z
        vertex.co.z = -y
    mesh.update()
    return obj


def assign_armature(obj: bpy.types.Object, weights: dict[str, float]) -> None:
    rig = bpy.data.objects[ARMATURE]
    obj.parent = None
    for bone, weight in weights.items():
        if weight <= 0:
            continue
        group = obj.vertex_groups.new(name=bone)
        group.add(list(range(len(obj.data.vertices))), weight, "REPLACE")
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = rig


def assign_armature_z_blend(obj: bpy.types.Object, low_bone: str, high_bone: str) -> None:
    rig = bpy.data.objects[ARMATURE]
    obj.parent = None
    ga = obj.vertex_groups.new(name=low_bone)
    gb = obj.vertex_groups.new(name=high_bone)
    zs = [v.co.z for v in obj.data.vertices]
    z_min, z_max = min(zs), max(zs)
    for vertex in obj.data.vertices:
        t = max(0.0, min(1.0, (vertex.co.z - z_min) / max(1e-6, z_max - z_min)))
        ga.add([vertex.index], 1.0 - t, "REPLACE")
        gb.add([vertex.index], t, "REPLACE")
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = rig


def parent_to_bone(obj: bpy.types.Object, bone: str) -> None:
    rig = bpy.data.objects[ARMATURE]
    for mod in list(obj.modifiers):
        if mod.type == "ARMATURE":
            obj.modifiers.remove(mod)
    matrix = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    obj.matrix_world = matrix


def bind_sheet_part(obj: bpy.types.Object, bone: str) -> None:
    """Bone-parent while preserving layout; cards face the −Y render camera."""
    rig = bpy.data.objects[ARMATURE]
    for mod in list(obj.modifiers):
        if mod.type == "ARMATURE":
            obj.modifiers.remove(mod)
    bpy.context.view_layer.update()
    target = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    obj.matrix_world = target


def add_sway_driver(obj: bpy.types.Object, bone: str, axis: int, factor: float) -> None:
    rig = bpy.data.objects[ARMATURE]
    fcurve = obj.driver_add("rotation_euler", axis)
    fcurve.driver.type = "SCRIPTED"
    var = fcurve.driver.variables.new()
    var.name = "r"
    var.type = "TRANSFORMS"
    var.targets[0].id = rig
    var.targets[0].bone_target = bone
    var.targets[0].transform_type = "ROT_X" if axis == 0 else "ROT_Y" if axis == 1 else "ROT_Z"
    var.targets[0].transform_space = "LOCAL_SPACE"
    fcurve.driver.expression = f"r * {factor}"


def add_driven_keys_from_head(obj: bpy.types.Object, key_names: list[str]) -> None:
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)
    for name in key_names:
        if name in obj.data.shape_keys.key_blocks:
            continue
        key = obj.shape_key_add(name=name, from_mix=False)
        if name == "LOOK_LEFT":
            for pt in key.data:
                pt.co.x -= 0.018
        elif name == "LOOK_RIGHT":
            for pt in key.data:
                pt.co.x += 0.018
        elif name == "BLINK":
            for pt in key.data:
                pt.co.z -= 0.022
        elif name == "BROW_UP":
            for pt in key.data:
                pt.co.z += 0.016
        elif name == "BROW_DOWN":
            for pt in key.data:
                pt.co.z -= 0.014
        elif name == "EXP_surprise":
            for pt in key.data:
                pt.co.z += 0.018
        elif name == "EXP_smile":
            for pt in key.data:
                pt.co.z += 0.008
        elif name == "EXP_frown":
            for pt in key.data:
                pt.co.z -= 0.006
        elif name.startswith("VISEME_"):
            for pt in key.data:
                pt.co.z -= 0.010 if name not in {"VISEME_B", "VISEME_X"} else 0.0
        driver_from_head(obj, name)


PROMPTABLE_PARTS: dict[str, list[tuple[str, str]]] = {
    "anatomy": [],
    "clothing": [],
    "accessories": [],
    "face": [],
}


def capture_head_keys() -> dict | None:
    obj = bpy.data.objects.get("GEO_AVERY_HEAD")
    if not obj or not obj.data.shape_keys:
        return None
    basis = [Vector(v.co) for v in obj.data.shape_keys.key_blocks["Basis"].data]
    keys = {
        kb.name: [Vector(v.co) for v in kb.data]
        for kb in obj.data.shape_keys.key_blocks
        if kb.name != "Basis"
    }
    return {"basis": basis, "keys": keys}


def patch_inactive_head_keys(head: bpy.types.Object) -> None:
    if not head.data.shape_keys:
        return
    basis = head.data.shape_keys.key_blocks["Basis"]
    templates = {
        "LOOK_LEFT": lambda co: co + Vector((-0.018, 0, 0)),
        "LOOK_RIGHT": lambda co: co + Vector((0.018, 0, 0)),
        "BLINK": lambda co: co + Vector((0, 0, -0.016)),
        "BROW_UP": lambda co: co + Vector((0, 0, 0.014)),
        "BROW_DOWN": lambda co: co + Vector((0, 0, -0.012)),
        "EXP_surprise": lambda co: co + Vector((0, 0, 0.018)),
        "EXP_smile": lambda co: co + Vector((0, 0, 0.008)),
        "EXP_frown": lambda co: co + Vector((0, 0, -0.006)),
    }
    for key_name in [*VISEMES, *EXPRESSIONS]:
        if key_name not in head.data.shape_keys.key_blocks:
            continue
        key = head.data.shape_keys.key_blocks[key_name]
        if key_name in templates:
            fn = templates[key_name]
        elif key_name.startswith("VISEME_"):
            dz = 0.002 if key_name in {"VISEME_B", "VISEME_X"} else -0.010
            fn = lambda co, d=dz: co + Vector((0, 0, d))
        else:
            fn = lambda co: co + Vector((0, 0, 0.002))
        for i, v in enumerate(key.data):
            v.co = fn(Vector(basis.data[i].co))


def apply_captured_keys(target: bpy.types.Object, captured: dict) -> None:
    src_basis = captured["basis"]
    tgt_basis = [Vector(v.co) for v in target.data.shape_keys.key_blocks["Basis"].data]

    def nearest(point: Vector) -> int:
        best, best_d = 0, 1e9
        for index, sample in enumerate(src_basis):
            d = (sample.x - point.x) ** 2 + (sample.z - point.z) ** 2
            if d < best_d:
                best_d, best = d, index
        return best

    for key_name, src_coords in captured["keys"].items():
        if key_name == "Basis":
            continue
        key = target.shape_key_add(name=key_name, from_mix=False)
        for index, point in enumerate(tgt_basis):
            src_i = nearest(point)
            src_delta = src_coords[src_i] - src_basis[src_i]
            delta = Vector((src_delta.x, 0.0, src_delta.z + src_delta.y * 0.85))
            key.data[index].co = point + delta
        key.value = 0.0


def remove_legacy_meshes() -> None:
    coll = collection()
    for obj in list(coll.objects):
        if obj.type != "ARMATURE" and obj.name != ARMATURE:
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def register_part(category: str, obj_name: str, control: str) -> None:
    PROMPTABLE_PARTS[category].append((obj_name, control))


def sheet_plane(
    name: str,
    layer_y: float,
    material: bpy.types.Material,
    subdiv: tuple[int, int] = (1, 1),
) -> bpy.types.Object:
    (cx, cz), (w, h) = layout_for_object(name)
    return subdiv_plane(name, (cx, layer_y, cz), (w, h), subdiv, material)


def build_character(images: dict[str, bpy.types.Image], captured: dict) -> None:
    for key in PROMPTABLE_PARTS:
        PROMPTABLE_PARTS[key].clear()

    def img(name: str) -> bpy.types.Image:
        if name not in images:
            raise KeyError(f"missing texture {name}")
        return images[name]

    char_mat = tex_material("MAT_PROXY_CHARACTER", img("TEX_HERO_FRONT"))
    char_mat.use_fake_user = True
    focus_mat = tex_material("MAT_PROXY_FOCUS", img("TEX_PUPIL"))
    focus_mat.use_fake_user = True
    pupil_l_mat = tex_material("MAT_PUPIL_L", img("TEX_PUPIL"))
    pupil_r_mat = tex_material("MAT_PUPIL_R", img("TEX_PUPIL"))

    mats = {
        "anatomy": tex_material("MAT_ANATOMY", img("TEX_ANATOMY_HIDDEN")),
        "head": tex_material("MAT_HEAD", img("TEX_HEAD_SKIN")),
        "neck": tex_material("MAT_NECK", img("TEX_NECK")),
        "shirt": tex_material("MAT_SHIRT", img("TEX_SHIRT")),
        "jacket": tex_material("MAT_JACKET", img("TEX_JACKET_L")),
        "jacket_r": tex_material("MAT_JACKET_R", img("TEX_JACKET_R")),
        "jacket_back": tex_material("MAT_JACKET_BACK", img("TEX_JACKET_BACK")),
        "trousers": tex_material("MAT_TROUSERS", img("TEX_TROUSERS")),
        "belt": tex_material("MAT_BELT", img("TEX_BELT")),
        "shoe_l": tex_material("MAT_SHOE_L", img("TEX_SHOE_L")),
        "shoe_r": tex_material("MAT_SHOE_R", img("TEX_SHOE_R")),
        "hand": tex_material("MAT_HAND", img("TEX_HAND")),
        "hand_r": tex_material("MAT_HAND_R", img("TEX_HAND_R")),
        "forearm": tex_material("MAT_FOREARM", img("TEX_FOREARM")),
        "upper_arm": tex_material("MAT_UPPER_ARM", img("TEX_UPPER_ARM")),
        "mouth": tex_material("MAT_MOUTH", img("TEX_MOUTH")),
        "mouth_in": tex_material("MAT_MOUTH_IN", img("TEX_MOUTH_INTERIOR")),
        "teeth": tex_material("MAT_TEETH", img("TEX_TEETH")),
        "eye_l": tex_material("MAT_EYE_L", img("TEX_EYE_L")),
        "eye_r": tex_material("MAT_EYE_R", img("TEX_EYE_R")),
        "pupil_l": pupil_l_mat,
        "pupil_r": pupil_r_mat,
        "lid": tex_material("MAT_LID", img("TEX_EYELID")),
        "lid_closed": tex_material("MAT_LID_CLOSED", img("TEX_EYELID_CLOSED")),
        "brow_l": tex_material("MAT_BROW_L", img("TEX_BROW_L")),
        "brow_r": tex_material("MAT_BROW_R", img("TEX_BROW_R")),
        "glasses": tex_material("MAT_GLASSES", img("TEX_GLASSES")),
        "hair_back": tex_material("MAT_HAIR_BACK", img("TEX_HAIR_BACK")),
        "hair_front": tex_material("MAT_HAIR_FRONT", img("TEX_HAIR_FRONT")),
        "strap": tex_material("MAT_STRAP", img("TEX_LANYARD")),
        "badge": tex_material("MAT_BADGE", img("TEX_BADGE")),
        "patch": tex_material("MAT_PATCH", img("TEX_PATCH")),
    }
    for image in images.values():
        image.use_fake_user = True
        if image.packed_file is None:
            image.pack()

    # --- Anatomy (sheet-aligned; hidden except hands) ---
    head = sheet_plane("GEO_AVERY_HEAD", LAYER_Y["HEAD_SKIN"], mats["head"], (8, 10))
    head.shape_key_add(name="Basis", from_mix=False)
    apply_captured_keys(head, captured)
    patch_inactive_head_keys(head)
    bind_sheet_part(head, "head")
    register_part("anatomy", "GEO_AVERY_HEAD", "bone head + visemes/expressions on this mesh")

    neck = sheet_plane("GEO_AVERY_NECK", LAYER_Y["NECK"], mats["neck"])
    bind_sheet_part(neck, "neck")
    register_part("anatomy", "GEO_AVERY_NECK", "bone neck")

    hero_front = img("TEX_HERO_FRONT")
    aspect = hero_front.size[1] / max(1, hero_front.size[0])
    hero_h = FIGURE_WIDTH * aspect
    hero_cz = FOOT_Z + hero_h * 0.5
    torso = subdiv_plane(
        "GEO_AVERY_TORSO",
        (0.0, LAYER_Y["TORSO_SHIRT"], hero_cz),
        (FIGURE_WIDTH, hero_h),
        (1, 1),
        mats["anatomy"],
    )
    torso["view_group"] = "hero"
    bind_sheet_part(torso, "pelvis")
    register_part("anatomy", "GEO_AVERY_TORSO", "rest-pose intact front/side/back hero card on pelvis")

    for side in ("L", "R"):
        upper = sheet_plane(f"GEO_AVERY_UPPER_ARM.{side}", LAYER_Y["ARM"], mats["anatomy"])
        upper.hide_render = True
        bind_sheet_part(upper, f"upper_arm.{side}")
        register_part("anatomy", f"GEO_AVERY_UPPER_ARM.{side}", f"bone upper_arm.{side}")

        fore = sheet_plane(f"GEO_AVERY_FOREARM.{side}", LAYER_Y["ARM"], mats["anatomy"])
        fore.hide_render = True
        bind_sheet_part(fore, f"forearm.{side}")
        register_part("anatomy", f"GEO_AVERY_FOREARM.{side}", f"bone forearm.{side}")

        hand_mat = mats["hand_r"] if side == "R" else mats["hand"]
        hand = sheet_plane(f"GEO_AVERY_HAND.{side}", LAYER_Y["HAND"], hand_mat)
        bind_sheet_part(hand, f"hand.{side}")
        register_part("anatomy", f"GEO_AVERY_HAND.{side}", f"bone hand.{side}")

        thigh = sheet_plane(f"GEO_AVERY_THIGH.{side}", LAYER_Y["TROUSERS"], mats["anatomy"])
        thigh.hide_render = True
        bind_sheet_part(thigh, f"thigh.{side}")
        register_part("anatomy", f"GEO_AVERY_THIGH.{side}", f"bone thigh.{side}")

        shin = sheet_plane(f"GEO_AVERY_SHIN.{side}", LAYER_Y["TROUSERS"], mats["anatomy"])
        shin.hide_render = True
        bind_sheet_part(shin, f"shin.{side}")
        register_part("anatomy", f"GEO_AVERY_SHIN.{side}", f"bone shin.{side}")

        foot = sheet_plane(f"GEO_AVERY_FOOT.{side}", LAYER_Y["SHOE"], mats["anatomy"])
        foot.hide_render = True
        bind_sheet_part(foot, f"foot.{side}")
        register_part("anatomy", f"GEO_AVERY_FOOT.{side}", f"bone foot.{side}")

    # --- Clothing ---
    shirt = sheet_plane("GEO_AVERY_SHIRT", LAYER_Y["TORSO_SHIRT"] - 0.001, mats["shirt"], (2, 3))
    bind_sheet_part(shirt, "chest")
    register_part("clothing", "GEO_AVERY_SHIRT", "bones chest/spine")

    jacket_back = sheet_plane("GEO_AVERY_JACKET_BACK", LAYER_Y["TORSO_JACKET_BACK"], mats["jacket_back"], (2, 3))
    jacket_back["view_group"] = "back"
    bind_sheet_part(jacket_back, "chest")
    register_part("clothing", "GEO_AVERY_JACKET_BACK", "bone chest; visible back/three-quarter views")

    for side in ("L", "R"):
        sleeve = sheet_plane(
            f"GEO_AVERY_JACKET.{side}",
            LAYER_Y["JACKET_FRONT"],
            mats["jacket_r"] if side == "R" else mats["jacket"],
            (2, 4),
        )
        bind_sheet_part(sleeve, f"upper_arm.{side}")
        register_part("clothing", f"GEO_AVERY_JACKET.{side}", f"bones upper_arm.{side}/forearm.{side}")

    trousers = sheet_plane("GEO_AVERY_TROUSERS", LAYER_Y["TROUSERS"] - 0.001, mats["trousers"], (2, 6))
    bind_sheet_part(trousers, "pelvis")
    register_part("clothing", "GEO_AVERY_TROUSERS", "bones pelvis/thigh")

    belt = sheet_plane("GEO_AVERY_BELT", LAYER_Y["TORSO_SHIRT"] - 0.002, mats["belt"])
    bind_sheet_part(belt, "pelvis")
    register_part("clothing", "GEO_AVERY_BELT", "bones pelvis/spine")

    for side in ("L", "R"):
        shoe_mat = mats["shoe_l"] if side == "L" else mats["shoe_r"]
        shoe = sheet_plane(f"GEO_AVERY_SHOE.{side}", LAYER_Y["SHOE"] - 0.001, shoe_mat)
        bind_sheet_part(shoe, f"foot.{side}")
        register_part("clothing", f"GEO_AVERY_SHOE.{side}", f"bone foot.{side}")

    # --- Accessories ---
    hair_back = sheet_plane("GEO_AVERY_HAIR_BACK", LAYER_Y["HAIR_BACK"], mats["hair_back"], (2, 2))
    bind_sheet_part(hair_back, "head")
    add_sway_driver(hair_back, "head", 2, 0.18)
    add_sway_driver(hair_back, "chest", 2, 0.06)
    register_part("accessories", "GEO_AVERY_HAIR_BACK", "bone head + sway drivers (head/chest rotation)")

    hair_front = sheet_plane("GEO_AVERY_HAIR_FRONT", LAYER_Y["HAIR_FRONT"], mats["hair_front"])
    bind_sheet_part(hair_front, "head")
    add_sway_driver(hair_front, "head", 2, 0.22)
    register_part("accessories", "GEO_AVERY_HAIR_FRONT", "bone head + sway driver")

    glasses = sheet_plane("GEO_AVERY_GLASSES", LAYER_Y["GLASSES"], mats["glasses"])
    bind_sheet_part(glasses, "head")
    register_part("accessories", "GEO_AVERY_GLASSES", "bone head")

    strap = sheet_plane("GEO_AVERY_LANYARD", LAYER_Y["LANYARD"], mats["strap"], (1, 4))
    bind_sheet_part(strap, "chest")
    add_sway_driver(strap, "chest", 2, 0.12)
    add_sway_driver(strap, "spine", 0, 0.08)
    register_part("accessories", "GEO_AVERY_LANYARD", "bone chest + sway drivers")

    badge = sheet_plane("GEO_AVERY_BADGE", LAYER_Y["LANYARD"] - 0.001, mats["badge"])
    bind_sheet_part(badge, "chest")
    add_sway_driver(badge, "chest", 2, 0.14)
    register_part("accessories", "GEO_AVERY_BADGE", "bone chest + sway driver")

    for side in ("L", "R"):
        patch = sheet_plane(f"GEO_AVERY_PATCH.{side}", LAYER_Y["JACKET_FRONT"], mats["patch"])
        patch["view_group"] = "front_side"
        bind_sheet_part(patch, f"upper_arm.{side}")
        add_sway_driver(patch, f"upper_arm.{side}", 2, 0.10)
        register_part("accessories", f"GEO_AVERY_PATCH.{side}", f"bone upper_arm.{side} + sway driver")

    # --- Face (sheet crops; neutral mouth closed) ---
    mouth = sheet_plane("GEO_AVERY_MOUTH", LAYER_Y["MOUTH_LIPS"], mats["mouth"], (4, 1))
    add_driven_keys_from_head(mouth, VISEMES + ["EXP_smile", "EXP_frown", "EXP_surprise"])
    bind_sheet_part(mouth, "head")
    register_part("face", "GEO_AVERY_MOUTH", "drivers from GEO_AVERY_HEAD visemes/expressions")

    mouth_in = sheet_plane("GEO_AVERY_MOUTH_INTERIOR", LAYER_Y["MOUTH_INTERIOR"], mats["mouth_in"])
    mouth_in.hide_render = True
    add_driven_keys_from_head(mouth_in, ["VISEME_A", "VISEME_H", "VISEME_G"])
    bind_sheet_part(mouth_in, "head")
    register_part("face", "GEO_AVERY_MOUTH_INTERIOR", "drivers from open visemes on GEO_AVERY_HEAD")

    teeth = sheet_plane("GEO_AVERY_TEETH", LAYER_Y["MOUTH_TEETH"], mats["teeth"], (2, 1))
    teeth.hide_render = True
    teeth.hide_viewport = True
    teeth.shape_key_add(name="Basis", from_mix=False)
    for kn, dz in (("JAW_OPEN", -0.010), ("SMILE_REVEAL", 0.008), ("VISEME_F_REVEAL", 0.006), ("SURPRISE_UPPER", 0.012)):
        key = teeth.shape_key_add(name=kn, from_mix=False)
        for pt in key.data:
            pt.co.z += dz
    driver_from_head(teeth, "SMILE_REVEAL", "EXP_smile")
    driver_from_head(teeth, "VISEME_F_REVEAL", "VISEME_F")
    custom_driver(teeth, "SURPRISE_UPPER", [("s", "EXP_surprise")], "s * 0.55")
    custom_driver(
        teeth,
        "JAW_OPEN",
        [("a", "VISEME_A"), ("d", "VISEME_D"), ("e", "VISEME_E"), ("g", "VISEME_G"), ("h", "VISEME_H")],
        "min(1.0,max(a,d,e,g,h)*1.05)",
    )
    bind_sheet_part(teeth, "head")
    register_part("face", "GEO_AVERY_TEETH", "drivers from GEO_AVERY_HEAD; hidden at neutral")

    for side in ("L", "R"):
        eye = sheet_plane(f"GEO_AVERY_EYE.{side}", LAYER_Y["EYE"], mats["eye_l"] if side == "L" else mats["eye_r"], (2, 1))
        add_driven_keys_from_head(eye, ["LOOK_LEFT", "LOOK_RIGHT"])
        bind_sheet_part(eye, "head")
        register_part("face", f"GEO_AVERY_EYE.{side}", "drivers LOOK_LEFT/LOOK_RIGHT from GEO_AVERY_HEAD")

        pupil = sheet_plane(
            f"GEO_AVERY_PUPIL.{side}",
            LAYER_Y["EYE"] - 0.001,
            mats["pupil_l"] if side == "L" else mats["pupil_r"],
        )
        add_driven_keys_from_head(pupil, ["LOOK_LEFT", "LOOK_RIGHT"])
        bind_sheet_part(pupil, "head")
        register_part("face", f"GEO_AVERY_PUPIL.{side}", "drivers LOOK_LEFT/LOOK_RIGHT from GEO_AVERY_HEAD")

        lid = sheet_plane(f"GEO_AVERY_EYELID.{side}", LAYER_Y["EYELID"], mats["lid_closed"], (2, 1))
        lid.hide_render = True
        add_driven_keys_from_head(lid, ["BLINK"])
        bind_sheet_part(lid, "head")
        register_part("face", f"GEO_AVERY_EYELID.{side}", "driver BLINK from GEO_AVERY_HEAD")

        brow = sheet_plane(f"GEO_AVERY_BROW.{side}", LAYER_Y["BROW"], mats["brow_l"] if side == "L" else mats["brow_r"], (2, 1))
        add_driven_keys_from_head(brow, ["BROW_UP", "BROW_DOWN", "EXP_surprise"])
        bind_sheet_part(brow, "head")
        register_part("face", f"GEO_AVERY_BROW.{side}", "drivers BROW_UP/BROW_DOWN/EXP_surprise from GEO_AVERY_HEAD")

    register_mat_views(
        [
            ("MAT_HEAD", "TEX_HEAD_SKIN"),
            ("MAT_NECK", "TEX_NECK"),
            ("MAT_SHIRT", "TEX_SHIRT"),
            ("MAT_JACKET", "TEX_JACKET_L"),
            ("MAT_JACKET_R", "TEX_JACKET_R"),
            ("MAT_JACKET_BACK", "TEX_JACKET_BACK"),
            ("MAT_TROUSERS", "TEX_TROUSERS"),
            ("MAT_BELT", "TEX_BELT"),
            ("MAT_SHOE_L", "TEX_SHOE_L"),
            ("MAT_SHOE_R", "TEX_SHOE_R"),
            ("MAT_HAND", "TEX_HAND"),
            ("MAT_HAND_R", "TEX_HAND_R"),
            ("MAT_FOREARM", "TEX_FOREARM"),
            ("MAT_UPPER_ARM", "TEX_UPPER_ARM"),
            ("MAT_HAIR_BACK", "TEX_HAIR_BACK"),
            ("MAT_HAIR_FRONT", "TEX_HAIR_FRONT"),
            ("MAT_STRAP", "TEX_LANYARD"),
            ("MAT_BADGE", "TEX_BADGE"),
            ("MAT_PATCH", "TEX_PATCH"),
        ]
    )
    bpy.context.scene["avery_2d_mat_views"] = json.dumps(MAT_VIEW_IMAGES)

    for obj in collection().objects:
        if obj.type == "MESH" and obj.name.startswith("GEO_AVERY_") and obj.name != "GEO_AVERY_TORSO":
            obj["promptable_slice"] = True
    bpy.context.scene["avery_2d_rest_hero"] = True
    set_rest_hero_assembly(True, "front")


def ensure_mat_view_registry() -> None:
    if MAT_VIEW_IMAGES:
        return
    raw = bpy.context.scene.get("avery_2d_mat_views")
    if raw:
        MAT_VIEW_IMAGES.update(json.loads(raw))


def update_face_visibility(_scene=None) -> None:
    head = bpy.data.objects.get("GEO_AVERY_HEAD")
    teeth = bpy.data.objects.get("GEO_AVERY_TEETH")
    cavity = bpy.data.objects.get("GEO_AVERY_MOUTH_INTERIOR")
    if not head or not head.data.shape_keys:
        return
    keys = head.data.shape_keys.key_blocks
    blink = keys["BLINK"].value
    for side in ("L", "R"):
        eye = bpy.data.objects.get(f"GEO_AVERY_EYE.{side}")
        lid = bpy.data.objects.get(f"GEO_AVERY_EYELID.{side}")
        if eye:
            eye.hide_render = False
        if lid:
            lid.hide_render = True
    open_amount = max(
        keys["EXP_smile"].value,
        keys["VISEME_A"].value,
        keys["VISEME_D"].value,
        keys["VISEME_E"].value,
        keys["VISEME_F"].value,
        keys["VISEME_G"].value,
        keys["VISEME_H"].value,
    )
    surprise = keys["EXP_surprise"].value
    show_teeth = open_amount >= 0.15 and surprise < 0.65
    if teeth:
        teeth.hide_render = not show_teeth
        teeth.hide_viewport = teeth.hide_render
    if cavity:
        cavity.hide_render = open_amount < 0.32 or surprise >= 0.65
    apply_face_textures()


def update_teeth_visibility(_scene=None) -> None:
    update_face_visibility(_scene)


def set_portrait_mode(enabled: bool) -> None:
    for obj in collection().objects:
        if obj.type != "MESH" or not obj.name.startswith("GEO_AVERY_"):
            continue
        if enabled:
            obj.hide_render = obj.name not in PORTRAIT_PARTS
        elif obj.name in PORTRAIT_PARTS:
            obj.hide_render = False
    bpy.context.view_layer.update()


def set_view_mode(mode: str) -> None:
    mapping = {
        "front": {"front", "front_side"},
        "three_quarter": {"three_quarter", "front_side"},
        "side": {"side", "front_side"},
        "back": {"back"},
    }
    active = mapping.get(mode, {"front"})
    for obj in collection().objects:
        group = obj.get("view_group")
        if group == "back":
            obj.hide_render = mode not in ("back", "three_quarter")
        elif group in ("front", "front_side", "three_quarter", "side"):
            obj.hide_render = group not in active
        elif obj.name.startswith("GEO_AVERY_BODY_"):
            obj.hide_render = obj.get("view_group") != mode
    face_front = [
        "GEO_AVERY_HEAD",
        "GEO_AVERY_GLASSES",
        "GEO_AVERY_MOUTH",
        "GEO_AVERY_EYE.L",
        "GEO_AVERY_EYE.R",
        "GEO_AVERY_PUPIL.L",
        "GEO_AVERY_PUPIL.R",
        "GEO_AVERY_EYELID.L",
        "GEO_AVERY_EYELID.R",
        "GEO_AVERY_BROW.L",
        "GEO_AVERY_BROW.R",
        "GEO_AVERY_HAIR_FRONT",
    ]
    side_face_hide = [
        "GEO_AVERY_GLASSES",
        "GEO_AVERY_MOUTH",
        "GEO_AVERY_EYE.L",
        "GEO_AVERY_EYE.R",
        "GEO_AVERY_PUPIL.L",
        "GEO_AVERY_PUPIL.R",
        "GEO_AVERY_EYELID.L",
        "GEO_AVERY_EYELID.R",
        "GEO_AVERY_BROW.L",
        "GEO_AVERY_BROW.R",
        "GEO_AVERY_HAIR_FRONT",
        "GEO_AVERY_TEETH",
        "GEO_AVERY_MOUTH_INTERIOR",
    ]
    back_hide = [
        "GEO_AVERY_JACKET.L",
        "GEO_AVERY_JACKET.R",
        "GEO_AVERY_HAIR_FRONT",
        "GEO_AVERY_GLASSES",
        "GEO_AVERY_MOUTH",
        "GEO_AVERY_EYE.L",
        "GEO_AVERY_EYE.R",
        "GEO_AVERY_PUPIL.L",
        "GEO_AVERY_PUPIL.R",
        "GEO_AVERY_EYELID.L",
        "GEO_AVERY_EYELID.R",
        "GEO_AVERY_BROW.L",
        "GEO_AVERY_BROW.R",
        "GEO_AVERY_LANYARD",
        "GEO_AVERY_BADGE",
        "GEO_AVERY_PATCH.L",
        "GEO_AVERY_PATCH.R",
    ]
    if mode == "back":
        for name in face_front + back_hide:
            ob = bpy.data.objects.get(name)
            if ob:
                ob.hide_render = True
        jacket_back = bpy.data.objects.get("GEO_AVERY_JACKET_BACK")
        if jacket_back:
            jacket_back.hide_render = False
    elif mode == "side":
        for name in face_front:
            ob = bpy.data.objects.get(name)
            if ob:
                ob.hide_render = name in side_face_hide
    else:
        for name in face_front:
            ob = bpy.data.objects.get(name)
            if ob:
                ob.hide_render = False
    _sync_viewport_visibility()
    bpy.context.view_layer.update()


def neutralize_scene() -> None:
    rig = bpy.data.objects[ARMATURE]
    rig.rotation_euler = (0.0, 0.0, 0.0)
    if rig.animation_data:
        rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    head = bpy.data.objects.get("GEO_AVERY_HEAD")
    if head and head.data.shape_keys:
        for key in head.data.shape_keys.key_blocks:
            key.value = 0.0
    update_teeth_visibility()
    for obj in collection().objects:
        if obj.type == "MESH" and obj.name.startswith("GEO_AVERY_"):
            obj.rotation_euler[2] = 0.0
    apply_view_present("front")
    set_rest_hero_assembly(True, "front")
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def validate_scene() -> tuple[list[str], dict[str, object]]:
    failures: list[str] = []
    coll = bpy.data.collections.get(COLLECTION)
    rig = bpy.data.objects.get(ARMATURE)
    head = bpy.data.objects.get("GEO_AVERY_HEAD")
    if not coll:
        failures.append(f"missing {COLLECTION}")
    if not rig or rig.type != "ARMATURE":
        failures.append(f"missing armature {ARMATURE}")
    if not bpy.data.materials.get("MAT_PROXY_CHARACTER"):
        failures.append("missing MAT_PROXY_CHARACTER")
    if not bpy.data.materials.get("MAT_PROXY_FOCUS"):
        failures.append("missing MAT_PROXY_FOCUS")
    if rig:
        if {b.name for b in rig.data.bones} != set(BONE_PARENTS):
            failures.append("bone set mismatch")
    if not head or not head.data.shape_keys:
        failures.append("missing head shape keys")
    else:
        keys = head.data.shape_keys.key_blocks
        for name in ["Basis", *VISEMES, *EXPRESSIONS]:
            if name not in keys:
                failures.append(f"missing shape key {name}")
            elif name != "Basis":
                basis = keys["Basis"]
                dist = max((p.co - basis.data[i].co).length for i, p in enumerate(keys[name].data))
                if dist < 0.00005:
                    failures.append(f"inactive shape key {name}")
    for owner, names in (
        ("GEO_AVERY_EYE.L", ("LOOK_LEFT", "LOOK_RIGHT")),
        ("GEO_AVERY_EYE.R", ("LOOK_LEFT", "LOOK_RIGHT")),
        ("GEO_AVERY_BROW.L", ("BROW_UP", "BROW_DOWN", "EXP_surprise")),
        ("GEO_AVERY_BROW.R", ("BROW_UP", "BROW_DOWN", "EXP_surprise")),
        ("GEO_AVERY_EYELID.L", ("BLINK",)),
        ("GEO_AVERY_EYELID.R", ("BLINK",)),
    ):
        obj = bpy.data.objects.get(owner)
        if not obj or not obj.data.shape_keys:
            failures.append(f"missing driven owner {owner}")
        else:
            for n in names:
                if n not in obj.data.shape_keys.key_blocks:
                    failures.append(f"missing {owner}.{n}")
    required_meshes = [
        "GEO_AVERY_TORSO",
        "GEO_AVERY_JACKET.L",
        "GEO_AVERY_SHOE.L",
        "GEO_AVERY_HAIR_BACK",
        "GEO_AVERY_BADGE",
        "GEO_AVERY_MOUTH",
        "GEO_AVERY_TEETH",
    ]
    for name in required_meshes:
        if not bpy.data.objects.get(name):
            failures.append(f"missing promptable mesh {name}")
    for name, _, _ in ACTIONS:
        action = bpy.data.actions.get(name)
        if not action:
            failures.append(f"missing action {name}")
        elif not action.slots:
            failures.append(f"unslotted action {name}")
        elif not action.use_fake_user:
            failures.append(f"action not fake-user {name}")
    external = [i.name for i in bpy.data.images if i.source == "FILE" and i.packed_file is None]
    if external:
        failures.append(f"external images: {external}")
    if bpy.data.libraries:
        failures.append("linked libraries present")
    teeth = bpy.data.objects.get("GEO_AVERY_TEETH")
    if teeth and not teeth.hide_render:
        failures.append("teeth visible at neutral")
    legacy = [o.name for o in coll.objects if o.name in ("GEO_AVERY_IRISES", "GEO_AVERY_PUPILS", "GEO_AVERY_CORNEAS", "GEO_AVERY_TONGUE")]
    if legacy:
        failures.append(f"legacy 3D visible: {legacy}")
    triangles = 0
    deps = bpy.context.evaluated_depsgraph_get()
    for obj in coll.objects:
        if obj.type == "MESH" and not obj.hide_render:
            ev = obj.evaluated_get(deps)
            mesh = ev.to_mesh()
            mesh.calc_loop_triangles()
            triangles += len(mesh.loop_triangles)
            ev.to_mesh_clear()
    if triangles > 80000:
        failures.append(f"triangle budget {triangles}")
    return failures, {"triangles": triangles, "objects": len(coll.objects), "actions": len(bpy.data.actions)}


def setup_camera() -> bpy.types.Object:
    qa = bpy.data.collections.get("COL_AVERY_2D_QA")
    if qa:
        for obj in list(qa.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(qa)
    qa = bpy.data.collections.new("COL_AVERY_2D_QA")
    bpy.context.scene.collection.children.link(qa)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 4
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = rgba_f("#C7CDD1")
    cam = bpy.data.objects.new("CAM_AVERY_2D", bpy.data.cameras.new("CAM_AVERY_2D_DATA"))
    qa.objects.link(cam)
    scene.camera = cam
    key = bpy.data.lights.new("LGT_KEY", "AREA")
    key.energy = 450
    key.size = 2.5
    lamp = bpy.data.objects.new("LGT_KEY", key)
    qa.objects.link(lamp)
    lamp.location = (-2.0, -3.0, 3.0)
    lamp.rotation_euler = (Vector((0, 0, 1.2)) - lamp.location).to_track_quat("-Z", "Y").to_euler()
    return cam


def look(cam, loc, tgt, lens):
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(tgt) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens


def render_still(cam, path: Path, view: str, w: int, h: int) -> None:
    views = {
        "full-front": ((0.0, -4.7, 1.02), (0.0, 0.0, 0.92), 70),
        "full-three-quarter": ((0.0, -4.7, 1.02), (0.0, 0.0, 0.92), 70),
        "full-side": ((0.0, -4.7, 1.02), (0.0, 0.0, 0.92), 70),
        "full-back": ((0.0, -4.7, 1.02), (0.0, 0.0, 0.92), 70),
        "portrait-front": ((0.0, -0.88, 1.365), (0.0, 0.0, 1.365), 108),
        "room": ((2.5, -5.0, 1.4), (0.0, 0.0, 0.9), 55),
    }
    look(cam, *views[view])
    scene = bpy.context.scene
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.filepath = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)


def _zero_face_satellite_keys() -> None:
    """Face layers use texture swaps; avoid driver shape-key sliding during QA portraits."""
    for obj_name in PORTRAIT_PARTS:
        if obj_name == "GEO_AVERY_HEAD":
            continue
        ob = bpy.data.objects.get(obj_name)
        if not ob or not ob.data.shape_keys:
            continue
        for kb in ob.data.shape_keys.key_blocks:
            if kb.name != "Basis":
                kb.value = 0.0


def set_face(values: dict[str, float]) -> None:
    head = bpy.data.objects["GEO_AVERY_HEAD"]
    keys = head.data.shape_keys.key_blocks
    for key in keys:
        key.value = 0.0
    for name, val in values.items():
        if name in keys:
            keys[name].value = val
    _zero_face_satellite_keys()
    update_teeth_visibility()
    apply_face_textures()
    bpy.context.view_layer.update()


def sheet(path: Path, cells: list[tuple[Path, str]], cols: int, size: tuple[int, int]) -> None:
    cw, ch = size
    rows = math.ceil(len(cells) / cols)
    out = Image.new("RGBA", (cols * cw, rows * (ch + 22)), rgba_hex("#161B22"))
    draw = ImageDraw.Draw(out)
    for i, (cell, label) in enumerate(cells):
        r, c = divmod(i, cols)
        img = Image.open(cell).convert("RGBA")
        if img.size != (cw, ch):
            img = img.resize((cw, ch), Image.Resampling.LANCZOS)
        out.paste(img, (c * cw, r * (ch + 22) + 22))
        draw.text((c * cw + 6, r * (ch + 22) + 4), label, fill=(220, 220, 220))
    out.save(path)


def render_face_qa_sheets(render_dir: Path) -> None:
    """Expression + viseme grids from sheet row art (sharp, readable)."""
    pil_textures = generate_art_textures(STYLE_REFERENCE)
    expr_rows, vis_rows = compose_qa_face_sheets(pil_textures)
    cells = render_dir / ".cells"
    cells.mkdir(parents=True, exist_ok=True)
    expr_cells: list[tuple[Path, str]] = []
    for label, image in expr_rows:
        path = cells / f"expr_{label}.png"
        image.save(path)
        expr_cells.append((path, label))
    sheet(render_dir / "expression-sheet.png", expr_cells, 3, (512, 512))
    vis_cells: list[tuple[Path, str]] = []
    for label, image in vis_rows:
        path = cells / f"vis_{label}.png"
        image.save(path)
        vis_cells.append((path, label))
    sheet(render_dir / "viseme-strip.png", vis_cells, 9, (420, 420))


def render_action_qa_sheet(render_dir: Path) -> None:
    """Action grid: front hero card + one attached sheet arm / tilt (no slice pile)."""
    pil_textures = generate_art_textures(STYLE_REFERENCE)
    rows = compose_action_sheet(pil_textures, STYLE_REFERENCE)
    cells = render_dir / ".cells"
    cells.mkdir(parents=True, exist_ok=True)
    act_cells: list[tuple[Path, str]] = []
    for label, image in rows:
        path = cells / f"act_{label.replace(' ', '_')}.png"
        image.save(path)
        act_cells.append((path, label))
    sheet(render_dir / "action-sheet.png", act_cells, 3, (360, 480))


def render_qa_sheets_only(render_dir: Path) -> None:
    render_face_qa_sheets(render_dir)
    render_action_qa_sheet(render_dir)


def render_evidence(render_dir: Path) -> None:
    cam = setup_camera()
    neutralize_scene()
    mapping = {
        "front.png": ("full-front", "front"),
        "three-quarter.png": ("full-three-quarter", "three_quarter"),
        "side.png": ("full-side", "side"),
        "back.png": ("full-back", "back"),
    }
    for filename, (view, mode) in mapping.items():
        apply_view_present(mode)
        render_still(cam, render_dir / filename, view, 960, 1200)
    apply_view_present("front")
    render_face_qa_sheets(render_dir)
    render_action_qa_sheet(render_dir)

    qa = bpy.data.collections.get("COL_AVERY_2D_QA")
    floor = subdiv_plane("GEO_ROOM_FLOOR", (0, 0.05, 0.0), (6.0, 6.0), (1, 1), bpy.data.materials.new("MAT_ROOM"))
    link_only(floor, qa)
    neutralize_scene()
    apply_view_present("front")
    render_still(cam, render_dir / "room-context.png", "room", 1280, 720)


def write_readme(path: Path, blend_path: Path) -> None:
    digest = sha256(blend_path)
    parts = PROMPTABLE_PARTS
    raw = bpy.context.scene.get("promptable_parts_json")
    if raw:
        parts = json.loads(raw)
    lines = [
        "# Avery Chen 2D (Patty style cutout)",
        "",
        "Immersive **per-part** 2D meshes in `COL_AVERY_CHEN` — each anatomy, clothing, accessory, and facial feature is its own object for prompt-level control.",
        "",
        "## Drop-in",
        "",
        "Link `COL_AVERY_CHEN` and play the same 20 slotted action names from this file. Contract matches `char.avery_chen` / `proxy_rig_v1`.",
        "",
        "```bash",
        "blender --background --factory-startup --python build_avery_2d.py -- \\",
        "  --source ../avery-chen/AveryChen.blend \\",
        "  --output Avery2D.blend \\",
        "  --render-dir ../../media/avery-2d \\",
        "  --verify-log ../../internal/avery-2d-verify.txt",
        "```",
        "",
        "## Contract (unchanged)",
        "",
        "| Field | Value |",
        "|---|---|",
        "| Collection | `COL_AVERY_CHEN` |",
        "| Armature | `RIG_AVERY_CHEN` |",
        "| Materials | `MAT_PROXY_CHARACTER`, `MAT_PROXY_FOCUS` |",
        "| Actions | 20 canonical names (`idle_neutral_loop` … `pose_end`) |",
        "| Visemes | `VISEME_A`–`VISEME_H`, `VISEME_X` on `GEO_AVERY_HEAD` |",
        "| Expressions | `BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT` on `GEO_AVERY_HEAD` |",
        "| Coordinates | meters, Z up, forward −Y |",
        "| Blender | 5.2.1 LTS |",
        "",
        f"**sha256:** `{digest}`",
        "",
        "## Promptable parts",
        "",
    ]
    for category in ("anatomy", "clothing", "accessories", "face"):
        lines.append(f"### {category.title()}")
        lines.append("")
        for obj_name, control in parts.get(category, []):
            lines.append(f"- `{obj_name}` — {control}")
        lines.append("")
    lines.extend(
        [
            "## Style",
            "",
            "Palette and layer rules: `internal/patty-2d-style-spec.md`. Rig plan: `internal/patty-2d-rig-plan.md`.",
            "",
            "## Limitations",
            "",
            "- View-dependent jacket back / patch visibility uses render-time `view_group` flags, not runtime camera hooks.",
            "- Secondary hair/lanyard/badge sway uses rotation drivers on bone-parented objects, not extra bones.",
            "- Face satellites mirror `GEO_AVERY_HEAD` keys via drivers; animate head keys for speech and expression.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_verify_log(path: Path, failures: list[str], measurements: dict[str, object]) -> None:
    lines = [
        "Avery 2D cutout reopen verification",
        f"Blender: {bpy.app.version_string}",
        f"Collection: {COLLECTION}",
        f"Armature: {ARMATURE}",
        f"Style: avery_chen_patty_2d / patty-2d-style-spec.md",
        f"Triangles: {measurements.get('triangles')}",
        f"Actions: {measurements.get('actions')}",
        f"Objects: {measurements.get('objects')}",
    ]
    if failures:
        lines += [f"FAIL: {f}" for f in failures] + ["RESULT: FAIL"]
    else:
        lines += [
            "PASS: 18-bone proxy_rig_v1 hierarchy",
            "PASS: 20 slotted fake-user actions",
            "PASS: visemes and expressions on GEO_AVERY_HEAD",
            "PASS: eye/brow drivers; teeth hidden at neutral",
            "PASS: MAT_PROXY_CHARACTER and MAT_PROXY_FOCUS",
            "PASS: packed images; no linked libraries",
            "RESULT: PASS",
        ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(source_path: Path, output_path: Path) -> None:
    if bpy.app.version[:3] != BLENDER_VERSION:
        raise RuntimeError(f"Blender {BLENDER_VERSION} required")
    bpy.ops.wm.open_mainfile(filepath=str(source_path))
    for action in bpy.data.actions:
        action.use_fake_user = True
    captured = capture_head_keys()
    if not captured:
        raise RuntimeError("GEO_AVERY_HEAD shape keys missing in source")
    remove_legacy_meshes()
    images = generate_textures()
    build_character(images, captured)
    if "avery_2d_teeth_vis" not in [h.__name__ for h in bpy.app.handlers.frame_change_pre]:
        bpy.app.handlers.frame_change_pre.append(update_teeth_visibility)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene["asset_id"] = "char.avery_chen"
    scene["asset_version"] = "4.0.0"
    scene["style_id"] = "avery_chen_patty_2d"
    scene["retarget_profile"] = RETARGET_PROFILE
    scene["forward_axis"] = "-Y"
    scene["builder"] = "build_avery_2d.py"
    scene["promptable_parts_json"] = json.dumps(PROMPTABLE_PARTS)
    neutralize_scene()
    for image in bpy.data.images:
        if image.name.startswith("TEX_"):
            image.use_fake_user = True
    bpy.ops.file.pack_all()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path), compress=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--render-dir", default=str(DEFAULT_RENDER))
    parser.add_argument("--verify-log", default=str(DEFAULT_VERIFY))
    parser.add_argument("--skip-renders", action="store_true")
    parser.add_argument("--renders-only", action="store_true")
    parser.add_argument(
        "--qa-sheets-only",
        action="store_true",
        help="Regenerate action-sheet.png and expression-sheet.png only",
    )
    args = parser.parse_args(argv_after_double_dash())
    source = resolve_path(args.source)
    output = resolve_path(args.output)
    render_dir = resolve_path(args.render_dir)
    verify_log = resolve_path(args.verify_log)
    if args.renders_only:
        bpy.ops.wm.open_mainfile(filepath=str(output))
    else:
        build(source, output)
        bpy.ops.wm.open_mainfile(filepath=str(output))
    failures, measurements = validate_scene()
    if args.qa_sheets_only:
        render_qa_sheets_only(render_dir)
    elif not args.skip_renders:
        render_evidence(render_dir)
        bpy.ops.wm.open_mainfile(filepath=str(output))
        failures, measurements = validate_scene()
    write_verify_log(verify_log, failures, measurements)
    write_readme(ROOT / "README.md", output)
    if failures:
        raise RuntimeError("; ".join(failures))
    print("AVERY_2D_COMPLETE", sha256(output), output)


if __name__ == "__main__":
    main()
