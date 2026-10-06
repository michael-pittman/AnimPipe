---
cursor:
  subagentId: "bc-da984421-d0d2-5651-9409-b49d2aca6af7"
---
# Avery Chen V3 facial-plan application

The measured plan in `internal/v3-facial-rig-plan.md` was applied to the procedural builder before the eyes, brows, teeth, neutral expression, eight expression controls, nine visemes, and contact sheets were treated as final. Contract verify on the shipped blend is `RESULT: PASS`.

## Shipped blend

| Item | Value |
|---|---|
| sha256 | `8d92e984fc5b4351cc137ace90acaa830e6a6482d2aaa215ef87565ded082793` |
| Triangles | 20180 |
| Texture memory | 0.0 MB |
| Blender | 5.2.1 |
| Store blend | `docs/avery-chen/AveryChen.blend` |
| Repo blend | `assets/characters/AveryChen.blend` |
| Builder | `scripts/build_avery_chen.py` |
| Verify | `internal/avery-chen-v3-verify.txt` |

V2 archive `docs/avery-chen/archive/AveryChen-v2.blend` is unchanged (`4c09c2fd…`). Nothing was committed.

## What the plan changed

- Iris, pupil, and a matched catchlight sit in a front opening of each sclera. The old glossy cornea shell was covering the iris.
- Glasses lenses are a separate thin-wall object (`GEO_AVERY_LENSES`). The previous lens cards used the opaque frame material and hid the eyes.
- Brow meshes still follow `BROW_UP` / `BROW_DOWN`, and gaze keys stay driven 1:1 between the head and the eyes.
- Blink now moves the real lid ring. An earlier index mismatch was dragging unrelated vertices and leaving the eyes open.
- Lips overlap at rest so the neutral seam does not show enamel. The smile rolls the upper lip back and shows a short upper tooth band. Lower teeth stay behind that lip.
- Anterior crowns use broad incisal faces with about a 0.04 mm contact gap. The cervix is tucked behind the lip. A jaw clamp still caps combined openers at 110% of the larger solo aperture.
- Transition strips for B↔F, C↔X, D↔E, E↔G, and A↔H are in the evidence set.

## Pixel checks on the final close-up

On `front-closeup.png` (960×1200, 8 samples):

- Modeled catchlights are both 8×8 px, centroids y = 548.50 and 548.43 (0.07 px apart), in the same upper quadrant toward character-left.
- A vertical sample through the open eye is a dark pupil with a warmer iris on both sides. Blink at the same column replaces that dark run with lid skin. No sclera/iris leak remains on that sample.
- `LOOK_LEFT` moves both catchlights together and keeps them the same size within 1 px.

## Limitations

- Visible lid aperture is still a little taller than the plan's 0.34–0.40 EH/EW target. That ratio is not one of the rejection bullets. Iris diameter stays inside 50–56% of EW.
- Catchlights are small emissive discs parented to the iris, so they travel with gaze. They do not behave like a specular that stays nearly fixed in world space.
- The key light brightens the viewer-left sclera more than the viewer-right sclera. The two catchlight discs still match.
- The smile band is a short connected upper arc, about 21% of crown height in the dental crop. A few interdental pixels are warm shadow rather than a hard black slot. It is not a full lower row.
- No wireframe overlay sheet was rendered.
- Doctor, a clean LFS clone, and the audience study were not run here.
---
