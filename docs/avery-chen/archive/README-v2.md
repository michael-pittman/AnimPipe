# Avery Chen

Drop-in character for the AnimPipe link-and-play host. The blend is already rigged, weighted, and baked. The host links the collection and plays actions by name. It does not retarget, bake, or rig.

**Path taken: A.** Bone names and the parent hierarchy match `proxy_rig_v1`. The mesh is the archived MakeHuman human, not the clay proxy mannequin. This V2 file was reset from `archive/AveryChen-v1.blend`. The body, the rig, the 20 actions, and the facial keys were kept. The jacket is a sleeveless vest cut from that archived suit. The proxy rig has no clavicles, so the arms are bare skin instead of sleeves.

The archived V1 file is still at `archive/AveryChen-v1.blend` (sha256 `6e9566f2f5ddab632b27472523e2977230c6f38686ddb37a13de3db67d1a02dd`). Macro sliders are not a description of Avery’s ethnicity or gender, and the surname Chen is not a facial reference.

The kit generator (`scripts/100_generate_proxy_kit_blender.py`) was not used. The pipeline in `/workspace` is zipped, not unpacked. Nothing was committed to that git repo.

Built with Blender **5.2.1 LTS** and MPFB **2.0.17** (nightly 2026-09-11).

## Drop-in

Suggested asset id: `char.avery_chen`

| Field | Value |
|---|---|
| File on the host | `assets/characters/avery_chen.blend` |
| Collection | `COL_AVERY_CHEN` |
| Armature object | `RIG_AVERY_CHEN` |
| Armature data | `RIG_AVERY_CHEN_DATA` |
| Retarget profile | `proxy_rig_v1` |
| Coordinates | meters, up `Z`, forward `-Y`, scale `1.0` |
| `blender_min` | `5.2.1` |
| sha256 | `4c09c2fdb6aa4c0b40079a17a2e1ec6b90c8d8de412573bc386c71549f0a6b84` |
| Triangles | 58236 rendered |
| Texture memory | 81 MB uncompressed RGBA, 12.0 MB packed |

Native orthographic measure, crown to chin, no hair: **7.92 heads**. Stature 1.696 m. Sole at z=0.008 m. Hip joint at 53.1% of stature. Acromion 1.98 head widths. Shoulder-to-hip breadth 0.95. Hand group length 0.49 head heights. Foot 1.11 head heights. These are the archived MakeHuman proportions. They were not edited to the stricter V2 gates.

Meshes in `COL_AVERY_CHEN`:

- `GEO_AVERY_HEAD` — the MakeHuman basemesh (19158 vertices). Closed neutral mouth, with a slight warm corner lift and about 1.2 mm of corner asymmetry on Basis and on every shape key. All facial shape keys live here. The stock suit mask still hides the torso and the legs. The shoulders, axilla, upper arms, and forearms are taken out of that mask, so a raised arm shows continuous skin from the opening into the torso.
- `GEO_AVERY_BODY` — CC0 `male_elegantsuit01`, restored from the V1 archive and cut into a sleeveless vest (5051 vertices, 4904 polygons). The sleeves were removed by walking each sleeve tube from its wrist cuff until the ring became the armscye. Those loops were then relaxed and seated about 6.5 mm off the body, and the shoulder tips were pulled onto the torso side of the deltoid. The polygon count did not change. The jacket torso, shirt, collar, and tie stay. The trousers are the archived faces and were not edited after that restore. Recolor: muted slate vest, warm-stone shirt, charcoal trousers. The tie is the same painted geometry, recolored to the lanyard teal `(48, 122, 118)` so it belongs with the badge strap. That is a stylized business-casual choice for a rig with no clavicles, not a claim that the stock suit shipped this way. The armscye and shoulder cap are weighted only to chest. The trouser weights were left as archived. There are no shape keys and no separate sleeve objects.
- `GEO_AVERY_BINDING` — one chest-parented curve with two closed armhole trims. Each is a 9 mm beveled tube (4.5 mm radius) in `MAT_AVERY_BINDING`, a slightly darker slate than the vest, sitting on the finished edge. It does not follow the arm.
- `GEO_AVERY_SHOES` — CC0 `shoes01`. The ankle collar is one shared UV island on `shoes01_diffuse.png`. That lining was a light gray-violet, and a sliver of it showed above the rear cuff. Those texels are now the trouser charcoal `(52, 58, 61)`, with the local weave kept. The leather, the roughness, and the normal map were not changed.
- `GEO_AVERY_EYES` — CC0 high-poly eyes, material `MAT_PROXY_FOCUS`. The iris texels on `brown_eye.png` were shifted to a dark brown. The sclera was left.
- `GEO_AVERY_BROWS` — CC0 `eyebrow001`, tinted a softer dark brown.
- `GEO_AVERY_HAIR` — CC0 `short02` crop, recolored natural dark brown. No cards were cut. On the regenerated closeups, both pupils are clear from the front and from ±30°. Brow coverage on those same cameras is 100% from the front and 94% from each side.
- `GEO_AVERY_TEETH` and `GEO_AVERY_TONGUE` — CC0 teeth and tongue inside the closed mouth.
- `GEO_AVERY_LANYARD` — the archived V1 band and blank badge, parented with the suit. Both the strap and the card render. The badge is about 36 × 24 mm. It was not replaced.

