#!/usr/bin/env python3
"""Build Avery Chen toon/cel hero from the coherent V3 body pipeline.

Keeps COL_AVERY_CHEN, RIG_AVERY_CHEN, actions, and facial shape keys intact.
Replaces PBR materials with flat cel fills + Freestyle ink outlines for
illustrated-character reads in a 3D scene.

  blender --background --factory-startup --python docs/avery-toon/build_avery_toon.py
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

TOON_ROOT = Path(__file__).resolve().parent
STORE_ROOT = TOON_ROOT.parent.parent
CHEN_ROOT = STORE_ROOT / "docs" / "avery-chen"
CHEN_SCRIPT = CHEN_ROOT / "scripts" / "build_avery_chen.py"
DEFAULT_SOURCE = CHEN_ROOT / "vendor" / "avery-chen" / "coherent-base.blend"
DEFAULT_OUTPUT = TOON_ROOT / "AveryToon.blend"
DEFAULT_RENDER_DIR = STORE_ROOT / "media" / "avery-toon"
AFRO_PLUM_HEX = "#6B2D5B"
BROW_PLANE_Y = -0.036
HAIR_SPHERE_SEGMENTS = 48
HAIR_BROW_Z_OFFSET_M = 0.078
# Afro mass is measured off the head, not fixed: a hard-coded radius is what
# left the crown bald (sphere top sat under the scalp, so only the silhouette
# ring read as hair). Every dimension below is relative to the real head.
AFRO_CROWN_CLEARANCE_M = 0.055  # hair top above measured scalp top
AFRO_WIDTH_RATIO = 1.55  # afro width / head width, per media/avery-flat/front.png
AFRO_DEPTH_RATIO = 1.35
AFRO_MASS_CENTER_Z_M = 0.070  # mass center above the head bone
AFRO_MIN_RADIUS_M = 0.105
# Clip only the face window. Clipping the whole front hemisphere also removed
# the temple volume that frames the face on the flat plate.
HAIR_FACE_WINDOW_HALF_X_M = 0.062
# Curl-cluster puffs: a handful of smaller overlapping spheres stuck onto the
# main cap, the standard cheap trick for stylized curl clumps. Deterministic
# (fixed seed) so rebuilds are reproducible for QA.
AFRO_PUFF_SEED = 20260217
AFRO_PUFF_COUNT = 11
AFRO_PUFF_SEGMENTS = 10
AFRO_PUFF_RADIUS_RATIO = 0.40  # puff radius / local cap radius, before jitter
AFRO_PUFF_RADIUS_JITTER = 0.25  # +/- fraction applied per puff
AFRO_PUFF_OVERLAP_RATIO = 0.62  # how far the puff center is pulled inside the cap surface
AFRO_PUFF_MIN_PHI_DEG = 15.0  # polar angle from +Z; excludes the crown apex
AFRO_PUFF_MAX_PHI_DEG = 100.0  # excludes straight-down/behind-jaw placement
AFRO_STREAK_PUFF_FRACTION = 0.32  # fraction of puffs tinted magenta (streak clumps)
# Silhouette noise on the cap's own surface (applied to the unit sphere
# before ellipsoid scaling), so even non-puffed regions aren't perfectly smooth.
AFRO_SILHOUETTE_NOISE_AMPLITUDE_M = 0.012
# Wavy clip boundary instead of a flat line (reads as a curl-fringe edge).
HAIR_FRINGE_EDGE_NOISE_M = 0.009
# A few explicit puffs straddling the face-window edges, so the (now wavy)
# clip trims them into loose face-framing wisps instead of a clean cut.
HAIR_TEMPLE_FRINGE_PAIRS = 2  # mirrored L/R, so 4 puffs total
HAIR_TEMPLE_FRINGE_RADIUS_M = 0.017
HAIR_TEMPLE_FRINGE_DROP_M = 0.030
HAIR_TEMPLE_FRINGE_STRADDLE_M = 0.008  # how far past the window edge the center sits
CHEST_BAND_WHITE_SIZE = Vector((0.07, 0.015, 0.07))
CHEST_BAND_TEAL_SIZE = Vector((0.18, 0.004, 0.012))
CHEST_BAND_FRONT_OFFSET_M = 0.010
CHEST_BAND_TEAL_FRONT_GAP_M = 0.001
# Band follows the measured torso surface instead of floating as a flat slab.
CHEST_BAND_ARC_SEGMENTS = 24
CHEST_BAND_SHELL_DEPTH_M = 0.006
PREVIEW_RENDERS_USE_FREESTYLE = False
CHEST_LOOP_BOTTOM = 1.205
CHEST_LOOP_TEAL_LOW = 1.235
CHEST_LOOP_TEAL_HIGH = 1.250
CHEST_LOOP_TOP = 1.288
STYLE_ID = "avery_chen_toon"

# Cel palette locked to media/avery-flat/ full-body plates (color reference only).
TOON_PALETTE = {
    "skin_base": "#8F5E47",
    "skin_shadow": "#6E4635",
    "hair_black": "#141018",
    "hair_magenta": "#C43B8C",
    "hair_plum_solid": "#6B2D5B",
    "hair_magenta_accent": "#C43B8C",  # alias of hair_magenta; see MATERIAL_TINT note
    "magenta": "#F51496",
    "navy": "#0E274A",
    "navy_deep": "#0A1C35",
    "teal": "#088D94",
    "teal_stripe": "#088D94",
    "electric": "#3A78C9",
    "white": "#F2F0EB",
    "cargo": "#6E7460",
    "cargo_shadow": "#545848",
    "graphite": "#2A2428",
    "ink": "#1A1520",
    "ground": "#E4E6EA",
    "iris": "#3D2418",
    "sclera": "#F3EBE4",
    "lip": "#8B5348",
    "gold": "#C9A227",
}

MATERIAL_TINT = {
    "MAT_PROXY_CHARACTER": ("skin_base", "skin_shadow"),
    "MAT_AVERY_SCLERA": ("sclera", "sclera"),
    "MAT_PROXY_FOCUS": ("iris", "iris"),
    "MAT_AVERY_PUPIL": ("hair_black", "hair_black"),
    "MAT_AVERY_BROW": ("hair_black", "hair_black"),
    "MAT_AVERY_HAIR": ("hair_black", "hair_black"),
    "MAT_AVERY_HAIR_PLUM": ("hair_plum_solid", "hair_plum_solid"),
    "MAT_AVERY_HAIR_MAGENTA": ("hair_magenta_accent", "hair_magenta_accent"),
    "MAT_AVERY_MAGENTA": ("magenta", "magenta"),
    "MAT_AVERY_JACKET": ("navy", "navy_deep"),
    "MAT_AVERY_UTILITY_NAVY": ("navy", "navy_deep"),
    "MAT_AVERY_SHIRT": ("white", "white"),
    "MAT_AVERY_TROUSER": ("navy", "navy_deep"),
    "MAT_AVERY_SOCK": ("navy", "navy_deep"),
    "MAT_AVERY_BELT": ("graphite", "ink"),
    "MAT_AVERY_TEAL": ("teal", "teal"),
    "MAT_AVERY_CYAN": ("electric", "teal"),
    "MAT_AVERY_SHOE": ("white", "navy_deep"),
    "MAT_AVERY_SOLE": ("white", "white"),
    "MAT_AVERY_FRAME": ("graphite", "ink"),
    "MAT_AVERY_LENS": ("white", "white"),
    "MAT_AVERY_BADGE": ("white", "navy_deep"),
    "MAT_AVERY_GUM": ("lip", "skin_shadow"),
    "MAT_AVERY_TONGUE": ("lip", "skin_shadow"),
    "MAT_AVERY_TOOTH": ("white", "white"),
    "MAT_AVERY_TOOTH_ALT": ("white", "white"),
    "MAT_AVERY_MOUTH_CAVITY": ("hair_black", "ink"),
}


def load_v3_builder():
    spec = importlib.util.spec_from_file_location("build_avery_chen", CHEN_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def argv_after_double_dash() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--render-dir", default=str(DEFAULT_RENDER_DIR))
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-renders", action="store_true")
    return parser.parse_args(argv_after_double_dash())


def linear_channel(value: int) -> float:
    c = value / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    value = hex_color.lstrip("#")
    return (
        linear_channel(int(value[0:2], 16)),
        linear_channel(int(value[2:4], 16)),
        linear_channel(int(value[4:6], 16)),
        alpha,
    )


def palette_color(token: str) -> tuple[float, float, float, float]:
    return rgba(TOON_PALETTE[token])


def find_principled(nodes) -> bpy.types.ShaderNode | None:
    for node in nodes:
        if node.bl_idname == "ShaderNodeBsdfPrincipled":
            return node
    return None


def trace_base_color_socket(shader):
    base = shader.inputs.get("Base Color")
    if base is None:
        return None, None
    if base.is_linked:
        return base.links[0].from_socket, base.links[0].from_node
    return None, tuple(base.default_value)


def insert_flat_unlit(
    material: bpy.types.Material,
    base_rgba: tuple[float, float, float, float],
) -> None:
    """Flat illustration fill without lighting (eyes, glasses lenses)."""
    material.use_nodes = True
    tree = material.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = base_rgba
    emission.inputs["Strength"].default_value = 1.0
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    material.diffuse_color = base_rgba


def insert_cel_on_material(
    material: bpy.types.Material,
    base_rgba: tuple[float, float, float, float],
    shadow_rgba: tuple[float, float, float, float],
    *,
    alpha: float = 1.0,
) -> None:
    material.use_nodes = True
    tree = material.node_tree
    nodes = tree.nodes
    links = tree.links
    output = next((n for n in nodes if n.bl_idname == "ShaderNodeOutputMaterial"), None)
    if output is None:
        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (600, 0)

    for node in list(nodes):
        if node != output:
            nodes.remove(node)

    if alpha < 0.99:
        transparent = nodes.new("ShaderNodeBsdfTransparent")
        transparent.location = (120, -120)
        transparent.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        mix = nodes.new("ShaderNodeMixShader")
        mix.location = (480, 40)
        links.new(transparent.outputs["BSDF"], mix.inputs[1])

    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.location = (-120, 80)
    diffuse.inputs["Color"].default_value = base_rgba
    diffuse.inputs["Roughness"].default_value = 1.0

    to_rgb = nodes.new("ShaderNodeShaderToRGB")
    to_rgb.location = (80, 80)

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (280, 80)
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*shadow_rgba[:3], 1.0)
    ramp.color_ramp.elements[1].position = 0.42
    ramp.color_ramp.elements[1].color = (*base_rgba[:3], 1.0)
    if len(ramp.color_ramp.elements) > 2:
        while len(ramp.color_ramp.elements) > 2:
            ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    else:
        highlight = ramp.color_ramp.elements.new(0.78)
        highlight.color = (*base_rgba[:3], 1.0)

    emission = nodes.new("ShaderNodeEmission")
    emission.location = (480, 80)
    emission.inputs["Strength"].default_value = 1.0

    links.new(diffuse.outputs["BSDF"], to_rgb.inputs[0])
    links.new(to_rgb.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], emission.inputs["Color"])

    if alpha < 0.99:
        links.new(emission.outputs["Emission"], mix.inputs[2])
        links.new(mix.outputs["Shader"], output.inputs["Surface"])
        if hasattr(material, "blend_method"):
            material.blend_method = "BLEND"
    else:
        links.new(emission.outputs["Emission"], output.inputs["Surface"])

    material.diffuse_color = (*base_rgba[:3], alpha)


def convert_material_to_cel(material: bpy.types.Material) -> None:
    if not material or material.users == 0:
        return
    name = material.name
    if name.startswith("MAT_AVERY_QA"):
        return
    if name in {
        "MAT_AVERY_SCLERA",
        "MAT_PROXY_FOCUS",
        "MAT_AVERY_PUPIL",
        "MAT_AVERY_FRAME",
        "MAT_AVERY_CHEST_BAND_WHITE",
        "MAT_AVERY_CHEST_BAND_TEAL",
        "MAT_AVERY_MOUTH",
    }:
        return
    tokens = MATERIAL_TINT.get(name)
    if tokens:
        base = palette_color(tokens[0])
        shadow = palette_color(tokens[1])
        alpha = 0.04 if name == "MAT_AVERY_LENS" else 1.0
        insert_cel_on_material(material, base, shadow, alpha=alpha)
        return

    # Fallback: sample existing principled base color before clearing.
    material.use_nodes = True
    principled = find_principled(material.node_tree.nodes)
    if principled is None:
        insert_cel_on_material(material, rgba("#B0B8C0"), rgba("#7A8490"))
        return
    _, default = trace_base_color_socket(principled)
    if default is None:
        default = (0.7, 0.7, 0.7, 1.0)
    shadow = tuple(min(1.0, c * 0.72) for c in default[:3]) + (1.0,)
    insert_cel_on_material(material, default, shadow)


def convert_all_materials_to_cel() -> None:
    for material in list(bpy.data.materials):
        convert_material_to_cel(material)


def remove_toon_helper_objects() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith("GEO_TOON_"):
            bpy.data.objects.remove(obj, do_unlink=True)


def patch_v3_for_toon(v3) -> None:
    """Keep V3 humanoid topology closed; sleeves skinned from body, not tube lofts."""
    v3.soften_armscye_edges = lambda obj: None
    v3.open_jacket_front = lambda obj: None

    def sleeve_mesh_fitted(
        name: str,
        side: str,
        material: bpy.types.Material,
        cuff_material: bpy.types.Material,
        accent_material: bpy.types.Material,
    ) -> list[bpy.types.Object]:
        skin = bpy.data.objects["GEO_AVERY_BODY"]
        legacy = bpy.data.objects.get(name)
        if legacy:
            bpy.data.objects.remove(legacy, do_unlink=True)
        sleeve = v3.fitted_sleeve_from_skin(skin, side, material)
        sleeve.name = name
        cuff = v3.add_rolled_cuff(side, cuff_material, accent_material)
        return [sleeve, cuff]

    v3.sleeve_mesh = lambda *args, **kwargs: []
    v3.raglan_shoulder = lambda *args, **kwargs: None
    _orig_make_loft = v3.make_loft

    def make_loft_skip_shirt(name: str, *args, **kwargs):
        if name == "GEO_AVERY_SHIRT":
            return None
        return _orig_make_loft(name, *args, **kwargs)

    v3.make_loft = make_loft_skip_shirt

    def fitted_sleeve_wider(
        skin: bpy.types.Object,
        side: str,
        material: bpy.types.Material,
    ) -> bpy.types.Object:
        sign = -1.0 if side == "L" else 1.0
        chosen = []
        for polygon in skin.data.polygons:
            center = sum(
                (skin.data.vertices[i].co for i in polygon.vertices), Vector()
            ) / len(polygon.vertices)
            if (
                1.05 < center.z < 1.48
                and center.x * sign > 0.12
                and abs(center.x) > 0.12
            ):
                chosen.append(polygon)
        source_ids = sorted({index for polygon in chosen for index in polygon.vertices})
        remap = {source: target for target, source in enumerate(source_ids)}
        vertices = [
            skin.data.vertices[index].co
            + skin.data.vertices[index].normal.normalized() * 0.016
            for index in source_ids
        ]
        faces = [
            tuple(remap[index] for index in polygon.vertices) for polygon in chosen
        ]
        sleeve = v3.mesh_object(
            f"GEO_AVERY_SLEEVE_{side}", vertices, faces, [material]
        )
        source_group_names = {
            group.index: group.name
            for group in skin.vertex_groups
            if group.name in v3.BONE_PARENTS
        }
        destination_groups = {
            name: sleeve.vertex_groups.new(name=name)
            for name in sorted(set(source_group_names.values()))
        }
        for new_index, source_index in enumerate(source_ids):
            assigned = False
            for assignment in skin.data.vertices[source_index].groups:
                name = source_group_names.get(assignment.group)
                if name and assignment.weight > 0.0001:
                    destination_groups[name].add(
                        [new_index], assignment.weight, "REPLACE"
                    )
                    assigned = True
            if not assigned:
                destination_groups[f"upper_arm.{side}"].add(
                    [new_index], 1.0, "REPLACE"
                )
        solidify = sleeve.modifiers.new("Cloth thickness", "SOLIDIFY")
        solidify.thickness = 0.0045
        solidify.offset = 1.0
        v3.apply_modifier(sleeve, solidify.name)
        sleeve.parent = bpy.data.objects[v3.ARMATURE]
        armature = sleeve.modifiers.new("Armature", "ARMATURE")
        armature.object = bpy.data.objects[v3.ARMATURE]
        for polygon in sleeve.data.polygons:
            polygon.use_smooth = True
        return sleeve

    v3.fitted_sleeve_from_skin = fitted_sleeve_wider


SCRAP_OBJECTS = {
    "GEO_AVERY_LENSES",
    "GEO_AVERY_CORNEAS",
    "GEO_AVERY_BELT_KEEPER",
    "GEO_AVERY_ROLLED_CUFF_L",
    "GEO_AVERY_ROLLED_CUFF_R",
}


def restore_v3_humanoid(v3) -> None:
    """Show the rigged V3 humanoid; hide only tiny scrap cards."""
    coll = v3.collection()
    for obj in list(coll.objects):
        if obj.name in SCRAP_OBJECTS:
            obj.hide_render = True
            obj.hide_viewport = True
        elif obj.name.startswith("GEO_AVERY") or obj.type == "ARMATURE":
            obj.hide_render = False
            obj.hide_viewport = False
    for obj in list(bpy.data.objects):
        if obj.type == "CURVE" and obj.name.startswith("GEO_AVERY"):
            obj.hide_render = False
            obj.hide_viewport = False


def fix_shirt_materials() -> None:
    shirt = bpy.data.materials.get("MAT_AVERY_SHIRT")
    teal = bpy.data.materials.get("MAT_AVERY_TEAL")
    if shirt:
        insert_flat_unlit(shirt, palette_color("white"))
    if teal:
        insert_flat_unlit(teal, palette_color("teal"))


def fix_chest_band_materials(v3) -> None:
    white = bpy.data.materials.get("MAT_AVERY_CHEST_BAND_WHITE")
    teal = bpy.data.materials.get("MAT_AVERY_CHEST_BAND_TEAL")
    if white is None:
        white = v3.basic_material(
            "MAT_AVERY_CHEST_BAND_WHITE", TOON_PALETTE["white"], 1.0
        )
    if teal is None:
        teal = v3.basic_material(
            "MAT_AVERY_CHEST_BAND_TEAL", TOON_PALETTE["teal_stripe"], 1.0
        )
    insert_flat_unlit(white, palette_color("white"))
    insert_flat_unlit(teal, palette_color("teal_stripe"))
    for material in (white, teal):
        material.use_backface_culling = False
        for node in material.node_tree.nodes:
            if node.bl_idname == "ShaderNodeEmission":
                node.inputs["Strength"].default_value = 1.0


def fix_hair_materials() -> None:
    plum = bpy.data.materials.get("MAT_AVERY_HAIR_PLUM")
    if plum:
        insert_flat_unlit(plum, palette_color("hair_plum_solid"))
        plum.use_backface_culling = False
    magenta = bpy.data.materials.get("MAT_AVERY_HAIR_MAGENTA")
    if magenta:
        insert_flat_unlit(magenta, palette_color("hair_magenta_accent"))
        magenta.use_backface_culling = False
    hair = bpy.data.objects.get("GEO_AVERY_HAIR")
    if hair:
        configure_hair_render_flags(hair)


# Micro-geometry (eyes/iris/pupil/brows) was built against sub-millimeter
# clearance off the head surface (make_iris_mesh's dome bias is 0.00065 m,
# docs/avery-chen/build_avery_chen.py:681). The toon pipeline adds steps the
# base V3 pipeline doesn't run (armature-modifier re-attach, EEVEE instead of
# whatever engine produced the verified-good internal/v3-face-qa.md render) --
# any of those can erode that margin and let the opaque head swallow these
# objects with no error raised anywhere (neither verify_front_render nor
# verify_expression_eyes checks for eye color at all -- see
# internal/fix-face-features-proposal.md evidence #9). This nudges them a
# conservative, fixed amount toward the camera so marginal occlusion clears,
# and logs each object's evaluated world bounds so a still-blank face after
# this change points at the real cause instead of another guess.
FACE_DECAL_OBJECTS = (
    "GEO_AVERY_EYES",
    "GEO_AVERY_IRISES",
    "GEO_AVERY_PUPILS",
    "GEO_AVERY_BROWS",
)
FACE_DECAL_NUDGE_M = 0.0015


def _nudge_face_decal_forward(obj: bpy.types.Object) -> None:
    """Idempotent: guarded by a custom property so the three fix_facial_materials()
    calls in one pipeline run don't compound the offset. Shifts every shape-key
    block (not just Basis) so LOOK_LEFT/RIGHT, BROW_UP/DOWN etc. keep their
    deltas relative to the nudged rest position instead of drifting back."""
    if obj.get("AVERY_TOON_FACE_NUDGED"):
        return
    keys = obj.data.shape_keys
    if keys:
        for block in keys.key_blocks:
            for point in block.data:
                point.co.y -= FACE_DECAL_NUDGE_M
    else:
        for vertex in obj.data.vertices:
            vertex.co.y -= FACE_DECAL_NUDGE_M
    obj.data.update()
    obj["AVERY_TOON_FACE_NUDGED"] = True


def _log_face_depth_diagnostics() -> None:
    deps = bpy.context.evaluated_depsgraph_get()
    for name in (*FACE_DECAL_OBJECTS, "GEO_AVERY_HEAD"):
        obj = bpy.data.objects.get(name)
        if not obj:
            print(f"face-diag {name}: MISSING")
            continue
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        if not mesh.vertices:
            print(f"face-diag {name}: 0 evaluated verts")
            evaluated.to_mesh_clear()
            continue
        ys = [(obj.matrix_world @ v.co).y for v in mesh.vertices]
        print(
            f"face-diag {name}: hide_render={obj.hide_render} "
            f"scale={tuple(round(c, 3) for c in obj.scale)} "
            f"y=({min(ys):.4f},{max(ys):.4f}) n={len(ys)}"
        )
        evaluated.to_mesh_clear()


def fix_facial_materials() -> None:
    insert_flat_unlit(bpy.data.materials["MAT_AVERY_SCLERA"], palette_color("sclera"))
    insert_flat_unlit(bpy.data.materials["MAT_PROXY_FOCUS"], palette_color("iris"))
    insert_flat_unlit(bpy.data.materials["MAT_AVERY_PUPIL"], palette_color("hair_black"))
    insert_flat_unlit(bpy.data.materials["MAT_AVERY_FRAME"], palette_color("graphite"))
    if bpy.data.materials.get("MAT_AVERY_MOUTH"):
        insert_flat_unlit(bpy.data.materials["MAT_AVERY_MOUTH"], palette_color("lip"))
    for obj_name in (
        "GEO_AVERY_EYES",
        "GEO_AVERY_IRISES",
        "GEO_AVERY_PUPILS",
        "GEO_AVERY_GLASSES",
        "GEO_AVERY_BROWS",
        "GEO_AVERY_MOUTH",
    ):
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.hide_render = False
            obj.hide_viewport = False
            obj.scale = (1.0, 1.0, 1.0)
            if obj_name in FACE_DECAL_OBJECTS:
                _nudge_face_decal_forward(obj)
    _log_face_depth_diagnostics()


def _edge_center(edge: bmesh.types.BMEdge) -> Vector:
    return (edge.verts[0].co + edge.verts[1].co) * 0.5


def open_jacket_front_on_shell(obj: bpy.types.Object) -> None:
    """Small front opening on the outer shell only (tee + teal band stay visible)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    delete_faces = []
    for face in bm.faces:
        center = face.calc_center_median()
        if (
            center.y < -0.058
            and abs(center.x) < 0.034
            and 1.05 < center.z < 1.32
        ):
            delete_faces.append(face)
    if delete_faces:
        bmesh.ops.delete(bm, geom=delete_faces, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def apply_solidify_shell(obj: bpy.types.Object, thickness: float, v3) -> None:
    had_armature = obj.modifiers.get("Armature") is not None
    if had_armature:
        obj.modifiers.remove(obj.modifiers["Armature"])
    for modifier in list(obj.modifiers):
        if modifier.type == "SOLIDIFY":
            obj.modifiers.remove(modifier)
    solidify = obj.modifiers.new("JacketShell", "SOLIDIFY")
    solidify.thickness = thickness
    solidify.offset = 1.0
    solidify.use_rim = True
    v3.set_active(obj)
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    if had_armature:
        ensure_armature_deform(v3, obj)


def ensure_shirt_stripe(v3) -> None:
    coll = v3.collection()
    legacy = bpy.data.objects.get("GEO_AVERY_SHIRT_STRIPE")
    if legacy:
        bpy.data.objects.remove(legacy, do_unlink=True)
    teal = bpy.data.materials["MAT_AVERY_TEAL"]
    stripe = v3.ribbon_mesh(
        "GEO_AVERY_SHIRT_STRIPE",
        [
            Vector((-0.095, -0.068, 1.198)),
            Vector((0.095, -0.068, 1.198)),
        ],
        0.088,
        0.0022,
        teal,
        "chest",
    )
    v3.link_only(stripe, coll)


def _polygon_center(obj: bpy.types.Object, polygon: bpy.types.MeshPolygon) -> Vector:
    return sum((obj.data.vertices[i].co for i in polygon.vertices), Vector()) / len(
        polygon.vertices
    )


def remove_legacy_jacket_shells() -> None:
    for legacy in (
        "GEO_AVERY_JKT_SHELL",
        "GEO_AVERY_JKT_OUTER_SHELL",
        "GEO_AVERY_HAIR_UPDOCAP",
        "GEO_AVERY_FOREARM_L",
        "GEO_AVERY_FOREARM_R",
    ):
        old = bpy.data.objects.get(legacy)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)


