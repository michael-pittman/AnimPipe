---
cursor:
  subagentId: "bc-45a32254-bff5-5dff-beb2-6c7acca5504f"
---
# Avery Chen V3 facial-rig correction plan

## Decision summary

V3 should correct the neutral calibration before resculpting expressions: enlarge/reseat the visible eye openings around the existing symmetric globes, separate iris/pupil/catchlight reads, couple the separate brow mesh to the brow keys, tighten the neutral lip envelope, and rebuild how the dental contacts render.

The user's dental diagnosis is perceptually correct but not literally a large central mesh gap. The blend has 32 separate crown components; the upper central crowns are about 8.03 mm wide with only a 0.036 mm modeled center gap. They still render as separated pegs because the proximal faces are rounded/narrow, the dark seams are high contrast, too many crowns are exposed, the gingiva does not mask the cervical edges, and the enamel is very glossy. Do not simply translate all teeth inward; that would create overlaps and z-fighting.

The Patty Patties image is a 480×360 concept sheet, not a same-character facial turnaround. It reliably establishes style direction—large readable eyes, distinct dark iris/pupil and highlight, high expressive brows, cheek/lid participation, a continuous friendly tooth band, and a small round surprise mouth—but is too small to supply exact dental anatomy or identity landmarks.

## Audit basis

| Asset | Native size / relevant fact |
|---|---|
| `AveryChen.blend` | Blender 5.2 format, zstd-compressed; loaded successfully in Blender 5.2.1 LTS |
| `front-closeup.png` | 960×1200 |
| `expression-sheet.png` | 1440×1524; nine 480×508 cells |
| `viseme-strip.png` | 4320×508; nine 480×508 cells |
| `patty-patties-style.jpg` | 480×360 |

Blend facts:

- Metric scene, scale 1.0; no saved camera; scene render setting is 480×720.
- `GEO_AVERY_HEAD` contains the facial expression and viseme keys.
- `GEO_AVERY_EYES` contains duplicate `LOOK_LEFT` and `LOOK_RIGHT` keys.
- There are no drivers connecting the duplicated gaze keys.
- `GEO_AVERY_BROWS`, `GEO_AVERY_TEETH`, and `GEO_AVERY_TONGUE` have no shape keys. Each is weighted only to the body `head` bone.
- The 18-bone armature has no facial or jaw bone. Thus the visible brow, lower dental arch, and tongue cannot currently follow facial keys from the saved blend without an external script.

Asset fingerprints used for this audit:

- Blend: `4c09c2fdb6aa4c0b40079a17a2e1ec6b90c8d8de412573bc386c71549f0a6b84`
- Front close-up: `a4e81744f36a570047ba9c1a4f3fe9522fd3e7f20d6b6e9aa0fe653e4ae797be`
- Expression sheet: `22a3bacf1e545b6b5fc3993ab62d804704995151563737f98801d55a85aa16c7`
- Viseme strip: `c25016f1a6b3102f801a4278f4ecb024f44485fb42f1aeba20c84cf2ae38c2d2`
- Reference: `0d1d28559d4a2c2a8cf06a5ae8b4a9c80aa9cc54bdc314d9fb27e1cfea4113aa`

## Non-negotiable shape-key contract

Preserve spelling, capitalization, underscores, owners, and zero-value `Basis`. Do not rename, namespace, case-normalize, or substitute these keys.

`GEO_AVERY_HEAD`:

```text
Basis
VISEME_A
VISEME_B
VISEME_C
VISEME_D
VISEME_E
VISEME_F
VISEME_G
VISEME_H
VISEME_X
BLINK
BROW_UP
BROW_DOWN
EXP_smile
EXP_frown
EXP_surprise
LOOK_LEFT
LOOK_RIGHT
```

`GEO_AVERY_EYES`:

```text
Basis
LOOK_LEFT
LOOK_RIGHT
```

The two gaze keys must be driven in lockstep across head and eyes from one animator-facing value. Extra internal controls or corrective keys are acceptable only if the delivery validator permits extras; the required names above must remain present and unchanged.