### Bones

`root`, `pelvis`, `spine`, `chest`, `neck`, `head`, `upper_arm.L`, `forearm.L`, `hand.L`, `upper_arm.R`, `forearm.R`, `hand.R`, `thigh.L`, `shin.L`, `foot.L`, `thigh.R`, `shin.R`, `foot.R`.

Parents: `pelvis→root`, `spine→pelvis`, `chest→spine`, `neck→chest`, `head→neck`, arms from `chest`, legs from `pelvis`. Pose bones use XYZ Euler.

Interaction points: `hand_left` → `hand.L`, `hand_right` → `hand.R`.

### Materials

- `MAT_PROXY_CHARACTER` — medium neutral-warm tan/olive-brown. Cheeks, nose, lips, ears, and eyelids are vertex-color zones. The CC0 skin diffuse remains as luminance detail, with a low bump and restrained subsurface.
- `MAT_PROXY_FOCUS` — the darkened brown iris on the eyeballs.
- `GEO_AVERY_HEAD.male_elegantsuit01` — the recolored suit texture on the original material.
- `MAT_AVERY_BINDING` — the armhole piping, sRGB `(52, 66, 62)`, roughness 0.55.

### Shape keys

On `GEO_AVERY_HEAD`, plus `Basis`:

Visemes: `VISEME_A`, `VISEME_B`, `VISEME_C`, `VISEME_D`, `VISEME_E`, `VISEME_F`, `VISEME_G`, `VISEME_H`, `VISEME_X`

Facial controls: `BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT`

Rhubarb map: `A→VISEME_A` through `X→VISEME_X`. Body actions do not drive these keys.

### Actions

All 20 are object actions on `RIG_AVERY_CHEN`, fake-user, one object slot (Blender 5.2 slotted actions). The eight `pose_*` clips are a single held frame. The other twelve are motions.

Motions: `idle_neutral_loop` (48, loop), `walk_cycle` (24, loop), `turn_left_90` (18), `turn_right_90` (18), `gesture_present` (28), `point_left` (24), `point_right` (24), `wave` (30), `head_nod` (20), `head_shake` (24), `reach_grab` (28), `place_release` (30).

Holds (1 frame): `pose_neutral`, `pose_present`, `pose_listen`, `pose_think`, `pose_point`, `pose_hold`, `pose_ready`, `pose_end`.

`turn_left_90` yaws the character toward their left (root Y = -90 at the last frame). `point_left` uses `upper_arm.L`.

## Manifest snippet