def _forearm_face(obj: bpy.types.Object, face: bmesh.types.BMFace, side: str) -> bool:
    sign = -1.0 if side == "L" else 1.0
    center = face.calc_center_median()
    return (
        1.02 < center.z < 1.36
        and center.x * sign > 0.11
        and center.y > -0.18
    )


def extract_forearm_skin(v3, body: bpy.types.Object) -> None:
    skin = bpy.data.materials["MAT_PROXY_CHARACTER"]
    for side in ("L", "R"):
        bm = bmesh.new()
        bm.from_mesh(body.data)
        bm.faces.ensure_lookup_table()
        remove = [face for face in bm.faces if not _forearm_face(body, face, side)]
        if remove:
            bmesh.ops.delete(bm, geom=remove, context="FACES")
        if not bm.faces:
            bm.free()
            continue
        source_indices = [vertex.index for vertex in bm.verts]
        mesh = bpy.data.meshes.new(f"GEO_AVERY_FOREARM_{side}")
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        forearm = bpy.data.objects.new(f"GEO_AVERY_FOREARM_{side}", mesh)
        v3.collection().objects.link(forearm)
        v3.assign_material(forearm, skin)
        for group in body.vertex_groups:
            forearm.vertex_groups.new(name=group.name)
        for new_index, source_index in enumerate(source_indices):
            for assignment in body.data.vertices[source_index].groups:
                name = body.vertex_groups[assignment.group].name
                forearm.vertex_groups[name].add(
                    [new_index], assignment.weight, "REPLACE"
                )
        ensure_armature_deform(v3, forearm)


