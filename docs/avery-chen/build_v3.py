#!/usr/bin/env python3
"""Avery Chen V3 appearance revamp.

The repository copy of this builder is `scripts/build_avery_chen.py`.
It must be run as:

  blender --background --factory-startup --python scripts/build_avery_chen.py -- \\
      --output assets/characters/AveryChen.blend \\
      --report /path/to/build.json

The committed character is `assets/characters/AveryChen.blend` (Git LFS).
The manifest entry is `assets.char.avery_chen` with
`file: characters/AveryChen.blend`. Release ZIPs are not rewritten.

This store copy still reads the archived V2 blend and the local MPFB
system assets while the appearance is in progress. Those machine-local
inputs have to be vendored or checksum-pinned before the repository
script can claim a clean-clone rebuild.
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_character as bc

ROOT = Path(__file__).resolve().parent
PRIMARY = ROOT / "AveryChen.blend"
STAGING = Path("/tmp/AveryChen-v3.blend")
MEDIA = Path("/cursor/stores/bc-b80cc329-0c07-499f-9a51-00c871f014b4/media/avery-chen-v3")
VERIFY_LOG = Path("/cursor/stores/bc-b80cc329-0c07-499f-9a51-00c871f014b4/internal/avery-chen-v3-verify.txt")
REFERENCE = Path("/cursor/stores/bc-b80cc329-0c07-499f-9a51-00c871f014b4/media/reference/patty-patties-style.jpg")

# Locked sRGB values from internal/v3-style-translation.md. Do not eyedrop the JPEG.
NAVY = (17, 45, 73)             # #112D49 core navy
NAVY_UTILITY = (28, 61, 90)     # #1C3D5A
SHIRT = (236, 232, 223)         # #ECE8DF warm soft white
TROUSER = (39, 55, 69)          # #273745
CHARCOAL = (48, 55, 64)         # #303740
MAGENTA = (209, 43, 120)        # #D12B78
TEAL = (23, 139, 140)           # #178B8C
CYAN = (42, 168, 207)           # #2AA8CF glint only
SOLE = (236, 232, 223)          # #ECE8DF
GUNMETAL = (101, 116, 127)      # #65747F
HAIR = (23, 21, 28)             # #17151C espresso
HAIR_PLUM = (97, 36, 79)        # #61244F
FRAME = (26, 32, 52)            # deep plum-navy acetate
TOOTH = (240, 230, 214)         # #F0E6D6
GUM = (164, 93, 102)            # #A45D66
IRIS = (42, 27, 23)             # #2A1B17
SCLERA = (231, 221, 210)        # #E7DDD2
SKIN = {
    "base": (151, 95, 73),      # #975F49
    "cheek": (181, 104, 104),   # #B56868 flush, blended
    "nose": (179, 113, 97),     # #B37161
    "lip": (137, 66, 88),       # #894258 berry, not magenta lipstick
    "ear": (179, 113, 97),
    "lid": (108, 65, 57),       # #6C4139
    "shadow": (108, 65, 57),
}


def srgb(color):
    return np.array([bc._srgb_u8_to_linear(channel) for channel in color], dtype=np.float32)


def principled(name, color, roughness, metallic=0.0):
    existing = bpy.data.materials.get(name)
    mat = existing or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(node for node in mat.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled")
    for link in list(bsdf.inputs["Base Color"].links):
        mat.node_tree.links.remove(link)
    bsdf.inputs["Base Color"].default_value = (*srgb(color), 1.0)
    if "Roughness" in bsdf.inputs and not bsdf.inputs["Roughness"].is_linked:
        bsdf.inputs["Roughness"].default_value = roughness
    if "Metallic" in bsdf.inputs and not bsdf.inputs["Metallic"].is_linked:
        bsdf.inputs["Metallic"].default_value = metallic
    mat.diffuse_color = (*srgb(color), 1.0)
    return mat


def cloth_material(name, roughness):
    """Vertex-color cloth with a fine weave. No photo print and no lettering."""
    mat = principled(name, (128, 128, 128), roughness)
    nt = mat.node_tree
    bsdf = next(node for node in nt.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled")
    for node in list(nt.nodes):
        if node != bsdf and node.bl_idname != "ShaderNodeOutputMaterial":
            nt.nodes.remove(node)
    color = nt.nodes.new("ShaderNodeVertexColor")
    color.layer_name = "CLOTH"
    color.location = (-640, 180)
    rough_attr = nt.nodes.new("ShaderNodeVertexColor")
    rough_attr.layer_name = "CLOTH"
    rough_attr.location = (-640, -40)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.location = (-640, -220)
    noise.inputs["Scale"].default_value = 80.0
    noise.inputs["Detail"].default_value = 2.0
    span = nt.nodes.new("ShaderNodeMapRange")
    span.location = (-400, -220)
    span.inputs["From Min"].default_value = 0.40
    span.inputs["From Max"].default_value = 0.60
    span.inputs["To Min"].default_value = 0.96
    span.inputs["To Max"].default_value = 1.04
    nt.links.new(noise.outputs["Fac"], span.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.location = (-160, 140)
    mix.inputs["Factor"].default_value = 1.0
    nt.links.new(color.outputs["Color"], mix.inputs["A"])
    combine = nt.nodes.new("ShaderNodeCombineColor")
    combine.location = (-160, -20)
    for channel in ("Red", "Green", "Blue"):
        nt.links.new(span.outputs["Result"], combine.inputs[channel])
    nt.links.new(combine.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    # Per-vertex roughness is stored in CLOTH alpha so jacket, shirt, and twill can differ.
    nt.links.new(rough_attr.outputs["Alpha"], bsdf.inputs["Roughness"])
    return mat


def hair_material():
    """Espresso base, plum variation, magenta only on a small thread mask."""
    mat = principled("MAT_AVERY_HAIR", HAIR, 0.46)
    nt = mat.node_tree
    bsdf = next(node for node in nt.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.location = (-700, 80)
    noise.inputs["Scale"].default_value = 14.0
    noise.inputs["Detail"].default_value = 6.0
    plum = nt.nodes.new("ShaderNodeMix")
    plum.data_type = "RGBA"
    plum.blend_type = "MIX"
    plum.location = (-420, 120)
    nt.links.new(noise.outputs["Fac"], plum.inputs["Factor"])
    plum.inputs["A"].default_value = (*srgb(HAIR), 1.0)
    plum.inputs["B"].default_value = (*srgb(HAIR_PLUM), 1.0)
    thread = nt.nodes.new("ShaderNodeTexNoise")
    thread.location = (-700, -120)
    thread.inputs["Scale"].default_value = 46.0
    thread.inputs["Detail"].default_value = 2.0
    mask = nt.nodes.new("ShaderNodeMapRange")
    mask.location = (-460, -120)
    mask.inputs["From Min"].default_value = 0.72
    mask.inputs["From Max"].default_value = 0.80
    mask.clamp = True
    nt.links.new(thread.outputs["Fac"], mask.inputs["Value"])
    accent = nt.nodes.new("ShaderNodeMix")
    accent.data_type = "RGBA"
    accent.blend_type = "MIX"
    accent.location = (-180, 40)
    nt.links.new(mask.outputs["Result"], accent.inputs["Factor"])
    nt.links.new(plum.outputs["Result"], accent.inputs["A"])
    accent.inputs["B"].default_value = (*srgb(MAGENTA), 1.0)
    for link in list(bsdf.inputs["Base Color"].links):
        nt.links.remove(link)
    nt.links.new(accent.outputs["Result"], bsdf.inputs["Base Color"])
    if "Roughness" in bsdf.inputs and not bsdf.inputs["Roughness"].is_linked:
        bsdf.inputs["Roughness"].default_value = 0.46
    if "Anisotropic" in bsdf.inputs and not bsdf.inputs["Anisotropic"].is_linked:
        bsdf.inputs["Anisotropic"].default_value = 0.28
    if "Specular IOR Level" in bsdf.inputs and not bsdf.inputs["Specular IOR Level"].is_linked:
        bsdf.inputs["Specular IOR Level"].default_value = 0.22
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.0015
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def paint_deep_skin(head):
    mesh = head.data
    coords = [vert.co.copy() for vert in mesh.vertices]
    crown = max(co.z for co in coords)
    chin_z = bc.find_chin_z(coords, crown)
    head_h = crown - chin_z
    nose_band = [
        co for co in coords
        if abs(co.x) < 0.012 and chin_z + 0.35 * head_h < co.z < chin_z + 0.78 * head_h
    ]
    nose = min(nose_band, key=lambda co: co.y)
    base = srgb(SKIN["base"])
    zones = {name: srgb(color) for name, color in SKIN.items() if name != "base"}
    rough = {"base": 0.50, "cheek": 0.48, "nose": 0.46, "lip": 0.42, "ear": 0.52, "lid": 0.48}
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
        elif co.z < chin_z + 0.16 * head_h or (on_face and abs(co.x) > 0.055 and rel < 0.35):
            color = srgb(SKIN["shadow"])
            rough_v = rough["base"]
        elif on_face and 0.018 < abs(co.x) < 0.055 and abs(co.z - (chin_z + 0.42 * head_h)) < 0.04 and co.y < -0.08:
            color = 0.55 * base + 0.45 * zones["cheek"]
            rough_v = rough["cheek"]
        elif on_face and 0.012 < abs(co.x) < 0.05 and abs(co.z - lid_z) < 0.018:
            color = zones["lid"]
            rough_v = rough["lid"]
        elif co.z > chin_z + 0.25 * head_h and abs(co.x) > 0.075 and abs(co.z - (chin_z + 0.48 * head_h)) < 0.06:
            color = zones["ear"]
            rough_v = rough["ear"]
        albedo.data[index].color = (float(color[0]), float(color[1]), float(color[2]), 1.0)
        roughness.data[index].color = (rough_v, rough_v, rough_v, 1.0)
    if "Subsurface Weight" in _bsdf(bpy.data.materials["MAT_PROXY_CHARACTER"]).inputs:
        bsdf = _bsdf(bpy.data.materials["MAT_PROXY_CHARACTER"])
        if not bsdf.inputs["Subsurface Weight"].is_linked:
            bsdf.inputs["Subsurface Weight"].default_value = 0.055
        if "Specular IOR Level" in bsdf.inputs and not bsdf.inputs["Specular IOR Level"].is_linked:
            bsdf.inputs["Specular IOR Level"].default_value = 0.28
        if "Subsurface Radius" in bsdf.inputs and not bsdf.inputs["Subsurface Radius"].is_linked:
            bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.22)
    print("deep skin", "chin", round(chin_z, 3))
    return chin_z, head_h, nose


def _bsdf(mat):
    return next(node for node in mat.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled")


def offset_keys(obj, index, delta):
    keys = obj.data.shape_keys
    if keys is None:
        obj.data.vertices[index].co += delta
        return
    for key in keys.key_blocks:
        key.data[index].co += delta


def friendly_face(head, chin_z, head_h):
    """Fuller lips and a slight corner lift, copied onto every expression key."""
    lip_z = chin_z + 0.20 * head_h
    lifted = 0
    for vert in head.data.vertices:
        co = vert.co
        if abs(co.x) > 0.05 or abs(co.z - lip_z) > 0.016 or co.y > -0.08:
            continue
        forward = 0.0016
        corner = 0.0013 if abs(co.x) > 0.012 else 0.0
        offset_keys(head, vert.index, Vector((0.0, -forward, corner)))
        lifted += 1
    frown = head.data.shape_keys.key_blocks["EXP_frown"]
    basis = head.data.shape_keys.key_blocks["Basis"]
    for index in range(len(head.data.vertices)):
        delta = frown.data[index].co - basis.data[index].co
        frown.data[index].co = basis.data[index].co + delta * 0.65
    smile = head.data.shape_keys.key_blocks["EXP_smile"]
    viseme_a = head.data.shape_keys.key_blocks["VISEME_A"]
    for index in range(len(head.data.vertices)):
        delta = smile.data[index].co - basis.data[index].co
        # A small hinge opening so the upper arc can show once the lips part.
        jaw = (viseme_a.data[index].co - basis.data[index].co) * 0.10
        smile.data[index].co = basis.data[index].co + delta * 1.05 + jaw
    surprise = head.data.shape_keys.key_blocks["EXP_surprise"]
    for index in range(len(head.data.vertices)):
        delta = surprise.data[index].co - basis.data[index].co
        surprise.data[index].co = basis.data[index].co + delta * 0.78
    print("lip verts", lifted)


def enlarge_hands(head, arm):
    moved = 0
    for side in ("L", "R"):
        bone = arm.data.bones[f"hand.{side}"]
        center = (bone.head_local + bone.tail_local) * 0.5
        group = head.vertex_groups.get(f"hand.{side}")
        if group is None:
            continue
        for vert in head.data.vertices:
            weight = 0.0
            for assignment in vert.groups:
                if assignment.group == group.index:
                    weight = assignment.weight
            if weight < 0.72:
                continue
            co = vert.co
            offset_keys(head, vert.index, (co - center) * 0.07)
            moved += 1
    print("enlarged hand verts", moved)


def _group_center(obj, name):
    return bc.group_center(obj, name)


def seat_eyes(head, eyes):
    left = _group_center(head, "joint-l-eye")
    right = _group_center(head, "joint-r-eye")
    if left is None or right is None:
        raise RuntimeError("eye joints missing")
    shared_y = (left.y + right.y) * 0.5 - 0.0025
    shared_z = (left.z + right.z) * 0.5
    targets = {
        1.0: Vector((left.x, shared_y, shared_z)),
        -1.0: Vector((right.x, shared_y, shared_z)),
    }
    verts = [vert.co.copy() for vert in eyes.data.vertices]
    old = {}
    radii = {}
    for sign in (1.0, -1.0):
        side = [co for co in verts if co.x * sign > 0.004]
        old[sign] = sum(side, Vector()) / len(side)
        radii[sign] = max((co - old[sign]).length for co in side if (co - old[sign]).length < 0.016)
    # A plausible globe, slightly large for readability. Not the mesh's outlier radius.
    radius = 0.0126
    pupil = _pupil_offsets(eyes, verts, old)
    if eyes.data.shape_keys and eyes.data.shape_keys.animation_data:
        eyes.data.shape_keys.animation_data_clear()
    if eyes.data.shape_keys:
        while len(eyes.data.shape_keys.key_blocks) > 1:
            eyes.shape_key_remove(eyes.data.shape_keys.key_blocks[-1])
        eyes.shape_key_clear()
    for index, co in enumerate(verts):
        sign = 1.0 if co.x >= 0.0 else -1.0
        direction = (co - old[sign]) * (radius / radii[sign])
        # Keep the cornea facing forward, then toe both eyes toward a point 2 m ahead.
        aim = Vector((0.0, targets[sign].y - 2.0, targets[sign].z)) - targets[sign]
        direction = Vector((0.0, -1.0, 0.0)).rotation_difference(aim.normalized()) @ direction
        eyes.data.vertices[index].co = targets[sign] + direction
    eyes.data.update()
    _darken_iris()
    bc.add_eye_look_keys(eyes, head)
    print(
        "eyes seated",
        tuple(round(c, 4) for c in targets[1.0]),
        tuple(round(c, 4) for c in targets[-1.0]),
        "radius mm", round(radius * 1000.0, 1),
    )
    return targets, radius


def _pupil_offsets(eyes, verts, old):
    """Vector from each globe center toward the darkest texel on that globe."""
    image = None
    mat = eyes.data.materials[0] if eyes.data.materials else None
    if mat and mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.bl_idname == "ShaderNodeTexImage" and node.image:
                image = node.image
                break
    offsets = {1.0: Vector((0.0, -1.0, 0.0)), -1.0: Vector((0.0, -1.0, 0.0))}
    if image is None or not eyes.data.uv_layers:
        return offsets
    pixels = bc._image_array(image)
    height, width, _ = pixels.shape
    luma = pixels[:, :, 0] * 0.2126 + pixels[:, :, 1] * 0.7152 + pixels[:, :, 2] * 0.0722
    uv_data = eyes.data.uv_layers.active.data
    buckets = {1.0: [], -1.0: []}
    for poly in eyes.data.polygons:
        for loop_index in poly.loop_indices:
            vert_index = eyes.data.loops[loop_index].vertex_index
            co = verts[vert_index]
            sign = 1.0 if co.x >= 0.0 else -1.0
            uv = uv_data[loop_index].uv
            ix = min(width - 1, max(0, int(uv.x * width)))
            iy = min(height - 1, max(0, int(uv.y * height)))
            if float(luma[iy, ix]) < 0.12:
                buckets[sign].append(co - old[sign])
    for sign, samples in buckets.items():
        if len(samples) < 8:
            continue
        mean = sum(samples, Vector()) / len(samples)
        if mean.length > 0.003:
            offsets[sign] = mean
    print("pupil samples", len(buckets[1.0]), len(buckets[-1.0]))
    return offsets


def _darken_iris():
    """Repaint the shared eye map: warm sclera, umber iris, near-black pupil."""
    mat = bpy.data.materials.get("MAT_PROXY_FOCUS")
    if mat is None or mat.node_tree is None:
        return
    bc.tune_eyes(mat)
    bsdf = _bsdf(mat)
    if "Roughness" in bsdf.inputs and not bsdf.inputs["Roughness"].is_linked:
        bsdf.inputs["Roughness"].default_value = 0.04
    image_node = next((node for node in mat.node_tree.nodes if node.bl_idname == "ShaderNodeTexImage" and node.image), None)
    if image_node is None:
        return
    image = image_node.image
    pixels = bc._image_array(image)
    luma = pixels[:, :, 0] * 0.2126 + pixels[:, :, 1] * 0.7152 + pixels[:, :, 2] * 0.0722
    pupil = srgb((9, 8, 10))
    iris = srgb(IRIS)
    sclera = srgb(SCLERA)
    pupil_mask = luma < 0.07
    iris_mask = (luma >= 0.07) & (luma < 0.55)
    sclera_mask = luma >= 0.55
    variation = np.clip(luma / 0.28, 0.82, 1.12)
    for channel in range(3):
        pixels[:, :, channel][pupil_mask] = pupil[channel]
        pixels[:, :, channel][iris_mask] = np.clip(iris[channel] * variation[iris_mask], 0.0, 1.0)
        pixels[:, :, channel][sclera_mask] = np.clip(sclera[channel] * np.clip(luma[sclera_mask] / 0.75, 0.94, 1.04), 0.0, 1.0)
    bc._write_image_array(image, pixels)
    image.pack()
    for link in list(bsdf.inputs["Base Color"].links):
        mat.node_tree.links.remove(link)
    mat.node_tree.links.new(image_node.outputs["Color"], bsdf.inputs["Base Color"])


def lift_brows(brows, targets, radius):
    mat = principled("MAT_AVERY_BROWS", (42, 26, 20), 0.55)
    if brows.data.materials:
        brows.data.materials[0] = mat
    else:
        brows.data.materials.append(mat)
    verts = [vert.co.copy() for vert in brows.data.vertices]
    for index, co in enumerate(verts):
        sign = 1.0 if co.x >= 0.0 else -1.0
        socket = targets[sign]
        # Sit on the ridge above the globe, with a higher peak over the outer iris.
        # About a 7° friendly rise: inner brow lower, arch over the outer iris.
        inner = max(0.0, 1.0 - abs(co.x) / 0.055)
        peak = 0.0042 * max(0.0, 1.0 - abs(abs(co.x) - (abs(socket.x) + 0.006)) / 0.018)
        asymmetry = 0.0015 if co.x < 0.0 else 0.0
        brows.data.vertices[index].co = Vector((
            co.x,
            socket.y + 0.008,
            socket.z + radius + 0.007 + peak - inner * 0.0015 + asymmetry,
        ))
    brows.data.update()
    print("brows lifted")


def close_blink(head, targets, radius):
    """Pull the blink shape onto the seated globes. Other expressions stay put."""
    key = head.data.shape_keys.key_blocks["BLINK"]
    basis = head.data.shape_keys.key_blocks["Basis"]
    changed = 0
    for index in range(len(head.data.vertices)):
        rest = basis.data[index].co
        posed = key.data[index].co
        if (posed - rest).length < 0.0004:
            continue
        sign = 1.0 if rest.x >= 0.0 else -1.0
        center = targets[sign]
        if (rest - center).length > 0.013:
            continue
        gap = (posed - center).length
        if gap <= radius + 0.0012:
            continue
        key.data[index].co = center + (posed - center).normalized() * (radius + 0.0006)
        changed += 1
    print("blink verts seated", changed)


def _new_mesh(name, material):
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(material)
    return obj


def build_teeth(head, coll, arm, chin_z, head_h):
    bc._drop_object("GEO_AVERY_TEETH")
    lip_z = chin_z + 0.20 * head_h
    lips = [vert.co for vert in head.data.vertices if abs(vert.co.x) < 0.02 and abs(vert.co.z - lip_z) < 0.012]
    if not lips:
        raise RuntimeError("could not find the lips")
    front_y = min(co.y for co in lips)
    center_z = sum(co.z for co in lips) / len(lips)
    tooth_mat = principled("MAT_AVERY_TEETH", TOOTH, 0.28)
    gum_mat = principled("MAT_AVERY_GUMS", GUM, 0.5)
    mesh = bpy.data.meshes.new("GEO_AVERY_TEETH_MESH")
    obj = bpy.data.objects.new("GEO_AVERY_TEETH", mesh)
    mesh.materials.append(tooth_mat)
    mesh.materials.append(gum_mat)
    bm = bmesh.new()
    lower_verts = []

    # Central incisors lead; laterals and canines narrow. Contact gap stays under 0.2 mm.
    upper_widths = (3.4, 3.8, 4.6, 5.4, 5.4, 4.6, 3.8, 3.4)
    lower_widths = (3.0, 3.3, 3.8, 4.2, 4.2, 3.8, 3.3, 3.0)

    def add_arch(z_center, height, y_shift, widths, lower):
        cursor = -sum(widths) / 2.0
        for width_mm in widths:
            width = width_mm / 1000.0
            x = cursor + width * 0.5
            cursor += width + 0.00015
            depth = 0.012 * (x / 0.022) ** 2
            y = front_y + 0.016 + depth * 1.8 + y_shift
            result = bmesh.ops.create_cube(bm, size=1.0)
            for vert in result["verts"]:
                vert.co.x = vert.co.x * (width * 0.5) + x
                vert.co.y = vert.co.y * 0.0032 + y
                vert.co.z = vert.co.z * (height * 0.5) + z_center
                # Round the biting edge so the row is not a set of piano keys.
                if vert.co.z > z_center + height * 0.28:
                    vert.co.y -= 0.0006
                if lower:
                    lower_verts.append(vert)
            for face in bm.faces:
                center = face.calc_center_median()
                if center.z < z_center - height * 0.18:
                    face.material_index = 1

    add_arch(center_z + 0.0062, 0.0084, 0.0, upper_widths, False)
    add_arch(center_z - 0.0068, 0.0064, 0.0020, lower_widths, True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    coll.objects.link(obj)
    bc._parent_keep_world(obj, arm, "head")
    basis = obj.shape_key_add(name="Basis", from_mix=False)
    jaw = obj.shape_key_add(name="JAW", from_mix=False)
    drop = Vector((0.0, 0.004, -0.012))
    lower_ids = {vert.index for vert in mesh.vertices if vert.co.z < center_z}
    for index, vert in enumerate(mesh.vertices):
        basis.data[index].co = vert.co
        jaw.data[index].co = vert.co + (drop if index in lower_ids else Vector())
    jaw.value = 0.0
    driver = jaw.driver_add("value").driver
    driver.type = "SCRIPTED"
    terms = []
    for name, scale in (
        ("VISEME_A", 1.0),
        ("VISEME_C", 0.28),
        ("VISEME_D", 0.55),
        ("VISEME_E", 0.22),
        ("VISEME_G", 0.35),
        ("VISEME_H", 0.30),
        ("EXP_surprise", 0.45),
    ):
        var = driver.variables.new()
        var.name = "k" + name[-1]
        var.targets[0].id_type = "OBJECT"
        var.targets[0].id = head
        var.targets[0].data_path = f'data.shape_keys.key_blocks["{name}"].value'
        terms.append(f"{scale:.2f}*{var.name}")
    driver.expression = "min(1.0, " + " + ".join(terms) + ")"
    print("teeth", len(mesh.vertices), "front y", round(front_y, 3), "lower", len(lower_ids))
    return obj


def tuck_tongue(tongue):
    if tongue is None:
        return
    for vert in tongue.data.vertices:
        vert.co.y += 0.004
        vert.co.z -= 0.001
    tongue.data.update()


def reveal_forearms(skin):
    revealed = 0
    arm_groups = []
    for name in ("forearm.L", "forearm.R", "hand.L", "hand.R", "upper_arm.L", "upper_arm.R"):
        group = skin.vertex_groups.get(name)
        if group is not None:
            arm_groups.append(group.index)
    for mod in skin.modifiers:
        if mod.type != "MASK" or not mod.vertex_group or not mod.vertex_group.startswith("Delete"):
            continue
        group = skin.vertex_groups.get(mod.vertex_group)
        if group is None:
            continue
        for vert in skin.data.vertices:
            arm_weight = 0.0
            in_delete = False
            for assignment in vert.groups:
                if assignment.group in arm_groups:
                    arm_weight += assignment.weight
                if assignment.group == group.index and assignment.weight > 0.0:
                    in_delete = True
            if in_delete and arm_weight > 0.15 and vert.co.z < 1.35:
                group.remove([vert.index])
                revealed += 1
    print("forearms revealed", revealed)


def fit_clothes(skin, arm, coll):
    from bl_ext.user_default.mpfb.entities.clothes.mhclo import Mhclo
    from bl_ext.user_default.mpfb.services.clothesservice import ClothesService

    HumanService, _target, props = bc.enable_mpfb()
    props.set_value("object_type", "Basemesh", entity_reference=skin)
    data = bc.asset_root()
    fitted = []
    for filename, kind, name in (
        ("clothes/female_casualsuit01/female_casualsuit01.mhclo", "Clothes", "GEO_AVERY_BODY"),
        ("clothes/shoes02/shoes02.mhclo", "Clothes", "GEO_AVERY_SHOES"),
    ):
        path = data / filename
        obj = bc.fit_asset(HumanService, skin, path, kind)
        obj.name = name
        bc.link_only(obj, coll)
        for mod in list(obj.modifiers):
            if mod.type == "SUBSURF":
                obj.modifiers.remove(mod)
        mhclo = Mhclo()
        mhclo.load(str(path))
        ClothesService.interpolate_weights(skin, obj, arm, mhclo)
        bc.limit_influences(obj)
        bc.bind_armature(obj, arm)
        fitted.append(obj)
        print("fitted", name, len(obj.data.vertices), len(obj.data.polygons))
    return fitted[0], fitted[1]


def _weight(obj, index, group_index):
    for assignment in obj.data.vertices[index].groups:
        if assignment.group == group_index:
            return assignment.weight
    return 0.0


def roll_sleeves(clothes, arm):
    """Remove the forearm cloth and leave a short sleeve for the rolled cuff."""
    bm = bmesh.new()
    bm.from_mesh(clothes.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    delete = []
    for side in ("L", "R"):
        bone = arm.data.bones[f"forearm.{side}"]
        origin = bone.head_local
        axis = (bone.tail_local - bone.head_local)
        length = axis.length
        axis = axis / length
        group = clothes.vertex_groups.get(f"forearm.{side}")
        hand = clothes.vertex_groups.get(f"hand.{side}")
        for face in bm.faces:
            center = face.calc_center_median()
            along = (center - origin).dot(axis)
            radial = (center - origin - axis * along).length
            weights = 0.0
            if group is not None:
                weights += sum(_weight(clothes, vert.index, group.index) for vert in face.verts) / len(face.verts)
            if hand is not None:
                weights += sum(_weight(clothes, vert.index, hand.index) for vert in face.verts) / len(face.verts)
            geometric = 0.03 < along < 0.32 and radial < 0.11 and abs(center.x) > 0.10
            if (weights > 0.15 and along > 0.03 and radial < 0.12) or geometric:
                delete.append(face)
    print("sleeve candidates", len(delete))
    bmesh.ops.delete(bm, geom=list({face.index: face for face in delete}.values()), context="FACES")
    bm.to_mesh(clothes.data)
    bm.free()
    clothes.data.update()
    print("sleeve faces removed", len(delete))


def open_jacket_front(clothes):
    """Part the center front so the warm shirt reads between the navy panels."""
    front = [vert.co.y for vert in clothes.data.vertices if 1.15 < vert.co.z < 1.45 and abs(vert.co.x) < 0.08]
    if not front:
        return
    y_cut = min(front) + 0.012
    moved = 0
    for vert in clothes.data.vertices:
        if not (1.08 < vert.co.z < 1.48 and vert.co.y < y_cut and abs(vert.co.x) < 0.06):
            continue
        sign = 1.0 if vert.co.x >= 0.0 else -1.0
        if abs(vert.co.x) < 0.004:
            sign = 1.0 if vert.index % 2 == 0 else -1.0
        vert.co.x = sign * max(abs(vert.co.x), 0.018)
        moved += 1
    clothes.data.update()
    print("jacket front opened", moved)


def paint_uniform(clothes):
    mesh = clothes.data
    existing = mesh.color_attributes.get("CLOTH")
    if existing is not None:
        mesh.color_attributes.remove(existing)
    layer = mesh.color_attributes.new("CLOTH", "FLOAT_COLOR", "POINT")
    navy = srgb(NAVY)
    navy2 = srgb(NAVY_UTILITY)
    shirt = srgb(SHIRT)
    trouser = srgb(TROUSER)
    groups = {group.name: group.index for group in clothes.vertex_groups}
    for vert in mesh.vertices:
        arm_weight = 0.0
        for name in ("upper_arm.L", "upper_arm.R", "forearm.L", "forearm.R", "hand.L", "hand.R"):
            index = groups.get(name)
            if index is not None:
                arm_weight += _weight(clothes, vert.index, index)
        if vert.co.z < 1.02 and arm_weight < 0.25:
            color = trouser
            rough = 0.62
        elif arm_weight < 0.25 and abs(vert.co.x) < 0.055 and 1.12 < vert.co.z < 1.48 and vert.co.y < -0.08:
            color = shirt
            rough = 0.68
        else:
            color = navy if abs(vert.co.x) < 0.12 else navy2
            rough = 0.43
        layer.data[vert.index].color = (float(color[0]), float(color[1]), float(color[2]), rough)
    if clothes.data.materials:
        clothes.data.materials[0] = cloth_material("MAT_AVERY_UNIFORM", 0.43)
    else:
        clothes.data.materials.append(cloth_material("MAT_AVERY_UNIFORM", 0.43))


def paint_sneakers(shoes):
    mesh = shoes.data
    existing = mesh.color_attributes.get("CLOTH")
    if existing is not None:
        mesh.color_attributes.remove(existing)
    layer = mesh.color_attributes.new("CLOTH", "FLOAT_COLOR", "POINT")
    zs = [vert.co.z for vert in mesh.vertices]
    z0, z1 = min(zs), max(zs)
    span = max(z1 - z0, 1e-4)
    navy = srgb(NAVY)
    white = srgb(SOLE)
    lace = srgb((174, 184, 192))
    for vert in mesh.vertices:
        height = (vert.co.z - z0) / span
        if height < 0.18:
            color = srgb(CHARCOAL)
            rough = 0.55
        elif height < 0.30:
            color = white
            rough = 0.55
        elif abs(vert.co.y) > 0.04 and height > 0.55:
            color = srgb(MAGENTA)
            rough = 0.38
        elif height > 0.72 and abs(vert.co.x) > 0.01 and vert.co.y < -0.02:
            color = lace
            rough = 0.38
        else:
            color = navy
            rough = 0.62
            if abs(vert.co.z - (z0 + span * 0.55)) < span * 0.04:
                color = srgb(TEAL)
                rough = 0.38
        layer.data[vert.index].color = (float(color[0]), float(color[1]), float(color[2]), rough)
    if shoes.data.materials:
        shoes.data.materials[0] = cloth_material("MAT_AVERY_SHOES", 0.42)
    else:
        shoes.data.materials.append(cloth_material("MAT_AVERY_SHOES", 0.42))


def bone_ring(name, arm, coll, bone_name, along, major, minor, color, roughness=0.5):
    bone = arm.data.bones[bone_name]
    origin = bone.head_local
    axis = bone.tail_local - bone.head_local
    axis = axis / axis.length
    center = origin + axis * along
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major, minor_radius=minor, major_segments=28, minor_segments=8,
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = name + "_MESH"
    mesh = obj.data
    obj.location = center
    obj.rotation_euler = axis.to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(principled(name + "_MAT", color, roughness))
    bc.link_only(obj, coll)
    bc._parent_keep_world(obj, arm, bone_name)
    return obj


def build_accessories(clothes, arm, coll):
    front = [
        vert.co.y for vert in clothes.data.vertices
        if abs(vert.co.x) < 0.08 and 1.20 < vert.co.z < 1.42
    ]
    chest_y = (min(front) - 0.008) if front else -0.12
    bone_ring("GEO_AVERY_BELT", arm, coll, "pelvis", 0.05, 0.148, 0.008, CHARCOAL, 0.56)
    _buckle(arm, coll)
    bone_ring("GEO_AVERY_CUFF_L", arm, coll, "forearm.L", 0.035, 0.048, 0.010, NAVY, 0.43)
    bone_ring("GEO_AVERY_CUFF_R", arm, coll, "forearm.R", 0.035, 0.048, 0.010, NAVY, 0.43)
    bone_ring("GEO_AVERY_CUFF_FLASH_L", arm, coll, "forearm.L", 0.028, 0.040, 0.0035, MAGENTA, 0.46)
    bone_ring("GEO_AVERY_CUFF_FLASH_R", arm, coll, "forearm.R", 0.030, 0.040, 0.0035, MAGENTA, 0.46)
    bone_ring("GEO_AVERY_HEM_L", arm, coll, "shin.L", 0.90, 0.052, 0.010, TROUSER, 0.62)
    bone_ring("GEO_AVERY_HEM_R", arm, coll, "shin.R", 0.88, 0.052, 0.010, TROUSER, 0.62)
    for side, alongs in (("L", (0.955, 0.968, 0.978)), ("R", (0.952, 0.966, 0.977))):
        bone_ring(f"GEO_AVERY_SOCK_{side}", arm, coll, f"shin.{side}", alongs[0], 0.040, 0.007, TROUSER, 0.66)
        bone_ring(f"GEO_AVERY_SOCK_{side}_MAG", arm, coll, f"shin.{side}", alongs[1], 0.041, 0.0022, MAGENTA, 0.66)
        bone_ring(f"GEO_AVERY_SOCK_{side}_TEAL", arm, coll, f"shin.{side}", alongs[2], 0.041, 0.0014, TEAL, 0.66)
    patch = _spark_patch("GEO_AVERY_PATCH", 0.016, 0.012)
    patch.location = (0.062, chest_y, 1.33)
    patch.rotation_euler = (math.radians(90), 0.0, 0.0)
    coll.objects.link(patch)
    bc._parent_keep_world(patch, arm, "chest")
    sleeve = _bar_patch("GEO_AVERY_PATCH_SLEEVE")
    bone = arm.data.bones["upper_arm.L"]
    sleeve.location = bone.head_local + (bone.tail_local - bone.head_local) * 0.42 + Vector((0.0, -0.05, 0.0))
    sleeve.rotation_euler = (math.radians(80), 0.0, math.radians(18))
    coll.objects.link(sleeve)
    bc._parent_keep_world(sleeve, arm, "upper_arm.L")
    print("accessories", "chest y", round(chest_y, 3))


def _spark_patch(name, half_w, half_h):
    """32×24 mm woven patch: one four-point spark between two chevrons. No words."""
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = bpy.data.objects.new(name, mesh)
    bm = bmesh.new()
    cloth = principled("MAT_AVERY_PATCH", (236, 232, 223), 0.58)
    spark = principled("MAT_AVERY_SPARK", TEAL, 0.58)
    mesh.materials.append(cloth)
    mesh.materials.append(spark)
    plate = bmesh.ops.create_cube(bm, size=1.0)
    for vert in plate["verts"]:
        vert.co.x *= half_w
        vert.co.y *= half_h
        vert.co.z *= 0.0004
    spark_verts = []
    for angle, radius in ((-90, 1.0), (0, 0.28), (0, 1.0), (90, 0.28), (90, 1.0), (180, 0.28), (180, 1.0), (270, 0.28)):
        rad = math.radians(angle)
        spark_verts.append(bm.verts.new((
            math.cos(rad) * half_w * 0.34 * radius,
            math.sin(rad) * half_h * 0.55 * radius + half_h * 0.05,
            0.0007,
        )))
    # Two short tapered chevrons under the spark. Not wings, a bird, or a seal.
    for y_shift, scale in ((-0.35, 1.0), (-0.62, 0.72)):
        chevron = [
            bm.verts.new((-half_w * 0.55 * scale, half_h * y_shift, 0.0007)),
            bm.verts.new((0.0, half_h * (y_shift + 0.22), 0.0007)),
            bm.verts.new((half_w * 0.55 * scale, half_h * y_shift, 0.0007)),
            bm.verts.new((half_w * 0.42 * scale, half_h * (y_shift - 0.08), 0.0007)),
            bm.verts.new((0.0, half_h * (y_shift + 0.08), 0.0007)),
            bm.verts.new((-half_w * 0.42 * scale, half_h * (y_shift - 0.08), 0.0007)),
        ]
        face = bm.faces.new(chevron)
        face.material_index = 1
    if len(spark_verts) >= 8:
        try:
            face = bm.faces.new(spark_verts[:8])
            face.material_index = 1
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    return obj


def _bar_patch(name):
    """48×18 mm sleeve patch: three staggered teal/cyan/magenta bars and three dots."""
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = bpy.data.objects.new(name, mesh)
    bm = bmesh.new()
    colors = (TEAL, CYAN, MAGENTA)
    mesh.materials.append(principled("MAT_AVERY_PATCH_GROUND", (236, 232, 223), 0.58))
    for index, color in enumerate(colors):
        mesh.materials.append(principled(f"MAT_AVERY_BAR_{index}", color, 0.58))
    ground = bmesh.ops.create_cube(bm, size=1.0)
    for vert in ground["verts"]:
        vert.co.x *= 0.024
        vert.co.y *= 0.009
        vert.co.z *= 0.0004
    for index, color in enumerate(colors):
        bar = bmesh.ops.create_cube(bm, size=1.0)
        for vert in bar["verts"]:
            vert.co.x = vert.co.x * 0.016 + (index - 1) * 0.004
            vert.co.y = vert.co.y * 0.0016 + 0.004 - index * 0.0032
            vert.co.z = vert.co.z * 0.0003 + 0.0006
        for face in bm.faces:
            if face.calc_center_median().z > 0.0005 and face.material_index == 0:
                center = face.calc_center_median()
                if abs(center.y - (0.004 - index * 0.0032)) < 0.001:
                    face.material_index = index + 1
    for index in range(3):
        dot = bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=0.0007)
        for vert in dot["verts"]:
            vert.co.x += -0.016 + index * 0.006
            vert.co.y += -0.006
            vert.co.z += 0.0006
    bm.to_mesh(mesh)
    bm.free()
    return obj


def _buckle(arm, coll):
    bone = arm.data.bones["pelvis"]
    origin = bone.head_local
    axis = bone.tail_local - bone.head_local
    axis = axis / axis.length
    center = origin + axis * 0.05 + Vector((0.0, -0.155, 0.0))
    mesh = bpy.data.meshes.new("GEO_AVERY_BUCKLE_MESH")
    obj = bpy.data.objects.new("GEO_AVERY_BUCKLE", mesh)
    bm = bmesh.new()
    cube = bmesh.ops.create_cube(bm, size=1.0)
    for vert in cube["verts"]:
        vert.co.x *= 0.012
        vert.co.y *= 0.003
        vert.co.z *= 0.008
    keeper = bmesh.ops.create_cube(bm, size=1.0)
    for vert in keeper["verts"]:
        vert.co.x = vert.co.x * 0.003 + 0.016
        vert.co.y *= 0.003
        vert.co.z *= 0.006
    bm.to_mesh(mesh)
    bm.free()
    obj.location = center
    mesh.materials.append(principled("MAT_AVERY_BUCKLE", GUNMETAL, 0.34))
    mesh.materials.append(principled("MAT_AVERY_KEEPER", MAGENTA, 0.56))
    for poly in mesh.polygons:
        if poly.center.x > 0.012:
            poly.material_index = 1
    buckle_bsdf = _bsdf(mesh.materials[0])
    if "Metallic" in buckle_bsdf.inputs:
        buckle_bsdf.inputs["Metallic"].default_value = 0.70
    coll.objects.link(obj)
    bc._parent_keep_world(obj, arm, "pelvis")


def build_updo(head, arm, coll):
    """Espresso braids into a three-lobed crown, peaked toward Avery's right (-X)."""
    bc._drop_object("GEO_AVERY_HAIR")
    for name in ("GEO_AVERY_BRAIDS", "GEO_AVERY_CROWN"):
        bc._drop_object(name)
    mat = hair_material()
    crown = max(vert.co.z for vert in head.data.vertices)
    # Avery faces -Y. Her right is -X. The peak sits ~20 mm that way and ~85 mm up.
    gather = Vector((-0.020, 0.034, crown + 0.078))
    mesh = bpy.data.meshes.new("GEO_AVERY_HAIR_MESH")
    obj = bpy.data.objects.new("GEO_AVERY_HAIR", mesh)
    bm = bmesh.new()
    lobes = (
        (gather + Vector((-0.012, 0.008, 0.028)), (0.046, 0.040, 0.038)),
        (gather + Vector((0.018, -0.006, 0.012)), (0.038, 0.034, 0.032)),
        (gather + Vector((-0.004, 0.022, 0.006)), (0.034, 0.030, 0.028)),
    )
    for center, scale in lobes:
        lobe = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0)
        for vert in lobe["verts"]:
            vert.co.x = vert.co.x * scale[0] + center.x
            vert.co.y = vert.co.y * scale[1] + center.y
            vert.co.z = vert.co.z * scale[2] + center.z
    for sign, y, z in ((1.0, -0.048, crown - 0.062), (-1.0, -0.042, crown - 0.058), (0.15, 0.055, crown - 0.095)):
        coil = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=1.0)
        for vert in coil["verts"]:
            vert.co.x = vert.co.x * 0.016 + sign * 0.072
            vert.co.y = vert.co.y * 0.014 + y
            vert.co.z = vert.co.z * 0.020 + z
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(mat)
    coll.objects.link(obj)
    bc._parent_keep_world(obj, arm, "head")
    _braids(arm, coll, mat, crown, gather)
    print("updo lobes", "crown", round(crown, 3), "gather", tuple(round(c, 3) for c in gather))
    return obj


