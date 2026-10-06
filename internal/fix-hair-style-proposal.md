# Avery Toon hair: curl-cluster + streak-material proposal

## symptom

Render (`images/6.png`) shows hair as a smooth, solid, flat-purple dome
(`~#6B2D5B`) with a hard straight horizontal cut line across the forehead
(bowl-cut fringe). No texture, no volume variation, no color variation.

Target (`images/7.png`, Patty Patties style sheet) shows big, voluminous,
textured curly hair: dark plum/burgundy base with visible magenta/pink
highlight streaks woven through the curls, and a soft, loose-curl/fringe
hairline in front view rather than a hard cut edge.

## evidence

- `docs/avery-toon/build_avery_toon.py:1215-1340` — `build_solid_afro_mesh()`
  builds hair as **one** UV sphere (`bmesh.ops.create_uvsphere`,
  `HAIR_SPHERE_SEGMENTS = 48`, line 33), scaled to an ellipsoid by
  `radius_x/radius_y/radius_z` (lines 1227-1237), with **no post-process
  displacement, no secondary geometry, no per-face variation** — this is
  mechanically why it renders as a perfectly smooth dome.
- `docs/avery-toon/build_avery_toon.py:1263-1273` — the only shaping op after
  the sphere is a hard delete of every vertex matching `_in_hair_face_window`
  (line 1158-1165), which is a flat-plane test:
  `world.y < BROW_PLANE_Y and world.z < brow_z and abs(world.x) < HAIR_FACE_WINDOW_HALF_X_M`.
  A flat `z < brow_z` cut through a smooth ellipsoid is mechanically exactly
  the hard straight fringe line visible in the render.
- `docs/avery-toon/build_avery_toon.py:470-477` — `fix_hair_materials()`
  calls `insert_flat_unlit(plum, palette_color("hair_plum_solid"))` on the
  single `MAT_AVERY_HAIR_PLUM` material — one material, one flat emission
  color, no shadow ramp, no second material anywhere in the hair's material
  slots (confirmed: `hair.data.materials.clear(); hair.data.materials.append(plum)`
  at lines 1321-1322, and every polygon forced to `material_index = 0` at
  line 1324). There is no code path that ever assigns a second material to
  `GEO_AVERY_HAIR`.
- `docs/avery-toon/build_avery_toon.py:61-83` (`TOON_PALETTE`) — `hair_magenta`
  already exists at `"#C43B8C"` (line 65), identical to the general `magenta`
  token (line 67). It is **referenced only by the QA color mask**
  (`_hair_crown_mask`, lines 1926-1942, which checks both `hair_plum_solid`
  and `hair_magenta` as "hair" pixels) — never by any geometry/material
  builder. This confirms the prompt's hypothesis: a magenta accent was
  anticipated by the QA gate but never wired into the actual build.
- `docs/avery-toon/build_avery_toon.py:1139-1155` (`_hair_island_split_left_right`)
  and `:1278-1284` (the `len(islands) != 1` check in `build_solid_afro_mesh`)
  are **hard-coded for a single watertight blob**: they explicitly reject
  multi-island meshes. Any "cluster of overlapping puff spheres" design
  must replace, not merely coexist with, this invariant (see `scope` below).

## root_cause

Working as designed; the design was too simple. `build_solid_afro_mesh` is a
recent, deliberate simplification (its own docstring: "Face-window clip
only — no shrinkwrap, solidify, or face culling") that fixed a worse bug (a
bald crown from fixed-radius spheres not clearing the scalp). In fixing that,
it collapsed the hair to the simplest possible shape: one smooth ellipsoid,
one flat clip plane, one flat-color material. That is mechanically sufficient
to pass every current QA gate (coverage floors/ceilings keyed to plum
pixels) but has no mechanism for silhouette texture, volume clumping, or
color variation — none of those properties were ever encoded in geometry or
materials, so none can appear in the render.

## confidence

High on the diagnosis (direct code inspection + visual confirmation against
both images). Medium on the exact numeric constants below — they're
reasoned from the existing scale (`AFRO_*_M` constants, QA sample-box
fractions) but should be tuned against one real render-and-measure pass,
called out explicitly in `verification`.

---

## proposed_change

### Design summary

1. **Perimeter/silhouette noise** on the main cap's own surface (unit-sphere
   radial perturbation via a few sine harmonics over spherical angle, applied
   before ellipsoid scaling) — breaks the perfectly smooth dome outline.
