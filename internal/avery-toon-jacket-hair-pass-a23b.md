---
cursor:
  subagentId: "bc-d50ccbb9-5975-5935-9203-a9c38956a23b"
---

# Avery toon jacket + hair pass (a23b)

Cross-link: [prior rebuild notes](/cursor/stores/bc-b80cc329-0c07-499f-9a51-00c871f014b4/internal/avery-toon-visual-qa-rebuild-a23b.md).

## User request (clothing + hair only)

Keep V3 body/head/glasses/hands/cargos/sneakers. Delete broken navy vest. Build closed jacket shells + afro hair. Verify `full-body-front.png` and `action-wave.png` vs flat plate.

## Implementation (`build_avery_toon.py`)

- **`delete_old_vest_and_jacket`**: removes `GEO_AVERY_BODY` jacket read, legacy sleeves/raglans/shirt loft/curve hair.
- **`configure_body_skin_only`**: body stays rigged but **hidden in render**; **`GEO_AVERY_SKIN_ARM_*`** extracts hand/forearm skin only (z capped, chest-adjacent polys stripped).
- **`build_toon_jacket`**: `GEO_AVERY_JKT_TORSO` (closed loft + clean front opening), `GEO_AVERY_SHIRT_PANEL` + teal stripe, `GEO_AVERY_JKT_UPPERARM_*` / `GEO_AVERY_JKT_FOREARM_*` (split meshes, **blended upper/forearm weights** on overlap), shoulder bridge patches, teal/magenta cuff bands.
- **`build_afro_hair_mass`**: ellipsoid curly volume (~0.78× head width in X), magenta/black slots, face-window bmesh trim, parented to `head`.

Automated checks: front continuity, wave navy sampling (passes), hair crown sampling (warn-only — face window makes crown sample hair-free).

## Deliverables overwritten

- `docs/avery-toon/AveryToon.blend`, `README.md`
- `media/avery-toon/*.png` (5)

No git commit.

## Visual status vs flat (manual review)

**Improved:** face + glasses visible; white chest panel + horizontal teal band; navy torso/sleeves as separate rigged meshes; wave frame shows navy on raised forearm; cargos/sneakers unchanged.

**Still short of flat:** hair reads as faceted ellipsoid (not soft afro); small shoulder/armhole gaps can still show skin; hair automated crown metric fails (logged as `AVERY_TOON_HAIR_WARN`).

Rebuild: `blender --background --factory-startup --python docs/avery-toon/build_avery_toon.py`