def _braids(arm, coll, mat, crown, gather):
    curve = bpy.data.curves.new("GEO_AVERY_BRAIDS", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 8
    curve.bevel_depth = 0.0055
    curve.bevel_resolution = 3
    curve.use_fill_caps = True
    # Seven channels: left temple and nape sweep diagonally into the right-rear gather.
    paths = [
        ((0.07, -0.04, crown - 0.09), (0.02, -0.01, crown - 0.01), gather + Vector((0.0, 0.0, 0.01))),
        ((0.05, -0.02, crown - 0.05), (0.0, 0.01, crown + 0.02), gather),
        ((0.08, 0.02, crown - 0.08), (0.01, 0.03, crown), gather + Vector((0.0, 0.01, 0.0))),
        ((-0.02, 0.07, crown - 0.10), (-0.02, 0.05, crown - 0.02), gather + Vector((0.0, 0.012, -0.005))),
        ((0.0, 0.08, crown - 0.07), (-0.015, 0.05, crown), gather),
        ((-0.06, 0.04, crown - 0.06), (-0.03, 0.03, crown + 0.01), gather + Vector((-0.008, 0.0, 0.012))),
        ((-0.07, -0.01, crown - 0.07), (-0.04, 0.01, crown), gather + Vector((-0.01, 0.0, 0.02))),
    ]
    for path in paths:
        spline = curve.splines.new("BEZIER")
        spline.bezier_points.add(len(path) - 1)
        for point, co in zip(spline.bezier_points, path):
            point.co = Vector(co)
            point.handle_left_type = "AUTO"
            point.handle_right_type = "AUTO"
            point.tilt = 0.8
    braids = bpy.data.objects.new("GEO_AVERY_BRAIDS", curve)
    braids.data.materials.append(mat)
    coll.objects.link(braids)
    bc._parent_keep_world(braids, arm, "head")


def build_glasses(targets, radius, arm, coll):
    """Rounded trapezoid frames, 48 mm lenses, 18 mm bridge, 138 mm temples."""
    curve = bpy.data.curves.new("GEO_AVERY_GLASSES", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 8
    curve.bevel_depth = 0.0015
    curve.bevel_resolution = 2
    curve.use_fill_caps = True
    lens_w = 0.024
    lens_h = 0.016
    bridge = 0.018
    # Place the pair on the face center so the bridge is 18 mm, not the eye spacing.
    mid_y = (targets[1.0].y + targets[-1.0].y) * 0.5 - 0.006
    mid_z = (targets[1.0].z + targets[-1.0].z) * 0.5
    centers = {
        1.0: Vector((targets[1.0].x, mid_y, mid_z)),
        -1.0: Vector((targets[-1.0].x, mid_y, mid_z)),
    }

    def trapezoid(center, sign):
        spline = curve.splines.new("POLY")
        top = lens_w * 1.08
        bot = lens_w * 0.92
        corners = (
            (center.x - sign * top, center.y, center.z + lens_h),
            (center.x + sign * top, center.y, center.z + lens_h * 0.92),
            (center.x + sign * bot, center.y, center.z - lens_h * 0.82),
            (center.x - sign * bot, center.y, center.z - lens_h),
        )
        spline.points.add(len(corners) - 1)
        for point, co in zip(spline.points, corners):
            point.co = (*co, 1.0)
        spline.use_cyclic_u = True

    trapezoid(centers[1.0], 1.0)
    trapezoid(centers[-1.0], -1.0)
    span = curve.splines.new("POLY")
    span.points.add(1)
    span.points[0].co = (centers[-1.0].x + lens_w * 0.92, mid_y, mid_z + 0.002, 1.0)
    span.points[1].co = (centers[1.0].x - lens_w * 0.92, mid_y, mid_z + 0.002, 1.0)
    for sign, center in centers.items():
        temple = curve.splines.new("POLY")
        temple.points.add(3)
        hinge_x = center.x + sign * lens_w * 1.05
        temple.points[0].co = (hinge_x, mid_y, mid_z, 1.0)
        temple.points[1].co = (hinge_x + sign * 0.012, mid_y + 0.035, mid_z + 0.004, 1.0)
        temple.points[2].co = (hinge_x + sign * 0.010, mid_y + 0.095, mid_z - 0.006, 1.0)
        temple.points[3].co = (hinge_x + sign * 0.004, mid_y + 0.128, mid_z - 0.016, 1.0)
    glasses = bpy.data.objects.new("GEO_AVERY_GLASSES", curve)
    glasses.data.materials.append(principled("MAT_AVERY_GLASSES", FRAME, 0.32))
    coll.objects.link(glasses)
    bc._parent_keep_world(glasses, arm, "head")
    lens_mat = principled("MAT_AVERY_LENS", (210, 220, 224), 0.035)
    lens_bsdf = _bsdf(lens_mat)
    if "Transmission Weight" in lens_bsdf.inputs:
        lens_bsdf.inputs["Transmission Weight"].default_value = 1.0
    elif "Transmission" in lens_bsdf.inputs:
        lens_bsdf.inputs["Transmission"].default_value = 1.0
    if "IOR" in lens_bsdf.inputs:
        lens_bsdf.inputs["IOR"].default_value = 1.46
    for sign, center in centers.items():
        lens_mesh = bpy.data.meshes.new(f"GEO_AVERY_LENS_{'L' if sign > 0 else 'R'}")
        lens = bpy.data.objects.new(lens_mesh.name, lens_mesh)
        bm = bmesh.new()
        face_verts = []
        for x_mul, z_mul in ((-1, 1), (1, 0.92), (1, -0.82), (-1, -1)):
            face_verts.append(bm.verts.new((
                center.x + sign * x_mul * (lens_w * (1.02 if z_mul > 0 else 0.86)),
                center.y + 0.0008,
                center.z + z_mul * lens_h * 0.92,
            )))
        bm.faces.new(face_verts)
        bm.to_mesh(lens_mesh)
        bm.free()
        lens.data.materials.append(lens_mat)
        coll.objects.link(lens)
        bc._parent_keep_world(lens, arm, "head")
    return glasses


def nudge_lanyard(arm):
    lanyard = bpy.data.objects.get("GEO_AVERY_LANYARD")
    if lanyard is None:
        return
    # Keep the archived blank badge. Only seat it on the new chest.
    if lanyard.parent_type != "BONE":
        bc._parent_keep_world(lanyard, arm, "chest")


def _cli_paths():
    """--output and --report follow Blender's `--`. Defaults stay in the store."""
    output = STAGING
    report = Path("/tmp/avery-chen-v3-build.json")
    argv = sys.argv
    if "--" in argv:
        tail = argv[argv.index("--") + 1:]
    else:
        tail = []
    index = 0
    while index < len(tail):
        token = tail[index]
        if token == "--output" and index + 1 < len(tail):
            output = Path(tail[index + 1])
            index += 2
            continue
        if token == "--report" and index + 1 < len(tail):
            report = Path(tail[index + 1])
            index += 2
            continue
        index += 1
    return output, report


def _reject_machine_local(path, label):
    text = str(path)
    blocked = ("/cursor/stores", "/tmp", "/home/")
    if any(part in text for part in blocked):
        raise SystemExit(f"{label} must be repository-relative, not {text}")


def build(output_path=None):
    output_path = Path(output_path) if output_path is not None else STAGING
    bpy.ops.wm.open_mainfile(filepath=str(PRIMARY))
    head = bpy.data.objects["GEO_AVERY_HEAD"]
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    coll = bpy.data.collections["COL_AVERY_CHEN"]
    if arm.animation_data:
        arm.animation_data.action = None
    bc.reset_pose(arm)
    for key in head.data.shape_keys.key_blocks:
        key.value = 0.0
    keys_before = [key.name for key in head.data.shape_keys.key_blocks]
    for name in ("GEO_AVERY_BODY", "GEO_AVERY_SHOES", "GEO_AVERY_HAIR", "GEO_AVERY_BINDING"):
        bc._drop_object(name)
    chin_z, head_h, _nose = paint_deep_skin(head)
    friendly_face(head, chin_z, head_h)
    enlarge_hands(head, arm)
    reveal_forearms(head)
    eyes = bpy.data.objects["GEO_AVERY_EYES"]
    targets, radius = seat_eyes(head, eyes)
    lift_brows(bpy.data.objects["GEO_AVERY_BROWS"], targets, radius)
    close_blink(head, targets, radius)
    build_teeth(head, coll, arm, chin_z, head_h)
    tuck_tongue(bpy.data.objects.get("GEO_AVERY_TONGUE"))
    clothes, shoes = fit_clothes(head, arm, coll)
    roll_sleeves(clothes, arm)
    open_jacket_front(clothes)
    paint_uniform(clothes)
    paint_sneakers(shoes)
    build_accessories(clothes, arm, coll)
    build_updo(head, arm, coll)
    build_glasses(targets, radius, arm, coll)
    nudge_lanyard(arm)
    keys_after = [key.name for key in head.data.shape_keys.key_blocks]
    if keys_after != keys_before:
        raise RuntimeError(f"head shape keys changed: {keys_after}")
    for key in head.data.shape_keys.key_blocks:
        key.value = 0.0
    bpy.ops.file.pack_all()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path), relative_remap=False, copy=True)
    print("V3 staged", output_path)
    return output_path


