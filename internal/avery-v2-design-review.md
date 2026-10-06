---
cursor:
  subagentId: "bc-2a291974-7fab-5112-a1f9-2f0ba306a0bb"
---

# Avery Chen V2 — strict visual acceptance checklist

## Acceptance rule

V2 is accepted only when **every blocker below passes with recorded evidence**. Scores cannot average away a blocker. Measurements are taken on the unposed base mesh with an orthographic camera, in meters, before clothing volume is added unless stated otherwise.

Reviewers must not be asked to guess Avery’s ethnicity or gender. “Nonspecific” does not mean that skin tone or facial features can literally be demographic-free; it means Avery is designed as a coherent individual without a named demographic preset, exaggerated identity markers, or stereotypes. The surname **Chen is not a facial reference**.

## V1 review from the supplied previews

The README describes a valid link-and-play asset structure, but the visible V1 is not an acceptable V2 design baseline:

- The full-body render reads at roughly **6–6.5 head lengths**, with a large head, broad rigid upper silhouette, short/heavy lower silhouette, small hands, and a neck buried by the collar. Orthographic measurements are still required before changing geometry because the supplied perspective render is not a measurement plate.
- The very pale, low-variation peach skin and smoothed facial planes read as a stock/mannequin surface. The README’s `young_caucasian_female2` texture and gender-slider provenance must not be treated as V2 art direction or “fixed” by a simple color multiply.
- The long ribbed fringe fully hides one eye and brow. It defeats eye contact, expression reading, lip-sync review, and reliable head-turn deformation; the orange/copper shell also reads more like molded geometry than hair.
- The matched dark suit, striped tie, broad shoulders, and oxfords read as generic formal corporate or “costume bureaucrat,” not the requested contemporary professional-casual early-career analyst.
- The small square badge is not a plausible ID-card proportion. Its straps compete with the tie and collar and are at high risk of floating or intersecting.
- The zero-expression face has slightly parted lips, weak eyelid/brow definition, and a fixed stare. The expression sheet shows controls functioning, but several poses read as isolated mouth or eye changes rather than integrated facial action.
- The stills cannot prove weighting quality. The minimal contract skeleton makes shoulder collapse, forearm twist, elbow/knee pinching, jacket/groin clipping, hair/neck collision, and lanyard instability priority motion tests.

## Concrete V2 visual direction

Avery should read as a specific, credible **26-year-old early-career program analyst**: balanced adult proportions, relaxed upright posture, direct eye contact, and a warm attentive neutral expression. Use a cohesive face with subtle natural asymmetry and clearly modeled eyelids, nose, lips, jaw, ears, and brow structure. Use a **medium, neutral-warm complexion** with believable hue and roughness variation—not V1’s pale pink wash, an artificial “universal” beige, or a demographic label.

Hair should be short-to-medium, naturally textured, and kept off both eyes: for example, an ear-to-jaw-length layered side part or textured crop with a tucked/open side. It should have medium-to-dark neutral brown value variation and a soft strand-group silhouette, not parallel molded ribs.

Wardrobe should be current without performing “youth”: a soft unstructured jacket or overshirt in muted slate/moss, a fine-knit crew or open-collar knit in warm stone, straight charcoal trousers, and clean low-profile lace-up shoes. Remove the matching suit and striped tie. Use a correctly scaled muted lanyard with a blank portrait-format card. Fit should be intentional rather than boxy or body-concealing. No logos, seals, slogans, flags, partisan cues, uniforms, tactical details, or trend props.

Suggested display-space palette starting points: slate/moss jacket `#40504C`, warm-stone knit `#B8AA98`, charcoal trouser `#343A3D`, muted lanyard `#59696A`, dark umber shoe `#4A3C35`. These are camera-test anchors, not immutable material albedos.

## Required evidence package

