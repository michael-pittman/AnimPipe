# Avery Chen V3

Original stylized instructor character for AnimPipe. The host links `COL_AVERY_CHEN` and plays slotted actions by name; it does not retarget or rig at runtime.

Version **3.0.0**. Style id `avery_chen_v3`. License **CC0-1.0**.

## Rebuild

From the repository root with **Blender 5.2.1 LTS** (Pillow optional; only needed for contact-sheet renders):

```bash
blender --background --factory-startup --python scripts/build_avery_chen.py -- \
  --output assets/characters/AveryChen.blend \
  --report docs/characters/avery-chen/build-report.json \
  --skip-renders
```

The builder opens the vendored coherent CC0 source `vendor/avery-chen/coherent-base.blend` (checksum-pinned in `vendor/avery-chen/SOURCE_MANIFEST.json`). It does **not** call MakeHuman, MPFB, archived blends, or machine-local store paths at runtime.

Optional renders require a `--reference` image path and `--render-dir`; those sheets are not shipped in this repository.

## Contract

| Field | Value |
|---|---|
| Asset id | `char.avery_chen` |
| Manifest | `assets/assets.yaml` |
| File | `characters/AveryChen.blend` |
| Collection | `COL_AVERY_CHEN` |
| Armature object | `RIG_AVERY_CHEN` |
| Retarget profile | `proxy_rig_v1` |
| Coordinates | meters, up Z, forward -Y, scale 1.0 |
| `blender_min` | 5.2.1 |
| Interaction | `hand_left` → `hand.L`, `hand_right` → `hand.R` |
| Materials | `MAT_PROXY_CHARACTER`, `MAT_PROXY_FOCUS`, plus authored wardrobe materials |
| Triangles | 66402 (see `build-report.json`) |
| Texture memory | 0.0 MB (packed vertex colors / procedural only) |
| sha256 | `751fd05872f4730ef39cec3160395b431693304a91a5283e6448199739f6f6bc` |

### Actions, visemes, and facial controls

Twenty canonical slotted actions (`idle_neutral_loop` … `pose_end`), nine visemes (`VISEME_A` … `VISEME_X`), and eight facial controls (`BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT`) on `GEO_AVERY_HEAD`. Eye, brow, dental, and tongue motion uses driven shape keys documented in `scripts/build_avery_chen.py`.

## Source inventory

| Input | Role | License |
|---|---|---|
| `vendor/avery-chen/coherent-base.blend` | hm08 anatomy, suit/shoe topology, eyes, integrated viseme deltas, proxy rig/actions | CC0-1.0 |
| `vendor/avery-chen/SOURCE_MANIFEST.json` | checksum + upstream record | — |
| `vendor/avery-chen/LICENSES.md` | SPDX and upstream links | — |
| `scripts/build_avery_chen.py` | deterministic V3 hero builder | CC0-1.0 |

## Known limitations

- Exact 18-bone contract: no clavicles, jaw bone, or hair-secondary bones; rolled sleeves and armscye patches are weighted approximations.
- Arm raise above ~90° can open the jacket armscye.
- Hair is head-locked; no runtime groom simulation.
- Dental/tongue motion uses driven shape keys, not a jaw bone.
- Blender 5.2.1 does not guarantee byte-identical `.blend` bytes across hosts; compare `build-report.json` sha256 and contract gates after each build.
- Stature follows proxy bone lengths (~1.74 m crown), not a shorter style prose target, unless the rig is shortened in a future contract revision.

## Validation

Static manifest checks (from an unpacked `AnimPipe_gpu_wave_hardened_v3_1.zip` pipeline tree):

```bash
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, 'blender_training_pipeline_proxy')
from asset_system.doctor import static_doctor
print(static_doctor(Path('assets/assets.yaml'), 'char.avery_chen', Path('assets')))
"
```

Blender reopen gates are embedded in `scripts/build_avery_chen.py` (`validate_scene`).