def _open_staging():
    if not STAGING.is_file():
        raise RuntimeError("V3 staging blend is missing; run build first")
    bpy.ops.wm.open_mainfile(filepath=str(STAGING))


def _v3_studio(scene):
    """AgX Medium High Contrast, cool gray ground, and the locked key/fill/rim ratio."""
    bc.studio(scene)
    scene.view_settings.view_transform = "AgX"
    look = "AgX - Medium High Contrast"
    if look in scene.view_settings.bl_rna.properties["look"].enum_items.keys():
        scene.view_settings.look = look
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    world = scene.world
    if world and world.node_tree:
        bg = world.node_tree.nodes.get("Background")
        if bg:
            bg.inputs[0].default_value = (*srgb((199, 205, 209)), 1.0)
            bg.inputs[1].default_value = 1.0
    lights = {obj.name: obj for obj in scene.objects if obj.type == "LIGHT"}
    # Camera looks from -Y. Camera-left is -X. Key is 40° that way and 30° up.
    if "KEY" in lights:
        lights["KEY"].location = (-1.9, -2.6, 2.35)
        lights["KEY"].data.energy = 220
        lights["KEY"].data.size = 2.4
        if hasattr(lights["KEY"].data, "temperature"):
            lights["KEY"].data.temperature = 5600
    if "FILL" in lights:
        lights["FILL"].location = (0.2, -2.8, 1.7)
        lights["FILL"].data.energy = 88
        lights["FILL"].data.size = 3.2
    if "RIM" in lights:
        lights["RIM"].location = (1.6, 1.8, 2.2)
        lights["RIM"].data.energy = 55
        if hasattr(lights["RIM"].data, "temperature"):
            lights["RIM"].data.temperature = 6200
    for obj in lights.values():
        bc.look_at(obj, (0.0, 0.0, 1.45))


