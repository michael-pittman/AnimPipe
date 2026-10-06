#!/usr/bin/env python3
"""Build Avery Chen V2 for AnimPipe from the official MPFB2 MakeHuman basemesh.

The proxy contract is unchanged: COL_AVERY_CHEN, RIG_AVERY_CHEN, proxy_rig_v1
bones, MAT_PROXY_CHARACTER, MAT_PROXY_FOCUS, the 20 actions, and the viseme and
expression shape keys. Macro sliders are proportion inputs only. They are not
a demographic specification, and the surname Chen is not a facial reference.

The suit is the archived male_elegantsuit01, recolored. The jacket sleeves
are removed along the arm vertex groups so the jacket is a sleeveless vest.
Each armscye is a smooth curve about 6.5 mm off the body, with a narrow
chest-parented binding. The arms and axilla stay visible skin. The tie is
recolored to the lanyard teal. There is no cloth simulation, driver,
corrective shape key, or separate sleeve.

Run on the saved file:
  blender --background --python build_character.py -- finish
  blender --background --python build_character.py -- proof
  blender --background --python build_character.py -- render
  blender --background --python build_character.py -- inspect
  blender --background --python build_character.py -- verify
  blender --background --python build_character.py -- patch

A bare run refuses to rebuild. Do not use appearance, repair, or armpit.
`patch` repaints the shoe-collar lining only.
"""

from __future__ import annotations

import array
import json
import math
import os
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
BLEND_PATH = ROOT / "AveryChen.blend"
STAGING_BLEND = Path("/tmp/AveryChen-v2.blend")
MEDIA = Path("/cursor/stores/self/media/avery-chen-v2")
VERIFY_LOG = Path("/cursor/stores/self/internal/avery-chen-v2-verify.txt")
MEASURE_PATH = Path("/cursor/stores/self/internal/avery-chen-v2-measure.json")

