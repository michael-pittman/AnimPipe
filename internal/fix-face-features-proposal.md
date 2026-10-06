# Blank face on Avery toon render — diagnosis + proposed fix

Scope: `docs/avery-toon/build_avery_toon.py` only. Nothing in
`docs/avery-chen/` is touched by the proposed diffs (see `root_cause` for why
that file is ruled out as the origin).

## symptom

`media/avery-toon/full-body-front.png` (the render the user just produced)
shows a face with **no visible eyes, iris, pupil, eyebrows, nose shading, or
mouth** — flat skin-tone under the glasses frame, which itself *does* render
correctly (its thin dark outline is clearly visible). The target style sheet
("Patty Patties") shows almond eyes with iris/pupil, dark eyebrows, and a
lip/mouth with a slight smile.

## evidence

**1. `fix_facial_materials()` is the *only* toon-side code that ever touches
these four objects.** An exhaustive regex grep of the whole file for
`GEO_AVERY_EYES|GEO_AVERY_IRISES|GEO_AVERY_PUPILS|GEO_AVERY_BROWS|GEO_AVERY_CORNEAS`
returns exactly two symbols: `fix_facial_materials` (`build_avery_toon.py:480-496`,
which names all four plus `GEO_AVERY_GLASSES`) and the module-level
`SCRAP_OBJECTS` set (`build_avery_toon.py:405-...`, which contains only
`GEO_AVERY_CORNEAS` and `GEO_AVERY_LENSES` — intentionally hidden, not these
four). Nothing else in the toon file hides, deletes, reparents, or rescales
them.

