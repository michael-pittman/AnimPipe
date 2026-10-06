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
| sha256 | `39ba942d7fa5b75baec390a31b7cab15632e30b1d67be594e541e8b3e24324fb` |

Textures are packed. Nothing in the file links out to a machine path.

## What is in the file

Front view is bone-parented cards cut from the style sheet: head and hair, torso, bag, thighs, shins, shoes, and each arm split into upper arm, forearm, and hand. The forearm card follows `forearm.L` / `forearm.R`, and the hand card (tablet included on the right) follows `hand.L` / `hand.R`, so an action that bends the elbow hinges the sleeve. `BLINK` draws lids over the eyes. Viseme and expression cards sit on the measured lips and are shown by a shape-key driver on `GEO_AVERY_HEAD` (no app handler, so a linked shot still opens the mouth). Side, three-quarter, and back are packed turnaround cards, hidden during a front shot.

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

- Knees hinge (`shin` has its own card). The elbow hinges too. The sleeve art is still a flat card, so the bend is a joint between two drawings, not a curved elbow.
- Front, side, and back are separate drawings. The live rig is the front cutout. Turn the view cards on for the other angles.
- Mouth shapes are painted cel cards in the style-sheet palette, driven by the viseme and expression keys. They cover the lips. They are not a new crop of the expression-row busts.
