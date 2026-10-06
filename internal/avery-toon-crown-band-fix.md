# Avery toon — crown + chest band fix (code only, not yet rendered)

Picks up the run that stopped on a usage limit mid-rebuild. Work was recovered
from the Cursor agent store and moved into `/Users/nucky/AnimPipe`.

**Not verified by a render.** Blender is not installed on this machine, so every
change below is reasoned from the geometry and from measurements taken on the
last shipped render. The first real rebuild is the proof.

## What the last render actually showed

`media/avery-toon/full-body-front.png` (the one that failed QA):

- **Crown bald.** The plum mass sat *behind* the head and read as a halo ring —
  the sphere's top was below the scalp, so only its silhouette showed past the
  head outline. Forehead and crown were bare skin.
- **Chest band a sticker.** A hard axis-aligned white rectangle floating off the
  chest, with a teal line through it. Solid, but not a shirt.

## Why it got past the gates

Three gate defects let a bald crown ship as a pass:

1. `build_solid_afro_mesh` asserted that some hair vertex was within 2 cm of
   `crown_center` — but `crown_center` was built from the **hair's own highest
   vertex**. The check compared the hair to itself and could never fail.
2. `verify_hair_plate` floors were `0.012` / `0.02`. The plum halo ring alone
   scores **0.40** / **0.17** on the bald render, so both passed comfortably.
3. `cheek_plum > 1.05` — a mean fraction is at most 1.0, so this check was dead
   and had never fired.

Also: materials are authored through `rgba()` (scene-linear) while the image
gates compare against `_display_rgb()` (raw sRGB). Depending on which encoding
`bpy` hands back for the PNG, the plum mask can match **nothing at all**, and
the crown checks would then be measuring an all-zero image.

## Changes to `docs/avery-toon/build_avery_toon.py`

### Hair
- `_head_world_metrics()` — new; returns measured `(scalp_top_z,
  head_half_width, head_center_y)`.
- `build_solid_afro_mesh()` — radii now derived from the head
  (`AFRO_WIDTH_RATIO` 1.55, `AFRO_DEPTH_RATIO` 1.35) and the mass positioned so
  its top sits `AFRO_CROWN_CLEARANCE_M` (5.5 cm) above the measured scalp.
  Fixed radii were the direct cause of the bald crown.
- `_in_hair_face_window()` — new shared predicate. The clip used to delete the
  whole front hemisphere below the brow; it now also requires
  `|x| < HAIR_FACE_WINDOW_HALF_X_M` (6.2 cm), so temple volume survives and
  frames the face the way `media/avery-flat/front.png` does.
- The tautological crown assert is replaced by two real ones: hair top must
  clear the scalp, and some hair must sit directly above the crown centre.
  `validate_hair_not_curtain()` now enforces the same two.

### Gates
- `_hair_crown_mask()` matches the plum in **either** encoding, so it cannot go
  silently blind.
- Crown floor `0.012 → 0.15`; crown-centre floor `0.02 → 0.55` (bald render
  scores 0.17, so this is now the decisive check); cheek ceiling `1.05 → 0.60`.

### Chest band
- `_chest_band_front_profile()` / `_chest_band_shell_mesh()` — new. The band is
  now a closed shell following the torso's measured front profile across
  `CHEST_BAND_ARC_SEGMENTS` columns, instead of an axis-aligned slab.
- It spans the **design loops** `CHEST_LOOP_BOTTOM → CHEST_LOOP_TOP`
  (1.122 → 1.288 m) that `_chest_band_slice_material` already assumed; the old
  slab ignored them and used a 7 cm box. Teal rides 1 mm proud of the white.
- `_link_weighted_chest_box` → `_link_weighted_chest_mesh` (vertices are
  authored in world space; identity transform).

### Dead pipeline removed
Eight unreferenced functions implementing the shrinkwrap / solidify / face-cull
pipeline you told the agent to delete were still in the file, and two of them
referenced constants that no longer exist (`HAIR_SCALP_SHRINKWRAP_OFFSET_M`,
`HAIR_AFRO_SOLIDIFY_M`) — they would have raised `NameError` if ever called.
Removed, along with the now-unused `BVHTree` import.

`_remove_head_scalp_under_hair`, `_delete_hair_face_faces`,
`_resnap_hair_inner_shell_bmesh`, `_fill_hair_crown_holes`,
`_weld_head_mirror_seam`, `_cap_crown_top`, `_prune_hair_islands`,
`_scalp_hair_contact_gap`.

## Rebuild

```bash
blender --background --factory-startup \
  --python docs/avery-toon/build_avery_toon.py
```

## What to watch on the first run

- The new geometry asserts print `scalp_top` and `hair_top`. If the build stops
  on *"hair crown does not clear scalp"*, raise `AFRO_CROWN_CLEARANCE_M`.
- The crown-centre floor of **0.55** is calibrated against the bald render
  (0.17) and an assumed near-full crown, not against a good render — nobody has
  rendered a correct afro yet. If a visually good crown lands between those,
  retune it rather than lowering it blindly.
- `AFRO_MIN_RADIUS_M` (0.105) will likely be the binding constraint on the
  vertical radius; the mass then reaches to about jaw level at the sides. If
  that reads as a curtain rather than an afro, reduce it.
- Chest band: confirm the teal stripe still lands inside the fixed sample rows
  of `verify_chest_band_front` — it moved down ~6 mm when the band switched to
  the design loop heights.

No git commit (per the standing instruction on this work).