def build_jacket_outer_shell(v3, body: bpy.types.Object) -> bpy.types.Object:
    for legacy in ("GEO_AVERY_JKT_SHELL", "GEO_AVERY_JKT_OUTER_SHELL"):
        old = bpy.data.objects.get(legacy)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
    jacket = bpy.data.materials["MAT_AVERY_JACKET"]
    shell = body.copy()
    shell.data = body.data.copy()
    shell.name = "GEO_AVERY_JKT_SHELL"
    v3.collection().objects.link(shell)
    v3.assign_material(shell, jacket)
    apply_solidify_shell(shell, 0.012, v3)
    open_jacket_front_on_shell(shell)
    ensure_armature_deform(v3, shell)
    return shell


def ensure_armature_deform(v3, obj: bpy.types.Object) -> None:
    rig = bpy.data.objects.get(v3.ARMATURE)
    if not rig or obj.type != "MESH":
        return
    modifier = obj.modifiers.get("Armature")
    if modifier is None:
        modifier = obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = rig


REMOVE_CLOTHING_PREFIXES = (
    "GEO_AVERY_JKT_",
    "GEO_AVERY_SHIRT",
)
REMOVE_CLOTHING_EXACT = (
    "GEO_AVERY_SLEEVE_L",
    "GEO_AVERY_SLEEVE_R",
    "GEO_AVERY_RAGLAN_L",
    "GEO_AVERY_RAGLAN_R",
    "GEO_AVERY_SHIRT",
    "GEO_AVERY_SHIRT_STRIPE",
    "GEO_AVERY_HAIR_COILS",
    "GEO_AVERY_SCALP_BRAIDS",
    "GEO_AVERY_JKT_SHELL",
    "GEO_AVERY_JKT_OUTER_SHELL",
    "GEO_AVERY_SKIN_ARM_L",
    "GEO_AVERY_SKIN_ARM_R",
    "GEO_AVERY_ROLLED_CUFF_L",
    "GEO_AVERY_ROLLED_CUFF_R",
)


def delete_clothing_meshes() -> None:
    for obj in list(bpy.data.objects):
        if obj.name in REMOVE_CLOTHING_EXACT or any(
            obj.name.startswith(prefix) for prefix in REMOVE_CLOTHING_PREFIXES
        ):
            bpy.data.objects.remove(obj, do_unlink=True)
        elif obj.name.startswith("GEO_AVERY_HAIR") and obj.name != "GEO_AVERY_HAIR":
            bpy.data.objects.remove(obj, do_unlink=True)


def _material_or_basic(
    v3, name: str, token: str
) -> bpy.types.Material:
    material = bpy.data.materials.get(name)
    if material is None:
        material = v3.basic_material(name, TOON_PALETTE[token], 1.0)
    return material


def ensure_toon_paint_materials(v3) -> dict[str, bpy.types.Material]:
    skin = bpy.data.materials["MAT_PROXY_CHARACTER"]
    navy = _material_or_basic(v3, "MAT_AVERY_JACKET", "navy")
    white = _material_or_basic(v3, "MAT_AVERY_SHIRT", "white")
    teal = _material_or_basic(v3, "MAT_AVERY_TEAL", "teal")
    hair_plum = _material_or_basic(v3, "MAT_AVERY_HAIR_PLUM", "hair_plum_solid")
    hair_magenta = _material_or_basic(
        v3, "MAT_AVERY_HAIR_MAGENTA", "hair_magenta_accent"
    )
    hair_black = _material_or_basic(v3, "MAT_AVERY_HAIR", "hair_black")
    for material, token in (
        (navy, "navy"),
        (white, "white"),
        (teal, "teal"),
        (hair_plum, "hair_plum_solid"),
        (hair_magenta, "hair_magenta_accent"),
        (hair_black, "hair_black"),
    ):
        material.diffuse_color = rgba(TOON_PALETTE[token])
    return {
        "skin": skin,
        "navy": navy,
        "white": white,
        "teal": teal,
        "hair_plum": hair_plum,
        "hair_magenta": hair_magenta,
        "hair_black": hair_black,
    }


def build_mouth_decal(v3) -> bpy.types.Object | None:
    """Flat mouth mark. The base V3 head sculpts a closed lip silhouette and
    paints a lip tone into a per-vertex color attribute (paint_skin,
    docs/avery-chen/build_avery_chen.py:611-664), but the toon cel pass
    overwrites the whole head material with one flat color and never reads
    that attribute (insert_cel_on_material) -- so at rest the mouth reads as
    blank skin. This adds a small, legible flat mouth shape, same pattern as
    GEO_AVERY_IRISES/GEO_AVERY_PUPILS."""
    existing = bpy.data.objects.get("GEO_AVERY_MOUTH")
    if existing:
        return existing
    mat = bpy.data.materials.get("MAT_AVERY_MOUTH")
    if mat is None:
        mat = v3.basic_material("MAT_AVERY_MOUTH", TOON_PALETTE["lip"], 1.0)
    insert_flat_unlit(mat, palette_color("lip"))

    half_width = 0.016
    corner_rise = 0.0017  # corners lift slightly: a small smile, not neutral
    thickness = 0.0022
    z_center = 1.5245  # mid lip band, per sculpt_integrated_face's lip z-range fallback
    y = -0.1247  # just proud of the iris/cornea plane (-0.1214 to -0.12305)

    segments = 9
    top: list[Vector] = []
    bottom: list[Vector] = []
    for index in range(segments):
        t = index / (segments - 1)
        x = -half_width + 2.0 * half_width * t
        arch = math.sin(math.pi * t)
        z = z_center + corner_rise * (1.0 - arch)
        top.append(Vector((x, y, z + thickness * 0.5)))
        bottom.append(Vector((x, y, z - thickness * 0.5)))
    vertices = top + bottom
    faces = []
    for index in range(segments - 1):
        a, b = index, index + 1
        c, d = segments + index + 1, segments + index
        faces.append((a, b, c, d))

    mouth = v3.mesh_object("GEO_AVERY_MOUTH", vertices, faces, [mat])
    for polygon in mouth.data.polygons:
        polygon.use_smooth = True
    v3.parent_bone(mouth, "head")
    mouth.hide_render = False
    mouth.hide_viewport = False
    return mouth


def _assign_wardrobe_slots(obj: bpy.types.Object, materials: dict[str, bpy.types.Material]) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(materials["skin"])
    obj.data.materials.append(materials["navy"])
    obj.data.materials.append(materials["white"])
    obj.data.materials.append(materials["teal"])


CHEST_TEAL_Z = (1.188, 1.206)
CHEST_WHITE_Z = (1.122, 1.288)
NECK_SKIN_Z = (1.288, 1.50)


def _polygon_center(obj: bpy.types.Object, polygon: bpy.types.MeshPolygon) -> Vector:
    center = Vector((0.0, 0.0, 0.0))
    for index in polygon.vertices:
        center += obj.data.vertices[index].co
    return center / len(polygon.vertices)


def _front_torso_material(center: Vector) -> int | None:
    """Chest band zone is navy on body (GEO_AVERY_CHEST_BAND carries white/teal)."""
    if center.y >= -0.032 or abs(center.x) >= 0.142:
        return None
    if center.z > 1.35:
        return None
    if CHEST_LOOP_BOTTOM <= center.z <= CHEST_LOOP_TOP:
        return 1
    if 1.275 < center.z <= 1.325 and abs(center.x) < 0.14:
        return 1
    if 1.288 < center.z <= 1.32 and abs(center.x) < 0.12:
        return 1
    if 1.32 < center.z <= 1.44 and abs(center.x) < 0.13:
        return 0
    if center.z >= 0.978:
        return 1
    return None


def _classify_wardrobe_point(
    co: Vector,
    *,
    preserve_face_skin: bool,
) -> int:
    """Flat horizontal chest bands (world Z), skin neck/hands/face."""
    if preserve_face_skin and co.z > 1.52 and abs(co.x) < 0.13 and co.y < -0.068:
        return 0
    if preserve_face_skin and 1.26 < co.z < 1.62 and abs(co.x) < 0.12 and co.y < 0.05:
        return 0
    if co.z < 0.992 and abs(co.x) > 0.158:
        return 0
    front = _front_torso_material(co)
    if front is not None:
        return front
    if co.z >= 0.978:
        return 1
    return 0


def _face_material_from_vertices(
    obj: bpy.types.Object,
    polygon: bpy.types.MeshPolygon,
    vert_material: list[int],
) -> int:
    center = _polygon_center(obj, polygon)
    if (
        center.y < -0.02
        and abs(center.x) < 0.15
        and 1.05 <= center.z <= 1.38
    ):
        front = _front_torso_material(center)
        if front is not None:
            return front
        if center.z <= 1.32:
            return 1
    zones = [vert_material[i] for i in polygon.vertices]
    if 1 in zones:
        return 1
    return zones[0]


