# Avery Toon wardrobe fix — diagnosis + proposal

Target: match `media/.../images/7.png` ("Patty Patties" federal-employee style
sheet) more closely than the current render (`images/6.png`, plain closed navy
sweater + floating white/teal sticker + olive pants, no accessories).

All line numbers below are against `docs/avery-toon/build_avery_toon.py` as it
exists on disk right now (verified by reading the file directly, not assumed
from the task brief). Everything the task brief asserted was re-checked and
confirmed accurate except where noted.

Architecture confirmed from `docs/avery-toon/README.md` "Look (toon pass)"
section and from code: wardrobe is **painted onto `GEO_AVERY_BODY` face
material slots** (navy/white/teal, 4 slots total incl. skin). There is no
`GEO_AVERY_JKT_*` or `GEO_AVERY_SHIRT_*` mesh in the shipped render —
`delete_clothing_meshes()` (L669‑676) removes any such object every build, and
`verify_no_clothing_meshes()` (L2066‑2070) hard-fails the build if one
survives. **Any fix must work by repainting regions and/or adding small
independent accessory/trim meshes — not by building a jacket garment mesh.**

---

## Sub-issue 1 — jacket reads as a closed sweater, no open front

**Symptom:** navy top is a single flat closed shape, no collar gap, no visible
opening, no lapels.

**Evidence:**
- `patch_v3_for_toon()` L306‑310: stubs `v3.soften_armscye_edges`,
  `v3.open_jacket_front`, and `v3.build_jacket_lapels` to no-ops, *before*
  `v3.build()` runs (called from `main()` L2111‑2126). Confirmed exact text:
  ```python
  def patch_v3_for_toon(v3) -> None:
      """Keep V3 humanoid topology closed; sleeves skinned from body, not tube lofts."""
      v3.soften_armscye_edges = lambda obj: None
      v3.open_jacket_front = lambda obj: None
      v3.build_jacket_lapels = lambda materials: None
  ```
- `open_jacket_front_on_shell()` (L503‑520) and `build_jacket_outer_shell()`
  (L620‑634) do exist and do implement "cut a front hole in a shell mesh",
  but **`graft_trace_calls` confirms zero callers of `build_jacket_outer_shell`
  anywhere in the indexed repo** — it is dead code. Even if it were called,
  the shell it builds is named `GEO_AVERY_JKT_SHELL`, which
  `delete_clothing_meshes()` (`REMOVE_CLOTHING_EXACT`, L660‑661) deletes on
  every build, and `verify_no_clothing_meshes()` would fail the build if it
  weren't deleted. **This mechanism is not just unused, it is structurally
  incompatible with the current paint-only architecture.** Do not revive it.
- `build_jacket_lapels()` *does* exist in the base V3 script
  (`docs/avery-chen/scripts/build_avery_chen.py` L1308‑1339) and builds two
  small standalone meshes (`GEO_AVERY_LAPEL_L/R`), parented to the `chest`
  bone, independent of body topology — it does not loft onto or cut the body
  mesh at all. It is unrelated to the topology concern the stub's docstring
  cites.
- Confirmed `GEO_AVERY_LAPEL_L` / `GEO_AVERY_LAPEL_R` are *also* listed in
  `SCRAP_OBJECTS` (L406‑407), which `restore_v3_humanoid()` (L425‑438) force
  `hide_render = True`. Because `build_jacket_lapels` is stubbed, these
  objects never even get created in the current pipeline, so the
  `SCRAP_OBJECTS` entries are currently inert (hiding something that doesn't
  exist) — **both** the stub and the hide-list entry need to go for lapels to
  actually appear.

**Root cause:** `soften_armscye_edges` and `open_jacket_front` were stubbed
because they operated on `GEO_AVERY_BODY`/sleeve topology in ways that
conflicted with the "closed body mesh, sleeves skinned not lofted" redesign
(see docstring). That redesign is correct and should stay. But
`build_jacket_lapels` was stubbed in the same line for no topology-related
reason — it's an independent accessory mesh, and stubbing it was collateral
damage, not a deliberate decision tied to the topology fix.

Given there is no jacket garment mesh at all, "open front" has to be sold
two ways simultaneously: (a) a visibly narrower band of white at the
collar instead of a floating rectangle (sub-issue 2), and (b) actual lapel
geometry framing the opening on both sides of centerline (this sub-issue).

