# Patty Patties — pipeline drop-in

Illustrated 2D cutout of the Patty Patties style sheet, rigged so AnimPipe can link it and play the existing proxy actions. About **352 triangles**, so a shot renders the character as flat cards instead of the 66k-triangle V3 body.

## Drop-in

File: `assets/characters/PattyPatties.blend`  
Manifest id: `char.patty_patties` in `assets/assets.yaml`

The collection and armature names match `char.avery_chen`, and the action names match `proxy_rig_v1`. A project can register this file as its own asset id, or point an existing `char.avery_chen` entry at `characters/PattyPatties.blend` without a retarget.

| Field | Value |
|---|---|
| Collection | `COL_AVERY_CHEN` |
| Armature | `RIG_AVERY_CHEN` |
| Retarget profile | `proxy_rig_v1` (18 bones) |
| Actions | 20 slotted names, `idle_neutral_loop` … `pose_end` |
| Visemes | `VISEME_A` … `VISEME_H`, `VISEME_X` on `GEO_AVERY_HEAD` |
| Expressions | `BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT` |
| Materials | `MAT_PROXY_CHARACTER`, `MAT_PROXY_FOCUS` |
| Coordinates | meters, Z up, forward −Y |
| Blender | 5.2.1 LTS |
| sha256 | `22e1d94b0da80babbc28929fc67939c750b5073d45b5a8ea7ba7d78f950d4c67` |

Textures are packed. Nothing in the file links out to a machine path.

## What is in the file

Front view is bone-parented cards cut from the style sheet: head and hair, torso, each arm, bag, tablet, thighs, shins, shoes. `BLINK` draws lids over the eyes. Side, three-quarter, and back are packed turnaround cards (`GEO_AVERY_VIEW_SIDE`, `GEO_AVERY_VIEW_THREE_QUARTER`, `GEO_AVERY_VIEW_BACK`), hidden during a front shot.

`GEO_AVERY_WATCH` and the viseme mouth cards are in the collection and parented, and they are hidden in the default render. The watch is already painted on the tablet hand. The expression-row mouth crops do not sit cleanly on the front portrait, so showing them covered the face.

## Rebuild

```bash
blender --background --factory-startup --python docs/avery-2d/build_patty_dropin.py
```

Needs Blender 5.2.1 and Pillow in that Blender's Python. The script rebuilds `assets/characters/PattyPatties.blend`, reopens it, checks the contract, links the collection the way the pipeline does, plays `wave`, and writes `media/patty-patties/`.

## Tested

On Blender 5.2.1 LTS:

- Reopen check: bone hierarchy, 20 slotted actions, visemes and expressions on `GEO_AVERY_HEAD`, both proxy materials, packed images, no linked libraries. `wave` moves `upper_arm.R`.
- Pipeline `asset_doctor_blender.py`: collection, armature, actions, visemes, and expressions passed.
- Link test: `COL_AVERY_CHEN` linked, library-overridden, `wave` assigned, frame 15 rendered to `media/patty-patties/link-wave.png`.

## Limits

- Elbows and knees do not hinge on their own. The arm card follows `upper_arm` and the shin card follows `shin`, so a wave or a step reads, but the sleeve does not bend at the elbow.
- Front, side, and back are separate drawings. The live rig is the front cutout. Turn the view cards on for the other angles; do not expect the front cards to look correct from the side.
- `BLINK` is the expression that changes the portrait. The other facial keys are on the head mesh for the pipeline, with small vertex motion, and the mouth image cards stay hidden.