- [ ] **BLOCKER — Measurement plates:** 2048 px orthographic front, side, and back views with crown, chin, acromion, elbow, wrist, crotch/hip joint, knee, ankle, hand, and foot landmarks labeled.
- [ ] **BLOCKER — Camera plates:** front and ±30° head-and-shoulders views using a 70–85 mm full-frame-equivalent lens at eye height, plus front/side/three-quarter full body using 50–70 mm. No wide-angle approval render.
- [ ] **BLOCKER — Neutral lighting:** locked neutral studio setup, neutral-gray background, fixed exposure/output transform, color and grayscale copies, and no beauty-only depth-of-field hiding defects.
- [ ] **BLOCKER — Functional sheets:** all nine visemes, all eight facial controls, all 20 named actions at start/key/extreme/end frames, plus front/side turntables.
- [ ] **BLOCKER — Thumbnail tests:** 200 px-tall full figure and 180 px-tall face crops in color, grayscale, and black silhouette.
- [ ] **BLOCKER — Clean-host report:** link-only host smoke test and both asset-doctor results, with no manual retarget, rebake, relink, or missing-file repair.

## 1. Character intent and representation

- [ ] **BLOCKER:** Avery remains 26, agency-neutral, nonpartisan, warm, competent, credible, and clearly a career civil servant—not political staff, military, law enforcement, or a campaign representative.
- [ ] **BLOCKER:** No facial, hair, body, wardrobe, color, or accessory decision is justified by a racial or gender stereotype. Source sliders and preset names are implementation inputs, not identity definitions.
- [ ] **BLOCKER:** V2 is a custom art pass, not V1 with recolored skin/hair. Face, body proportions, hair, wardrobe, lanyard, skin shader, and baseline expression all show authored changes.
- [ ] **BLOCKER:** In a blind review of at least five people, including at least three early-career/20–30-year-old viewers, at least 80% read Avery as an adult approximately **21–32**. Median ratings for “warm,” “competent,” “credible,” and “someone who could explain a federal process without talking down to me” are each at least **4/5**.
- [ ] **BLOCKER:** In the same review, median ratings for “partisan,” “costume bureaucrat,” “corporate executive,” and “trying too hard to look young” are each **2/5 or lower**.
- [ ] Review prompts assess age, role, affect, credibility, and relatability only; they do not ask viewers to classify ethnicity, sex, or gender.

## 2. Adult proportions and anatomy

The ranges below are a V2 design target, not a claim that all healthy adults share one body canon.

- [ ] **BLOCKER:** Canonical height is declared and preserved to ±5 mm through save/link. Target: **1.69–1.76 m**, with `Z=0` at the planted sole.
- [ ] **BLOCKER:** Crown-to-sole height is **7.25–7.75 anatomical head heights** (target 7.5), measured crown-to-chin without hair volume.
- [ ] **BLOCKER:** Floor-to-crotch/hip-joint height is **48–52%** of stature; knees sit near the midpoint between hip joint and ankle rather than low on a shortened leg.
- [ ] **BLOCKER:** Base-mesh acromion width is **2.0–2.35 head widths**; outer jacket width is no more than **2.45 head widths**. The intended front silhouette has a shoulder-to-hip breadth ratio of approximately **1.0–1.15**, avoiding V1’s top-heavy wedge.
- [ ] **BLOCKER:** In relaxed anatomical stance, elbows align with the waist/lower rib region, wrists reach the upper-thigh/crotch region, and fingertips reach mid-thigh. Left/right landmark error is ≤10 mm in the symmetric rest mesh.
- [ ] **BLOCKER:** Hand length is **0.70–0.80 head height** and foot length **0.95–1.15 head height**. Fingers, thumb web, heel, arch, ankle, and toe box have distinct readable form; no mitten hands or block feet.
- [ ] **BLOCKER:** Head, rib cage, pelvis, and feet face the same rest direction (`-Y`); spine has a restrained natural curve; pelvis is neutral; knees track over feet; feet are neither parallel boards nor excessively turned out.
- [ ] **BLOCKER:** Neck emerges visibly from the torso with trapezius and jaw clearance. Clothing must not make the head appear directly attached to the shoulders.
- [ ] **BLOCKER:** Eye globes are seated inside sockets and wrapped by upper/lower lids; ears join at anatomically plausible depth; nostrils, philtrum, lip rolls, chin, and jaw transition remain coherent in front, profile, and three-quarter views.
- [ ] **BLOCKER:** No child-coding anatomy: no oversized cranium/eyes, shortened midface, tiny jaw, or undersized body. No age-up cues such as deep static wrinkles or pronounced tissue sag.
- [ ] At rest, weight distribution feels stable: center of mass falls inside the foot support polygon and neither foot appears to float.

## 3. Silhouette and face readability