**Confidence:** High that the stub + dead-code read is accurate. Medium-high
that re-enabling just `build_jacket_lapels` (and leaving the other two
stubbed) is sufficient to read as "open jacket" combined with the band fix
below — this is a visual judgment call that should be checked against the
next render, not just reasoned from code.

**Proposed change:**

1. Stop stubbing `build_jacket_lapels` only (leave the other two stubs intact
   — they protect the body-topology redesign and are unrelated to this fix):

```diff
 def patch_v3_for_toon(v3) -> None:
     """Keep V3 humanoid topology closed; sleeves skinned from body, not tube lofts."""
     v3.soften_armscye_edges = lambda obj: None
     v3.open_jacket_front = lambda obj: None
-    v3.build_jacket_lapels = lambda materials: None
```

2. Remove the now-dead hide entries for the lapels from `SCRAP_OBJECTS`
   (L405‑422) so `restore_v3_humanoid()` stops force-hiding them:

```diff
 SCRAP_OBJECTS = {
-    "GEO_AVERY_LAPEL_L",
-    "GEO_AVERY_LAPEL_R",
     "GEO_AVERY_PATCH_CHEST",
     "GEO_AVERY_PATCH_SLEEVE_L",
     "GEO_AVERY_PATCH_SLEEVE_R",
     "GEO_AVERY_LENSES",
     "GEO_AVERY_CORNEAS",
     "GEO_AVERY_BADGE_BAR_0",
     "GEO_AVERY_BADGE_BAR_1",
     "GEO_AVERY_BADGE_BAR_2",
     "GEO_AVERY_BADGE_CLIP",
     "GEO_AVERY_BADGE_PORTRAIT",
     "GEO_AVERY_LANYARD_BREAKAWAY",
     "GEO_AVERY_BELT_KEEPER",
     "GEO_AVERY_ROLLED_CUFF_L",
     "GEO_AVERY_ROLLED_CUFF_R",
 }
```
(The patch/badge/lanyard entries in this same set are addressed in sub-issue 4
below — shown together there so the diff isn't split across two patches to
the same literal.)

3. Lapels use `materials["utility_navy"]` → `MAT_AVERY_UTILITY_NAVY`, which
   *is* in `MATERIAL_TINT` (L95) so `convert_all_materials_to_cel()` repaints
   it automatically — no new material needed. Optional cohesion tweak: it's
   currently a flat single-tone (`navy_deep`/`navy_deep`), one shade darker
   than the two-tone cel-shaded jacket torso (`navy`/`navy_deep`). Matching
   the torso's tone makes the lapels read as part of the same garment instead
   of a separate darker piece:

```diff
 MATERIAL_TINT = {
     ...
     "MAT_AVERY_JACKET": ("navy", "navy_deep"),
-    "MAT_AVERY_UTILITY_NAVY": ("navy_deep", "navy_deep"),
+    "MAT_AVERY_UTILITY_NAVY": ("navy", "navy_deep"),
     "MAT_AVERY_SHIRT": ("white", "white"),
```
(Low-risk, cosmetic-only; skip if it looks worse in practice.)

**Verification:** Next front/3-quarter render should show two thin navy lapel
flaps flanking the centerline from roughly collarbone to waist, standing
slightly proud of the torso silhouette (lapels have real 3D thickness via
their own geometry, not paint) — this plus the narrowed chest-band gap
(sub-issue 2) should read as "jacket open over a garment underneath" rather
than a single flat sweater shape. If it still reads flat/closed even with
lapels, the next lever is widening the gap between the lapels' inner edges
(currently `side * 0.036`–`side * 0.066` in `build_jacket_lapels`,
`docs/avery-chen/scripts/build_avery_chen.py` L1310‑1319 — a base-V3 file,
see Scope).

---

## Sub-issue 2 — chest band reads as a floating rectangle, not a collar gap

**Symptom:** wide white rectangle with a teal bar sits mid-chest, disconnected
from any collar or opening — looks like a sticker/logo, not a shirt visible
through an open jacket.

