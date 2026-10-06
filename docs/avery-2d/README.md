# Avery Chen 2D builders (Patty style)

The tested pipeline drop-in is [`assets/characters/PattyPatties.blend`](../../assets/characters/PattyPatties.blend) (`char.patty_patties`).

## Rebuild the drop-in

Requires **Blender 5.2.1 LTS** and Pillow in that Blender's Python.

```bash
blender --background --factory-startup --python docs/avery-2d/build_patty_dropin.py
```

Docs: [`docs/characters/patty-patties/README.md`](../characters/patty-patties/README.md). Style lock: [`internal/patty-2d-style-spec.md`](../../internal/patty-2d-style-spec.md).

## Modules

| File | Role |
|---|---|
| `build_patty_dropin.py` | Builds and validates `assets/characters/PattyPatties.blend` |
| `patty_parts.py` | Style-sheet crops and bone-aligned layers |
| `patty_elbow.py` | Upper arm / forearm / hand split |
| `patty_viseme.py` | Painted mouth cards driven by head shape keys |
| `build_avery_2d.py` | Earlier hero-card experiment (writes a local `Avery2D.blend`, not shipped) |

## Contract

| Field | Value |
|---|---|
| Collection | `COL_AVERY_CHEN` |
| Armature | `RIG_AVERY_CHEN` |
| Materials | `MAT_PROXY_CHARACTER`, `MAT_PROXY_FOCUS` |
| Actions | 20 canonical names (`idle_neutral_loop` … `pose_end`) |
| Visemes | `VISEME_A`–`VISEME_H`, `VISEME_X` on `GEO_AVERY_HEAD` |
| Expressions | `BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT` |
| Coordinates | meters, Z up, forward −Y |
| Blender | 5.2.1 LTS |
