# Avery Chen V3

Original stylized instructor character for AnimPipe. The host links `COL_AVERY_CHEN` and plays slotted actions by name; it does not retarget or rig at runtime.

Version **3.0.0**. Style id `avery_chen_v3`. License **CC0-1.0**.

## Rebuild

From the `docs/avery-chen/` directory (repository root is one level up when integrated):

```bash
blender --background --factory-startup --python scripts/build_avery_chen.py -- \
  --output ../../assets/characters/AveryChen.blend \
  --report build.json \
  --render-dir ../../media/avery-chen-v3 \
  --reference docs/reference/patty-patties-style.jpg \
  --verify-log ../../internal/avery-chen-v3-verify.txt
```

Requires **Blender 5.2.1 LTS** and **Pillow** (render sheets only).

The builder opens the vendored coherent CC0 source `vendor/avery-chen/coherent-base.blend` (checksum-pinned). It does **not** call MakeHuman, MPFB, archived blends, or Cursor store paths at runtime.

## Contract

| Field | Value |
|---|---|
| Asset id | `char.avery_chen` |
| File | `characters/AveryChen.blend` |
| Collection | `COL_AVERY_CHEN` |
| Armature object | `RIG_AVERY_CHEN` |
| Retarget profile | `proxy_rig_v1` |
| Coordinates | meters, up Z, forward -Y, scale 1.0 |
| `blender_min` | 5.2.1 |
| Interaction | `hand_left` → `hand.L`, `hand_right` → `hand.R` |
| Materials | `MAT_PROXY_CHARACTER`, `MAT_PROXY_FOCUS`, plus authored wardrobe materials |
| Triangles | see `build.json` (`triangles`) |
| Texture memory | 0.0 MB (packed vertex colors / procedural only) |
| sha256 | see `build.json` (`sha256`) |

### Actions, visemes, and facial controls

Twenty canonical slotted actions (`idle_neutral_loop` … `pose_end`), nine visemes (`VISEME_A` … `VISEME_X`), and eight facial controls (`BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT`) on `GEO_AVERY_HEAD`. `GEO_AVERY_EYES`, `GEO_AVERY_BROWS`, `GEO_AVERY_TEETH`, and `GEO_AVERY_TONGUE` follow driven keys documented in the builder.

## Source inventory

| Input | Role | License |
|---|---|---|
| `vendor/avery-chen/coherent-base.blend` | hm08 anatomy, suit/shoe topology, eyes, integrated viseme deltas, proxy rig/actions | CC0-1.0 |
| `vendor/avery-chen/SOURCE_MANIFEST.json` | checksum + upstream record | — |
| `scripts/build_avery_chen.py` | deterministic V3 hero builder | CC0-1.0 |

Historical archives under `archive/` are provenance only and are not build inputs.

## Look

Warm deep-brown skin, soft-square integrated MakeHuman face, volumetric espresso updo with controlled magenta thread, rounded trapezoid glasses, navy open utility jacket with rolled forearm sleeves, warm-white shirt, high-waisted cuffed trousers, belt, ribbed socks, modeled sneakers, teal lanyard with neutral badge, and agency-neutral spark/chevron patches. Palette locks match `internal/v3-style-translation.md`.

## Known limitations

- Exact 18-bone contract: no clavicles, jaw bone, or hair-secondary bones; rolled sleeves and armscye patches are weighted approximations.
- Arm raise above ~90° can open the jacket armscye (see `shoulder-tests.png`).
- Hair is head-locked; no runtime groom simulation.
- Dental/tongue motion uses driven shape keys, not a jaw bone.
- Blender 5.2.1 does not guarantee byte-identical `.blend` bytes; use `build.json` sha256 after each build.
- Stature follows proxy bone lengths (~1.74 m crown), not the 1.67 m style prose target, unless the rig is shortened in a future contract revision.

## Evidence

Contact sheets and turntable: `media/avery-chen-v3/`. Contract reopen log: `internal/avery-chen-v3-verify.txt`.