## Measured V2 findings

### Eyes and gaze

- In the 960×1200 neutral close-up, the combined dark iris/pupil regions measure approximately:
  - viewer-left: bbox `(382,558)–(414,579)`, centroid `(397.76,568.17)`
  - viewer-right: bbox `(544,558)–(576,579)`, centroid `(560.33,568.55)`
- Both dark regions are 33×22 px and vertically aligned within 0.4 px. Their midpoint is `x=479.05`, correctly near the 480 px frame center.
- Within each visible gray aperture, both dark regions are displaced slightly toward the nose. The neutral therefore reads mildly converged even though the underlying globes are exactly mirrored.
- Iris and pupil collapse into one dark shape; no iris annulus or catchlight survives the close-up.
- The visible eye openings are small relative to their center separation. The reference's friendly read comes primarily from a larger lid aperture, not from arbitrarily moving the skull or nose.
- Blend geometry has four eye components—two coincident components per side—with centers at about `x=±28.92 mm`, `z=1597.79 mm`. Component widths are 30.16–30.98 mm; the left/right centers are geometrically symmetric.
- `brown_eye.png` is used through one material for all eye components. There is no separate pupil, iris, or catchlight object/material.
- Each eye gaze key moves all 1,064 eye vertices, with a maximum displacement of 6.30 mm. The corresponding head key moves lid-area vertices by up to 5.51 mm, but no driver keeps the two objects synchronized.
- `LOOK_LEFT` and `LOOK_RIGHT` are readable in the sheet, but scleral exposure and apparent travel are not exact mirrors. No highlight helps the viewer read globe rotation.

### Brows

- `GEO_AVERY_BROWS` contains two exactly mirrored components, each 48.09 mm wide.
- Brow centers are `x=±33.225 mm`, `z=1606.95 mm`: 4.30 mm farther lateral and 9.16 mm above the eye-component centers.
- Inner brow edges are at `x=±9.18 mm`; outer edges reach `x=±57.27 mm`.
- The neutral base geometry is perfectly mirrored, so the uneasy asymmetry in the preview is a texture/opacity and surrounding-lid read, not a different left/right mesh placement.
- More importantly, the visible brow object has no `BROW_UP` or `BROW_DOWN` deformation, no facial bones, and no driver. Those keys affect only the head mesh. Any brow motion seen in the V2 sheet is not reproducible from the saved blend alone.
- V2 brows are broad, low-contrast, and nearly uniform in thickness. Their low inner/arch relationship contributes to a skeptical or worried neutral instead of the open reference style.

### Neutral mouth and expression proportions

- The dark neutral seam is approximately 121×8 px, bbox `(420,742)–(540,749)`, with centroid `x=477.23`; the facial midline is acceptable.
- The soft lip-color envelope is approximately 145×80 px (`H/W≈0.55`, ±5 px because of the diffuse edge). The upper lip reads fuller than the lower lip.
- The long dark corner extensions and nearly level central seam make the neutral read downturned. Cupid's bow, philtral break, and commissures are indistinct.
- `EXP_smile` creates a strong hooked closed-mouth curve but little cheek lift or lower-lid narrowing.
- `EXP_frown` is mostly a lip horseshoe/pout with limited chin, cheek, or brow support.
- `EXP_surprise` opens the eyes effectively, but the mouth is broad and toothy; it reads as fear/shock rather than the reference's friendly small “O.”

### Teeth, gums, and tongue