```yaml
char.avery_chen:
  kind: character
  version: 2.0.0
  sha256: 4c09c2fdb6aa4c0b40079a17a2e1ec6b90c8d8de412573bc386c71549f0a6b84
  blender_min: 5.2.1
  file: characters/avery_chen.blend
  collection: COL_AVERY_CHEN
  object: null
  coordinates: {units: meters, up: Z, forward: -Y, scale: 1.0}
  interaction_points: {hand_left: hand.L, hand_right: hand.R}
  material_roles: [character, focus]
  complexity: {triangles: 58236, texture_memory_estimate_mb: 81}
  source: makehuman-community:mpfb2+cc0-system-assets
  license: CC0-1.0
  style_id: avery_chen_v2
  tags: [instructor, rigged, lip-sync, stylized-realism]
  rig:
    armature: RIG_AVERY_CHEN
    retarget_profile: proxy_rig_v1
    required_actions:
      - idle_neutral_loop
      - walk_cycle
      - turn_left_90
      - turn_right_90
      - gesture_present
      - point_left
      - point_right
      - wave
      - head_nod
      - head_shake
      - reach_grab
      - place_release
      - pose_neutral
      - pose_present
      - pose_listen
      - pose_think
      - pose_point
      - pose_hold
      - pose_ready
      - pose_end
    visemes:
      A: VISEME_A
      B: VISEME_B
      C: VISEME_C
      D: VISEME_D
      E: VISEME_E
      F: VISEME_F
      G: VISEME_G
      H: VISEME_H
      X: VISEME_X
    facial_controls:
      - BLINK
      - BROW_UP
      - BROW_DOWN
      - EXP_smile
      - EXP_frown
      - EXP_surprise
      - LOOK_LEFT
      - LOOK_RIGHT
    action_metadata:
      idle_neutral_loop: {duration_frames: 48, category: idle, loop: true}
      walk_cycle: {duration_frames: 24, category: locomotion, loop: true}
      turn_left_90: {duration_frames: 18, category: locomotion, loop: false}
      turn_right_90: {duration_frames: 18, category: locomotion, loop: false}
      gesture_present: {duration_frames: 28, category: gesture, loop: false}
      point_left: {duration_frames: 24, category: gesture, loop: false}
      point_right: {duration_frames: 24, category: gesture, loop: false}
      wave: {duration_frames: 30, category: gesture, loop: false}
      head_nod: {duration_frames: 20, category: head, loop: false}
      head_shake: {duration_frames: 24, category: head, loop: false}
      reach_grab: {duration_frames: 28, category: interaction, loop: false}
      place_release: {duration_frames: 30, category: interaction, loop: false}
      pose_neutral: {duration_frames: 1, category: pose, loop: false}
      pose_present: {duration_frames: 1, category: pose, loop: false}
      pose_listen: {duration_frames: 1, category: pose, loop: false}
      pose_think: {duration_frames: 1, category: pose, loop: false}
      pose_point: {duration_frames: 1, category: pose, loop: false}
      pose_hold: {duration_frames: 1, category: pose, loop: false}
      pose_ready: {duration_frames: 1, category: pose, loop: false}
      pose_end: {duration_frames: 1, category: pose, loop: false}
```

`style_id: avery_chen_v2` is not `proxy_clay_v1`. Drop the field if the host style registry only allows the clay id. `texture_memory_estimate_mb` is uncompressed RGBA of the native maps. The packed PNGs are 12.0 MB.

## What the host still does

These are handoff checks. They were not run here.

1. Unpack the pipeline (it is not unpacked in `/workspace`).
2. Copy `AveryChen.blend` to `assets/characters/avery_chen.blend`.
3. Add the snippet to `assets/assets.yaml`. Do not overwrite `assets.proxy.yaml`.
4. Run `pipe asset doctor char.avery_chen` and `pipe asset doctor char.avery_chen --blender`, then `pipe asset export-manifest`.
5. Link the collection from a clean host and play one motion and one `pose_*` hold.
6. A five-person audience read is still outstanding.

## Local evidence

`wardrobe-proof.png` is front, side, and back of this file. The vest and trousers are the archived `male_elegantsuit01` with the sleeves removed.

- `/cursor/stores/self/media/avery-chen-v2/wardrobe-proof.png`
- `/cursor/stores/self/media/avery-chen-v2/front-closeup.png`
- `/cursor/stores/self/media/avery-chen-v2/three-quarter-closeup.png`
- `/cursor/stores/self/media/avery-chen-v2/head-minus-30.png`
- `/cursor/stores/self/media/avery-chen-v2/head-plus-30.png`
- `/cursor/stores/self/media/avery-chen-v2/full-body-front.png`
- `/cursor/stores/self/media/avery-chen-v2/full-body-side.png`
- `/cursor/stores/self/media/avery-chen-v2/full-body-back.png`
- `/cursor/stores/self/media/avery-chen-v2/full-body-three-quarter.png`
- `/cursor/stores/self/media/avery-chen-v2/expression-sheet.png`
- `/cursor/stores/self/media/avery-chen-v2/viseme-strip.png`
- `/cursor/stores/self/media/avery-chen-v2/deformation-sheet.png`
- `/cursor/stores/self/media/avery-chen-v2/action-sheet.png`
- `/cursor/stores/self/media/avery-chen-v2/shoulder-tests.png`
- `/cursor/stores/self/media/avery-chen-v2/measure-front.png`
- `/cursor/stores/self/media/avery-chen-v2/measure-side.png`
- `/cursor/stores/self/media/avery-chen-v2/measure-back.png`
- `/cursor/stores/self/media/avery-chen-v2/rear-leg-proof.png`

`verify` reopens the blend and writes `/cursor/stores/self/internal/avery-chen-v2-verify.txt`. The measure record is `/cursor/stores/self/internal/avery-chen-v2-measure.json`.

