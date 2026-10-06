---
cursor:
  subagentId: "bc-99a0d8d1-aa12-5ac7-a905-8e1dd763a972"
---

VERDICT: PASS WITH NOTES

## Evidence and build

- **Batch:** final **24-sheet** set, **2026-09-30 21:12–21:24 UTC**, single generation under `media/avery-chen-v3/`.
- **Blend:** sha256 **`751fd05872f4730ef39cec3160395b431693304a91a5283e6448199739f6f6bc`** (matches expected).
- **Triangles:** **66,402** (`internal/avery-chen-v3-verify.txt`, `RESULT: PASS`).
- **Builder intent in scope:** no EXP_smile/VISEME_G coupling; no lower tooth row, tongue, or mouth cavity; upper arc behind lips; sealed Basis/closed visemes; surprise without lower dental; pupil alignment pass.
- **References:** `internal/v3-facial-rig-plan.md`, `media/reference/patty-patties-style.jpg`, `docs/avery-chen/README.md`.

Judgment uses **only this batch** (not 20:03 or 18:08 sheets).

## Blocker checklist (user request)

| Check | Result | Evidence |
|---|---|---|
| Neutral enamel peek | **Clear** | `front-closeup.png`, `eye-brow-alignment.png`, `closeup-profile.png`, `viseme-strip.png` — **0%** white in lip bbox sampling. `expression-sheet.png` **NEUTRAL** ~**0.02%** white. `eye-brow-matrix.png` all cells **sealed**. `neutral-calibration.png` FRONT/3-4/PROFILE closed. |
| Exterior / chin bars | **Clear** | `dental-sheet.png` all panels — no white on skin; chin-zone white **0%**; prior floating bars **gone**. |
| Smile tear / interior junk | **Clear (lip mesh)** | `expression-sheet.png` **EXP_SMILE** — wide **closed** smile, **no** oral tear or interior pink mass. `dental-sheet.png` **EXP_SMILE** — sealed lips; **note:** subtle **cheek stretch lines** (~4% pink-line sampling in cheek band), not lip penetration. |
| Lower surprise band | **Clear** | `expression-sheet.png` **EXP_SURPRISE**, `facial-angle-matrix.png` SURPRISE row, `dental-sheet.png` **EXP_SURPRISE** — **upper band only**; dark interior void, **no lower row**. |
| Dental penetration | **Clear** | All retest sheets; upper arc sits **behind** lip line in open visemes (`viseme-strip.png`, `facial-angle-matrix.png`, combos, transitions). |
| Wall-eye | **Clear** | `eye-brow-alignment.png` pupils on shared horizontal guide; `eye-brow-matrix.png` / `expression-sheet.png` **LOOK_*** conjugate. `front-closeup.png` inspection: **mild convergence** on one eye only — **not** wall-eye; does not fail this gate. |

## Minimum retest sheets

| Sheet | Verdict | Notes |
|---|---|---|
| `front-closeup.png` | Pass | Firm lip seal; direct gaze; integrated hero. |
| `closeup-three-quarter.png`, `closeup-profile.png` | Pass | Closed neutral; no enamel; profile depth OK. |
| `eye-brow-alignment.png` | Pass | Midline overlay; sealed mouth; pupils level. |
| `neutral-calibration.png` | Pass | Four-view neutral consistent. |
| `expression-sheet.png` | Pass w/ note | All keys readable; **EXP_SMILE** is **closed-lip** (no upper band) — differs from plan’s toothed smile but matches builder simplification. |
| `dental-sheet.png` | Pass w/ note | Open visemes show **continuous upper band** + dark void; **EXP_SMILE** cheek stretch artifact only. |
| `facial-angle-matrix.png` | Pass | NEUTRAL sealed; SMILE closed; SURPRISE / **VISEME_F** upper arc clean in 3 angles. |
| `eye-brow-matrix.png` | Pass | Full 3×9 brow × gaze × blink — gold standard. |
| `viseme-strip.png` | Pass | Distinct A–X; B/E/X-class seals; upper band when open. |
| `expression-viseme-combos.png` | Pass | 4×9 stacks clean; smile/surprise combos without lower teeth or leaks. |
| `transition-strips.png` | Pass | Critical pairs smooth; sealed ends **~0.05%** mouth white (negligible). |

## Functional quality vs plan

- **Eyes / lids / gaze:** Blink and look keys **pass** on matrices and expression sheet. README **emissive catchlights** and slightly tall lids **accepted**. Automated dark-centroid vertical delta ~**6 px** on `front-closeup.png` (lashes/sampling); **alignment plate reads level** — not treated as blocker.
- **Brows:** Seated and expressive on matrix and expression sheet; stylized thin brows remain **cooler** than Patty reference (warmth note only).
- **Teeth:** Upper **slab arc** meets “continuous band, no picket fence”; intentionally **flat** vs reference smile — acceptable for V3 simplification.
- **Warmth / appeal:** `reference-comparison.png` — coherent, trustworthy; still **stiffer** than Patty teaching smile (non-blocker).

## Residual notes (non-blocking)

1. **`dental-sheet.png` `EXP_SMILE=1.00`** — horizontal cheek **deformation streaks** at wide closed smile; monitor if they read as uncanny in motion.
2. **`EXP_SMILE` without visible upper incisors** — functional closed smile; differs from `v3-facial-rig-plan.md` **EXP_smile** tooth-band spec unless keyed separately in production.
3. **Open-mouth interior** is a **dark void** (no tongue/cavity) — correct per builder, less realistic than reference surprise “O.”

## Conclusion

Facial QA **accepts** the final **751fd058…** hero for the stated dental/gaze blockers. Remaining items are **documentation / appeal**, not rejection triggers.