- `GEO_AVERY_TEETH` is one static mesh with 33 connected components: 16 upper crowns, 16 lower crowns, and one 1,852-vertex dental base.
- Overall dental bounds are approximately 58.49 mm wide × 71.35 mm deep × 47.30 mm tall.
- Upper central crowns are 8.03 mm wide × 11.16 mm high; their modeled center gap is only 0.036 mm.
- Lower central crowns are 6.00 mm wide × 9.25 mm high; their modeled center gap is 0.068 mm.
- The upper median crown width/height is 8.40/9.47 mm; lower is 7.19/9.09 mm. Dimensions are plausible, but many crowns have similarly rounded block silhouettes, so they read as pegs.
- One `teeth.png` material serves the whole dental mesh. The Principled roughness is 0.2, which exaggerates bright crowns and dark interproximal seams.
- There is no separately controllable gum object/material visible in the rig contract. Cervical edges are therefore not naturally masked.
- `GEO_AVERY_TONGUE` is static and measures 43.76 mm wide × 69.16 mm deep × 26.81 mm high—about 75% of dental-arch width. In open poses it reads as a broad cavity-filling patch.
- In surprise and open visemes, six or more similarly sized crowns, strong black gaps, and the broad tongue are simultaneously visible. This creates the reported “scary” read despite the tiny modeled central gap.

### Visemes

The strip demonstrates useful gross categories, but the following pairs are not sufficiently separated:

- `VISEME_B` / `VISEME_F`: both read as lightly parted near-neutral mouths.
- `VISEME_C` / `VISEME_X`: both rely on a tight rounded/pursed silhouette.
- `VISEME_D` / `VISEME_E` / `VISEME_G`: all are shallow tooth-bearing spreads with insufficient contact/tongue distinction.
- `VISEME_A` and `VISEME_H` are distinct in aperture, but both expose the same peg-like dentistry and broad tongue.

No phoneme-to-letter map is stored in the assets. The V3 silhouettes below retain the V2 visual intent; the lip-sync owner should separately confirm the phoneme mapping before production export.

## V3 neutral specification

Use these normalized measures:

- `EW`: visible lid-aperture width in neutral.
- `EH`: visible lid-aperture height in neutral.
- `MW`: neutral mouth-seam width.
- `CH`: visible upper-central-incisor crown height.

### Eye globe, iris/pupil, lids, gaze, and catchlights

1. Keep the eye midpoint on the facial midline. First enlarge/reseat the lids around the symmetric globes; do not immediately move both globes.
2. Target pupil-center separation of `1.90–2.10 EW`, equivalent to an inner-canthus gap of `0.90–1.10 EW`.
3. If widening the apertures cannot satisfy that ratio without exposing globe edges, move each globe medially by at most 1–2 mm and reproject both lids. Keep left/right depth and height within 0.25 mm and scale within 1%.
4. Neutral aperture target: `EH/EW=0.34–0.40`; outer canthus 2–4% of `EH` above the inner canthus.
5. Iris diameter: 50–56% of `EW`. Pupil diameter: 45–55% of iris diameter. Maintain an iris annulus at least 3 px wide in the 960×1200 close-up.
6. Neutral pupil centers: horizontal offset from each aperture center ≤1% of `EW`; left/right vertical difference ≤1 px at close-up scale. Put the pupil center 0–3% of `EH` above aperture center so the upper lid overlaps the iris naturally.
7. Upper lid overlap: 8–15% of iris diameter. Lower lid should touch or leave only 2–5% of iris diameter as lower scleral clearance. Do not let the iris look pasted in front of the lids.
8. Add a modeled or shader iris/pupil hierarchy. Do not bake iris, pupil, and sclera into one undifferentiated dark patch.
9. Use one primary catchlight per eye, 10–14% of iris diameter (3–4 px in the close-up), in the same upper quadrant. Left/right catchlight vertical mismatch must be ≤1 px.
10. Prefer a light-driven/specular catchlight. Across gaze extremes it may move no more than 15% of iris travel and must not flip quadrant, disappear in one eye, or stick to the pupil center.
11. Add a subtle upper-lid rim and crease; the lower rim should be softer. Preserve globe volume during blink and gaze.

### Brows and brow controls

Neutral targets:

- Brow length: `1.08–1.18 EW`.
- Inner end: vertically above the inner canthus within ±5% of `EW`.
- Outer tail: over the outer canthus or up to 10% of `EW` beyond it.
- Lower brow edge to upper lid: `0.50–0.65 EH`.
- Apex: 65–72% of brow length from inner end; apex rise 20–30% of `EH` above the inner-to-tail chord.
- Taper thickness from a fuller inner head to a tail approximately 45–60% as thick.
- Neutral inner-end height difference ≤0.10 `EH`; apex difference ≤0.08 `EH`. Add at most a deliberate 1 mm / 2° asymmetry after the symmetric calibration passes. It must not read as one raised skeptical brow.

Internal controls, not replacements for required keys:

| Control | Required influence |
|---|---|
| `CTRL_brow_inner.L/R` | vertical plus medial/lateral motion of inner 30% |
| `CTRL_brow_arch.L/R` | vertical arch/apex motion, no endpoint translation |
| `CTRL_brow_tail.L/R` | tail height and taper angle |
| `CTRL_brow_master.L/R` | coordinated inner/arch/tail offset |

Add matching deformations to `GEO_AVERY_BROWS` and drive them 1:1 from the required head `BROW_UP` / `BROW_DOWN` values, or add non-export facial controls that are baked before delivery. The visible brow mesh and forehead/upper-lid skin must move together.

### Neutral mouth and lips

- Preserve the current horizontal midline; only correct the residual visual imbalance if the final centroid differs by more than 1% of `MW`.
- Tighten the visible vermilion envelope to `H/W=0.34–0.42`; reduce diffuse color spill rather than flattening the whole mouth volume.
- Upper-to-lower vermilion thickness ratio: 0.75–0.90. The lower lip should remain modestly fuller.
- Define a soft cupid's bow and central tubercle, but keep them stylized rather than photoreal.
- Commissures must terminate cleanly. Dark seam extensions beyond each commissure may not exceed 4% of `MW`.
- Neutral corner height must be within ±2% of `MW` of the center seam; use flat-to-very-slightly-upturned corners, not a pre-frown.
- No teeth, gum, or tongue may be visible in neutral, `VISEME_B`, or `VISEME_X`.

## Dental rebuild specification

### Geometry and spacing

Keep a natural close-contact arcade. Do not preserve 32 equally readable crown silhouettes.

| Tooth type | Upper target width | Lower target width | Visible crown height |
|---|---:|---:|---:|
| Central incisor | 8.0–8.5 mm | 5.0–5.7 mm | 9.0–10.5 mm |
| Lateral incisor | 6.3–7.0 mm | 5.5–6.2 mm | 8.0–9.5 mm |
| Canine | 7.0–7.8 mm | 6.3–7.0 mm | 9.0–10.5 mm |
| Premolar | 6.8–7.5 mm | 6.8–7.5 mm | progressively occluded |

- Keep the dental midline at facial `x=0` within 0.25 mm and within 1% of `MW` in renders.
- Anterior physical contact gaps: 0.05–0.15 mm. Build broad, nearly contacting proximal faces; do not use round pegs separated by black wedges.
- At the 480×508 expression-cell scale, interdental seams may anti-alias but must not form a continuous ≥1 px black slot. At 960×1200 close-up scale, no visible anterior gap may exceed 1 px.
- Central incisors should be rounded trapezoids, laterals slightly narrower/shorter, canines subtly pointed but not fang-like.
- Rotate posterior crowns along the arcade so they recede behind the canines. Only 4–6 upper teeth should be clearly readable in an ordinary smile; posterior teeth become a soft continuous band.
- Upper incisors should sit 1–2 mm inside the relaxed upper lip, with 5–10° labial pitch. Lower incisors sit 2–3 mm behind the upper row with 1.5–2.5 mm overbite.
- Split upper and lower rows into separate vertex groups or driven objects. The lower row must follow jaw opening; the upper row remains head-locked.

### Materials, gums, tongue, and visibility

