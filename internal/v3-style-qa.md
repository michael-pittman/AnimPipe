---
cursor:
  subagentId: "bc-e989c532-48e0-5b33-bbfd-62a3c856454c"
---

VERDICT: PASS WITH NOTES

## Scope

Style-fidelity review of the **unified evidence batch** (PNG mtimes **2026-09-30 20:03–20:15 UTC**). Inspected all **24** PNGs in `media/avery-chen-v3/`, plus `media/reference/patty-patties-style.jpg`, `internal/v3-style-translation.md`, `docs/character-direction.md`, `docs/avery-chen/README.md`, `docs/avery-chen/build.json`, and `internal/avery-chen-v3-verify.txt`. Judgment is based on **this** hash’s pixels only (not the prior `9555e8cf…` / `82918` tris set).

## Build and verify

| Check | Result |
|---|---|
| Blend sha256 | **`6b4e64ec715979278d1f00c643e546fb11884bd2f5eb5a24f71ed59358dcc12e`** — matches expected hash (`build.json`, on-disk `assets/characters/AveryChen.blend`) |
| Render tris | **66,792** — matches verify log and `build.json` |
| Packed | **PASS** — no external images / linked libraries (`avery-chen-v3-verify.txt`) |
| Reopen verify | **`RESULT: PASS`** |
| PNG set | **24/24** present; sha256 entries in `build.json` `renders[]` |

## Summary

The recovered hero now **translates reference principles** at full-body and turntable distance: warm deep-brown skin, Black woman read, rounded bespectacled face, navy utility stack, teal lanyard + neutral badge, magenta/teal accent discipline, high textured crown mass, tapered trouser + sneaker silhouette, and **no** copied PattyPatties branding or federal credential mimicry (`reference-comparison.png`).

Wardrobe and hair refactors from the builder are **visible in the new batch**:

- **Open utility jacket + shirt:** lapels open over a light shirt panel and lanyard (`full-body-front.png`, `full-body-three-quarter.png`, `wardrobe-proof.png`, `reference-comparison.png`).
- **Raglan yokes + rolled cuffs:** short navy sleeves with magenta **band** cuffs; raglan seam read on shoulders (`turnaround.png`, `full-body-back.png`, `wardrobe-proof.png`).
- **Single-surface patches:** chest and upper-arm accents read as one woven spark/chevron family—not the prior floating bar stacks (`turntable.png`, `action-sheet.png`, `deformation-sheet.png`).
- **Braided crown:** three-lobe magenta/espresso crown with nape coil and scalp channel routing at medium shots (`turnaround.png`, `turntable.png`, `full-body-back.png`, `wireframe-overlay.png`).

Contract and style **proxy** gates can advance with the notes below; this is **not** a claim of full §11 art-lock parity with `v3-style-translation.md`.

## Major notes (ship risk — not primitive-batch regressions)

### 1. Disclosed residual armscye gap (special attention)

Raglan torso and rolled sleeve tubes are **restored and parented**, but a **continuous cloth bridge at the armscye is still missing** at neutral and worsens with raise (aligned with `docs/avery-chen/README.md` and `internal/avery-chen-v3-hero-recovery.md` disclosures).

- **Neutral / 360°:** visible sleeve–torso slot or background readthrough (`turnaround.png`, `turntable.png` — multiple yaw panels, `wardrobe-proof.png`, `full-body-front.png`, `full-body-side.png`, `full-body-back.png`).
- **Bust scale:** jagged armscye edges on jacket panels (`expression-sheet.png`, `front-closeup.png`, `wireframe-overlay.png`).
- **90°–120°:** gap and cuff/patch accent separation increase (`shoulder-tests.png`); gesture poses (`action-sheet.png` **`WAVE`**, `deformation-sheet.png` **`GESTURE_PRESENT`** frames **10** / **19**).

**Ask:** acceptable for proxy explainer if shoulders rarely above 90°; **not** reference-closed. Track for a future armscye fill or weight pass before hero marketing stills.

### 2. Band-like cuffs and patches (special attention)

Rolled cuffs and sleeve/chest patches read as **flat magenta/teal bands** at production scale rather than §5’s 0.3–0.5 mm embroidered relief and staggered bar read.

- **Evidence:** `full-body-back.png`, `wardrobe-proof.png`, `turntable.png`, `full-body-front.png`.
- **Judgment:** matches intentional **single-surface** patch construction; acceptable proxy simplification **if** armscye note is accepted.

### 3. Curve-proxy hair vs sculpted updo (special attention)

Medium shots show the **32-channel three-lobe crown + nape coil** target (`turnaround.png`, `turntable.png`, `reference-comparison.png` hero panels). Closeups still expose **curve-tube / sparse crown** read and scalp channel wires (`closeup-profile.png`, `closeup-three-quarter.png`, `neutral-calibration.png` **BACK HAIR** / **PROFILE NEUTRAL**).

**Judgment:** consistent with builder “curve-proxy, not sculpted mesh updo” (`internal/avery-chen-v3-hero-recovery.md`); acceptable for talking-head distance, weak for beauty crops.

## What cleared (vs prior style FAIL)

| Prior blocker | This batch |
|---|---|
| Floating orphan shoulder markers | **Cleared** — accents attach to sleeve/raglan pieces (`action-sheet.png`, `turnaround.png`) |
| Sleeveless vest / no open jacket | **Cleared** — open lapels + shirt (`wardrobe-proof.png`, `reference-comparison.png`) |
| Coil-helmet hair only | **Improved** — three-lobe crown + channels (`turntable.png`, `wireframe-overlay.png`) |
| Detached limbs / peach mannequin | **Cleared** — coherent MakeHuman body throughout motion sheets |

## Focused checklist

| Requirement | Result |
|---|---|
| Black woman / warm deep-brown skin | **Pass** — full-body + comparison set |
| Glasses, approachable face | **Pass** — bust/full-body; lip dental peek out of scope here |
| Navy utility + magenta/teal accents | **Pass** |
| Open jacket framing light shirt (not chest skin bleed) | **Pass** — shirt panel visible; inappropriate torso skin gap **not** the primary defect |
| Rolled sleeves | **Partial** — cuff **bands** present; armscye gap limits “finished sleeve” read |
| Spark/chevron neutral patches | **Partial** — present, band-like at distance |
| 360° hair routing | **Partial** — back/side adequate at medium shot; closeups weak |
| Arm raise / deformation | **Note** — usable locomotion; armscye opens under gesture |
| Prohibited branding | **Pass** |

## Files reviewed

All 24 PNGs: `action-sheet.png`, `closeup-profile.png`, `closeup-three-quarter.png`, `deformation-sheet.png`, `dental-sheet.png`, `expression-sheet.png`, `expression-viseme-combos.png`, `eye-brow-alignment.png`, `eye-brow-matrix.png`, `facial-angle-matrix.png`, `front-closeup.png`, `full-body-back.png`, `full-body-front.png`, `full-body-side.png`, `full-body-three-quarter.png`, `neutral-calibration.png`, `reference-comparison.png`, `shoulder-tests.png`, `transition-strips.png`, `turnaround.png`, `turntable.png`, `viseme-strip.png`, `wardrobe-proof.png`, `wireframe-overlay.png`.

Facial/dental sheets were scanned for wardrobe/hair intersection only; numeric facial gates remain in `internal/v3-face-qa.md`.

## Disposition

**PASS WITH NOTES** for V3 **style proxy** acceptance on hash `6b4e64ec…`. Before final art-lock or marketing beauty frames: close neutral armscye visually, thicken patch/cuff embroidery read, and add close-range hair volume if beauty crops are in scope.