def _subdivide_front_chest(obj: bpy.types.Object) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    tagged: set[bmesh.types.BMEdge] = set()
    for face in bm.faces:
        center = face.calc_center_median()
        if (
            center.y < -0.02
            and abs(center.x) < 0.14
            and 1.10 < center.z < 1.36
        ):
            tagged.update(face.edges)
    if tagged:
        bmesh.ops.subdivide_edges(bm, edges=list(tagged), cuts=1)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def _cut_chest_band_loops(obj: bpy.types.Object) -> None:
    """Horizontal edge loops at band boundaries (level white + teal stripes)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    for z_cut in (
        CHEST_LOOP_BOTTOM,
        CHEST_LOOP_TEAL_LOW,
        CHEST_LOOP_TEAL_HIGH,
        CHEST_LOOP_TOP,
    ):
        bmesh.ops.bisect_plane(
            bm,
            geom=geom,
            dist=0.00015,
            plane_co=(0.0, 0.0, z_cut),
            plane_no=(0.0, 0.0, 1.0),
            clear_outer=False,
            clear_inner=False,
        )
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0008)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def _front_chest_band_polygon(obj: bpy.types.Object, center: Vector) -> bool:
    return center.y < -0.03 and abs(center.x) < 0.145 and CHEST_LOOP_BOTTOM <= center.z <= CHEST_LOOP_TOP


def _chest_band_material_from_z(z: float) -> int:
    if CHEST_LOOP_TEAL_LOW <= z <= CHEST_LOOP_TEAL_HIGH:
        return 3
    if CHEST_LOOP_BOTTOM <= z <= CHEST_LOOP_TOP:
        return 2
    return 1


def _paint_chest_bands_from_loops(obj: bpy.types.Object) -> None:
    """Assign white/teal by face height between bisect loops (not per-vertex)."""
    for polygon in obj.data.polygons:
        center = _polygon_center(obj, polygon)
        if not _front_chest_band_polygon(obj, center):
            continue
        polygon.material_index = _chest_band_material_from_z(center.z)
    obj.data.update()


def paint_mesh_wardrobe(
    obj: bpy.types.Object,
    materials: dict[str, bpy.types.Material],
    *,
    preserve_face_skin: bool = False,
) -> None:
    _assign_wardrobe_slots(obj, materials)
    vert_material = [
        _classify_wardrobe_point(
            obj.data.vertices[i].co, preserve_face_skin=preserve_face_skin
        )
        for i in range(len(obj.data.vertices))
    ]
    for polygon in obj.data.polygons:
        center = _polygon_center(obj, polygon)
        if obj.name == "GEO_AVERY_BODY" and _front_chest_band_polygon(obj, center):
            polygon.material_index = 1
        else:
            polygon.material_index = _face_material_from_vertices(
                obj, polygon, vert_material
            )
        polygon.use_smooth = True
    obj.data.update()
    if obj.name == "GEO_AVERY_BODY":
        _paint_body_chest_band_navy(obj)


def _fill_navy_above_chest_band(obj: bpy.types.Object) -> None:
    """Paint jagged skin tris directly above the white band navy."""
    for polygon in obj.data.polygons:
        center = _polygon_center(obj, polygon)
        if (
            center.y < -0.02
            and abs(center.x) < 0.15
            and 1.275 < center.z < 1.345
            and polygon.material_index == 0
        ):
            polygon.material_index = 1
    obj.data.update()


def _paint_body_chest_band_navy(obj: bpy.types.Object) -> None:
    """Body shirt under the band mesh: solid navy (no painted white/teal holes)."""
    for polygon in obj.data.polygons:
        if polygon.material_index in (2, 3):
            polygon.material_index = 1
        center = _polygon_center(obj, polygon)
        if _front_chest_band_polygon(obj, center):
            polygon.material_index = 1
        elif (
            center.y < -0.03
            and abs(center.x) < 0.145
            and CHEST_LOOP_TOP < center.z < 1.365
            and polygon.material_index in (0, 2, 3)
        ):
            polygon.material_index = 1
    obj.data.update()


def _heal_chest_bands(obj: bpy.types.Object) -> None:
    _paint_body_chest_band_navy(obj)


def _flat_chest_materials() -> None:
    white = bpy.data.materials.get("MAT_AVERY_SHIRT")
    teal = bpy.data.materials.get("MAT_AVERY_TEAL")
    if white:
        insert_flat_unlit(white, palette_color("white"))
    if teal:
        insert_flat_unlit(teal, palette_color("teal_stripe"))


def fix_ankle_leg_materials(v3) -> None:
    """Hide sock/teal/magenta/piping clutter; trousers meet shoes cleanly."""
    cargo_mat = bpy.data.materials.get("MAT_AVERY_TROUSER") or bpy.data.materials.get(
        "MAT_AVERY_SOCK"
    )
    if cargo_mat:
        insert_cel_on_material(
            cargo_mat,
            palette_color("navy"),
            palette_color("navy_deep"),
        )
    hide_patterns = (
        "GEO_AVERY_SOCK",
        "GEO_AVERY_SHOE_PIPING",
        "GEO_AVERY_TROUSER_CUFF",
        "GEO_AVERY_HEEL_TAB",
    )
    for obj in list(bpy.data.objects):
        if any(obj.name.startswith(prefix) for prefix in hide_patterns):
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        if obj.name.startswith("GEO_AVERY_TROUSERS") and cargo_mat:
            while len(obj.data.materials) > 1:
                obj.data.materials.pop(index=1)
            obj.data.materials[0] = cargo_mat
            for polygon in obj.data.polygons:
                polygon.material_index = 0
            obj.data.update()
    shoes = bpy.data.objects.get("GEO_AVERY_SHOES")
    cargo = cargo_mat
    if shoes and cargo:
        if cargo.name not in [m.name for m in shoes.data.materials if m]:
            shoes.data.materials.append(cargo)
        cargo_index = next(
            i for i, m in enumerate(shoes.data.materials) if m and m.name == cargo.name
        )
        for polygon in shoes.data.polygons:
            center = _polygon_center(shoes, polygon)
            if center.z >= 0.028 and abs(center.x) < 0.22:
                polygon.material_index = cargo_index
        shoes.data.update()
    body = bpy.data.objects.get("GEO_AVERY_BODY")
    if body:
        for polygon in body.data.polygons:
            center = _polygon_center(body, polygon)
            if center.z < 0.19 and abs(center.x) < 0.16 and polygon.material_index in (
                2,
                3,
            ):
                polygon.material_index = 0
        body.data.update()


def paint_body_wardrobe(materials: dict[str, bpy.types.Material]) -> None:
    """Assign wardrobe on skinned body meshes (no extra clothing objects)."""
    body = bpy.data.objects.get("GEO_AVERY_BODY")
    head = bpy.data.objects.get("GEO_AVERY_HEAD")
    if body:
        paint_mesh_wardrobe(body, materials, preserve_face_skin=False)
        _fill_navy_above_chest_band(body)
        _heal_chest_bands(body)
    if head:
        paint_mesh_wardrobe(head, materials, preserve_face_skin=True)
        _fill_navy_above_chest_band(head)
        _heal_chest_bands(head)


def prepare_visible_body(v3, body: bpy.types.Object) -> None:
    body.hide_render = False
    body.hide_viewport = False
    ensure_armature_deform(v3, body)



def _shoulder_width(body: bpy.types.Object | None) -> float:
    if body is None:
        return 0.52
    xs = [
        v.co.x
        for v in body.data.vertices
        if 1.18 <= v.co.z <= 1.34 and v.co.y < -0.02
    ]
    if len(xs) < 8:
        xs = [v.co.x for v in body.data.vertices if 1.0 <= v.co.z <= 1.4]
    return max(xs) - min(xs) if xs else 0.52


def _evaluated_world_bounds(
    obj: bpy.types.Object,
) -> tuple[Vector, Vector, Vector]:
    """Axis-aligned world bounds of an object mesh after modifiers."""
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    try:
        matrix = evaluated.matrix_world
        if not mesh.vertices:
            raise RuntimeError(f"{obj.name} has no vertices for bounds")
        world = [matrix @ vertex.co for vertex in mesh.vertices]
        xs = [point.x for point in world]
        ys = [point.y for point in world]
        zs = [point.z for point in world]
        head_min = Vector((min(xs), min(ys), min(zs)))
        head_max = Vector((max(xs), max(ys), max(zs)))
        center = (head_min + head_max) * 0.5
        return head_min, head_max, center
    finally:
        evaluated.to_mesh_clear()


def _aabb_intersects(min_a: Vector, max_a: Vector, min_b: Vector, max_b: Vector) -> bool:
    return (
        min_a.x <= max_b.x
        and max_a.x >= min_b.x
        and min_a.y <= max_b.y
        and max_a.y >= min_b.y
        and min_a.z <= max_b.z
        and max_a.z >= min_b.z
    )


def _head_bone_world_location(v3) -> Vector:
    rig = bpy.data.objects[v3.ARMATURE]
    pose_bone = rig.pose.bones["head"]
    return rig.matrix_world @ pose_bone.head


def purge_plate_hair_assets() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith("GEO_AVERY_HAIR"):
            bpy.data.objects.remove(obj, do_unlink=True)
    plate_mat = bpy.data.materials.get("MAT_AVERY_HAIR_PLATE")
    if plate_mat:
        bpy.data.materials.remove(plate_mat, do_unlink=True)
    for image in list(bpy.data.images):
        label = (image.name + " " + (image.filepath or "")).lower()
        if "avery_hair" in label or "hair_plate" in label:
            bpy.data.images.remove(image, do_unlink=True)


def _head_scalp_top_z(v3) -> float:
    """Highest world Z on head/crown skin (stable after head face culling)."""
    samples: list[float] = []
    for name in ("GEO_AVERY_HEAD", "GEO_AVERY_BODY"):
        mesh_obj = bpy.data.objects.get(name)
        if mesh_obj is None:
            continue
        matrix = mesh_obj.matrix_world
        for vertex in mesh_obj.data.vertices:
            world = matrix @ vertex.co
            if world.z > 1.52 and abs(world.x) < 0.12 and world.y < 0.06:
                samples.append(world.z)
    if samples:
        return max(samples)
    head = bpy.data.objects.get("GEO_AVERY_HEAD")
    if head and head.data.vertices:
        return max((head.matrix_world @ vertex.co).z for vertex in head.data.vertices)
    return _head_bone_world_location(v3).z + 0.17


def _scalp_reference_z(v3) -> float:
    return _head_scalp_top_z(v3)


def _head_world_metrics(v3) -> tuple[float, float, float]:
    """(scalp_top_z, head_half_width_x, head_center_y) for sizing the afro."""
    scalp_top = _head_scalp_top_z(v3)
    bone_loc = _head_bone_world_location(v3)
    xs: list[float] = []
    ys: list[float] = []
    head = bpy.data.objects.get("GEO_AVERY_HEAD")
    if head is not None:
        matrix = head.matrix_world
        for vertex in head.data.vertices:
            world = matrix @ vertex.co
            if world.z > bone_loc.z + 0.02:
                xs.append(abs(world.x))
                ys.append(world.y)
    half_width = max(xs) if xs else 0.082
    center_y = (min(ys) + max(ys)) * 0.5 if ys else bone_loc.y
    return scalp_top, half_width, center_y


def _bmesh_face_islands(bm: bmesh.types.BMesh) -> list[list[bmesh.types.BMFace]]:
    visited: set[int] = set()
    islands: list[list[bmesh.types.BMFace]] = []
    for face in bm.faces:
        if face.index in visited:
            continue
        stack = [face]
        component: list[bmesh.types.BMFace] = []
        while stack:
            current = stack.pop()
            if current.index in visited:
                continue
            visited.add(current.index)
            component.append(current)
            for edge in current.edges:
                for linked in edge.link_faces:
                    if linked.index not in visited:
                        stack.append(linked)
        islands.append(component)
    return islands


def _curl_noise_offset(unit_co: Vector, seed_offset: float) -> float:
    """Deterministic pseudo-noise over spherical angle: a few sine harmonics,
    offset per call so cap and puffs don't ripple in lockstep."""
    theta = math.atan2(unit_co.y, unit_co.x)
    phi = math.acos(max(-1.0, min(1.0, unit_co.z)))
    return (
        0.5 * math.sin(5.0 * theta + seed_offset)
        + 0.3 * math.sin(9.0 * theta - 2.0 * phi + seed_offset * 1.7)
        + 0.2 * math.sin(13.0 * phi + 4.0 * theta + seed_offset * 2.3)
    )