- Use warm enamel, not pure white. Increase enamel roughness from 0.2 to 0.35–0.50 and use a broad, low-contrast highlight.
- Reduce or disable cavity/AO contribution in interproximal seams if it produces black stripes.
- Add a distinct scalloped gingival strip/material. It should cover cervical joins and remove the floating-block read.
- Neutral/speech gum exposure: 0. `EXP_smile` maximum gum exposure: ≤1 mm or ≤8% of `CH`, whichever is smaller. Surprise must not expose gum.
- Narrow the visible tongue surface to 50–62% of dental-arch width. Keep the apex 2–4 mm behind the lower incisors and 4–6 mm below their edges at rest.
- Tongue may occupy ≤25% of open-cavity area in `VISEME_A`, ≤18% in `VISEME_H`, and ≤10% in other visible poses.
- Lower teeth remain hidden in neutral and most vowels. Permit only a thin lower-incisor edge in explicitly tooth-contact shapes; never expose a full upper and lower “picket fence.”

## Required shape-key behavior

| Required key | V3 behavior at value 1.0 |
|---|---|
| `BLINK` | Upper lid supplies 70–80% of closure; lower lid rises 20–30%. Continuous slightly curved seam, subtle lower-lid compression, no sclera/iris leak, no globe scaling, brows unchanged. At 0.5, both eyes retain equal aperture within 5%. |
| `BROW_UP` | Visible brows and forehead move together: inner +4–5 mm, arch +6–8 mm, tail +4–6 mm. Upper lid may open 1–2 mm. Do not preserve a skeptical unilateral offset. |
| `BROW_DOWN` | Inner brow −4–5 mm and 2–3 mm medially; arch −3–4 mm; tail −1–2 mm. Add subtle upper-lid pressure. Do not turn the arches into a sad/worried inverted V. |
| `EXP_smile` | Mouth width +10–16%; corners rise 8–12% of `MW`; cheek mass rises 2–4 mm; lower lids narrow 5–10%. Show a connected upper-incisor band equal to 20–35% of `CH`; lower teeth and gums hidden. |
| `EXP_frown` | Corners descend 6–10% of `MW`, mouth width changes no more than 5%, lower lip/chin tension increases, cheeks settle slightly. Avoid an exaggerated horseshoe or lip-only pout. |
| `EXP_surprise` | Brows rise 6–8 mm, eye height increases 15–22%, jaw opens to a rounded aperture with `H/W=0.70–0.90` and width 70–85% of neutral `MW`. Upper central teeth ≤25% of `CH`; no lower teeth or gums; tongue low. |
| `LOOK_LEFT` | Both pupils travel conjugately 28–33% of `EW` toward character-left; vertical drift ≤2% of `EH`. Lids follow 10–15% of travel and keep even scleral exposure. Head and eye-object keys receive the same value. |
| `LOOK_RIGHT` | Exact mirrored behavior of `LOOK_LEFT` within 5% travel. Same lid-follow, catchlight, and eye-object synchronization rules. |

## Friendly, distinct viseme specification

Expression keys own cheeks and outer-face affect; visemes own inner lip contact, jaw/tongue articulation, and dental visibility. A viseme must not add a scowl.

| Viseme | Required silhouette and internal visibility |
|---|---|
| `VISEME_A` | Relaxed vertical opening, `H/W=0.70–0.85`; corners neutral; upper central teeth ≤20% `CH`; tongue low and ≤25% cavity. |
| `VISEME_B` | Firm but friendly bilabial seal; aperture 0; lip height compressed 10–15%; mouth width 92–97% of neutral. No teeth/tongue. |
| `VISEME_C` | Rounded forward funnel, width 52–62% of neutral, `H/W=0.75–1.00`; no teeth; central dark aperture with soft corners. |
| `VISEME_D` | Medium narrow opening, `H/W=0.30–0.42`; connected upper-incisor band 20–30% `CH`; tongue stays behind lower incisors. |
| `VISEME_E` | Horizontally spread mid-open shape, width 105–112% neutral, `H/W=0.24–0.34`; upper tooth band 25–35% `CH`; corners level, not a full smile. |
| `VISEME_F` | Clear lower-lip-to-upper-incisor contact; lower lip rolls inward 1–2 mm; only upper incisal edges show. This contact state must separate it from `VISEME_B`. |
| `VISEME_G` | Broad friendly “grin/ee” articulation, width 112–120% neutral, `H/W=0.18–0.28`; connected upper band 30–45% `CH`; slight cheek support but less than `EXP_smile`. |
| `VISEME_H` | Medium vertical opening, `H/W=0.50–0.68`; tongue tip visible behind or briefly between incisors by ≤2 mm and ≤18% cavity; no pinched corners. |
| `VISEME_X` | Relaxed rest seal: aperture 0, neutral width, no compression/purse and no teeth/tongue. It differs from `VISEME_B` by pressure and lip roll, and from `VISEME_C` by having no round aperture. |