**Evidence:**
```python
CHEST_BAND_WHITE_SIZE = Vector((0.18, 0.015, 0.07))   # L46 — 18 cm wide
CHEST_LOOP_BOTTOM = 1.122                              # L54
CHEST_LOOP_TEAL_LOW = 1.188                             # L55
CHEST_LOOP_TEAL_HIGH = 1.206                            # L56
CHEST_LOOP_TOP = 1.288                                  # L57  (≈ base of neck —
                                                          #  NECK_SKIN_Z starts
                                                          #  at 1.288, L723)
```
`build_chest_band_mesh()` (L1515‑1566) builds this as a curved shell
(`_chest_band_shell_mesh`, L1444‑1488) that correctly follows the measured
torso surface now (this was fixed last round per the comment at L1532‑1534 —
no longer an axis-aligned floating slab). But the *shape* is still a constant-
width rectangle 18 cm wide × 16.6 cm tall (`CHEST_LOOP_TOP − CHEST_LOOP_BOTTOM`
= 0.166 m), spanning from mid-chest almost down to the sternum. The style
sheet shows a **narrow strip** of undershirt visible only where the jacket
is open — a few centimeters wide, concentrated right at the collar, not a
banner covering most of the upper torso.

Note `CHEST_LOOP_TOP` (1.288) already sits exactly at the neck/collar
boundary (`NECK_SKIN_Z` starts at 1.288, L723) — the top edge position is
already correct. The problem is **width and vertical extent**, not vertical
placement.

**Root cause:** mis-sized, not structurally wrong. The band-following-surface
mechanism is sound; the authored dimensions (`CHEST_BAND_WHITE_SIZE.x`,
`CHEST_LOOP_BOTTOM`) were set for a different silhouette (a wide crew/henley
placket) and were never revisited for the "narrow gap at an open collar"
read this style sheet needs.

**Confidence:** High on diagnosis. Medium on the exact new numbers below —
they're a reasoned first pass (half the width, half the height, same
relative teal-stripe position within the band), not derived from a render.
Expect one calibration pass.

**Proposed change** — shrink and raise the band, keep the top anchored at the
collar, keep the teal stripe at the same relative position within the band:

```diff
-CHEST_BAND_WHITE_SIZE = Vector((0.18, 0.015, 0.07))
+CHEST_BAND_WHITE_SIZE = Vector((0.07, 0.015, 0.07))
 CHEST_BAND_TEAL_SIZE = Vector((0.18, 0.004, 0.012))
 CHEST_BAND_FRONT_OFFSET_M = 0.010
 CHEST_BAND_TEAL_FRONT_GAP_M = 0.001
 # Band follows the measured torso surface instead of floating as a flat slab.
 CHEST_BAND_ARC_SEGMENTS = 24
 CHEST_BAND_SHELL_DEPTH_M = 0.006
 PREVIEW_RENDERS_USE_FREESTYLE = False
-CHEST_LOOP_BOTTOM = 1.122
-CHEST_LOOP_TEAL_LOW = 1.188
-CHEST_LOOP_TEAL_HIGH = 1.206
+CHEST_LOOP_BOTTOM = 1.205
+CHEST_LOOP_TEAL_LOW = 1.235
+CHEST_LOOP_TEAL_HIGH = 1.250
 CHEST_LOOP_TOP = 1.288
```
This halves both width (18 cm → 7 cm) and height (16.6 cm → 8.3 cm), keeps
`CHEST_LOOP_TOP` fixed at the collar, and keeps the teal stripe at roughly
the same fractional height within the band (was ~40% up from the bottom, now
~36%). All of `_front_torso_material()`, `_fill_navy_above_chest_band()`,
and `_paint_body_chest_band_navy()` reference `CHEST_LOOP_TOP` or hardcoded
literals (1.275, 1.345, 1.365) that are independent of `CHEST_LOOP_BOTTOM` —
confirmed by reading L733‑918 — so **no other function needs to change** for
this resize; they all key off the unchanged `CHEST_LOOP_TOP` or their own
fixed offsets.

**Stretch goal (optional, not included in the diff above):** a true V-taper
(wider at the collar, narrowing to a point lower down, instead of a constant-
width rectangle) would sell "open collar gap" even better. This needs
`_chest_band_shell_mesh` to vary `profile` width by z-band rather than use one
constant `half_width` for the whole shell — e.g. call it twice with two
different `half_width` values for an upper and lower sub-band and stitch them,
or parametrize `_chest_band_front_profile`'s `half_width` as a function of z.
This is a bigger, riskier structural change than the constant resize above;
recommend trying the cheap resize first and only doing this if it still reads
as a rectangle.