2. **Cluster of overlapping "puff" spheres** stuck onto the cap (the
   "common cheap technique for stylized curl clumps" named in the brief) —
   gives the silhouette real volume variation, not just surface ripple.
3. **Two materials** (`MAT_AVERY_HAIR_PLUM` base, new `MAT_AVERY_HAIR_MAGENTA`
   accent) with magenta assigned to a deterministic subset of the puff
   clumps — produces visible streak clumps instead of one flat color. Reuses
   the already-defined `hair_magenta` palette token (`#C43B8C`); see
   `color choice` note below for why I'm not changing the hex.
4. **Wavy clip boundary** instead of a flat plane: `_in_hair_face_window`'s
   z and x thresholds get small deterministic positional jitter, so the
   clip edge reads as an irregular curl-fringe line instead of a ruler-
   straight bowl cut. A few explicit "temple fringe" puffs are placed
   straddling the window's vertical edges so the (now wavy) clip trims them
   into loose wisps at the hairline rather than leaving a clean boundary.
5. The exact-one-island / no-left-right-split build-time self-checks are
   replaced with a cluster-overlap check, since multiple overlapping (but
   topologically disconnected) puff islands are now the intended geometry,
   not a bug signature.

### Scoping decision: front-framing loose curls, not an explicit pulled-back pouf

`render_toon_set()` (`docs/avery-toon/build_avery_toon.py:1735-1829`) renders
exactly three body views — `full-front`, `full-three-quarter`, `full-side` —
plus a front-facing expression sheet and a three-quarter action-wave still.
**No back view is ever rendered.** The style sheet's most distinctive
"pulled-back pouf/bun with escaping tendrils" read depends heavily on the
back view (the gathering point, the loose strands trailing down the nape),
which this pipeline never produces evidence for, and partially on an
asymmetric mass shifted toward the back-crown, which is also the riskiest
change against the existing crown-center/no-curtain invariants
(`validate_hair_not_curtain`'s "hair directly above crown center" box check,
`docs/avery-toon/build_avery_toon.py:1185-1193`).

Because this hair is a real 3D mesh (not a billboard/sprite), a
symmetric, voluminous, curl-textured mass with streak materials and a soft
fringe will *already* read as volumetric, non-flat hair from front,
three-quarter, and side — the dimension actually being graded. I'm scoping
to that: a big curl-cloud silhouette with loose face-framing fringe,
deterministically clumped and streaked all around the cap (crown, sides,
back), not a separate asymmetric "gathered into a bun" topology. Attempting
the literal pouf/bun would mean solving a harder, riskier geometry problem
to sell a detail (the gather point + trailing tendrils) that's mostly
invisible in the views this pipeline actually grades — not worth it.

### Code changes

**1. New import** (top of file, with the others):

```python
# before
import argparse
import importlib.util
import math
import sys

# after
import argparse
import importlib.util
import math
import random
import sys
```

**2. New constants** (after the existing `AFRO_*`/`HAIR_*` block, i.e. after
line 45 `HAIR_FACE_WINDOW_HALF_X_M = 0.062`):

```python
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
```

**3. New palette entry** (`TOON_PALETTE`, after line 66
`"hair_plum_solid": "#6B2D5B",`):

```python
    "hair_plum_solid": "#6B2D5B",
    "hair_magenta_accent": "#C43B8C",  # alias of existing hair_magenta; see note below
```

Color choice note: I considered the sheet's raw swatch magenta (`#F51496`)
but the existing `hair_magenta` token (`#C43B8C`, line 65) is *already* a
muted raspberry/magenta that visually matches how the streaks read in
`face_zoom.png` (blended into dark curls, not pure-saturated) — and it's
already load-bearing in `_hair_crown_mask`'s QA tolerance (lines 1936-1941,
tolerance `0.14`). Reusing it exactly (rather than introducing a new hex)
means the color-coverage QA gates need **zero threshold changes** — see
`verification`. I'm adding `hair_magenta_accent` as an explicit alias purely
so the new material's intent is named clearly in `MATERIAL_TINT`; it is not
a new color.

**4. New `MATERIAL_TINT` entry** (after line 92
`"MAT_AVERY_HAIR_PLUM": ("hair_plum_solid", "hair_plum_solid"),`):