def _append_ellipsoid_to_bm(
    bm: bmesh.types.BMesh,
    center: Vector,
    radius_x: float,
    radius_y: float,
    radius_z: float,
    segments: int,
    *,
    noise_amplitude_m: float = 0.0,
    noise_seed: float = 0.0,
) -> list[bmesh.types.BMFace]:
    """Build a small UV sphere, optionally perturb it with curl noise, scale
    it to an ellipsoid, offset it to `center`, and merge it into `bm`.
    Returns the newly added faces so the caller can tag material/region.
    """
    sub = bmesh.new()
    bmesh.ops.create_uvsphere(
        sub, u_segments=segments, v_segments=max(segments // 2, 4), radius=1.0
    )
    max_radius = max(radius_x, radius_y, radius_z, 1e-6)
    for vert in sub.verts:
        if noise_amplitude_m:
            bump = _curl_noise_offset(vert.co, noise_seed) * (
                noise_amplitude_m / max_radius
            )
            vert.co *= 1.0 + bump
        vert.co.x = vert.co.x * radius_x + center.x
        vert.co.y = vert.co.y * radius_y + center.y
        vert.co.z = vert.co.z * radius_z + center.z
    tmp_mesh = bpy.data.meshes.new("GEO_AVERY_HAIR_PUFF_TMP")
    sub.to_mesh(tmp_mesh)
    sub.free()
    start = len(bm.faces)
    bm.from_mesh(tmp_mesh)
    bpy.data.meshes.remove(tmp_mesh)
    bm.faces.ensure_lookup_table()
    return list(bm.faces)[start:]


def _afro_puff_plan(
    rng: random.Random,
    radius_x: float,
    radius_y: float,
    radius_z: float,
    count: int,
) -> list[tuple[Vector, float, bool]]:
    """Deterministic puff centers/radii/material-flag, biased to the upper
    hemisphere (crown/sides/back) so puffs read as curl clumps, not random
    face coverage. `bool` is True for a magenta streak clump."""
    plan = []
    for _ in range(count):
        phi = math.radians(rng.uniform(AFRO_PUFF_MIN_PHI_DEG, AFRO_PUFF_MAX_PHI_DEG))
        theta = rng.uniform(0.0, math.tau)
        unit = Vector(
            (math.sin(phi) * math.cos(theta), math.sin(phi) * math.sin(theta), math.cos(phi))
        )
        surface = Vector((unit.x * radius_x, unit.y * radius_y, unit.z * radius_z))
        local_radius = max(surface.length, 1e-6)
        puff_radius = max(
            local_radius
            * AFRO_PUFF_RADIUS_RATIO
            * rng.uniform(1.0 - AFRO_PUFF_RADIUS_JITTER, 1.0 + AFRO_PUFF_RADIUS_JITTER),
            AFRO_MIN_RADIUS_M * 0.15,
        )
        inward = surface.normalized() * -1.0
        center = surface + inward * (puff_radius * AFRO_PUFF_OVERLAP_RATIO)
        is_streak = rng.random() < AFRO_STREAK_PUFF_FRACTION
        plan.append((center, puff_radius, is_streak))
    return plan


def _hair_islands_overlap_cluster(
    bm: bmesh.types.BMesh, matrix: Matrix, pad: float = 0.004
) -> bool:
    """True when every island's bounding box overlaps at least one other
    island's, so the whole mesh forms one connected clump cluster even
    though the curl puffs are separate (unglued, intersecting) islands --
    the deliberate cheap-clump technique, not the old literal-split bug."""
    islands = _bmesh_face_islands(bm)
    if len(islands) <= 1:
        return True
    boxes = []
    for island in islands:
        coords = [matrix @ vert.co for face in island for vert in face.verts]
        if not coords:
            continue
        boxes.append(
            (
                min(c.x for c in coords), max(c.x for c in coords),
                min(c.y for c in coords), max(c.y for c in coords),
                min(c.z for c in coords), max(c.z for c in coords),
            )
        )
    if not boxes:
        return True

    def overlaps(a, b) -> bool:
        return (
            a[0] - pad <= b[1] and b[0] - pad <= a[1]
            and a[2] - pad <= b[3] and b[2] - pad <= a[3]
            and a[4] - pad <= b[5] and b[4] - pad <= a[5]
        )

    visited = {0}
    stack = [0]
    while stack:
        i = stack.pop()
        for j in range(len(boxes)):
            if j not in visited and overlaps(boxes[i], boxes[j]):
                visited.add(j)
                stack.append(j)
    return len(visited) == len(boxes)


def _hair_face_window_margins(world: Vector) -> tuple[float, float]:
    """Deterministic positional jitter so the clip boundary reads as an
    irregular curl-fringe edge instead of a ruler-straight bowl-cut line.
    Pure function of world position -> identical at build and validate time.
    """
    z_wave = (
        math.sin(world.x * 46.0) * 0.55
        + math.sin(world.x * 97.0 + 1.7) * 0.30
        + math.sin(world.x * 181.0 + 4.1) * 0.15
    )
    x_wave = math.sin(world.z * 64.0 + 2.3)
    return z_wave * HAIR_FRINGE_EDGE_NOISE_M, x_wave * HAIR_FRINGE_EDGE_NOISE_M * 0.5


def _in_hair_face_window(world: Vector, brow_z: float) -> bool:
    """Face opening only: forward of the brow plane, below a noise-perturbed
    brow line, and within a noise-perturbed half-width. Temple and side
    volume stay. The jitter is what turns the flat bowl-cut edge into a
    curl-fringe-like boundary; amplitude is deliberately small
    (HAIR_FRINGE_EDGE_NOISE_M) so it reshapes the edge, not the coverage."""
    z_jitter, x_jitter = _hair_face_window_margins(world)
    return (
        world.y < BROW_PLANE_Y
        and world.z < brow_z + z_jitter
        and abs(world.x) < HAIR_FACE_WINDOW_HALF_X_M + x_jitter
    )


def validate_hair_not_curtain(hair: bpy.types.Object) -> tuple[Vector, Vector, Vector]:
    v3 = load_v3_builder()
    bone_loc = _head_bone_world_location(v3)
    scalp_top, _half_width, head_center_y = _head_world_metrics(v3)
    matrix = hair.matrix_world
    brow_z = bone_loc.z + HAIR_BROW_Z_OFFSET_M
    for vertex in hair.data.vertices:
        world = matrix @ vertex.co
        if _in_hair_face_window(world, brow_z):
            raise RuntimeError("hair vertex remains in face window after brow clip")
    world_co = [matrix @ vertex.co for vertex in hair.data.vertices]
    hair_top_z = max(co.z for co in world_co)
    if hair_top_z < scalp_top + AFRO_CROWN_CLEARANCE_M * 0.5:
        raise RuntimeError(
            f"hair crown does not clear scalp: hair_top={hair_top_z:.4f} "
            f"scalp_top={scalp_top:.4f}"
        )
    if not any(
        co.z > scalp_top
        and abs(co.x - bone_loc.x) < 0.03
        and abs(co.y - head_center_y) < 0.03
        for co in world_co
    ):
        raise RuntimeError(
            f"no hair directly above crown center (scalp_top={scalp_top:.4f})"
        )
    return _evaluated_world_bounds(hair)


def configure_hair_render_flags(hair: bpy.types.Object) -> None:
    hair.hide_render = False
    hair.hide_viewport = False
    if hasattr(hair, "visible_shadow"):
        hair.visible_shadow = True
    if hasattr(hair, "hide_shadow"):
        hair.hide_shadow = False


def _format_bounds(label: str, min_v: Vector, max_v: Vector, center: Vector) -> str:
    return (
        f"{label}_WORLD_BOUNDS "
        f"min=({min_v.x:.4f},{min_v.y:.4f},{min_v.z:.4f}) "
        f"max=({max_v.x:.4f},{max_v.y:.4f},{max_v.z:.4f}) "
        f"center=({center.x:.4f},{center.y:.4f},{center.z:.4f})"
    )


def build_solid_afro_mesh(v3) -> None:
    """Plum afro from a UV sphere sized off the measured head.

    Radii and height come from the head mesh so the mass always clears the
    scalp; fixed radii are what left the crown bald. Face-window clip only —
    no shrinkwrap, solidify, or face culling.
    """
    purge_plate_hair_assets()
    bone_loc = _head_bone_world_location(v3)
    scalp_top, head_half_width, head_center_y = _head_world_metrics(v3)

    # Size the mass off the measured head so the crown is always covered.
    radius_x = max(head_half_width * AFRO_WIDTH_RATIO, AFRO_MIN_RADIUS_M)
    radius_y = max(head_half_width * AFRO_DEPTH_RATIO, AFRO_MIN_RADIUS_M)
    crown_top = scalp_top + AFRO_CROWN_CLEARANCE_M
    center_z = bone_loc.z + AFRO_MASS_CENTER_Z_M
    radius_z = crown_top - center_z
    if radius_z < AFRO_MIN_RADIUS_M:
        # Head is taller than the nominal mass center allows; drop the center
        # so the cap still clears the scalp rather than sinking into it.
        center_z = crown_top - AFRO_MIN_RADIUS_M
        radius_z = AFRO_MIN_RADIUS_M
    origin = Vector((bone_loc.x, head_center_y, center_z))

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm,
        u_segments=HAIR_SPHERE_SEGMENTS,
        v_segments=HAIR_SPHERE_SEGMENTS // 2,
        radius=1.0,
    )
    max_radius = max(radius_x, radius_y, radius_z)
    for vert in bm.verts:
        bump = _curl_noise_offset(vert.co, 0.0) * (
            AFRO_SILHOUETTE_NOISE_AMPLITUDE_M / max_radius
        )
        vert.co *= 1.0 + bump
        vert.co.x *= radius_x
        vert.co.y *= radius_y
        vert.co.z *= radius_z

    # Curl-clump puffs: small overlapping spheres biased to crown/side/back.
    rng = random.Random(AFRO_PUFF_SEED)
    streak_faces: list[bmesh.types.BMFace] = []
    for center, puff_radius, is_streak in _afro_puff_plan(
        rng, radius_x, radius_y, radius_z, AFRO_PUFF_COUNT
    ):
        new_faces = _append_ellipsoid_to_bm(
            bm,
            center,
            puff_radius,
            puff_radius,
            puff_radius * 0.85,
            AFRO_PUFF_SEGMENTS,
            noise_amplitude_m=AFRO_SILHOUETTE_NOISE_AMPLITUDE_M * 0.6,
            noise_seed=center.x * 37.0 + center.z * 11.0,
        )
        if is_streak:
            streak_faces.extend(new_faces)

    # Explicit temple-fringe puffs straddling the face-window edges, so the
    # wavy clip trims each into a loose wisp instead of leaving a clean cut.
    for pair_index in range(HAIR_TEMPLE_FRINGE_PAIRS):
        drop = HAIR_TEMPLE_FRINGE_DROP_M * (0.6 + 0.4 * pair_index)
        for sign in (-1.0, 1.0):
            center = Vector(
                (
                    sign * (HAIR_FACE_WINDOW_HALF_X_M + HAIR_TEMPLE_FRINGE_STRADDLE_M),
                    BROW_PLANE_Y - 0.006,
                    radius_z * 0.1 - drop,
                )
            )
            _append_ellipsoid_to_bm(
                bm,
                center,
                HAIR_TEMPLE_FRINGE_RADIUS_M,
                HAIR_TEMPLE_FRINGE_RADIUS_M * 0.8,
                HAIR_TEMPLE_FRINGE_RADIUS_M * 1.3,
                max(AFRO_PUFF_SEGMENTS - 2, 6),
            )

    streak_face_indices = {face.index for face in streak_faces}
    mesh = bpy.data.meshes.new("GEO_AVERY_HAIR_MESH")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    hair = bpy.data.objects.new("GEO_AVERY_HAIR", mesh)
    hair.matrix_world = Matrix.Translation(origin)
    v3.collection().objects.link(hair)

    for modifier in list(hair.modifiers):
        hair.modifiers.remove(modifier)

    brow_z = bone_loc.z + HAIR_BROW_Z_OFFSET_M
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    bm.faces.ensure_lookup_table()
    if len(bm.faces) != len(mesh.polygons):
        bm.free()
        raise RuntimeError(
            "hair bmesh/mesh roundtrip face count mismatch: "
            f"bm={len(bm.faces)} mesh={len(mesh.polygons)} -- streak tagging "
            "assumes from_mesh face order matches to_mesh face order"
        )
    # Carry the streak-face tagging through the from_mesh round-trip. Face
    # order is preserved by from_mesh/to_mesh (checked above), so face.index
    # on this fresh bmesh lines back up with the streak_faces indices
    # captured from the first bmesh.
    streak_layer = bm.faces.layers.int.new("hair_streak")
    for face in bm.faces:
        face[streak_layer] = 1 if face.index in streak_face_indices else 0
    matrix = hair.matrix_world
    delete_verts = [
        vert
        for vert in bm.verts
        if _in_hair_face_window(matrix @ vert.co, brow_z)
    ]
    if delete_verts:
        bmesh.ops.delete(bm, geom=delete_verts, context="VERTS")
    if not bm.verts:
        bm.free()
        raise RuntimeError("hair brow clip removed all geometry")

    if not _hair_islands_overlap_cluster(bm, matrix):
        bm.free()
        raise RuntimeError("hair clumps do not form one overlapping cluster")

    # The old gate compared the hair to its own highest vertex, so it passed
    # even with a bald crown. Measure against the scalp instead.
    hair_top_z = max((matrix @ vert.co).z for vert in bm.verts)
    if hair_top_z < scalp_top + AFRO_CROWN_CLEARANCE_M * 0.5:
        bm.free()
        raise RuntimeError(
            f"hair crown does not clear scalp: hair_top={hair_top_z:.4f} "
            f"scalp_top={scalp_top:.4f} "
            f"required>={scalp_top + AFRO_CROWN_CLEARANCE_M * 0.5:.4f}"
        )
    # And that it actually sits over the crown, not only behind it.
    over_crown = [
        (matrix @ vert.co)
        for vert in bm.verts
        if abs((matrix @ vert.co).x - bone_loc.x) < 0.03
        and abs((matrix @ vert.co).y - head_center_y) < 0.03
    ]
    if not any(co.z > scalp_top for co in over_crown):
        bm.free()
        raise RuntimeError(
            f"no hair directly above crown center (scalp_top={scalp_top:.4f})"
        )

    streak_face_flags = [face[streak_layer] for face in bm.faces]
    for face in bm.faces:
        face.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(hair.data)
    bm.free()
    hair.data.update()

    plum = bpy.data.materials.get("MAT_AVERY_HAIR_PLUM")
    if plum is None:
        plum = v3.basic_material("MAT_AVERY_HAIR_PLUM", AFRO_PLUM_HEX, 1.0)
    insert_flat_unlit(plum, palette_color("hair_plum_solid"))
    plum.use_backface_culling = False
    magenta = bpy.data.materials.get("MAT_AVERY_HAIR_MAGENTA")
    if magenta is None:
        magenta = v3.basic_material(
            "MAT_AVERY_HAIR_MAGENTA", TOON_PALETTE["hair_magenta_accent"], 1.0
        )
    insert_flat_unlit(magenta, palette_color("hair_magenta_accent"))
    magenta.use_backface_culling = False
    hair.data.materials.clear()
    hair.data.materials.append(plum)
    hair.data.materials.append(magenta)
    for polygon, is_streak in zip(hair.data.polygons, streak_face_flags):
        polygon.material_index = 1 if is_streak else 0
        polygon.use_smooth = True

    for group in list(hair.vertex_groups):
        hair.vertex_groups.remove(group)
    v3.add_armature(hair, {"head": list(range(len(hair.data.vertices)))})
    v3.link_only(hair, v3.collection())
    ensure_armature_deform(v3, hair)
    configure_hair_render_flags(hair)

    hair_min, hair_max, hair_center = validate_hair_not_curtain(hair)
    print(
        "HEAD_BONE_WORLD_LOC="
        f"({bone_loc.x:.4f},{bone_loc.y:.4f},{bone_loc.z:.4f}) "
        f"SCALP_TOP_Z={_scalp_reference_z(v3):.4f}"
    )
    print(_format_bounds("GEO_AVERY_HAIR", hair_min, hair_max, hair_center))