def render():
    from PIL import Image, ImageDraw
    _open_staging()
    scene = bpy.context.scene
    head = bpy.data.objects["GEO_AVERY_HEAD"]
    arm = bpy.data.objects["RIG_AVERY_CHEN"]
    arm.hide_render = True
    if arm.animation_data:
        arm.animation_data.action = None
    bc.reset_pose(arm)
    bc.neutral_shapes(head)
    scene.frame_set(1)
    _v3_studio(scene)
    MEDIA.mkdir(parents=True, exist_ok=True)
    samples = int(os.environ.get("AVERY_SAMPLES", "12"))
    scene.cycles.samples = samples
    stats = bc.measure_anatomy(head)
    crown = stats["crown_z"]
    stature = stats["stature_m"]
    eye_z = crown - 0.10
    mid_z = stature * 0.48
    # 70 mm on a 24 mm vertical sensor, pulled back so the body stays inside the frame.
    body_dist = 6.05

    def still(name, loc, target, lens, rx, ry, ortho=None, sample_count=None):
        if sample_count is not None:
            scene.cycles.samples = sample_count
        scene.render.resolution_x = rx
        scene.render.resolution_y = ry
        bc._cam(scene, loc, target, lens, "CAM_" + name, ortho)
        path = MEDIA / name
        bc.render_still(scene, path)
        scene.cycles.samples = samples
        return path

    still("full-body-front.png", (0.0, -body_dist, mid_z), (0.0, 0.0, mid_z), 70, 900, 1600)
    still("full-body-side.png", (body_dist, 0.0, mid_z), (0.0, 0.0, mid_z), 70, 900, 1600)
    still("full-body-back.png", (0.0, body_dist, mid_z), (0.0, 0.0, mid_z), 70, 900, 1600)
    yaw = math.radians(35.0)
    still(
        "full-body-three-quarter.png",
        (math.sin(yaw) * body_dist, -math.cos(yaw) * body_dist, mid_z),
        (0.0, 0.0, mid_z),
        70, 900, 1600,
    )
    still("front-closeup.png", (0.0, -1.65, eye_z), (0.0, 0.0, eye_z - 0.02), 85, 960, 1200)
    turn = Image.new("RGB", (900 * 4, 1600))
    for index, name in enumerate((
        "full-body-front.png",
        "full-body-three-quarter.png",
        "full-body-side.png",
        "full-body-back.png",
    )):
        turn.paste(Image.open(MEDIA / name).convert("RGB"), (index * 900, 0))
    turn.save(MEDIA / "turnaround.png")

    if REFERENCE.is_file():
        ref = Image.open(REFERENCE).convert("RGB")
        hero = Image.open(MEDIA / "full-body-front.png").convert("RGB")
        ref.thumbnail((900, 1600))
        sheet = Image.new("RGB", (ref.width + hero.width, max(ref.height, hero.height)), (40, 40, 42))
        sheet.paste(ref, (0, 0))
        sheet.paste(hero, (ref.width, 0))
        ImageDraw.Draw(sheet).text((16, 16), "reference", fill=(240, 240, 240))
        ImageDraw.Draw(sheet).text((ref.width + 16, 16), "avery v3", fill=(240, 240, 240))
        sheet.save(MEDIA / "reference-comparison.png")

    # Eye and brow alignment, neutral.
    still("eye-brow-alignment.png", (0.0, -0.85, eye_z), (0.0, 0.0, eye_z), 90, 1200, 700)

    scene.render.resolution_x = 480
    scene.render.resolution_y = 480
    scene.cycles.samples = min(8, samples)
    bc._cam(scene, (0.0, -0.72, eye_z - 0.04), (0.0, 0.0, eye_z - 0.05), 70, "CAM_FACE")
    qa = Path("/tmp/avery-v3-qa")
    qa.mkdir(parents=True, exist_ok=True)
    bc.set_shape(head, "VISEME_A", 1.0)
    bc.render_still(scene, MEDIA / "dental-open.png")
    bc.neutral_shapes(head)
    bc.set_shape(head, "EXP_smile", 1.0)
    bc.render_still(scene, MEDIA / "dental-smile.png")
    bc.neutral_shapes(head)
    dental = Image.new("RGB", (960, 480))
    dental.paste(Image.open(MEDIA / "dental-open.png").convert("RGB"), (0, 0))
    dental.paste(Image.open(MEDIA / "dental-smile.png").convert("RGB"), (480, 0))
    dental.save(MEDIA / "dental-sheet.png")

    viseme_paths = []
    for name in bc.VISEMES:
        bc.set_shape(head, name, 1.0)
        path = qa / f"{name}.png"
        bc.render_still(scene, path)
        viseme_paths.append(path)
    bc.neutral_shapes(head)
    bc.montage(viseme_paths, MEDIA / "viseme-strip.png", columns=9)

    expr_paths = []
    for name in bc.EXPRESSIONS:
        bc.set_shape(head, name, 1.0)
        path = qa / f"{name}.png"
        bc.render_still(scene, path)
        expr_paths.append(path)
    bc.neutral_shapes(head)
    bc.montage(expr_paths, MEDIA / "expression-sheet.png", columns=4)

    combo_paths = []
    for label, shapes in (
        ("smile-A", (("EXP_smile", 1.0), ("VISEME_A", 0.65))),
        ("smile-E", (("EXP_smile", 1.0), ("VISEME_E", 0.8))),
        ("smile-B", (("EXP_smile", 0.6), ("VISEME_B", 1.0))),
        ("surprise-A", (("EXP_surprise", 1.0), ("VISEME_A", 0.5))),
        ("frown-D", (("EXP_frown", 1.0), ("VISEME_D", 0.7))),
        ("blink-smile", (("BLINK", 1.0), ("EXP_smile", 1.0))),
    ):
        bc.neutral_shapes(head)
        for name, value in shapes:
            head.data.shape_keys.key_blocks[name].value = value
        path = qa / f"combo-{label}.png"
        bc.render_still(scene, path)
        combo_paths.append(path)
    bc.neutral_shapes(head)
    bc.montage(combo_paths, MEDIA / "expression-viseme-combos.png", columns=3)

    scene.render.resolution_x = 480
    scene.render.resolution_y = 720
    scene.cycles.samples = min(8, samples)
    shoulder_paths = []
    for view, loc in (("front", (0.0, -5.15, mid_z)), ("three-quarter", (1.45, -4.7, mid_z))):
        for angle in (0.0, 45.0, 90.0, 120.0):
            bc._stop(arm)
            bc.neutral_shapes(head)
            if angle:
                arm.pose.bones["upper_arm.L"].rotation_euler.z = math.radians(angle)
                arm.pose.bones["upper_arm.R"].rotation_euler.z = math.radians(-angle)
                bpy.context.view_layer.update()
            bc._cam(scene, loc, (0.0, 0.0, mid_z), 60, "CAM_SHOULDER")
            path = qa / f"shoulder-{view}-{int(angle)}.png"
            bc.render_still(scene, path)
            shoulder_paths.append(path)
    bc._stop(arm)
    bc.montage(shoulder_paths, MEDIA / "shoulder-tests.png", columns=4)

    scene.render.resolution_x = 420
    scene.render.resolution_y = 720
    bc._cam(scene, (0.35, -4.6, mid_z), (0.0, 0.0, mid_z), 60, "CAM_DEFORM")
    deform_paths = []
    for label, action_name, frame in (
        ("rest", None, 1),
        ("elbows-knees", "manual", 1),
        ("shoulders-90", "shoulders", 1),
        ("walk_cycle", "walk_cycle", 7),
        ("gesture_present", "gesture_present", 14),
        ("reach_grab", "reach_grab", 16),
    ):
        bc._stop(arm)
        bc.neutral_shapes(head)
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
            bc._play(arm, action_name, frame)
        path = qa / f"deform-{label}.png"
        bc.render_still(scene, path)
        deform_paths.append(path)
    bc._stop(arm)
    bc.montage(deform_paths, MEDIA / "deformation-sheet.png", columns=3)

    action_frames = {
        "idle_neutral_loop": 24, "walk_cycle": 7, "turn_left_90": 18, "turn_right_90": 18,
        "gesture_present": 14, "point_left": 12, "point_right": 12, "wave": 10,
        "head_nod": 7, "head_shake": 8, "reach_grab": 16, "place_release": 16,
    }
    scene.render.resolution_x = 320
    scene.render.resolution_y = 520
    bc._cam(scene, (0.2, -4.8, mid_z), (0.0, 0.0, mid_z), 60, "CAM_ACT")
    action_paths = []
    for name in bc.ACTIONS:
        bc._play(arm, name, action_frames.get(name, 1))
        path = qa / f"act-{name}.png"
        bc.render_still(scene, path)
        action_paths.append(path)
    bc._stop(arm)
    bc.montage(action_paths, MEDIA / "action-sheet.png", columns=5)
    print("V3 previews", MEDIA)