- [ ] **BLOCKER:** At 200 px full-figure height, head/neck, torso/pelvis, both arms/hands, and both legs/feet remain separable. Jacket and trousers do not merge into one rectangular column.
- [ ] **BLOCKER:** At 180 px face height, both pupils, upper lids, both brows, nose base, lip line, jaw, and chin remain readable in color and grayscale.
- [ ] **BLOCKER:** Hair leaves **100% of both pupils/irises** and at least **75% of each eyebrow arc** visible in front and ±30° views. A few wisps may cross the forehead but not the eyes.
- [ ] **BLOCKER:** Direct gaze is visually centered; pupil/catchlight placement matches between eyes within 1 px in the approval crop unless a deliberate gaze control is active.
- [ ] **BLOCKER:** Facial asymmetry is subtle and anatomical—approximately 1–3 mm in brow height, mouth corner, or jaw contour—not a mirrored mannequin and not a distorted eye/nose/mouth.
- [ ] **BLOCKER:** Avery remains recognizable from front, profile, and three-quarter views; the nose, lips, and chin do not flatten or jump in depth on rotation.
- [ ] Do not impose a “classical” facial ratio as an ethnicity proxy. Pass/fail is based on coherent anatomy, camera readability, and non-caricature, not conformity to one population-specific facial average.

## 4. Skin, eyes, and hair

- [ ] **BLOCKER:** Skin is a custom medium neutral-warm material with localized variation at cheeks, lids, lips, ears, and nose. It is not a uniform fill, simple warm multiply, or a named ethnicity texture used unchanged.
- [ ] **BLOCKER:** Under the locked approval light/output transform, fewer than **0.5%** of facial pixels clip at code 0 or 255; highlights retain pore/form detail and shadows retain the eye sockets, nostrils, and lip separation.
- [ ] **BLOCKER:** Shader has restrained subsurface response, zone-based roughness variation, and low-amplitude normal detail. Skin reads as living tissue, not wax, vinyl, chalk, or airbrushed porcelain at headshot distance.
- [ ] **BLOCKER:** Lips are related to—not painted independently from—the face; redness/saturation remains plausible under both neutral and slightly warm/cool test lights.
- [ ] **BLOCKER:** Sclera is off-white with subtle variation, not pure white; iris/pupil boundaries and corneal catchlights remain visible without glowing or “doll eye” contrast.
- [ ] **BLOCKER:** Hair has scalp coverage from front, side, back, and modest high angle; no bald gaps, open shell, repeated rib pattern, or abrupt card edge.
- [ ] **BLOCKER:** Hair-to-skin static clearance is ≥3 mm except at the intended hairline. Across every required action, there is no visible penetration through eyelids, cheeks, ears, neck, jacket, or collar.
- [ ] Hair value separates from the background and jacket in grayscale by enough contrast to retain the head contour; adjust lighting/material rather than adding an outline.

## 5. Wardrobe and lanyard

- [ ] **BLOCKER:** Replace the matching dark suit and striped tie with the specified soft-structured professional-casual system. The outfit looks plausible across agencies and is reusable across episodes.
- [ ] **BLOCKER:** Fit follows the revised body: shoulder seams land within 15 mm of the acromion, sleeves finish at the wrist, jacket hem ends around mid-hip, trouser crotch does not sag, and hems meet shoes without exposing gaps or swallowing the foot.
- [ ] **BLOCKER:** No logos, seal-like shapes, flags, readable text, slogans, tactical hardware, rank markers, campaign colors/marks, or agency-specific identifiers.
- [ ] **BLOCKER:** Fabric scale and roughness read at headshot and full-body distances. No moiré, specular crawling, painted-on seams, or tiny high-contrast patterns at 1080p.
- [ ] **BLOCKER:** Neckline frames rather than buries the neck and leaves the lanyard legible. Garment layers have believable thickness and do not z-fight.
- [ ] **BLOCKER:** Lanyard webbing is **10–15 mm** wide with plausible thickness; blank card is approximately **54 × 86 mm** in portrait orientation with mildly rounded corners—not V1’s small square.
- [ ] **BLOCKER:** Badge hangs centered on the sternum/upper chest, remains subordinate to the face, and has no logo, seal, text, barcode, flag, or agency color coding.
- [ ] **BLOCKER:** At rest, lanyard has 3–8 mm garment clearance and no floating strap segment. In motion it stays within 40 mm of the torso, never enters the body/collar/chin, and does not whip or jitter.
- [ ] **BLOCKER:** Hair and lanyard behavior is deterministic after linking. No unbaked cloth, hair, collision, or rigid-body simulation may be required at shot time.