**2. `fix_facial_materials()` runs, unconditionally, as the last
face-object-touching statement before every render.** In `main()`
(`build_avery_toon.py:2111-2214`) it is called at line ~2127 (right after
`postprocess_toon_cohesion`) and again at line ~2168, immediately before
`render_paths = render_toon_set(v3, render_dir)` — nothing runs in between
that references these object names (confirmed by evidence #1). So at the
moment the renderer runs, `GEO_AVERY_EYES/IRISES/PUPILS/BROWS` are
unconditionally `hide_render = False`, `hide_viewport = False`,
`scale = (1, 1, 1)` (`build_avery_toon.py:486-496`).

**3. These objects definitely exist.** `rebuild_eyes_and_brows()`
(`docs/avery-chen/build_avery_chen.py:722-829`, identical in
`docs/avery-chen/scripts/build_avery_chen.py:722-829`) opens with
`eyes = bpy.data.objects["GEO_AVERY_EYES"]` — a hard bracket index, not
`.get()`. If that object were missing this would raise `KeyError` and abort
the whole pipeline before any render was produced. The user got a complete
full-body-front.png, so `build()` ran this function to completion, which also
means `GEO_AVERY_IRISES`, `GEO_AVERY_PUPILS`, `GEO_AVERY_CORNEAS` (via
`make_iris_mesh`, `build_avery_chen.py:667-719`) and `GEO_AVERY_BROWS`
(`build_avery_chen.py:812-829`) were all freshly built without error.

**4. Deletion by the clothing/hair purges is ruled out.**
`delete_clothing_meshes()` (`build_avery_toon.py:669-676`) only matches
`REMOVE_CLOTHING_EXACT` / `REMOVE_CLOTHING_PREFIXES`
(`build_avery_toon.py:647-666`) — neither list contains anything that matches
`GEO_AVERY_EYES`, `_IRISES`, `_PUPILS`, or `_BROWS`. `purge_plate_hair_assets()`
(`build_avery_toon.py:1061-1071`) only matches `GEO_AVERY_HAIR*`.

**5. QA-suppression is ruled out.** `main()`'s failure filter
(`build_avery_toon.py:2153`, `if "implausibly low" not in failure and
"triangle budget" not in failure`) looked suspicious — but the only place
that string is ever produced is
`docs/avery-chen/build_avery_chen.py:2405`:
`f"triangle count {triangles} is implausibly low for coherent base"` — a
whole-scene mesh-budget sanity check, unrelated to per-feature visibility.
There is no suppressed "pupil/brow visibility" failure; `validate_scene()`
(`build_avery_chen.py:2282-2423`) only checks that the shape keys and driven
owners *exist*, never that they're visually legible.

**6. The bone-parenting mechanism itself is not broken.**
`GEO_AVERY_IRISES`/`_PUPILS`/`_CORNEAS` (via `make_iris_mesh`,
`build_avery_chen.py:719`) and `GEO_AVERY_BROWS`
(`build_avery_chen.py:829`) are attached with the exact same
`parent_bone(obj, "head")` helper (`build_avery_chen.py:181-186`) as
`GEO_AVERY_GLASSES` (`build_avery_chen.py:1002`) — and the glasses frame is
the one facial feature that *does* render correctly in the user's screenshot.
Same mechanism, same build() call, same bone, same point in the pipeline —
one works, the rest don't, so the parenting code is not the differentiator.

**7. Material color/alpha is ruled out.** `insert_flat_unlit()`
(`build_avery_toon.py:172-187`) unconditionally clears the material's node
tree and rebuilds it as a single opaque `ShaderNodeEmission` wired straight
to the output — `palette_color()` (`build_avery_toon.py:152-153`) always
returns alpha `1.0` (via `rgba()`'s default, `build_avery_toon.py:142-149`).
There's no transparency node in this chain at all, so this is not a
translucency/alpha bug (I initially suspected `basic_material()`'s third
positional argument was alpha — it's actually `roughness`,
`build_avery_chen.py:200-230` — so the `0.24-0.52` values in
`material_library()`, `build_avery_chen.py:2117-2127`, are glossiness, not
transparency; this red herring is noted here so it isn't re-investigated).
The sclera/iris/skin palette colors are also high-contrast
(`#F3EBE4` / `#3D2418` / `#8F5E47`), so this isn't a
too-close-to-skin-tone problem either.

**8. The shared face-building code is independently proven correct.**
`internal/v3-face-qa.md` is a sha256-pinned QA pass
(`751fd058…`) of a render built from the *exact same*
`docs/avery-chen/build_avery_chen.py` that the toon pipeline loads via
`load_v3_builder()` (`build_avery_toon.py:115-120`) — it explicitly calls the
`eye-brow-matrix.png` sheet (pupils, brows, gaze, blink) "gold standard" and
reports 0% enamel/white leakage. `patch_v3_for_toon()`
(`build_avery_toon.py:306-402`) only monkey-patches clothing/sleeve functions
(`soften_armscye_edges`, `open_jacket_front`, `build_jacket_lapels`,
`sleeve_mesh`, `raglan_shoulder`, `make_loft`) — it never touches
`sculpt_integrated_face`, `rebuild_eyes_and_brows`, `make_iris_mesh`, or
`paint_skin`. So the face-geometry-and-placement code the toon pipeline runs
is byte-for-byte the same code that is independently verified to produce a
visible, correctly-placed, QA-passed face. This rules out `avery-chen` as the
origin and is why the proposed fix stays entirely inside
`docs/avery-toon/build_avery_toon.py`.

**9. No QA gate would have caught this.** `verify_front_render()`
(`build_avery_toon.py:1861-1885`) only checks overall silhouette continuity
against the ground color — it has no notion of a face at all.
`verify_expression_eyes()` (`build_avery_toon.py:2042-2063`) only measures
"hair over eyes" fraction via `_magenta_on_eyes` — a **blank** face (no eye
color at all) trivially passes this, since there's no magenta/hair pixel
sampled either. This is why the bug shipped silently.

**10. Mouth/lips: confirmed absent, not merely hidden.** Grepping the whole
toon file for `lip|mouth` (case-insensitive) turns up exactly: the palette
entry `"lip": "#8B5348"` (`build_avery_toon.py:81`) and two `MATERIAL_TINT`
entries, `MAT_AVERY_GUM`/`MAT_AVERY_TONGUE` → `("lip", "skin_shadow")`
(`build_avery_toon.py:107-108`) — both interior-mouth materials
(`rebuild_dental`, `build_avery_chen.py:856-940`) that sit behind a closed
mouth and are never meant to be visible at rest. There is no
`GEO_AVERY_MOUTH`/`GEO_AVERY_LIPS` object and no face-paint step for lips.
The base V3 sculpt does shape a closed-lip silhouette and
`paint_skin()` (`build_avery_chen.py:611-664`) does write a `lip`-toned
per-vertex color into the `AVERY_SKIN_COLOR` attribute over the lip vertex
group — but `convert_material_to_cel()`'s `MATERIAL_TINT` entry for
`MAT_PROXY_CHARACTER` (`build_avery_toon.py:86`) routes the whole head
material through `insert_cel_on_material()`, whose diffuse node reads a
single hardcoded `base_rgba` (`build_avery_toon.py:220`) — there is no
`ShaderNodeAttribute` anywhere in that chain reading `AVERY_SKIN_COLOR`. So
even the one per-vertex lip-tone cue that *does* exist in the data is
discarded by the toon cel conversion. The mouth is genuinely blank, not just
occluded.

## root_cause

**I could not pin this down to one mechanistic line** — there is no Blender
available in this environment to inspect the live, depsgraph-evaluated scene
(exact world-space position of the iris/pupil/sclera/brow meshes relative to
`GEO_AVERY_HEAD`'s evaluated surface at render time), and every *toon-side*
mutation of `GEO_AVERY_HEAD` or the scene between `v3.build()` returning and
the render (`ensure_armature_deform`, `paint_body_wardrobe` →
`paint_mesh_wardrobe(head, ..., preserve_face_skin=True)`, the EEVEE engine
switch in `setup_toon_render`, `build_avery_toon.py:1651-1708`) is a
*plausible* place for a depth/visibility regression to be introduced, but I
have no way to confirm which one actually does it from static reading alone.

What evidence #1-#9 above *does* establish with high confidence:
- the objects exist, are unhidden, and are at unit scale at render time;
- they are not deleted, misnamed, or mis-parented by anything toon-specific;
- their materials are opaque and high-contrast;
- the identical geometry-and-placement code is independently proven correct
  in the non-toon V3 pipeline.

That combination means the fault is a **toon-only rendering/visibility
regression** — most likely the already-small depth margins these decal
meshes were built with (sub-millimeter to low-single-millimeter offsets off
the head surface — e.g. the iris "dome" bias is `0.00065` m, see
`make_iris_mesh`, `build_avery_chen.py:681`) are being eaten by *something*
in toon-only postprocessing or the EEVEE render path, pushing the opaque
head surface in front of (or exactly coincident with) geometry that used to
clear it. I'm stating this as the leading hypothesis, not a confirmed cause.

## confidence

**Medium** on localization (toon-only postprocessing or render-engine
behavior in `build_avery_toon.py`, not the shared `avery-chen` geometry
code) — backed by evidence #1-#9, each independently checkable.
**Low** on the exact mechanism within that scope — I was not able to execute
Blender to inspect the evaluated scene, so I cannot name the single
responsible line with certainty. The proposed fix below is deliberately
split into (a) a zero-risk diagnostic that will tell the human exactly what's
happening on the next real render, and (b) a conservative, idempotent
corrective nudge that helps regardless of which specific toon-side step is
eroding the depth margin — plus the mouth/lips addition, which *is* high
confidence (evidence #10 is a direct code-absence proof, not an inference).

## proposed_change

All changes are in `docs/avery-toon/build_avery_toon.py`.

### 1. Diagnostics + a conservative, idempotent forward nudge on the face decals

Replace `fix_facial_materials()` (`build_avery_toon.py:480-496`):

```python
# before
def fix_facial_materials() -> None:
    insert_flat_unlit(bpy.data.materials["MAT_AVERY_SCLERA"], palette_color("sclera"))
    insert_flat_unlit(bpy.data.materials["MAT_PROXY_FOCUS"], palette_color("iris"))
    insert_flat_unlit(bpy.data.materials["MAT_AVERY_PUPIL"], palette_color("hair_black"))
    insert_flat_unlit(bpy.data.materials["MAT_AVERY_FRAME"], palette_color("graphite"))
    for obj_name in (
        "GEO_AVERY_EYES",
        "GEO_AVERY_IRISES",
        "GEO_AVERY_PUPILS",
        "GEO_AVERY_GLASSES",
        "GEO_AVERY_BROWS",
    ):
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.hide_render = False
            obj.hide_viewport = False
            obj.scale = (1.0, 1.0, 1.0)
```

```python
# after
# Micro-geometry (eyes/iris/pupil/brows) was built against sub-millimeter
# clearance off the head surface (make_iris_mesh's dome bias is 0.00065 m,
# docs/avery-chen/build_avery_chen.py:681). The toon pipeline adds steps the
# base V3 pipeline doesn't run (armature-modifier re-attach, EEVEE instead of
# whatever engine produced the verified-good internal/v3-face-qa.md render) —
# any of those can erode that margin and let the opaque head swallow these
# objects with no error raised anywhere. This nudges them a conservative,
# fixed amount toward the camera (forward_axis is "-Y", set in
# docs/avery-chen/build_avery_chen.py's build()) so marginal occlusion clears,
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
```

(`MAT_AVERY_MOUTH`/`GEO_AVERY_MOUTH` are created by the new
`build_mouth_decal()` in change 3 below; the `.get()` guard keeps this
function safe to call before that object exists.)

Also add `"MAT_AVERY_MOUTH"` to the exclusion set in
`convert_material_to_cel()` (`build_avery_toon.py:265-272`) so
`convert_all_materials_to_cel()` doesn't clobber its flat-unlit look on its
first pass each run:

```python
# before
    if name in {
        "MAT_AVERY_SCLERA",
        "MAT_PROXY_FOCUS",
        "MAT_AVERY_PUPIL",
        "MAT_AVERY_FRAME",
        "MAT_AVERY_CHEST_BAND_WHITE",
        "MAT_AVERY_CHEST_BAND_TEAL",
    }:
        return
```

```python
# after
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
```

### 2. New QA gate that actually looks at the face

Neither existing gate (`verify_front_render`, `verify_expression_eyes`)
samples for eye/iris color at all (evidence #9). Add a gate that does, and
wire it into `main()` alongside the other `verify_*` calls
(`build_avery_toon.py:2140-2150` region, same pattern as `verify_wave_sleeve`
etc.):

```python
def verify_face_features(path: Path) -> tuple[bool, str]:
    """full-body-front.png must show actual eye color, not just a
    QA-passing blank oval. verify_front_render only checks silhouette
    continuity and verify_expression_eyes only checks hair-over-eyes —
    neither would catch a fully blank face (this is how the bug shipped)."""
    if not path.is_file():
        return False, "missing full-body-front.png"
    rgb = _read_render_rgb(path)
    height, width = rgb.shape[:2]
    # NOTE: this window is a first estimate off the full-body front framing
    # used by render_toon_set; calibrate the fractions against an actual
    # render before trusting this as a hard gate, same as the crown/chest
    # floors in internal/avery-toon-crown-band-fix.md were tuned against a
    # real bad render rather than guessed.
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
```

Wire-up (inside `main()`, right after the existing `ok, render_detail =
verify_front_render(front)` block, `build_avery_toon.py:~2140`):

```python
        ok_face, face_detail = verify_face_features(front)
        if not ok_face:
            raise RuntimeError(f"face QA failed: {face_detail}")
```

### 3. Add the mouth/lips decal (new geometry — the gap is real, per evidence #10)

A small flat, cel-painted mouth shape, built the same way
`GEO_AVERY_IRISES`/`GEO_AVERY_PUPILS` are (a tiny standalone mesh,
`parent_bone`'d to the `"head"` bone, flat-unlit material) rather than trying
to paint it onto the head's single cel material (which has no per-vertex
color input once `insert_cel_on_material` runs — evidence #10). Placement
reuses the lip-region bounds `sculpt_integrated_face` falls back to when no
`lips` vertex group is present (`abs(x) < 0.055`, `1.505 < z < 1.555`,
`build_avery_chen.py:465-469`), centered, with a slight upward curve at the
corners for the "slight smile" the style sheet shows.

Add near `make_iris_mesh`-equivalent toon helpers (e.g. after
`ensure_toon_paint_materials`, `build_avery_toon.py:710`):

```python
def build_mouth_decal(v3) -> bpy.types.Object | None:
    """Flat mouth mark. The base V3 head sculpts a closed lip silhouette and
    paints a lip tone into a per-vertex color attribute (paint_skin,
    docs/avery-chen/build_avery_chen.py:611-664), but the toon cel pass
    overwrites the whole head material with one flat color and never reads
    that attribute (insert_cel_on_material, build_avery_toon.py:190-256) —
    so at rest the mouth reads as blank skin. This adds a small, legible
    flat mouth shape, same pattern as GEO_AVERY_IRISES/GEO_AVERY_PUPILS."""
    existing = bpy.data.objects.get("GEO_AVERY_MOUTH")
    if existing:
        return existing
    mat = bpy.data.materials.get("MAT_AVERY_MOUTH")
    if mat is None:
        mat = v3.basic_material("MAT_AVERY_MOUTH", TOON_PALETTE["lip"], 1.0)
    insert_flat_unlit(mat, palette_color("lip"))

    half_width = 0.016
    corner_rise = 0.0017    # corners lift slightly: a small smile, not neutral
    thickness = 0.0022
    z_center = 1.5245       # mid lip band, consistent with sculpt_integrated_face's fallback lip z-range
    y = -0.1247              # just proud of the iris/cornea plane (-0.1214 to -0.12305) so it clears the head surface

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
```

Call it once from `postprocess_toon_cohesion()`
(`build_avery_toon.py:1569-1608`), right after materials are available:

```python
# before
    materials = ensure_toon_paint_materials(v3)
    body = bpy.data.objects.get("GEO_AVERY_BODY")
```

```python
# after
    materials = ensure_toon_paint_materials(v3)
    build_mouth_decal(v3)
    body = bpy.data.objects.get("GEO_AVERY_BODY")
```

`fix_facial_materials()` (change 1) already re-applies the flat-unlit
material and unhide/scale-reset to `GEO_AVERY_MOUTH` on every subsequent
call, matching how the other facial decals are kept correct across the
pipeline's three `fix_facial_materials()` calls.

## verification

On the next real Blender run:

1. **Read the new `face-diag` console lines** (from
   `_log_face_depth_diagnostics`, printed once per `fix_facial_materials()`
   call, i.e. 3× per run). For each of `GEO_AVERY_EYES/IRISES/PUPILS/BROWS`
   plus `GEO_AVERY_HEAD`, compare the printed `y` range at the final call —
   if a decal's `y` range is *less negative* than (i.e. sits behind) the
   head's `y` at the same region, that confirms the occlusion hypothesis
   directly and tells us how much more nudge is needed, or that a different
   mechanism (collection exclusion, a stray modifier) is actually at play.
2. **Open `full-body-front.png`** and confirm: a cream-white sclera patch
   behind each glasses lens, a visibly darker iris/pupil dot inside it, a
   thin dark brow stroke above each glasses lens, and a small lip-colored
   mark at the mouth with a slight upward curve.
3. **Confirm the new `verify_face_features` gate passes** (or, if it fails
   even though the render now looks correct, recalibrate its sample-window
   fractions against this render rather than loosening the thresholds
   blindly — same approach this repo already documents in
   `internal/avery-toon-crown-band-fix.md`).
4. If the face is still blank after the nudge, the `face-diag` log from step
   1 should make the actual cause legible without another round of guessing.

## scope

- Touches only `docs/avery-toon/build_avery_toon.py`. `docs/avery-chen/` (both
  `build_avery_chen.py` and `scripts/build_avery_chen.py`) and `docs/avery-2d/`
  are untouched — consistent with evidence #8 that the shared geometry code
  is already proven correct and this is a toon-only regression.
- New custom properties (`AVERY_TOON_FACE_NUDGED`) are written onto the
  affected objects' ID data; harmless, but will persist into the saved
  `.blend` — worth knowing if anything elsewhere ever iterates
  `obj.keys()`/custom properties on these objects (nothing currently does,
  per the exhaustive grep in evidence #1).
- The new `GEO_AVERY_MOUTH` object adds one more name to any future
  "every `GEO_AVERY_*` object" loops (e.g. `restore_v3_humanoid`,
  `build_avery_toon.py:425-438`, already handles it generically via the
  `GEO_AVERY` prefix match) and to `avery-2d`'s `validate_scene()` legacy-name
  check (`docs/avery-2d/build_avery_2d.py`) only if avery-2d ever imports
  toon output directly, which it does not appear to today.
- `verify_face_features`'s sample window is a first estimate and explicitly
  flagged as needing calibration against a real render before being trusted
  as a hard failure gate — don't let it block a build on an untuned window.