## Rig implementation rules

1. Duplicate the V2 file to a V3 working file; never edit the audited source in place.
2. Correct `Basis` neutral first. Rebase every existing key so its authored result remains intentional after the neutral changes.
3. Create one source-of-truth control for each duplicated gaze name. Drive `GEO_AVERY_HEAD` and `GEO_AVERY_EYES` at 1:1.
4. Add synchronized brow deformation to `GEO_AVERY_BROWS`; the current head-only brow keys are insufficient.
5. Separate upper/lower dental motion and give the lower row and tongue a jaw-follow path. If facial bones are prohibited by export, add same-named driven keys to teeth/tongue while retaining the required head keys.
6. Use an opening clamp: expression plus viseme jaw aperture may not exceed 110% of the larger solo aperture. `EXP_surprise+VISEME_A` and `EXP_surprise+VISEME_H` must not double-open the jaw.
7. Lip-contact precedence: sealed/contact visemes (`B`, `F`, `X`) control the inner 60% of the lips; expression keys control corners/cheeks. A smile must not break `B`/`X` closure, and a frown must not break `F` tooth contact.
8. If combination correctives are permitted, keep them internal with a `CORR_` prefix and do not rename required keys. If extras are prohibited, resolve the same issues through driven dental/tongue motion and carefully localized key deltas.

## Expression and viseme combination tests

Run all tests at the locked QA camera and lighting:

1. Every required key at weights `0, .25, .50, .75, 1.0`.
2. All 9 visemes at weight 1.0 combined with neutral, `EXP_smile`, `EXP_frown`, and `EXP_surprise` at weights `.5` and `1.0`.
3. Critical stacks:
   - `VISEME_A + EXP_surprise`
   - `VISEME_B + EXP_smile`
   - `VISEME_C + EXP_frown`
   - `VISEME_D + EXP_smile`
   - `VISEME_E + EXP_smile`
   - `VISEME_F + EXP_smile`
   - `VISEME_G + EXP_smile`
   - `VISEME_H + EXP_surprise`
   - `VISEME_X + EXP_frown`
4. Pair transitions at `0/.25/.5/.75/1`: `B↔F`, `C↔X`, `D↔E`, `E↔G`, `A↔H`.
5. `LOOK_LEFT/RIGHT × BLINK` at blink `.25/.5/.75/1`, plus both brow keys at `.5/1`.
6. Independent internal left/right brow controls with neutral gaze and both gaze extremes.
7. Profile and three-quarter checks for smile, surprise, A, F, G, and H to expose dental/lip penetration hidden in front view.

## Acceptance contact sheets

Use one saved QA camera (85 mm-equivalent perspective or a documented orthographic match), fixed exposure, fixed key/fill/rim, neutral head pose, and no per-cell framing changes.