```python
    "MAT_AVERY_HAIR_PLUM": ("hair_plum_solid", "hair_plum_solid"),
    "MAT_AVERY_HAIR_MAGENTA": ("hair_magenta_accent", "hair_magenta_accent"),
```

**5. `ensure_toon_paint_materials()`** (`:688-710`) — keep the magenta hair
material in sync the same way `hair_plum` already is:

```python
# before
    hair_plum = _material_or_basic(v3, "MAT_AVERY_HAIR_PLUM", "hair_plum_solid")
    hair_black = _material_or_basic(v3, "MAT_AVERY_HAIR", "hair_black")
    for material, token in (
        (navy, "navy"),
        (white, "white"),
        (teal, "teal"),
        (hair_plum, "hair_plum_solid"),
        (hair_black, "hair_black"),
    ):
        material.diffuse_color = rgba(TOON_PALETTE[token])
    return {
        "skin": skin,
        "navy": navy,
        "white": white,
        "teal": teal,
        "hair_plum": hair_plum,
        "hair_black": hair_black,
    }

# after
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
```

**6. `fix_hair_materials()`** (`:470-477`) — flat-unlit both hair materials:

```python
# before
def fix_hair_materials() -> None:
    plum = bpy.data.materials.get("MAT_AVERY_HAIR_PLUM")
    if plum:
        insert_flat_unlit(plum, palette_color("hair_plum_solid"))
        plum.use_backface_culling = False
    hair = bpy.data.objects.get("GEO_AVERY_HAIR")
    if hair:
        configure_hair_render_flags(hair)

# after
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
```

**7. Wavy clip boundary** — replace `_in_hair_face_window`
(`:1158-1165`) with a jittered version. Because `validate_hair_not_curtain`
(`:1168-1194`) calls this *exact same function* against the already-clipped
mesh, whatever boundary shape it defines is enforced identically at build
time and validate time — the "no vertex remains in the window" invariant
stays mathematically exact regardless of the jitter shape, so this is
zero-risk against that gate by construction:

```python
# before
def _in_hair_face_window(world: Vector, brow_z: float) -> bool:
    """Face opening only: forward of the brow plane, below the brow, and
    within the face's half-width. Temple and side volume stay."""
    return (
        world.y < BROW_PLANE_Y
        and world.z < brow_z
        and abs(world.x) < HAIR_FACE_WINDOW_HALF_X_M
    )

# after
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
```

**8. New puff-cluster helpers** (place near `_bmesh_face_islands`,
`:1117-1136`):

```python
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
    the deliberate cheap-clump technique, not the old literal-split bug.
    Supersedes both the old exact-one-island check and
    `_hair_island_split_left_right` (which assumed <=2 islands and would
    false-positive on an intentionally multi-island puff cluster)."""
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
```

**9. `build_solid_afro_mesh()` rewrite** (`:1215-1340`). Keep the head-metric
sizing exactly as-is (lines 1215-1237 unchanged — this is what fixed the
bald-crown bug and must not regress); change the sphere construction, the
clip-validation block, and the material assignment:

```python
# before (lines 1239-1254)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm,
        u_segments=HAIR_SPHERE_SEGMENTS,
        v_segments=HAIR_SPHERE_SEGMENTS // 2,
        radius=1.0,
    )
    for vert in bm.verts:
        vert.co.x *= radius_x
        vert.co.y *= radius_y
        vert.co.z *= radius_z

    mesh = bpy.data.meshes.new("GEO_AVERY_HAIR_MESH")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

# after
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm,
        u_segments=HAIR_SPHERE_SEGMENTS,
        v_segments=HAIR_SPHERE_SEGMENTS // 2,
        radius=1.0,
    )
    max_radius = max(radius_x, radius_y, radius_z)
    cap_faces: list[bmesh.types.BMFace] = list(bm.faces)
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
    brow_z_local = AFRO_MASS_CENTER_Z_M  # placeholder; real brow_z computed below
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
```

```python
# before (lines 1263-1284)
    brow_z = bone_loc.z + HAIR_BROW_Z_OFFSET_M
    bm = bmesh.new()
    bm.from_mesh(hair.data)
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

    islands = _bmesh_face_islands(bm)
    if len(islands) != 1:
        bm.free()
        raise RuntimeError(f"hair must be one mesh island, found {len(islands)}")
    if _hair_island_split_left_right(bm, matrix):
        bm.free()
        raise RuntimeError("hair mesh split into separate left and right islands")

# after
    brow_z = bone_loc.z + HAIR_BROW_Z_OFFSET_M
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    bm.faces.ensure_lookup_table()
    # Carry the streak-face tagging through the from_mesh round-trip via a
    # face integer layer (face order is preserved by from_mesh/to_mesh).
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
```