**Verification:** `verify_chest_band_front()` (L2073‑2094) is a **hard QA
gate** (`main()` L2197‑2199 raises `RuntimeError` on failure) that samples a
*fixed pixel box* — rows `[0.357h, 0.386h]`, cols `[0.38w, 0.62w]` — and
requires white_frac ≥ 0.40, navy_frac ≤ 0.18, teal_frac ≥ 0.025. That box was
tuned against the *old* (wider/taller) band. After this resize the band's
on-screen position and extent both change, so **this sample box will very
likely need recalibration** — I cannot compute the right numbers from static
analysis alone (they depend on camera framing in the actual render). Treat
this as a required companion change: render once with the new constants,
inspect where the band actually lands in `full-body-front.png`, then tighten
the row/col fractions (probably a narrower, slightly higher row range) before
trusting the gate again. Don't skip this — right now a too-wide fixed window
sampling past the new smaller band's edges will likely false-fail on
`white_frac`.

---

## Sub-issue 3 — pants are olive/khaki instead of navy

**Symptom:** solid olive-green trousers; style sheet shows navy trousers
matching the jacket (flight-suit/jumpsuit silhouette).

**Evidence:**
```python
TOON_PALETTE = {
    ...
    "cargo": "#6E7460",            # L74
    "cargo_shadow": "#545848",     # L75
    ...
}
MATERIAL_TINT = {
    ...
    "MAT_AVERY_TROUSER": ("cargo", "cargo_shadow"),  # L97
    "MAT_AVERY_SOCK": ("cargo", "cargo_shadow"),      # L98
    ...
}
```
`fix_ankle_leg_materials()` (L934‑984) separately repaints the same material
by name, independent of `MATERIAL_TINT`:
```python
cargo_mat = bpy.data.materials.get("MAT_AVERY_TROUSER") or ...
if cargo_mat:
    insert_cel_on_material(cargo_mat, palette_color("cargo"), palette_color("cargo_shadow"))  # L940-944
```
This is **documented, deliberate current design**, not a bug:
`docs/avery-toon/README.md` L38 says *"`GEO_AVERY_TROUSERS` stay olive and
meet navy at the waist"* and L41 says *"olive trousers run into sneakers"*.
`GEO_AVERY_TROUSERS` is confirmed to be a real separate mesh object (not
painted onto `GEO_AVERY_BODY` like the jacket/shirt) — `fix_ankle_leg_materials`
L955 matches `obj.name.startswith("GEO_AVERY_TROUSERS")` and reassigns its
material slot directly, so this is a pure material swap, no geometry change
needed.

**Root cause:** not a bug — `media/avery-flat/front.png` (the prior reference
art this pipeline was built against) shows olive cargo pants, and the code
faithfully reproduces that. The user has now confirmed the *style sheet*
(`images/7.png`, navy trousers) is the real target, which the olive reference
predates or diverged from.

