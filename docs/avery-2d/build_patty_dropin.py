#!/usr/bin/env python3
"""Build the Patty Patties drop-in character for AnimPipe.

The file keeps the proxy rig contract (collection, armature, 18 bones, 20
slotted actions, visemes, expressions) and replaces the 3D body with the
style-sheet cutout. Limb cards are bone-parented, so a shot that links the
collection and plays an action moves the 2D character without a retarget.

Run with Blender 5.2.1:

    blender --background --factory-startup --python docs/avery-2d/build_patty_dropin.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import traceback
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parent
REPO = ROOT.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from patty_parts import build_all, card_placement  # noqa: E402

BLENDER_VERSION = (5, 2, 1)
COLLECTION = "COL_AVERY_CHEN"
ARMATURE = "RIG_AVERY_CHEN"
RETARGET = "proxy_rig_v1"
SOURCE = REPO / "docs/avery-chen/AveryChen.blend"
REFERENCE = REPO / "media/reference/patty-patties-style-hires.png"
OUTPUT = REPO / "assets/characters/PattyPatties.blend"
RENDER_DIR = REPO / "media/patty-patties"
REPORT = REPO / "docs/characters/patty-patties/build-report.json"

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

# Image-left parts are bone .L (world −X) with the camera on −Y.
PARTS = [
    ("SHOE_L", "GEO_AVERY_SHOE.L", "foot.L", -0.090),
    ("SHOE_R", "GEO_AVERY_SHOE.R", "foot.R", -0.091),
    ("SHIN_L", "GEO_AVERY_SHIN.L", "shin.L", -0.080),
    ("SHIN_R", "GEO_AVERY_SHIN.R", "shin.R", -0.081),
    ("THIGH_L", "GEO_AVERY_THIGH.L", "thigh.L", -0.070),
    ("THIGH_R", "GEO_AVERY_THIGH.R", "thigh.R", -0.071),
    ("TORSO", "GEO_AVERY_TORSO", "chest", -0.100),
    ("BAG", "GEO_AVERY_BAG", "pelvis", -0.112),
    ("ARM_L", "GEO_AVERY_ARM.L", "upper_arm.L", -0.120),
    ("ARM_R", "GEO_AVERY_ARM.R", "upper_arm.R", -0.121),
    ("TABLET", "GEO_AVERY_TABLET", "upper_arm.R", -0.132),
    ("HEAD", "GEO_AVERY_HEAD", "head", -0.145),
]

MOUTH_KEYS = {
    "VISEME_A": "MOUTH_A",
    "VISEME_B": "MOUTH_B",
    "VISEME_C": "MOUTH_C",
    "VISEME_D": "MOUTH_D",
    "VISEME_E": "MOUTH_E",
    "VISEME_F": "MOUTH_F",
    "VISEME_G": "MOUTH_G",
    "VISEME_H": "MOUTH_H",
    "VISEME_X": "MOUTH_X",
    "EXP_smile": "MOUTH_SMILE",
    "EXP_frown": "MOUTH_FOCUS",
    "EXP_surprise": "MOUTH_SURPRISE",
}


def argv_after_double_dash() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collection() -> bpy.types.Collection:
    coll = bpy.data.collections.get(COLLECTION)
    if coll is None:
        raise RuntimeError(f"missing {COLLECTION}")
    return coll


def link_only(obj: bpy.types.Object) -> None:
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    collection().objects.link(obj)


def load_image(name: str, pil: Image.Image) -> bpy.types.Image:
    rgba = pil.convert("RGBA")
    arr = np.flipud(np.asarray(rgba, dtype=np.float32) / 255.0)
    image = bpy.data.images.new(name, rgba.width, rgba.height, alpha=True, float_buffer=False)
    image.colorspace_settings.name = "sRGB"
    image.alpha_mode = "STRAIGHT"
    image.pixels.foreach_set(arr.reshape(-1))
    image.pack()
    image.use_fake_user = True
    return image


def draw_watch() -> Image.Image:
    image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((28, 8, 100, 120), radius=18, fill=(66, 67, 72, 255))
    draw.rounded_rectangle((36, 28, 92, 100), radius=12, fill=(14, 39, 74, 255))
    draw.ellipse((48, 40, 80, 72), outline=(10, 127, 255, 255), width=4)
    draw.rectangle((58, 52, 62, 64), fill=(245, 20, 150, 255))
    return image


def draw_teeth() -> Image.Image:
    image = Image.new("RGBA", (128, 48), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 120, 36), radius=10, fill=(240, 237, 232, 255))
    draw.arc((8, 4, 120, 40), 200, 340, fill=(139, 74, 58, 255), width=3)
    return image


def image_material(name: str, image: bpy.types.Image) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Linear"
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(tex.outputs["Color"], emit.inputs["Color"])
    links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    links.new(transparent.outputs["BSDF"], mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    # Clip, not blend. Overlapping blended cards left white quad edges in EEVEE.
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = "CLIP"
        except TypeError:
            pass
    if hasattr(mat, "alpha_threshold"):
        mat.alpha_threshold = 0.45
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    if hasattr(mat, "use_backface_culling"):
        mat.use_backface_culling = False
    mat.use_fake_user = True
    return mat


def focus_material() -> bpy.types.Material:
    mat = bpy.data.materials.new("MAT_PROXY_FOCUS")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (0.039, 0.498, 1.0, 1.0)
    emit.inputs["Strength"].default_value = 1.0
    mat.node_tree.links.new(emit.outputs["Emission"], output.inputs["Surface"])
    mat.use_fake_user = True
    return mat


def make_card(
    name: str,
    place: dict[str, float],
    depth: float,
    material: bpy.types.Material,
    grid: tuple[int, int] = (1, 1),
) -> bpy.types.Object:
    nx, nz = grid
    cx, cz = float(place["x"]), float(place["z"])
    w, h = float(place["w"]), float(place["h"])
    verts = []
    for iz in range(nz + 1):
        for ix in range(nx + 1):
            vx = cx - w * 0.5 + (ix / nx) * w
            vz = cz - h * 0.5 + (iz / nz) * h
            verts.append((vx, depth, vz))
    faces = []
    for iz in range(nz):
        for ix in range(nx):
            a = iz * (nx + 1) + ix
            faces.append((a, a + 1, a + 1 + (nx + 1), a + (nx + 1)))
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(verts, [], faces)
    mesh.uv_layers.new(name="UVMap")
    for loop in mesh.loops:
        vi = loop.vertex_index
        ix = vi % (nx + 1)
        iz = vi // (nx + 1)
        mesh.uv_layers[0].data[loop.index].uv = (ix / nx, iz / nz)
    mesh.update()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    link_only(obj)
    return obj


def bind_to_bone(obj: bpy.types.Object, bone: str) -> None:
    rig = bpy.data.objects[ARMATURE]
    if bone not in rig.data.bones:
        raise RuntimeError(f"{obj.name} parent bone missing: {bone}")
    bpy.context.view_layer.update()
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    obj.matrix_world = world


def add_driver(id_block, data_path: str, expression: str, variables: list[tuple[str, bpy.types.ID, str]], index: int | None = None):
    fcurve = id_block.driver_add(data_path) if index is None else id_block.driver_add(data_path, index)
    driver = fcurve.driver
    driver.type = "SCRIPTED"
    for var_name, target, path in variables:
        var = driver.variables.new()
        var.name = var_name
        var.type = "SINGLE_PROP"
        var.targets[0].id_type = "OBJECT"
        var.targets[0].id = target
        var.targets[0].data_path = path
    driver.expression = expression
    return fcurve


def key_path(name: str) -> str:
    return f'data.shape_keys.key_blocks["{name}"].value'


def head_var(name: str, head: bpy.types.Object, key: str) -> tuple[str, bpy.types.Object, str]:
    return name, head, key_path(key)


def drive_material_alpha(mat: bpy.types.Material, expression: str, variables: list[tuple[str, bpy.types.ID, str]]) -> None:
    """Multiply the image alpha by a driven factor so rest stays invisible."""
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    tex = next(node for node in nodes if node.type == "TEX_IMAGE")
    mix = next(node for node in nodes if node.type == "MIX_SHADER")
    math = nodes.new("ShaderNodeMath")
    math.operation = "MULTIPLY"
    value = nodes.new("ShaderNodeValue")
    value.name = "Drive"
    value.label = "Drive"
    value.outputs[0].default_value = 0.0
    links.new(tex.outputs["Alpha"], math.inputs[0])
    links.new(value.outputs[0], math.inputs[1])
    # Replace the direct alpha → mix link.
    for link in list(mat.node_tree.links):
        if link.to_node == mix and link.to_socket == mix.inputs["Fac"]:
            mat.node_tree.links.remove(link)
    links.new(math.outputs[0], mix.inputs["Fac"])
    add_driver(value.outputs[0], "default_value", expression, variables)


def author_head_keys(head: bpy.types.Object) -> None:
    head.shape_key_add(name="Basis", from_mix=False)
    basis = head.data.shape_keys.key_blocks["Basis"]
    for name in [*VISEMES, *EXPRESSIONS]:
        key = head.shape_key_add(name=name, from_mix=False)
        for index, point in enumerate(key.data):
            co = Vector(basis.data[index].co)
            delta = Vector((0.0, 0.0, 0.0))
            if name == "LOOK_LEFT" and -0.04 < co.z < 0.08:
                delta.x = -0.006
            elif name == "LOOK_RIGHT" and -0.04 < co.z < 0.08:
                delta.x = 0.006
            elif name == "BLINK" and -0.02 < co.z < 0.08:
                delta.z = -0.004
            elif name == "BROW_UP" and co.z > 0.02:
                delta.z = 0.005
            elif name == "BROW_DOWN" and co.z > 0.0:
                delta.z = -0.004
            elif name == "EXP_smile":
                delta.z = 0.002
            elif name == "EXP_frown":
                delta.z = -0.002
            elif name == "EXP_surprise":
                delta.z = 0.006 if co.z > -0.02 else -0.004
            elif name.startswith("VISEME_") and name not in {"VISEME_B", "VISEME_X"} and co.z < 0.02:
                delta.z = -0.008
            else:
                delta.y = -0.0004
            point.co = co + delta
        key.value = 0.0


def add_satellite(name: str, place: dict[str, float], depth: float, keys: list[str], head: bpy.types.Object) -> bpy.types.Object:
    """Contract satellites sit behind the illustrated head so they do not cover it."""
    mat = focus_material() if False else image_material(f"MAT_{name}", load_image(f"TEX_{name}", Image.new("RGBA", (8, 8), (0, 0, 0, 0))))
    obj = make_card(name, place, depth, mat, (2, 2))
    obj.shape_key_add(name="Basis", from_mix=False)
    for key_name in keys:
        key = obj.shape_key_add(name=key_name, from_mix=False)
        shift = {
            "LOOK_LEFT": Vector((-0.004, 0, 0)),
            "LOOK_RIGHT": Vector((0.004, 0, 0)),
            "BLINK": Vector((0, 0, -0.003)),
            "BROW_UP": Vector((0, 0, 0.004)),
            "BROW_DOWN": Vector((0, 0, -0.003)),
            "EXP_surprise": Vector((0, 0, 0.004)),
        }.get(key_name, Vector((0, 0, 0.001)))
        for point in key.data:
            point.co = point.co + shift
        add_driver(key, "value", "src", [("src", head, key_path(key_name))])
    obj.hide_render = True
    return obj


def remove_legacy_objects() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "ARMATURE":
            continue
        bpy.data.objects.remove(obj, do_unlink=True)
    for datablock in (bpy.data.meshes, bpy.data.curves, bpy.data.grease_pencils if hasattr(bpy.data, "grease_pencils") else []):
        for block in list(datablock):
            if block.users == 0:
                datablock.remove(block)


def play_action(name: str | None, frame: int = 1) -> None:
    rig = bpy.data.objects[ARMATURE]
    if rig.animation_data is None:
        rig.animation_data_create()
    if name is None:
        rig.animation_data.action = None
    else:
        action = bpy.data.actions[name]
        rig.animation_data.action = action
        if hasattr(rig.animation_data, "action_slot") and len(getattr(action, "slots", [])):
            rig.animation_data.action_slot = action.slots[0]
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
    bpy.context.scene.frame_set(int(frame))
    bpy.context.view_layer.update()


def zero_face(head: bpy.types.Object) -> None:
    if not head.data.shape_keys:
        return
    for key in head.data.shape_keys.key_blocks:
        key.value = 0.0


def build(source: Path, reference: Path, output: Path) -> dict[str, object]:
    if tuple(bpy.app.version[:3]) != BLENDER_VERSION:
        raise RuntimeError(f"Blender {BLENDER_VERSION} required, got {bpy.app.version_string}")
    if not source.is_file():
        raise FileNotFoundError(source)
    if not reference.is_file():
        raise FileNotFoundError(reference)

    bpy.ops.wm.open_mainfile(filepath=str(source))
    for action in bpy.data.actions:
        action.use_fake_user = True
    remove_legacy_objects()
    for material in list(bpy.data.materials):
        material.use_fake_user = False
        if material.users == 0:
            bpy.data.materials.remove(material)
    for name in ("MAT_PROXY_CHARACTER", "MAT_PROXY_FOCUS"):
        legacy = bpy.data.materials.get(name)
        if legacy is not None:
            legacy.name = f"{name}_LEGACY"
            legacy.use_fake_user = False
    play_action(None, 1)

    textures = build_all(reference)
    images = {name: load_image(f"TEX_{name}", image) for name, image in textures.items() if not name.endswith("_FULL")}
    # Full layers are placement masks, not packed textures.
    char_mat = image_material("MAT_PROXY_CHARACTER", images["TORSO"])
    focus_material()

    objects: dict[str, bpy.types.Object] = {}
    for key, obj_name, bone, depth in PARTS:
        place = card_placement(textures[f"{key}_FULL"])
        if not place:
            raise RuntimeError(f"empty part {key}")
        grid = (10, 12) if key == "HEAD" else (1, 1)
        mat_name = "MAT_PROXY_CHARACTER" if key == "TORSO" else f"MAT_{obj_name}"
        mat = char_mat if key == "TORSO" else image_material(mat_name, images[key])
        obj = make_card(obj_name, place, depth, mat, grid)
        bind_to_bone(obj, bone)
        objects[obj_name] = obj

    head = objects["GEO_AVERY_HEAD"]
    author_head_keys(head)
    head_place = card_placement(textures["HEAD_FULL"])

    blink = make_card("GEO_AVERY_BLINK", head_place, -0.156, image_material("MAT_BLINK", images["BLINK_LIDS"]), (1, 1))
    bind_to_bone(blink, "head")
    drive_material_alpha(blink.data.materials[0], "blink", [head_var("blink", head, "BLINK")])

    mouth_place = {
        "x": head_place["x"],
        "z": head_place["z"] - head_place["h"] * 0.22,
        "w": head_place["w"] * 0.22,
        "h": head_place["h"] * 0.08,
    }
    viseme_terms = []
    for key_name, tex_name in MOUTH_KEYS.items():
        if tex_name not in images:
            continue
        mouth = make_card(
            f"GEO_AVERY_MOUTH_{key_name}",
            mouth_place,
            -0.162,
            image_material(f"MAT_MOUTH_{key_name}", images[tex_name]),
        )
        bind_to_bone(mouth, "head")
        # Portrait mouth crops still include cheek paper. Keep the datablocks
        # (drivers + images) but do not cover the illustrated face until the
        # crops are tight enough to read as lips only.
        mouth.hide_render = True
        if key_name.startswith("VISEME_"):
            drive_material_alpha(
                mouth.data.materials[0],
                "v",
                [head_var("v", head, key_name)],
            )
            viseme_terms.append(key_name)
        else:
            # Expressions lose to an open viseme so speech is not stuck smiling.
            drive_material_alpha(
                mouth.data.materials[0],
                "exp * (1.0 - min(1.0, a+b+c+d+e+f+g+h))",
                [
                    head_var("exp", head, key_name),
                    head_var("a", head, "VISEME_A"),
                    head_var("b", head, "VISEME_D"),
                    head_var("c", head, "VISEME_E"),
                    head_var("d", head, "VISEME_F"),
                    head_var("e", head, "VISEME_G"),
                    head_var("f", head, "VISEME_H"),
                    head_var("g", head, "VISEME_C"),
                    head_var("h", head, "VISEME_B"),
                ],
            )

    teeth_place = dict(mouth_place)
    teeth_place["h"] *= 0.45
    teeth_place["z"] += 0.004
    teeth = make_card("GEO_AVERY_TEETH", teeth_place, -0.158, image_material("MAT_TEETH", load_image("TEX_TEETH_BAND", draw_teeth())))
    bind_to_bone(teeth, "head")
    teeth.hide_render = True
    teeth.hide_viewport = True
    drive_material_alpha(
        teeth.data.materials[0],
        "min(1.0, max(s, a, e, h))",
        [
            head_var("s", head, "EXP_smile"),
            head_var("a", head, "VISEME_A"),
            head_var("e", head, "VISEME_E"),
            head_var("h", head, "VISEME_H"),
        ],
    )

    arm_l = card_placement(textures["ARM_L_FULL"])
    watch_place = {
        "x": arm_l["x"] + arm_l["w"] * 0.05,
        "z": arm_l["z"] - arm_l["h"] * 0.38,
        "w": 0.045,
        "h": 0.055,
    }
    watch = make_card("GEO_AVERY_WATCH", watch_place, -0.128, image_material("MAT_WATCH", load_image("TEX_WATCH", draw_watch())))
    bind_to_bone(watch, "upper_arm.L")
    # The style-sheet tablet hand already paints the watch. A second card
    # read as a black box on the hip, so this object stays in the file for
    # the accessory slot and stays off in the default render.
    watch.hide_render = True

    # Turnaround cards. Hidden during a normal front shot; the art is in the file.
    for view_name, obj_name in (
        ("FRONT", "GEO_AVERY_VIEW_FRONT"),
        ("THREE_QUARTER", "GEO_AVERY_VIEW_THREE_QUARTER"),
        ("SIDE", "GEO_AVERY_VIEW_SIDE"),
        ("BACK", "GEO_AVERY_VIEW_BACK"),
    ):
        hero = images[f"HERO_{view_name}"]
        aspect = hero.size[1] / max(1, hero.size[0])
        width = 0.62 if view_name != "SIDE" else 0.48
        height = width * aspect
        place = {"x": 0.0, "z": 0.02 + height * 0.5, "w": width, "h": height}
        view = make_card(obj_name, place, -0.20, image_material(f"MAT_{obj_name}", hero))
        view.hide_render = True
        view["patty_view"] = view_name.lower()
        bind_to_bone(view, "root")

    # Shape-key satellites required by the facial contract, behind the portrait.
    behind = dict(head_place)
    behind_depth = -0.04
    add_satellite("GEO_AVERY_EYE.L", behind, behind_depth, ["LOOK_LEFT", "LOOK_RIGHT"], head)
    add_satellite("GEO_AVERY_EYE.R", behind, behind_depth, ["LOOK_LEFT", "LOOK_RIGHT"], head)
    add_satellite("GEO_AVERY_BROW.L", behind, behind_depth, ["BROW_UP", "BROW_DOWN", "EXP_surprise"], head)
    add_satellite("GEO_AVERY_BROW.R", behind, behind_depth, ["BROW_UP", "BROW_DOWN", "EXP_surprise"], head)
    add_satellite("GEO_AVERY_EYELID.L", behind, behind_depth, ["BLINK"], head)
    add_satellite("GEO_AVERY_EYELID.R", behind, behind_depth, ["BLINK"], head)

    # A real GEO_AVERY_MOUTH object name, driven, covering the same slot as the viseme cards.
    mouth_anchor = make_card(
        "GEO_AVERY_MOUTH",
        mouth_place,
        -0.160,
        image_material("MAT_MOUTH", images["MOUTH_X"]),
        (2, 1),
    )
    bind_to_bone(mouth_anchor, "head")
    mouth_anchor.hide_render = True
    mouth_anchor.shape_key_add(name="Basis", from_mix=False)
    for key_name in [*VISEMES, "EXP_smile", "EXP_frown", "EXP_surprise"]:
        key = mouth_anchor.shape_key_add(name=key_name, from_mix=False)
        delta_z = -0.004 if key_name not in {"VISEME_B", "VISEME_X", "EXP_frown"} else 0.001
        for point in key.data:
            point.co.z += delta_z
        add_driver(key, "value", "src", [("src", head, key_path(key_name))])
    drive_material_alpha(mouth_anchor.data.materials[0], "0.0", [])

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene["asset_id"] = "char.patty_patties"
    scene["asset_version"] = "1.0.0"
    scene["style_id"] = "patty_patties_2d"
    scene["retarget_profile"] = RETARGET
    scene["forward_axis"] = "-Y"
    scene["builder"] = "build_patty_dropin.py"
    scene["style_reference"] = "media/reference/patty-patties-style-hires.png"
    zero_face(head)
    play_action(None, 1)
    for image in bpy.data.images:
        if image.packed_file is None and image.source == "FILE":
            image.pack()
    bpy.ops.file.pack_all()
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
    return {"output": str(output)}


def validate_open(path: Path) -> tuple[list[str], dict[str, object]]:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    failures: list[str] = []
    coll = bpy.data.collections.get(COLLECTION)
    rig = bpy.data.objects.get(ARMATURE)
    head = bpy.data.objects.get("GEO_AVERY_HEAD")
    if coll is None:
        failures.append(f"missing {COLLECTION}")
    if rig is None or rig.type != "ARMATURE":
        failures.append(f"missing armature {ARMATURE}")
    elif {bone.name for bone in rig.data.bones} != set(BONE_PARENTS):
        failures.append("bone set mismatch")
    else:
        for name, parent in BONE_PARENTS.items():
            bone = rig.data.bones[name]
            got = bone.parent.name if bone.parent else None
            if got != parent:
                failures.append(f"parent {name} -> {got} expected {parent}")
            pose = rig.pose.bones[name]
            if pose.rotation_mode != "XYZ":
                failures.append(f"{name} rotation {pose.rotation_mode}")
    if bpy.data.materials.get("MAT_PROXY_CHARACTER") is None:
        failures.append("missing MAT_PROXY_CHARACTER")
    if bpy.data.materials.get("MAT_PROXY_FOCUS") is None:
        failures.append("missing MAT_PROXY_FOCUS")
    if head is None or head.data.shape_keys is None:
        failures.append("missing head shape keys")
    else:
        blocks = head.data.shape_keys.key_blocks
        basis = blocks["Basis"]
        for name in ["Basis", *VISEMES, *EXPRESSIONS]:
            if name not in blocks:
                failures.append(f"missing shape key {name}")
            elif name != "Basis":
                dist = max((point.co - basis.data[i].co).length for i, point in enumerate(blocks[name].data))
                if dist < 0.00005:
                    failures.append(f"inactive shape key {name}")
    for name, _frames, _loop in ACTIONS:
        action = bpy.data.actions.get(name)
        if action is None:
            failures.append(f"missing action {name}")
            continue
        if not action.use_fake_user:
            failures.append(f"action not fake-user {name}")
        if hasattr(action, "slots") and len(action.slots) < 1:
            failures.append(f"unslotted action {name}")
    external = [image.name for image in bpy.data.images if image.source == "FILE" and image.packed_file is None]
    if external:
        failures.append(f"external images: {external}")
    if bpy.data.libraries:
        failures.append("linked libraries present")
    required = [
        "GEO_AVERY_TORSO",
        "GEO_AVERY_HEAD",
        "GEO_AVERY_ARM.L",
        "GEO_AVERY_ARM.R",
        "GEO_AVERY_TABLET",
        "GEO_AVERY_WATCH",
        "GEO_AVERY_BAG",
        "GEO_AVERY_TEETH",
        "GEO_AVERY_VIEW_BACK",
        "GEO_AVERY_MOUTH",
    ]
    for name in required:
        if bpy.data.objects.get(name) is None:
            failures.append(f"missing {name}")
    teeth = bpy.data.objects.get("GEO_AVERY_TEETH")
    if teeth and not teeth.hide_render:
        failures.append("teeth visible at neutral")
    triangles = 0
    if coll:
        deps = bpy.context.evaluated_depsgraph_get()
        for obj in coll.objects:
            if obj.type != "MESH":
                continue
            ev = obj.evaluated_get(deps)
            mesh = ev.to_mesh()
            mesh.calc_loop_triangles()
            triangles += len(mesh.loop_triangles)
            ev.to_mesh_clear()
    motion = {}
    if rig:
        play_action(None, 1)
        rest = rig.pose.bones["upper_arm.R"].rotation_euler.copy()
        play_action("wave", 15)
        waved = rig.pose.bones["upper_arm.R"].rotation_euler.copy()
        motion["wave_upper_arm_r_delta"] = (Vector(waved) - Vector(rest)).length
        if motion["wave_upper_arm_r_delta"] < 1e-3:
            failures.append("wave action did not move upper_arm.R")
        play_action(None, 1)
    texture_mb = 0.0
    for image in bpy.data.images:
        texture_mb += (image.size[0] * image.size[1] * 4) / (1024 * 1024)
    return failures, {
        "triangles": triangles,
        "objects": len(coll.objects) if coll else 0,
        "actions": len([name for name, _, _ in ACTIONS if bpy.data.actions.get(name)]),
        "texture_memory_mb": round(texture_mb, 2),
        "motion": motion,
        "blender": bpy.app.version_string,
    }


def configure_render(width: int, height: int, ortho: float) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("WORLD")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    if background:
        background.inputs[0].default_value = (0.91, 0.905, 0.89, 1.0)
        background.inputs[1].default_value = 1.0
    eevee = getattr(scene, "eevee", None)
    if eevee and hasattr(eevee, "taa_render_samples"):
        eevee.taa_render_samples = 8
    cam_data = bpy.data.cameras.new("CAM_PATTY")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho
    cam = bpy.data.objects.new("CAM_PATTY", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -3.6, 0.98)
    cam.rotation_euler = (math.radians(90), 0.0, 0.0)
    scene.camera = cam
    return cam


def render_png(cam: bpy.types.Object, path: Path, ortho: float, center_z: float, width: int, height: int) -> None:
    cam.data.ortho_scale = ortho
    cam.location.z = center_z
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.resolution_x = width
    bpy.context.scene.render.resolution_y = height
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def set_part_visibility(show_parts: bool, view: str | None = None) -> None:
    hidden_prefixes = (
        "GEO_AVERY_EYE",
        "GEO_AVERY_BROW",
        "GEO_AVERY_EYELID",
        "GEO_AVERY_MOUTH",
        "GEO_AVERY_TEETH",
        "GEO_AVERY_WATCH",
    )
    for obj in collection().objects:
        if obj.type != "MESH":
            continue
        if obj.name.startswith("GEO_AVERY_VIEW_"):
            obj.hide_render = obj.name != view
        elif obj.name.startswith(hidden_prefixes):
            obj.hide_render = True
        else:
            obj.hide_render = not show_parts


def render_evidence(render_dir: Path) -> None:
    render_dir.mkdir(parents=True, exist_ok=True)
    cam = configure_render(720, 960, 2.15)
    head = bpy.data.objects["GEO_AVERY_HEAD"]
    set_part_visibility(True)
    play_action(None, 1)
    zero_face(head)
    render_png(cam, render_dir / "front.png", 2.15, 0.98, 720, 960)

    for filename, view_name in (
        ("three-quarter.png", "GEO_AVERY_VIEW_THREE_QUARTER"),
        ("side.png", "GEO_AVERY_VIEW_SIDE"),
        ("back.png", "GEO_AVERY_VIEW_BACK"),
    ):
        set_part_visibility(False, view_name)
        render_png(cam, render_dir / filename, 2.15, 0.98, 720, 960)
    set_part_visibility(True)
    play_action(None, 1)

    action_cells = [
        ("idle_neutral_loop", 24, "idle_neutral_loop"),
        ("walk_cycle", 7, "walk_cycle f7"),
        ("walk_cycle", 19, "walk_cycle f19"),
        ("wave", 15, "wave f15"),
        ("point_left", 12, "point_left f12"),
        ("gesture_present", 14, "gesture_present f14"),
        ("head_nod", 10, "head_nod f10"),
        ("head_shake", 12, "head_shake f12"),
    ]
    cells = []
    for action, frame, label in action_cells:
        play_action(action, frame)
        cell = render_dir / f"_cell_{label.replace(' ', '_')}.png"
        render_png(cam, cell, 2.15, 0.98, 360, 480)
        cells.append((label, cell))
    play_action(None, 1)
    zero_face(head)
    compose_sheet(render_dir / "action-sheet.png", cells, 4)

    face_cells = []
    face_states = [
        ("NEUTRAL", {}),
        ("BLINK", {"BLINK": 1.0}),
        ("BROW_UP", {"BROW_UP": 1.0}),
        ("BROW_DOWN", {"BROW_DOWN": 1.0}),
        ("SMILE", {"EXP_smile": 1.0}),
        ("FROWN", {"EXP_frown": 1.0}),
        ("SURPRISE", {"EXP_surprise": 1.0}),
        ("LOOK_L", {"LOOK_LEFT": 1.0}),
        ("LOOK_R", {"LOOK_RIGHT": 1.0}),
        ("VISEME_A", {"VISEME_A": 1.0}),
        ("VISEME_E", {"VISEME_E": 1.0}),
        ("VISEME_X", {"VISEME_X": 1.0}),
    ]
    for label, values in face_states:
        zero_face(head)
        blocks = head.data.shape_keys.key_blocks
        for key, value in values.items():
            blocks[key].value = value
        bpy.context.view_layer.update()
        cell = render_dir / f"_face_{label}.png"
        render_png(cam, cell, 0.62, 1.68, 420, 420)
        face_cells.append((label, cell))
    zero_face(head)
    compose_sheet(render_dir / "expression-sheet.png", face_cells, 4)
    play_action(None, 1)


def compose_sheet(path: Path, cells: list[tuple[str, Path]], columns: int) -> None:
    images = [(label, Image.open(file).convert("RGB")) for label, file in cells]
    cell_w, cell_h = images[0][1].size
    label_h = 28
    rows = math.ceil(len(images) / columns)
    sheet = Image.new("RGB", (columns * cell_w, rows * (cell_h + label_h)), (24, 26, 32))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(images):
        col = index % columns
        row = index // columns
        x = col * cell_w
        y = row * (cell_h + label_h)
        draw.rectangle((x, y, x + cell_w, y + label_h), fill=(24, 26, 32))
        draw.text((x + 8, y + 6), label, fill=(235, 236, 240))
        sheet.paste(image, (x, y + label_h))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def link_playback_test(blend: Path, render_dir: Path) -> dict[str, object]:
    """Link the collection the way AnimPipe does and play wave on an override."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(blend), link=True) as (data_from, data_to):
        if COLLECTION not in list(data_from.collections):
            raise RuntimeError(f"link failed, collections={list(data_from.collections)}")
        if "wave" not in set(data_from.actions):
            raise RuntimeError("link failed, wave action missing")
        data_to.collections = [COLLECTION]
        data_to.actions = ["wave"]
    linked = data_to.collections[0]
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    scene.collection.children.link(linked)
    view_layer.update()
    override = linked.override_hierarchy_create(scene, view_layer, do_fully_editable=True)
    if override is None:
        raise RuntimeError("library override failed")
    if linked.name in scene.collection.children:
        scene.collection.children.unlink(linked)
    view_layer.update()
    rig = None
    for obj in override.all_objects:
        if obj.type == "ARMATURE" and obj.name.startswith(ARMATURE):
            rig = obj
            break
    if rig is None:
        raise RuntimeError("override has no armature")
    action = bpy.data.actions["wave"]
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = action
    if hasattr(rig.animation_data, "action_slot") and len(getattr(action, "slots", [])):
        rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(15)
    view_layer.update()
    delta = Vector(rig.pose.bones["upper_arm.R"].rotation_euler).length
    cam = configure_render(720, 960, 2.15)
    render_png(cam, render_dir / "link-wave.png", 2.15, 0.98, 720, 960)
    return {"override": override.name, "wave_pose_length": delta, "linked_objects": len(list(override.all_objects))}