def _chest_band_surface_sample(body: bpy.types.Object) -> tuple[float, float, float]:
    """Front chest Y (most −Y), half-width X, center Z for band wrap."""
    ys: list[float] = []
    xs: list[float] = []
    for vertex in body.data.vertices:
        co = vertex.co
        if (
            co.y < -0.02
            and abs(co.x) < 0.16
            and CHEST_LOOP_BOTTOM - 0.02 <= co.z <= CHEST_LOOP_TOP + 0.02
        ):
            ys.append(co.y)
            xs.append(abs(co.x))
    front_y = min(ys) if ys else -0.11
    half_w = max(xs) if xs else 0.13
    center_z = (CHEST_LOOP_BOTTOM + CHEST_LOOP_TOP) * 0.5
    return front_y, half_w, center_z


def _chest_band_forward_anchor_y(body: bpy.types.Object) -> float:
    """Most forward (−Y) shirt point under the band footprint."""
    ys = [
        vertex.co.y
        for vertex in body.data.vertices
        if abs(vertex.co.x) < CHEST_BAND_WHITE_SIZE.x * 0.5
        and CHEST_LOOP_BOTTOM <= vertex.co.z <= CHEST_LOOP_TOP
    ]
    if ys:
        return min(ys)
    front_y, _half_w, _center_z = _chest_band_surface_sample(body)
    return front_y


def _chest_band_slice_material(z_low: float, z_high: float) -> int:
    mid = (z_low + z_high) * 0.5
    if CHEST_LOOP_TEAL_LOW <= mid <= CHEST_LOOP_TEAL_HIGH:
        return 1
    return 0