**Confidence:** High — this is a one-line color-token swap, no structural
risk. Checked `verify_front_render`, `verify_wave_sleeve`,
`verify_no_clothing_meshes`, `verify_no_bare_midriff` (the other hard QA
gates) and none of them reference `"cargo"` or sample the leg region for a
specific hue — **this change does not risk breaking any existing QA gate**
(unlike sub-issue 2's chest band resize).

**Proposed change** — repoint the trouser material to the jacket's existing
navy tokens (already near-pixel-identical to the style sheet's `#0E254A` per
the task brief, so no new palette entries needed):

```diff
 MATERIAL_TINT = {
     ...
-    "MAT_AVERY_TROUSER": ("cargo", "cargo_shadow"),
-    "MAT_AVERY_SOCK": ("cargo", "cargo_shadow"),
+    "MAT_AVERY_TROUSER": ("navy", "navy_deep"),
+    "MAT_AVERY_SOCK": ("navy", "navy_deep"),
     ...
 }
```
```diff
 def fix_ankle_leg_materials(v3) -> None:
     """Hide sock/teal/magenta/piping clutter; trousers meet shoes cleanly."""
     cargo_mat = bpy.data.materials.get("MAT_AVERY_TROUSER") or bpy.data.materials.get(
         "MAT_AVERY_SOCK"
     )
     if cargo_mat:
         insert_cel_on_material(
             cargo_mat,
-            palette_color("cargo"),
-            palette_color("cargo_shadow"),
+            palette_color("navy"),
+            palette_color("navy_deep"),
         )
```
The `"cargo"`/`"cargo_shadow"` palette entries (L74‑75) can stay in
`TOON_PALETTE` unused (harmless — no other code references them after this
change) or be deleted; leaving them costs nothing and keeps the diff smaller.

**Verification:** trousers should render navy, matching the jacket tone, with
a visible seam only where paint-navy jacket meets separate-mesh-navy
trousers at the waist (same navy hex on both sides of that seam, so check
`verify_no_bare_midriff`, L2097‑2108, still passes — it only checks for
*skin* color in that band, unaffected by this change, but worth a visual
check that the waistband doesn't disappear into one undifferentiated navy
mass — if it does, consider a slightly darker/lighter navy for trousers vs.
jacket, or rely on the existing belt geometry to break up the silhouette).

---

## Sub-issue 4 — accessories (badge, lanyard, patches, piping) hidden or absent

**Symptom:** no badge, no lanyard, no visible chest/sleeve patches, no
magenta/pink accent color anywhere, no smartwatch, no tablet.

**Evidence — badge/lanyard, already built, explicitly hidden twice:**
1. `postprocess_toon_cohesion()` L1598‑1607 — explicit "clutter" hide loop:
```python
    for clutter in (
        "GEO_AVERY_BADGE",
        "GEO_AVERY_BADGE_PORTRAIT",
        "GEO_AVERY_BADGE_CLIP",
        "GEO_AVERY_LANYARD_L",
        "GEO_AVERY_LANYARD_R",
    ):
        obj = bpy.data.objects.get(clutter)
        if obj:
            obj.hide_render = True
```
2. `SCRAP_OBJECTS` (L405‑422) separately force-hides
   `GEO_AVERY_PATCH_CHEST`, `GEO_AVERY_PATCH_SLEEVE_L/R`,
   `GEO_AVERY_BADGE_BAR_0/1/2`, `GEO_AVERY_BADGE_CLIP`,
   `GEO_AVERY_BADGE_PORTRAIT`, `GEO_AVERY_LANYARD_BREAKAWAY` (plus
   `GEO_AVERY_LAPEL_L/R`, addressed in sub-issue 1) via
   `restore_v3_humanoid()` (L425‑438).

All of this geometry is built unconditionally by `build_accessories()` in the
base V3 script (`docs/avery-chen/scripts/build_avery_chen.py` L1978‑2112,
confirmed not stubbed by `patch_v3_for_toon`) — lanyard straps (ribbon mesh,
teal), lanyard breakaway clasp (magenta), badge clip (gunmetal), badge card
(cream/white), badge portrait window (utility navy), 3 badge bars (gray), and
two "woven patch" chest/sleeve accents that **already use navy + teal +
magenta + cyan material slots** (`woven_patch()` L2084‑2093, called at
L2100‑2112 for `GEO_AVERY_PATCH_CHEST` and `GEO_AVERY_PATCH_SLEEVE_L/R`) —
i.e. the magenta/teal accent chevrons the style sheet wants are **already
modeled**, just hidden. Materials: `MAT_AVERY_BADGE` → `("white","navy_deep")`
and `MAT_AVERY_UTILITY_NAVY` → in `MATERIAL_TINT`; `MAT_AVERY_GUNMETAL` /
`MAT_AVERY_GRAY` are *not* in `MATERIAL_TINT` but `convert_material_to_cel()`'s
fallback branch (L286‑292) samples and darkens their existing PBR base color,
so they'll still get a flat cel treatment automatically, just not from the
explicit token table — acceptable, no change needed there.

**Evidence — smartwatch/tablet, genuinely absent:**
Searched `build_accessories()` (the function actually used — confirmed via
`CHEN_SCRIPT = CHEN_ROOT / "scripts" / "build_avery_chen.py"` at L27, which is
`docs/avery-chen/scripts/build_avery_chen.py`) and found no watch or tablet
geometry anywhere in it. There's an unrelated, unused older script
(`docs/avery-chen/build_v3.py`) with its own `build_accessories()` containing
cuff/sock rings — **that script is not on the toon pipeline's load path**
(`load_v3_builder()` L115‑120 loads `CHEN_SCRIPT` specifically), so it's not a
source of reusable watch geometry either. **Smartwatch and tablet are
confirmed not to exist anywhere in this repo's build scripts** — these would
be genuinely new geometry, not a re-enable.

**Root cause:** badge/lanyard/patches were deliberately hidden at some point
(labeled "clutter"/"scrap") for reasons not fully recoverable from the two
`internal/avery-toon-*-a23b.md` docs without a deeper read, but structurally
they are intact, correctly parented, and already carry roughly the right
palette (teal/magenta/navy) — this is the cheapest win in the whole proposal.
Watch/tablet are absent because they were never built, full stop.

**Confidence:** High that un-hiding is sufficient for badge/lanyard/patches
(geometry + materials already correct, this is purely a visibility flag
flip). High that watch/tablet require new geometry if wanted at all.

**Proposed change:**

1. Stop hiding badge/lanyard — delete the "clutter" loop in
   `postprocess_toon_cohesion()` (L1598‑1607):
```diff
-    for clutter in (
-        "GEO_AVERY_BADGE",
-        "GEO_AVERY_BADGE_PORTRAIT",
-        "GEO_AVERY_BADGE_CLIP",
-        "GEO_AVERY_LANYARD_L",
-        "GEO_AVERY_LANYARD_R",
-    ):
-        obj = bpy.data.objects.get(clutter)
-        if obj:
-            obj.hide_render = True
     fix_facial_materials()
```

2. Stop force-hiding the patches/badge sub-parts/lanyard clasp via
   `SCRAP_OBJECTS` (combined with the lapel removal from sub-issue 1 — this is
   the full new set):
```diff
 SCRAP_OBJECTS = {
-    "GEO_AVERY_LAPEL_L",
-    "GEO_AVERY_LAPEL_R",
-    "GEO_AVERY_PATCH_CHEST",
-    "GEO_AVERY_PATCH_SLEEVE_L",
-    "GEO_AVERY_PATCH_SLEEVE_R",
     "GEO_AVERY_LENSES",
     "GEO_AVERY_CORNEAS",
-    "GEO_AVERY_BADGE_BAR_0",
-    "GEO_AVERY_BADGE_BAR_1",
-    "GEO_AVERY_BADGE_BAR_2",
-    "GEO_AVERY_BADGE_CLIP",
-    "GEO_AVERY_BADGE_PORTRAIT",
-    "GEO_AVERY_LANYARD_BREAKAWAY",
     "GEO_AVERY_BELT_KEEPER",
     "GEO_AVERY_ROLLED_CUFF_L",
     "GEO_AVERY_ROLLED_CUFF_R",
 }
```
Kept hidden: `GEO_AVERY_LENSES`/`GEO_AVERY_CORNEAS` (unrelated to wardrobe —
eyewear internals), `GEO_AVERY_BELT_KEEPER` (minor, sheet doesn't emphasize a
belt), `GEO_AVERY_ROLLED_CUFF_L/R` (moot either way — these are also in
`REMOVE_CLOTHING_EXACT`, L664‑665, so `delete_clothing_meshes()` deletes them
outright regardless of `SCRAP_OBJECTS` membership; reviving rolled cuffs would
require un-stubbing the separate `sleeve_mesh`/`add_rolled_cuff` path in
`patch_v3_for_toon`, which is a bigger, separate change — out of scope here).

3. Magenta accent color — bump toward the sheet's `#F51496` (currently a
   fairly muted `#C43B8C`, shared by nothing else that would be affected —
   confirmed `"hair_magenta"` is a *separate* palette key, not this one, so
   this change is isolated to garment/accessory accents):