> Note on the `streak_face_indices` plumbing: `bm.to_mesh(mesh)` then a fresh
> `bm.from_mesh(hair.data)` preserves polygon order (Blender's mesh I/O does
> not reorder faces), so `face.index` on the second bmesh lines back up with
> the `streak_faces` indices captured from the first. This is simpler than
> threading a custom data layer through the mesh roundtrip, but it is an
> implementation detail worth a one-line assert in the real patch
> (`len(mesh.polygons) == len(streak_face_indices | ...)`-style sanity check)
> — flagging this as the one piece of the plumbing I'd actually want to
> watch in a real Blender run rather than reason about statically.

```python
# before (lines 1286-1332, the post-clip validation + smoothing + material block)
    # The old gate compared the hair to its own highest vertex, so it passed
    # even with a bald crown. Measure against the scalp instead.
    hair_top_z = max((matrix @ vert.co).z for vert in bm.verts)
    if hair_top_z < scalp_top + AFRO_CROWN_CLEARANCE_M * 0.5:
        bm.free()
        raise RuntimeError(...)
    # And that it actually sits over the crown, not only behind it.
    over_crown = [...]
    if not any(co.z > scalp_top for co in over_crown):
        bm.free()
        raise RuntimeError(...)

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
    hair.data.materials.clear()
    hair.data.materials.append(plum)
    for polygon in hair.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True

# after
    # (hair_top_z / over_crown checks unchanged -- keep verbatim)
    hair_top_z = max((matrix @ vert.co).z for vert in bm.verts)
    if hair_top_z < scalp_top + AFRO_CROWN_CLEARANCE_M * 0.5:
        bm.free()
        raise RuntimeError(
            f"hair crown does not clear scalp: hair_top={hair_top_z:.4f} "
            f"scalp_top={scalp_top:.4f} "
            f"required>={scalp_top + AFRO_CROWN_CLEARANCE_M * 0.5:.4f}"
        )
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
```

Everything after this point (vertex groups, `v3.add_armature`,
`ensure_armature_deform`, `configure_hair_render_flags`,
`validate_hair_not_curtain(hair)` call, print statements) is **unchanged** —
all of it already operates on "all of `hair.data.vertices`" generically and
doesn't assume a single material or a single topological island.

---

## verification

What needs to pass, and why I expect it to without threshold changes:

- **`validate_hair_not_curtain`** (`:1168-1194`, called both inside
  `build_solid_afro_mesh` and again in `main()` before `render_toon_set`):
  the no-vertex-in-window check is self-consistent by construction (same
  `_in_hair_face_window` predicate used to clip and to validate — see point
  7 above). Crown-clearance and crown-center checks are untouched by the
  puff/noise additions (main cap construction for those regions is
  unchanged) and can only go up, never down, since puffs/noise are purely
  additive on top of the same cap. **No threshold change.**
- **`verify_hair_plate`** (`:1955-1996`) and **`_hair_crown_mask`**
  (`:1926-1942`): the mask already matches *both* `hair_plum_solid` and
  `hair_magenta` as "hair" pixels. Since the new magenta material reuses
  that exact hex (`#C43B8C`, aliased as `hair_magenta_accent`), streak
  clumps are counted identically to plum by every coverage floor
  (`crown`, `plum_center`) and ceiling (`cheek_plum`, `eye_plum`) check.
  Puffs are placed with `AFRO_PUFF_MIN_PHI_DEG = 15` / `MAX = 100`, biased
  to crown/upper-side/back, which should only *add* to the crown/
  crown-center floors (good) and shouldn't meaningfully move the cheek
  ceiling since puffs stay off the lower-forward hemisphere where the
  cheek sample boxes sit (`width 0.30-0.40` / `0.60-0.70`,
  `height 0.19-0.27`). **No threshold change proposed**, but this is the
  one gate I'd actually watch on the first real render: if the temple
  fringe puffs (which deliberately sit near the window edge, closer to the
  cheek region than the other puffs) push `cheek_plum` toward the existing
  `0.60` ceiling, shrink `HAIR_TEMPLE_FRINGE_RADIUS_M` or
  `HAIR_TEMPLE_FRINGE_PAIRS` rather than loosen the gate — the ceiling
  itself ("hair must not cover the cheeks") is still a true requirement of
  the style, independent of this change.