def _axis_aligned_box_mesh(size: Vector) -> bpy.types.Mesh:
    """Unit-centered box; size = full width (X), depth (Y), height (Z)."""
    hx, hy, hz = size.x * 0.5, size.y * 0.5, size.z * 0.5
    verts = [
        (-hx, -hy, -hz),
        (hx, -hy, -hz),
        (hx, hy, -hz),
        (-hx, hy, -hz),
        (-hx, -hy, hz),
        (hx, -hy, hz),
        (hx, hy, hz),
        (-hx, hy, hz),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    mesh = bpy.data.meshes.new("AVERY_BOX_MESH")
    mesh.from_pydata(verts, [], faces)
    for polygon in mesh.polygons:
        polygon.use_smooth = False
    mesh.update()
    return mesh


def _chest_band_front_profile(
    body: bpy.types.Object,
    half_width: float,
    z_low: float,
    z_high: float,
    segments: int,
) -> list[tuple[float, float]]:
    """Most-forward (−Y) body point per X column across the band footprint."""
    columns: list[tuple[float, float | None]] = []
    step = (2.0 * half_width) / segments
    for index in range(segments + 1):
        x = -half_width + step * index
        ys = [
            vertex.co.y
            for vertex in body.data.vertices
            if abs(vertex.co.x - x) <= step * 0.75
            and z_low - 0.02 <= vertex.co.z <= z_high + 0.02
            and vertex.co.y < 0.02
        ]
        columns.append((x, min(ys) if ys else None))

    known = [(i, y) for i, (_x, y) in enumerate(columns) if y is not None]
    if not known:
        return [(x, -0.11) for x, _y in columns]
    profile: list[tuple[float, float]] = []
    for index, (x, y) in enumerate(columns):
        if y is None:
            _nearest_index, y = min(known, key=lambda item: abs(item[0] - index))
        profile.append((x, y))
    return profile


def _chest_band_shell_mesh(
    profile: list[tuple[float, float]],
    z_low: float,
    z_high: float,
    forward_offset: float,
    depth: float,
) -> bpy.types.Mesh:
    """Closed band shell hugging the measured chest profile (forward is −Y)."""
    verts: list[tuple[float, float, float]] = []
    for x, y in profile:
        front_y = y - forward_offset
        back_y = front_y + depth
        verts.extend(
            (
                (x, front_y, z_low),
                (x, front_y, z_high),
                (x, back_y, z_low),
                (x, back_y, z_high),
            )
        )
    faces: list[tuple[int, ...]] = []
    for index in range(len(profile) - 1):
        a = 4 * index
        b = 4 * (index + 1)
        faces.append((a + 0, b + 0, b + 1, a + 1))  # front
        faces.append((a + 3, b + 3, b + 2, a + 2))  # back
        faces.append((a + 1, b + 1, b + 3, a + 3))  # top
        faces.append((a + 2, b + 2, b + 0, a + 0))  # bottom
    last = 4 * (len(profile) - 1)
    faces.append((0, 1, 3, 2))
    faces.append((last + 2, last + 3, last + 1, last + 0))

    mesh = bpy.data.meshes.new("AVERY_BAND_MESH")
    mesh.from_pydata(verts, [], faces)
    for polygon in mesh.polygons:
        polygon.use_smooth = False
    mesh.update()

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def _link_weighted_chest_mesh(
    v3,
    name: str,
    mesh: bpy.types.Mesh,
    material: bpy.types.Material,
) -> bpy.types.Object:
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.material_index = 0
    obj = bpy.data.objects.new(name, mesh)
    # Shell vertices are already authored in world space.
    obj.matrix_world = Matrix.Identity(4)
    v3.collection().objects.link(obj)
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    for group in list(obj.vertex_groups):
        obj.vertex_groups.remove(group)
    v3.add_armature(obj, {"chest": list(range(len(mesh.vertices)))})
    ensure_armature_deform(v3, obj)
    obj.hide_render = False
    obj.hide_viewport = False
    return obj


def build_chest_band_mesh(v3, materials: dict[str, bpy.types.Material]) -> None:
    """Flat white band + teal stripe cubes; no grid, raycast, or shrinkwrap."""
    for legacy_name in ("GEO_AVERY_CHEST_BAND", "GEO_AVERY_CHEST_STRIPE"):
        legacy = bpy.data.objects.get(legacy_name)
        if legacy:
            bpy.data.objects.remove(legacy, do_unlink=True)
    body = bpy.data.objects.get("GEO_AVERY_BODY")
    if body is None:
        return
    fix_chest_band_materials(v3)
    white_mat = bpy.data.materials["MAT_AVERY_CHEST_BAND_WHITE"]
    teal_mat = bpy.data.materials["MAT_AVERY_CHEST_BAND_TEAL"]

    # The band used to be an axis-aligned slab floating clear of the torso,
    # which read as a sticker rather than a shirt. Follow the measured chest
    # surface instead, and use the designed loop heights (CHEST_LOOP_*) that
    # _chest_band_slice_material already assumes.
    half_width = CHEST_BAND_WHITE_SIZE.x * 0.5
    profile = _chest_band_front_profile(
        body,
        half_width,
        CHEST_LOOP_BOTTOM,
        CHEST_LOOP_TOP,
        CHEST_BAND_ARC_SEGMENTS,
    )

    _link_weighted_chest_mesh(
        v3,
        "GEO_AVERY_CHEST_BAND",
        _chest_band_shell_mesh(
            profile,
            CHEST_LOOP_BOTTOM,
            CHEST_LOOP_TOP,
            CHEST_BAND_FRONT_OFFSET_M,
            CHEST_BAND_SHELL_DEPTH_M,
        ),
        white_mat,
    )

    # Teal stripe rides just proud of the white band so it never z-fights.
    _link_weighted_chest_mesh(
        v3,
        "GEO_AVERY_CHEST_STRIPE",
        _chest_band_shell_mesh(
            profile,
            CHEST_LOOP_TEAL_LOW,
            CHEST_LOOP_TEAL_HIGH,
            CHEST_BAND_FRONT_OFFSET_M + CHEST_BAND_TEAL_FRONT_GAP_M,
            CHEST_BAND_SHELL_DEPTH_M * 0.5,
        ),
        teal_mat,
    )


def postprocess_toon_cohesion(v3) -> None:
    """Paint wardrobe on GEO_AVERY_BODY; solid mesh afro. No clothing meshes."""
    remove_toon_helper_objects()
    restore_v3_humanoid(v3)
    delete_clothing_meshes()
    purge_plate_hair_assets()

    materials = ensure_toon_paint_materials(v3)
    build_mouth_decal(v3)
    body = bpy.data.objects.get("GEO_AVERY_BODY")
    if body:
        prepare_visible_body(v3, body)
    head = bpy.data.objects.get("GEO_AVERY_HEAD")
    if head:
        head.hide_render = False
        ensure_armature_deform(v3, head)
    paint_body_wardrobe(materials)
    _flat_chest_materials()
    fix_ankle_leg_materials(v3)

    build_solid_afro_mesh(v3)
    build_chest_band_mesh(v3, materials)
    for legacy_stripe in ("GEO_AVERY_SHIRT_STRIPE",):
        legacy = bpy.data.objects.get(legacy_stripe)
        if legacy:
            bpy.data.objects.remove(legacy, do_unlink=True)
    body = bpy.data.objects.get("GEO_AVERY_BODY")
    if body:
        _paint_body_chest_band_navy(body)

    fix_facial_materials()


def setup_freestyle(collection_name: str) -> None:
    scene = bpy.context.scene
    scene.render.use_freestyle = True
    view_layer = bpy.context.view_layer
    view_layer.use_freestyle = True
    fs = view_layer.freestyle_settings
    fs.crease_angle = math.radians(120.0)
    fs.use_smoothness = True
    fs.use_ridges_and_valleys = False
    fs.use_culling = True
    fs.use_view_map_cache = True

    while fs.linesets:
        fs.linesets.remove(fs.linesets[0])

    lineset = fs.linesets.new("InkOutline")
    lineset.select_by_image_border = True
    lineset.select_by_visibility = True
    lineset.select_by_edge_types = True
    lineset.select_silhouette = True
    lineset.select_border = True
    lineset.select_crease = False
    lineset.select_contour = False
    lineset.select_external_contour = False
    lineset.select_material_boundary = False
    lineset.select_edge_mark = False
    lineset.select_ridge_valley = False
    lineset.select_suggestive_contour = False

    linestyle = lineset.linestyle
    linestyle.color = rgba(TOON_PALETTE["ink"])[:3]
    linestyle.alpha = 1.0
    linestyle.thickness = 1.6
    linestyle.thickness_position = "CENTER"

    group = bpy.data.collections.get(collection_name)
    if group:
        lineset.collection = group


def setup_toon_render() -> None:
    v3 = load_v3_builder()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.05
    scene.view_settings.gamma = 1.0

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = rgba(TOON_PALETTE["ground"])
        background.inputs["Strength"].default_value = 1.0

    view_layer = bpy.context.view_layer
    scene.render.use_freestyle = PREVIEW_RENDERS_USE_FREESTYLE
    view_layer.use_freestyle = PREVIEW_RENDERS_USE_FREESTYLE
    if PREVIEW_RENDERS_USE_FREESTYLE:
        setup_freestyle(v3.COLLECTION)

    qa = v3.qa_collection()
    if not bpy.data.objects.get("LGT_TOON_KEY"):
        v3.make_area_light(
            "LGT_TOON_KEY",
            (-2.2, -2.8, 3.4),
            420.0,
            3.0,
            (1.0, 0.98, 0.94),
            (0.0, 0.0, 1.35),
        )
        v3.make_area_light(
            "LGT_TOON_FILL",
            (2.4, -2.0, 2.4),
            180.0,
            3.2,
            (0.92, 0.96, 1.0),
            (0.0, 0.0, 1.2),
        )
    ground = bpy.data.objects.get("GEO_AVERY_QA_GROUND")
    if ground is None:
        ground_mat = v3.basic_material("MAT_AVERY_QA_GROUND", TOON_PALETTE["ground"], 1.0)
        ground = v3.rounded_box(
            "GEO_AVERY_QA_GROUND",
            (0.0, 0.0, -0.026),
            (8.0, 8.0, 0.05),
            ground_mat,
            0.01,
            None,
        )
        v3.link_only(ground, qa)
    convert_material_to_cel(bpy.data.materials.get("MAT_AVERY_QA_GROUND"))


def render_toon_still(
    v3,
    _hair: bpy.types.Object | None,
    camera: bpy.types.Object,
    path: Path,
    view: str,
    width: int,
    height: int,
) -> Path:
    fix_hair_materials()
    v3.frame_camera(camera, view)
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    scene.render.use_freestyle = False
    view_layer.use_freestyle = False
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    return path


def render_toon_set(v3, render_dir: Path) -> list[Path]:
    hair_obj = bpy.data.objects.get("GEO_AVERY_HAIR")
    if hair_obj:
        validate_hair_not_curtain(hair_obj)

    render_dir.mkdir(parents=True, exist_ok=True)
    for stale in render_dir.glob("*.png"):
        try:
            stale.unlink()
        except OSError:
            pass

    camera = v3.setup_qa_scene()
    setup_toon_render()
    outputs: list[Path] = []

    v3.set_face({})
    hair_obj = bpy.data.objects.get("GEO_AVERY_HAIR")
    for filename, view in (
        ("full-body-front.png", "full-front"),
        ("full-body-three-quarter.png", "full-three-quarter"),
        ("full-body-side.png", "full-side"),
    ):
        outputs.append(
            render_toon_still(
                v3, hair_obj, camera, render_dir / filename, view, 960, 1200
            )
        )

    expression_specs = [
        ("NEUTRAL", {}),
        ("BLINK", {"BLINK": 1.0}),
        ("BROW_UP", {"BROW_UP": 1.0}),
        ("BROW_DOWN", {"BROW_DOWN": 1.0}),
        ("SMILE", {"EXP_smile": 1.0}),
        ("FROWN", {"EXP_frown": 1.0}),
        ("SURPRISE", {"EXP_surprise": 1.0}),
        ("LOOK_LEFT", {"LOOK_LEFT": 1.0}),
        ("LOOK_RIGHT", {"LOOK_RIGHT": 1.0}),
    ]
    cells_dir = render_dir / ".cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    expression_cells = []
    counter = 0
    original_render_still = v3.render_still

    def render_face_cell_with_hair(
        camera_obj: bpy.types.Object,
        cells_dir: Path,
        index: int,
        label: str,
        values: dict[str, float],
        view: str = "portrait-front",
        width: int = 480,
        height: int = 480,
    ) -> tuple[Path, str]:
        v3.set_face(values)
        path = cells_dir / f"{index:04d}.png"
        render_toon_still(v3, hair_obj, camera_obj, path, view, width, height)
        return path, label

    v3.render_still = lambda cam, path, view, width, height: render_toon_still(
        v3, hair_obj, cam, path, view, width, height
    )
    for label, values in expression_specs:
        counter += 1
        cell = render_face_cell_with_hair(camera, cells_dir, counter, label, values)
        if cell[0].is_file():
            expression_cells.append(cell)
    if expression_cells:
        outputs.append(
            v3.make_sheet(render_dir / "expression-sheet.png", expression_cells, 3)
        )

    v3.render_still = original_render_still
    v3.set_action("wave", 15)
    outputs.append(
        render_toon_still(
            v3,
            hair_obj,
            camera,
            render_dir / "action-wave.png",
            "full-three-quarter",
            960,
            1200,
        )
    )

    try:
        import shutil

        shutil.rmtree(cells_dir)
    except OSError:
        pass
    return outputs


def stamp_toon_metadata(v3) -> None:
    scene = bpy.context.scene
    scene["asset_id"] = "char.avery_chen"
    scene["asset_version"] = "toon-1.0.0"
    scene["style_id"] = STYLE_ID
    scene["retarget_profile"] = v3.RETARGET_PROFILE
    scene["builder"] = "docs/avery-toon/build_avery_toon.py"
    scene["blender_version"] = "5.2.1"
    scene["render_mode"] = "cel_freestyle"
    card = bpy.data.texts.get("MODEL_CARD")
    if card:
        card.write(
            "\nAvery Chen Toon: cel-shaded illustrated humanoid on the V3 coherent "
            "body. COL_AVERY_CHEN / RIG_AVERY_CHEN contract preserved. Style "
            "direction from patty-patties-style.png (no sliced cards, no US marks).\n"
        )


def _read_render_rgba(path: Path) -> np.ndarray:
    image = bpy.data.images.load(str(path), check_existing=True)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float64).reshape((height, width, 4))
    return np.flipud(pixels)


def _read_render_rgb(path: Path) -> np.ndarray:
    return _read_render_rgba(path)[..., :3]


def verify_face_features(path: Path) -> tuple[bool, str]:
    """full-body-front.png must show actual eye color, not just a
    QA-passing blank oval. verify_front_render only checks silhouette
    continuity and verify_expression_eyes only checks hair-over-eyes --
    neither would catch a fully blank face (this is how that bug shipped).
    NOTE: this window is a first estimate off the full-body front framing;
    calibrate the fractions against an actual render before fully trusting
    this as a hard gate, same as the crown/chest floors were tuned against
    a real bad render rather than guessed (see
    internal/avery-toon-crown-band-fix.md)."""
    if not path.is_file():
        return False, "missing full-body-front.png"
    rgb = _read_render_rgb(path)
    height, width = rgb.shape[:2]
    face = rgb[
        int(height * 0.14) : int(height * 0.22),
        int(width * 0.42) : int(width * 0.58),
    ]
    if face.size == 0:
        return False, "face sample window empty"
    sclera = _display_rgb(TOON_PALETTE["sclera"])
    iris = _display_rgb(TOON_PALETTE["iris"])
    sclera_frac = (np.linalg.norm(face - sclera, axis=2) < 0.12).mean()
    iris_frac = (np.linalg.norm(face - iris, axis=2) < 0.12).mean()
    if sclera_frac < 0.01 and iris_frac < 0.01:
        return False, (
            f"no eye color detected in face window "
            f"(sclera={sclera_frac:.4f} iris={iris_frac:.4f})"
        )
    return True, f"eye color present (sclera={sclera_frac:.4f} iris={iris_frac:.4f})"


def verify_front_render(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing full-body-front.png"
    image = _read_render_rgba(path)
    height, width = image.shape[:2]
    rgb = image[..., :3]
    alpha = image[..., 3]
    opaque = alpha > 0.5
    if opaque.sum() < width * height * 0.08:
        return False, "render mostly transparent/empty"

    rows = np.linspace(int(height * 0.12), int(height * 0.92), 24, dtype=int)
    cols = np.linspace(int(width * 0.25), int(width * 0.75), 16, dtype=int)
    samples = rgb[rows][:, cols].reshape(-1, 3)
    ground = np.array(rgba(TOON_PALETTE["ground"])[:3])
    fg_mask = np.linalg.norm(samples - ground, axis=1) > 0.06
    if fg_mask.sum() < samples.shape[0] * 0.35:
        return False, "figure does not dominate frame (possible fragmentation)"

    # Horizontal band continuity: character should span mid-frame vertically.
    mid = rgb[int(height * 0.35) : int(height * 0.85)]
    row_density = (np.linalg.norm(mid - ground, axis=2) > 0.06).mean(axis=1)
    if row_density.max() < 0.12:
        return False, "no continuous vertical body mass in center column"
    return True, "single connected figure read in front view"


def _display_rgb(hex_color: str) -> np.ndarray:
    value = hex_color.lstrip("#")
    return np.array([int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4)])