```diff
 TOON_PALETTE = {
     ...
-    "magenta": "#C43B8C",
+    "magenta": "#F51496",
     ...
 }
```
This is a judgment call flagged per the task brief rather than silently
decided: the sheet's exact value is vivid/saturated; the existing muted
`#C43B8C` is closer to the cel-flat-shading aesthetic already established
elsewhere. Picking the sheet-exact value here as the default proposal since
the task brief explicitly offered it as an option — but worth a visual check
against the render; if it looks too neon against the muted navy/teal/white,
fall back to something between the two, e.g. `#D6177E`.

4. Smartwatch (optional, new geometry, lower priority than 1‑3 above): a
   small navy/graphite band + face on one forearm, parented the same way
   `build_accessories()` parents other chest items (`parent_bone(obj, "chest")`
   pattern → here `parent_bone(obj, "forearm.L")` or similar bone name — bone
   naming needs checking against the actual V3 armature before writing this,
   not assumed). Sketch only, not a full diff — this is net-new geometry and
   should be scoped as a separate small pass once 1‑3 are confirmed to look
   right, rather than bundled into this fix:
```python
def build_smartwatch(v3, materials: dict) -> None:
    """Small band + face on the left wrist, cel-shaded navy/graphite."""
    # rounded_box-style band around forearm bone near the wrist end,
    # + a thin square/circle "face" in graphite or electric-blue accent.
    # Needs: confirm wrist bone name in RIG_AVERY_CHEN, confirm forearm
    # world-space position at wrist (not mid-forearm) before placing.
    ...
```