| Sheet | Required layout |
|---|---|
| Neutral calibration | 960×1200 front close-up plus left/right three-quarter and profile; overlay facial midline, canthi, pupil centers, brow endpoints/apices, commissures, and dental midline |
| Expressions | 3×3, 480×508 per cell: neutral, `BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT` |
| Visemes | 9×1, 480×508 per cell, exact required labels in A/B/C/D/E/F/G/H/X order |
| Combination matrix | 9 columns × 4 rows (neutral/smile/frown/surprise), 480×508 per cell |
| Transition strips | Five frames per critical pair at `0/.25/.5/.75/1` |
| Dental close-ups | Smile, surprise, A, D, F, G, H at 2× mouth crop, with gums/tongue visible where applicable |
| Eye/brow matrix | Neutral/up/down brows × neutral/left/right gaze × blink `0/.5/1` |

Every cell must print exact key names and numeric weights. Include one wireframe/solid-overlay version of the neutral, smile, surprise, and F poses.

## Measurable rejection criteria

Reject V3 if any condition is true:

### Contract and rig

- Any required key is missing, renamed, on the wrong required owner, or nonzero in the saved neutral.
- Head and eye-object gaze values differ by more than `0.001`.
- A required key produces no visible target-region movement at value 1.0.
- Visible brows remain static under `BROW_UP` or `BROW_DOWN`.
- Lower teeth or tongue remain head-locked while the jaw visibly opens.

### Eyes and brows

- Neutral pupil midpoint misses facial center by >1% `EW`.
- Left/right pupil-center height differs by >1 px at 960×1200.
- Neutral horizontal pupil offset within either aperture exceeds 2% `EW`.
- Pupil travel differs left versus right by >5% `EW`, or vertical drift exceeds 2% `EH`.
- Iris/pupil are not separately readable, iris annulus is <3 px, or catchlights differ in quadrant/size by >1 px.
- Blink leaves any ≥1 px sclera/iris leak, pinches through the globe, or changes globe scale by >1%.
- Neutral brow inner heights differ unintentionally by >0.10 `EH`; a bilateral brow key differs left/right by >5% displacement.
- Brows intersect lids, hair, or forehead, or fail to move with their head-skin deformation.

### Mouth, teeth, gums, and tongue

- Neutral visible lip envelope remains above `H/W=0.42`, upper lip remains thicker than lower, or either corner has a dark extension >4% `MW`.
- Dental midline differs from facial/mouth center by >1% `MW`.
- Any anterior interdental black slot is ≥1 px at 480×508 cell scale or >1 px at 960×1200 close-up.
- More than six upper crowns are clearly separated in a normal smile, any full lower row appears, or upper and lower rows form a picket fence.
- Gum is visible in neutral/speech or exceeds 1 mm / 8% `CH` in smile.
- Tongue exceeds its pose-specific cavity-area limit or crosses in front of lower incisors except the authored H contact.
- Teeth, gums, tongue, or lips penetrate, float, z-fight, or expose the dental base in any tested combination/profile.

### Expression and viseme quality

- Smile/frown changes only lips: cheek landmarks must move at least 1% of face width and smile lower-lid height must reduce 5–10%.
- Surprise mouth `H/W<0.70`, shows lower teeth/gum, or exposes >25% `CH`.
- Two visemes have the same lip-contact, tooth, and tongue state and also have silhouette IoU >0.90.
- Any critical viseme pair differs by <15% aperture area and <0.12 in `H/W` without a distinct contact state.
- Combined aperture exceeds 110% of the larger solo pose, or a sealed viseme leaks by ≥1 px.
- A landmark moves >2 px between adjacent 25% transition frames without a corresponding continuous silhouette change.
- Any non-target landmark drifts >1% of visible face width.

## Implementation order

1. Lock the QA camera, lighting, landmark overlay, and required-name validator.
2. Correct neutral lid aperture, neutral gaze, iris/pupil/catchlight, brow placement, and neutral lips.
3. Rebuild dental contacts/material/gums and narrow/reseat the tongue.
4. Rebase all existing keys to the corrected neutral.
5. Connect duplicated gaze keys and visible brow deformation; add jaw-follow for lower teeth/tongue.
6. Resculpt required expressions, then the nine visemes.
7. Add or tune combination correctives.
8. Generate every acceptance sheet and reject against the numeric gates above.

No source blend or repository file was modified during this audit.