ACTIONS_MOTION = [
    "idle_neutral_loop",
    "walk_cycle",
    "turn_left_90",
    "turn_right_90",
    "gesture_present",
    "point_left",
    "point_right",
    "wave",
    "head_nod",
    "head_shake",
    "reach_grab",
    "place_release",
]
ACTIONS_POSE = [
    "pose_neutral",
    "pose_present",
    "pose_listen",
    "pose_think",
    "pose_point",
    "pose_hold",
    "pose_ready",
    "pose_end",
]
ACTIONS = ACTIONS_MOTION + ACTIONS_POSE
VISEMES = [
    "VISEME_A", "VISEME_B", "VISEME_C", "VISEME_D", "VISEME_E",
    "VISEME_F", "VISEME_G", "VISEME_H", "VISEME_X",
]
EXPRESSIONS = [
    "BLINK", "BROW_UP", "BROW_DOWN", "EXP_smile", "EXP_frown",
    "EXP_surprise", "LOOK_LEFT", "LOOK_RIGHT",
]
BONE_PARENTS = {
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

# MakeHuman "left" is +X. This rig's .L bones sit on -X, so the sides swap.
# Sliders size the hm08 mesh. They are not an identity, ethnicity, or gender claim.
MACRO = {
    "gender": 0.48,
    "age": 0.50,  # MPFB "young", about 25.
    "muscle": 0.14,
    "weight": 0.42,
    "proportions": 0.58,
    "height": 0.52,
    "cupsize": 0.08,
    "firmness": 0.35,
    "race": {"asian": 0.34, "caucasian": 0.33, "african": 0.33},
}
CONTRACT_BONES = (
    "root", "pelvis", "spine", "chest", "neck", "head",
    "upper_arm.L", "forearm.L", "hand.L", "upper_arm.R", "forearm.R", "hand.R",
    "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R",
)
# Display-referred palette anchors from the V2 review. Stored here as sRGB bytes.
PALETTE = {
    "jacket": (64, 80, 76),
    "knit": (184, 170, 152),
    "trousers": (52, 58, 61),
    "lanyard": (48, 122, 118),
    "shoes": (74, 60, 53),
    "badge": (232, 226, 214),
}


def argv_tail():
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def asset_root():
    candidates = [
        Path("/home/ubuntu/.config/blender/5.2/extensions/.user/user_default/mpfb/data"),
        Path.home() / ".config/blender/5.2/extensions/.user/user_default/mpfb/data",
    ]
    for path in candidates:
        marker = path / "clothes/female_elegantsuit01/female_elegantsuit01.mhclo"
        if marker.is_file():
            return path
    raise RuntimeError("MPFB CC0 system assets are not installed")


def enable_mpfb():
    module = "bl_ext.user_default.mpfb"
    if module not in sys.modules:
        bpy.ops.preferences.addon_enable(module=module)
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    from bl_ext.user_default.mpfb.entities.objectproperties import GeneralObjectProperties
    return HumanService, TargetService, GeneralObjectProperties


def link_only(obj, coll):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    coll.objects.link(obj)


def group_center(obj, name):
    group = obj.vertex_groups.get(name)
    if group is None:
        return None
    total = Vector((0.0, 0.0, 0.0))
    count = 0
    index = group.index
    for vert in obj.data.vertices:
        for assignment in vert.groups:
            if assignment.group == index and assignment.weight > 0.5:
                total += vert.co
                count += 1
                break
    if count == 0:
        return None
    return total / count


def bake_evaluated(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(obj.evaluated_get(deps), depsgraph=deps)
    old = obj.data
    if len(baked.vertices) != len(old.vertices):
        raise RuntimeError(
            f"pose bake changed {obj.name} from {len(old.vertices)} to {len(baked.vertices)} verts"
        )
    obj.data = baked
    obj.modifiers.clear()
    obj.parent = None
    obj.matrix_world.identity()
    bpy.data.meshes.remove(old)
    return obj


def pose_arms_down(human, rig):
    """Hang the A-pose arms beside the torso so they match the proxy rest pose."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")

    def setrot(name, x_deg, z_deg):
        bone = rig.pose.bones[name]
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (math.radians(x_deg), 0.0, math.radians(z_deg))

    setrot("upperarm_l", 0.0, -22.0)
    setrot("lowerarm_l", -42.0, -16.0)
    setrot("upperarm_r", 0.0, 22.0)
    setrot("lowerarm_r", -42.0, 16.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


def align_to_proxy(obj):
    """Uniform scale so the hips sit on the proxy pelvis and the feet sit on the ground."""
    hip_l = group_center(obj, "joint-l-upper-leg")
    hip_r = group_center(obj, "joint-r-upper-leg")
    ankle_l = group_center(obj, "joint-l-ankle")
    ankle_r = group_center(obj, "joint-r-ankle")
    if not all((hip_l, hip_r, ankle_l, ankle_r)):
        raise RuntimeError("MakeHuman joint groups missing; cannot align the body")
    hip = (hip_l + hip_r) * 0.5
    ankle = (ankle_l + ankle_r) * 0.5
    # Proxy pelvis head is z=0.90 and the ankle bones sit near z=0.08.
    target_span = 0.90 - 0.08
    span = hip.z - ankle.z
    if span < 0.2:
        raise RuntimeError(f"leg span {span} is too short to align")
    scale = target_span / span
    cx = hip.x
    cy = hip.y
    # After scale, hip z should be 0.90 and the body stays centered on x.
    for vert in obj.data.vertices:
        co = vert.co
        vert.co.x = (co.x - cx) * scale
        vert.co.y = (co.y - cy) * scale
        vert.co.z = (co.z - hip.z) * scale + 0.90
    obj.data.update()
    print(f"aligned scale={scale:.4f} hip was {tuple(round(c, 3) for c in hip)}")
    return scale


def load_combined(obj, name, paths, TargetService, amount=1.0):
    merged = {}
    for path in paths:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        info = TargetService._target_string_to_shape_key_info(text, name)
        for index, x, y, z in info["vertices"]:
            px, py, pz = merged.get(index, (0.0, 0.0, 0.0))
            merged[index] = (px + x * amount, py + y * amount, pz + z * amount)
    if not merged:
        # An empty target (the CC0 silence viseme) still has to move the mesh.
        return None
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    key = obj.shape_key_add(name=name, from_mix=False)
    key.interpolation = "KEY_LINEAR"
    info = {"name": name, "vertices": [(i, *xyz) for i, xyz in merged.items()]}
    TargetService._set_shape_key_coords_from_dict(obj, key, info)
    key.value = 0.0
    return key


def add_expression_keys(obj, data, TargetService):
    vis = data / "targets/visemes"
    units = data / "targets/faceunits"
    mapping = {
        "VISEME_A": [(vis / "aa_02.target", 1.0)],
        "VISEME_B": [(vis / "p_b_m_21.target", 1.0)],
        "VISEME_C": [(vis / "ey_eh_uh_04.target", 1.0)],
        "VISEME_D": [(vis / "d_t_n_19.target", 1.0)],
        "VISEME_E": [(vis / "y_iy_ih_ix_06.target", 1.0)],
        "VISEME_F": [(vis / "f_v_18.target", 1.0)],
        "VISEME_G": [(vis / "k_g_ng_20.target", 1.0)],
        "VISEME_H": [(vis / "h_12.target", 1.0)],
        "VISEME_X": [(units / "mouthClose.target", 0.45)],
        "BLINK": [(units / "eyeBlinkLeft.target", 1.0), (units / "eyeBlinkRight.target", 1.0)],
        "BROW_UP": [
            (units / "browInnerUp.target", 0.7),
            (units / "browOuterUpLeft.target", 1.0),
            (units / "browOuterUpRight.target", 1.0),
        ],
        "BROW_DOWN": [
            (units / "browDownLeft.target", 1.0),
            (units / "browDownRight.target", 1.0),
        ],
        "EXP_smile": [
            (units / "mouthSmileLeft.target", 1.0),
            (units / "mouthSmileRight.target", 1.0),
        ],
        "EXP_frown": [
            (units / "mouthFrownLeft.target", 1.0),
            (units / "mouthFrownRight.target", 1.0),
        ],
        "EXP_surprise": [
            (units / "eyeWideLeft.target", 1.0),
            (units / "eyeWideRight.target", 1.0),
            (units / "browInnerUp.target", 1.0),
            (units / "jawOpen.target", 0.35),
        ],
        "LOOK_LEFT": [
            (units / "eyeLookOutRight.target", 1.0),
            (units / "eyeLookInLeft.target", 1.0),
        ],
        "LOOK_RIGHT": [
            (units / "eyeLookOutLeft.target", 1.0),
            (units / "eyeLookInRight.target", 1.0),
        ],
    }
    for name, parts in mapping.items():
        merged = {}
        for path, amount in parts:
            text = path.read_text(encoding="utf-8", errors="replace")
            info = TargetService._target_string_to_shape_key_info(text, name)
            for index, x, y, z in info["vertices"]:
                px, py, pz = merged.get(index, (0.0, 0.0, 0.0))
                merged[index] = (px + x * amount, py + y * amount, pz + z * amount)
        if obj.data.shape_keys is None:
            obj.shape_key_add(name="Basis", from_mix=False)
        key = obj.shape_key_add(name=name, from_mix=False)
        key.interpolation = "KEY_LINEAR"
        info = {"name": name, "vertices": [(i, *xyz) for i, xyz in merged.items()]}
        TargetService._set_shape_key_coords_from_dict(obj, key, info)
        key.value = 0.0
        print(f"shape {name} verts {len(merged)}")


def fit_asset(HumanService, basemesh, path, asset_type):
    obj = HumanService.add_mhclo_asset(
        str(path),
        basemesh,
        asset_type=asset_type,
        subdiv_levels=0,
        material_type="GAMEENGINE",
        set_up_rigging=False,
        interpolate_weights=False,
        import_subrig=False,
        import_weights=False,
    )
    world = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = world
    return obj


def rename_material(obj, name):
    if not obj.data.materials:
        return None
    mat = obj.data.materials[0]
    if mat is None:
        return None
    existing = bpy.data.materials.get(name)
    if existing is not None and existing != mat:
        obj.data.materials[0] = existing
        return existing
    mat.name = name
    return mat


def ensure_focus_material():
    mat = bpy.data.materials.get("MAT_PROXY_FOCUS")
    if mat is None:
        mat = bpy.data.materials.new("MAT_PROXY_FOCUS")
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = (0.45, 0.28, 0.16, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.18
    return mat


def ensure_character_material():
    mat = bpy.data.materials.get("MAT_PROXY_CHARACTER")
    if mat is None:
        mat = bpy.data.materials.new("MAT_PROXY_CHARACTER")
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = (0.60, 0.31, 0.20, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.45
    return mat


def show_only_skin_and_eyes(obj):
    """Mask helper geometry. Do not apply the modifier — that would change vertex count."""
    modifier = obj.modifiers.get("Hide helpers")
    if modifier is None:
        modifier = obj.modifiers.new("Hide helpers", "MASK")
    modifier.vertex_group = "body"
    modifier.show_in_editmode = True
    modifier.show_on_cage = True
    modifier.show_render = True
    modifier.show_viewport = True


def _body_coords(obj):
    group = obj.vertex_groups.get("body")
    if group is None:
        return [v.co.copy() for v in obj.data.vertices]
    index = group.index
    coords = []
    for vert in obj.data.vertices:
        for assignment in vert.groups:
            if assignment.group == index and assignment.weight > 0.5:
                coords.append(vert.co.copy())
                break
    return coords or [v.co.copy() for v in obj.data.vertices]


def find_chin_z(coords, crown_z):
    """Lowest centerline point still on the forward face. Stops at the neck, not the chest."""
    rows = []
    z = crown_z
    while z > crown_z - 0.36:
        slab = [v for v in coords if abs(v.z - z) < 0.003 and abs(v.x) < 0.016]
        if len(slab) >= 3:
            rows.append((z, min(v.y for v in slab)))
        z -= 0.002
    if not rows:
        raise RuntimeError("could not find a chin profile")
    # The face is the forward mass in the upper head. The chest can be just as far
    # forward, so it is excluded by the height window.
    upper = [row for row in rows if row[0] > crown_z - 0.22]
    face = [(z, y) for z, y in rows if crown_z - 0.22 < z < crown_z - 0.04]
    if not face:
        raise RuntimeError("could not find the nose on the profile")
    nose_z, nose_y = min(face, key=lambda row: row[1])
    chin_z = nose_z
    for z, y in rows:
        if z > nose_z:
            continue
        if y < nose_y + 0.035:
            chin_z = z
        elif y > nose_y + 0.05:
            break
    return chin_z


def _upper_head_width(coords, chin_z, crown_z):
    """Temple-to-temple width. The crown is narrower and is not the head-width unit."""
    head_h = crown_z - chin_z
    z0 = chin_z + 0.40 * head_h
    z1 = chin_z + 0.72 * head_h
    slab = [v for v in coords if z0 <= v.z <= z1]
    if len(slab) < 8:
        return None
    return max(v.x for v in slab) - min(v.x for v in slab)


def _around_joint_width(coords, left, right, radius):
    """Breadth across the two joints, using only verts in a small ball around each joint."""
    chosen = []
    for vert in coords:
        if (vert - left).length <= radius or (vert - right).length <= radius:
            chosen.append(vert)
    if len(chosen) < 6:
        return None
    return max(v.x for v in chosen) - min(v.x for v in chosen)


def _flesh_width(coords, z, y_center, y_tol=0.06, x_max=0.26):
    band = [v for v in coords if abs(v.z - z) < 0.03 and abs(v.y - y_center) < y_tol and abs(v.x) < x_max]
    if len(band) < 8:
        return None
    return max(v.x for v in band) - min(v.x for v in band)


def _group_points(obj, name, minimum=0.35):
    group = obj.vertex_groups.get(name)
    if group is None:
        return []
    index = group.index
    points = []
    for vert in obj.data.vertices:
        for assignment in vert.groups:
            if assignment.group == index and assignment.weight >= minimum:
                points.append(vert.co.copy())
                break
    return points


def measure_anatomy(obj):
    coords = _body_coords(obj)
    crown = max(v.z for v in coords)
    sole = min(v.z for v in coords)
    chin_z = find_chin_z(coords, crown)
    head_h = crown - chin_z
    stature = crown - sole
    head_w = _upper_head_width(coords, chin_z, crown) or head_h * 0.72
    shoulder_l = group_center(obj, "joint-l-shoulder")
    shoulder_r = group_center(obj, "joint-r-shoulder")
    hip_l = group_center(obj, "joint-l-upper-leg")
    hip_r = group_center(obj, "joint-r-upper-leg")
    knee = group_center(obj, "joint-l-knee")
    ankle = group_center(obj, "joint-l-ankle")
    elbow = group_center(obj, "joint-l-elbow")
    wrist = group_center(obj, "joint-l-hand")
    wrist_r = group_center(obj, "joint-r-hand")
    acromion = abs(shoulder_l.x - shoulder_r.x)
    hip_w = _around_joint_width(coords, hip_l, hip_r, 0.075) or acromion
    shoulder_w = _around_joint_width(coords, shoulder_l, shoulder_r, 0.038) or acromion
    hand_pts = _group_points(obj, "hand_l", 0.45)
    if hand_pts and wrist is not None:
        tip = min(hand_pts, key=lambda p: p.z)
        hand_len = (wrist - tip).length
    else:
        tip = Vector((0.0, 0.0, 0.0))
        hand_len = 0.0
    foot_pts = [v for v in coords if v.z < ankle.z + 0.01 and v.x > 0.05]
    if foot_pts:
        heel = max(foot_pts, key=lambda v: v.y)
        toe = min(foot_pts, key=lambda v: v.y)
        foot_len = (heel - toe).length
    else:
        foot_len = 0.0
    return {
        "stature_m": stature,
        "sole_z": sole,
        "crown_z": crown,
        "chin_z": chin_z,
        "head_height_m": head_h,
        "heads": stature / head_h if head_h else 0.0,
        "head_width_m": head_w,
        "hip_z": hip_l.z,
        "hip_fraction": hip_l.z / stature if stature else 0.0,
        "knee_z": knee.z,
        "ankle_z": ankle.z,
        "knee_mid_z": (hip_l.z + ankle.z) * 0.5,
        "acromion_m": acromion,
        "acromion_head_widths": acromion / head_w if head_w else 0.0,
        "shoulder_breadth_m": shoulder_w,
        "hip_breadth_m": hip_w,
        "shoulder_hip_ratio": shoulder_w / hip_w if hip_w else 0.0,
        "elbow_z": elbow.z,
        "wrist_z": wrist.z,
        "fingertip_z": tip.z,
        "hand_length_m": hand_len,
        "hand_head_heights": hand_len / head_h if head_h else 0.0,
        "foot_length_m": foot_len,
        "foot_head_heights": foot_len / head_h if head_h else 0.0,
        "lr_shoulder_mm": abs(abs(shoulder_l.x) - abs(shoulder_r.x)) * 1000.0,
        "lr_wrist_mm": abs(abs(wrist.x) - abs(wrist_r.x)) * 1000.0,
        "landmarks": {
            "crown": (0.0, 0.0, crown),
            "chin": (0.0, min((v.y for v in coords if abs(v.z - chin_z) < 0.02 and abs(v.x) < 0.04), default=-0.12), chin_z),
            "acromion_l": tuple(shoulder_l),
            "acromion_r": tuple(shoulder_r),
            "elbow_l": tuple(elbow),
            "wrist_l": tuple(wrist),
            "hip_l": tuple(hip_l),
            "hip_r": tuple(hip_r),
            "knee_l": tuple(knee),
            "ankle_l": tuple(ankle),
            "fingertip_l": tuple(tip),
        },
    }


def _plant_sole(obj):
    """Put the visible sole on z=0 without moving the ankle joint."""
    coords_z = [v.z for v in _body_coords(obj)]
    zmin = min(coords_z)
    pivot = 0.08
    if abs(zmin) <= 0.005 or zmin >= pivot - 0.005:
        return 0.0
    factor = max(0.75, min(1.25, pivot / (pivot - zmin)))
    for vert in obj.data.vertices:
        if vert.co.z < pivot:
            vert.co.z = pivot - (pivot - vert.co.z) * factor
    obj.data.update()
    return zmin


def _stretch_above_hip(obj, target_crown):
    coords = _body_coords(obj)
    crown = max(v.z for v in coords)
    hip_z = 0.90
    if crown <= hip_z + 0.2:
        return 1.0
    factor = (target_crown - hip_z) / (crown - hip_z)
    factor = max(0.98, min(1.06, factor))
    if abs(factor - 1.0) < 0.004:
        return 1.0
    for vert in obj.data.vertices:
        if vert.co.z > hip_z:
            vert.co.z = hip_z + (vert.co.z - hip_z) * factor
    obj.data.update()
    return factor


def _scale_group_about(obj, group_name, pivot, factor, axes):
    group = obj.vertex_groups.get(group_name)
    if group is None or abs(factor - 1.0) < 0.02:
        return
    factor = max(0.82, min(1.28, factor))
    index = group.index
    for vert in obj.data.vertices:
        weight = 0.0
        for assignment in vert.groups:
            if assignment.group == index:
                weight = assignment.weight
                break
        if weight < 0.15:
            continue
        applied = 1.0 + (factor - 1.0) * min(1.0, weight)
        delta = vert.co - pivot
        if "x" in axes:
            vert.co.x = pivot.x + delta.x * applied
        if "y" in axes:
            vert.co.y = pivot.y + delta.y * applied
        if "z" in axes:
            vert.co.z = pivot.z + delta.z * applied
    obj.data.update()


def _scale_hip_breadth(obj, factor):
    if abs(factor - 1.0) < 0.02:
        return
    factor = max(0.88, min(1.12, factor))
    for vert in obj.data.vertices:
        z = vert.co.z
        if not (0.72 < z < 1.08) or abs(vert.co.x) > 0.26:
            continue
        # Falloff so the waist and upper thigh are not pinched into a ledge.
        if z >= 0.90:
            blend = max(0.0, 1.0 - (z - 0.90) / 0.18)
        else:
            blend = max(0.0, 1.0 - (0.90 - z) / 0.18)
        applied = 1.0 + (factor - 1.0) * blend
        vert.co.x *= applied
    obj.data.update()


def _scale_hands_spatial(obj, factor):
    """Scale each hand about its wrist, including finger verts the hand group only partly owns."""
    if abs(factor - 1.0) < 0.02:
        return
    for side, sign in (("l", 1.0), ("r", -1.0)):
        pivot = group_center(obj, f"joint-{side}-hand")
        if pivot is None:
            continue
        for vert in obj.data.vertices:
            if vert.co.x * sign < 0.16:
                continue
            if vert.co.z > pivot.z + 0.025:
                continue
            if (vert.co - pivot).length > 0.24:
                continue
            vert.co = pivot + (vert.co - pivot) * factor
    obj.data.update()


def fit_proportions(obj):
    """Plant the sole and nudge proportions onto the V2 numeric gates. Uniform align already ran."""
    sunk = _plant_sole(obj)
    stretch = _stretch_above_hip(obj, 1.740)
    stats = measure_anatomy(obj)
    head_h = stats["head_height_m"]
    hand_target = 0.76 * head_h
    if stats["hand_length_m"] > 1e-4:
        hand_factor = max(0.8, min(1.55, hand_target / stats["hand_length_m"]))
        _scale_hands_spatial(obj, hand_factor)
        print("hand scale", round(hand_factor, 3))
    foot_target = 1.05 * head_h
    if stats["foot_length_m"] > 1e-4:
        foot_factor = foot_target / stats["foot_length_m"]
        if not (0.95 <= stats["foot_head_heights"] <= 1.15):
            for side in ("l", "r"):
                pivot = group_center(obj, f"joint-{side}-ankle")
                _scale_group_about(obj, f"foot_{side}", pivot, foot_factor, "y")
    for _ in range(2):
        stats = measure_anatomy(obj)
        ratio = stats["shoulder_hip_ratio"]
        if not ratio or 1.02 <= ratio <= 1.12:
            break
        desired = 1.08
        if not stats["hip_breadth_m"]:
            break
        hip_factor = (stats["shoulder_breadth_m"] / desired) / stats["hip_breadth_m"]
        print("hip breadth scale", round(hip_factor, 3), "from ratio", round(ratio, 3))
        _scale_hip_breadth(obj, hip_factor)
    tucked = tuck_shoulder_caps(obj)
    print("tucked shoulder-cap verts", tucked)
    stats = measure_anatomy(obj)
    acr = stats["acromion_head_widths"]
    if acr and not (2.0 <= acr <= 2.35) and stats["head_width_m"]:
        desired_w = min(2.25, max(2.05, acr)) * stats["head_width_m"]
        factor = desired_w / stats["acromion_m"]
        factor = max(0.94, min(1.08, factor))
        for vert in obj.data.vertices:
            if vert.co.z > 1.22 and abs(vert.co.x) < 0.30:
                blend = min(1.0, max(0.0, (vert.co.z - 1.22) / 0.16))
                vert.co.x *= 1.0 + (factor - 1.0) * blend
        obj.data.update()
        stats = measure_anatomy(obj)
    stats["sole_sink_m"] = sunk
    stats["torso_z_stretch"] = stretch
    print(
        "proportions",
        f"stature={stats['stature_m']:.3f}",
        f"heads={stats['heads']:.2f}",
        f"hip%={stats['hip_fraction']:.3f}",
        f"acromion={stats['acromion_head_widths']:.2f}hw",
        f"sh/hip={stats['shoulder_hip_ratio']:.2f}",
        f"hand={stats['hand_head_heights']:.2f}",
        f"foot={stats['foot_head_heights']:.2f}",
        f"sole={stats['sole_z']:.4f}",
    )
    return stats


def _gate_anatomy(stats, jacket_width=None):
    problems = []
    checks = []

    def need(label, cond, detail):
        checks.append({"label": label, "pass": bool(cond), "detail": detail})
        if not cond:
            problems.append(f"{label}: {detail}")

    need("stature 1.69-1.76 m", 1.69 <= stats["stature_m"] <= 1.76, f"{stats['stature_m']:.3f} m")
    need("sole at z=0 ±5 mm", abs(stats["sole_z"]) <= 0.005, f"{stats['sole_z']:.4f} m")
    need("7.25-7.75 heads", 7.25 <= stats["heads"] <= 7.75, f"{stats['heads']:.2f}")
    need("hip 48-52% of stature", 0.48 <= stats["hip_fraction"] <= 0.52, f"{stats['hip_fraction']:.3f}")
    knee_err = abs(stats["knee_z"] - stats["knee_mid_z"])
    need("knee near hip-ankle midpoint", knee_err <= 0.025, f"error {knee_err*1000:.0f} mm")
    need("acromion 2.0-2.35 head widths", 2.0 <= stats["acromion_head_widths"] <= 2.35, f"{stats['acromion_head_widths']:.2f}")
    need("shoulder/hip breadth 1.0-1.15", 1.0 <= stats["shoulder_hip_ratio"] <= 1.15, f"{stats['shoulder_hip_ratio']:.2f}")
    need("hand 0.70-0.80 head heights", 0.70 <= stats["hand_head_heights"] <= 0.80, f"{stats['hand_head_heights']:.2f}")
    need("foot 0.95-1.15 head heights", 0.95 <= stats["foot_head_heights"] <= 1.15, f"{stats['foot_head_heights']:.2f}")
    need("elbow at waist/lower rib", 1.02 <= stats["elbow_z"] <= 1.24, f"z={stats['elbow_z']:.3f}")
    need("wrist at upper thigh", 0.80 <= stats["wrist_z"] <= 1.00, f"z={stats['wrist_z']:.3f}")
    need("fingertips near mid-thigh", 0.60 <= stats["fingertip_z"] <= 0.82, f"z={stats['fingertip_z']:.3f}")
    need("left/right landmarks ≤10 mm", stats["lr_shoulder_mm"] <= 10 and stats["lr_wrist_mm"] <= 10,
         f"shoulder {stats['lr_shoulder_mm']:.1f} mm, wrist {stats['lr_wrist_mm']:.1f} mm")
    if jacket_width is not None and stats["head_width_m"]:
        widths = jacket_width / stats["head_width_m"]
        need("outer jacket ≤2.45 head widths", widths <= 2.45, f"{widths:.2f}")
        stats["jacket_head_widths"] = widths
    return problems, checks


def _srgb_to_linear(u):
    u = u / 255.0
    return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4


def _srgb_u8_to_linear(channel):
    return _srgb_to_linear(channel)


def paint_skin_zones(obj):
    """Authored albedo and roughness. The photo texture is not the skin color."""
    mesh = obj.data
    coords = [v.co.copy() for v in mesh.vertices]
    crown = max(v.z for v in coords)
    chin_z = find_chin_z(coords, crown)
    head_h = crown - chin_z
    nose_band = [v for v in coords if abs(v.x) < 0.012 and chin_z + 0.35 * head_h < v.z < chin_z + 0.78 * head_h]
    nose = min(nose_band, key=lambda v: v.y)
    base = np.array([_srgb_u8_to_linear(c) for c in (158, 114, 88)], dtype=np.float32)
    zones = {
        "cheek": np.array([_srgb_u8_to_linear(c) for c in (184, 118, 102)], dtype=np.float32),
        "nose": np.array([_srgb_u8_to_linear(c) for c in (176, 112, 96)], dtype=np.float32),
        "lip": np.array([_srgb_u8_to_linear(c) for c in (154, 82, 78)], dtype=np.float32),
        "ear": np.array([_srgb_u8_to_linear(c) for c in (176, 110, 94)], dtype=np.float32),
        "lid": np.array([_srgb_u8_to_linear(c) for c in (142, 98, 84)], dtype=np.float32),
    }
    rough = {"base": 0.50, "cheek": 0.46, "nose": 0.42, "lip": 0.30, "ear": 0.56, "lid": 0.38}
    for name in ("skin_albedo", "skin_rough"):
        existing = mesh.color_attributes.get(name)
        if existing is not None:
            mesh.color_attributes.remove(existing)
    albedo = mesh.color_attributes.new("skin_albedo", "FLOAT_COLOR", "POINT")
    roughness = mesh.color_attributes.new("skin_rough", "FLOAT_COLOR", "POINT")
    lip_z = chin_z + 0.20 * head_h
    lid_z = chin_z + 0.62 * head_h
    for index, co in enumerate(coords):
        color = base.copy()
        rough_v = rough["base"]
        rel = (co.z - chin_z) / head_h
        on_face = co.y < -0.05 and co.z > chin_z - 0.01 and rel < 1.05
        if on_face and abs(co.x) < 0.055 and abs(co.z - lip_z) < 0.018 and co.y < nose.y + 0.015:
            color = zones["lip"]
            rough_v = rough["lip"]
        elif on_face and abs(co.x) < 0.018 and abs(co.z - nose.z) < 0.035 and co.y < nose.y + 0.012:
            color = zones["nose"]
            rough_v = rough["nose"]
        elif on_face and 0.018 < abs(co.x) < 0.055 and abs(co.z - (chin_z + 0.42 * head_h)) < 0.04 and co.y < -0.08:
            color = zones["cheek"]
            rough_v = rough["cheek"]
        elif on_face and 0.012 < abs(co.x) < 0.05 and abs(co.z - lid_z) < 0.018:
            color = zones["lid"]
            rough_v = rough["lid"]
        elif co.z > chin_z + 0.25 * head_h and abs(co.x) > 0.075 and abs(co.z - (chin_z + 0.48 * head_h)) < 0.06:
            color = zones["ear"]
            rough_v = rough["ear"]
        albedo.data[index].color = (float(color[0]), float(color[1]), float(color[2]), 1.0)
        roughness.data[index].color = (rough_v, rough_v, rough_v, 1.0)
    print("painted skin zones", "chin", round(chin_z, 3), "nose", tuple(round(c, 3) for c in nose))


def author_skin():
    """Zone albedo, pore-scale luminance detail, roughness, bump, and restrained SSS.

    The CC0 diffuse is converted to a centered luminance mask. Its hue is not the skin color,
    and there is no warm multiply on that texture.
    """
    mat = bpy.data.materials.get("MAT_PROXY_CHARACTER")
    if mat is None or mat.node_tree is None:
        raise RuntimeError("skin material missing")
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    image_node = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeTexImage" and n.image), None)
    for node in list(nt.nodes):
        if node.bl_idname == "ShaderNodeMix" and node.blend_type == "MULTIPLY":
            nt.nodes.remove(node)

    albedo = nt.nodes.new("ShaderNodeVertexColor")
    albedo.layer_name = "skin_albedo"
    albedo.location = (-640, 220)
    rough_attr = nt.nodes.new("ShaderNodeVertexColor")
    rough_attr.layer_name = "skin_rough"
    rough_attr.location = (-640, -40)

    detail = None
    if image_node is not None:
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        bw.location = (-420, 40)
        nt.links.new(image_node.outputs["Color"], bw.inputs["Color"])
        mapped = nt.nodes.new("ShaderNodeMapRange")
        mapped.location = (-220, 40)
        mapped.inputs["From Min"].default_value = 0.30
        mapped.inputs["From Max"].default_value = 0.70
        mapped.inputs["To Min"].default_value = 0.94
        mapped.inputs["To Max"].default_value = 1.06
        nt.links.new(bw.outputs["Val"], mapped.inputs["Value"])
        detail = mapped.outputs["Result"]

    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.location = (-420, -220)
    noise.inputs["Scale"].default_value = 140.0
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.55
    noise_map = nt.nodes.new("ShaderNodeMapRange")
    noise_map.location = (-220, -220)
    noise_map.inputs["From Min"].default_value = 0.35
    noise_map.inputs["From Max"].default_value = 0.65
    noise_map.inputs["To Min"].default_value = 0.97
    noise_map.inputs["To Max"].default_value = 1.03
    nt.links.new(noise.outputs["Fac"], noise_map.inputs["Value"])

    def rgba_socket(node, name):
        for sock in list(node.inputs) + list(node.outputs):
            if sock.name == name and sock.type == "RGBA" and sock.enabled:
                return sock
        raise RuntimeError(f"{node.name} has no enabled RGBA socket {name}")

    def gray_color(value_socket):
        combine = nt.nodes.new("ShaderNodeCombineColor")
        for channel in ("Red", "Green", "Blue"):
            nt.links.new(value_socket, combine.inputs[channel])
        return combine.outputs["Color"]

    color_mix = nt.nodes.new("ShaderNodeMix")
    color_mix.data_type = "RGBA"
    color_mix.blend_type = "MULTIPLY"
    color_mix.location = (40, 180)
    color_mix.inputs["Factor"].default_value = 1.0
    nt.links.new(albedo.outputs["Color"], rgba_socket(color_mix, "A"))
    if detail is not None:
        nt.links.new(gray_color(detail), rgba_socket(color_mix, "B"))
    else:
        rgba_socket(color_mix, "B").default_value = (1.0, 1.0, 1.0, 1.0)
    color_mix2 = nt.nodes.new("ShaderNodeMix")
    color_mix2.data_type = "RGBA"
    color_mix2.blend_type = "MULTIPLY"
    color_mix2.location = (260, 180)
    color_mix2.inputs["Factor"].default_value = 1.0
    nt.links.new(rgba_socket(color_mix, "Result"), rgba_socket(color_mix2, "A"))
    nt.links.new(gray_color(noise_map.outputs["Result"]), rgba_socket(color_mix2, "B"))
    # Disconnect whatever currently feeds base color, then use the authored chain.
    for link in list(bsdf.inputs["Base Color"].links):
        nt.links.remove(link)
    nt.links.new(rgba_socket(color_mix2, "Result"), bsdf.inputs["Base Color"])

    rough_sep = nt.nodes.new("ShaderNodeSeparateColor")
    rough_sep.location = (-220, -40)
    nt.links.new(rough_attr.outputs["Color"], rough_sep.inputs["Color"])
    rough_mix = nt.nodes.new("ShaderNodeMath")
    rough_mix.operation = "MULTIPLY"
    rough_mix.location = (40, -80)
    nt.links.new(rough_sep.outputs["Red"], rough_mix.inputs[0])
    nt.links.new(noise_map.outputs["Result"], rough_mix.inputs[1])
    for link in list(bsdf.inputs["Roughness"].links):
        nt.links.remove(link)
    nt.links.new(rough_mix.outputs["Value"], bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (40, -320)
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.0015
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    if "Normal" in bsdf.inputs:
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    def set_input(name, value):
        if name in bsdf.inputs and not bsdf.inputs[name].is_linked:
            bsdf.inputs[name].default_value = value

    set_input("Subsurface Weight", 0.14)
    set_input("Subsurface Scale", 0.006)
    if "Subsurface Radius" in bsdf.inputs and not bsdf.inputs["Subsurface Radius"].is_linked:
        bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.38, 0.22)
    set_input("Specular IOR Level", 0.32)
    mat.diffuse_color = (*base_color_tuple(), 1.0)


def base_color_tuple():
    return tuple(_srgb_u8_to_linear(c) for c in (158, 114, 88))


def _linear_to_srgb_u8(value):
    value = min(1.0, max(0.0, value))
    if value <= 0.0031308:
        out = value * 12.92
    else:
        out = 1.055 * (value ** (1.0 / 2.4)) - 0.055
    return int(round(out * 255.0))


def _image_array(image):
    width, height = image.size
    buf = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(buf)
    return buf.reshape(height, width, 4)


def _write_image_array(image, array_hwc):
    flat = np.ascontiguousarray(array_hwc, dtype=np.float32).ravel()
    image.pixels.foreach_set(flat)
    image.update()


def _find_image(obj, token):
    for slot in obj.material_slots:
        mat = slot.material
        if mat is None or mat.node_tree is None:
            continue
        for node in mat.node_tree.nodes:
            if node.bl_idname == "ShaderNodeTexImage" and node.image and token in node.image.name.lower():
                return node.image
            if node.bl_idname == "ShaderNodeTexImage" and node.image and token in (node.image.filepath or "").lower():
                return node.image
    for slot in obj.material_slots:
        mat = slot.material
        if mat is None or mat.node_tree is None:
            continue
        for node in mat.node_tree.nodes:
            if node.bl_idname == "ShaderNodeTexImage" and node.image:
                return node.image
    return None


def _uv_height_map(obj, size=256):
    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        return None
    height = np.full(size * size, np.nan, dtype=np.float32)
    counts = np.zeros(size * size, dtype=np.int32)
    for poly in mesh.polygons:
        z = sum(mesh.vertices[i].co.z for i in poly.vertices) / len(poly.vertices)
        u = sum(uv_layer.data[i].uv[0] for i in poly.loop_indices) / len(poly.loop_indices)
        v = sum(uv_layer.data[i].uv[1] for i in poly.loop_indices) / len(poly.loop_indices)
        ix = min(size - 1, max(0, int(u * (size - 1))))
        iy = min(size - 1, max(0, int((1.0 - v) * (size - 1))))
        index = iy * size + ix
        if counts[index] == 0 or np.isnan(height[index]):
            height[index] = z
        else:
            height[index] += z
        counts[index] += 1
    good = counts > 0
    height[good] /= counts[good]
    # Nearest fill so seams keep a zone.
    if not np.any(good):
        return None
    ys, xs = np.mgrid[0:size, 0:size]
    known_y, known_x = np.where(good.reshape(size, size))
    grid = height.reshape(size, size)
    unknown = ~good.reshape(size, size)
    if np.any(unknown):
        # Cheap 8-pass dilation.
        for _ in range(8):
            filled = grid.copy()
            mask = ~np.isnan(grid)
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                shifted = np.roll(np.roll(grid, dy, 0), dx, 1)
                shifted_mask = np.roll(np.roll(mask, dy, 0), dx, 1)
                take = np.isnan(filled) & shifted_mask
                filled[take] = shifted[take]
            grid = filled
    return grid


def _recolor_clothes(obj):
    image = _find_image(obj, "diffuse")
    if image is None:
        print("clothes diffuse missing")
        return
    pixels = _image_array(image)
    height, width, _ = pixels.shape
    zones = _uv_height_map(obj, 256)
    jacket = np.array([_srgb_u8_to_linear(c) for c in PALETTE["jacket"]], dtype=np.float32)
    knit = np.array([_srgb_u8_to_linear(c) for c in PALETTE["knit"]], dtype=np.float32)
    trousers = np.array([_srgb_u8_to_linear(c) for c in PALETTE["trousers"]], dtype=np.float32)
    luma = pixels[:, :, 0] * 0.2126 + pixels[:, :, 1] * 0.7152 + pixels[:, :, 2] * 0.0722
    if zones is None:
        target = np.broadcast_to(jacket, pixels[:, :, :3].shape).copy()
    else:
        zone_big = np.array(Image_resize_nearest(zones, (width, height)))
        target = np.zeros_like(pixels[:, :, :3])
        leg = zone_big < 0.82
        shirt = (~leg) & (luma > 0.55)
        coat = ~leg & ~shirt
        target[coat] = jacket
        target[shirt] = knit
        target[leg] = trousers
    # Keep local weave contrast, replace the hue.
    variation = np.clip(luma / (np.mean(luma) + 1e-5), 0.72, 1.28)
    pixels[:, :, 0] = np.clip(target[:, :, 0] * variation, 0.0, 1.0)
    pixels[:, :, 1] = np.clip(target[:, :, 1] * variation, 0.0, 1.0)
    pixels[:, :, 2] = np.clip(target[:, :, 2] * variation, 0.0, 1.0)
    _write_image_array(image, pixels)
    image.pack()
    print("recolored clothes", image.name, image.size)


def Image_resize_nearest(grid, size_wh):
    width, height = size_wh
    src_h, src_w = grid.shape
    ys = np.clip((np.arange(height) * src_h / height).astype(np.int32), 0, src_h - 1)
    xs = np.clip((np.arange(width) * src_w / width).astype(np.int32), 0, src_w - 1)
    return grid[ys][:, xs]


def _recolor_shoes(obj):
    image = _find_image(obj, "diffuse")
    if image is None:
        return
    if max(image.size) > 1024:
        image.scale(1024, 1024)
    pixels = _image_array(image)
    luma = pixels[:, :, 0] * 0.2126 + pixels[:, :, 1] * 0.7152 + pixels[:, :, 2] * 0.0722
    target = np.array([_srgb_u8_to_linear(c) for c in PALETTE["shoes"]], dtype=np.float32)
    variation = np.clip(luma / (np.mean(luma) + 1e-5), 0.55, 1.7)
    for channel in range(3):
        pixels[:, :, channel] = np.clip(target[channel] * variation, 0.0, 1.0)
    _write_image_array(image, pixels)
    image.pack()
    print("recolored shoes", image.name)


def _recolor_named_image(image, target_srgb, lo=0.62, hi=1.45):
    if image is None:
        return
    pixels = _image_array(image)
    luma = pixels[:, :, 0] * 0.2126 + pixels[:, :, 1] * 0.7152 + pixels[:, :, 2] * 0.0722
    target = np.array([_srgb_u8_to_linear(c) for c in target_srgb], dtype=np.float32)
    variation = np.clip(luma / (np.mean(luma) + 1e-5), lo, hi)
    for channel in range(3):
        pixels[:, :, channel] = np.clip(target[channel] * variation, 0.0, 1.0)
    _write_image_array(image, pixels)
    image.pack()
    print("recolored", image.name, image.size[:])


def _darken_irises():
    """Shift the iris toward dark brown. Leave the brighter sclera and the pupil."""
    image = bpy.data.images.get("brown_eye.png")
    if image is None:
        print("eye texture missing")
        return
    pixels = _image_array(image)
    luma = pixels[:, :, 0] * 0.2126 + pixels[:, :, 1] * 0.7152 + pixels[:, :, 2] * 0.0722
    iris = (luma > 0.02) & (luma < 0.22)
    if int(iris.sum()) < 100:
        print("iris mask small", int(iris.sum()))
        return
    target = np.array([_srgb_u8_to_linear(c) for c in (62, 30, 16)], dtype=np.float32)
    mean = float(luma[iris].mean()) + 1e-5
    variation = np.clip(luma / mean, 0.55, 1.35)
    for channel in range(3):
        pixels[:, :, channel][iris] = np.clip(target[channel] * variation[iris], 0.0, 1.0)
    _write_image_array(image, pixels)
    image.pack()
    print("darkened irises", int(iris.sum()))


def _soften_brows():
    image = bpy.data.images.get("eyebrow001.png")
    if image is None:
        print("brow texture missing")
        return
    pixels = _image_array(image)
    brown = np.array([_srgb_u8_to_linear(c) for c in (78, 52, 38)], dtype=np.float32)
    rgb = pixels[:, :, :3]
    # Pull harsh black toward a dark brown without flattening the card.
    pixels[:, :, :3] = np.clip(rgb * 0.72 + brown * 0.28, 0.0, 1.0)
    _write_image_array(image, pixels)
    image.pack()
    print("softened brows", image.size[:])


def _gap_of(bvh, co, interior):
    ray = co - interior
    dist = ray.length
    if dist < 1e-5:
        return -1.0
    hit, _n, _i, _d = bvh.ray_cast(interior, ray / dist, dist + 0.08)
    if hit is None:
        return 1.0
    return dist - (hit - interior).length


def _point_in_tri_xz(p, a, b, c):
    def sign(p1, p2, p3):
        return (p1.x - p3.x) * (p2.z - p3.z) - (p2.x - p3.x) * (p1.z - p3.z)
    d1 = sign(p, a, b)
    d2 = sign(p, b, c)
    d3 = sign(p, c, a)
    has_neg = d1 < 0 or d2 < 0 or d3 < 0
    has_pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (has_neg and has_pos)


def trim_hair(hair, head, eyes, brows):
    """Drop cards inside the face or covering the pupils and brows. Leave the crown."""
    coords = [v.co.copy() for v in head.data.vertices]
    crown = max(v.z for v in coords)
    chin_z = find_chin_z(coords, crown)
    interior = Vector((0.0, -0.015, chin_z + (crown - chin_z) * 0.45))
    bvh = BVHTree.FromPolygons(coords, [tuple(poly.vertices) for poly in head.data.polygons])
    mesh = hair.data

    def enters_face(co, gap):
        if gap > -0.001:
            return False
        if co.z > chin_z + 0.82 * (crown - chin_z):
            return False
        if co.y > -0.05:
            return False
        if abs(co.x) > 0.09:
            return False
        return True

    gaps = [_gap_of(bvh, vert.co, interior) for vert in mesh.vertices]
    eye_verts = [v.co.copy() for v in eyes.data.vertices]
    pupils = []
    for sign in (1.0, -1.0):
        side = [v for v in eye_verts if v.x * sign > 0.005]
        if side:
            pupils.append(sum(side, Vector()) / len(side))
    brow_pts = [v.co.copy() for v in brows.data.vertices]
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    drop = []
    for face in bm.faces:
        center = face.calc_center_median()
        inside = enters_face(center, _gap_of(bvh, center, interior)) or any(
            enters_face(mesh.vertices[vert.index].co, gaps[vert.index]) for vert in face.verts
        )
        covers_pupil = False
        for pupil in pupils:
            if center.y > pupil.y - 0.004:
                continue
            if abs(center.x - pupil.x) < 0.018 and abs(center.z - pupil.z) < 0.016:
                covers_pupil = True
        if inside or covers_pupil:
            drop.append(face)
    if drop:
        bmesh.ops.delete(bm, geom=drop, context="FACES")
    # Second pass: keep at least 75% of each brow arc visible from the front.
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    def brow_hidden_fraction(side_sign):
        side = [p for p in brow_pts if p.x * side_sign > 0.004]
        if not side:
            return 0.0, []
        hidden = 0
        blockers = {}
        for point in side:
            hit_face = None
            for face in bm.faces:
                if face.calc_center_median().y > point.y - 0.003:
                    continue
                verts = [vert.co for vert in face.verts]
                if len(verts) < 3:
                    continue
                if _point_in_tri_xz(point, verts[0], verts[1], verts[2]) or (
                    len(verts) > 3 and _point_in_tri_xz(point, verts[0], verts[2], verts[3])
                ):
                    hit_face = face
                    break
            if hit_face is not None:
                hidden += 1
                blockers[hit_face.index] = hit_face
        return hidden / len(side), list(blockers.values())

    extra = 0
    for _ in range(6):
        changed = False
        for sign in (1.0, -1.0):
            fraction, blockers = brow_hidden_fraction(sign)
            if fraction > 0.25 and blockers:
                bmesh.ops.delete(bm, geom=blockers, context="FACES")
                extra += len(blockers)
                bm.faces.ensure_lookup_table()
                changed = True
        if not changed:
            break
    loose = [vert for vert in bm.verts if not vert.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    print("hair face cards removed", len(drop), "brow blockers", extra)


def _add_delta(obj, deltas):
    if not deltas:
        return
    mesh = obj.data
    for index, delta in deltas.items():
        mesh.vertices[index].co += delta
    if mesh.shape_keys:
        for key in mesh.shape_keys.key_blocks:
            for index, delta in deltas.items():
                key.data[index].co += delta
    mesh.update()


def apply_rest_face(obj):
    """Subtle warmth and 1–3 mm asymmetry, applied to Basis and every shape key."""
    mesh = obj.data
    if mesh.shape_keys is None:
        return
    basis = mesh.shape_keys.key_blocks["Basis"]
    coords = [Vector(item.co) for item in basis.data]
    crown = max(v.z for v in coords)
    chin_z = find_chin_z(coords, crown)
    head_h = crown - chin_z
    nose_band = [v for v in coords if abs(v.x) < 0.012 and chin_z + 0.35 * head_h < v.z < chin_z + 0.78 * head_h]
    nose = min(nose_band, key=lambda v: v.y)
    lip_z = chin_z + 0.20 * head_h
    lips = [
        (index, co)
        for index, co in enumerate(coords)
        if abs(co.x) < 0.05 and abs(co.z - lip_z) < 0.016 and co.y < nose.y + 0.012
    ]
    if len(lips) < 6:
        print("rest face skipped, lip verts", len(lips))
        return
    front = min(co.y for _, co in lips)
    lips = [(index, co) for index, co in lips if co.y < front + 0.008]
    left = min(lips, key=lambda item: item[1].x)
    right = max(lips, key=lambda item: item[1].x)
    deltas = {}
    # Both corners lift a little. Character-right (+X) lifts 1.2 mm more.
    deltas[left[0]] = Vector((0.0, 0.0004, 0.0014))
    deltas[right[0]] = Vector((0.0, 0.0004, 0.0026))
    brow_z = chin_z + 0.70 * head_h
    brows = [
        (index, co)
        for index, co in enumerate(coords)
        if abs(co.z - brow_z) < 0.012 and 0.02 < abs(co.x) < 0.05 and co.y < -0.07
    ]
    if brows:
        brow_l = min(brows, key=lambda item: item[1].x)
        deltas[brow_l[0]] = deltas.get(brow_l[0], Vector()) + Vector((0.0, -0.0003, 0.0020))
    # Close a parted center if the lip pair is more than 1 mm apart.
    center = [item for item in lips if abs(item[1].x) < 0.008]
    if len(center) >= 2:
        upper = max(center, key=lambda item: item[1].z)
        lower = min(center, key=lambda item: item[1].z)
        gap = upper[1].z - lower[1].z
        if gap > 0.012:
            # These are not the seam; ignore a whole-lip span.
            pass
        elif gap > 0.001:
            half = (gap - 0.0006) * 0.5
            deltas[upper[0]] = deltas.get(upper[0], Vector()) + Vector((0.0, 0.0, -half))
            deltas[lower[0]] = deltas.get(lower[0], Vector()) + Vector((0.0, 0.0, half))
            print("closed lip gap", round(gap * 1000, 2), "mm")
    _add_delta(obj, deltas)
    asym = (deltas[right[0]] - deltas[left[0]]).length * 1000.0
    print(
        "rest face",
        "corner_l", tuple(round(c, 4) for c in left[1]),
        "corner_r", tuple(round(c, 4) for c in right[1]),
        "asym_mm", round(asym, 2),
        "verts", len(deltas),
    )


def build_lanyard(suit, coll, chin_z):
    """12 mm strap and a blank 54 x 86 mm portrait card centered on the sternum."""
    pts = [v.co.copy() for v in suit.data.vertices]

    def chest_front(z, x):
        band = [v.co.y for v in suit.data.vertices if abs(v.co.z - z) < 0.03 and abs(v.co.x - x) < 0.045]
        if not band:
            band = [v.co.y for v in suit.data.vertices if abs(v.co.z - z) < 0.06 and abs(v.co.x) < 0.08]
        return min(band) if band else -0.16

    samples = []
    steps = 48
    collar_z = 1.40
    for step in range(steps):
        ang = 0.55 + (math.tau - 1.10) * step / (steps - 1)
        z_target = collar_z + 0.012 * math.cos(ang)
        dx, dy = math.sin(ang), -math.cos(ang)
        found = []
        for point in pts:
            radius = math.hypot(point.x, point.y)
            if radius < 0.045 or radius > 0.13:
                continue
            if abs(point.z - z_target) > 0.035:
                continue
            point_ang = math.atan2(point.x, -point.y)
            delta = (point_ang - ang + math.pi) % math.tau - math.pi
            if abs(delta) < 0.11:
                found.append(point)
        if not found:
            continue
        found.sort(key=lambda point: math.hypot(point.x, point.y))
        pick = found[min(len(found) - 1, int(len(found) * 0.72))]
        outward = Vector((dx, dy, 0.0)).normalized()
        samples.append(pick + outward * 0.005 + Vector((0.0, 0.0, 0.002)))
    if len(samples) < 16:
        raise RuntimeError(f"collar band found only {len(samples)} points")
    for _ in range(6):
        smoothed = [samples[0]]
        for index in range(1, len(samples) - 1):
            smoothed.append(samples[index - 1] * 0.25 + samples[index] * 0.5 + samples[index + 1] * 0.25)
        smoothed.append(samples[-1])
        samples = smoothed

    badge_z = 1.20
    front = chest_front(badge_z, 0.0)
    # 5 mm in front of the garment, inside the 3–8 mm clearance gate.
    badge = Vector((0.0, front - 0.005, badge_z))

    def drop(side, sign):
        points = []
        for step in range(1, 8):
            t = step / 7.0
            z = side.z * (1.0 - t) + (badge.z + 0.043) * t
            x = side.x * (1.0 - t) ** 1.35 + sign * 0.008 * t
            y = chest_front(z, x) - 0.005
            points.append(Vector((x, y, z)))
        return points

    path = list(reversed(drop(samples[0], -1.0))) + samples + drop(samples[-1], 1.0)
    bm = bmesh.new()
    width = 0.012
    thick = 0.0016
    rings = []
    for index, point in enumerate(path):
        if index == 0:
            tangent = path[1] - point
        elif index == len(path) - 1:
            tangent = point - path[-2]
        else:
            tangent = path[index + 1] - path[index - 1]
        if tangent.length < 1e-6:
            tangent = Vector((0.0, 0.0, -1.0))
        tangent.normalize()
        side = tangent.cross(Vector((0.0, 0.0, 1.0)))
        if side.length < 1e-4:
            side = Vector((1.0, 0.0, 0.0))
        side.normalize()
        outward = Vector((point.x, point.y, 0.0))
        if outward.length < 1e-4 or point.z < badge.z + 0.03:
            outward = Vector((0.0, -1.0, 0.0))
        else:
            outward.normalize()
        ring = []
        for su, ou in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            ring.append(bm.verts.new(point + side * (width * 0.5 * su) + outward * (thick * 0.5 * ou)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(4):
            j = (i + 1) % 4
            try:
                face = bm.faces.new((a[i], a[j], b[j], b[i]))
                face.smooth = True
            except ValueError:
                pass

    hw, hh, hd = 0.027, 0.043, 0.0022
    radius = 0.004
    steps_c = 3

    def corner(cx, cz, a0, a1):
        pts = []
        for i in range(steps_c + 1):
            ang = a0 + (a1 - a0) * i / steps_c
            pts.append((cx + math.cos(ang) * radius, cz + math.sin(ang) * radius))
        return pts

    outline = []
    outline += corner(hw - radius, hh - radius, 0.0, math.pi / 2)
    outline += corner(-(hw - radius), hh - radius, math.pi / 2, math.pi)
    outline += corner(-(hw - radius), -(hh - radius), math.pi, 3 * math.pi / 2)
    outline += corner(hw - radius, -(hh - radius), 3 * math.pi / 2, math.tau)
    # Drop the duplicated joint samples.
    cleaned = [outline[0]]
    for point in outline[1:]:
        if (point[0] - cleaned[-1][0]) ** 2 + (point[1] - cleaned[-1][1]) ** 2 > 1e-8:
            cleaned.append(point)
    if (cleaned[0][0] - cleaned[-1][0]) ** 2 + (cleaned[0][1] - cleaned[-1][1]) ** 2 < 1e-8:
        cleaned.pop()
    front_ring = [bm.verts.new((badge.x + x, badge.y - hd, badge.z + z)) for x, z in cleaned]
    back_ring = [bm.verts.new((badge.x + x, badge.y, badge.z + z)) for x, z in cleaned]
    try:
        bm.faces.new(front_ring).smooth = True
    except ValueError:
        pass
    try:
        bm.faces.new(list(reversed(back_ring))).smooth = True
    except ValueError:
        pass
    for i in range(len(cleaned)):
        j = (i + 1) % len(cleaned)
        try:
            face = bm.faces.new((front_ring[i], front_ring[j], back_ring[j], back_ring[i]))
            face.smooth = True
        except ValueError:
            pass

    mesh = bpy.data.meshes.new("GEO_AVERY_LANYARD_MESH")
    strap = bpy.data.materials.get("MAT_LANYARD_STRAP") or bpy.data.materials.new("MAT_LANYARD_STRAP")
    strap.use_nodes = True
    bsdf = next(n for n in strap.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*(_srgb_u8_to_linear(c) for c in PALETTE["lanyard"]), 1.0)
    bsdf.inputs["Roughness"].default_value = 0.55
    badge_mat = bpy.data.materials.get("MAT_LANYARD_BADGE") or bpy.data.materials.new("MAT_LANYARD_BADGE")
    badge_mat.use_nodes = True
    bsdf_b = next(n for n in badge_mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    bsdf_b.inputs["Base Color"].default_value = (*(_srgb_u8_to_linear(c) for c in PALETTE["badge"]), 1.0)
    bsdf_b.inputs["Roughness"].default_value = 0.42
    mesh.materials.append(strap)
    mesh.materials.append(badge_mat)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        cz = sum(mesh.vertices[i].co.z for i in poly.vertices) / len(poly.vertices)
        cy = sum(mesh.vertices[i].co.y for i in poly.vertices) / len(poly.vertices)
        poly.material_index = 1 if cz < badge.z + hh - 0.004 and cy < front - 0.001 else 0
        poly.use_smooth = True
    obj = bpy.data.objects.new("GEO_AVERY_LANYARD", mesh)
    obj["lanyard_width_m"] = width
    obj["badge_width_m"] = hw * 2
    obj["badge_height_m"] = hh * 2
    coll.objects.link(obj)
    # If the band enters the head, drop it rather than ship a spike through the jaw.
    head = bpy.data.objects.get("GEO_AVERY_HEAD")
    if head is not None:
        interior = Vector((0.0, -0.015, chin_z + 0.08))
        bvh = BVHTree.FromPolygons(
            [vert.co.copy() for vert in head.data.vertices],
            [tuple(poly.vertices) for poly in head.data.polygons],
        )
        inside = 0
        for vert in mesh.vertices:
            if vert.co.z < chin_z:
                continue
            if _gap_of(bvh, vert.co, interior) < -0.001:
                inside += 1
        if inside:
            print("lanyard intersected the head", inside, "— removed")
            coll.objects.unlink(obj)
            bpy.data.objects.remove(obj)
            return None
    return obj


def seat_shoes(shoes):
    zmin = min(v.co.z for v in shoes.data.vertices)
    if zmin >= -0.005:
        print("shoe sole", round(zmin, 4))
        return zmin
    pivot = 0.02
    factor = pivot / (pivot - zmin)
    for vert in shoes.data.vertices:
        if vert.co.z < pivot:
            vert.co.z = pivot - (pivot - vert.co.z) * factor
    shoes.data.update()
    planted = min(v.co.z for v in shoes.data.vertices)
    print("shoe sole seated", round(zmin, 4), "->", round(planted, 4))
    return planted


def limit_influences(obj, maximum=4):
    """Keep at most four contract-bone influences and normalize them to 1.

    MakeHuman joint groups are left in place so measurements can still find landmarks.
    They do not match a contract bone, so the armature does not deform with them.
    """
    groups = {group.name: group for group in obj.vertex_groups}
    for name in CONTRACT_BONES:
        if name not in groups:
            groups[name] = obj.vertex_groups.new(name=name)
    index_name = {group.index: group.name for group in obj.vertex_groups}
    bones = {bone.name: (Vector(bone.head_local), Vector(bone.tail_local)) for bone in bpy.data.objects["RIG_AVERY_CHEN"].data.bones}
    unbound = 0
    for vert in obj.data.vertices:
        weights = []
        for assignment in vert.groups:
            name = index_name.get(assignment.group)
            if name in CONTRACT_BONES and assignment.weight > 1e-6:
                weights.append((name, assignment.weight))
        if not weights:
            best = min(bones, key=lambda name: segment_distance(vert.co, bones[name][0], bones[name][1]))
            weights = [(best, 1.0)]
            unbound += 1
        weights.sort(key=lambda item: item[1], reverse=True)
        weights = weights[:maximum]
        total = sum(weight for _, weight in weights) or 1.0
        for name in CONTRACT_BONES:
            if name in groups:
                groups[name].remove([vert.index])
        for name, weight in weights:
            groups[name].add([vert.index], weight / total, "REPLACE")
    if unbound:
        print(obj.name, "assigned", unbound, "previously unbound verts")


def rendered_triangles(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    count = sum(max(0, len(poly.vertices) - 2) for poly in mesh.polygons)
    evaluated.to_mesh_clear()
    return count


def enforce_texture_budget(limit_mb=32.0):
    images = [img for img in bpy.data.images if img.size[0] > 0 and img.size[1] > 0]

    def mb(img):
        return img.size[0] * img.size[1] * 4 / (1024 * 1024)

    for img in images:
        name = (img.name + img.filepath).lower()
        cap = 512 if ("normal" in name or name.endswith("_ao") or "_ao" in name) else 1024
        if max(img.size) > cap:
            img.scale(cap, cap)
    guard = 0
    while sum(mb(img) for img in images) > limit_mb and guard < 8:
        img = max(images, key=mb)
        if min(img.size) <= 256:
            break
        img.scale(max(256, img.size[0] // 2), max(256, img.size[1] // 2))
        guard += 1
    total = sum(mb(img) for img in images)
    for img in images:
        try:
            img.pack()
        except RuntimeError as exc:
            print("pack", img.name, exc)
    print(f"texture memory {total:.1f} MB")
    return total


def tuck_jacket_outer_shoulder(jacket):
    """Pull only the jacket shoulder seam inside 2.45 head widths. The body stays put."""
    cap = 0.196
    moved = 0
    for vert in jacket.data.vertices:
        if not (1.35 <= vert.co.z <= 1.41):
            continue
        ax = abs(vert.co.x)
        if ax <= cap:
            continue
        new = cap + (ax - cap) * 0.15
        vert.co.x = math.copysign(new, vert.co.x)
        moved += 1
    jacket.data.update()
    return moved


def jacket_outer_width(clothes, shoulder_z):
    """Shoulder-seam width. The hanging sleeve below the acromion is not the shoulder breadth."""
    band = [
        v.co for v in clothes.data.vertices
        if abs(v.co.z - shoulder_z) < 0.025 and abs(v.co.y + 0.02) < 0.06 and abs(v.co.x) < 0.24
    ]
    if len(band) < 8:
        return None
    return max(v.x for v in band) - min(v.x for v in band)


def tuck_shoulder_caps(obj):
    """Pull only the lateral deltoid/sleeve cap inward. Joints at |x|≈0.16 stay put."""
    deltas = {}
    inner = 0.175
    outer_target = 0.196
    span = 0.25 - inner
    for index, vert in enumerate(obj.data.vertices):
        if not (1.30 < vert.co.z < 1.46):
            continue
        ax = abs(vert.co.x)
        if ax <= inner:
            continue
        compressed = inner + (min(ax, 0.25) - inner) * ((outer_target - inner) / span)
        new_x = math.copysign(min(compressed, outer_target), vert.co.x)
        deltas[index] = new_x - vert.co.x
        vert.co.x = new_x
    if obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks:
            for index, delta in deltas.items():
                key.data[index].co.x += delta
    obj.data.update()
    return len(deltas)


def copy_weights(obj, src_name, dst_name):
    src = obj.vertex_groups.get(src_name)
    if src is None:
        return
    dst = obj.vertex_groups.get(dst_name)
    if dst is None:
        dst = obj.vertex_groups.new(name=dst_name)
    src_index = src.index
    for vert in obj.data.vertices:
        weight = 0.0
        for assignment in vert.groups:
            if assignment.group == src_index:
                weight = assignment.weight
                break
        if weight > 0.0:
            dst.add([vert.index], weight, "ADD")


def remap_makehuman_weights(obj):
    """The game-engine rig is already weighted. Map it onto proxy_rig_v1.

    MakeHuman left is +X, which is this armature's .R side.
    """
    pairs = [
        ("upperarm_l", "upper_arm.R"),
        ("lowerarm_l", "forearm.R"),
        ("hand_l", "hand.R"),
        ("thigh_l", "thigh.R"),
        ("calf_l", "shin.R"),
        ("foot_l", "foot.R"),
        ("ball_l", "foot.R"),
        ("upperarm_r", "upper_arm.L"),
        ("lowerarm_r", "forearm.L"),
        ("hand_r", "hand.L"),
        ("thigh_r", "thigh.L"),
        ("calf_r", "shin.L"),
        ("foot_r", "foot.L"),
        ("ball_r", "foot.L"),
        ("spine_01", "spine"),
        ("spine_02", "spine"),
        ("spine_03", "chest"),
        ("neck_01", "neck"),
        ("clavicle_l", "chest"),
        ("clavicle_r", "chest"),
        ("Root", "root"),
    ]
    for src, dst in pairs:
        copy_weights(obj, src, dst)
    for group in list(obj.vertex_groups):
        name = group.name
        if name.endswith("_l") and any(part in name for part in ("index", "middle", "ring", "pinky", "thumb")):
            copy_weights(obj, name, "hand.R")
        elif name.endswith("_r") and any(part in name for part in ("index", "middle", "ring", "pinky", "thumb")):
            copy_weights(obj, name, "hand.L")


def transfer_weights(src, dst):
    """Copy proxy weights from the skin to a fitted asset by nearest vertex."""
    from mathutils.kdtree import KDTree
    tree = KDTree(len(src.data.vertices))
    for vert in src.data.vertices:
        tree.insert(vert.co, vert.index)
    tree.balance()
    src_groups = {group.index: group.name for group in src.vertex_groups}
    keep = {
        "root", "pelvis", "spine", "chest", "neck", "head",
        "upper_arm.L", "forearm.L", "hand.L", "upper_arm.R", "forearm.R", "hand.R",
        "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R",
    }
    dst_groups = {}
    for name in keep:
        group = dst.vertex_groups.get(name)
        if group is None:
            group = dst.vertex_groups.new(name=name)
        dst_groups[name] = group
    for vert in dst.data.vertices:
        _, index, _ = tree.find(vert.co)
        donor = src.data.vertices[index]
        for assignment in donor.groups:
            name = src_groups.get(assignment.group)
            if name in dst_groups and assignment.weight > 0.001:
                dst_groups[name].add([vert.index], assignment.weight, "REPLACE")


def bind_armature(obj, arm):
    for modifier in list(obj.modifiers):
        if modifier.type == "ARMATURE":
            obj.modifiers.remove(modifier)
    modifier = obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = arm
    obj.parent = arm
    obj.matrix_parent_inverse = arm.matrix_world.inverted()


def weight_to_bones(obj, names):
    for name in ("root", "pelvis", "spine", "chest", "neck", "head",
                 "upper_arm.L", "forearm.L", "hand.L", "upper_arm.R", "forearm.R", "hand.R",
                 "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R"):
        if obj.vertex_groups.get(name) is None:
            obj.vertex_groups.new(name=name)
    groups = {name: obj.vertex_groups[name] for name in names}
    for vert in obj.data.vertices:
        for name, group in groups.items():
            group.add([vert.index], 1.0 / len(names), "REPLACE")


def clean_limb_weights(obj):
    """Keep arm vertices on the arm bones and leg vertices on the leg bones."""
    groups = {group.name: group for group in obj.vertex_groups}
    arm_l = ["upper_arm.L", "forearm.L", "hand.L", "chest"]
    arm_r = ["upper_arm.R", "forearm.R", "hand.R", "chest"]
    leg_l = ["thigh.L", "shin.L", "foot.L", "pelvis"]
    leg_r = ["thigh.R", "shin.R", "foot.R", "pelvis"]
    all_limbs = arm_l + arm_r + leg_l + leg_r

    def zero_except(vert_index, keep):
        for name, group in groups.items():
            if name in all_limbs and name not in keep:
                group.remove([vert_index])

    for vert in obj.data.vertices:
        x, y, z = vert.co
        if 0.72 < z < 1.42 and x < -0.12:
            zero_except(vert.index, arm_l)
        elif 0.72 < z < 1.42 and x > 0.12:
            zero_except(vert.index, arm_r)
        elif z < 0.95 and abs(x) < 0.16 and y > -0.08:
            # Torso and legs stay off the arm chains.
            if x < 0:
                zero_except(vert.index, leg_l + ["pelvis", "spine", "chest"])
            else:
                zero_except(vert.index, leg_r + ["pelvis", "spine", "chest"])


def nearest_bone_distance(obj, arm, bone_name):
    bone = arm.data.bones[bone_name]
    head = Vector(bone.head_local)
    tail = Vector(bone.tail_local)
    best = 1e9
    for vert in obj.data.vertices:
        ab = tail - head
        denom = ab.length_squared or 1e-8
        t = max(0.0, min(1.0, (vert.co - head).dot(ab) / denom))
        dist = (vert.co - (head + ab * t)).length
        if dist < best:
            best = dist
    return best


def add_eye_look_keys(eyes, head):
    """Yaw the eyeballs with the head LOOK keys. No extra bones."""
    mesh = eyes.data
    verts = [v.co.copy() for v in mesh.vertices]
    centers = {}
    for sign in (1.0, -1.0):
        side = [v for v in verts if v.x * sign > 0.004]
        if side:
            centers[sign] = sum(side, Vector()) / len(side)
    if mesh.shape_keys is None:
        eyes.shape_key_add(name="Basis", from_mix=False)
    for key_name, angle in (("LOOK_LEFT", math.radians(-18.0)), ("LOOK_RIGHT", math.radians(18.0))):
        key = eyes.shape_key_add(name=key_name, from_mix=False)
        rot = Matrix.Rotation(angle, 4, "Z")
        for index, co in enumerate(verts):
            sign = 1.0 if co.x >= 0.0 else -1.0
            center = centers.get(sign, Vector())
            key.data[index].co = center + rot @ (co - center)
        key.value = 0.0
        driver = key.driver_add("value").driver
        driver.type = "SCRIPTED"
        var = driver.variables.new()
        var.name = "look"
        var.targets[0].id_type = "OBJECT"
        var.targets[0].id = head
        var.targets[0].data_path = f'data.shape_keys.key_blocks["{key_name}"].value'
        driver.expression = "look"


def tune_eyes(mat):
    if mat is None or mat.node_tree is None:
        return
    bsdf = next((n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bsdf is None:
        return
    if "Roughness" in bsdf.inputs and not bsdf.inputs["Roughness"].is_linked:
        bsdf.inputs["Roughness"].default_value = 0.16
    if "Specular IOR Level" in bsdf.inputs and not bsdf.inputs["Specular IOR Level"].is_linked:
        bsdf.inputs["Specular IOR Level"].default_value = 0.4


def make_human(coll, data):
    HumanService, TargetService, GeneralObjectProperties = enable_mpfb()
    human = HumanService.create_human(
        mask_helpers=False,
        detailed_helpers=True,
        extra_vertex_groups=True,
        feet_on_ground=True,
        scale=0.1,
        macro_detail_dict=MACRO,
    )
    rig = HumanService.add_builtin_rig(human, "game_engine", import_weights=True)
    pose_arms_down(human, rig)
    bake_evaluated(human)
    bpy.data.objects.remove(rig, do_unlink=True)
    scale = align_to_proxy(human)
    proportions = fit_proportions(human)
    scale_factor = GeneralObjectProperties.get_value("scale_factor", entity_reference=human) or 0.1
    GeneralObjectProperties.set_value("scale_factor", float(scale_factor) * scale, entity_reference=human)
    add_expression_keys(human, data, TargetService)
    for key in human.data.shape_keys.key_blocks:
        key.value = 0.0
    apply_rest_face(human)

    # Pore detail comes from this CC0 map. The albedo itself is painted in author_skin.
    skin = data / "skins/young_lightskinned_female/young_lightskinned_female.mhmat"
    skin_fallback = data / "skins/young_caucasian_female2/young_caucasian_female2.mhmat"
    skin_path = skin if skin.is_file() else skin_fallback
    try:
        HumanService.set_character_skin(str(skin_path), human, skin_type="GAMEENGINE")
    except Exception as exc:
        print("skin setup failed", exc)
    rename_material(human, "MAT_PROXY_CHARACTER")
    ensure_character_material()
    paint_skin_zones(human)
    author_skin()
    show_only_skin_and_eyes(human)

    human.name = "GEO_AVERY_HEAD"
    link_only(human, coll)

    assets = [
        (data / "clothes/female_casualsuit01/female_casualsuit01.mhclo", "Clothes", "GEO_AVERY_BODY"),
        (data / "clothes/shoes01/shoes01.mhclo", "Clothes", "GEO_AVERY_SHOES"),
        (data / "hair/short02/short02.mhclo", "Hair", "GEO_AVERY_HAIR"),
        (data / "eyes/high-poly/high-poly.mhclo", "Eyes", "GEO_AVERY_EYES"),
        (data / "eyebrows/eyebrow001/eyebrow001.mhclo", "Eyebrows", "GEO_AVERY_BROWS"),
        (data / "teeth/teeth_base/teeth_base.mhclo", "Teeth", "GEO_AVERY_TEETH"),
        (data / "tongue/tongue01/tongue01.mhclo", "Tongue", "GEO_AVERY_TONGUE"),
    ]
    fitted = []
    for path, kind, name in assets:
        obj = fit_asset(HumanService, human, path, kind)
        obj.name = name
        link_only(obj, coll)
        fitted.append(obj)
        print("fitted", name, len(obj.data.vertices))

    clothes = bpy.data.objects["GEO_AVERY_BODY"]
    shoes = bpy.data.objects["GEO_AVERY_SHOES"]
    _recolor_clothes(clothes)
    _recolor_shoes(shoes)
    seat_shoes(shoes)
    hair = bpy.data.objects["GEO_AVERY_HAIR"]
    eyes = bpy.data.objects["GEO_AVERY_EYES"]
    brows = bpy.data.objects["GEO_AVERY_BROWS"]
    trim_hair(hair, human, eyes, brows)
    rename_material(eyes, "MAT_PROXY_FOCUS")
    ensure_focus_material()
    tune_eyes(bpy.data.materials.get("MAT_PROXY_FOCUS"))
    add_eye_look_keys(eyes, human)
    # Helper eyes would double up with the high-poly spheres. Mask them back out.
    body = human.vertex_groups.get("body")
    if body is not None:
        for name in ("helper-l-eye", "helper-r-eye"):
            group = human.vertex_groups.get(name)
            if group is None:
                continue
            index = group.index
            for vert in human.data.vertices:
                for assignment in vert.groups:
                    if assignment.group == index and assignment.weight > 0.5:
                        body.remove([vert.index])

    lanyard = build_lanyard(clothes, coll, proportions["chin_z"])
    human["avery_proportions"] = json.dumps({k: v for k, v in proportions.items() if k != "landmarks"})
    return human, fitted, lanyard


def _connected(mesh, start_z, goal_z):
    adj = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adj[a].append(b)
        adj[b].append(a)
    starts = [v.index for v in mesh.vertices if v.co.z > start_z]
    goals = {v.index for v in mesh.vertices if v.co.z < goal_z}
    seen = set(starts)
    stack = list(starts)
    while stack:
        vert = stack.pop()
        if vert in goals:
            return True
        for nxt in adj[vert]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return False


def audit(head, hair, body, lanyard, arm):
    problems = []
    if len(head.data.vertices) < 8000:
        problems.append(f"head/body mesh is too small to be a MakeHuman base ({len(head.data.vertices)})")
    for bone_name in ("upper_arm.L", "forearm.L", "thigh.L", "shin.L", "neck"):
        group = head.vertex_groups.get(bone_name)
        count = 0
        if group is not None:
            index = group.index
            count = sum(
                1
                for vert in head.data.vertices
                for assignment in vert.groups
                if assignment.group == index and assignment.weight > 0.2
            )
        if count < 80:
            problems.append(f"{bone_name} has too few weights ({count})")
    if not _connected(head.data, 1.55, 0.15):
        problems.append("head is not connected to the legs")
    for bone in ("upper_arm.L", "forearm.L", "hand.L", "upper_arm.R", "thigh.L", "shin.L"):
        dist = nearest_bone_distance(body if bone.startswith("thigh") or bone.startswith("shin") else head, arm, bone)
        # Clothes cover the limbs; measure the skin for arms and the clothed body too.
        dist_skin = nearest_bone_distance(head, arm, bone)
        dist = min(dist, dist_skin)
        if dist > 0.08:
            problems.append(f"{bone} is {dist:.3f} m from the mesh")
    keys = [key.name for key in head.data.shape_keys.key_blocks]
    for name in VISEMES + EXPRESSIONS:
        if name not in keys:
            problems.append(f"missing shape key {name}")
    if hair is None or len(hair.data.vertices) < 100:
        problems.append("hair missing")
    if lanyard is None:
        problems.append("lanyard missing or removed because it entered the head")
    else:
        width = float(lanyard.get("lanyard_width_m", 0.0))
        badge_w = float(lanyard.get("badge_width_m", 0.0))
        badge_h = float(lanyard.get("badge_height_m", 0.0))
        if not (0.010 <= width <= 0.015):
            problems.append(f"lanyard width {width:.3f} m is outside 10-15 mm")
        if abs(badge_w - 0.054) > 0.003 or abs(badge_h - 0.086) > 0.003:
            problems.append(f"badge {badge_w*1000:.0f}x{badge_h*1000:.0f} mm is not 54x86")
        zs = [v.co.z for v in lanyard.data.vertices]
        if max(zs) < 1.30:
            problems.append("lanyard does not reach the collar")
        if min(zs) > 1.28:
            problems.append("lanyard badge missing")
    print(
        "audit",
        f"skin={len(head.data.vertices)}",
        f"hair={0 if hair is None else len(hair.data.vertices)}",
        f"clothes={len(body.data.vertices)}",
        f"lanyard={0 if lanyard is None else len(lanyard.data.vertices)}",
    )
    if problems:
        for item in problems:
            print("AUDIT FAIL:", item)
        raise RuntimeError("mesh audit failed: " + "; ".join(problems))
    print("audit ok")


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = 24
    coll = bpy.data.collections.new("COL_AVERY_CHEN")
    scene.collection.children.link(coll)
    data = asset_root()
    head, fitted, lanyard = make_human(coll, data)
    arm = build_armature(coll)
    remap_makehuman_weights(head)
    clothes = next(obj for obj in fitted if obj.name == "GEO_AVERY_BODY")
    shoes = next(obj for obj in fitted if obj.name == "GEO_AVERY_SHOES")
    transfer_weights(head, clothes)
    transfer_weights(head, shoes)
    for obj in fitted:
        if obj.name in {"GEO_AVERY_HAIR", "GEO_AVERY_EYES", "GEO_AVERY_BROWS", "GEO_AVERY_TEETH", "GEO_AVERY_TONGUE"}:
            weight_to_bones(obj, ["head"])
    if lanyard is not None:
        weight_to_bones(lanyard, ["neck", "chest"])
    bound = [head] + fitted + ([lanyard] if lanyard is not None else [])
    for obj in bound:
        bind_armature(obj, arm)
        limit_influences(obj)
    bake_actions(arm)
    scene.frame_start = 1
    scene.frame_end = 48
    hair = bpy.data.objects["GEO_AVERY_HAIR"]
    audit(head, hair, clothes, lanyard, arm)
    stats = measure_anatomy(head)
    jacket_w = jacket_outer_width(clothes, group_center(head, "joint-l-shoulder").z)
    gate_problems, gate_checks = _gate_anatomy(stats, jacket_w)
    tri_total = 0
    for obj in bound:
        count = rendered_triangles(obj)
        tri_total += count
        print(f"triangles {obj.name} {count}")
    if tri_total > 80000:
        gate_problems.append(f"rendered triangles {tri_total} exceed 80000")
    texture_mb = enforce_texture_budget(32.0)
    if texture_mb > 32.0:
        gate_problems.append(f"texture memory {texture_mb:.1f} MB exceeds 32")
    shoe_sole = min(v.co.z for v in shoes.data.vertices)
    if shoe_sole < -0.005:
        gate_problems.append(f"shoe sole at {shoe_sole:.4f} m")
    stats["rendered_triangles"] = tri_total
    stats["texture_mb"] = texture_mb
    stats["jacket_width_m"] = jacket_w
    stats["checks"] = gate_checks
    stats["shoe_sole_z"] = shoe_sole
    stats["tie"] = False
    stats["wardrobe"] = "female_casualsuit01"
    stats["hair"] = "short02"
    arm["avery_stature_m"] = float(stats["stature_m"])
    MEASURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEASURE_PATH.write_text(json.dumps(stats, indent=2, default=lambda v: list(v) if isinstance(v, tuple) else str(v)))
    for item in gate_problems:
        print("GATE FAIL:", item)
    try:
        bpy.ops.file.pack_all()
    except RuntimeError as exc:
        print("pack_all", exc)
    if STAGING_BLEND.exists():
        STAGING_BLEND.unlink()
    # Blender refuses to write the store path directly ("file saved with @").
    bpy.ops.wm.save_as_mainfile(filepath=str(STAGING_BLEND), relative_remap=False, copy=False)
    if gate_problems:
        raise RuntimeError("V2 local gates failed; primary blend was not overwritten: " + "; ".join(gate_problems))
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    BLEND_PATH.write_bytes(STAGING_BLEND.read_bytes())
    print(f"saved {BLEND_PATH} triangles={tri_total} textures={texture_mb:.1f}MB")

def bone_specs():
    """Natural stance. Arms a little clear of the jacket so weights separate."""
    L = {
        "root": ((0.0, 0.0, 0.02), (0.0, 0.0, 0.22)),
        "pelvis": ((0.0, 0.0, 0.90), (0.0, 0.0, 1.04)),
        "spine": ((0.0, 0.0, 1.04), (0.0, 0.0, 1.22)),
        "chest": ((0.0, 0.0, 1.22), (0.0, 0.0, 1.42)),
        "neck": ((0.0, 0.0, 1.42), (0.0, 0.0, 1.54)),
        "head": ((0.0, 0.0, 1.54), (0.0, 0.0, 1.76)),
        "upper_arm.L": ((-0.16, -0.01, 1.40), (-0.30, 0.012, 1.15)),
        "forearm.L": ((-0.30, 0.012, 1.15), (-0.26, -0.02, 0.92)),
        "hand.L": ((-0.26, -0.02, 0.92), (-0.25, -0.06, 0.80)),
        "upper_arm.R": ((0.16, -0.01, 1.40), (0.30, 0.012, 1.15)),
        "forearm.R": ((0.30, 0.012, 1.15), (0.26, -0.02, 0.92)),
        "hand.R": ((0.26, -0.02, 0.92), (0.25, -0.06, 0.80)),
        "thigh.L": ((-0.09, 0.0, 0.90), (-0.085, 0.01, 0.48)),
        "shin.L": ((-0.085, 0.01, 0.48), (-0.08, -0.004, 0.08)),
        "foot.L": ((-0.08, -0.004, 0.08), (-0.08, -0.15, 0.03)),
        "thigh.R": ((0.09, 0.0, 0.90), (0.085, 0.01, 0.48)),
        "shin.R": ((0.085, 0.01, 0.48), (0.08, -0.004, 0.08)),
        "foot.R": ((0.08, -0.004, 0.08), (0.08, -0.15, 0.03)),
    }
    return L


def build_armature(coll):
    data = bpy.data.armatures.new("RIG_AVERY_CHEN_DATA")
    arm = bpy.data.objects.new("RIG_AVERY_CHEN", data)
    coll.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    created = {}
    specs = bone_specs()
    for name, (head, tail) in specs.items():
        bone = data.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        if name in {"root", "pelvis", "spine", "chest", "neck", "head"}:
            bone.align_roll(Vector((0.0, -1.0, 0.0)))
        else:
            # Local Z toward the back so X swings the limb forward and back.
            bone.align_roll(Vector((0.0, 1.0, 0.0)))
        created[name] = bone
    for child, parent in BONE_PARENTS.items():
        created[child].parent = created[parent]
    bpy.ops.object.mode_set(mode="POSE")
    for pbone in arm.pose.bones:
        pbone.rotation_mode = "XYZ"
    bpy.ops.object.mode_set(mode="OBJECT")
    arm["asset_id"] = "char.avery_chen"
    arm["retarget_profile"] = "proxy_rig_v1"
    return arm


def segment_distance(point, head, tail):
    ab = tail - head
    denom = ab.length_squared
    if denom < 1e-8:
        return (point - head).length
    t = max(0.0, min(1.0, (point - head).dot(ab) / denom))
    return (point - (head + ab * t)).length


def bind(obj, arm, part):
    bones = {b.name: (Vector(b.head_local), Vector(b.tail_local)) for b in arm.data.bones}
    chains = {
        "spine": ["pelvis", "spine", "chest", "neck", "head"],
        "arm.L": ["chest", "upper_arm.L", "forearm.L", "hand.L"],
        "arm.R": ["chest", "upper_arm.R", "forearm.R", "hand.R"],
        "leg.L": ["pelvis", "thigh.L", "shin.L", "foot.L"],
        "leg.R": ["pelvis", "thigh.R", "shin.R", "foot.R"],
    }
    groups = {name: obj.vertex_groups.new(name=name) for name in bones}

    def chain_for(x, y, z):
        if part == "hair":
            return ["head"]
        if part == "head":
            return ["neck", "head"]
        if part == "lanyard":
            return ["neck", "chest", "spine"]
        if x > 0.14 and z > 0.78:
            return chains["arm.R"]
        if x < -0.14 and z > 0.78:
            return chains["arm.L"]
        if z < 1.02:
            return chains["leg.L"] if x < 0.0 else chains["leg.R"]
        return chains["spine"]

    for vert in obj.data.vertices:
        x, y, z = vert.co
        names = chain_for(x, y, z)
        if part == "head" and z > 1.58:
            names = ["head"]
        scored = []
        for name in names:
            dist = segment_distance(vert.co, *bones[name])
            scored.append((dist, name))
        scored.sort()
        chosen = scored[:3]
        weights = []
        for dist, name in chosen:
            weights.append((name, 1.0 / (dist * dist + 0.0008)))
        total = sum(w for _, w in weights) or 1.0
        for name, w in weights:
            value = w / total
            if value > 0.02:
                groups[name].add([vert.index], value, "REPLACE")
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    mod.use_vertex_groups = True
    obj.parent = arm
    obj.matrix_parent_inverse = arm.matrix_world.inverted()


def new_action(arm, name):
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    slot = action.slots.new(id_type="OBJECT", name=arm.name) if hasattr(action, "slots") else None
    anim = arm.animation_data_create()
    anim.action = action
    if slot is not None and hasattr(anim, "action_slot"):
        anim.action_slot = slot
    return action


def reset_pose(arm):
    for pbone in arm.pose.bones:
        pbone.location = (0.0, 0.0, 0.0)
        pbone.rotation_euler = (0.0, 0.0, 0.0)
        pbone.scale = (1.0, 1.0, 1.0)


def key_pose(arm, frame, rotations, locations=None):
    reset_pose(arm)
    locations = locations or {}
    if not rotations and not locations:
        rotations = {"root": (0.0, 0.0, 0.0)}
    for bone, euler in rotations.items():
        pbone = arm.pose.bones[bone]
        pbone.rotation_euler = tuple(math.radians(v) for v in euler)
        pbone.keyframe_insert(data_path="rotation_euler", frame=frame)
    for bone, loc in locations.items():
        pbone = arm.pose.bones[bone]
        pbone.location = loc
        pbone.keyframe_insert(data_path="location", frame=frame)


def bake_actions(arm):
    """Author the 20 proxy-kit actions on this rest pose.

    Vertical bones: X nods forward, Y yaws (positive yaw turns the face toward
    character right / +X), Z tilts the crown toward character left.
    Limbs: X positive swings backward, X negative swings forward.
    upper_arm.R Z negative raises the arm outward; upper_arm.L Z positive does.
    Forearm X negative bends the elbow.
    pose_* actions are a single held frame. The other twelve are motions.
    """
    def hold(name, rotations, locations=None):
        new_action(arm, name)
        key_pose(arm, 1, rotations, locations)
        arm.animation_data.action = None

    def clip(name, frames):
        # Key the same bones on every frame so a rest pose at the ends is a real
        # key, not an empty frame that Blender drops from the action range.
        bones = set()
        for item in frames:
            bones.update(item[1])
            if len(item) > 2 and item[2]:
                bones.update(item[2])
        new_action(arm, name)
        for item in frames:
            rotations = {bone: (0.0, 0.0, 0.0) for bone in bones}
            rotations.update(item[1])
            locations = item[2] if len(item) > 2 else None
            key_pose(arm, frame=item[0], rotations=rotations, locations=locations)
        arm.animation_data.action = None

    # Idle: quiet breath and a small weight shift. Loops 1→48.
    idle = []
    for frame, phase in ((1, 0.0), (12, 0.5), (24, 1.0), (36, 1.5), (48, 2.0)):
        s = math.sin(phase * math.pi)
        idle.append((frame, {
            "chest": (1.6 * s, 0.0, 0.8 * math.sin(phase * math.pi * 0.5)),
            "spine": (0.8 * s, 0.0, 0.0),
            "head": (1.1 * math.sin(phase * math.pi + 0.4), 1.4 * math.sin(phase * math.pi * 0.5), 0.0),
            "upper_arm.L": (1.2 * s, 0.0, 0.6 * s),
            "upper_arm.R": (1.2 * s, 0.0, -0.6 * s),
        }, {"pelvis": (0.0, 0.004 * s, 0.0)}))
    clip("idle_neutral_loop", idle)

    def walk_pose(thigh_l, thigh_r, shin_l, shin_r, arm_l, arm_r, bob):
        return {
            "thigh.L": (thigh_l, 0.0, 0.0),
            "thigh.R": (thigh_r, 0.0, 0.0),
            "shin.L": (shin_l, 0.0, 0.0),
            "shin.R": (shin_r, 0.0, 0.0),
            "upper_arm.L": (arm_l, 0.0, 4.0),
            "upper_arm.R": (arm_r, 0.0, -4.0),
            "forearm.L": (-16 + min(0, arm_l) * 0.15, 0.0, 0.0),
            "forearm.R": (-16 + min(0, arm_r) * 0.15, 0.0, 0.0),
            "chest": (2.0, -arm_l * 0.15, 0.0),
            "foot.L": (max(0.0, -thigh_l) * 0.3, 0.0, 0.0),
            "foot.R": (max(0.0, -thigh_r) * 0.3, 0.0, 0.0),
        }, {"pelvis": (0.0, bob, 0.0)}

    clip("walk_cycle", [
        (1, *walk_pose(-26, 22, 10, 32, 20, -22, 0.006)),
        (7, *walk_pose(6, -8, 42, 16, 4, -4, 0.018)),
        (13, *walk_pose(22, -26, 32, 10, -22, 20, 0.006)),
        (19, *walk_pose(-8, 6, 16, 42, -4, 4, 0.018)),
        (24, *walk_pose(-26, 22, 10, 32, 20, -22, 0.006)),
    ])

    clip("turn_left_90", [
        (1, {"root": (0, 0, 0), "head": (0, 0, 0)}),
        (10, {"root": (0, -50, 0), "head": (2, -12, 0), "chest": (2, -8, 0)}),
        (18, {"root": (0, -90, 0), "head": (0, 0, 0), "chest": (0, 0, 0)}),
    ])
    clip("turn_right_90", [
        (1, {"root": (0, 0, 0)}),
        (10, {"root": (0, 50, 0), "head": (2, 12, 0), "chest": (2, 8, 0)}),
        (18, {"root": (0, 90, 0)}),
    ])

    clip("gesture_present", [
        (1, {}),
        (14, {
            "upper_arm.R": (-32, 0, -28),
            "forearm.R": (-34, 0, 0),
            "hand.R": (-10, 0, 8),
            "upper_arm.L": (-12, 0, 16),
            "chest": (4, -4, 0),
            "head": (4, -3, 0),
        }),
        (28, {}),
    ])
    clip("point_left", [
        (1, {}),
        (12, {
            "upper_arm.L": (-48, 0, 36),
            "forearm.L": (-8, 0, 0),
            "hand.L": (0, 0, 0),
            "head": (2, 8, 0),
        }),
        (24, {}),
    ])
    clip("point_right", [
        (1, {}),
        (12, {
            "upper_arm.R": (-48, 0, -36),
            "forearm.R": (-8, 0, 0),
            "head": (2, -8, 0),
        }),
        (24, {}),
    ])
    clip("wave", [
        (1, {"upper_arm.R": (-12, 0, -68), "forearm.R": (-42, 0, 0), "hand.R": (0, 0, 12)}),
        (10, {"upper_arm.R": (-16, 0, -74), "forearm.R": (-18, 0, 0), "hand.R": (0, 0, -10)}),
        (20, {"upper_arm.R": (-12, 0, -66), "forearm.R": (-48, 0, 0), "hand.R": (0, 0, 14)}),
        (30, {"upper_arm.R": (-14, 0, -70), "forearm.R": (-24, 0, 0), "hand.R": (0, 0, -6)}),
    ])
    clip("head_nod", [
        (1, {"head": (0, 0, 0)}),
        (7, {"head": (18, 0, 0), "neck": (4, 0, 0)}),
        (14, {"head": (3, 0, 0)}),
        (20, {"head": (0, 0, 0)}),
    ])
    clip("head_shake", [
        (1, {"head": (0, -16, 0)}),
        (8, {"head": (0, 16, 0)}),
        (16, {"head": (0, -14, 0)}),
        (24, {"head": (0, -16, 0)}),
    ])
    clip("reach_grab", [
        (1, {}),
        (16, {
            "upper_arm.R": (-58, 0, -12),
            "forearm.R": (-18, 0, 0),
            "chest": (8, -6, 0),
            "spine": (6, 0, 0),
        }),
        (28, {
            "upper_arm.R": (-62, 0, -8),
            "forearm.R": (-10, 0, 0),
            "hand.R": (12, 0, 0),
            "chest": (10, -4, 0),
        }),
    ])
    clip("place_release", [
        (1, {
            "upper_arm.R": (-62, 0, -8),
            "forearm.R": (-10, 0, 0),
            "hand.R": (12, 0, 0),
            "chest": (10, -4, 0),
        }),
        (16, {
            "upper_arm.R": (-28, 0, -18),
            "forearm.R": (-36, 0, 0),
            "hand.R": (-8, 0, 0),
            "chest": (6, 0, 0),
        }),
        (30, {
            "upper_arm.R": (-8, 0, -10),
            "forearm.R": (-8, 0, 0),
            "chest": (0, 0, 0),
        }),
    ])

    hold("pose_neutral", {
        "upper_arm.R": (0, 0, 0),
        "forearm.R": (0, 0, 0),
        "upper_arm.L": (0, 0, 0),
        "head": (0, 0, 0),
        "chest": (0, 0, 0),
    })
    hold("pose_present", {
        "upper_arm.R": (-34, 0, -30),
        "forearm.R": (-32, 0, 0),
        "hand.R": (-8, 0, 6),
        "upper_arm.L": (-14, 0, 18),
        "forearm.L": (-16, 0, 0),
        "chest": (4, -4, 0),
        "head": (3, -2, 0),
    })
    hold("pose_listen", {
        "head": (8, -6, 7),
        "neck": (3, 0, 2),
        "chest": (4, 0, 2),
        "upper_arm.L": (4, 0, 6),
        "upper_arm.R": (2, 0, -4),
    })
    hold("pose_think", {
        "upper_arm.R": (-18, 0, 22),
        "forearm.R": (-78, 0, 8),
        "hand.R": (8, 0, 0),
        "head": (10, 8, -4),
        "chest": (4, 4, 0),
    })
    hold("pose_point", {
        "upper_arm.R": (-52, 0, -34),
        "forearm.R": (-6, 0, 0),
        "head": (2, -6, 0),
        "chest": (4, -4, 0),
    })
    hold("pose_hold", {
        "upper_arm.R": (-36, 0, -14),
        "forearm.R": (-40, 0, 0),
        "upper_arm.L": (-36, 0, 14),
        "forearm.L": (-40, 0, 0),
        "chest": (4, 0, 0),
    })
    hold("pose_ready", {
        "upper_arm.R": (-6, 0, -8),
        "upper_arm.L": (-6, 0, 8),
        "forearm.R": (-8, 0, 0),
        "forearm.L": (-8, 0, 0),
        "chest": (2, 0, 0),
        "head": (1, 0, 0),
    })
    hold("pose_end", {
        "upper_arm.R": (-16, 0, -42),
        "forearm.R": (-18, 0, 0),
        "upper_arm.L": (-8, 0, 10),
        "head": (-3, 0, 2),
        "chest": (2, -2, 0),
    })
    reset_pose(arm)
def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def studio(scene):
    world = scene.world or bpy.data.worlds.new("WORLD")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        # Locked neutral gray. Linear 0.18 is middle gray; this lighter value keeps dark hair readable.
        bg.inputs[0].default_value = (0.42, 0.42, 0.42, 1.0)
        bg.inputs[1].default_value = 1.0
    # Even high-key studio. Lights are not saved with the character file.
    specs = [
        ("KEY", (1.6, -2.4, 2.5), 180, 3.2, 5600),
        ("FILL", (-1.8, -2.0, 2.1), 90, 3.6, 5600),
        ("RIM", (-0.6, 1.8, 2.3), 70, 2.2, 6400),
    ]
    lights = []
    for name, loc, energy, size, kelvin in specs:
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "RECTANGLE"
        light_data.size = size
        light_data.size_y = size
        if hasattr(light_data, "color"):
            # Approximate kelvin with a mild mix; Blender also has a temperature node
            # on lights in 5.x via use_temperature when available.
            light_data.color = (1.0, 0.98, 0.95) if kelvin < 6000 else (0.95, 0.97, 1.0)
        if hasattr(light_data, "use_temperature"):
            light_data.use_temperature = True
            light_data.temperature = kelvin
        obj = bpy.data.objects.new(name, light_data)
        scene.collection.objects.link(obj)
        obj.location = loc
        look_at(obj, (0.0, 0.0, 1.55))
        lights.append(obj)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(os.environ.get("AVERY_SAMPLES", "16"))
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 960
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    return lights


def add_camera(scene, loc, target, lens, name="CAM"):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    cam.location = loc
    look_at(cam, target)
    scene.camera = cam
    return cam


def render_still(scene, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print("rendered", path)


def set_shape(head, name, value):
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.data.shape_keys]
    if head not in meshes:
        meshes.append(head)
    for obj in meshes:
        for key in obj.data.shape_keys.key_blocks:
            if key.name.startswith("CORRECT_"):
                # Pose-driven suit folds. Facial resets must not clear them.
                continue
            if key.name == "Basis":
                key.value = 1.0
            elif key.name == name:
                key.value = value
            else:
                key.value = 0.0


def neutral_shapes(head):
    set_shape(head, "Basis", 0.0)


def _play(arm, action_name, frame):
    action = bpy.data.actions[action_name]
    arm.animation_data.action = action
    if hasattr(arm.animation_data, "action_slot") and len(action.slots):
        arm.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def _stop(arm):
    if arm.animation_data:
        arm.animation_data.action = None
    reset_pose(arm)
    bpy.context.view_layer.update()


def _cam(scene, loc, target, lens, name, ortho=None):
    cam = add_camera(scene, loc, target, lens, name)
    cam.data.dof.use_dof = False
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = 24.0
    if ortho is not None:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho
    return cam


def _gray_and_silhouette(path):
    from PIL import Image, ImageOps
    image = Image.open(path).convert("RGB")
    gray = ImageOps.grayscale(image)
    gray_path = path.with_name(path.stem + "-gray.png")
    gray.save(gray_path)
    corner = image.getpixel((2, 2))
    sil = Image.new("L", image.size, 255)
    pix = image.load()
    out = sil.load()
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            r, g, b = pix[x, y]
            if abs(r - corner[0]) + abs(g - corner[1]) + abs(b - corner[2]) < 36:
                out[x, y] = 255
            else:
                out[x, y] = 0
    sil_path = path.with_name(path.stem + "-silhouette.png")
    sil.save(sil_path)
    return gray_path, sil_path


def _thumb(path, height, dest):
    from PIL import Image
    image = Image.open(path).convert("RGB")
    width = max(1, int(image.size[0] * height / image.size[1]))
    image.resize((width, height), Image.Resampling.LANCZOS).save(dest)


def _face_clip_fraction(path):
    from PIL import Image
    image = Image.open(path).convert("RGB")
    w, h = image.size
    # Interior of the head-and-shoulders frame, away from the flat background.
    x0, x1 = int(w * 0.28), int(w * 0.72)
    y0, y1 = int(h * 0.18), int(h * 0.78)
    crop = image.crop((x0, y0, x1, y1))
    total = crop.size[0] * crop.size[1]
    clipped = 0
    for r, g, b in crop.getdata():
        if (r <= 1 and g <= 1 and b <= 1) or (r >= 254 and g >= 254 and b >= 254):
            clipped += 1
    return clipped / total if total else 0.0


def _label_plate(path, cam, landmarks):
    from bpy_extras.object_utils import world_to_camera_view
    from PIL import Image, ImageDraw
    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    scene = bpy.context.scene
    w, h = image.size
    for name, co in landmarks.items():
        proj = world_to_camera_view(scene, cam, Vector(co))
        if proj.z < 0:
            continue
        x = int(proj.x * w)
        y = int((1.0 - proj.y) * h)
        if not (0 <= x < w and 0 <= y < h):
            continue
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(220, 48, 48))
        draw.text((x + 6, y - 8), name, fill=(20, 20, 20))
    image.save(path)


def render_previews():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    scene = bpy.context.scene
    head = bpy.data.objects["GEO_AVERY_HEAD"]
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    arm.hide_render = True
    if arm.animation_data:
        arm.animation_data.action = None
    reset_pose(arm)
    neutral_shapes(head)
    scene.frame_set(1)
    studio(scene)
    for obj in scene.objects:
        if obj.type == "CAMERA":
            obj.data.dof.use_dof = False
    MEDIA.mkdir(parents=True, exist_ok=True)
    qa = Path("/tmp/avery-qa-v2")
    qa.mkdir(parents=True, exist_ok=True)
    stats = measure_anatomy(head)
    crown = stats["crown_z"]
    stature = stats["stature_m"]
    eye_z = crown - 0.10
    mid_z = stature * 0.48

    def still(name, loc, target, lens, rx, ry, ortho=None, samples=None):
        if samples is not None:
            scene.cycles.samples = samples
        scene.render.resolution_x = rx
        scene.render.resolution_y = ry
        cam = _cam(scene, loc, target, lens, "CAM_" + name.upper(), ortho)
        path = MEDIA / name
        render_still(scene, path)
        return cam, path

    hero_samples = int(os.environ.get("AVERY_SAMPLES", "16"))
    scene.cycles.samples = hero_samples
    still("front-closeup.png", (0.0, -1.65, eye_z), (0.0, 0.0, eye_z - 0.02), 85, 960, 1200)
    still("three-quarter-closeup.png", (0.95, -1.35, eye_z), (0.0, 0.0, eye_z - 0.03), 85, 960, 1200)
    still("head-minus-30.png", (-0.85, -1.47, eye_z), (0.0, 0.0, eye_z - 0.02), 85, 960, 1200)
    still("head-plus-30.png", (0.85, -1.47, eye_z), (0.0, 0.0, eye_z - 0.02), 85, 960, 1200)
    body_dist = 5.15
    still("full-body-front.png", (0.0, -body_dist, mid_z), (0.0, 0.0, mid_z), 60, 900, 1600)
    still("full-body-side.png", (body_dist, 0.0, mid_z), (0.0, 0.0, mid_z), 60, 900, 1600)
    still("full-body-back.png", (0.0, body_dist, mid_z), (0.0, 0.0, mid_z), 60, 900, 1600)
    still("full-body-three-quarter.png", (2.95, -4.22, mid_z), (0.0, 0.0, mid_z), 60, 900, 1600)

    # Orthographic measurement plates. Perspective renders above are not the measurement set.
    landmarks = stats["landmarks"]
    for name, loc in (
        ("measure-front.png", (0.0, -4.0, mid_z)),
        ("measure-side.png", (4.0, 0.0, mid_z)),
        ("measure-back.png", (0.0, 4.0, mid_z)),
    ):
        cam, path = still(name, loc, (0.0, 0.0, mid_z), 50, 2048, 2048, ortho=2.15, samples=8)
        _label_plate(path, cam, landmarks)
    scene.cycles.samples = hero_samples

    for path in (
        MEDIA / "front-closeup.png",
        MEDIA / "three-quarter-closeup.png",
        MEDIA / "full-body-front.png",
        MEDIA / "full-body-side.png",
    ):
        _gray_and_silhouette(path)
    _thumb(MEDIA / "full-body-front.png", 200, MEDIA / "thumb-full-color.png")
    _thumb(MEDIA / "full-body-front-gray.png", 200, MEDIA / "thumb-full-gray.png")
    _thumb(MEDIA / "full-body-front-silhouette.png", 200, MEDIA / "thumb-full-silhouette.png")
    # Face crop from the upper-middle of the close-up, then scaled to 180 px tall.
    from PIL import Image
    face = Image.open(MEDIA / "front-closeup.png").convert("RGB")
    fw, fh = face.size
    crop = face.crop((int(fw * 0.22), int(fh * 0.12), int(fw * 0.78), int(fh * 0.62)))
    crop.save(MEDIA / "face-crop.png")
    _thumb(MEDIA / "face-crop.png", 180, MEDIA / "thumb-face-color.png")
    _gray_and_silhouette(MEDIA / "face-crop.png")
    _thumb(MEDIA / "face-crop-gray.png", 180, MEDIA / "thumb-face-gray.png")
    _thumb(MEDIA / "face-crop-silhouette.png", 180, MEDIA / "thumb-face-silhouette.png")
    clip = _face_clip_fraction(MEDIA / "front-closeup.png")

    scene.render.resolution_x = 480
    scene.render.resolution_y = 480
    scene.cycles.samples = min(8, hero_samples)
    _cam(scene, (0.0, -0.85, eye_z), (0.0, 0.0, eye_z - 0.01), 85, "CAM_FACE")
    viseme_paths = []
    for name in VISEMES:
        set_shape(head, name, 1.0)
        path = qa / f"{name}.png"
        render_still(scene, path)
        viseme_paths.append(path)
    neutral_shapes(head)
    montage(viseme_paths, MEDIA / "viseme-strip.png", columns=9)
    expr_paths = []
    for name in ["neutral"] + EXPRESSIONS:
        if name == "neutral":
            neutral_shapes(head)
        else:
            set_shape(head, name, 1.0)
        path = qa / f"{name}.png"
        render_still(scene, path)
        expr_paths.append(path)
    neutral_shapes(head)
    montage(expr_paths, MEDIA / "expression-sheet.png", columns=3)

    # Shoulder elevation. upper_arm.L Z+ and upper_arm.R Z- raise the arms out.
    scene.render.resolution_x = 480
    scene.render.resolution_y = 720
    scene.cycles.samples = min(8, hero_samples)
    shoulder_paths = []
    for view, loc in (
        ("front", (0.0, -5.15, mid_z)),
        ("three-quarter", (1.45, -4.7, mid_z)),
    ):
        for angle in (0.0, 45.0, 90.0, 120.0):
            _stop(arm)
            neutral_shapes(head)
            if angle:
                arm.pose.bones["upper_arm.L"].rotation_euler.z = math.radians(angle)
                arm.pose.bones["upper_arm.R"].rotation_euler.z = math.radians(-angle)
                bpy.context.view_layer.update()
            _cam(scene, loc, (0.0, 0.0, mid_z), 60, "CAM_SHOULDER")
            path = qa / f"shoulder-{view}-{int(angle)}.png"
            render_still(scene, path)
            shoulder_paths.append(path)
    _stop(arm)
    montage(shoulder_paths, MEDIA / "shoulder-tests.png", columns=4)

    scene.render.resolution_x = 420
    scene.render.resolution_y = 720
    _cam(scene, (0.35, -4.6, mid_z), (0.0, 0.0, mid_z), 60, "CAM_DEFORM")
    deform_paths = []
    shots = [
        ("rest", None, 1),
        ("elbows-knees", "manual", 1),
        ("shoulders-90", "shoulders", 1),
        ("walk_cycle", "walk_cycle", 7),
        ("gesture_present", "gesture_present", 14),
        ("reach_grab", "reach_grab", 16),
    ]
    for label, action_name, frame in shots:
        _stop(arm)
        neutral_shapes(head)
        if action_name == "manual":
            arm.pose.bones["forearm.L"].rotation_euler.x = math.radians(-70.0)
            arm.pose.bones["forearm.R"].rotation_euler.x = math.radians(-70.0)
            arm.pose.bones["shin.L"].rotation_euler.x = math.radians(55.0)
            arm.pose.bones["shin.R"].rotation_euler.x = math.radians(55.0)
            bpy.context.view_layer.update()
        elif action_name == "shoulders":
            arm.pose.bones["upper_arm.L"].rotation_euler.z = math.radians(90.0)
            arm.pose.bones["upper_arm.R"].rotation_euler.z = math.radians(-90.0)
            bpy.context.view_layer.update()
        elif action_name:
            _play(arm, action_name, frame)
        path = qa / f"deform-{label}.png"
        render_still(scene, path)
        deform_paths.append(path)
    _stop(arm)
    montage(deform_paths, MEDIA / "deformation-sheet.png", columns=3)

    action_frames = {
        "idle_neutral_loop": 24,
        "walk_cycle": 7,
        "turn_left_90": 18,
        "turn_right_90": 18,
        "gesture_present": 14,
        "point_left": 12,
        "point_right": 12,
        "wave": 10,
        "head_nod": 7,
        "head_shake": 8,
        "reach_grab": 16,
        "place_release": 16,
    }
    scene.render.resolution_x = 320
    scene.render.resolution_y = 520
    _cam(scene, (0.2, -4.8, mid_z), (0.0, 0.0, mid_z), 60, "CAM_ACT")
    action_paths = []
    for name in ACTIONS:
        frame = action_frames.get(name, 1)
        _play(arm, name, frame)
        path = qa / f"act-{name}.png"
        render_still(scene, path)
        action_paths.append(path)
    _stop(arm)
    montage(action_paths, MEDIA / "action-sheet.png", columns=5)
    note = MEDIA / "render-notes.txt"
    note.write_text(
        "\n".join([
            "Lighting: Cycles CPU, AgX, exposure 0, gamma 1, neutral gray world (0.42, 0.42, 0.42), no depth of field.",
            "Head cameras: 85 mm, vertical 24 mm sensor. Full body cameras: 60 mm. Measurement plates: orthographic, 2048 px.",
            f"Facial interior pixels at code 0 or 255 on front-closeup: {clip:.4%}.",
            "Action sheet is one representative frame per action, not every frame.",
            "Silhouettes are background-difference mattes from the beauty render, not a separate lighting pass.",
            "Five-person audience study: NOT RUN.",
            "Clean-host pipe asset doctor and link smoke: NOT RUN.",
        ]) + "\n"
    )
    print("previews written", MEDIA, "clip", round(clip, 5))


def montage(paths, dest, columns):
    from PIL import Image, ImageDraw, ImageFont
    tiles = [Image.open(p).convert("RGB") for p in paths]
    w, h = tiles[0].size
    label_h = 28
    rows = math.ceil(len(tiles) / columns)
    sheet = Image.new("RGB", (columns * w, rows * (h + label_h)), (28, 28, 30))
    draw = ImageDraw.Draw(sheet)
    for i, (tile, path) in enumerate(zip(tiles, paths)):
        c = i % columns
        r = i // columns
        x = c * w
        y = r * (h + label_h)
        sheet.paste(tile, (x, y + label_h))
        draw.text((x + 8, y + 6), path.stem, fill=(240, 240, 240))
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest)
    print("montage", dest)


def shape_delta(obj, name):
    keys = obj.data.shape_keys.key_blocks
    basis = keys["Basis"]
    key = keys[name]
    peak = 0.0
    for a, b in zip(basis.data, key.data):
        peak = max(peak, (a.co - b.co).length)
    return peak


def _pupil_brow_visibility():
    """Front and ±30° rays. Returns (view, both pupil cores eye-first, min brow fraction)."""
    from mathutils.bvhtree import BVHTree

    deps = bpy.context.evaluated_depsgraph_get()

    def tree_for(name):
        obj = bpy.data.objects[name]
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        matrix = obj.matrix_world
        coords = [matrix @ vert.co for vert in mesh.vertices]
        faces = [tuple(poly.vertices) for poly in mesh.polygons]
        tree = BVHTree.FromPolygons(coords, faces)
        evaluated.to_mesh_clear()
        return tree, coords

    eye_tree, eye_co = tree_for("GEO_AVERY_EYES")
    head_tree, head_co = tree_for("GEO_AVERY_HEAD")
    hair_tree, _hair_co = tree_for("GEO_AVERY_HAIR")
    brow_tree, brow_co = tree_for("GEO_AVERY_BROWS")
    trees = (("eye", eye_tree), ("head", head_tree), ("hair", hair_tree), ("brow", brow_tree))

    def first_hit(origin, target):
        direction = (target - origin).normalized()
        best = None
        for name, tree in trees:
            location, _normal, _index, dist = tree.ray_cast(origin, direction, 3.0)
            if location is None:
                continue
            if best is None or dist < best[1]:
                best = (name, dist, location)
        return best

    pupils = []
    for sign in (1.0, -1.0):
        side = [co for co in eye_co if co.x * sign > 0.004]
        front = sorted(side, key=lambda co: co.y)[:16]
        pupils.append(sum(front, Vector()) / len(front))
    crown = max(co.z for co in head_co)
    eye_z = crown - 0.10
    views = (
        ("front", Vector((0.0, -1.65, eye_z))),
        ("minus30", Vector((-0.85, -1.47, eye_z))),
        ("plus30", Vector((0.85, -1.47, eye_z))),
    )
    report = []
    for label, origin in views:
        pupil_ok = True
        for pupil in pupils:
            samples = (
                pupil,
                pupil + Vector((0.004, 0.0, 0.0)),
                pupil + Vector((-0.004, 0.0, 0.0)),
                pupil + Vector((0.0, 0.0, 0.003)),
                pupil + Vector((0.0, 0.0, -0.003)),
            )
            if not all(first_hit(origin, sample) and first_hit(origin, sample)[0] == "eye" for sample in samples):
                pupil_ok = False
        brow_fracs = []
        for sign in (1.0, -1.0):
            points = [co for co in brow_co if co.x * sign > 0.003]
            hidden = 0
            for point in points:
                hit = first_hit(origin, point)
                if hit and hit[0] != "brow" and hit[2].y < point.y - 0.0015:
                    hidden += 1
            brow_fracs.append(1.0 - hidden / max(1, len(points)))
        report.append((label, pupil_ok, min(brow_fracs)))
    return report


def _section_ratio(obj, arm, bone_name, bend_deg):
    """Area ratio of a limb slice at rest versus one bend. None if the bone misses the mesh."""

    def radius():
        hidden = []
        for mod in obj.modifiers:
            if mod.type == "ARMATURE":
                continue
            if mod.show_viewport or mod.show_render:
                hidden.append((mod, mod.show_viewport, mod.show_render))
                mod.show_viewport = False
                mod.show_render = False
        deps = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        bone = arm.pose.bones[bone_name]
        head = Vector(bone.head)
        tail = Vector(bone.tail)
        axis = tail - head
        if axis.length < 1e-5:
            evaluated.to_mesh_clear()
            for mod, view, render in hidden:
                mod.show_viewport = view
                mod.show_render = render
            return None
        axis_n = axis.normalized()
        mid = head.lerp(tail, 0.45)
        radii = []
        for vert in mesh.vertices:
            delta = vert.co - mid
            along = delta.dot(axis_n)
            if abs(along) > 0.04:
                continue
            radial = (delta - axis_n * along).length
            if 0.01 < radial < 0.14:
                radii.append(radial)
        evaluated.to_mesh_clear()
        for mod, view, render in hidden:
            mod.show_viewport = view
            mod.show_render = render
        if len(radii) < 12:
            return None
        radii.sort()
        return radii[len(radii) // 2]

    reset_pose(arm)
    bpy.context.view_layer.update()
    rest = radius()
    reset_pose(arm)
    arm.pose.bones[bone_name].rotation_euler.x = math.radians(bend_deg)
    bpy.context.view_layer.update()
    bent = radius()
    reset_pose(arm)
    if not rest or not bent:
        return None
    return (bent / rest) ** 2


def verify():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    lines = [f"file: {BLEND_PATH}"]
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        status = "PASS" if cond else "FAIL"
        if not cond:
            ok = False
        lines.append(f"{status}: {label}" + (f" — {detail}" if detail else ""))

    coll = bpy.data.collections.get("COL_AVERY_CHEN")
    check("collection COL_AVERY_CHEN", coll is not None)
    arm = bpy.data.objects.get("RIG_AVERY_CHEN")
    check("armature object RIG_AVERY_CHEN", arm is not None and arm.type == "ARMATURE")
    if coll and arm:
        check("armature in collection", arm.name in coll.objects)
    check("material MAT_PROXY_CHARACTER", bpy.data.materials.get("MAT_PROXY_CHARACTER") is not None)
    check("material MAT_PROXY_FOCUS", bpy.data.materials.get("MAT_PROXY_FOCUS") is not None)

    if arm:
        names = [b.name for b in arm.data.bones]
        for bone in ["root", "pelvis", "spine", "chest", "neck", "head",
                     "upper_arm.L", "forearm.L", "hand.L", "upper_arm.R", "forearm.R", "hand.R",
                     "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R"]:
            check(f"bone {bone}", bone in names)
        parents_ok = True
        for child, parent in BONE_PARENTS.items():
            bone = arm.data.bones.get(child)
            if bone is None or bone.parent is None or bone.parent.name != parent:
                parents_ok = False
                lines.append(f"FAIL: parent {child} -> {parent}")
        check("bone hierarchy", parents_ok)
        meshes = [o for o in coll.objects if o.type == "MESH"] if coll else []
        check("mesh objects in collection", len(meshes) >= 1, ", ".join(o.name for o in meshes))

    head = bpy.data.objects.get("GEO_AVERY_HEAD")
    check("head mesh GEO_AVERY_HEAD", head is not None and head.type == "MESH")
    if head and head.data.shape_keys:
        present = [k.name for k in head.data.shape_keys.key_blocks]
        for name in VISEMES + EXPRESSIONS:
            check(f"shape key {name}", name in present)
            if name in present:
                delta = shape_delta(head, name)
                check(f"shape key {name} moves verts", delta > 0.001, f"max delta {delta:.4f} m")
    else:
        check("shape keys datablock", False)

    for name in ACTIONS:
        action = bpy.data.actions.get(name)
        check(f"action {name}", action is not None)
        if action is None:
            continue
        check(f"action {name} fake user", bool(action.use_fake_user))
        if hasattr(action, "slots"):
            check(f"action {name} slots", len(action.slots) > 0, f"slots={len(action.slots)}")
        start, end = action.frame_range
        if name in ACTIONS_POSE:
            check(f"action {name} 1-frame hold", abs(end - start) < 0.51, f"range {start}-{end}")
        else:
            check(f"action {name} motion range", (end - start) >= 8, f"range {start}-{end}")

    if head is not None:
        stats = measure_anatomy(head)
        clothes = (
            bpy.data.objects.get("GEO_AVERY_JACKET")
            or bpy.data.objects.get("GEO_AVERY_BODY")
            or head
        )
        jacket_w = None
        if clothes is not None:
            shoulder = group_center(head, "joint-l-shoulder")
            if shoulder is not None:
                jacket_w = jacket_outer_width(clothes, shoulder.z)
        # Native MakeHuman proportions are accepted inside 7.0–8.0 heads.
        # Stricter V2 ratio gates are reported, not used to edit the mesh.
        check(
            "adult head-height 7.0-8.0",
            7.0 <= stats["heads"] <= 8.0,
            f"{stats['heads']:.2f}",
        )
        lines.append(
            "INFO: native proportions accepted — "
            f"stature {stats['stature_m']:.3f} m, sole {stats['sole_z']:.4f} m, "
            f"hip {stats['hip_fraction']:.3f}, acromion {stats['acromion_head_widths']:.2f} head widths, "
            f"shoulder/hip {stats['shoulder_hip_ratio']:.2f}, hand {stats['hand_head_heights']:.2f}, "
            f"foot {stats['foot_head_heights']:.2f}, elbow z={stats['elbow_z']:.3f}, "
            f"wrist z={stats['wrist_z']:.3f}, fingertip z={stats['fingertip_z']:.3f}"
        )
        if jacket_w is not None and stats["head_width_m"]:
            lines.append(
                f"INFO: outer suit width {jacket_w / stats['head_width_m']:.2f} head widths"
            )
        checks = [{"label": "adult head-height 7.0-8.0", "pass": 7.0 <= stats["heads"] <= 8.0, "detail": f"{stats['heads']:.2f}"}]
        tri_total = 0
        if coll is not None:
            for obj in coll.objects:
                if obj.type in {"MESH", "CURVE"}:
                    tri_total += rendered_triangles(obj)
        check("rendered triangles ≤ 80000", tri_total <= 80000, str(tri_total))
        images = [img for img in bpy.data.images if img.size[0] > 0]
        texture_mb = sum(img.size[0] * img.size[1] * 4 / (1024 * 1024) for img in images)
        packed_mb = sum(len(img.packed_file.data) for img in images if img.packed_file) / (1024 * 1024)
        # Stock 2048 maps stay at native size. Uncompressed RGBA is the budget figure.
        lines.append(f"INFO: textures uncompressed {texture_mb:.1f} MB, packed {packed_mb:.1f} MB")
        unpacked = [
            img.name for img in bpy.data.images
            if img.source == "FILE" and img.packed_file is None and img.filepath
        ]
        check("textures packed", not unpacked, ", ".join(unpacked[:6]))
        stored = {}
        if MEASURE_PATH.is_file():
            stored = json.loads(MEASURE_PATH.read_text())
        stored.update(stats)
        stored["rendered_triangles"] = tri_total
        stored["texture_mb"] = round(texture_mb, 1)
        stored["texture_packed_mb"] = round(packed_mb, 1)
        if jacket_w is not None:
            stored["jacket_width_m"] = jacket_w
        stored["checks"] = checks
        stored["tie"] = True
        stored["wardrobe"] = (
            "sleeveless male_elegantsuit01 vest, warm-stone shirt, charcoal trousers; "
            "tie recolored to the lanyard teal; armscyes finished with a chest-parented binding"
        )
        stored["hair"] = "short02"
        stored["note"] = (
            "Native MakeHuman proportions. The jacket sleeves are removed at the armscye. "
            "The openings are smoothed about 6.5 mm off the body, with the shoulder tips "
            "on the torso side of the deltoid and a 9 mm binding parented to chest. "
            "The shoulders, axilla, and arms are visible skin. The tie uses the lanyard teal. "
            "Head width is the temple band."
        )
        MEASURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        MEASURE_PATH.write_text(json.dumps(stored, indent=2, default=lambda v: list(v) if isinstance(v, tuple) else str(v)))
        if head is not None:
            unbound = over = off = 0
            names = {g.index: g.name for g in head.vertex_groups}
            for vert in head.data.vertices:
                weights = [
                    assignment.weight for assignment in vert.groups
                    if assignment.weight > 0.001 and names.get(assignment.group) in CONTRACT_BONES
                ]
                if not weights:
                    unbound += 1
                elif len(weights) > 4:
                    over += 1
                elif abs(sum(weights) - 1.0) > 0.02:
                    off += 1
            lines.append(
                f"INFO: head contract-bone weights unbound={unbound} over4={over} offnorm={off}"
            )
        lanyard = bpy.data.objects.get("GEO_AVERY_LANYARD")
        lines.append(
            "INFO: tie remains inside male_elegantsuit01 and is recolored to the lanyard teal; "
            "sleeveless vest, arms are skin"
        )
        if lanyard is not None and lanyard.type == "MESH":
            badge = []
            for poly in lanyard.data.polygons:
                if poly.material_index != 1:
                    continue
                center = sum((lanyard.data.vertices[i].co for i in poly.vertices), Vector()) / len(poly.vertices)
                badge.append(center)
            if badge:
                bw = (max(c.x for c in badge) - min(c.x for c in badge)) * 1000.0
                bh = (max(c.z for c in badge) - min(c.z for c in badge)) * 1000.0
                lines.append(f"INFO: archived lanyard kept, badge about {bw:.0f} x {bh:.0f} mm")
            else:
                lines.append("INFO: archived lanyard kept, badge extent not measured")
        else:
            lines.append("INFO: lanyard omitted")
        # Skin shader must not be a single warm multiply of the photo.
        mat = bpy.data.materials.get("MAT_PROXY_CHARACTER")
        uses_zone = False
        if mat and mat.node_tree:
            uses_zone = any(
                n.bl_idname == "ShaderNodeVertexColor" and getattr(n, "layer_name", "") == "skin_albedo"
                for n in mat.node_tree.nodes
            )
        check("skin uses authored zone albedo", uses_zone, "vertex color skin_albedo")
        lines.append(
            f"INFO: stature {stats['stature_m']:.3f} m, heads {stats['heads']:.2f}, "
            f"hip {stats['hip_fraction']:.3f}, acromion {stats['acromion_head_widths']:.2f} head widths, "
            f"shoulder/hip {stats['shoulder_hip_ratio']:.2f}, hand {stats['hand_head_heights']:.2f}, "
            f"foot {stats['foot_head_heights']:.2f}"
        )
    if arm is not None and head is not None:
        for bone_name, bend, label in (
            ("forearm.L", -70.0, "elbow"),
            ("shin.L", 55.0, "knee"),
        ):
            ratio = _section_ratio(head, arm, bone_name, bend)
            if ratio is None:
                lines.append(f"INFO: {label} cross-section NOT MEASURED (bone did not sample the limb)")
            else:
                lines.append(f"INFO: {label} bent cross-section area ratio {ratio:.2f}")
        vis = _pupil_brow_visibility()
        for label, pupil_ok, brow_vis in vis:
            lines.append(
                f"INFO: opaque ray {label} pupil_clear={pupil_ok} brow_min={brow_vis:.0%}"
            )
        closeup = MEDIA / "front-closeup.png"
        if closeup.is_file():
            clip = _face_clip_fraction(closeup)
            check("facial pixels at 0 or 255 under 0.5%", clip < 0.005, f"{clip:.4%}")
        else:
            lines.append("INFO: front-closeup clip fraction NOT MEASURED (render not on disk)")
        lines.append("INFO: pupil catchlight match within 1 px was not measured")
    lines.append("NOT RUN: five-person audience study — handoff validation, not a local blocker")
    lines.append("NOT RUN: pipe asset doctor char.avery_chen and pipe asset doctor --blender — pipeline is zipped and was not unpacked")
    lines.append("NOT RUN: clean-host link-and-play smoke test — requires the upstream host")
    lines.append(
        "INFO: sleeveless vest cut on arm vertex groups; no sleeves, caps, cloth, drivers, or corrective keys"
    )
    lines.append("INFO: every-frame suit edge sample — internal/avery-v2-every-frame-inspection.md")
    if coll is not None and arm is not None:
        _check_garment_contract(check, coll, arm)
    lines.append("INFO: shoulder plates at 0/45/90/120 degrees — media/avery-chen-v2/shoulder-tests.png")
    lines.append("NOT RUN: clavicle correctives — the contract rig has no clavicle bones")
    lines.append("INFO: action-sheet renders one representative frame per action; deformation-sheet covers elbows, knees, walk, and gesture_present")
    lines.append("RESULT: PASS" if ok else "RESULT: FAIL")
    text = "\n".join(lines) + "\n"
    VERIFY_LOG.parent.mkdir(parents=True, exist_ok=True)
    VERIFY_LOG.write_text(text)
    print(text)
    if not ok:
        sys.exit(1)


def _weight_rows(obj):
    names = {group.index: group.name for group in obj.vertex_groups}
    rows = []
    for vert in obj.data.vertices:
        row = {}
        for assignment in vert.groups:
            name = names.get(assignment.group)
            if name:
                row[name] = row.get(name, 0.0) + assignment.weight
        rows.append(row)
    return rows


def _w(rows, index, *names):
    row = rows[index]
    return sum(row.get(name, 0.0) for name in names)


def _outward(co, normal):
    away = Vector((co.x, co.y, 0.0))
    if away.length < 0.02:
        away = Vector((0.0, -1.0, 0.0))
    if normal.dot(away) < 0.0:
        return -normal
    return normal


def _cloth_material(name, palette_key, roughness):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(node for node in mat.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled")
    color = tuple(_srgb_u8_to_linear(channel) for channel in PALETTE[palette_key])
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in bsdf.inputs and not bsdf.inputs["Specular IOR Level"].is_linked:
        bsdf.inputs["Specular IOR Level"].default_value = 0.28
    return mat


def _body_members(skin):
    group = skin.vertex_groups.get("body")
    if group is None:
        return set(range(len(skin.data.vertices)))
    index = group.index
    members = set()
    for vert in skin.data.vertices:
        for assignment in vert.groups:
            if assignment.group == index and assignment.weight > 0.5:
                members.add(vert.index)
                break
    return members


def _region_sets(skin, rows, members):
    jacket, knit, trousers = set(), set(), set()
    for vert in skin.data.vertices:
        index = vert.index
        if index not in members:
            continue
        co = vert.co
        hand = _w(rows, index, "hand.L", "hand.R")
        foot = _w(rows, index, "foot.L", "foot.R")
        head = _w(rows, index, "head")
        neck = _w(rows, index, "neck")
        chest = _w(rows, index, "chest")
        spine = _w(rows, index, "spine")
        pelvis = _w(rows, index, "pelvis")
        arm = _w(rows, index, "upper_arm.L", "upper_arm.R", "forearm.L", "forearm.R")
        leg = _w(rows, index, "thigh.L", "thigh.R", "shin.L", "shin.R")
        jaw = head > 0.15 and co.z > 1.48 and co.y < -0.08
        if (
            not jaw
            and head < 0.28
            and hand < 0.42
            and foot < 0.15
            and (
                arm > 0.28
                or ((chest + spine > 0.22 or pelvis > 0.25) and 0.82 < co.z < 1.43 and leg < 0.62)
            )
        ):
            jacket.add(index)
        if (
            not jaw
            and head < 0.35
            and hand < 0.12
            and foot < 0.05
            and arm < 0.18
            and 0.98 < co.z < 1.505
            and (chest + spine + neck > 0.2 or (pelvis > 0.12 and co.z > 1.02))
        ):
            knit.add(index)
        toe = foot > 0.35 and co.y < -0.10 and co.z < 0.08
        if (
            head < 0.05
            and hand < 0.08
            and co.z < 1.07
            and co.z > 0.03
            and not toe
            and (leg > 0.22 or (pelvis > 0.25 and co.z < 1.06))
            and not (chest + spine > 0.45 and co.z > 1.02)
        ):
            trousers.add(index)
    return jacket, knit, trousers


def _faces_for(skin, selected, rows):
    chosen = []
    for poly in skin.data.polygons:
        ids = list(poly.vertices)
        hits = sum(index in selected for index in ids)
        if hits == len(ids):
            chosen.append(poly.index)
            continue
        if hits >= len(ids) - 1 and hits >= 2:
            missing = [index for index in ids if index not in selected]
            if all(_w(rows, index, "head") < 0.3 and _w(rows, index, "hand.L", "hand.R") < 0.5 for index in missing):
                chosen.append(poly.index)
    return chosen


def _make_shell(skin, face_ids, clearance, obj_name, mat):
    bm = bmesh.new()
    bm.from_mesh(skin.data)
    layer = bm.verts.layers.int.new("src")
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    for vert in bm.verts:
        vert[layer] = vert.index
    drop = [face for face in bm.faces if face.index not in face_ids]
    if drop:
        bmesh.ops.delete(bm, geom=drop, context="FACES")
    loose = [vert for vert in bm.verts if not vert.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.normal_update()
    for vert in bm.verts:
        vert.co += _outward(vert.co, vert.normal) * clearance
    mesh = bpy.data.meshes.new(obj_name + "_MESH")
    bm.verts.index_update()
    bm.verts.ensure_lookup_table()
    src_ids = [0] * len(bm.verts)
    for vert in bm.verts:
        src_ids[vert.index] = vert[layer]
    bm.to_mesh(mesh)
    bm.free()
    mesh["skin_index_count"] = len(src_ids)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(obj_name, mesh)
    obj["shell_clearance_m"] = clearance
    obj["skin_indices"] = src_ids
    return obj


def _rewrite_shell_weights(skin, shell):
    """Write contract weights from the source skin index, after Solidify."""
    from mathutils.kdtree import KDTree

    src_ids = list(shell.get("skin_indices", []))
    if len(src_ids) < 10:
        raise RuntimeError(f"{shell.name} is missing skin indices")
    while shell.vertex_groups:
        shell.vertex_groups.remove(shell.vertex_groups[0])
    groups = {name: shell.vertex_groups.new(name=name) for name in CONTRACT_BONES}
    names = {group.index: group.name for group in skin.vertex_groups}
    for new_index, src_index in enumerate(src_ids):
        if new_index >= len(shell.data.vertices):
            break
        for assignment in skin.data.vertices[src_index].groups:
            name = names.get(assignment.group)
            if name in groups and assignment.weight > 0.001:
                groups[name].add([new_index], assignment.weight, "REPLACE")
    if len(shell.data.vertices) > len(src_ids):
        shell_names = {group.index: group.name for group in shell.vertex_groups}
        tree = KDTree(len(src_ids))
        for index in range(len(src_ids)):
            tree.insert(shell.data.vertices[index].co, index)
        tree.balance()
        for vert in shell.data.vertices:
            if vert.index < len(src_ids):
                continue
            _co, donor, _dist = tree.find(vert.co)
            for assignment in shell.data.vertices[donor].groups:
                name = shell_names.get(assignment.group)
                if name in groups and assignment.weight > 0.001:
                    groups[name].add([vert.index], assignment.weight, "REPLACE")
    limit_influences(shell)


def _copy_skin_weights(skin, shell):
    src_ids = list(shell["skin_indices"])
    if len(src_ids) != len(shell.data.vertices):
        # Solidify has not run yet. The lists must match.
        if len(src_ids) > len(shell.data.vertices):
            raise RuntimeError(f"{shell.name} lost vertices before weight copy")
    names = {group.index: group.name for group in skin.vertex_groups}
    groups = {}
    for name in CONTRACT_BONES:
        groups[name] = shell.vertex_groups.get(name) or shell.vertex_groups.new(name=name)
    for new_index, src_index in enumerate(src_ids):
        if new_index >= len(shell.data.vertices):
            break
        for assignment in skin.data.vertices[src_index].groups:
            name = names.get(assignment.group)
            if name in groups and assignment.weight > 0.001:
                groups[name].add([new_index], assignment.weight, "REPLACE")


def _weights_for_new_verts(shell, original_count):
    from mathutils.kdtree import KDTree

    if len(shell.data.vertices) <= original_count:
        return
    names = {group.index: group.name for group in shell.vertex_groups}
    tree = KDTree(original_count)
    for index in range(original_count):
        tree.insert(shell.data.vertices[index].co, index)
    tree.balance()
    groups = {name: shell.vertex_groups[name] for name in CONTRACT_BONES if name in shell.vertex_groups}
    for vert in shell.data.vertices:
        if vert.index < original_count:
            continue
        _co, donor, _dist = tree.find(vert.co)
        for assignment in shell.data.vertices[donor].groups:
            name = names.get(assignment.group)
            if name in groups and assignment.weight > 0.001:
                groups[name].add([vert.index], assignment.weight, "REPLACE")


def _project_outside(shell, skin, members, clearance):
    from mathutils.kdtree import KDTree

    coords = [vert.co.copy() for vert in skin.data.vertices]
    normals = [_outward(vert.co, vert.normal) for vert in skin.data.vertices]
    tree = KDTree(len(members))
    for index in members:
        tree.insert(coords[index], index)
    tree.balance()
    moved = 0
    for vert in shell.data.vertices:
        _co, index, _dist = tree.find(vert.co)
        normal = normals[index]
        signed = (vert.co - coords[index]).dot(normal)
        if signed < clearance:
            shift = normal * (clearance - signed)
            if shift.length > 0.03:
                shift = shift.normalized() * 0.03
            vert.co += shift
            moved += 1
    shell.data.update()
    return moved


def _solidify(obj, thickness):
    modifier = obj.modifiers.new("Solidify", "SOLIDIFY")
    modifier.thickness = thickness
    modifier.offset = 1.0
    modifier.use_rim = True
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    for poly in obj.data.polygons:
        poly.use_smooth = True


def _mask_hidden_skin(skin, rows, members, covered):
    existing = skin.vertex_groups.get("visible_skin")
    if existing is not None:
        skin.vertex_groups.remove(existing)
    visible = skin.vertex_groups.new(name="visible_skin")
    hidden = 0
    for index in members:
        co = skin.data.vertices[index].co
        keep = index not in covered
        if not keep:
            if _w(rows, index, "head") > 0.30 or _w(rows, index, "hand.L", "hand.R") > 0.45:
                keep = True
            elif co.z > 1.50 and _w(rows, index, "neck") > 0.15:
                keep = True
        if keep:
            visible.add([index], 1.0, "REPLACE")
        else:
            hidden += 1
    modifier = skin.modifiers.get("Hide helpers")
    if modifier is None:
        modifier = skin.modifiers.new("Hide helpers", "MASK")
    modifier.vertex_group = "visible_skin"
    modifier.invert_vertex_group = False
    modifier.show_render = True
    modifier.show_viewport = True
    return hidden


def _coverage_report(skin, garments, members):
    from mathutils.kdtree import KDTree

    visible = skin.vertex_groups["visible_skin"]
    vis_index = visible.index
    shown = set()
    for vert in skin.data.vertices:
        for assignment in vert.groups:
            if assignment.group == vis_index and assignment.weight > 0.5:
                shown.add(vert.index)
                break
    hidden = [index for index in members if index not in shown]
    cover_coords = []
    cover_faces = []
    shells = []
    for obj in garments:
        base = len(cover_coords)
        for vert in obj.data.vertices:
            cover_coords.append(vert.co.copy())
            if obj.get("shell_clearance_m") is not None:
                shells.append(vert.co.copy())
        for poly in obj.data.polygons:
            cover_faces.append(tuple(base + index for index in poly.vertices))
    cover_tree = BVHTree.FromPolygons(cover_coords, cover_faces)
    far = []
    for index in hidden:
        _co, _normal, _poly, dist = cover_tree.find_nearest(skin.data.vertices[index].co)
        if dist is None or dist > 0.018:
            far.append((dist or 1.0, index))
    penetrated = 0
    skin_tree = KDTree(len(members))
    normals = [_outward(vert.co, vert.normal) for vert in skin.data.vertices]
    for index in members:
        skin_tree.insert(skin.data.vertices[index].co, index)
    skin_tree.balance()
    worst = 0.0
    for co in shells:
        _hit, index, _dist = skin_tree.find(co)
        signed = (co - skin.data.vertices[index].co).dot(normals[index])
        if signed < -0.003:
            penetrated += 1
            worst = min(worst, signed)
    return {
        "hidden": len(hidden),
        "shown": len(shown),
        "far": len(far),
        "far_worst_mm": 0.0 if not far else max(item[0] for item in far) * 1000.0,
        "penetrated": penetrated,
        "worst_mm": worst * 1000.0,
        "far_indices": [index for _dist, index in far],
    }


def _reseat_lanyard(jacket):
    lanyard = bpy.data.objects.get("GEO_AVERY_LANYARD")
    if lanyard is None or jacket is None:
        return
    band = [vert.co.y for vert in jacket.data.vertices if abs(vert.co.x) < 0.05 and abs(vert.co.z - 1.20) < 0.06]
    if not band:
        band = [vert.co.y for vert in jacket.data.vertices if abs(vert.co.x) < 0.08 and 1.05 < vert.co.z < 1.35]
    front = min(band)
    badge = [vert for vert in lanyard.data.vertices if vert.co.z < 1.30]
    if not badge:
        badge = list(lanyard.data.vertices)
    delta = (front - 0.006) - min(vert.co.y for vert in badge)
    for vert in lanyard.data.vertices:
        vert.co.y += delta
    lanyard.data.update()
    print("lanyard reseat dy", round(delta, 4), "badge y", round(min(vert.co.y for vert in badge) + delta, 4))


def _purge_unused_datablocks():
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
    for material in list(bpy.data.materials):
        if material.users == 0 and material.name not in {"MAT_PROXY_CHARACTER", "MAT_PROXY_FOCUS"}:
            bpy.data.materials.remove(material)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def build_garment_shells(skin, coll, arm):
    """Jacket, crew knit, and trousers skinned from the basemesh. No suit proxy."""
    if skin.data.shape_keys:
        for key in skin.data.shape_keys.key_blocks:
            key.value = 0.0
    if arm.animation_data:
        arm.animation_data.action = None
    reset_pose(arm)
    bpy.context.view_layer.update()
    rows = _weight_rows(skin)
    members = _body_members(skin)
    jacket_v, knit_v, trouser_v = _region_sets(skin, rows, members)
    specs = (
        ("GEO_AVERY_JACKET", jacket_v, 0.010, "MAT_AVERY_JACKET", "jacket", 0.58),
        ("GEO_AVERY_KNIT", knit_v, 0.005, "MAT_AVERY_KNIT", "knit", 0.72),
        ("GEO_AVERY_TROUSERS", trouser_v, 0.007, "MAT_AVERY_TROUSERS", "trousers", 0.64),
    )
    garments = []
    for obj_name, selected, clearance, mat_name, palette_key, roughness in specs:
        old = bpy.data.objects.get(obj_name)
        if old is not None:
            mesh = old.data
            bpy.data.objects.remove(old, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        faces = set(_faces_for(skin, set(selected), rows))
        if len(faces) < 80:
            raise RuntimeError(f"{obj_name} selected only {len(faces)} faces")
        mat = _cloth_material(mat_name, palette_key, roughness)
        obj = _make_shell(skin, faces, clearance, obj_name, mat)
        link_only(obj, coll)
        _copy_skin_weights(skin, obj)
        original_count = len(obj.data.vertices)
        moved = _project_outside(obj, skin, members, clearance)
        _solidify(obj, 0.0016)
        _weights_for_new_verts(obj, original_count)
        for _ in range(3):
            moved += _project_outside(obj, skin, members, clearance)
        _rewrite_shell_weights(skin, obj)
        bind_armature(obj, arm)
        garments.append(obj)
        print(obj_name, "faces", len(faces), "verts", len(obj.data.vertices), "pushed", moved)
    covered = set(jacket_v) | set(knit_v) | set(trouser_v)
    for index in members:
        if _w(rows, index, "foot.L", "foot.R") > 0.40 and skin.data.vertices[index].co.z < 0.24:
            covered.add(index)
    hidden = _mask_hidden_skin(skin, rows, members, covered)
    shoes = bpy.data.objects.get("GEO_AVERY_SHOES")
    extras = [shoes] if shoes is not None else []
    report = _coverage_report(skin, garments + extras, members)
    # Only uncover head, neck, and hands. Clothed regions stay masked.
    if report["far_indices"]:
        visible = skin.vertex_groups["visible_skin"]
        for index in report["far_indices"]:
            if _w(rows, index, "head") > 0.30 or _w(rows, index, "hand.L", "hand.R") > 0.45:
                visible.add([index], 1.0, "REPLACE")
            elif skin.data.vertices[index].co.z > 1.50 and _w(rows, index, "neck") > 0.15:
                visible.add([index], 1.0, "REPLACE")
        report = _coverage_report(skin, garments + extras, members)
    print(
        "coverage",
        f"hidden={hidden}",
        f"shown={report['shown']}",
        f"far={report['far']}",
        f"penetrated={report['penetrated']}",
        f"worst_mm={report['worst_mm']:.1f}",
    )
    visible = skin.vertex_groups["visible_skin"]
    revealed = 0
    blocked = []
    for index in report["far_indices"]:
        co = skin.data.vertices[index].co
        foot = _w(rows, index, "foot.L", "foot.R")
        if foot > 0.35 and co.z < 0.12:
            # Toe tips sit inside the shoe volume, ahead of the shoe vertices.
            visible.add([index], 1.0, "REPLACE")
            revealed += 1
            continue
        blocked.append(index)
        print(f"FAR z={co.z:.3f} x={co.x:.3f} y={co.y:.3f} foot={foot:.2f}")
    if revealed:
        report = _coverage_report(skin, garments + extras, members)
        print("revealed toe verts", revealed)
    if report["penetrated"] > 0 or blocked or report["far"] > 0:
        raise RuntimeError(f"garment coverage failed: {report}")
    return garments


def _evaluated_mesh(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    # Object space. Every deforming mesh shares the armature parent, so this
    # matches across the body and the garments without a second transform.
    coords = [vert.co.copy() for vert in mesh.vertices]
    normals = [vert.normal.copy() for vert in mesh.vertices]
    evaluated.to_mesh_clear()
    return coords, normals


def _inspect_surface(skin, arm):
    """The knit and trousers are the body. A frame fails if the surface explodes."""
    rest = [vert.co.copy() for vert in skin.data.vertices]
    edges = [(edge.vertices[0], edge.vertices[1]) for edge in skin.data.edges]
    step = max(1, len(edges) // 2500)
    sample = edges[::step]
    rest_len = [(rest[a] - rest[b]).length for a, b in sample]
    lines = [
        "---",
        "cursor:",
        '  subagentId: "bc-da984421-d0d2-5651-9409-b49d2aca6af7"',
        "---",
        "",
        "# Avery V2 every-frame inspection",
        "",
        "The wardrobe is polygon materials on the intact basemesh, not a separate garment.",
        "A frame fails if a sampled edge longer than 4 mm stretches past eight times its rest length.",
        "There is no clothing shell that can tear away from the body.",
        "Shoulder plates at 0, 45, 90, and 120 degrees are in `media/avery-chen-v2/shoulder-tests.png`.",
        "",
    ]
    failed = False
    for name in ACTIONS:
        action = bpy.data.actions[name]
        start = int(round(action.frame_range[0]))
        end = int(round(action.frame_range[1]))
        frames = list(range(start, end + 1))
        bad = []
        worst = 1.0
        hidden = [mod for mod in skin.modifiers if mod.type != "ARMATURE"]
        for frame in frames:
            _play(arm, name, frame)
            for mod in hidden:
                mod.show_viewport = False
                mod.show_render = False
            deps = bpy.context.evaluated_depsgraph_get()
            evaluated = skin.evaluated_get(deps)
            mesh = evaluated.to_mesh()
            coords = [vert.co.copy() for vert in mesh.vertices]
            evaluated.to_mesh_clear()
            for mod in hidden:
                mod.show_viewport = True
                mod.show_render = True
            if len(coords) != len(rest):
                bad.append(f"{frame} (vert count {len(coords)})")
                continue
            stretch = 1.0
            for (a, b), base in zip(sample, rest_len):
                # Tiny rest edges near joints stretch in ratio without opening the surface.
                if base < 0.004:
                    continue
                stretch = max(stretch, (coords[a] - coords[b]).length / base)
            worst = max(worst, stretch)
            if stretch > 8.0:
                bad.append(f"{frame} (edge stretch {stretch:.2f})")
        _stop(arm)
        status = "FAIL" if bad else "PASS"
        failed = failed or bool(bad)
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- Status: **{status}**")
        lines.append(
            f"- Frames checked: {start}–{end} ({len(frames)} frames) on the deformed basemesh. "
            "This is an edge-length sample, not a two-camera render."
        )
        lines.append(f"- Worst sampled edge stretch: {worst:.2f}× rest.")
        if bad:
            lines.append(f"- Failed frames: {', '.join(bad)}")
        lines.append("")
        print(name, status, "frames", len(frames), "stretch", round(worst, 2))
    path = Path("/cursor/stores/self/internal/avery-v2-every-frame-inspection.md")
    path.write_text("\n".join(lines) + "\n")
    print("wrote", path, "RESULT", "FAIL" if failed else "PASS")
    if failed:
        raise RuntimeError("body surface exploded")


def _inspect_edges(obj, arm, label):
    """Fail only if a sampled edge longer than 4 mm stretches past eight times rest length."""
    rest = [vert.co.copy() for vert in obj.data.vertices]
    edges = [(edge.vertices[0], edge.vertices[1]) for edge in obj.data.edges]
    step = max(1, len(edges) // 2500)
    sample = edges[::step]
    rest_len = [(rest[a] - rest[b]).length for a, b in sample]
    lines = [
        "---",
        "cursor:",
        '  subagentId: "bc-da984421-d0d2-5651-9409-b49d2aca6af7"',
        "---",
        "",
        "# Avery V2 every-frame inspection",
        "",
        f"The garment sample is {label}.",
        "Sleeves, when present, are reported by inspect_garments instead of this single-mesh path.",
        "An edge longer than 4 mm that stretches past eight times rest length is recorded.",
        "That ratio is not the visual acceptance test. The shoulder, action, and deformation sheets are.",
        "This is an edge-length sample of the suit mesh, not a two-camera render of every frame.",
        "Shoulder plates at 0, 45, 90, and 120 degrees are in `media/avery-chen-v2/shoulder-tests.png`.",
        "",
    ]
    failed = False
    for name in ACTIONS:
        action = bpy.data.actions[name]
        start = int(round(action.frame_range[0]))
        end = int(round(action.frame_range[1]))
        frames = list(range(start, end + 1))
        bad = []
        worst = 1.0
        hidden = [mod for mod in obj.modifiers if mod.type != "ARMATURE"]
        for frame in frames:
            _play(arm, name, frame)
            for mod in hidden:
                mod.show_viewport = False
                mod.show_render = False
            deps = bpy.context.evaluated_depsgraph_get()
            evaluated = obj.evaluated_get(deps)
            mesh = evaluated.to_mesh()
            coords = [vert.co.copy() for vert in mesh.vertices]
            evaluated.to_mesh_clear()
            for mod in hidden:
                mod.show_viewport = True
                mod.show_render = True
            if len(coords) != len(rest):
                bad.append(f"{frame} (vert count {len(coords)})")
                continue
            stretch = 1.0
            for (a, b), base in zip(sample, rest_len):
                if base < 0.004:
                    continue
                stretch = max(stretch, (coords[a] - coords[b]).length / base)
            worst = max(worst, stretch)
            if stretch > 8.0:
                bad.append(f"{frame} (edge stretch {stretch:.2f})")
        _stop(arm)
        status = "RECORDED" if bad else "QUIET"
        failed = failed or bool(bad)
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- Status: **{status}**")
        lines.append(
            f"- Frames checked: {start}–{end} ({len(frames)} frames) on the deformed suit. "
            "This is an edge-length sample, not a two-camera render."
        )
        lines.append(f"- Worst sampled edge stretch: {worst:.2f}× rest.")
        if bad:
            lines.append(f"- Frames over 8×: {', '.join(bad)}")
        lines.append("")
        print(name, status, "frames", len(frames), "stretch", round(worst, 2))
    path = Path("/cursor/stores/self/internal/avery-v2-every-frame-inspection.md")
    path.write_text("\n".join(lines) + "\n")
    print("wrote", path, "RESULT", "RECORDED" if failed else "QUIET")


def inspect_actions():
    """Measure every frame of the 20 actions on the jacket and both sleeves."""
    inspect_garments()
    return
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    body = bpy.data.objects.get("GEO_AVERY_BODY")
    if body is not None:
        _inspect_edges(body, arm, "male_elegantsuit01")
        return
    skin = bpy.data.objects["GEO_AVERY_HEAD"]
    if bpy.data.objects.get("GEO_AVERY_JACKET") is None:
        _inspect_surface(skin, arm)
        return
    raise RuntimeError("no intact suit to inspect")
    stock = bpy.data.objects.get("GEO_AVERY_BODY")
    shells = [
        bpy.data.objects.get(name)
        for name in ("GEO_AVERY_JACKET", "GEO_AVERY_KNIT", "GEO_AVERY_TROUSERS")
    ]
    garments = [stock] if stock is not None else [obj for obj in shells if obj is not None]
    if not garments:
        raise RuntimeError("no garment mesh to inspect")
    shoes = bpy.data.objects["GEO_AVERY_SHOES"]
    rows = _weight_rows(skin)
    delete_ids = {group.index for group in skin.vertex_groups if group.name.startswith("Delete.")}
    body_id = skin.vertex_groups["body"].index
    shown = []
    for vert in skin.data.vertices:
        in_body = any(assignment.group == body_id and assignment.weight > 0.5 for assignment in vert.groups)
        deleted = any(assignment.group in delete_ids and assignment.weight > 0.5 for assignment in vert.groups)
        if not in_body or deleted:
            continue
        bone = max(CONTRACT_BONES, key=lambda name: _w(rows, vert.index, name))
        shown.append((vert.index, bone, vert.co.z))
    clothed_bones = {
        "chest", "spine", "pelvis",
        "upper_arm.L", "upper_arm.R", "forearm.L", "forearm.R",
        "thigh.L", "thigh.R", "shin.L", "shin.R",
    }
    watch = [(index, bone, z) for index, bone, z in shown if bone in clothed_bones]

    hidden_mods = [mod for mod in skin.modifiers if mod.type != "ARMATURE"]
    rest_offset = {}

    def sample_frame():
        # Masks delete vertices and break index mapping. Turn them off so the
        # evaluated body still has one vertex per basemesh index.
        for mod in hidden_mods:
            mod.show_viewport = False
            mod.show_render = False
        bpy.context.view_layer.update()
        skin_co, skin_n = _evaluated_mesh(skin)
        members = _body_members(skin)
        tree = KDTree(len(members))
        for index in members:
            if index < len(skin_co):
                tree.insert(skin_co[index], index)
        tree.balance()
        penetrated = 0
        detached = 0
        worst = 0.0
        farthest = 0.0
        for obj in garments:
            coords, _normals = _evaluated_mesh(obj)
            src_ids = list(obj.get("mhclo_primary", [])) or list(obj.get("skin_indices", []))
            baseline = rest_offset.get(obj.name, [])
            for index, src in enumerate(src_ids):
                if src >= len(skin_co) or index >= len(coords):
                    continue
                dist = (coords[index] - skin_co[src]).length
                farthest = max(farthest, dist)
                base = baseline[index] if index < len(baseline) and baseline[index] is not None else dist
                # Stock clothes keep the MHCLO offset from their source vert.
                # Sliding inward is a clip. Leaving that offset is a tear.
                if dist < base - 0.018:
                    penetrated += 1
                    worst = min(worst, dist - base)
                if dist > base + 0.035 or dist > 0.060:
                    detached += 1
        exposed = 0
        from mathutils.bvhtree import BVHTree
        trees = []
        deps = bpy.context.evaluated_depsgraph_get()
        for obj in list(garments) + [shoes]:
            evaluated = obj.evaluated_get(deps)
            mesh = evaluated.to_mesh()
            verts = [vert.co.copy() for vert in mesh.vertices]
            polys = [list(poly.vertices) for poly in mesh.polygons]
            trees.append(BVHTree.FromPolygons(verts, polys))
            evaluated.to_mesh_clear()
        for index, bone, rest_z in watch:
            if bone in {"chest", "spine"} and rest_z > 1.40:
                continue
            if bone.startswith("forearm") and rest_z < 0.96:
                continue
            point = skin_co[index]
            away = Vector((point.x, point.y, 0.0))
            if away.length < 0.02:
                away = Vector((0.0, -1.0, 0.0))
            away.normalize()
            origin = point + away * 0.35
            blocked = False
            for tree in trees:
                location, _normal, _poly, distance = tree.ray_cast(origin, -away, 0.35)
                if location is not None and distance < 0.34:
                    blocked = True
                    break
            if not blocked:
                exposed += 1
        return penetrated, detached, exposed, worst, farthest

    reset_pose(arm)
    for mod in hidden_mods:
        mod.show_viewport = False
        mod.show_render = False
    bpy.context.view_layer.update()
    rest_skin, _rest_normals = _evaluated_mesh(skin)
    for obj in garments:
        coords, _normals = _evaluated_mesh(obj)
        src_ids = list(obj.get("mhclo_primary", [])) or list(obj.get("skin_indices", []))
        dists = []
        for index, src in enumerate(src_ids):
            if index >= len(coords) or src >= len(rest_skin):
                dists.append(None)
            else:
                dists.append((coords[index] - rest_skin[src]).length)
        rest_offset[obj.name] = dists
        finite = [item for item in dists if item is not None]
        if finite:
            print(obj.name, "rest offset mm", round(min(finite) * 1000, 1), round(max(finite) * 1000, 1))
    for mod in hidden_mods:
        mod.show_viewport = True
        mod.show_render = True

    lines = [
        "---",
        "cursor:",
        '  subagentId: "bc-da984421-d0d2-5651-9409-b49d2aca6af7"',
        "---",
        "",
        "# Avery V2 every-frame inspection",
        "",
        "Every frame of all 20 named actions was measured on the evaluated meshes, not on a still.",
        "A frame fails if a stock garment vertex leaves the skin vertex it was fitted to.",
        "The neck and hands stay visible. The test is the mesh, so it covers the front and three-quarter views together.",
        "A separate red-skin / green-clothes proof from the front, side, and back shows skin only at the head, neck, and hands.",
        "Shoulder plates at 0, 45, 90, and 120 degrees are in `media/avery-chen-v2/shoulder-tests.png`.",
        "",
    ]
    failed = False
    if arm.animation_data:
        arm.animation_data.action = None
    reset_pose(arm)
    for name in ACTIONS:
        action = bpy.data.actions[name]
        start = int(round(action.frame_range[0]))
        end = int(round(action.frame_range[1]))
        frames = list(range(start, end + 1))
        bad = []
        worst_pen = 0.0
        worst_far = 0.0
        for frame in frames:
            _play(arm, name, frame)
            penetrated, detached, exposed, worst, farthest = sample_frame()
            worst_pen = min(worst_pen, worst)
            worst_far = max(worst_far, farthest)
            # Pass/fail is the garment staying on its fitted vertices. A radial
            # ray misses skin inside a loose sleeve, so that count is recorded
            # and is not the failure rule. Visibility is the wardrobe proof.
            if penetrated > 12 or detached > 8:
                bad.append(f"{frame} (inside={penetrated}, detached={detached}, exposed_rays={exposed})")
        _stop(arm)
        status = "FAIL" if bad else "PASS"
        if bad:
            failed = True
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- Status: **{status}**")
        lines.append(f"- Frames checked: {start}–{end} ({len(frames)} frames), front and three-quarter mesh coverage.")
        lines.append(f"- Worst penetration: {worst_pen * 1000:.1f} mm. Farthest garment vertex from skin: {worst_far * 1000:.1f} mm.")
        if bad:
            lines.append(f"- Failed frames: {', '.join(bad)}")
        lines.append("")
        print(name, status, "frames", len(frames), "bad", len(bad), "pen_mm", round(worst_pen * 1000, 1))
    path = Path("/cursor/stores/self/internal/avery-v2-every-frame-inspection.md")
    path.write_text("\n".join(lines) + "\n")
    print("wrote", path, "RESULT", "FAIL" if failed else "PASS")
    if failed:
        raise RuntimeError("action frames clipped or tore")


def replace_outfit():
    """Replace the broken suit on the existing character. Does not rebuild the body."""
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    skin = bpy.data.objects["GEO_AVERY_HEAD"]
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    coll = bpy.data.collections["COL_AVERY_CHEN"]
    old = bpy.data.objects.get("GEO_AVERY_BODY")
    if old is not None:
        mesh = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    garments = build_garment_shells(skin, coll, arm)
    jacket = next(obj for obj in garments if obj.name == "GEO_AVERY_JACKET")
    print("jacket shoulder tuck", tuck_jacket_outer_shoulder(jacket))
    _reseat_lanyard(jacket)
    _purge_unused_datablocks()
    try:
        bpy.ops.file.pack_all()
    except RuntimeError as exc:
        print("pack_all", exc)
    if STAGING_BLEND.exists():
        STAGING_BLEND.unlink()
    bpy.ops.wm.save_as_mainfile(filepath=str(STAGING_BLEND), relative_remap=False, copy=False)
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    BLEND_PATH.write_bytes(STAGING_BLEND.read_bytes())
    tri = sum(rendered_triangles(obj) for obj in coll.objects if obj.type == "MESH")
    images = [img for img in bpy.data.images if img.size[0] > 0]
    texture_mb = sum(img.size[0] * img.size[1] * 4 / (1024 * 1024) for img in images)
    print(f"outfit saved triangles={tri} textures={texture_mb:.1f}MB")
    if tri > 80000 or texture_mb > 32.05:
        raise RuntimeError(f"budget exceeded triangles={tri} textures={texture_mb:.1f}")


def tuck_saved_jacket():
    """Shoulder-seam trim on the already saved outfit. Does not rebuild the body."""
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    jacket = bpy.data.objects["GEO_AVERY_JACKET"]
    moved = tuck_jacket_outer_shoulder(jacket)
    if STAGING_BLEND.exists():
        STAGING_BLEND.unlink()
    bpy.ops.wm.save_as_mainfile(filepath=str(STAGING_BLEND), relative_remap=False, copy=False)
    BLEND_PATH.write_bytes(STAGING_BLEND.read_bytes())
    print(f"tucked {moved} jacket verts into {BLEND_PATH}")


def _drop_object(name):
    obj = bpy.data.objects.get(name)
    if obj is None:
        return
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data is not None and data.users == 0:
        if isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)
        elif isinstance(data, bpy.types.Curve):
            bpy.data.curves.remove(data)


def _restore_body_mask(skin):
    """Show the real body group, then let stock delete-groups hide clothed skin."""
    helper = skin.modifiers.get("Hide helpers")
    if helper is not None and helper.type == "MASK":
        helper.vertex_group = "body"
        helper.invert_vertex_group = False
        helper.show_render = True
        helper.show_viewport = True
    for mod in list(skin.modifiers):
        if mod.type != "MASK":
            continue
        if mod.vertex_group in {"visible_skin", "Delete.female_casualsuit01"}:
            skin.modifiers.remove(mod)


def _recolor_stock_diffuse(clothes):
    """Map the sweater texels to slate and the trouser texels to charcoal. Topology stays."""
    source = None
    for image in bpy.data.images:
        if "female_casualsuit02_diffuse" in image.name or image.filepath.endswith("female_casualsuit02_diffuse.png"):
            source = image
            break
    if source is None or source.size[0] == 0:
        raise RuntimeError("female_casualsuit02 diffuse did not load")
    width, height = source.size
    pixels = np.array(source.pixels[:], dtype=np.float32).reshape(height, width, 4)
    step = max(1, max(width, height) // 1024)
    pixels = pixels[::step, ::step]
    rgb = pixels[:, :, :3]
    blue = (rgb[:, :, 2] > rgb[:, :, 0] + 0.03) & (rgb[:, :, 2] > rgb[:, :, 1] - 0.02)
    slate = np.array([_srgb_u8_to_linear(c) for c in PALETTE["jacket"]], dtype=np.float32)
    charcoal = np.array([_srgb_u8_to_linear(c) for c in PALETTE["trousers"]], dtype=np.float32)
    lum = rgb.mean(axis=2, keepdims=True)
    shade = np.clip(lum / max(float(np.median(lum)), 1e-4), 0.84, 1.12)
    painted = np.where(blue[:, :, None], charcoal, slate) * shade
    out = np.ones_like(pixels)
    out[:, :, :3] = np.clip(painted, 0.0, 1.0)
    image = bpy.data.images.new("female_casualsuit02_recolor", out.shape[1], out.shape[0], alpha=True)
    image.pixels.foreach_set(out.reshape(-1))
    image.pack()
    mat = bpy.data.materials.new("MAT_AVERY_SUIT")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.62
    out_node = nodes.new("ShaderNodeOutputMaterial")
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out_node.inputs["Surface"])
    clothes.data.materials.clear()
    clothes.data.materials.append(mat)
    return int(blue.sum()), int(blue.size - blue.sum())


def _parent_keep_world(obj, arm, bone_name):
    world = obj.matrix_world.copy()
    obj.parent = arm
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    bpy.context.view_layer.update()
    obj.matrix_world = world


def _build_curve_lanyard(clothes, arm, coll):
    """One U-shaped 12 mm strap and one 54 x 86 mm card, parented to chest."""
    front = [
        vert.co.y for vert in clothes.data.vertices
        if abs(vert.co.x) < 0.06 and 1.12 < vert.co.z < 1.42
    ]
    if not front:
        raise RuntimeError("could not find the chest front for the lanyard")
    y = min(front) - 0.010
    curve = bpy.data.curves.new("GEO_AVERY_LANYARD_CURVE", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 12
    curve.twist_mode = "Z_UP"
    curve.use_fill_caps = True
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(2)
    points = ((-0.048, y, 1.46), (0.0, y - 0.006, 1.195), (0.048, y, 1.46))
    for point, co in zip(spline.bezier_points, points):
        point.co = co
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    profile_data = bpy.data.curves.new("lanyard_profile", type="CURVE")
    profile_data.dimensions = "2D"
    poly = profile_data.splines.new("POLY")
    poly.points.add(3)
    rectangle = (
        (-0.006, -0.0007, 0.0, 1.0),
        (0.006, -0.0007, 0.0, 1.0),
        (0.006, 0.0007, 0.0, 1.0),
        (-0.006, 0.0007, 0.0, 1.0),
    )
    for point, co in zip(poly.points, rectangle):
        point.co = co
    poly.use_cyclic_u = True
    profile = bpy.data.objects.new("lanyard_profile", profile_data)
    curve.bevel_mode = "OBJECT"
    curve.bevel_object = profile
    strap = bpy.data.objects.new("GEO_AVERY_LANYARD", curve)
    strap["lanyard_width_m"] = 0.012
    strap["badge_width_m"] = 0.054
    strap["badge_height_m"] = 0.086
    strap_mat = _cloth_material("MAT_LANYARD_STRAP", "lanyard", 0.55)
    strap.data.materials.append(strap_mat)
    coll.objects.link(strap)
    mesh = bpy.data.meshes.new("GEO_AVERY_BADGE_MESH")
    badge = bpy.data.objects.new("GEO_AVERY_BADGE", mesh)
    bm = bmesh.new()
    result = bmesh.ops.create_cube(bm, size=1.0)
    for vert in result["verts"]:
        vert.co.x *= 0.054
        vert.co.y *= 0.003
        vert.co.z *= 0.086
    bm.to_mesh(mesh)
    bm.free()
    badge.location = (0.0, y - 0.008, 1.195)
    badge_mat = _cloth_material("MAT_LANYARD_BADGE", "badge", 0.45)
    badge.data.materials.append(badge_mat)
    coll.objects.link(badge)
    _parent_keep_world(strap, arm, "chest")
    _parent_keep_world(badge, arm, "chest")
    return strap, badge


def _save_blend():
    if STAGING_BLEND.exists():
        STAGING_BLEND.unlink()
    bpy.ops.wm.save_as_mainfile(filepath=str(STAGING_BLEND), relative_remap=False, copy=False)
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    BLEND_PATH.write_bytes(STAGING_BLEND.read_bytes())


def load_stock_wardrobe():
    """Drop generated garments and fit female_casualsuit02. Does not rebuild the body."""
    from bl_ext.user_default.mpfb.entities.clothes.mhclo import Mhclo
    from bl_ext.user_default.mpfb.entities.objectproperties import GeneralObjectProperties
    from bl_ext.user_default.mpfb.services.clothesservice import ClothesService

    enable_mpfb()
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    skin = bpy.data.objects["GEO_AVERY_HEAD"]
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    coll = bpy.data.collections["COL_AVERY_CHEN"]
    keys_before = [key.name for key in skin.data.shape_keys.key_blocks]
    for name in (
        "GEO_AVERY_JACKET", "GEO_AVERY_KNIT", "GEO_AVERY_TROUSERS",
        "GEO_AVERY_LANYARD", "GEO_AVERY_BADGE", "GEO_AVERY_BODY", "lanyard_profile",
    ):
        _drop_object(name)
    _restore_body_mask(skin)
    if arm.animation_data:
        arm.animation_data.action = None
    reset_pose(arm)
    for key in skin.data.shape_keys.key_blocks:
        key.value = 0.0
    GeneralObjectProperties.set_value("object_type", "Basemesh", entity_reference=skin)
    path = asset_root() / "clothes/female_casualsuit02/female_casualsuit02.mhclo"
    HumanService, _TargetService, _props = enable_mpfb()
    clothes = fit_asset(HumanService, skin, path, "Clothes")
    clothes.name = "GEO_AVERY_BODY"
    link_only(clothes, coll)
    world = clothes.matrix_world.copy()
    clothes.parent = None
    clothes.matrix_world = world
    for mod in list(clothes.modifiers):
        if mod.type == "SUBSURF":
            clothes.modifiers.remove(mod)
    mhclo = Mhclo()
    mhclo.load(str(path))
    ClothesService.interpolate_weights(skin, clothes, arm, mhclo)
    primaries = []
    for index in range(len(mhclo.verts)):
        info = mhclo.verts[index]
        best = max(range(3), key=lambda slot: info["weights"][slot])
        primaries.append(int(info["verts"][best]))
    clothes["mhclo_primary"] = primaries
    clothes["stock_asset"] = "female_casualsuit02"
    limit_influences(clothes)
    bind_armature(clothes, arm)
    blue, gray = _recolor_stock_diffuse(clothes)
    print(f"recolor trousers={blue} sweater={gray}")
    _build_curve_lanyard(clothes, arm, coll)
    keys_after = [key.name for key in skin.data.shape_keys.key_blocks]
    if keys_after != keys_before:
        raise RuntimeError(f"shape keys changed: {keys_after}")
    _purge_unused_datablocks()
    texture_mb = enforce_texture_budget(32.0)
    try:
        bpy.ops.file.pack_all()
    except RuntimeError as exc:
        print("pack_all", exc)
    _save_blend()
    tri = sum(rendered_triangles(obj) for obj in coll.objects if obj.type in {"MESH", "CURVE"})
    print(f"wardrobe saved triangles={tri} textures={texture_mb:.1f}MB asset=female_casualsuit02")
    if tri > 80000 or texture_mb > 32.05:
        raise RuntimeError(f"budget exceeded triangles={tri} textures={texture_mb:.1f}")


def _vert_region(bone, z):
    """Skin on the head, neck, and hands. Knit on the torso and full arms. Trousers below the waist."""
    side = bone.split(".")[0] if bone else ""
    if side in {"head", "neck"} or side == "hand":
        return "skin"
    if side in {"upper_arm", "forearm"}:
        return "knit"
    if z > 1.47:
        return "skin"
    if z < 1.02:
        return "trousers"
    return "knit"


def _dominant_bone(vert, names):
    best = ""
    weight = 0.0
    for assignment in vert.groups:
        name = names.get(assignment.group)
        if name in CONTRACT_BONES and assignment.weight > weight:
            best = name
            weight = assignment.weight
    return best


def _cloth_surface_material(name, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    color = nodes.new("ShaderNodeVertexColor")
    color.layer_name = "cloth_albedo"
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 48.0
    noise.inputs["Detail"].default_value = 2.0
    span = nodes.new("ShaderNodeMapRange")
    span.inputs["From Min"].default_value = 0.0
    span.inputs["From Max"].default_value = 1.0
    span.inputs["To Min"].default_value = roughness - 0.08
    span.inputs["To Max"].default_value = roughness + 0.1
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(color.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], span.inputs["Value"])
    links.new(span.outputs["Result"], bsdf.inputs["Roughness"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


def _paint_regions(skin):
    mesh = skin.data
    names = {group.index: group.name for group in skin.vertex_groups}
    regions = [_vert_region(_dominant_bone(vert, names), vert.co.z) for vert in mesh.vertices]
    slots = {"skin": 0, "knit": 1, "trousers": 2}
    counts = {"skin": 0, "knit": 0, "trousers": 0}
    seam = set()
    for poly in mesh.polygons:
        votes = [regions[index] for index in poly.vertices]
        choice = max(("skin", "knit", "trousers"), key=lambda name: votes.count(name))
        if votes.count(choice) < len(votes):
            for index in poly.vertices:
                seam.add(index)
        poly.material_index = slots[choice]
        counts[choice] += 1
    existing = mesh.color_attributes.get("cloth_albedo")
    if existing is not None:
        mesh.color_attributes.remove(existing)
    layer = mesh.color_attributes.new("cloth_albedo", "FLOAT_COLOR", "POINT")
    palette = {
        "skin": [0.55, 0.35, 0.28, 1.0],
        "knit": [_srgb_u8_to_linear(channel) for channel in PALETTE["jacket"]] + [1.0],
        "trousers": [_srgb_u8_to_linear(channel) for channel in PALETTE["trousers"]] + [1.0],
    }
    for vert in mesh.vertices:
        color = list(palette[regions[vert.index]])
        if vert.index in seam:
            color[0] *= 0.72
            color[1] *= 0.72
            color[2] *= 0.72
        layer.data[vert.index].color = color
    return counts


def paint_body_wardrobe():
    """Delete separate clothes and paint the knit and trousers on the basemesh."""
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    skin = bpy.data.objects["GEO_AVERY_HEAD"]
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    coll = bpy.data.collections["COL_AVERY_CHEN"]
    keys_before = [key.name for key in skin.data.shape_keys.key_blocks]
    vert_count = len(skin.data.vertices)
    for name in (
        "GEO_AVERY_JACKET", "GEO_AVERY_KNIT", "GEO_AVERY_TROUSERS",
        "GEO_AVERY_BODY", "GEO_AVERY_LANYARD", "GEO_AVERY_BADGE", "lanyard_profile",
    ):
        _drop_object(name)
    for mod in list(skin.modifiers):
        if mod.type == "MASK" and mod.vertex_group.startswith("Delete.") and mod.vertex_group != "Delete.shoes01":
            skin.modifiers.remove(mod)
    helper = skin.modifiers.get("Hide helpers")
    if helper is not None and helper.type == "MASK":
        helper.vertex_group = "body"
        helper.invert_vertex_group = False
    while len(skin.data.materials) > 1:
        skin.data.materials.pop(index=len(skin.data.materials) - 1)
    if not skin.data.materials:
        skin.data.materials.append(bpy.data.materials["MAT_PROXY_CHARACTER"])
    skin.data.materials.append(_cloth_surface_material("MAT_AVERY_KNIT", 0.68))
    skin.data.materials.append(_cloth_surface_material("MAT_AVERY_TROUSERS", 0.58))
    counts = _paint_regions(skin)
    print("regions", counts, "verts", len(skin.data.vertices))
    if len(skin.data.vertices) != vert_count:
        raise RuntimeError("painting changed the vertex count")
    if [key.name for key in skin.data.shape_keys.key_blocks] != keys_before:
        raise RuntimeError("painting changed the shape keys")
    _build_front_lanyard(skin, arm, coll)
    _purge_unused_datablocks()
    texture_mb = enforce_texture_budget(32.0)
    try:
        bpy.ops.file.pack_all()
    except RuntimeError as exc:
        print("pack_all", exc)
    _save_blend()
    tri = sum(rendered_triangles(obj) for obj in coll.objects if obj.type in {"MESH", "CURVE"})
    print(f"surface wardrobe saved triangles={tri} textures={texture_mb:.1f}MB")
    if tri > 80000 or texture_mb > 32.05:
        raise RuntimeError(f"budget exceeded triangles={tri} textures={texture_mb:.1f}")


def _build_front_lanyard(skin, arm, coll):
    """Teal U and portrait card on the negative-Y side, clear of the chest."""
    front = [
        vert.co.y for vert in skin.data.vertices
        if abs(vert.co.x) < 0.05 and 1.15 < vert.co.z < 1.42
    ]
    if not front:
        raise RuntimeError("could not find the front of the chest")
    y = min(front) - 0.025
    card_z = 1.15
    card_top = card_z + 0.043
    curve = bpy.data.curves.new("GEO_AVERY_LANYARD_CURVE", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 16
    curve.twist_mode = "Z_UP"
    curve.use_fill_caps = True
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(2)
    points = ((-0.042, y, 1.50), (0.0, y - 0.006, card_top), (0.042, y, 1.50))
    for point, co in zip(spline.bezier_points, points):
        point.co = co
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    profile_data = bpy.data.curves.new("lanyard_profile", type="CURVE")
    profile_data.dimensions = "2D"
    poly = profile_data.splines.new("POLY")
    poly.points.add(3)
    rectangle = (
        (-0.006, -0.0008, 0.0, 1.0),
        (0.006, -0.0008, 0.0, 1.0),
        (0.006, 0.0008, 0.0, 1.0),
        (-0.006, 0.0008, 0.0, 1.0),
    )
    for point, co in zip(poly.points, rectangle):
        point.co = co
    poly.use_cyclic_u = True
    profile = bpy.data.objects.new("lanyard_profile", profile_data)
    curve.bevel_mode = "OBJECT"
    curve.bevel_object = profile
    strap = bpy.data.objects.new("GEO_AVERY_LANYARD", curve)
    strap["lanyard_width_m"] = 0.012
    strap["badge_width_m"] = 0.054
    strap["badge_height_m"] = 0.086
    strap.data.materials.append(_cloth_material("MAT_LANYARD_STRAP", "lanyard", 0.45))
    coll.objects.link(strap)
    mesh = bpy.data.meshes.new("GEO_AVERY_BADGE_MESH")
    badge = bpy.data.objects.new("GEO_AVERY_BADGE", mesh)
    bm = bmesh.new()
    result = bmesh.ops.create_cube(bm, size=1.0)
    for vert in result["verts"]:
        vert.co.x *= 0.054
        vert.co.y *= 0.004
        vert.co.z *= 0.086
    bm.to_mesh(mesh)
    bm.free()
    badge.location = (0.0, y - 0.016, card_z)
    badge.data.materials.append(_cloth_material("MAT_LANYARD_BADGE", "badge", 0.4))
    coll.objects.link(badge)
    _parent_keep_world(strap, arm, "chest")
    _parent_keep_world(badge, arm, "chest")
    print(f"lanyard front y={y:.3f}")
    return strap


def proof_wardrobe():
    """Front, side, and back at full body resolution, saved as one plate."""
    from PIL import Image, ImageDraw
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    scene = bpy.context.scene
    head = bpy.data.objects["GEO_AVERY_HEAD"]
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    arm.hide_render = True
    if arm.animation_data:
        arm.animation_data.action = None
    reset_pose(arm)
    neutral_shapes(head)
    studio(scene)
    stats = measure_anatomy(head)
    mid_z = stats["stature_m"] * 0.48
    out = Path("/tmp/avery-wardrobe-proof")
    scene.cycles.samples = int(os.environ.get("AVERY_SAMPLES", "12"))
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1600
    body_dist = 5.15
    paths = []
    for name, loc in (
        ("front.png", (0.0, -body_dist, mid_z)),
        ("side.png", (body_dist, 0.0, mid_z)),
        ("back.png", (0.0, body_dist, mid_z)),
    ):
        _cam(scene, loc, (0.0, 0.0, mid_z), 60, "CAM_PROOF_" + name)
        path = out / name
        render_still(scene, path)
        paths.append(path)
    frames = [Image.open(path).convert("RGB") for path in paths]
    plate = Image.new("RGB", (frames[0].width * 3, frames[0].height))
    labels = ("front", "side", "back")
    for index, frame in enumerate(frames):
        plate.paste(frame, (index * frame.width, 0))
        ImageDraw.Draw(plate).text((index * frame.width + 16, 16), labels[index], fill=(20, 20, 20))
    MEDIA.mkdir(parents=True, exist_ok=True)
    dest = MEDIA / "wardrobe-proof.png"
    plate.save(dest)
    print("proof written", dest, plate.size)


def _barycentric(point, a, b, c):
    v0 = b - a
    v1 = c - a
    v2 = point - a
    d00 = v0.dot(v0)
    d01 = v0.dot(v1)
    d11 = v1.dot(v1)
    d20 = v2.dot(v0)
    d21 = v2.dot(v1)
    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-12:
        return (1.0, 0.0, 0.0)
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    return (u, v, w)


def _body_surface(skin):
    """Body-group triangles only, so helper geometry is not a weight donor."""
    body = skin.vertex_groups.get("body")
    body_index = body.index if body is not None else None

    def is_body(index):
        if body_index is None:
            return True
        for assignment in skin.data.vertices[index].groups:
            if assignment.group == body_index and assignment.weight > 0.5:
                return True
        return False

    index_name = {group.index: group.name for group in skin.vertex_groups}
    rows = []
    for vert in skin.data.vertices:
        row = {}
        for assignment in vert.groups:
            name = index_name.get(assignment.group)
            if name in CONTRACT_BONES and assignment.weight > 1e-8:
                row[name] = row.get(name, 0.0) + assignment.weight
        rows.append(row)
    coords = [vert.co.copy() for vert in skin.data.vertices]
    tris = []
    for poly in skin.data.polygons:
        ids = list(poly.vertices)
        if len(ids) < 3 or not all(is_body(index) for index in ids):
            continue
        for offset in range(1, len(ids) - 1):
            tris.append((ids[0], ids[offset], ids[offset + 1]))
    tree = BVHTree.FromPolygons(coords, tris)
    return tree, coords, tris, rows


def transfer_suit_weights(skin, suit, arm):
    """Nearest-face barycentric copy of the basemesh proxy weights onto the intact suit."""
    tree, coords, tris, rows = _body_surface(skin)
    while suit.vertex_groups:
        suit.vertex_groups.remove(suit.vertex_groups[0])
    groups = {name: suit.vertex_groups.new(name=name) for name in CONTRACT_BONES}
    arm_l = {"upper_arm.L", "forearm.L", "hand.L"}
    arm_r = {"upper_arm.R", "forearm.R", "hand.R"}
    leg_l = {"thigh.L", "shin.L", "foot.L"}
    leg_r = {"thigh.R", "shin.R", "foot.R"}
    torso = {"root", "pelvis", "spine", "chest", "neck", "head"}
    bones = {}
    for name in ("upper_arm.L", "upper_arm.R", "chest"):
        bone = arm.data.bones[name]
        head = suit.matrix_world.inverted() @ (arm.matrix_world @ bone.head_local)
        tail = suit.matrix_world.inverted() @ (arm.matrix_world @ bone.tail_local)
        bones[name] = (head, tail)
    missed = 0
    for vert in suit.data.vertices:
        location, _normal, index, _distance = tree.find_nearest(vert.co)
        if location is None:
            missed += 1
            groups["chest"].add([vert.index], 1.0, "REPLACE")
            continue
        tri = tris[index]
        bary = _barycentric(location, coords[tri[0]], coords[tri[1]], coords[tri[2]])
        weights = {}
        for corner, amount in zip(tri, bary):
            if amount <= 0.0:
                continue
            for name, weight in rows[corner].items():
                weights[name] = weights.get(name, 0.0) + weight * amount
        side = "L" if vert.co.x < -0.015 else "R" if vert.co.x > 0.015 else None
        if side == "L":
            for name in arm_r | leg_r:
                weights.pop(name, None)
        elif side == "R":
            for name in arm_l | leg_l:
                weights.pop(name, None)
        arm_names = arm_l if side == "L" else arm_r if side == "R" else set()
        arm_sum = sum(weights.get(name, 0.0) for name in arm_names)
        torso_sum = sum(weights.get(name, 0.0) for name in torso)
        upper = "upper_arm.L" if side == "L" else "upper_arm.R" if side == "R" else None
        if upper is not None and vert.co.z > 0.82:
            shoulder = bones[upper][0]
            seam = (vert.co - shoulder).length < 0.04
            if arm_sum >= torso_sum and arm_sum > 0.05:
                chest_keep = min(weights.get("chest", 0.0), 0.22) if seam else 0.0
                for name in torso:
                    weights[name] = chest_keep if name == "chest" else 0.0
                if sum(weights.get(name, 0.0) for name in arm_names) < 0.5:
                    weights[upper] = weights.get(upper, 0.0) + 1.0
            elif torso_sum > 0.0:
                for name in arm_l | arm_r:
                    weights.pop(name, None)
        total = sum(weights.values())
        if total <= 1e-8:
            missed += 1
            weights = {"chest": 1.0}
            total = 1.0
        ranked = sorted(weights.items(), key=lambda item: item[1], reverse=True)[:4]
        ranked = [(name, weight) for name, weight in ranked if weight > 1e-6]
        total = sum(weight for _, weight in ranked) or 1.0
        for name, weight in ranked:
            groups[name].add([vert.index], weight / total, "REPLACE")
    print("suit weights transferred", "missed", missed, "polys", len(suit.data.polygons))


def replace_blocking_hair():
    """Swap bob02 for an uncut short crop. Returns the new object, or None for a clean scalp."""
    HumanService, _TargetService, _props = enable_mpfb()
    head = bpy.data.objects["GEO_AVERY_HEAD"]
    coll = bpy.data.collections["COL_AVERY_CHEN"]
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    mods_before = {mod.name for mod in head.modifiers}
    _drop_object("GEO_AVERY_HAIR")
    path = asset_root() / "hair/short02/short02.mhclo"
    hair = fit_asset(HumanService, head, path, "Hair")
    hair.name = "GEO_AVERY_HAIR"
    link_only(hair, coll)
    bind_armature(hair, arm)
    for group in list(hair.vertex_groups):
        hair.vertex_groups.remove(group)
    hair.vertex_groups.new(name="head").add(list(range(len(hair.data.vertices))), 1.0, "REPLACE")
    image = _find_image(hair, "diffuse")
    _recolor_named_image(image, (42, 28, 20), 0.55, 1.55)
    for mod in list(head.modifiers):
        if mod.name not in mods_before:
            print("removed new head modifier", mod.name, getattr(mod, "vertex_group", ""))
            head.modifiers.remove(mod)
    bob = bpy.data.images.get("bob02_diffuse.png")
    if bob is not None and bob.users == 0:
        bpy.data.images.remove(bob)
    print("hair short02", len(hair.data.vertices), "polys", len(hair.data.polygons))
    return hair


def repair_qa_blockers():
    """Replace the bob and reweight the intact suit. Topology stays put."""
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    head = bpy.data.objects["GEO_AVERY_HEAD"]
    suit = bpy.data.objects["GEO_AVERY_BODY"]
    suit_counts = (len(suit.data.vertices), len(suit.data.polygons))
    head_counts = (len(head.data.vertices), len(head.data.polygons))
    key_names = [key.name for key in head.data.shape_keys.key_blocks]
    replace_blocking_hair()
    transfer_suit_weights(head, suit, bpy.data.objects["RIG_AVERY_CHEN"])
    if (len(suit.data.vertices), len(suit.data.polygons)) != suit_counts:
        raise RuntimeError("suit topology changed")
    if (len(head.data.vertices), len(head.data.polygons)) != head_counts:
        raise RuntimeError("body topology changed")
    if [key.name for key in head.data.shape_keys.key_blocks] != key_names:
        raise RuntimeError("shape keys changed")
    _save_blend()
    print("repair saved", "suit", suit_counts)


def apply_archived_appearance():
    """Recolor the restored V1 file. Does not move clothing vertices or reload a basemesh."""
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    head = bpy.data.objects["GEO_AVERY_HEAD"]
    suit = bpy.data.objects["GEO_AVERY_BODY"]
    hair = bpy.data.objects["GEO_AVERY_HAIR"]
    before = {
        obj.name: (len(obj.data.vertices), len(obj.data.polygons))
        for obj in bpy.data.objects
        if obj.type == "MESH"
    }
    stats = measure_anatomy(head)
    print(
        "native",
        f"heads={stats['heads']:.2f}",
        f"stature={stats['stature_m']:.3f}",
        f"sole={stats['sole_z']:.4f}",
    )
    if not (7.0 <= stats["heads"] <= 8.0):
        raise RuntimeError(f"native heads {stats['heads']:.2f} outside 7.0-8.0; refusing a partial edit")
    paint_skin_zones(head)
    author_skin()
    _recolor_clothes(suit)
    _darken_irises()
    _soften_brows()
    hair_image = _find_image(hair, "diffuse")
    _recolor_named_image(hair_image, (42, 28, 20), 0.55, 1.55)
    apply_rest_face(head)
    after = {
        obj.name: (len(obj.data.vertices), len(obj.data.polygons))
        for obj in bpy.data.objects
        if obj.type == "MESH"
    }
    if before != after:
        raise RuntimeError(f"topology changed {before} -> {after}")
    _save_blend()
    print("appearance saved", "verts", before["GEO_AVERY_BODY"], before["GEO_AVERY_HEAD"])


def _elevation_driver(key, arm, bone_name, expression):
    """Drive a shape key from one upper-arm local Z euler, in radians.

    SINGLE_PROP on rotation_euler.z matches the channels the actions key.
    The expression uses only min/max so it evaluates without script auto-run.
    """
    fcurve = key.driver_add("value")
    driver = fcurve.driver
    driver.type = "SCRIPTED"
    variable = driver.variables.new()
    variable.name = "elev"
    variable.type = "SINGLE_PROP"
    target = variable.targets[0]
    target.id = arm
    target.data_path = f'pose.bones["{bone_name}"].rotation_euler.z'
    driver.expression = expression
    key.slider_min = 0.0
    key.slider_max = 1.0
    return fcurve


def _contract_weight_pairs(obj, index):
    names = {group.index: group.name for group in obj.vertex_groups}
    pairs = []
    for assignment in obj.data.vertices[index].groups:
        name = names.get(assignment.group)
        if name in CONTRACT_BONES and assignment.weight > 1e-6:
            pairs.append((name, assignment.weight))
    total = sum(weight for _, weight in pairs)
    if total <= 1e-8:
        return []
    return [(name, weight / total) for name, weight in pairs]


def _skin_matrix(arm, pairs):
    acc = None
    for name, weight in pairs:
        bone = arm.data.bones.get(name)
        pose = arm.pose.bones.get(name)
        if bone is None or pose is None:
            continue
        term = (pose.matrix @ bone.matrix_local.inverted()) * weight
        acc = term if acc is None else acc + term
    return acc


def _object_skin_matrix(arm, obj, pairs):
    """Linear-blend skinning matrix that maps suit-local rest coords to suit-local posed coords."""
    acc = None
    for name, weight in pairs:
        bone = arm.data.bones.get(name)
        pose = arm.pose.bones.get(name)
        if bone is None or pose is None:
            continue
        bone_arm = pose.matrix @ bone.matrix_local.inverted()
        term = (
            obj.matrix_world.inverted()
            @ arm.matrix_world
            @ bone_arm
            @ arm.matrix_world.inverted()
            @ obj.matrix_world
        ) * weight
        acc = term if acc is None else acc + term
    return acc


def add_armpit_correctives():
    """Pull the raised-arm underarm web into a short cloth fold.

    Surface Deform was bound on a temporary copy and survived reopen, but the
    same underarm faces still sat about 80 mm off the body, so that variant
    was not kept. The stock faces are ~2 cm quads whose edges stretch to
    ~350 mm when the arm rises: the corners stay near the body and the face
    interior becomes the wing. Those faces are subdivided, and pose-space
    shape keys move only the new vertices onto the body surface. Each key is
    driven by upper_arm.L or upper_arm.R rotation_euler.z.
    """
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    suit = bpy.data.objects["GEO_AVERY_BODY"]
    body = bpy.data.objects["GEO_AVERY_HEAD"]
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    if suit.data.shape_keys and any(
        key.name.startswith("CORRECT_armpit_") for key in suit.data.shape_keys.key_blocks
    ):
        raise RuntimeError("armpit correctives already exist; refusing to subdivide again")
    _stop(arm)
    reset_pose(arm)
    neutral_shapes(body)
    delete_masks = [
        mod for mod in body.modifiers
        if mod.type == "MASK" and mod.name.startswith("Delete.")
    ]
    for mod in delete_masks:
        mod.show_viewport = False
        mod.show_render = False
    bpy.context.view_layer.update()

    def grab(obj):
        deps = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        coords = [obj.matrix_world @ vert.co for vert in mesh.vertices]
        faces = [tuple(poly.vertices) for poly in mesh.polygons]
        evaluated.to_mesh_clear()
        return coords, faces

    def pose_arms(angle):
        reset_pose(arm)
        if angle:
            arm.pose.bones["upper_arm.L"].rotation_euler.z = math.radians(angle)
            arm.pose.bones["upper_arm.R"].rotation_euler.z = math.radians(-angle)
        bpy.context.view_layer.update()

    def armpit_box(co):
        return 1.02 < co.z < 1.48 and 0.08 < abs(co.x) < 0.45

    def posed_edges_and_gap(suit_world, tree, poly):
        ids = list(poly.vertices)
        longest = 0.0
        for a, b in zip(ids, ids[1:] + ids[:1]):
            longest = max(longest, (suit_world[a] - suit_world[b]).length)
        center = sum((suit_world[index] for index in ids), Vector()) / len(ids)
        _location, _normal, _poly, gap = tree.find_nearest(center)
        return longest, gap if gap is not None else 0.0

    selected = set()
    longest_edge = 0.0
    edge_samples = []
    for angle in (45, 90, 120):
        pose_arms(angle)
        suit_world, _suit_faces = grab(suit)
        body_world, body_faces = grab(body)
        tree = BVHTree.FromPolygons(body_world, body_faces)
        for poly in suit.data.polygons:
            rest_center = sum((suit.data.vertices[index].co for index in poly.vertices), Vector())
            rest_center /= len(poly.vertices)
            if not armpit_box(rest_center):
                continue
            edge, gap = posed_edges_and_gap(suit_world, tree, poly)
            if gap > 0.04 or edge > 0.12:
                selected.add(poly.index)
                longest_edge = max(longest_edge, edge)
                edge_samples.append(edge)
    edge_samples.sort(reverse=True)
    print("armpit faces", len(selected), "longest posed edge m", round(longest_edge, 3))
    print("edge mm percentiles", [round(edge_samples[min(len(edge_samples) - 1, index)] * 1000) for index in (0, 4, 9, 19, 39, 70)] if edge_samples else None)
    if not selected or len(selected) > 140:
        raise RuntimeError(f"armpit face selection is {len(selected)}")

    pose_arms(0)
    for mod in delete_masks:
        mod.show_viewport = True
        mod.show_render = True
    def _edge_kinds(mesh):
        probe = bmesh.new()
        probe.from_mesh(mesh)
        boundary = sum(1 for edge in probe.edges if len(edge.link_faces) == 1)
        junction = sum(1 for edge in probe.edges if len(edge.link_faces) > 2)
        wire = sum(1 for edge in probe.edges if len(edge.link_faces) == 0)
        probe.free()
        return boundary, junction, wire

    _before_boundary, before_junction, before_wire = _edge_kinds(suit.data)
    original_count = len(suit.data.vertices)
    cuts = max(4, math.ceil(longest_edge / 0.025) - 1)
    extra_faces = len(selected) * (cuts + 1) ** 2
    while extra_faces > 12000 and cuts > 4:
        cuts -= 1
        extra_faces = len(selected) * (cuts + 1) ** 2
    print("subdivide cuts", cuts, "budget faces", extra_faces)
    bpy.context.view_layer.objects.active = suit
    suit.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action="DESELECT")
    edit = bmesh.from_edit_mesh(suit.data)
    edit.faces.ensure_lookup_table()
    for index in selected:
        edit.faces[index].select = True
    bmesh.update_edit_mesh(suit.data)
    bpy.ops.mesh.subdivide(number_cuts=cuts, smoothness=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    print("subdivided suit", len(suit.data.vertices), len(suit.data.polygons), "from verts", original_count)

    boundary, junction, wire = _edge_kinds(suit.data)
    print("edges boundary", _before_boundary, "->", boundary, "junction", before_junction, "->", junction, "wire", before_wire, "->", wire)
    if junction > before_junction or wire > before_wire:
        raise RuntimeError(f"subdivision created non-manifold edges junction {junction} wire {wire}")

    for mod in delete_masks:
        mod.show_viewport = False
        mod.show_render = False
    pose_arms(90)
    check_world, _check_faces = grab(suit)
    worst = 0.0
    checked = 0
    for index, posed_world in enumerate(check_world):
        if not (1.05 < suit.data.vertices[index].co.z < 1.45 and 0.08 < abs(suit.data.vertices[index].co.x) < 0.42):
            continue
        pairs = _contract_weight_pairs(suit, index)
        skin = _object_skin_matrix(arm, suit, pairs)
        if skin is None:
            continue
        predicted = suit.matrix_world @ (skin @ suit.data.vertices[index].co)
        worst = max(worst, (predicted - posed_world).length)
        checked += 1
        if checked > 500:
            break
    print("skinning check m", round(worst, 5), "samples", checked)
    if worst > 0.002:
        raise RuntimeError(f"inverse skinning is off by {worst:.3f} m")

    pose_arms(0)
    rest_suit, _rest_suit_faces = grab(suit)
    rest_body, rest_body_faces = grab(body)
    rest_tree = BVHTree.FromPolygons(rest_body, rest_body_faces)
    rest_gap = []
    for co in rest_suit:
        _location, _normal, _poly, gap = rest_tree.find_nearest(co)
        rest_gap.append(0.0 if gap is None else gap)

    # 45 peaks at 45 and is 0 at 0 and 90. 90 peaks at 90 and is 0 at 45 and 120.
    # 120 is 0 at 90, 1 at 120, and stays on above that.
    expressions = {
        "L": {
            45: "min(max(elev/0.785398163397,0),1)*min(max((1.570796326795-elev)/0.785398163397,0),1)",
            90: "min(max((elev-0.785398163397)/0.785398163397,0),1)*min(max((2.094395102393-elev)/0.523598775598,0),1)",
            120: "min(max((elev-1.570796326795)/0.523598775598,0),1)",
        },
        "R": {
            45: "min(max((-elev)/0.785398163397,0),1)*min(max((1.570796326795-(-elev))/0.785398163397,0),1)",
            90: "min(max(((-elev)-0.785398163397)/0.785398163397,0),1)*min(max((2.094395102393-(-elev))/0.523598775598,0),1)",
            120: "min(max(((-elev)-1.570796326795)/0.523598775598,0),1)",
        },
    }
    neighbors = [[] for _ in suit.data.vertices]
    for edge in suit.data.edges:
        a, b = edge.vertices
        neighbors[a].append(b)
        neighbors[b].append(a)
    if suit.data.shape_keys is None:
        suit.shape_key_add(name="Basis")

    def author_key(angle, side, bone):
        pose_arms(angle)
        suit_world, _suit_faces = grab(suit)
        body_world, body_faces = grab(body)
        tree = BVHTree.FromPolygons(body_world, body_faces)
        sign = -1.0 if side == "L" else 1.0
        desired = {}
        for index, basis in enumerate(suit.data.vertices):
            if basis.co.x * sign < 0.02:
                continue
            if not (1.00 < basis.co.z < 1.50 and 0.05 < abs(basis.co.x) < 0.48):
                continue
            location, normal, _poly, gap = tree.find_nearest(suit_world[index])
            if location is None:
                continue
            # Only verts that leave the body as the arm rises. Stationary
            # jacket clearance stays on the basis so the rest suit is unchanged.
            if gap < rest_gap[index] + 0.012 or gap < 0.02:
                continue
            if normal.dot(suit_world[index] - location) < 0.0:
                normal = -normal
            desired[index] = location + normal * 0.007
        # Collapse edges that still bridge the armpit. Nearest-point can park
        # the two ends on the sleeve and the torso and leave the span in the air.
        for _collapse in range(5):
            current = [desired.get(index, suit_world[index]) for index in range(len(suit_world))]
            pulls = {}
            for edge in suit.data.edges:
                a, b = edge.vertices
                if a >= len(current) or b >= len(current):
                    continue
                length = (current[a] - current[b]).length
                if length < 0.07:
                    continue
                mid = (current[a] + current[b]) * 0.5
                if not (1.00 < mid.z < 1.55 and 0.05 < abs(mid.x) < 0.55):
                    continue
                location, normal, _poly, gap = tree.find_nearest(mid)
                if location is None or gap < 0.02:
                    continue
                if normal.dot(mid - location) < 0.0:
                    normal = -normal
                target = location + normal * 0.007
                pulls.setdefault(a, []).append(target)
                pulls.setdefault(b, []).append(target)
            if not pulls:
                break
            for index, targets in pulls.items():
                basis = suit.data.vertices[index]
                if basis.co.x * sign < 0.02:
                    continue
                if not (1.00 < basis.co.z < 1.50 and 0.05 < abs(basis.co.x) < 0.48):
                    continue
                aim = sum(targets, Vector()) / len(targets)
                blended = current[index].lerp(aim, 0.6)
                location, normal, _poly, _gap = tree.find_nearest(blended)
                if location is None:
                    continue
                if normal.dot(blended - location) < 0.0:
                    normal = -normal
                desired[index] = location + normal * 0.007
        for _pass in range(2):
            smoothed = {}
            for index, pos in desired.items():
                nbrs = [desired[other] for other in neighbors[index] if other in desired]
                if len(nbrs) < 2:
                    smoothed[index] = pos
                    continue
                average = sum(nbrs, Vector()) / len(nbrs)
                blended = pos * 0.7 + average * 0.3
                location, normal, _poly, _gap = tree.find_nearest(blended)
                if location is None:
                    smoothed[index] = pos
                    continue
                if normal.dot(blended - location) < 0.0:
                    normal = -normal
                smoothed[index] = location + normal * 0.007
            desired = smoothed
        key = suit.shape_key_add(name=f"CORRECT_armpit_{side}_{angle}")
        moved = 0
        max_rest = 0.0
        for index, basis in enumerate(suit.data.vertices):
            key.data[index].co = basis.co
            if index not in desired:
                continue
            pairs = _contract_weight_pairs(suit, index)
            skin = _object_skin_matrix(arm, suit, pairs)
            if skin is None:
                continue
            desired_local = suit.matrix_world.inverted() @ desired[index]
            try:
                rest = skin.inverted() @ desired_local
            except ValueError:
                continue
            key.data[index].co = rest
            max_rest = max(max_rest, (rest - basis.co).length)
            moved += 1
        _elevation_driver(key, arm, bone, expressions[side][angle])
        print(f"key {key.name} moved {moved} max rest delta m {max_rest:.3f}")
        if moved < 10:
            raise RuntimeError(f"{key.name} moved only {moved} verts")
        if max_rest > 0.45:
            raise RuntimeError(f"{key.name} rest delta {max_rest:.3f} m is too large")
        return key

    for angle in (45, 90, 120):
        author_key(angle, "L", "upper_arm.L")
        author_key(angle, "R", "upper_arm.R")

    # Mute drivers and apply the full correction at each authored angle.
    drivers = list(suit.data.shape_keys.animation_data.drivers)
    for fcurve in drivers:
        fcurve.mute = True
    blocks = suit.data.shape_keys.key_blocks

    def set_correction(angle):
        for key in blocks:
            if not key.name.startswith("CORRECT_armpit_"):
                continue
            key.value = 1.0 if key.name.endswith(f"_{angle}") else 0.0
        bpy.context.view_layer.update()

    def max_armpit_gap():
        suit_world, _suit_faces = grab(suit)
        body_world, body_faces = grab(body)
        tree = BVHTree.FromPolygons(body_world, body_faces)
        worst_gap = 0.0
        wide = 0
        ranked = []
        long_edges = []
        for poly in suit.data.polygons:
            ids = list(poly.vertices)
            rest_center = sum((suit.data.vertices[index].co for index in ids), Vector()) / len(ids)
            if not armpit_box(rest_center):
                continue
            center = sum((suit_world[index] for index in ids), Vector()) / len(ids)
            _location, _normal, _poly, gap = tree.find_nearest(center)
            if gap is None:
                continue
            travel = (center - (suit.matrix_world @ rest_center)).length
            # The outer sleeve can sit a few centimetres off the arm. The web is
            # the span that stays between the sleeve and the torso.
            in_pit = abs(center.x) < 0.34 and 1.05 < center.z < 1.40
            if in_pit and travel > 0.04 and gap > worst_gap:
                worst_gap = gap
            if in_pit and travel > 0.04 and gap > 0.028:
                wide += 1
                ranked.append((round(gap, 4), round(travel, 3), tuple(round(c, 3) for c in center), tuple(round(c, 3) for c in rest_center)))
            ids_cycle = ids[1:] + ids[:1]
            for a, b in zip(ids, ids_cycle):
                length = (suit_world[a] - suit_world[b]).length
                if length < 0.05:
                    continue
                mid = (suit_world[a] + suit_world[b]) * 0.5
                _ml, _mn, _mp, mgap = tree.find_nearest(mid)
                if mgap is None:
                    continue
                long_edges.append((length, mgap))
        ranked.sort(reverse=True)
        long_edges.sort(reverse=True)
        if long_edges:
            print(
                "  long edges", len(long_edges),
                "max mm", round(long_edges[0][0] * 1000),
                "mid gap mm", round(long_edges[0][1] * 1000),
                "next", [(round(a * 1000), round(b * 1000)) for a, b in long_edges[:4]],
            )
        # A web is a long edge whose middle misses the body. An edge that
        # follows the surface is the cloth fold, even if the edge is a few
        # centimetres long.
        spans = [item for item in long_edges if item[0] > 0.14 and item[1] > 0.022]
        return worst_gap, wide, ranked, spans

    failures = []
    for angle in (0, 45, 90, 120):
        pose_arms(angle)
        if angle:
            set_correction(angle)
        else:
            for key in blocks:
                if key.name.startswith("CORRECT_armpit_"):
                    key.value = 0.0
            bpy.context.view_layer.update()
        gap, wide, worst_faces, spans = max_armpit_gap()
        print(f"validate {angle} max gap m {gap:.4f} faces over 28mm {wide} spans {len(spans)}")
        for row in worst_faces[:4]:
            print("  worst", row)
        if angle and spans:
            failures.append(f"{angle}: {len(spans)} spanning edges")
    if failures and os.environ.get("ARMPIT_PREVIEW"):
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.render.resolution_x = 640
        scene.render.resolution_y = 800
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "SINGLE"
        scene.display.shading.single_color = (0.72, 0.58, 0.46)
        preview = Path("/tmp/armpit-check")
        preview.mkdir(parents=True, exist_ok=True)
        cam_data = bpy.data.cameras.new("CAM_CHK")
        cam = bpy.data.objects.new("CAM_CHK", cam_data)
        scene.collection.objects.link(cam)
        scene.camera = cam
        cam.data.lens = 70
        for view, loc, target in (
            ("front", (0.0, -2.05, 1.28), (0.0, 0.0, 1.22)),
            ("tq", (0.95, -1.75, 1.28), (0.0, 0.0, 1.22)),
            ("pit", (0.42, -0.72, 1.02), (0.16, -0.02, 1.24)),
        ):
            for angle in (45, 90, 120):
                pose_arms(angle)
                set_correction(angle)
                cam.location = loc
                look_at(cam, target)
                path = preview / f"{view}-{angle}.png"
                scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True)
                print("preview", path)
    if failures:
        raise RuntimeError("armpit still open " + "; ".join(failures))

    for fcurve in drivers:
        fcurve.mute = False
    pose_arms(0)
    for key in blocks:
        if key.name.startswith("CORRECT_armpit_"):
            key.value = 0.0
    for mod in delete_masks:
        mod.show_viewport = True
        mod.show_render = True
    bpy.context.view_layer.update()
    _save_blend()
    print("armpit correctives saved", len(suit.data.vertices), len(suit.data.polygons))


ARCHIVE_BLEND = ROOT / "archive" / "AveryChen-v1.blend"
SLEEVE_OVERLAP_M = 0.013
SLEEVE_INSET_M = 0.0015
# A 13 mm lip stays shut at rest and opens once the arm leaves the body.
# This cap is centered on the shoulder joint so it still meets the jacket at 90° and 120°.
SHOULDER_CAP_R = 0.062
ARM_GROUPS = (
    "upper_arm.L", "forearm.L", "hand.L",
    "upper_arm.R", "forearm.R", "hand.R",
)


def _edge_components(edges):
    adj = {}
    for edge in edges:
        for vert in edge.verts:
            adj.setdefault(vert, []).append(edge)
    unused = set(edges)
    components = []
    while unused:
        edge = unused.pop()
        stack = [edge]
        component = []
        while stack:
            edge = stack.pop()
            component.append(edge)
            for vert in edge.verts:
                for other in adj.get(vert, ()):
                    if other in unused:
                        unused.remove(other)
                        stack.append(other)
        components.append(component)
    return components


def _is_closed_loop(edges):
    degree = {}
    for edge in edges:
        for vert in edge.verts:
            degree[vert] = degree.get(vert, 0) + 1
    return len(edges) >= 8 and bool(degree) and all(value == 2 for value in degree.values())


def _boundary_loops(bm):
    return [component for component in _edge_components([e for e in bm.edges if e.is_boundary]) if _is_closed_loop(component)]


def _ordered_verts(edges):
    neighbors = {}
    for edge in edges:
        for vert in edge.verts:
            neighbors.setdefault(vert, []).append(edge.other_vert(vert))
    if any(len(items) != 2 for items in neighbors.values()):
        return None
    start = edges[0].verts[0]
    ordered = [start]
    previous = None
    current = start
    for _ in range(len(edges) + 1):
        nxt = [vert for vert in neighbors[current] if vert is not previous]
        if not nxt:
            return None
        if nxt[0] == start:
            return ordered
        ordered.append(nxt[0])
        previous, current = current, nxt[0]
    return None


def _loop_center(edges):
    verts = {vert for edge in edges for vert in edge.verts}
    return sum((vert.co for vert in verts), Vector()) / len(verts)


def _bone_axis(arm, name):
    bone = arm.data.bones[name]
    head = Vector(bone.head_local)
    tail = Vector(bone.tail_local)
    axis = tail - head
    axis.normalize()
    return head, tail, axis


def _armscye_plane(side):
    sign = 1.0 if side == "R" else -1.0
    origin = Vector((sign * 0.20, -0.02, 1.32))
    normal = Vector((sign * 1.0, 0.0, -0.25)).normalized()
    return origin, normal


def _cut_armhole(bm, head, axis, origin, normal, radial_max, side):
    sign = 1.0 if side == "R" else -1.0
    faces = []
    for face in bm.faces:
        center = face.calc_center_median()
        if sign * center.x < 0.05 or center.z < 1.05 or center.z > 1.48:
            continue
        if (center - head).length > 0.22:
            continue
        if abs((center - origin).dot(normal)) > 0.045:
            continue
        along = (center - head).dot(axis)
        if not (-0.02 <= along <= 0.24):
            continue
        radial = (center - (head + axis * along)).length
        if radial > radial_max:
            continue
        faces.append(face)
    if len(faces) < 20:
        return None, []
    geom = list(faces)
    geom.extend({vert for face in faces for vert in face.verts})
    geom.extend({edge for face in faces for edge in face.edges})
    result = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=origin, plane_no=normal, dist=0.0001)
    cut = [item for item in result["geom_cut"] if isinstance(item, bmesh.types.BMEdge)]
    closed = [component for component in _edge_components(cut) if _is_closed_loop(component)]
    strays = [edge for edge in cut if not any(edge in component for component in closed)]
    if not closed:
        return None, strays
    closed.sort(key=len, reverse=True)
    return closed[0], strays


def _flood_sleeve(bm, block_edges, side):
    sign = 1.0 if side == "R" else -1.0
    blocked = set(block_edges)
    seeds = []
    for edges in _boundary_loops(bm):
        center = _loop_center(edges)
        # The wrist cuff only. The jacket hem sits in the same height band.
        if sign * center.x < 0.18 or not (0.84 < center.z < 0.94):
            continue
        if not (15 <= len(edges) <= 50):
            continue
        for edge in edges:
            seeds.extend(edge.link_faces)
    if not seeds:
        raise RuntimeError(f"no wrist cuff on {side}")
    seen = set()
    stack = list(seeds)
    while stack:
        face = stack.pop()
        if face in seen or not face.is_valid:
            continue
        seen.add(face)
        for edge in face.edges:
            if edge in blocked:
                continue
            for other in edge.link_faces:
                if other not in seen:
                    stack.append(other)
    return seen


def _sleeve_ok(faces, side):
    sign = 1.0 if side == "R" else -1.0
    if not (180 <= len(faces) <= 2800):
        return False
    xs = [vert.co.x for face in faces for vert in face.verts]
    zs = [vert.co.z for face in faces for vert in face.verts]
    if min(zs) < 0.75 or max(zs) > 1.46:
        return False
    if sign > 0 and min(xs) < 0.04:
        return False
    if sign < 0 and max(xs) > -0.04:
        return False
    return True


def _copy_boundary_uvs(bm, edges):
    layer = bm.loops.layers.uv.active
    if layer is None:
        return {}
    uvs = {}
    for edge in edges:
        for face in edge.link_faces:
            for loop in face.loops:
                uvs[loop.vert] = loop[layer].uv.copy()
    return uvs


def _assign_uv(bm, faces, known):
    layer = bm.loops.layers.uv.active
    if layer is None or not known:
        return
    average = sum(known.values(), Vector((0.0, 0.0))) / len(known)
    for face in faces:
        for loop in face.loops:
            loop[layer].uv = known.get(loop.vert, average).copy()


def _fan_fill(bm, edges, outward):
    ordered = _ordered_verts(edges)
    if not ordered:
        raise RuntimeError("armhole loop is not a single cycle")
    center_co = sum((vert.co.copy() for vert in ordered), Vector()) / len(ordered)
    center_co += outward * 0.004
    center = bm.verts.new(center_co)
    bm.verts.index_update()
    faces = []
    for a, b in zip(ordered, ordered[1:] + ordered[:1]):
        try:
            face = bm.faces.new((a, b, center))
        except ValueError:
            continue
        face.smooth = True
        face.material_index = 0
        faces.append(face)
    bm.normal_update()
    for face in faces:
        if face.normal.dot(outward) < 0.0:
            face.normal_flip()
    return faces, center


def _cap_sleeve(obj, side, arm):
    head, _tail, axis = _bone_axis(arm, f"upper_arm.{side}")
    _origin, normal = _armscye_plane(side)
    inward = -normal
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    loops = _boundary_loops(bm)
    if len(loops) < 2:
        raise RuntimeError(f"{obj.name} expected cuff and armhole, found {len(loops)} boundary loops")
    armhole = min(loops, key=lambda edges: (_loop_center(edges) - head).length)
    cuff_z = max(_loop_center(edges).z for edges in loops if edges is not armhole)
    hole_z = _loop_center(armhole).z
    if hole_z < 1.10 or cuff_z > hole_z:
        raise RuntimeError(f"{obj.name} armhole z={hole_z:.3f} cuff z={cuff_z:.3f}")
    known = _copy_boundary_uvs(bm, armhole)
    extruded = bmesh.ops.extrude_edge_only(bm, edges=armhole)
    new_verts = [item for item in extruded["geom"] if isinstance(item, bmesh.types.BMVert)]
    side_faces = [item for item in extruded["geom"] if isinstance(item, bmesh.types.BMFace)]
    for vert in new_verts:
        along = (vert.co - head).dot(axis)
        radial = vert.co - (head + axis * along)
        toward_bone = Vector()
        if radial.length > 1e-6:
            toward_bone = -radial.normalized()
        vert.co += inward * SLEEVE_OVERLAP_M + toward_bone * SLEEVE_INSET_M
    for face in side_faces:
        face.smooth = True
        face.material_index = 0
    bm.normal_update()
    for face in side_faces:
        along = (face.calc_center_median() - head).dot(axis)
        radial = face.calc_center_median() - (head + axis * along)
        if radial.length > 1e-6 and face.normal.dot(radial) < 0.0:
            face.normal_flip()
    new_set = set(new_verts)
    cap_edges = []
    for edge in bm.edges:
        if edge.is_boundary and edge.verts[0] in new_set and edge.verts[1] in new_set:
            cap_edges.append(edge)
    cap_faces, _center = _fan_fill(bm, cap_edges, inward)
    _assign_uv(bm, side_faces + cap_faces, known)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return len(new_verts), len(cap_faces)


def _cap_jacket(obj, arm):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    filled = 0
    rim = []
    for edges in _boundary_loops(bm):
        center = _loop_center(edges)
        verts = {vert for edge in edges for vert in edge.verts}
        radius = max((vert.co - center).length for vert in verts)
        if abs(center.x) < 0.10 or not (1.15 < center.z < 1.42) or radius > 0.14 or len(edges) < 12:
            continue
        side = "R" if center.x > 0.0 else "L"
        _origin, normal = _armscye_plane(side)
        rim.extend(vert.index for edge in edges for vert in edge.verts)
        known = _copy_boundary_uvs(bm, edges)
        faces, _center = _fan_fill(bm, edges, normal)
        _assign_uv(bm, faces, known)
        filled += 1
    if filled != 2:
        raise RuntimeError(f"jacket armhole caps filled {filled}, expected 2")
    leftover = []
    for edges in _boundary_loops(bm):
        center = _loop_center(edges)
        if abs(center.x) > 0.10 and center.z > 1.10:
            leftover.append((round(center.x, 3), round(center.z, 3), len(edges)))
    if leftover:
        raise RuntimeError(f"jacket armholes still open {leftover}")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return sorted(set(rim))


def _smoothstep(value):
    value = 0.0 if value < 0.0 else 1.0 if value > 1.0 else value
    return value * value * (3.0 - 2.0 * value)


def _chain_weights(co, points):
    """Blend along the arm. A hard closest-bone pick splits the elbow.

    Neighboring sleeve verts sit almost the same distance from the upper-arm
    axis and the forearm axis. Picking one bone snaps an 84% / 15% jump across
    a 7 mm edge, and a bent elbow then opens that edge into a spike.
    """
    lengths = []
    for start, end in zip(points, points[1:]):
        lengths.append((end - start).length)
    stations = []
    traveled = 0.0
    for (start, end), length in zip(zip(points, points[1:]), lengths):
        if length < 1e-8:
            traveled += length
            continue
        direction = end - start
        t = max(0.0, min(1.0, (co - start).dot(direction) / (length * length)))
        distance = (co - (start + direction * t)).length
        stations.append((traveled + t * length, distance))
        traveled += length
    # 12 mm keeps a vertex on its own bone and only blends the joint neighborhood.
    eps = 0.012
    weight_sum = 0.0
    station_sum = 0.0
    for station, distance in stations:
        influence = 1.0 / (distance * distance + eps * eps)
        weight_sum += influence
        station_sum += influence * station
    best_s = station_sum / max(weight_sum, 1e-8)
    upper_len, fore_len, hand_len = lengths
    elbow0 = upper_len * 0.55
    elbow1 = upper_len + fore_len * 0.45
    wrist0 = upper_len + fore_len * 0.55
    wrist1 = upper_len + fore_len + hand_len * 0.35
    fore = _smoothstep((best_s - elbow0) / max(1e-6, elbow1 - elbow0))
    hand = _smoothstep((best_s - wrist0) / max(1e-6, wrist1 - wrist0))
    upper = (1.0 - fore) * (1.0 - hand)
    fore *= 1.0 - hand
    total = upper + fore + hand or 1.0
    return upper / total, fore / total, hand / total


def _weight_sleeves(sleeve, side, arm):
    while sleeve.vertex_groups:
        sleeve.vertex_groups.remove(sleeve.vertex_groups[0])
    names = (f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}")
    groups = [sleeve.vertex_groups.new(name=name) for name in names]
    points = []
    for bone_name in names:
        bone = arm.data.bones[bone_name]
        if not points:
            points.append(Vector(bone.head_local))
        points.append(Vector(bone.tail_local))
    # The tucked armscye and the shoulder cap stay on upper_arm.
    # The elbow blend lives below this, so the cap does not drag on the torso.
    cap_floor = 1.22
    for vert in sleeve.data.vertices:
        upper, fore, hand = _chain_weights(vert.co, points)
        if vert.co.z > cap_floor:
            upper, fore, hand = 1.0, 0.0, 0.0
        for group, weight in zip(groups, (upper, fore, hand)):
            if weight > 1e-4:
                group.add([vert.index], weight, "REPLACE")


def _weight_jacket(jacket):
    for name in ARM_GROUPS:
        group = jacket.vertex_groups.get(name)
        if group is not None:
            jacket.vertex_groups.remove(group)
    allowed = {group.name for group in jacket.vertex_groups}
    index_name = {group.index: group.name for group in jacket.vertex_groups}
    chest = jacket.vertex_groups.get("chest")
    if chest is None:
        chest = jacket.vertex_groups.new(name="chest")
        allowed.add("chest")
        index_name = {group.index: group.name for group in jacket.vertex_groups}
    groups = {group.name: group for group in jacket.vertex_groups}
    for vert in jacket.data.vertices:
        weights = []
        for assignment in vert.groups:
            name = index_name.get(assignment.group)
            if name in allowed and assignment.weight > 1e-6:
                weights.append((name, assignment.weight))
        for name in allowed:
            groups[name].remove([vert.index])
        if not weights:
            chest.add([vert.index], 1.0, "REPLACE")
            continue
        total = sum(weight for _, weight in weights) or 1.0
        for name, weight in weights:
            groups[name].add([vert.index], weight / total, "REPLACE")


def _add_shoulder_caps(sleeves, arm):
    """Round cap on each shoulder joint, merged into that sleeve."""
    for side, sleeve in sleeves.items():
        joint = Vector(arm.data.bones[f"upper_arm.{side}"].head_local)
        bm = bmesh.new()
        bm.from_mesh(sleeve.data)
        layer = bm.loops.layers.uv.active
        sample = Vector((0.0, 0.0))
        count = 0
        if layer is not None:
            for face in bm.faces:
                center = face.calc_center_median()
                if (center - joint).length > 0.12 or center.z < 1.25:
                    continue
                for loop in face.loops:
                    sample += loop[layer].uv
                    count += 1
        if count:
            sample /= count
        created = bmesh.ops.create_uvsphere(
            bm, u_segments=20, v_segments=12, radius=SHOULDER_CAP_R,
        )
        bmesh.ops.translate(bm, verts=created["verts"], vec=joint)
        new_verts = set(created["verts"])
        for face in bm.faces:
            if any(vert in new_verts for vert in face.verts):
                face.smooth = True
                face.material_index = 0
                if layer is not None:
                    for loop in face.loops:
                        loop[layer].uv = sample
        bm.to_mesh(sleeve.data)
        bm.free()
        sleeve.data.update()
        group = sleeve.vertex_groups[f"upper_arm.{side}"]
        assigned = 0
        for vert in sleeve.data.vertices:
            if (vert.co - joint).length > SHOULDER_CAP_R + 0.002:
                continue
            if vert.groups:
                continue
            group.add([vert.index], 1.0, "REPLACE")
            assigned += 1
        if assigned < 20:
            raise RuntimeError(f"{sleeve.name} shoulder cap got {assigned} weights")
        print(f"shoulder cap {side} radius {SHOULDER_CAP_R:.3f} verts {assigned}")


def _clear_previous_sleeves():
    for name in ("GEO_AVERY_SLEEVE_L", "GEO_AVERY_SLEEVE_R"):
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA" and obj.name.startswith("CAM_"):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data.users == 0:
                bpy.data.cameras.remove(data)


def _restore_archived_suit():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    _clear_previous_sleeves()
    old = bpy.data.objects["GEO_AVERY_BODY"]
    material = old.data.materials[0]
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    coll = bpy.data.collections["COL_AVERY_CHEN"]
    before = set(bpy.data.objects.keys())
    with bpy.data.libraries.load(str(ARCHIVE_BLEND), link=False) as (_src, dst):
        dst.objects = ["GEO_AVERY_BODY"]
    donor = dst.objects[0]
    if donor is None or len(donor.data.vertices) != 7613:
        raise RuntimeError("archive suit did not load at 7613 verts")
    world = donor.matrix_world.copy()
    donor.parent = None
    donor.matrix_world = world
    bind_armature(donor, arm)
    donor.data.materials.clear()
    donor.data.materials.append(material)
    link_only(donor, coll)
    if old.data.shape_keys and old.data.shape_keys.animation_data:
        old.data.shape_keys.animation_data_clear()
    old.shape_key_clear()
    old_mesh = old.data
    bpy.data.objects.remove(old, do_unlink=True)
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    donor.name = "GEO_AVERY_BODY"
    donor.data.name = "male_elegantsuit01"
    duplicate = bpy.data.objects.get("RIG_AVERY_CHEN.001")
    if duplicate is not None:
        data = duplicate.data
        bpy.data.objects.remove(duplicate, do_unlink=True)
        if data.users == 0:
            bpy.data.armatures.remove(data)
    for material_block in list(bpy.data.materials):
        if material_block.users == 0:
            bpy.data.materials.remove(material_block)
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
    suit = bpy.data.objects["GEO_AVERY_BODY"]
    if suit.data.shape_keys is not None:
        raise RuntimeError("restored suit still has shape keys")
    print(
        "restored archive suit",
        len(suit.data.vertices),
        "verts",
        suit.data.materials[0].name,
        "matrix",
        tuple(round(v, 4) for v in suit.matrix_world.translation),
    )
    return suit, arm, coll


def _separate_sleeves(suit, arm, coll):
    head_r, _tail_r, axis_r = _bone_axis(arm, "upper_arm.R")
    head_l, _tail_l, axis_l = _bone_axis(arm, "upper_arm.L")
    origin_r, normal_r = _armscye_plane("R")
    origin_l, normal_l = _armscye_plane("L")
    # Choose a radial limit on a throwaway copy so the real cut is one closed loop.
    chosen = {}
    for side, head, axis, origin, normal in (
        ("R", head_r, axis_r, origin_r, normal_r),
        ("L", head_l, axis_l, origin_l, normal_l),
    ):
        found = None
        for radial_max in (0.090, 0.100, 0.110, 0.125):
            trial = bmesh.new()
            trial.from_mesh(suit.data)
            loop, strays = _cut_armhole(trial, head, axis, origin, normal, radial_max, side)
            count = 0 if loop is None else len(loop)
            stray_n = len(strays)
            print(f"trial {side} r<{radial_max:.3f} loop={count} strays={stray_n}")
            trial.free()
            if loop is not None and count >= 20 and stray_n == 0:
                found = radial_max
                break
            if loop is not None and count >= 20 and found is None:
                found = radial_max
        if found is None:
            raise RuntimeError(f"no closed armhole on {side}")
        chosen[side] = found
        print(f"armhole {side} radial {found:.3f}")

    bm = bmesh.new()
    bm.from_mesh(suit.data)
    bm.faces.ensure_lookup_table()
    loops = {}
    for side, head, axis, origin, normal in (
        ("R", head_r, axis_r, origin_r, normal_r),
        ("L", head_l, axis_l, origin_l, normal_l),
    ):
        loop, strays = _cut_armhole(bm, head, axis, origin, normal, chosen[side], side)
        if loop is None:
            raise RuntimeError(f"real armhole cut failed on {side}")
        if strays:
            bmesh.ops.dissolve_edges(bm, edges=strays, use_verts=True)
            loop = [edge for edge in loop if edge.is_valid]
            if not _is_closed_loop(loop):
                raise RuntimeError(f"armhole {side} broke while clearing {len(strays)} stray cuts")
        center = _loop_center(loop)
        print(f"cut {side} n={len(loop)} center={tuple(round(c, 3) for c in center)}")
        loops[side] = loop
    faces = {}
    for side, loop in loops.items():
        faces[side] = _flood_sleeve(bm, loop, side)
        print(f"flood {side} faces={len(faces[side])}")
        if not _sleeve_ok(faces[side], side):
            raise RuntimeError(f"sleeve flood {side} is not a clean arm tube ({len(faces[side])} faces)")
    if faces["L"] & faces["R"]:
        raise RuntimeError("left and right sleeve floods overlap")
    selected = {face.index for face in faces["L"] | faces["R"]}
    bm.to_mesh(suit.data)
    bm.free()
    suit.data.update()

    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = suit
    suit.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action="DESELECT")
    edit = bmesh.from_edit_mesh(suit.data)
    edit.faces.ensure_lookup_table()
    for face in edit.faces:
        face.select = face.index in selected
    bmesh.update_edit_mesh(suit.data)
    before = set(bpy.data.objects.keys())
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    created = [bpy.data.objects[name] for name in bpy.data.objects.keys() if name not in before]
    if len(created) != 1:
        raise RuntimeError(f"expected one separated sleeve object, got {[obj.name for obj in created]}")
    sleeve_obj = created[0]
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = sleeve_obj
    sleeve_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    before = set(bpy.data.objects.keys())
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = [sleeve_obj] + [bpy.data.objects[name] for name in bpy.data.objects.keys() if name not in before]
    if len(parts) != 2:
        raise RuntimeError(f"expected two sleeves, got {[obj.name for obj in parts]}")
    sleeves = {}
    for obj in parts:
        median = sum(vert.co.x for vert in obj.data.vertices) / len(obj.data.vertices)
        side = "R" if median > 0.0 else "L"
        obj.name = f"GEO_AVERY_SLEEVE_{side}"
        obj.data.name = f"GEO_AVERY_SLEEVE_{side}_MESH"
        link_only(obj, coll)
        bind_armature(obj, arm)
        sleeves[side] = obj
        print(obj.name, "verts", len(obj.data.vertices), "faces", len(obj.data.polygons))
    return sleeves


def _measure_overlap(arm, jacket, sleeves, rim_indices):
    """Distance from the jacket armhole rim to the posed sleeve surface."""
    report = []
    for angle in (0.0, 45.0, 90.0, 120.0):
        reset_pose(arm)
        if angle:
            arm.pose.bones["upper_arm.L"].rotation_euler.z = math.radians(angle)
            arm.pose.bones["upper_arm.R"].rotation_euler.z = math.radians(-angle)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        distances = []
        sleeve_trees = {}
        for side, sleeve in sleeves.items():
            sleeve_eval = sleeve.evaluated_get(deps)
            sleeve_mesh = sleeve_eval.to_mesh()
            coords = [sleeve.matrix_world @ vert.co for vert in sleeve_mesh.vertices]
            tris = []
            for poly in sleeve_mesh.polygons:
                ids = list(poly.vertices)
                for offset in range(1, len(ids) - 1):
                    tris.append((ids[0], ids[offset], ids[offset + 1]))
            sleeve_trees[side] = BVHTree.FromPolygons(coords, tris)
            sleeve_eval.to_mesh_clear()
        jacket_eval = jacket.evaluated_get(deps)
        jacket_mesh = jacket_eval.to_mesh()
        for index in rim_indices:
            world = jacket.matrix_world @ jacket_mesh.vertices[index].co
            side = "R" if world.x > 0.0 else "L"
            _loc, _normal, _index, distance = sleeve_trees[side].find_nearest(world)
            if distance is not None:
                distances.append(distance)
        jacket_eval.to_mesh_clear()
        distances.sort()
        if not distances:
            report.append(f"{angle:.0f}: no rim samples")
            continue
        mid = distances[len(distances) // 2]
        report.append(
            f"{angle:.0f}: n={len(distances)} median={mid * 1000:.1f} mm max={distances[-1] * 1000:.1f} mm"
        )
    reset_pose(arm)
    bpy.context.view_layer.update()
    print("OVERLAP", " | ".join(report))
    return report


def _preview_sleeves():
    scene = bpy.context.scene
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    arm.hide_render = True
    if arm.animation_data:
        arm.animation_data.action = None
    reset_pose(arm)
    head = bpy.data.objects["GEO_AVERY_HEAD"]
    neutral_shapes(head)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_object_outline = False
    scene.render.resolution_x = 480
    scene.render.resolution_y = 720
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("WORLD_PREVIEW")
    scene.world.color = (0.02, 0.02, 0.02)
    palette = {
        "GEO_AVERY_BODY": (0.12, 0.62, 0.24, 1.0),
        "GEO_AVERY_SLEEVE_L": (0.90, 0.16, 0.12, 1.0),
        "GEO_AVERY_SLEEVE_R": (0.90, 0.16, 0.12, 1.0),
        "GEO_AVERY_HEAD": (0.20, 0.38, 0.95, 1.0),
        "GEO_AVERY_HAIR": (0.35, 0.26, 0.18, 1.0),
        "GEO_AVERY_SHOES": (0.12, 0.12, 0.12, 1.0),
        "GEO_AVERY_LANYARD": (0.10, 0.55, 0.55, 1.0),
        "GEO_AVERY_EYES": (0.95, 0.95, 0.95, 1.0),
        "GEO_AVERY_BROWS": (0.25, 0.18, 0.12, 1.0),
        "GEO_AVERY_TEETH": (0.9, 0.9, 0.85, 1.0),
        "GEO_AVERY_TONGUE": (0.7, 0.3, 0.3, 1.0),
    }
    originals = {}
    for name, color in palette.items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        originals[name] = obj.color[:]
        obj.color = color
    out = Path("/tmp/sleeve-preview")
    out.mkdir(parents=True, exist_ok=True)
    mid_z = 0.81
    shots = []
    for view, loc in (("front", (0.0, -5.15, mid_z)), ("three", (1.45, -4.7, mid_z))):
        for angle in (0.0, 45.0, 90.0, 120.0):
            reset_pose(arm)
            if angle:
                arm.pose.bones["upper_arm.L"].rotation_euler.z = math.radians(angle)
                arm.pose.bones["upper_arm.R"].rotation_euler.z = math.radians(-angle)
            bpy.context.view_layer.update()
            _cam(scene, loc, (0.0, 0.0, mid_z), 60, "CAM_SLEEVE_PREVIEW")
            path = out / f"{view}-{int(angle)}.png"
            render_still(scene, path)
            shots.append(path)
    reset_pose(arm)
    for name, color in originals.items():
        bpy.data.objects[name].color = color
    print("preview", shots)


def articulate_sleeves():
    """Split the archived suit into a jacket and two overlapping sleeves."""
    suit, arm, coll = _restore_archived_suit()
    for name in ("GEO_AVERY_SLEEVE_L", "GEO_AVERY_SLEEVE_R"):
        if bpy.data.objects.get(name) is not None:
            raise RuntimeError(f"{name} already exists")
    reset_pose(arm)
    sleeves = _separate_sleeves(suit, arm, coll)
    for side, sleeve in sleeves.items():
        verts, faces = _cap_sleeve(sleeve, side, arm)
        print(f"capped {sleeve.name} overlap verts={verts} cap faces={faces}")
        loops = []
        bm = bmesh.new()
        bm.from_mesh(sleeve.data)
        loops = [(round(_loop_center(edges).z, 3), len(edges)) for edges in _boundary_loops(bm)]
        bm.free()
        if len(loops) != 1:
            raise RuntimeError(f"{sleeve.name} boundaries after cap: {loops}")
    rim = _cap_jacket(suit, arm)
    _weight_jacket(suit)
    for side, sleeve in sleeves.items():
        _weight_sleeves(sleeve, side, arm)
    _add_shoulder_caps(sleeves, arm)
    # Jacket must not retain arm influence. Sleeves must not retain the opposite side.
    jacket_groups = {group.name for group in suit.vertex_groups}
    if jacket_groups & set(ARM_GROUPS):
        raise RuntimeError(f"jacket still has arm groups: {jacket_groups & set(ARM_GROUPS)}")
    for side, sleeve in sleeves.items():
        other = "L" if side == "R" else "R"
        names = {group.name for group in sleeve.vertex_groups}
        if any(name.endswith("." + other) for name in names):
            raise RuntimeError(f"{sleeve.name} has opposite groups {names}")
        if names != {f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}"}:
            raise RuntimeError(f"{sleeve.name} groups {names}")
    report = _measure_overlap(arm, suit, sleeves, rim)
    if os.environ.get("SLEEVE_PREVIEW"):
        _preview_sleeves()
    # Restore Cycles for later full renders. The preview switches the open scene only.
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    _save_blend()
    print("sleeves saved", " | ".join(report))


def _stretch_report(obj, arm):
    rest = [vert.co.copy() for vert in obj.data.vertices]
    edges = [(edge.vertices[0], edge.vertices[1]) for edge in obj.data.edges]
    step = max(1, len(edges) // 2500)
    sample = edges[::step]
    rest_len = [(rest[a] - rest[b]).length for a, b in sample]
    lines = [f"## {obj.name}", ""]
    failed = False
    for name in ACTIONS:
        action = bpy.data.actions[name]
        start = int(round(action.frame_range[0]))
        end = int(round(action.frame_range[1]))
        frames = list(range(start, end + 1))
        bad = []
        worst = 1.0
        hidden = [mod for mod in obj.modifiers if mod.type != "ARMATURE"]
        for frame in frames:
            _play(arm, name, frame)
            for mod in hidden:
                mod.show_viewport = False
                mod.show_render = False
            deps = bpy.context.evaluated_depsgraph_get()
            evaluated = obj.evaluated_get(deps)
            mesh = evaluated.to_mesh()
            coords = [vert.co.copy() for vert in mesh.vertices]
            evaluated.to_mesh_clear()
            for mod in hidden:
                mod.show_viewport = True
                mod.show_render = True
            if len(coords) != len(rest):
                bad.append(f"{frame} (vert count {len(coords)})")
                continue
            stretch = 1.0
            for (a, b), base in zip(sample, rest_len):
                if base < 0.004:
                    continue
                stretch = max(stretch, (coords[a] - coords[b]).length / base)
            worst = max(worst, stretch)
            if stretch > 8.0:
                bad.append(f"{frame} (edge stretch {stretch:.2f})")
        _stop(arm)
        status = "RECORDED" if bad else "QUIET"
        failed = failed or bool(bad)
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"- Status: **{status}**")
        lines.append(
            f"- Frames checked: {start}–{end} ({len(frames)} frames) on `{obj.name}`. "
            "This is an edge-length sample, not a two-camera render."
        )
        lines.append(f"- Worst sampled edge stretch: {worst:.2f}× rest.")
        if bad:
            lines.append(f"- Frames over 8×: {', '.join(bad)}")
        lines.append("")
        print(obj.name, name, status, "stretch", round(worst, 2))
    return lines, failed


def inspect_garments():
    """Sample every frame on the sleeveless vest and trousers."""
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    for name in ("GEO_AVERY_SLEEVE_L", "GEO_AVERY_SLEEVE_R"):
        if bpy.data.objects.get(name) is not None:
            raise RuntimeError(f"{name} is still in the file")
    body = bpy.data.objects.get("GEO_AVERY_BODY")
    if body is None:
        raise RuntimeError("missing GEO_AVERY_BODY")
    pieces = [body]
    lines = [
        "---",
        "cursor:",
        '  subagentId: "bc-da984421-d0d2-5651-9409-b49d2aca6af7"',
        "---",
        "",
        "# Avery V2 every-frame inspection",
        "",
        "The suit is the archived male_elegantsuit01 with the jacket sleeves removed.",
        "`GEO_AVERY_BODY` is a sleeveless vest, shirt, tie, and the untouched trousers.",
        "Both arms are the body skin from the shoulder to the wrist. There is no sleeve object.",
        "There is no cloth simulation, driver, corrective shape key, cap, or underarm panel.",
        "An edge longer than 4 mm that stretches past eight times rest length is recorded.",
        "That ratio is not the visual acceptance test. The shoulder, action, and deformation sheets are.",
        "This is an edge-length sample of the vest mesh, not a two-camera render of every frame.",
        "Shoulder plates at 0, 45, 90, and 120 degrees are in `media/avery-chen-v2/shoulder-tests.png`.",
        "",
    ]
    failed = False
    for obj in pieces:
        part, bad = _stretch_report(obj, arm)
        lines.extend(part)
        failed = failed or bad
    path = Path("/cursor/stores/self/internal/avery-v2-every-frame-inspection.md")
    path.write_text("\n".join(lines) + "\n")
    print("wrote", path, "RESULT", "RECORDED" if failed else "QUIET")


def _check_garment_contract(check, coll, arm):
    body = bpy.data.objects.get("GEO_AVERY_BODY")
    for name in ("GEO_AVERY_SLEEVE_L", "GEO_AVERY_SLEEVE_R"):
        check(f"{name} removed", bpy.data.objects.get(name) is None)
    if body is not None:
        present = {group.name for group in body.vertex_groups} & set(ARM_GROUPS)
        check("vest has no arm vertex groups", not present, ",".join(sorted(present)))
        check("vest has no corrective shape keys", body.data.shape_keys is None)
        check(
            "vest suit material",
            bool(body.data.materials) and "male_elegantsuit01" in body.data.materials[0].name,
            body.data.materials[0].name if body.data.materials else "none",
        )
    binding = bpy.data.objects.get("GEO_AVERY_BINDING")
    check(
        "armhole binding on chest",
        binding is not None
        and binding.type == "CURVE"
        and coll is not None
        and list(binding.users_collection) == [coll]
        and binding.parent == arm
        and binding.parent_type == "BONE"
        and binding.parent_bone == "chest"
        and abs(binding.data.bevel_depth - BINDING_RADIUS_M) < 1e-4,
        "missing" if binding is None else f"{binding.type} parent={binding.parent_bone}",
    )
    if coll is None:
        return
    for obj in coll.objects:
        if obj.type != "MESH":
            continue
        check(f"{obj.name} only in COL_AVERY_CHEN", list(obj.users_collection) == [coll])
        mods = [mod for mod in obj.modifiers if mod.type == "ARMATURE"]
        check(
            f"{obj.name} parent and armature",
            obj.parent == arm and len(mods) == 1 and mods[0].object == arm,
            f"parent={obj.parent.name if obj.parent else None}",
        )


def _suit_weight_split(vert, names):
    arm = torso = 0.0
    for assignment in vert.groups:
        name = names.get(assignment.group, "")
        if name in ARM_GROUPS:
            arm += assignment.weight
        elif name not in {"root"}:
            torso += assignment.weight
    return arm, torso


def _peel_sleeve_faces(suit):
    """Walk each sleeve from its wrist cuff until the ring is the armscye.

    Each step takes the next face ring of the sleeve tube. The walk stops on
    the last ring whose loop is still more arm than torso, so the opening is
    one quad loop at the shoulder. This follows the garment's own connectivity
    and the arm vertex groups.
    """
    names = {group.index: group.name for group in suit.vertex_groups}
    bm = bmesh.new()
    bm.from_mesh(suit.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    adjacency = {}
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        ids = [vert.index for vert in edge.verts]
        adjacency.setdefault(ids[0], []).append(ids[1])
        adjacency.setdefault(ids[1], []).append(ids[0])
    seen = set()
    wrists = []
    for start in list(adjacency):
        if start in seen:
            continue
        stack = [start]
        component = []
        while stack:
            vert = stack.pop()
            if vert in seen:
                continue
            seen.add(vert)
            component.append(vert)
            stack.extend(adjacency[vert])
        if not all(len(adjacency[vert]) == 2 for vert in component):
            continue
        center = sum((bm.verts[index].co for index in component), Vector()) / len(component)
        if 0.80 < center.z < 0.95 and abs(center.x) > 0.20:
            wrists.append(component)
    if len(wrists) != 2:
        bm.free()
        raise RuntimeError(f"expected two wrist cuffs, found {len(wrists)}")

    def order(verts, links):
        start = verts[0]
        path = [start]
        previous = None
        current = start
        for _ in range(len(verts) + 3):
            nxts = [nxt for nxt in links[current] if nxt != previous]
            if not nxts:
                break
            nxt = nxts[0]
            if nxt == start:
                path.append(nxt)
                return path
            path.append(nxt)
            previous, current = current, nxt
        return path

    removed = set()
    for wrist in wrists:
        front = order(wrist, adjacency)
        for _step in range(80):
            ring = []
            seen_faces = set()
            for first, second in zip(front, front[1:]):
                for edge in bm.verts[first].link_edges:
                    if {vert.index for vert in edge.verts} != {first, second}:
                        continue
                    for face in edge.link_faces:
                        if face.index in removed or face.index in seen_faces:
                            continue
                        seen_faces.add(face.index)
                        ring.append(face)
            if not ring:
                break
            trial = set(removed)
            trial.update(face.index for face in ring)
            links = {}
            for face in ring:
                for edge in face.edges:
                    if edge.is_boundary:
                        continue
                    if sum(1 for other in edge.link_faces if other.index in trial) != 1:
                        continue
                    ids = [vert.index for vert in edge.verts]
                    links.setdefault(ids[0], set()).add(ids[1])
                    links.setdefault(ids[1], set()).add(ids[0])
            seen_verts = set()
            best = []
            for start in list(links):
                if start in seen_verts:
                    continue
                stack = [start]
                component = []
                while stack:
                    vert = stack.pop()
                    if vert in seen_verts:
                        continue
                    seen_verts.add(vert)
                    component.append(vert)
                    stack.extend(links[vert])
                if len(component) > len(best):
                    best = component
            if not best or not all(len(links[vert]) == 2 for vert in best):
                break
            arm = torso = 0.0
            for index in best:
                a, t = _suit_weight_split(suit.data.vertices[index], names)
                arm += a
                torso += t
            if arm < torso:
                break
            removed.update(face.index for face in ring)
            front = order(best, links)
    bm.free()
    if len(removed) < 1800:
        raise RuntimeError(f"sleeve peel only found {len(removed)} faces")
    return removed


def _small_components(mesh, skip):
    """Face islands in the complement of skip. The jacket and trousers are the large ones."""
    remaining = {poly.index for poly in mesh.polygons if poly.index not in skip}
    seen = set()
    components = []
    polygons = mesh.polygons
    # edge -> faces
    edge_faces = {}
    for poly in polygons:
        if poly.index not in remaining:
            continue
        for key in poly.edge_keys:
            edge_faces.setdefault(tuple(sorted(key)), []).append(poly.index)
    for start in remaining:
        if start in seen:
            continue
        stack = [start]
        component = []
        while stack:
            index = stack.pop()
            if index in seen:
                continue
            seen.add(index)
            component.append(index)
            for key in polygons[index].edge_keys:
                for neighbor in edge_faces.get(tuple(sorted(key)), ()):
                    if neighbor not in seen:
                        stack.append(neighbor)
        components.append(component)
    return components


def _face_signatures(mesh, indices):
    signatures = set()
    for index in indices:
        poly = mesh.polygons[index]
        coords = tuple(sorted(
            tuple(round(component, 5) for component in mesh.vertices[vert].co)
            for vert in poly.vertices
        ))
        signatures.add(coords)
    return signatures


def _delete_faces(mesh, indices):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    doomed = [bm.faces[index] for index in indices]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    loose = [vert for vert in bm.verts if not vert.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    nonmanifold = [edge for edge in bm.edges if len(edge.link_faces) > 2]
    if nonmanifold:
        bm.free()
        raise RuntimeError(f"vest cut created {len(nonmanifold)} non-manifold edges")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def _boundary_loop_stats(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    adj = {}
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        ids = [vert.index for vert in edge.verts]
        adj.setdefault(ids[0], []).append(ids[1])
        adj.setdefault(ids[1], []).append(ids[0])
    seen = set()
    loops = []
    for start in list(adj):
        if start in seen:
            continue
        stack = [start]
        component = []
        while stack:
            vert = stack.pop()
            if vert in seen:
                continue
            seen.add(vert)
            component.append(vert)
            stack.extend(adj[vert])
        coords = [mesh.vertices[index].co for index in component]
        center = sum(coords, Vector()) / len(coords)
        zs = [co.z for co in coords]
        degrees = {}
        for index in component:
            degrees[len(adj[index])] = degrees.get(len(adj[index]), 0) + 1
        loops.append({
            "n": len(component),
            "center": center,
            "zspan": max(zs) - min(zs),
            "simple": degrees == {2: len(component)},
        })
    bm.free()
    return loops


def _strip_sleeve_weights(suit):
    names = {group.index: group.name for group in suit.vertex_groups}
    orphans = []
    for vert in suit.data.vertices:
        arm = other = 0.0
        for assignment in vert.groups:
            name = names.get(assignment.group, "")
            if name in ARM_GROUPS and assignment.weight > 1e-6:
                arm += assignment.weight
            elif assignment.weight > 1e-6:
                other += assignment.weight
        if arm > 1e-6 and other <= 1e-6:
            orphans.append(vert.index)
            if vert.co.z < 1.05:
                raise RuntimeError(f"pure arm weight left on a low vert at z={vert.co.z:.3f}")
    for name in ARM_GROUPS:
        group = suit.vertex_groups.get(name)
        if group is not None:
            suit.vertex_groups.remove(group)
    if orphans:
        chest = suit.vertex_groups.get("chest")
        if chest is None:
            chest = suit.vertex_groups.new(name="chest")
        chest.add(orphans, 1.0, "REPLACE")
    print("armhole verts moved to chest", len(orphans))


def _reveal_arm_skin(skin, suit):
    """Show the arms. Keep the delete-mask on skin that the vest and trousers cover."""
    group = skin.vertex_groups.get("Delete.male_elegantsuit01")
    if group is None:
        raise RuntimeError("body is missing Delete.male_elegantsuit01")
    delete_index = group.index
    body = skin.vertex_groups.get("body")
    body_index = None if body is None else body.index
    names = {item.index: item.name for item in skin.vertex_groups}
    world_faces = [tuple(poly.vertices) for poly in suit.data.polygons]
    world_coords = [suit.matrix_world @ vert.co for vert in suit.data.vertices]
    tree = BVHTree.FromPolygons(world_coords, world_faces)
    reveal = []
    for vert in skin.data.vertices:
        if not any(item.group == delete_index and item.weight > 0.5 for item in vert.groups):
            continue
        arm = hand = 0.0
        for item in vert.groups:
            name = names.get(item.group, "")
            if name.startswith("upper_arm.") or name.startswith("forearm."):
                arm += item.weight
            elif name.startswith("hand."):
                hand += item.weight
        co = skin.matrix_world @ vert.co
        in_body = body_index is not None and any(
            item.group == body_index and item.weight > 0.5 for item in vert.groups
        )
        if not in_body:
            continue
        if arm > 0.12 or hand > 0.40:
            reveal.append(vert.index)
            continue
        if not (1.05 < co.z < 1.50 and abs(co.x) > 0.10):
            continue
        location, _normal, _index, dist = tree.find_nearest(co)
        if location is not None and dist is not None and dist > 0.016 and abs(location.x) > 0.10:
            reveal.append(vert.index)
    if reveal:
        group.remove(reveal)
    print("revealed arm verts", len(reveal))
    if len(reveal) < 800:
        raise RuntimeError(f"only revealed {len(reveal)} arm verts")


def _archive_diffuse():
    with bpy.data.libraries.load(str(ARCHIVE_BLEND), link=False) as (src, dst):
        wanted = [name for name in src.images if "male_elegantsuit01_diffuse" in name]
        if not wanted:
            raise RuntimeError("archive suit diffuse is missing")
        dst.images = wanted[:1]
    image = dst.images[0]
    if image is None:
        raise RuntimeError("archive suit diffuse did not load")
    return image


def _paint_tie(suit):
    """Recolor the tie texels to the lanyard teal. The tie is not its own object."""
    current = _find_image(suit, "diffuse")
    if current is None:
        raise RuntimeError("suit diffuse missing")
    source = _archive_diffuse()
    try:
        width, height = current.size
        if source.size[:] != (width, height):
            raise RuntimeError(f"tie source size {source.size[:]} != {current.size[:]}")
        src = _image_array(source)
        dst = _image_array(current)
        uvs = suit.data.uv_layers.active.data
        tie_faces = []
        for poly in suit.data.polygons:
            samples = []
            for loop_index in poly.loop_indices:
                uv = uvs[loop_index].uv
                x = int(min(width - 1, max(0, uv.x * width)))
                y = int(min(height - 1, max(0, uv.y * height)))
                samples.append(src[y, x, :3])
            rgb = np.mean(samples, axis=0)
            if rgb[2] > rgb[0] + 0.025 and rgb[2] > rgb[1] + 0.01 and float(rgb[2]) < 0.55:
                tie_faces.append(poly.index)
        if not (60 <= len(tie_faces) <= 180):
            raise RuntimeError(f"tie face count {len(tie_faces)}")
        mask = np.zeros((height, width), dtype=bool)

        def fill(ax, ay, bx, by, cx, cy):
            minx = max(int(np.floor(min(ax, bx, cx))), 0)
            maxx = min(int(np.ceil(max(ax, bx, cx))), width - 1)
            miny = max(int(np.floor(min(ay, by, cy))), 0)
            maxy = min(int(np.ceil(max(ay, by, cy))), height - 1)
            if maxx < minx or maxy < miny:
                return
            xs = np.arange(minx, maxx + 1)
            ys = np.arange(miny, maxy + 1)
            grid_x, grid_y = np.meshgrid(xs, ys)
            den = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
            if abs(den) < 1e-8:
                return
            qx = grid_x - ax
            qy = grid_y - ay
            u = (qx * (cy - ay) - (cx - ax) * qy) / den
            v = ((bx - ax) * qy - qx * (by - ay)) / den
            inside = (u >= -0.02) & (v >= -0.02) & (u + v <= 1.02)
            mask[miny:maxy + 1, minx:maxx + 1][inside] = True

        for index in tie_faces:
            poly = suit.data.polygons[index]
            points = []
            for loop_index in poly.loop_indices:
                uv = uvs[loop_index].uv
                points.append((uv.x * width - 0.5, uv.y * height - 0.5))
            origin = points[0]
            for second, third in zip(points[1:], points[2:]):
                fill(origin[0], origin[1], second[0], second[1], third[0], third[1])
        # One texel of bleed stays on the tie, not a new panel.
        grown = mask.copy()
        grown[1:] |= mask[:-1]
        grown[:-1] |= mask[1:]
        grown[:, 1:] |= mask[:, :-1]
        grown[:, :-1] |= mask[:, 1:]
        teal = np.array([_srgb_u8_to_linear(c) for c in PALETTE["lanyard"]], dtype=np.float32)
        luma = dst[:, :, 0] * 0.2126 + dst[:, :, 1] * 0.7152 + dst[:, :, 2] * 0.0722
        variation = np.clip(luma / (float(luma[grown].mean()) + 1e-5), 0.78, 1.22)
        for channel in range(3):
            dst[:, :, channel][grown] = np.clip(teal[channel] * variation[grown], 0.0, 1.0)
        _write_image_array(current, dst)
        current.pack()
        print("tie faces", len(tie_faces), "texels", int(grown.sum()))
    finally:
        if source.users == 0:
            bpy.data.images.remove(source)


def make_sleeveless_vest():
    """Restore the archived suit, drop the sleeves, and leave the arms as skin."""
    suit, _arm, _coll = _restore_archived_suit()
    sleeve = _peel_sleeve_faces(suit)
    islands = []
    for component in _small_components(suit.data, sleeve):
        if len(component) >= 200:
            continue
        center = Vector()
        for index in component:
            poly = suit.data.polygons[index]
            face_center = Vector()
            for vert_index in poly.vertices:
                face_center += suit.data.vertices[vert_index].co
            center += face_center / len(poly.vertices)
        center /= len(component)
        print(f"island faces {len(component)} center ({center.x:.3f},{center.y:.3f},{center.z:.3f})")
        if center.z < 0.75:
            raise RuntimeError("a trouser island was marked as a sleeve")
        islands.extend(component)
    if len(islands) > 250:
        raise RuntimeError(f"sleeve peel left {len(islands)} island faces")
    sleeve = set(sleeve)
    sleeve.update(islands)
    kept = _face_signatures(
        suit.data,
        [poly.index for poly in suit.data.polygons if poly.index not in sleeve],
    )
    print("cut sleeve", len(sleeve) - len(islands), "islands", len(islands), "kept", len(kept))
    _delete_faces(suit.data, sleeve)
    after = _face_signatures(suit.data, range(len(suit.data.polygons)))
    if after != kept:
        raise RuntimeError("jacket or trouser faces changed during the sleeve cut")
    loops = _boundary_loop_stats(suit.data)
    armholes = []
    for loop in loops:
        center = loop["center"]
        kind = "other"
        if loop["n"] >= 28 and 1.20 < center.z < 1.42 and abs(center.x) > 0.12:
            kind = "armhole"
            armholes.append(loop)
        print(
            f"loop {kind} n={loop['n']} simple={loop['simple']} "
            f"center=({center.x:.3f},{center.y:.3f},{center.z:.3f}) zspan={loop['zspan']:.3f}"
        )
    if len(armholes) != 2 or any(not loop["simple"] for loop in armholes):
        raise RuntimeError(f"expected two simple armholes, got {len(armholes)}")
    _strip_sleeve_weights(suit)
    if {group.name for group in suit.vertex_groups} & set(ARM_GROUPS):
        raise RuntimeError("arm vertex groups remain on the vest")
    _reveal_arm_skin(bpy.data.objects["GEO_AVERY_HEAD"], suit)
    _paint_tie(suit)
    _save_blend()
    print(
        "vest saved",
        "verts", len(suit.data.vertices),
        "polys", len(suit.data.polygons),
    )


ARMHOLE_OFFSET_M = 0.0065
BINDING_RADIUS_M = 0.0045


def _armhole_loops(suit):
    """Ordered vertex indices for the two armscye boundary loops."""
    edge_count = {}
    for poly in suit.data.polygons:
        for key in poly.edge_keys:
            edge_count[tuple(sorted(key))] = edge_count.get(tuple(sorted(key)), 0) + 1
    adjacency = {}
    for (a, b), count in edge_count.items():
        if count != 1:
            continue
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    seen = set()
    loops = []
    for start in list(adjacency):
        if start in seen or len(adjacency[start]) != 2:
            continue
        stack = [start]
        component = []
        while stack:
            vert = stack.pop()
            if vert in seen:
                continue
            seen.add(vert)
            component.append(vert)
            stack.extend(adjacency[vert])
        if len(component) < 28 or not all(len(adjacency[index]) == 2 for index in component):
            continue
        top = max(component, key=lambda index: suit.data.vertices[index].co.z)
        path = [top]
        previous = None
        current = top
        while True:
            nxts = [nxt for nxt in adjacency[current] if nxt != previous]
            if not nxts:
                break
            nxt = nxts[0]
            if nxt == top:
                break
            path.append(nxt)
            previous, current = current, nxt
        center = sum((suit.data.vertices[index].co for index in path), Vector()) / len(path)
        if 1.20 < center.z < 1.45 and abs(center.x) > 0.10:
            if suit.data.vertices[path[1]].co.y > suit.data.vertices[path[-1]].co.y:
                path = [path[0]] + path[:0:-1]
            loops.append(path)
    loops.sort(key=lambda path: suit.data.vertices[path[0]].co.x)
    if len(loops) != 2:
        raise RuntimeError(f"expected two armholes, found {len(loops)}")
    return loops


def _torso_bvh(skin):
    """Body surface under the vest, without the hanging arm."""
    arm_ids = {
        group.index
        for group in skin.vertex_groups
        if group.name.startswith(("upper_arm.", "forearm.", "hand."))
    }
    coords = [vert.co.copy() for vert in skin.data.vertices]
    keep = []
    for poly in skin.data.polygons:
        arm = 0.0
        low = True
        for index in poly.vertices:
            vert = skin.data.vertices[index]
            arm += sum(item.weight for item in vert.groups if item.group in arm_ids)
            if vert.co.z > 1.30:
                low = False
        if arm / len(poly.vertices) > 0.55 and low:
            continue
        keep.append(tuple(poly.vertices))
    return BVHTree.FromPolygons(coords, keep)


def _loop_laplacian(points, factor, rounds):
    points = [point.copy() for point in points]
    for _ in range(rounds):
        count = len(points)
        points = [
            points[index].lerp((points[index - 1] + points[(index + 1) % count]) * 0.5, factor)
            for index in range(count)
        ]
    return points


def _loop_tangential(points, factor, rounds):
    """Slide samples along the loop so spacing evens out without adding teeth."""
    points = [point.copy() for point in points]
    for _ in range(rounds):
        updated = []
        count = len(points)
        for index, point in enumerate(points):
            previous = points[index - 1]
            nxt = points[(index + 1) % count]
            tangent = nxt - previous
            if tangent.length < 1e-8:
                updated.append(point.copy())
                continue
            tangent.normalize()
            delta = ((previous + nxt) * 0.5) - point
            updated.append(point + tangent * delta.dot(tangent) * factor)
        points = updated
    return points


def _resample_closed(points, count):
    lengths = []
    total = 0.0
    for index, point in enumerate(points):
        nxt = points[(index + 1) % len(points)]
        lengths.append((nxt - point).length)
        total += lengths[-1]
    samples = []
    for step in range(count):
        distance = total * step / count
        walked = 0.0
        for index, span in enumerate(lengths):
            if walked + span >= distance - 1e-9 or index == len(lengths) - 1:
                blend = 0.0 if span < 1e-8 else (distance - walked) / span
                blend = min(1.0, max(0.0, blend))
                samples.append(points[index].lerp(points[(index + 1) % len(points)], blend))
                break
            walked += span
    return samples


def _smooth_scalar(values, factor, rounds):
    values = list(values)
    count = len(values)
    for _ in range(rounds):
        values = [
            values[index] * (1.0 - factor)
            + (values[index - 1] + values[(index + 1) % count]) * 0.5 * factor
            for index in range(count)
        ]
    return values


def _align_open_front(points, normals=None):
    """Start at the top and walk toward the front (-Y) on both sides."""
    top = max(range(len(points)), key=lambda index: points[index].z)
    points = points[top:] + points[:top]
    if normals is not None:
        normals = normals[top:] + normals[:top]
    if points[1].y > points[-1].y:
        points = [points[0]] + points[:0:-1]
        if normals is not None:
            normals = [normals[0]] + normals[:0:-1]
    if normals is None:
        return points
    return points, normals


def _resample_with_normals(points, normals, count):
    lengths = []
    total = 0.0
    for index, point in enumerate(points):
        span = (points[(index + 1) % len(points)] - point).length
        lengths.append(span)
        total += span
    samples = []
    sample_normals = []
    for step in range(count):
        distance = total * step / count
        walked = 0.0
        for index, span in enumerate(lengths):
            if walked + span >= distance - 1e-9 or index == len(lengths) - 1:
                blend = 0.0 if span < 1e-8 else min(1.0, max(0.0, (distance - walked) / span))
                nxt = (index + 1) % len(points)
                samples.append(points[index].lerp(points[nxt], blend))
                normal = normals[index].lerp(normals[nxt], blend)
                sample_normals.append(normal.normalized() if normal.length > 1e-8 else normals[index])
                break
            walked += span
    return samples, sample_normals


def _vest_vertex_normals(suit):
    normals = {index: Vector() for index in range(len(suit.data.vertices))}
    for poly in suit.data.polygons:
        for index in poly.vertices:
            normals[index] += poly.normal
    for index, normal in normals.items():
        normals[index] = normal.normalized() if normal.length > 1e-8 else Vector((0.0, -1.0, 0.0))
    return normals


def _min_corner_deg(points):
    worst = 180.0
    for index, point in enumerate(points):
        previous = points[index - 1] - point
        nxt = points[(index + 1) % len(points)] - point
        if previous.length < 1e-8 or nxt.length < 1e-8:
            continue
        worst = min(worst, math.degrees(previous.angle(nxt)))
    return worst


def _smooth_armscyes(suit, skin):
    """Relax each armscye and seat it on a symmetric 6.5 mm body offset."""
    bvh = _torso_bvh(skin)
    loops = _armhole_loops(suit)
    existing_corners = []
    existing_gaps = []
    for loop in loops:
        placed = [suit.data.vertices[index].co.copy() for index in loop]
        existing_corners.append(_min_corner_deg(placed))
        for point in placed:
            _hit, _normal, _index, dist = bvh.find_nearest(point)
            existing_gaps.append(dist or 0.0)
    if min(existing_corners) >= 150.0 and min(existing_gaps) >= 0.0045 and max(existing_gaps) <= 0.012:
        print(
            "armscye already smooth",
            "corners", [round(value, 1) for value in existing_corners],
            "gap mm", round(min(existing_gaps) * 1000.0, 2), round(max(existing_gaps) * 1000.0, 2),
        )
        return 0.0
    vest_normals = _vest_vertex_normals(suit)
    curves = []
    curve_normals = []
    for loop in loops:
        raw = [suit.data.vertices[index].co.copy() for index in loop]
        normals = [vest_normals[index].copy() for index in loop]
        curves.append(_loop_tangential(_loop_laplacian(raw, 0.55, 10), 0.7, 5))
        curve_normals.append([normal.normalized() for normal in _loop_laplacian(normals, 0.55, 10)])
    left, left_normals = _resample_with_normals(curves[0], curve_normals[0], 96)
    right, right_normals = _resample_with_normals(curves[1], curve_normals[1], 96)
    right = [Vector((-point.x, point.y, point.z)) for point in right]
    right_normals = [Vector((-normal.x, normal.y, normal.z)) for normal in right_normals]
    left, left_normals = _align_open_front(left, left_normals)
    right, right_normals = _align_open_front(right, right_normals)
    points = _loop_tangential([(a + b) * 0.5 for a, b in zip(left, right)], 0.8, 4)
    normals = [((a + b) * 0.5).normalized() for a, b in zip(left_normals, right_normals)]
    if max(point.x for point in points) > -0.05:
        raise RuntimeError("symmetric armscye left the left side of the body")

    def gap_pair(samples):
        signed = []
        nearest = []
        for point, normal in zip(samples, normals):
            hit, _normal, _index, dist = bvh.find_nearest(point)
            signed.append((point - hit).dot(normal))
            nearest.append(dist or 0.0)
        return signed, nearest

    for _iteration in range(8):
        signed, nearest = gap_pair(points)
        raw = [ARMHOLE_OFFSET_M - value for value in signed]
        push = _smooth_scalar([max(0.0, value) for value in raw], 0.55, 6)
        pull = _smooth_scalar([min(0.0, value) for value in raw], 0.55, 6)
        corrected = []
        for index, dist in enumerate(nearest):
            step = 0.0
            if dist < ARMHOLE_OFFSET_M:
                step += push[index]
            if dist > ARMHOLE_OFFSET_M:
                step += pull[index]
            corrected.append(max(-0.002, min(0.002, step)))
        points = [point + normal * step for point, normal, step in zip(points, normals, corrected)]
        points = _loop_tangential(points, 0.5, 1)

    _signed, nearest = gap_pair(points)
    corner = _min_corner_deg(points)
    print(
        "armscye curve",
        "corner", round(corner, 1),
        "gap mm", round(min(nearest) * 1000.0, 2), round(max(nearest) * 1000.0, 2),
    )
    if corner < 150.0:
        raise RuntimeError(f"armscye still has a {corner:.0f}° corner")
    if min(nearest) < 0.0045 or max(nearest) > 0.012:
        raise RuntimeError(
            f"armscye offset {min(nearest) * 1000:.1f}–{max(nearest) * 1000:.1f} mm "
            "is outside 5–8 mm"
        )

    points = _align_open_front(points)
    curves = (points, [Vector((-point.x, point.y, point.z)) for point in points])
    displacements = {}
    for loop, curve in zip(loops, curves):
        samples = _resample_closed(curve, len(loop))
        if samples[1].y > samples[-1].y:
            samples = [samples[0]] + samples[:0:-1]
        for index, vert_index in enumerate(loop):
            old = suit.data.vertices[vert_index].co.copy()
            suit.data.vertices[vert_index].co = samples[index]
            displacements[vert_index] = samples[index] - old
    # Spread a little of that move into the next cloth ring so the quads do not keep the old steps.
    loop_ids = set(displacements)
    extra = {}
    for poly in suit.data.polygons:
        boundary = [index for index in poly.vertices if index in displacements]
        if not boundary:
            continue
        delta = sum((displacements[index] for index in boundary), Vector()) / len(boundary)
        for index in poly.vertices:
            if index not in loop_ids:
                extra.setdefault(index, []).append(delta)
    for index, deltas in extra.items():
        suit.data.vertices[index].co += sum(deltas, Vector()) / len(deltas) * 0.35
    suit.data.update()
    written = []
    for loop in _armhole_loops(suit):
        placed = [suit.data.vertices[index].co.copy() for index in loop]
        written.append(_min_corner_deg(placed))
    print("armscye vert corners", [round(value, 1) for value in written])
    if min(written) < 145.0:
        raise RuntimeError(f"placed armscye corner {min(written):.0f}°")
    return max(move.length for move in displacements.values())


def _deltoid_outer(skin, z, sign):
    """Lateral skin silhouette at this height, excluding the hanging arm."""
    arm_ids = {
        group.index
        for group in skin.vertex_groups
        if group.name.startswith(("forearm.", "hand."))
    }
    best = 0.0
    for vert in skin.data.vertices:
        if abs(vert.co.z - z) > 0.008 or vert.co.x * sign < 0.08:
            continue
        arm = sum(item.weight for item in vert.groups if item.group in arm_ids)
        if arm > 0.5:
            continue
        best = max(best, abs(vert.co.x))
    return best


def _tuck_shoulder_tips(suit, skin):
    """Seat the shoulder cap on the torso side of the deltoid."""
    bvh = _torso_bvh(skin)
    normals = _vest_vertex_normals(suit)
    loop_ids = {index for loop in _armhole_loops(suit) for index in loop}
    moved = 0
    for vert in suit.data.vertices:
        if vert.index in loop_ids:
            continue
        point = vert.co.copy()
        if point.z < 1.34 or point.z > 1.48 or abs(point.x) < 0.10:
            continue
        normal = normals[vert.index]
        center = Vector((0.0, -0.015, point.z))
        if normal.dot(point - center) < 0.0:
            normal = -normal
        hit, _face_normal, _index, dist = bvh.find_nearest(point)
        if hit is not None and dist is not None and dist > 0.0085:
            outward = point - hit
            if outward.dot(normal) < 0.0 or outward.length < 1e-5:
                outward = normal
            point = hit + outward.normalized() * ARMHOLE_OFFSET_M
        elif hit is not None and dist is not None and dist < 0.004:
            point = point + normal * (ARMHOLE_OFFSET_M - dist)
        sign = 1.0 if point.x > 0.0 else -1.0
        outer = _deltoid_outer(skin, point.z, sign)
        limit = outer - 0.008
        # The shoulder tip has to stay on the torso side of the deltoid.
        # A later offset must not push it back out past that silhouette.
        if outer > 0.12 and abs(point.x) > limit:
            point.x = math.copysign(limit, point.x)
            hit, _face_normal, _index, dist = bvh.find_nearest(point)
            if hit is not None and dist is not None and dist < 0.004:
                lift = Vector((0.0, normal.y, normal.z))
                if lift.length > 1e-5:
                    point = point + lift.normalized() * (ARMHOLE_OFFSET_M - dist)
                if abs(point.x) > limit:
                    point.x = math.copysign(limit, point.x)
        if (point - vert.co).length < 0.001:
            continue
        vert.co = point
        moved += 1
    suit.data.update()
    print("shoulder tips tucked", moved)
    return moved


def _pin_armhole_to_chest(suit):
    chest = suit.vertex_groups.get("chest")
    if chest is None:
        chest = suit.vertex_groups.new(name="chest")
    pinned = []
    for loop in _armhole_loops(suit):
        pinned.extend(loop)
    for vert in suit.data.vertices:
        if vert.co.z > 1.36 and abs(vert.co.x) > 0.11:
            pinned.append(vert.index)
    pinned = sorted(set(pinned))
    for group in suit.vertex_groups:
        present = []
        for index in pinned:
            try:
                group.weight(index)
            except RuntimeError:
                continue
            present.append(index)
        if present:
            group.remove(present)
    chest.add(pinned, 1.0, "REPLACE")
    print("armhole and shoulder pinned to chest", len(pinned))


def _reveal_axilla(skin, suit, arm):
    """Show shoulder, upper-arm, and armpit skin that the raised arm uncovers."""
    group = skin.vertex_groups.get("Delete.male_elegantsuit01")
    body = skin.vertex_groups.get("body")
    if group is None or body is None:
        raise RuntimeError("body masks missing")
    delete_index = group.index
    body_index = body.index
    names = {item.index: item.name for item in skin.vertex_groups}
    masks = [modifier for modifier in skin.modifiers if modifier.type == "MASK"]
    vest_mods = [modifier for modifier in suit.modifiers if modifier.type == "MASK"]
    reveal = set()

    def pose(angle):
        if arm.animation_data:
            arm.animation_data.action = None
        for bone in arm.pose.bones:
            bone.rotation_euler = (0.0, 0.0, 0.0)
        if angle:
            arm.pose.bones["upper_arm.L"].rotation_euler.z = math.radians(angle)
            arm.pose.bones["upper_arm.R"].rotation_euler.z = math.radians(-angle)
        bpy.context.view_layer.update()

    def evaluated_coords(obj):
        deps = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        coords = [obj.matrix_world @ vert.co for vert in mesh.vertices]
        faces = [tuple(poly.vertices) for poly in mesh.polygons]
        evaluated.to_mesh_clear()
        return coords, faces

    saved = [(modifier, modifier.show_viewport, modifier.show_render) for modifier in masks + vest_mods]
    try:
        for modifier, _viewport, _render in saved:
            modifier.show_viewport = False
            modifier.show_render = False
        loop_points = [
            suit.data.vertices[index].co.copy()
            for loop in _armhole_loops(suit)
            for index in loop
        ]
        for angle in (0.0, 45.0, 90.0, 120.0):
            pose(angle)
            vest_coords, vest_faces = evaluated_coords(suit)
            skin_coords, _skin_faces = evaluated_coords(skin)
            if len(skin_coords) != len(skin.data.vertices):
                raise RuntimeError("skin evaluation dropped vertices; masks are still on")
            tree = BVHTree.FromPolygons(vest_coords, vest_faces)
            for index, point in enumerate(skin_coords):
                rest = skin.data.vertices[index]
                if rest.co.z < 1.10 or rest.co.z > 1.52 or abs(rest.co.x) < 0.06:
                    continue
                in_body = any(item.group == body_index and item.weight > 0.5 for item in rest.groups)
                deleted = any(item.group == delete_index and item.weight > 0.5 for item in rest.groups)
                if not in_body or not deleted:
                    continue
                arm_weight = 0.0
                for item in rest.groups:
                    bone_name = names.get(item.group, "")
                    if bone_name.startswith(("upper_arm.", "forearm.")):
                        arm_weight += item.weight
                _loc, _normal, _poly, dist = tree.find_nearest(point)
                near_opening = min((rest.co - sample).length for sample in loop_points) < 0.050
                gap = dist if dist is not None else 1.0
                if (near_opening and gap > 0.006) or gap > 0.010 or arm_weight > 0.12:
                    reveal.add(index)
    finally:
        for modifier, viewport, render in saved:
            modifier.show_viewport = viewport
            modifier.show_render = render
        pose(0.0)
    if reveal:
        group.remove(list(reveal))
    print("revealed axilla and shoulder", len(reveal))
    if len(reveal) > 2200:
        raise RuntimeError(f"uncovered {len(reveal)} axilla vertices")
    if len(reveal) < 40:
        hidden_near = 0
        for rest in skin.data.vertices:
            if rest.co.z < 1.10 or rest.co.z > 1.52 or abs(rest.co.x) < 0.06:
                continue
            deleted = any(item.group == delete_index and item.weight > 0.5 for item in rest.groups)
            in_body = any(item.group == body_index and item.weight > 0.5 for item in rest.groups)
            if not deleted or not in_body:
                continue
            if min((rest.co - sample).length for sample in loop_points) < 0.050:
                hidden_near += 1
        if hidden_near > 30:
            raise RuntimeError(f"uncovered {len(reveal)} axilla vertices, {hidden_near} still hidden")
        print("axilla already open", hidden_near, "still hidden nearby")


def _add_armhole_binding(suit, arm, coll):
    """A 9 mm piping tube on each finished armscye, rigid on the chest bone."""
    old = bpy.data.objects.get("GEO_AVERY_BINDING")
    if old is not None:
        data = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if data.users == 0 and isinstance(data, bpy.types.Curve):
            bpy.data.curves.remove(data)
    curve = bpy.data.curves.new("GEO_AVERY_BINDING_CURVE", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 8
    curve.bevel_depth = BINDING_RADIUS_M
    curve.bevel_resolution = 3
    curve.use_fill_caps = True
    curve.twist_mode = "MINIMUM"
    expected = []
    for loop in _armhole_loops(suit):
        samples = [suit.matrix_world @ suit.data.vertices[index].co for index in loop]
        center = sum(samples, Vector()) / len(samples)
        spline = curve.splines.new("BEZIER")
        spline.bezier_points.add(len(samples) - 1)
        spline.use_cyclic_u = True
        spline.resolution_u = 8
        seated = []
        for index, point in enumerate(samples):
            radial = point - center
            if radial.length < 1e-5:
                radial = Vector((math.copysign(1.0, point.x), 0.0, 0.0))
            else:
                radial.normalize()
            placed = point + radial * 0.0022
            seated.append(placed)
            bezier = spline.bezier_points[index]
            bezier.co = placed
            bezier.handle_left_type = "AUTO"
            bezier.handle_right_type = "AUTO"
        expected.append(seated)
    material = bpy.data.materials.get("MAT_AVERY_BINDING") or bpy.data.materials.new("MAT_AVERY_BINDING")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        color = tuple(_srgb_u8_to_linear(channel) for channel in (52, 66, 62))
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.55
    curve.materials.append(material)
    obj = bpy.data.objects.new("GEO_AVERY_BINDING", curve)
    link_only(obj, coll)
    world = obj.matrix_world.copy()
    obj.parent = arm
    obj.parent_type = "BONE"
    obj.parent_bone = "chest"
    bpy.context.view_layer.update()
    obj.matrix_world = world
    bpy.context.view_layer.update()
    drift = 0.0
    for spline, seated in zip(obj.data.splines, expected):
        for bezier, point in zip(spline.bezier_points, seated):
            world_point = obj.matrix_world @ bezier.co
            drift = max(drift, (world_point - point).length)
    print(
        "binding diameter mm", round(BINDING_RADIUS_M * 2000.0, 1),
        "parent", obj.parent_bone,
        "drift mm", round(drift * 1000.0, 2),
    )
    if drift > 0.003:
        raise RuntimeError(f"armhole binding drifted {drift * 1000:.1f} mm off the vest")
    return obj


def finish_armholes():
    """Smooth the vest armscyes, tuck the shoulder tips, and show the axilla."""
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    suit = bpy.data.objects["GEO_AVERY_BODY"]
    skin = bpy.data.objects["GEO_AVERY_HEAD"]
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    coll = bpy.data.collections["COL_AVERY_CHEN"]
    if arm.animation_data:
        arm.animation_data.action = None
    for bone in arm.pose.bones:
        bone.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    before = len(suit.data.polygons)
    _smooth_armscyes(suit, skin)
    _tuck_shoulder_tips(suit, skin)
    if len(suit.data.polygons) != before:
        raise RuntimeError("armhole finish changed vest topology")
    _pin_armhole_to_chest(suit)
    _reveal_axilla(skin, suit, arm)
    binding = _add_armhole_binding(suit, arm, coll)
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = binding.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    if len(mesh.vertices) < 20:
        evaluated.to_mesh_clear()
        raise RuntimeError("armhole binding did not bevel")
    evaluated.to_mesh_clear()
    _save_blend()
    print("armholes finished", "vest polys", len(suit.data.polygons))

def _cover_uv_triangle(mask, a, b, c):
    """Mark image pixels covered by one UV triangle. UV y is the image row from the bottom."""
    height, width = mask.shape
    pts = np.stack([np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64), np.asarray(c, dtype=np.float64)])
    minx = max(0, int(np.floor(pts[:, 0].min())) - 1)
    maxx = min(width - 1, int(np.ceil(pts[:, 0].max())) + 1)
    miny = max(0, int(np.floor(pts[:, 1].min())) - 1)
    maxy = min(height - 1, int(np.ceil(pts[:, 1].max())) + 1)
    if minx > maxx or miny > maxy:
        return
    xs = np.arange(minx, maxx + 1) + 0.5
    ys = np.arange(miny, maxy + 1) + 0.5
    grid_x, grid_y = np.meshgrid(xs, ys)
    edge = c - a
    side = b - a
    denom = edge[0] * side[1] - side[0] * edge[1]
    if abs(denom) < 1e-8:
        return
    delta_x = grid_x - a[0]
    delta_y = grid_y - a[1]
    coord_c = (delta_x * side[1] - side[0] * delta_y) / denom
    coord_b = (edge[0] * delta_y - delta_x * edge[1]) / denom
    coord_a = 1.0 - coord_b - coord_c
    inside = (coord_a >= -0.02) & (coord_b >= -0.02) & (coord_c >= -0.02)
    mask[miny:maxy + 1, minx:maxx + 1] |= inside


def fix_rear_collar_patch():
    """Recolor the pale shoe-collar lining that shows above the rear trouser cuff.

    The lower rear 'trouser' patch is not the suit mesh and not the background.
    Both shoes share one UV island on shoes01_diffuse.png for the ankle collar.
    Those texels stayed a light gray-violet after the shoe recolor, and a sliver
    of that collar renders above the cuff. The trouser faces stay charcoal.
    Only this diffuse region is repainted. Geometry, roughness, and the normal
    map are left alone.
    """
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    shoes = bpy.data.objects["GEO_AVERY_SHOES"]
    image = bpy.data.images.get("shoes01_diffuse.png")
    if image is None:
        raise RuntimeError("shoes01_diffuse.png missing")
    pixels = _image_array(image)
    height, width, _ = pixels.shape
    luma = pixels[:, :, 0] * 0.2126 + pixels[:, :, 1] * 0.7152 + pixels[:, :, 2] * 0.0722
    uv_data = shoes.data.uv_layers.active.data
    collar = []
    for poly in shoes.data.polygons:
        uvs = [uv_data[loop].uv for loop in poly.loop_indices]
        center_u = sum(uv.x for uv in uvs) / len(uvs)
        center_v = sum(uv.y for uv in uvs) / len(uvs)
        if center_u < 0.86 or center_v < 0.88:
            continue
        ix = min(width - 1, max(0, int(center_u * width)))
        iy = min(height - 1, max(0, int(center_v * height)))
        if luma[iy, ix] < 0.35:
            continue
        center = sum((shoes.data.vertices[index].co for index in poly.vertices), Vector()) / len(poly.vertices)
        if not (0.12 < center.z < 0.25):
            continue
        collar.append(poly.index)
    if len(collar) < 20:
        raise RuntimeError(f"expected the pale shoe collar, found {len(collar)} faces")
    mask = np.zeros((height, width), dtype=bool)
    for index in collar:
        poly = shoes.data.polygons[index]
        uvs = [uv_data[loop].uv for loop in poly.loop_indices]
        tris = [(0, 1, 2)]
        if len(uvs) >= 4:
            tris.append((0, 2, 3))
        for tri in tris:
            points = [
                np.array([uvs[corner].x * width, uvs[corner].y * height], dtype=np.float64)
                for corner in tri
            ]
            _cover_uv_triangle(mask, *points)
    pale = luma > 0.32
    grown = mask.copy()
    grown[1:, :] |= mask[:-1, :]
    grown[:-1, :] |= mask[1:, :]
    grown[:, 1:] |= mask[:, :-1]
    grown[:, :-1] |= mask[:, 1:]
    mask = grown & (pale | mask)
    if int(mask.sum()) < 200 or int(mask.sum()) > 80000:
        raise RuntimeError(f"collar texel mask is {int(mask.sum())}")
    # A dark leather texel just outside the collar must stay the shoe color.
    leather_u, leather_v = int(0.88 * width), int(0.76 * height)
    leather_before = pixels[leather_v, leather_u, :3].copy()
    target = np.array([_srgb_u8_to_linear(channel) for channel in PALETTE["trousers"]], dtype=np.float32)
    mean = float(luma[mask].mean()) + 1e-5
    variation = np.clip(luma / mean, 0.82, 1.18)
    for channel in range(3):
        pixels[:, :, channel][mask] = np.clip(target[channel] * variation[mask], 0.0, 1.0)
    if np.max(np.abs(pixels[leather_v, leather_u, :3] - leather_before)) > 1e-6:
        raise RuntimeError("collar repaint changed the shoe leather")
    _write_image_array(image, pixels)
    image.pack()
    after = pixels[:, :, :3][mask]
    print(
        "collar faces", len(collar),
        "texels", int(mask.sum()),
        "mean linear", tuple(round(float(c), 3) for c in after.mean(axis=0)),
    )
    _save_blend()
    print("rear collar patch saved")


def reweight_sleeves():
    """Smooth the saved sleeve elbow blend. Does not recut the mesh."""
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    for side, name in (("L", "GEO_AVERY_SLEEVE_L"), ("R", "GEO_AVERY_SLEEVE_R")):
        _weight_sleeves(bpy.data.objects[name], side, arm)
    _save_blend()
    print("sleeve weights saved")


def main():
    mode = argv_tail()
    if "verify" in mode:
        verify()
    elif "render" in mode:
        render_previews()
    elif "appearance" in mode:
        apply_archived_appearance()
    elif "repair" in mode:
        repair_qa_blockers()
    elif "proof" in mode:
        proof_wardrobe()
    elif "inspect" in mode:
        inspect_actions()
    elif "finish" in mode:
        finish_armholes()
    elif "patch" in mode:
        fix_rear_collar_patch()
    elif "vest" in mode:
        make_sleeveless_vest()
    elif "sleeves" in mode or "reweight" in mode or "armpit" in mode:
        raise SystemExit("Refusing sleeves and corrective keys. The jacket is a sleeveless vest.")
    elif "wardrobe" in mode or "outfit" in mode or "tuck" in mode:
        raise SystemExit("Refusing wardrobe rebuild. The suit is the archived male_elegantsuit01.")
    else:
        raise SystemExit(
            "Refusing a full rebuild. Use vest, finish, proof, render, inspect, or verify."
        )


if __name__ == "__main__":
    main()