## 6. Baseline expression, controls, and lip sync

- [ ] **BLOCKER:** Zeroed shape keys produce an attentive neutral: jaw relaxed, lips gently closed or separated by ≤1 mm, mouth corners level to subtly positive, brows relaxed, eyes focused, and no startled stare.
- [ ] **BLOCKER:** Neutral reads warm and available without a fixed grin. Smile, frown, surprise, brow, and gaze controls return exactly to the same zero state.
- [ ] **BLOCKER:** `BLINK` fully closes both lids over the globes with no gap, inversion, or eye penetration. At 50%, lid motion follows a natural arc rather than a linear shutter.
- [ ] **BLOCKER:** `BROW_UP` and `BROW_DOWN` move brow tissue with restrained forehead/upper-lid response; hair does not hide the result.
- [ ] **BLOCKER:** `EXP_smile` raises cheeks and slightly narrows lower lids in addition to moving lip corners. `EXP_frown` and `EXP_surprise` affect connected facial regions and avoid theatrical caricature or bulging eyes.
- [ ] **BLOCKER:** Gaze controls move both eyes together, keep pupils on the globe surface, preserve lid contact, and avoid cross-eyed or wall-eyed endpoints.
- [ ] **BLOCKER:** All nine required visemes are distinct and include readable closed-lip, wide/spread, open, rounded, labiodental, and tongue/alveolar classes as appropriate to the existing A–H/X map.
- [ ] **BLOCKER:** At a 180 px face crop, every speech viseme differs visibly from rest and adjacent classes; at full headshot, lips, teeth, and tongue never intersect or expose an empty mouth cavity.
- [ ] **BLOCKER:** Pairwise blends of each expression with representative visemes at 50% remain usable; no collapsed lips, doubled folds, exploding vertices, or identity drift.
- [ ] Teeth remain behind lips in neutral and do not form an unbroken bright strip during speech; tongue appears only when the viseme requires it.

## 7. Deformation and action checks

- [ ] **BLOCKER:** Render all 20 named actions from front and three-quarter cameras. Inspect every frame, not only endpoints.
- [ ] **BLOCKER:** Shoulder tests at 0°, 45°, 90°, and 120° arm elevation preserve deltoid/armpit volume; jacket shoulders do not cave in, spike, or detach. The `proxy_rig_v1` lack of contract clavicles must be solved with validated helpers or corrective shapes, not ignored.
- [ ] **BLOCKER:** Elbows and knees preserve at least **85%** of nearby straight-limb cross-sectional volume at maximum required bend; no pinching, inversion, or sharp tube hinge.
- [ ] **BLOCKER:** Forearm/wrist and thigh/shin twist shows no candy-wrapper collapse. Hands stay aligned with forearms; feet stay aligned with shins.
- [ ] **BLOCKER:** Neck turns/nods preserve throat and jaw volume and do not pull the collar, hair, or shoulders into the face.
- [ ] **BLOCKER:** Jacket collar/lapels, underarm, elbows, hem, trouser crotch, knees, cuffs, shoes, hair, and lanyard show **no visible interpenetration at 1080p for any frame**. Hidden penetration may not exceed 3 mm.
- [ ] **BLOCKER:** `point_left`, `point_right`, `gesture_present`, `wave`, `reach_grab`, and `place_release` read unambiguously at medium-shot scale. Hands must have intentional relaxed/open/indicating shapes, not rigid splayed fingers.
- [ ] **BLOCKER:** Additional hand or corrective bones are allowed only if the clean-host and asset-doctor tests explicitly accept extras and the required skeleton is unchanged. Otherwise use self-contained corrective shape/driver solutions.
- [ ] **BLOCKER:** Planted foot drift is ≤10 mm during contact phases; feet do not penetrate the ground by more than 3 mm or float more than 5 mm.
- [ ] **BLOCKER:** `turn_left_90` and `turn_right_90` end at **90° ±1°** in the documented direction without unintended scale or vertical root drift.
- [ ] **BLOCKER:** First/last frames of `idle_neutral_loop` and `walk_cycle` match within 1 mm translation and 0.1° rotation on every contract bone, with no visible seam in two repeated cycles.
- [ ] Body-volume change caused by skinning is ≤10% at shoulders, elbows, hips, and knees between neutral and tested extremes, excluding intentional muscle compression.