def verify():
    _open_staging()
    lines = []
    ok = True

    def check(label, passed, detail=""):
        nonlocal ok
        ok = ok and bool(passed)
        lines.append(f"{'PASS' if passed else 'FAIL'}: {label}" + (f" — {detail}" if detail else ""))

    coll = bpy.data.collections.get("COL_AVERY_CHEN")
    arm = bpy.data.objects.get("RIG_AVERY_CHEN")
    head = bpy.data.objects.get("GEO_AVERY_HEAD")
    check("collection COL_AVERY_CHEN", coll is not None)
    check("armature RIG_AVERY_CHEN", arm is not None and arm.type == "ARMATURE")
    check("material MAT_PROXY_CHARACTER", bpy.data.materials.get("MAT_PROXY_CHARACTER") is not None)
    check("material MAT_PROXY_FOCUS", bpy.data.materials.get("MAT_PROXY_FOCUS") is not None)
    if arm is not None:
        names = {bone.name for bone in arm.data.bones}
        for bone in bc.CONTRACT_BONES:
            check(f"bone {bone}", bone in names)
        parents = {bone.name: (bone.parent.name if bone.parent else "") for bone in arm.data.bones}
        expected = {
            "pelvis": "root", "spine": "pelvis", "chest": "spine", "neck": "chest", "head": "neck",
            "upper_arm.L": "chest", "forearm.L": "upper_arm.L", "hand.L": "forearm.L",
            "upper_arm.R": "chest", "forearm.R": "upper_arm.R", "hand.R": "forearm.R",
            "thigh.L": "pelvis", "shin.L": "thigh.L", "foot.L": "shin.L",
            "thigh.R": "pelvis", "shin.R": "thigh.R", "foot.R": "shin.R",
        }
        check("bone hierarchy", all(parents.get(name) == parent for name, parent in expected.items()))
    check("head mesh", head is not None)
    if head is not None and head.data.shape_keys:
        present = {key.name for key in head.data.shape_keys.key_blocks}
        for name in bc.VISEMES + bc.EXPRESSIONS:
            key = head.data.shape_keys.key_blocks.get(name)
            delta = 0.0
            if key is not None:
                basis = head.data.shape_keys.key_blocks["Basis"]
                delta = max((key.data[i].co - basis.data[i].co).length for i in range(0, len(head.data.vertices), 17))
            check(f"shape {name}", name in present and delta > 0.0005, f"delta {delta:.4f} m")
    if arm is not None:
        actions = {action.name for action in bpy.data.actions}
        for name in bc.ACTIONS:
            check(f"action {name}", name in actions)
    tri = 0
    if coll is not None:
        for obj in coll.objects:
            if obj.type in {"MESH", "CURVE"}:
                tri += bc.rendered_triangles(obj)
    check("rendered triangles ≤ 80000", tri <= 80000, str(tri))
    images = [img for img in bpy.data.images if img.size[0] > 0]
    texture_mb = sum(img.size[0] * img.size[1] * 4 / (1024 * 1024) for img in images)
    packed_mb = sum(len(img.packed_file.data) for img in images if img.packed_file) / (1024 * 1024)
    lines.append(f"INFO: textures uncompressed {texture_mb:.1f} MB, packed {packed_mb:.1f} MB")
    lines.append(f"INFO: triangles {tri}")
    eyes = bpy.data.objects.get("GEO_AVERY_EYES")
    if eyes is not None and head is not None:
        left = bc.group_center(head, "joint-l-eye")
        right = bc.group_center(head, "joint-r-eye")
        centers = {}
        for vert in eyes.data.vertices:
            sign = 1.0 if vert.co.x >= 0.0 else -1.0
            centers.setdefault(sign, []).append(vert.co.copy())
        for sign, socket in ((1.0, left), (-1.0, right)):
            center = sum(centers[sign], Vector()) / len(centers[sign])
            gap = (Vector((center.x, 0.0, center.z)) - Vector((socket.x, 0.0, socket.z))).length
            check(f"eye socket {'L' if sign > 0 else 'R'}", gap < 0.004, f"gap {gap * 1000:.1f} mm")
        z_delta = abs(
            (sum(centers[1.0], Vector()) / len(centers[1.0])).z
            - (sum(centers[-1.0], Vector()) / len(centers[-1.0])).z
        )
        check("eye vertical match", z_delta < 0.001, f"{z_delta * 1000:.2f} mm")
    check("glasses present", bpy.data.objects.get("GEO_AVERY_GLASSES") is not None)
    check("updo present", bpy.data.objects.get("GEO_AVERY_HAIR") is not None)
    check("sleeves object absent", bpy.data.objects.get("GEO_AVERY_SLEEVE_L") is None)
    lines.append("RESULT: PASS" if ok else "RESULT: FAIL")
    text = "\n".join(lines) + "\n"
    VERIFY_LOG.parent.mkdir(parents=True, exist_ok=True)
    VERIFY_LOG.write_text(text)
    print(text)
    if not ok:
        sys.exit(1)
    return tri, texture_mb, packed_mb