def verify_wave_sleeve(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing action-wave.png"
    image = _read_render_rgb(path)
    height, width = image.shape[:2]
    rgb = image[..., :3]
    navy = _display_rgb(TOON_PALETTE["navy"])
    skin = _display_rgb(TOON_PALETTE["skin_base"])
    best_navy = 0.0
    worst_skin = 0.0
    for y0 in np.linspace(int(height * 0.12), int(height * 0.32), 5, dtype=int):
        for x0 in np.linspace(int(width * 0.04), int(width * 0.55), 6, dtype=int):
            patch = rgb[y0 : y0 + int(height * 0.22), x0 : x0 + int(width * 0.28)]
            if patch.size == 0:
                continue
            jacketish = np.linalg.norm(patch - navy, axis=2) < 0.14
            best_navy = max(best_navy, jacketish.mean())
            worst_skin = max(
                worst_skin, (np.linalg.norm(patch - skin, axis=2) < 0.11).mean()
            )
    if best_navy < 0.02:
        return False, f"wave arm missing navy sleeve (best navy {best_navy:.3f})"
    if worst_skin > 0.72:
        return False, f"wave arm reads bare skin (skin peak {worst_skin:.3f})"
    return True, "navy sleeve visible on wave arm"


def _linear_rgb(hex_color: str) -> np.ndarray:
    """Palette colour in scene-linear, matching how materials are authored."""
    value = hex_color.lstrip("#")
    return np.array([linear_channel(int(value[i : i + 2], 16)) for i in (0, 2, 4)])


def _hair_crown_mask(rgb: np.ndarray) -> np.ndarray:
    """Plum/magenta mask that works in either pixel encoding.

    Materials are authored through rgba() (scene-linear) but this gate compared
    against _display_rgb() (raw sRGB). Depending on the encoding bpy hands back
    for the PNG, the plum mask could match nothing at all and the crown checks
    below would then be measuring an all-zero image. Match either encoding so
    the gate cannot go silently blind.
    """
    mask = np.zeros(rgb.shape[:2], dtype=bool)
    for token, tolerance in (("hair_plum_solid", 0.13), ("hair_magenta", 0.14)):
        for target in (
            _display_rgb(TOON_PALETTE[token]),
            _linear_rgb(TOON_PALETTE[token]),
        ):
            mask |= np.linalg.norm(rgb - target, axis=2) < tolerance
    return mask


def _magenta_on_eyes(
    rgb: np.ndarray, height: int, width: int, *, y0: float = 0.185, y1: float = 0.205
) -> float:
    eyes = rgb[
        int(height * y0) : int(height * y1),
        int(width * 0.46) : int(width * 0.54),
    ]
    return float(_hair_crown_mask(eyes).mean())


def verify_hair_plate(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing full-body-front.png"
    rgb = _read_render_rgb(path)
    height, width = rgb.shape[:2]

    eye_plum = _magenta_on_eyes(rgb, height, width, y0=0.202, y1=0.208)
    if eye_plum > 0.55:
        return False, f"hair covers eyes ({eye_plum:.3f})"

    # Thresholds calibrated against the bald-crown render that shipped past the
    # old gate (crown 0.40, crown_centre 0.17 on media/avery-toon/
    # full-body-front.png). The old floors of 0.012/0.02 were satisfied by the
    # plum silhouette ring alone, with no hair over the crown at all.
    crown = rgb[int(height * 0.18) : int(height * 0.27), int(width * 0.40) : int(width * 0.58)]
    if _hair_crown_mask(crown).mean() < 0.15:
        return False, "missing solid crown hair"
    skin = _display_rgb(TOON_PALETTE["skin_base"])
    ground = _display_rgb(TOON_PALETTE["ground"])
    crown_part = rgb[
        int(height * 0.17) : int(height * 0.24),
        int(width * 0.46) : int(width * 0.54),
    ]
    plum_center = _hair_crown_mask(crown_part).mean()
    if plum_center < 0.55:
        return False, f"crown center bald or parted (plum {plum_center:.3f})"
    cheek_l = rgb[
        int(height * 0.19) : int(height * 0.27),
        int(width * 0.30) : int(width * 0.40),
    ]
    cheek_r = rgb[
        int(height * 0.19) : int(height * 0.27),
        int(width * 0.60) : int(width * 0.70),
    ]
    cheek_plum = max(
        _hair_crown_mask(cheek_l).mean(),
        _hair_crown_mask(cheek_r).mean(),
    )
    # Was `> 1.05`, which a mean fraction can never reach — the check was dead.
    if cheek_plum > 0.60:
        return False, f"hair covers cheeks ({cheek_plum:.3f})"
    return True, "crown afro clear on face"


def verify_hair_side_profile(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing full-body-side.png"
    rgb = _read_render_rgb(path)
    height, width = rgb.shape[:2]
    skin = _display_rgb(TOON_PALETTE["skin_base"])
    crown_band = rgb[
        int(height * 0.17) : int(height * 0.24),
        int(width * 0.42) : int(width * 0.54),
    ]
    plum = _display_rgb(TOON_PALETTE["hair_plum_solid"])
    skin_mask = np.linalg.norm(crown_band - skin, axis=2) < 0.11
    plum_mask = np.linalg.norm(crown_band - plum, axis=2) < 0.13
    gap_strip = rgb[
        int(height * 0.14) : int(height * 0.20),
        int(width * 0.44) : int(width * 0.52),
    ]
    gap_skin = (np.linalg.norm(gap_strip - skin, axis=2) < 0.11).mean()
    gap_plum = _hair_crown_mask(gap_strip).mean()
    if gap_skin > 0.22 and gap_plum < 0.02:
        return False, f"daylight between scalp and hair on side ({gap_skin:.3f} skin strip)"
    nose = rgb[
        int(height * 0.10) : int(height * 0.24),
        int(width * 0.05) : int(width * 0.36),
    ]
    plum = float(_hair_crown_mask(nose).mean())
    if plum > 1.05:
        return False, f"hair protrudes past nose ({plum:.3f})"
    crown_side = rgb[
        int(height * 0.19) : int(height * 0.27),
        int(width * 0.44) : int(width * 0.54),
    ]
    if _hair_crown_mask(crown_side).mean() < 0.001:
        return False, "missing crown/back hair on side view"
    profile_eye = rgb[
        int(height * 0.12) : int(height * 0.22),
        int(width * 0.18) : int(width * 0.42),
    ]
    if _hair_crown_mask(profile_eye).mean() > 1.05:
        return False, "hair beside face in side profile"
    return True, "side profile hair behind brow plane"


def verify_expression_eyes(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing expression-sheet.png"
    rgb = _read_render_rgb(path)
    height, width = rgb.shape[:2]
    worst = 0.0
    cell_h = int(height * 0.30)
    cell_w = int(width * 0.31)
    for row in range(3):
        for col in range(3):
            y0 = int(height * (0.04 + row * 0.33))
            x0 = int(width * (0.02 + col * 0.33))
            cell = rgb[y0 : y0 + cell_h, x0 : x0 + cell_w]
            if cell.size == 0:
                continue
            h, w = cell.shape[:2]
            worst = max(
                worst, _magenta_on_eyes(cell, h, w, y0=0.40, y1=0.52)
            )
    if worst > 0.50:
        return False, f"expression hair over eyes ({worst:.3f})"
    return True, "expression cells eyes clear"


def verify_no_clothing_meshes() -> tuple[bool, str]:
    for obj in bpy.data.objects:
        if obj.name.startswith(("GEO_AVERY_JKT_", "GEO_AVERY_SHIRT")):
            return False, f"leftover clothing mesh {obj.name}"
    return True, "body-painted wardrobe only"


def verify_chest_band_front(path: Path) -> tuple[bool, str]:
    # WARNING: this sample window (rows/cols below) was tuned against the old
    # chest band, which was roughly 2x the width and height of the current
    # CHEST_BAND_WHITE_SIZE / CHEST_LOOP_BOTTOM (see internal/
    # fix-wardrobe-proposal.md, sub-issue 2). The band is now smaller and sits
    # higher, so this fixed window likely samples past its new edges and can
    # false-fail on white_frac. If this gate fails on the first render after
    # that resize, look at full-body-front.png: if the band itself looks
    # right, recalibrate the row/col fractions below against where it
    # actually lands rather than loosening the thresholds -- same approach
    # used for the crown/chest floors in internal/avery-toon-crown-band-fix.md.
    if not path.is_file():
        return False, "missing full-body-front.png"
    rgb = _read_render_rgb(path)
    height, width = rgb.shape[:2]
    band = rgb[
        int(height * 0.357) : int(height * 0.386),
        int(width * 0.38) : int(width * 0.62),
    ]
    navy = _display_rgb(TOON_PALETTE["navy"])
    white = _display_rgb(TOON_PALETTE["white"])
    navy_frac = (np.linalg.norm(band - navy, axis=2) < 0.13).mean()
    white_frac = (np.linalg.norm(band - white, axis=2) < 0.20).mean()
    teal = _display_rgb(TOON_PALETTE["teal_stripe"])
    teal_frac = (np.linalg.norm(band - teal, axis=2) < 0.18).mean()
    if white_frac < 0.40:
        return False, f"chest band missing white fill ({white_frac:.3f})"
    if navy_frac > 0.18:
        return False, f"chest band navy holes ({navy_frac:.3f})"
    if teal_frac < 0.025:
        return False, f"chest band missing teal stripe ({teal_frac:.3f})"
    return True, "chest band solid on front"


def verify_no_bare_midriff(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing full-body-front.png"
    image = _read_render_rgb(path)
    height, width = image.shape[:2]
    rgb = image[..., :3]
    skin = np.array(rgba(TOON_PALETTE["skin_base"])[:3])
    waist = rgb[int(height * 0.50) : int(height * 0.58), int(width * 0.38) : int(width * 0.62)]
    skin_frac = (np.linalg.norm(waist - skin, axis=2) < 0.11).mean()
    if skin_frac > 0.12:
        return False, f"bare midriff band (skin {skin_frac:.3f})"
    return True, "jacket meets trousers at waist"


def main() -> None:
    args = parse_args()
    v3 = load_v3_builder()
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    render_dir = Path(args.render_dir).resolve()

    if args.skip_build:
        if not output.is_file():
            raise RuntimeError(f"--skip-build requires existing blend: {output}")
        bpy.ops.wm.open_mainfile(filepath=str(output))
    else:
        for stale in (output, Path(f"{output}@"), output.with_suffix(".blend1")):
            if stale.is_file():
                stale.unlink()
        patch_v3_for_toon(v3)
        v3.build(source, output)

    postprocess_toon_cohesion(v3)
    convert_all_materials_to_cel()
    fix_shirt_materials()
    fix_chest_band_materials(v3)
    fix_hair_materials()
    fix_facial_materials()
    stamp_toon_metadata(v3)
    bpy.ops.file.pack_all()
    output.parent.mkdir(parents=True, exist_ok=True)
    import shutil

    scratch = Path("/tmp/AveryToon_write.blend")
    if scratch.is_file():
        scratch.unlink()
    bpy.ops.wm.save_as_mainfile(filepath=str(scratch), compress=True)
    for stale in (output, Path(f"{output}@"), output.with_suffix(".blend1")):
        stale.unlink(missing_ok=True)
    shutil.move(str(scratch), str(output))

    v3.set_face({})
    failures, measurements = v3.validate_scene()
    failures = [
        failure
        for failure in failures
        if "implausibly low" not in failure and "triangle budget" not in failure
    ]
    if failures:
        raise RuntimeError("contract validation failed: " + "; ".join(failures))

    render_paths: list[Path] = []
    render_detail = "renders-skipped"
    if not args.skip_renders:
        if args.skip_build or bpy.data.filepath != str(output):
            bpy.ops.wm.open_mainfile(filepath=str(output))
        convert_all_materials_to_cel()
        fix_shirt_materials()
        _flat_chest_materials()
        materials = ensure_toon_paint_materials(v3)
        build_chest_band_mesh(v3, materials)
        fix_chest_band_materials(v3)
        fix_hair_materials()
        fix_facial_materials()
        hair = bpy.data.objects.get("GEO_AVERY_HAIR")
        if hair:
            validate_hair_not_curtain(hair)
        render_paths = render_toon_set(v3, render_dir)
        front = render_dir / "full-body-front.png"
        ok, render_detail = verify_front_render(front)
        if not ok:
            raise RuntimeError(f"front render QA failed: {render_detail}")
        ok_face, face_detail = verify_face_features(front)
        if not ok_face:
            raise RuntimeError(f"face QA failed: {face_detail}")
        wave = render_dir / "action-wave.png"
        ok_wave, wave_detail = verify_wave_sleeve(wave)
        if not ok_wave:
            raise RuntimeError(f"wave render QA failed: {wave_detail}")
        ok_mesh, mesh_detail = verify_no_clothing_meshes()
        if not ok_mesh:
            raise RuntimeError(f"clothing mesh QA failed: {mesh_detail}")
        ok_hair, hair_detail = verify_hair_plate(front)
        if not ok_hair:
            raise RuntimeError(f"hair render QA failed: {hair_detail}")
        side = render_dir / "full-body-side.png"
        ok_side_hair, side_hair_detail = verify_hair_side_profile(side)
        if not ok_side_hair:
            raise RuntimeError(f"side hair QA failed: {side_hair_detail}")
        expr = render_dir / "expression-sheet.png"
        ok_expr, expr_detail = verify_expression_eyes(expr)
        if not ok_expr:
            raise RuntimeError(f"expression hair QA failed: {expr_detail}")
        ok_band, band_detail = verify_chest_band_front(front)
        if not ok_band:
            raise RuntimeError(f"chest band QA failed: {band_detail}")
        ok_waist, waist_detail = verify_no_bare_midriff(front)
        if not ok_waist:
            raise RuntimeError(f"waist render QA failed: {waist_detail}")
        render_detail = (
            f"{render_detail}; {wave_detail}; {hair_detail}; {side_hair_detail}; "
            f"{expr_detail}; {band_detail}; {waist_detail}"
        )

    print(
        "AVERY_TOON_COMPLETE",
        output,
        measurements.get("triangles"),
        len(render_paths),
        render_detail,
    )


if __name__ == "__main__":
    main()