- **`verify_hair_side_profile`** (`:1999-2039`): the active checks (daylight
  gap, crown/back-hair-present floor) depend on overall footprint
  (`AFRO_WIDTH_RATIO`/`AFRO_DEPTH_RATIO`/clearance), which are untouched.
  Two of its checks (`plum > 1.05`, nose/profile-eye) are numerically
  unreachable against a `[0,1]` mean-fraction value and were already dead
  before this change — not something I'm touching, flagging only because
  the prompt asked whether geometry changes require threshold updates, and
  these particular ones can't be tripped either way. **No threshold
  change.**
- New build-time self-check `_hair_islands_overlap_cluster` replaces the old
  `len(islands) != 1` / `_hair_island_split_left_right` pair, which were
  calibrated for "exactly one blob, or a literal 2-piece left/right split"
  and would misfire (near-certain false positive) against an intentionally
  multi-island puff cluster — see `scope`.

Recommended first pass: run the build once, then specifically inspect
`crown_part`/`cheek_l`/`cheek_r`/`eye_plum` numbers (the gates already print
their measured fraction in the failure message) against the new render
before assuming the constants above are final. I'd expect `AFRO_PUFF_COUNT`,
`AFRO_STREAK_PUFF_FRACTION`, and the temple fringe sizing to need one or two
rounds of visual tuning — they're reasoned from scale, not measured.

## scope

- **Render time**: negligible. Main cap is unchanged (`HAIR_SPHERE_SEGMENTS
  = 48`, ~1,150 quads). Each puff is `AFRO_PUFF_SEGMENTS = 10` (~40 quads),
  times `AFRO_PUFF_COUNT = 11` plus 4 temple-fringe puffs at slightly lower
  res — roughly 600 additional quads total, well under 1% of the full
  character's triangle budget. No new shaders, no raytracing-heavy nodes
  (both materials stay `insert_flat_unlit`, an `Emission` node — cheapest
  possible shader).
- **QA gate thresholds**: no numeric threshold changes proposed anywhere
  (see `verification`). One build-time *invariant* changes (island-count
  check -> cluster-overlap check) but that's internal to the builder, not
  one of the three named pixel-based QA gates, and has no caller outside
  `build_solid_afro_mesh` (confirmed via `graft grep` — both
  `_bmesh_face_islands` and `_hair_island_split_left_right` have exactly one
  caller each, both inside this function).
- **Other functions reading `GEO_AVERY_HAIR`'s single-material assumption**:
  checked every reference to `GEO_AVERY_HAIR`/`MAT_AVERY_HAIR_PLUM` in the
  file (`grep -n`). None of the other call sites
  (`configure_hair_render_flags`, `purge_plate_hair_assets`,
  `delete_clothing_meshes`, `render_toon_set`, `validate_hair_not_curtain`,
  armature/vertex-group setup) index into `hair.data.materials` by position
  or assume a material count — they all operate on the object or on "all
  vertices" generically. The two places that *do* reference
  `MAT_AVERY_HAIR_PLUM` by name outside the builder
  (`ensure_toon_paint_materials` at `:693`, `MATERIAL_TINT` at `:92`) are
  both updated above to add the matching `MAT_AVERY_HAIR_MAGENTA` entry so
  they stay in sync.
- **Single-object invariant preserved**: `delete_clothing_meshes` (`:669-676`)
  removes any object matching `GEO_AVERY_HAIR*` except the exact name
  `GEO_AVERY_HAIR`. This is why the proposal merges cap + puffs + fringe
  into **one bmesh -> one mesh datablock -> one object** named
  `GEO_AVERY_HAIR`, rather than separate puff objects — multiple objects
  would be silently deleted by that cleanup pass (and would also require
  reworking the armature-binding and render-flag code, which all assume one
  object).
- **Not in scope / explicitly deferred**: the pulled-back pouf/bun topology
  (see scoping decision above — no back view is rendered, not worth the
  added geometric risk); re-tuning `AFRO_WIDTH_RATIO`/`AFRO_DEPTH_RATIO`/etc
  (left as-is, already calibrated against `media/avery-flat/front.png`);
  fixing the two dead/unreachable `verify_hair_side_profile` checks (noted,
  not touched, out of scope for a hair-shape change).