5. Tablet: **not proposed**. The style sheet shows it only in action/hero
   poses, not the front/3-quarter/side/back reference views. The toon
   pipeline's current render set (`full-body-front`, `-three-quarter`,
   `-side`, `expression-sheet`, `action-wave`) has no pose where a held prop
   would read correctly without new pose/IK work — recommend treating this as
   genuinely out of scope for a wardrobe fix.

**Verification:** next front render should show the lanyard straps running
from shoulders down to a badge card at chest height (sitting on the navy
jacket area just below the narrowed chest band, not overlapping it — checked
the badge's z-position, ~1.14‑1.2 m, against the new `CHEST_LOOP_BOTTOM` of
1.205 m from sub-issue 2, and it lands just below the band, which is
correct/more-realistic badge placement, not a conflict), plus small
navy/teal/magenta chevron patches on the chest and one sleeve. Confirm no new
QA gate failures — `verify_no_clothing_meshes` only checks `GEO_AVERY_JKT_`/
`GEO_AVERY_SHIRT` prefixes, unaffected by any of these object names.

---

## Scope

- **Deliberate visible departure flagged for human review:** the olive →
  navy trouser recolor (sub-issue 3) is a conscious pivot away from
  `media/avery-flat/front.png`'s olive cargo pants, which this pipeline was
  originally built against and which `docs/avery-toon/README.md` currently
  documents as correct ("stay olive"). It matches the user's now-confirmed
  target (`images/7.png`) but is **not a bug fix** — it changes the
  character's established look. The orchestrator should look at this diff
  specifically before applying it. `README.md`'s "Look (toon pass)" section
  (L38, L41) will also need updating to match if this is applied — not
  included above since the instruction was to touch only the proposal file,
  but flagging it so the README doesn't go stale.
- **All proposed code changes are toon-pass-local**, confined to
  `docs/avery-toon/build_avery_toon.py`. No edits are proposed to
  `docs/avery-chen/scripts/build_avery_chen.py` or any other base-V3 file —
  every accessory/lapel/patch object needed already exists there unmodified;
  the toon pass just needs to stop hiding it. The one exception is the
  optional smartwatch (item 4 in sub-issue 4), which, if pursued, is new
  geometry that could live in either the toon pass or the base V3 script —
  recommend toon-pass-local (`build_avery_toon.py`) to keep base-V3 untouched,
  consistent with everything else here.
- **Coupled change required, not optional:** sub-issue 2's chest-band resize
  and `verify_chest_band_front()`'s fixed pixel-sample box are tightly
  coupled. Applying the constant resize without recalibrating that QA gate's
  row/col fractions will likely cause a false `RuntimeError` on the next full
  build. Recalibrate empirically against the first post-resize render, not by
  guessing.
- **Not touched / explicitly out of scope:** rolled cuffs (would need
  un-stubbing a separate `sleeve_mesh`/`add_rolled_cuff` path in
  `patch_v3_for_toon`, bigger change), belt detail, tablet prop, the
  `open_jacket_front`/`soften_armscye_edges` stubs (left in place — they
  protect the closed-body-topology redesign and aren't needed given the
  paint+lapel approach above achieves the "open front" read without them).
