---
cursor:
  subagentId: "bc-04107bd8-d789-5742-bf40-855a0e87ee72"
---

# Character pipeline contract (verified from `/workspace` git repo)

**The animation/character pipeline is not present as an unpacked source tree in this git checkout** — only `README.md` and three release archives. All contract details below are quoted from those archives (primary source: `AnimPipe_gpu_wave_hardened_v3_1.zip` → `blender_training_pipeline_proxy/`). Paths below are relative to that bundle root unless prefixed with `/workspace/`.

## Git-tracked layout (`/workspace`)

| Path | Role |
|---|---|
| `README.md` | Title only: `# AnimPipe` / `Blender pipeline` |
| `AnimPipe_gpu_wave_hardened_v3_1.zip` | Full pipeline tree (recommended contract source) |
| `blender_training_pipeline_proxy_slim.zip` | Slim tree; includes generated `assets/assets.proxy.yaml` (no `.blend` in listing) |
| `blender_training_pipeline_proxy_v1.zip` | Older partial tree |

No loose files such as `scripts/100_generate_proxy_kit_blender.py`, `proxy_kit/kit.yaml`, or `assets/assets.proxy.yaml` exist at the git root.

## Pipeline behavior (runtime)

From `docs/BUILDER.md` and `blend_build/assets.py`:

- **No runtime retarget, bake, or rigging.** Shot build **links** the manifest `.blend`, **library-overrides** the named collection when mutation is needed, **links Actions by name** from the same `.blend`, and plays NLA stacks.
- `rig.retarget_profile` is an **admission label**, not a runtime retarget step. Builder rejects cast `retarget_profile` mismatches vs manifest (`blend_build/assets.py`).
- Blender **5.2.1 LTS** pinned (`asset_system/models.py` default `blender_min: "5.2.1"`).

## Proxy kit vs user drop-in assets

| Track | Canonical spec | Manifest | Retarget profile | Action naming |
|---|---|---|---|---|
| **Proxy Animation Kit v1** | `proxy_kit/kit.yaml` | Generated `assets/assets.proxy.yaml` | `proxy_rig_v1` | 20 names below (e.g. `idle_neutral_loop`) |
| **User/production example** | `assets/assets.yaml.example` | `assets/assets.yaml` (author-maintained) | e.g. `humanoid_v1` | Example uses `idle_neutral`, `gesture_point`, `talk_loop_a` — **different vocabulary** |

Building against the **proxy acceptance film** requires the **proxy** row. The example manifest illustrates registration shape for custom IDs, not the proxy action list.

## Tooling (inside bundle)

| Artifact | Path |
|---|---|
| Kit generator (Blender script) | `scripts/100_generate_proxy_kit_blender.py` |
| Kit spec (source of truth for proxy) | `proxy_kit/kit.yaml` |
| Proxy manifest (generated; example in slim zip) | `assets/assets.proxy.yaml` |
| Resolved JSON for builds | `build/assets.proxy.resolved.json` (after `export-manifest` / `proxy generate`) |
| Static manifest doctor | `asset_system/doctor.py` → `static_doctor()` |
| Blender datablock doctor | `blend_build/asset_doctor_blender.py` |
| Builder link/play | `blend_build/assets.py`, `blend_build/performance.py`, `blend_build/stages.py` |

**No prebuilt `proxy_character.blend` in hardened zip** — only `assets/proxy/.gitkeep`. Slim zip ships `assets/assets.proxy.yaml` + `reports/proxy/character_blender_doctor.json` from a prior run, not necessarily the `.blend` blob.

### Validation / doctor commands

From `Makefile`, `RUNBOOK.md`, `src/blender_training_pipeline/cli.py`:

```bash
.venv/bin/pipe proxy validate          # Pydantic validate proxy_kit/kit.yaml
.venv/bin/pipe proxy generate          # Blender generate + assets/assets.proxy.yaml + doctors
.venv/bin/pipe asset doctor <asset_id> # static: path, sha256, rig fields
.venv/bin/pipe asset doctor <asset_id> --blender  # + collection, armature, actions, visemes, expressions
.venv/bin/pipe asset export-manifest   # assets/assets.yaml → build/assets.resolved.json
make validate                          # scripts/90_validate_bundle.py (bundle CI)
```

`proxy generate` additionally runs `blend_build/asset_doctor_blender.py` on `assets/proxy/proxy_character.blend` with the full action/viseme/expression lists (`src/blender_training_pipeline/proxy_factory.py`).