## 8. Pipeline construction gate

- [ ] **BLOCKER:** The linked collection is exactly `COL_AVERY_CHEN`; armature object `RIG_AVERY_CHEN`; armature data `RIG_AVERY_CHEN_DATA`. The host can link the collection and play actions without retargeting, baking, or manual setup.
- [ ] **BLOCKER:** Scene uses meters, `Z` up, `-Y` forward, scale 1.0. Armature/root origin is on the ground plane under the character; armature and export meshes have location `(0,0,0)`, rotation `(0,0,0)`, and scale `(1,1,1)` in the authored rest state.
- [ ] **BLOCKER:** All 18 required contract bones exist with exact names and documented parent hierarchy; no required bone is renamed, reparented, scaled non-uniformly, or repurposed. Pose bones remain XYZ Euler where the host expects it.
- [ ] **BLOCKER:** Interaction points remain `hand_left → hand.L` and `hand_right → hand.R` and follow the visible palm location within 20 mm.
- [ ] **BLOCKER:** Mesh naming and separation remain unambiguous for head/body, eyes, brows, hair, shoes, teeth, tongue, and lanyard. Every deforming mesh has one intended armature path; no duplicate hidden body or renderable proxy survives.
- [ ] **BLOCKER:** Deform weights are normalized to **1.00 ±0.01**, reference only existing deform bones, and use no more than four nonzero influences per vertex unless the host explicitly supports more. Zero-weight and unbound vertices are absent.
- [ ] **BLOCKER:** Shape keys remain on the head mesh with exact names: `VISEME_A`–`VISEME_H`, `VISEME_X`, `BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT`. No modifier order or topology edit invalidates them.
- [ ] **BLOCKER:** All 20 required actions retain exact names, object-action ownership on `RIG_AVERY_CHEN`, one valid object slot, fake user, documented frame counts, categories, and loop flags. No action depends on the currently open scene or NLA state.
- [ ] **BLOCKER:** File has no missing external texture, font, cache, linked-library, or simulation dependency when copied to a clean host. Paths are packed or project-relative and resolve without the authoring machine.
- [ ] **BLOCKER:** No nonuniform negative scale, unapplied mirror, invalid normals, nonmanifold tears, duplicate faces, z-fighting surfaces, or render-disabled object needed for the final appearance.
- [ ] **BLOCKER:** Final complexity is declared and kept at **≤80,000 rendered triangles** and **≤32 MB texture memory** unless the production manifest budget is explicitly raised. Transparent hair cards are included in the count.
- [ ] **BLOCKER:** `pipe asset doctor char.avery_chen`, `pipe asset doctor char.avery_chen --blender`, and the link-and-play host smoke test all pass from a clean unpacked pipeline.
- [ ] **BLOCKER:** Final `.blend` is reopened and reverified after the last save; manifest version/style ID, Blender minimum, triangle count, texture estimate, source/license record, and SHA-256 match the delivered bytes.

## Final hard-reject list

Reject V2 immediately if any of these remain: under-7-head childlike proportions; one eye/brow hidden by hair; hanging-open neutral mouth; pale uniform mannequin skin; a demographic preset used as the design rationale; matched formal suit plus striped tie; square/floating badge; agency or political marking; visible body/clothing/hair/lanyard penetration; broken shoulders/elbows/knees; unreadable visemes; foot sliding; missing dependency; renamed/reparented contract bone; or any requirement to retarget, rebake, or repair the asset after linking.

## Sign-off

- [ ] Visual lead: all representation, direction, anatomy, silhouette, material, wardrobe, hair, and expression blockers pass.
- [ ] Rig/animation lead: all deformation, facial-combination, loop, contact, and action-semantic blockers pass.
- [ ] Pipeline lead: all contract, clean-host, doctor, dependency, budget, manifest, and hash blockers pass.
- [ ] Target-audience review meets the age, warmth, competence, credibility, relatability, and non-caricature thresholds above.

Only after all four sign-offs is the asset eligible to be labeled `avery_chen_v2`.