An elbow slice at a 70° bend kept area ratio 0.94. A knee slice at a 55° bend kept area ratio 0.94. Facial interior pixels at code 0 or 255 on `front-closeup.png` are 0.0000%. Catchlight alignment within 1 px was not measured. An opaque ray from the front and ±30° cameras hits each pupil before hair, brow, or lid, and each brow arc stays at 100% (front) or 94% (±30°).

## Rebuild

```bash
blender --background --python build_character.py -- vest
blender --background --python build_character.py -- finish
blender --background --python build_character.py -- proof
blender --background --python build_character.py -- render
blender --background --python build_character.py -- inspect
blender --background --python build_character.py -- verify
```

`vest` restores the archived suit, removes the sleeves at the armscye, shows the arms, and recolors the tie. `finish` smooths those openings, tucks the shoulder tips, and adds the binding. Run `finish` after `vest`; running `vest` again restores the raw cut. `patch` repaints the shoe-collar lining on the current file and does not recut the vest. A bare run refuses to rebuild. `sleeves`, `reweight`, and `armpit` are refused. `render` does not save over the blend. `verify` must stay `RESULT: PASS`.

## Honest limits

- The five-person audience study was not run.
- `pipe asset doctor` was not run. The pipeline zip was not unpacked.
- A local library link of `COL_AVERY_CHEN` and the 20 actions into an empty file played `wave`. The linked right upper arm was about 69° out, the visible arm skin moved 32 mm between frames 1 and 16, and the chest-parented binding did not follow the arm. That is not the upstream host smoke test.
- Full jacket sleeves were abandoned. The rig has no clavicles. Separate sleeve meshes, a 62 mm shoulder cap, Surface Deform, and six corrective shape keys were all tried. The caps read as pads and the underarm still webbed or spiked. None of that is in this file.
- The shipped jacket is a sleeveless vest. Each sleeve was deleted as a face ring walked from the wrist cuff until the loop was more torso than arm. Those loops, 40 verts on the left and 43 on the right, were relaxed tangentially, mirrored, and seated on the body. The finished edge sits about 6.2–8.8 mm off the torso, with no corner sharper than about 155°. The shoulder tips end on the torso side of the deltoid. A 9 mm binding follows each opening and is parented to `chest`, so it stays with the vest when the arm lifts. No sleeve, bridge, or underarm panel was added. Shoulder, axilla, and arm faces of the basemesh are unmasked, so the opening shows skin rather than the background.
- The tie is still painted into the suit. Its texels are the muted teal of the lanyard. That is a deliberate business-casual compromise, documented here, not a separate object and not the stock tie color.
- The trousers are the archived faces. Their signatures were checked after the sleeve cut and matched. The back-view plate from this file has no enclosed background-colored hole in the legs. Trouser topology was not edited after the restore. The pale gray-violet patch above the rear cuff was the shoe-collar lining, not a trouser face. It is recolored to the surrounding charcoal. The cuff and the shoe edge stay where they were.
- The every-frame sample on the vest is QUIET. No edge longer than 4 mm exceeded 8×. The highest sample is 5.05× on `walk_cycle`. The log is `internal/avery-v2-every-frame-inspection.md`. That test is not a two-camera render of every frame.
- Shoulder raises at 0, 45, 90, and 120 degrees are in `shoulder-tests.png`. The cloth no longer spans the shoulder joint. This rig has no clavicle bones.
- Vest outer width measures 1.97 head widths. That is the sleeveless jacket after the shoulder tips were pulled in, not a sleeved shoulder.
- Head contract-bone weights: unbound 0, more than four influences on 11 vertices, off-normalization 0. Those head weights were not rewritten.
- Native proportions sit outside the old stricter V2 numeric gates. They were left as measured.

## License

No commercial character is in this file.

- **Generator:** MPFB 2.0.17 (GPL-3.0-or-later), nightly build 2026-09-11. Source: <https://github.com/makehumancommunity/mpfb2>. The addon created the hm08 basemesh.
- **CC0 assets** from the MakeHuman system pack: skin diffuse `young_lightskinned_female_diffuse2` (luminance detail only), suit `male_elegantsuit01`, shoes `shoes01`, hair `short02`, eyes `high-poly` with `brown_eye`, eyebrows `eyebrow001`, teeth `teeth_base`, tongue `tongue01`.
- **Lanyard** is the archived original band and blank badge. No seal, no lettering.
- **CC0 visemes and face units:** <https://files.makehumancommunity.org/functional/visemes01.zip> and <https://files.makehumancommunity.org/functional/faceunits01.zip>.

The manifest `license` field is `CC0-1.0` for the fitted assets. The generator addon is GPL-3.0-or-later.