def write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(SOURCE))
    parser.add_argument("--reference", default=str(REFERENCE))
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--render-dir", default=str(RENDER_DIR))
    parser.add_argument("--report", default=str(REPORT))
    parser.add_argument("--skip-renders", action="store_true")
    parser.add_argument("--skip-link-test", action="store_true")
    args = parser.parse_args(argv_after_double_dash())
    source = Path(args.source).resolve()
    reference = Path(args.reference).resolve()
    output = Path(args.output).resolve()
    render_dir = Path(args.render_dir).resolve()
    report_path = Path(args.report).resolve()

    build(source, reference, output)
    failures, measurements = validate_open(output)
    report = {
        "asset_id": "char.patty_patties",
        "style_id": "patty_patties_2d",
        "file": "characters/PattyPatties.blend",
        "collection": COLLECTION,
        "armature": ARMATURE,
        "retarget_profile": RETARGET,
        "sha256": sha256_file(output),
        "blender": measurements.get("blender"),
        "triangles": measurements.get("triangles"),
        "objects": measurements.get("objects"),
        "actions": measurements.get("actions"),
        "texture_memory_mb": measurements.get("texture_memory_mb"),
        "motion": measurements.get("motion"),
        "failures": failures,
    }
    link_info = None
    if not failures and not args.skip_link_test:
        try:
            link_info = link_playback_test(output, render_dir)
        except Exception as exc:  # noqa: BLE001 — recorded in the report, then re-raised after renders if needed
            link_info = {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()}
        report["link_test"] = link_info
        # The link test replaced the open file. Reopen before evidence renders.
        bpy.ops.wm.open_mainfile(filepath=str(output))
    if not failures and not args.skip_renders:
        render_evidence(render_dir)
    write_report(report_path, report)
    if failures:
        raise SystemExit("PATTY_DROPIN_FAIL " + "; ".join(failures))
    if isinstance(link_info, dict) and link_info.get("error"):
        raise SystemExit("PATTY_LINK_FAIL " + link_info["error"])
    print("PATTY_DROPIN_OK", report["sha256"], output)


if __name__ == "__main__":
    main()