def publish():
    if not STAGING.is_file():
        raise SystemExit("refusing to publish without a staged blend")
    log = VERIFY_LOG.read_text() if VERIFY_LOG.is_file() else ""
    if "RESULT: PASS" not in log:
        raise SystemExit("refusing to publish before verify passes")
    PRIMARY.write_bytes(STAGING.read_bytes())
    print("published", PRIMARY, "sha will be computed by the caller")


def write_build_report(blend_path, report_path):
    """JSON the manifest is allowed to copy from. No placeholder hashes."""
    import hashlib
    import json
    _open = bpy.ops.wm.open_mainfile
    _open(filepath=str(blend_path))
    digest = hashlib.sha256(Path(blend_path).read_bytes()).hexdigest()
    coll = bpy.data.collections["COL_AVERY_CHEN"]
    triangles = 0
    for obj in coll.objects:
        if obj.type in {"MESH", "CURVE"}:
            triangles += bc.rendered_triangles(obj)
    images = [img for img in bpy.data.images if img.size[0] > 0]
    texture_mb = sum(img.size[0] * img.size[1] * 4 / (1024 * 1024) for img in images)
    actions = []
    for name in bc.ACTIONS:
        action = bpy.data.actions[name]
        start, end = action.frame_range
        actions.append({
            "name": name,
            "duration_frames": int(round(end - start)) + 1,
            "loop": name in {"idle_neutral_loop", "walk_cycle"},
        })
    payload = {
        "file": "characters/AveryChen.blend",
        "collection": "COL_AVERY_CHEN",
        "armature": "RIG_AVERY_CHEN",
        "retarget_profile": "proxy_rig_v1",
        "sha256": digest,
        "blender_min": "5.2.1",
        "version": "3.0.0",
        "triangles": triangles,
        "texture_memory_estimate_mb": round(texture_mb, 1),
        "actions": actions,
        "visemes": list(bc.VISEMES),
        "facial_controls": list(bc.EXPRESSIONS),
        "license": "CC0-1.0",
        "source": "makehuman-community:mpfb2+cc0-system-assets",
        "style_id": "avery_chen_v3",
    }
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2) + "\n")
    print("report", report_path, digest)


def main():
    output_path, report_path = _cli_paths()
    mode = bc.argv_tail()
    if "verify" in mode:
        verify()
    elif "render" in mode:
        render()
    elif "publish" in mode:
        publish()
    elif "build" in mode or "--output" in sys.argv:
        built = build(output_path)
        write_build_report(built, report_path)
    else:
        raise SystemExit(
            "Use build, render, verify, or publish. "
            "Repository invocation: --output assets/characters/AveryChen.blend --report build.json"
        )


if __name__ == "__main__":
    main()