**Blender doctor checks** (`blend_build/asset_doctor_blender.py`):

- `collection` name exists
- `armature` object exists and type `ARMATURE`
- every `--actions` name in `bpy.data.actions`
- on Blender 4.4+: each action has `len(action.slots) > 0`
- all `--visemes` on **some** mesh shape-key block
- all `--expressions` in union of all mesh shape-key names

Static doctor (`asset_system/doctor.py`) for `kind: character`: file exists, sha256, `rig` present, `retarget_profile`, `required_actions`, `visemes`, optional `facial_controls`.

## Proxy character identity (from `proxy_kit/kit.yaml`)

| Field | Value |
|---|---|
| Asset ID | `char.proxy_instructor` |
| Collection | `COL_PROXY_CHARACTER` |
| Armature object | `RIG_PROXY` |
| Armature data | `RIG_PROXY_DATA` (generator: `character["armature"] + "_DATA"`) |
| Retarget profile | `proxy_rig_v1` |
| Coordinates | `units: meters`, `up: Z`, `forward: -Y`, `scale: 1.0` |
| Attachment bones (`interaction_points`) | `hand_left` → `hand.L`, `hand_right` → `hand.R` |

## Mesh object naming (proxy generator)

From `scripts/100_generate_proxy_kit_blender.py` (`generate_character`):

| Pattern | Examples |
|---|---|
| Torso / head | `BODY_torso`, `BODY_head` |
| Limbs | `BODY_{bone}` for `upper_arm.L`, `forearm.L`, `upper_arm.R`, `forearm.R`, `thigh.L`, `shin.L`, `thigh.R`, `shin.R` |
| Hands / feet | `BODY_hand.L`, `BODY_hand.R`, `BODY_foot.L`, `BODY_foot.R` |
| Face | `FACE_eye.L`, `FACE_eye.R`, `FACE_controls` (shape keys live on `FACE_controls`) |

Geometry is **bone-parented** (`parent_type: BONE`), not weight-painted.

## Proxy rig bone names (exact)

From `make_armature()` in `scripts/100_generate_proxy_kit_blender.py`:

```
root
pelvis
spine
chest
neck
head
upper_arm.L
forearm.L
hand.L
upper_arm.R
forearm.R
hand.R
thigh.L
shin.L
foot.L
thigh.R
shin.R
foot.R
```

Hierarchy (child → parent): `pelvis→root`, `spine→pelvis`, `chest→spine`, `neck→chest`, `head→neck`, arms from `chest`, legs from `pelvis`.

Pose bones use `rotation_mode = "XYZ"`.

## Required action list (canonical 20)

Source: `proxy_kit/kit.yaml` → `character.actions` (confirmed by `tests/test_proxy_kit.py`: `len(kit.character.actions) == 20`).

**Motion (12, non-pose):**

1. `idle_neutral_loop`
2. `walk_cycle`
3. `turn_left_90`
4. `turn_right_90`
5. `gesture_present`
6. `point_left`
7. `point_right`
8. `wave`
9. `head_nod`
10. `head_shake`
11. `reach_grab`
12. `place_release`

**Held pose actions (8, `category: pose`, duration 1 frame in spec):**

13. `pose_neutral`
14. `pose_present`
15. `pose_listen`
16. `pose_think`
17. `pose_point`
18. `pose_hold`
19. `pose_ready`
20. `pose_end`

Manifest field: `rig.required_actions` must list these exact strings (`assets/assets.proxy.yaml` in slim zip mirrors this list).

Actions are **object Actions on the armature** with `use_fake_user = True`; generator creates **slotted** actions when `hasattr(action, "slots")` (Blender 4.4+).

## Shape keys (exact names)

**Visemes** (`character.visemes` map → shape key names on face mesh):

- `VISEME_A`, `VISEME_B`, `VISEME_C`, `VISEME_D`, `VISEME_E`, `VISEME_F`, `VISEME_G`, `VISEME_H`, `VISEME_X`

**Facial controls** (`character.expressions` / manifest `rig.facial_controls`):

- `BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT`

Generator adds `Basis` then the above keys on `FACE_controls` (`add_shape_keys()`).

## Materials

Proxy generator (`material()` in `scripts/100_generate_proxy_kit_blender.py`):

```python
name = f"MAT_PROXY_{role.upper()}"
```

For character assets, roles used are **`character`** and **`focus`** → materials:

- `MAT_PROXY_CHARACTER`
- `MAT_PROXY_FOCUS`

Manifest lists `material_roles: [character, focus]` for `char.proxy_instructor`; roles are semantic palette keys from `config/proxy/style.yaml`, not free-form names in the generator.

**Custom material names:** Not enforced globally by doctor. User example (`assets/assets.yaml.example`) does not use `MAT_PROXY_*`. Shot **look overrides** match materials by `material.name` or stripped linked suffix (`base_name = material.name.split(".")[0]`) in `blend_build/assets.py` — so custom names are allowed if manifest/shot config references them; **proxy kit regeneration hard-codes `MAT_PROXY_{ROLE}`**.

## Registering a new asset ID and `retarget_profile`

1. Place `.blend` under **`assets/`** using a **relative POSIX path** (no `..`, non-empty) — enforced in `asset_system/models.py` `AssetEntry.validate_contract`.
2. Add entry to **`assets/assets.yaml`** (production) or extend generated **`assets/assets.proxy.yaml`** (proxy kit only).
3. Required character fields (from `AssetEntry` / `RigContract`):
   - `kind: character`
   - `version`, `sha256`, `blender_min`, `file`, `collection`
   - `rig.armature`, `rig.retarget_profile` (**required non-empty**)
   - `rig.required_actions` (list)
   - `rig.visemes` (map Rhubarb letter → shape key name)
   - `rig.facial_controls` (list), optional `action_metadata`
   - `coordinates`, `complexity`, `source`, `license` per example
4. Run `pipe asset doctor <asset_id>` and `--blender` before admission.
5. Run `pipe asset export-manifest` → `build/assets.resolved.json` for shot builds.

Cast shots reference manifest asset IDs and action names; builder **links** actions from the character `.blend` — names must exist verbatim (`link_actions()` in `blend_build/assets.py`).

Example registration snippet (`assets/assets.yaml.example`):

```yaml
char.instructor_a:
  kind: character
  rig:
    armature: RIG_instructor_a
    retarget_profile: humanoid_v1
    required_actions: [idle_neutral, gesture_point, talk_loop_a]
```

Proxy registration is emitted by `build_manifest()` in `proxy_factory.py` with `retarget_profile: proxy_rig_v1` and the 20 proxy action names.

## Drop-in file path conventions

| Asset | Relative path (under `assets/`) | Collection |
|---|---|---|
| Proxy character (generated) | `proxy/proxy_character.blend` | `COL_PROXY_CHARACTER` |
| Proxy set | `proxy/proxy_environment.blend` | `COL_PROXY_ROOM` |
| Proxy props (multi-asset file) | `proxy/proxy_props.blend` | per prop: `COL_PROP_*` |
| Proxy paths | `proxy/proxy_paths.blend` | CURVE objects e.g. `PATH_short_arc` |
| User example character | `characters/instructor_a.blend` | `CHAR_instructor_a` |

Builder resolves paths as `assets_root / entry.file` (`safe_asset_path()`).

Shot configs for proxy acceptance use `retarget_profile: proxy_rig_v1` and actions from the 20-name set (e.g. `config/proxy/acceptance/shot/proxy_s01.yaml` uses `walk_cycle`).

## Evidence index (repo → bundle path)

| Claim | File in `AnimPipe_gpu_wave_hardened_v3_1.zip` |
|---|---|
| 20 actions + visemes + expressions | `blender_training_pipeline_proxy/proxy_kit/kit.yaml` |
| Bone list + mesh names + materials | `blender_training_pipeline_proxy/scripts/100_generate_proxy_kit_blender.py` |
| Link-only cast build | `blender_training_pipeline_proxy/blend_build/assets.py` |
| Manifest schema | `blender_training_pipeline_proxy/asset_system/models.py` |
| Generated manifest example | `blender_training_pipeline_proxy_slim.zip` → `assets/assets.proxy.yaml` |
| Doctor pass example | `blender_training_pipeline_proxy_slim.zip` → `reports/proxy/character_blender_doctor.json` |

## What this repo does **not** contain

- Unpacked pipeline source at git root
- Committed binary `.blend` files in the hardened archive listing
- Guaranteed vendored proxy `.blend` matching slim `sha256` without running `pipe proxy generate`

Do not infer bone or action names beyond the files above; production `humanoid_v1` vocabulary in `assets/assets.yaml.example` is explicitly **not** the proxy 20-action set.
