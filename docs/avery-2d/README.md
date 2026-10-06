# Avery Chen 2D (Patty style cutout)

The tested pipeline drop-in is [`assets/characters/PattyPatties.blend`](../../assets/characters/PattyPatties.blend) (`char.patty_patties`). Rebuild it with `build_patty_dropin.py`. This folder's older `Avery2D.blend` is the earlier hero-card cutout.

Immersive **per-part** 2D meshes in `COL_AVERY_CHEN` — each anatomy, clothing, accessory, and facial feature is its own object for prompt-level control.

## Drop-in

Link `COL_AVERY_CHEN` and play the same 20 slotted action names from this file. Contract matches `char.avery_chen` / `proxy_rig_v1`.

```bash
blender --background --factory-startup --python build_avery_2d.py -- \
  --source ../avery-chen/AveryChen.blend \
  --output Avery2D.blend \
  --render-dir ../../media/avery-2d \
  --verify-log ../../internal/avery-2d-verify.txt
```

## Contract (unchanged)

| Field | Value |
|---|---|
| Collection | `COL_AVERY_CHEN` |
| Armature | `RIG_AVERY_CHEN` |
| Materials | `MAT_PROXY_CHARACTER`, `MAT_PROXY_FOCUS` |
| Actions | 20 canonical names (`idle_neutral_loop` … `pose_end`) |
| Visemes | `VISEME_A`–`VISEME_H`, `VISEME_X` on `GEO_AVERY_HEAD` |
| Expressions | `BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT` on `GEO_AVERY_HEAD` |
| Coordinates | meters, Z up, forward −Y |
| Blender | 5.2.1 LTS |

**sha256:** `1c3483ba07650bed09519d4852de7005a009ed5ed6ea233020221e7b771db641`

## Promptable parts

### Anatomy

- `GEO_AVERY_HEAD` — bone head + visemes/expressions on this mesh
- `GEO_AVERY_NECK` — bone neck
- `GEO_AVERY_TORSO` — rest-pose intact front/side/back hero card on pelvis
- `GEO_AVERY_UPPER_ARM.L` — bone upper_arm.L
- `GEO_AVERY_FOREARM.L` — bone forearm.L
- `GEO_AVERY_HAND.L` — bone hand.L
- `GEO_AVERY_THIGH.L` — bone thigh.L
- `GEO_AVERY_SHIN.L` — bone shin.L
- `GEO_AVERY_FOOT.L` — bone foot.L
- `GEO_AVERY_UPPER_ARM.R` — bone upper_arm.R
- `GEO_AVERY_FOREARM.R` — bone forearm.R
- `GEO_AVERY_HAND.R` — bone hand.R
- `GEO_AVERY_THIGH.R` — bone thigh.R
- `GEO_AVERY_SHIN.R` — bone shin.R
- `GEO_AVERY_FOOT.R` — bone foot.R

### Clothing

- `GEO_AVERY_SHIRT` — bones chest/spine
- `GEO_AVERY_JACKET_BACK` — bone chest; visible back/three-quarter views
- `GEO_AVERY_JACKET.L` — bones upper_arm.L/forearm.L
- `GEO_AVERY_JACKET.R` — bones upper_arm.R/forearm.R
- `GEO_AVERY_TROUSERS` — bones pelvis/thigh
- `GEO_AVERY_BELT` — bones pelvis/spine
- `GEO_AVERY_SHOE.L` — bone foot.L
- `GEO_AVERY_SHOE.R` — bone foot.R

### Accessories

- `GEO_AVERY_HAIR_BACK` — bone head + sway drivers (head/chest rotation)
- `GEO_AVERY_HAIR_FRONT` — bone head + sway driver
- `GEO_AVERY_GLASSES` — bone head
- `GEO_AVERY_LANYARD` — bone chest + sway drivers
- `GEO_AVERY_BADGE` — bone chest + sway driver
- `GEO_AVERY_PATCH.L` — bone upper_arm.L + sway driver
- `GEO_AVERY_PATCH.R` — bone upper_arm.R + sway driver

### Face

- `GEO_AVERY_MOUTH` — drivers from GEO_AVERY_HEAD visemes/expressions
- `GEO_AVERY_MOUTH_INTERIOR` — drivers from open visemes on GEO_AVERY_HEAD
- `GEO_AVERY_TEETH` — drivers from GEO_AVERY_HEAD; hidden at neutral
- `GEO_AVERY_EYE.L` — drivers LOOK_LEFT/LOOK_RIGHT from GEO_AVERY_HEAD
- `GEO_AVERY_PUPIL.L` — drivers LOOK_LEFT/LOOK_RIGHT from GEO_AVERY_HEAD
- `GEO_AVERY_EYELID.L` — driver BLINK from GEO_AVERY_HEAD
- `GEO_AVERY_BROW.L` — drivers BROW_UP/BROW_DOWN/EXP_surprise from GEO_AVERY_HEAD
- `GEO_AVERY_EYE.R` — drivers LOOK_LEFT/LOOK_RIGHT from GEO_AVERY_HEAD
- `GEO_AVERY_PUPIL.R` — drivers LOOK_LEFT/LOOK_RIGHT from GEO_AVERY_HEAD
- `GEO_AVERY_EYELID.R` — driver BLINK from GEO_AVERY_HEAD
- `GEO_AVERY_BROW.R` — drivers BROW_UP/BROW_DOWN/EXP_surprise from GEO_AVERY_HEAD

## Style

Palette and layer rules: `internal/patty-2d-style-spec.md`. Rig plan: `internal/patty-2d-rig-plan.md`.

## Limitations

- View-dependent jacket back / patch visibility uses render-time `view_group` flags, not runtime camera hooks.
- Secondary hair/lanyard/badge sway uses rotation drivers on bone-parented objects, not extra bones.
- Face satellites mirror `GEO_AVERY_HEAD` keys via drivers; animate head keys for speech and expression.
