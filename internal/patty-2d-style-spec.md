---
cursor:
  subagentId: "bc-93be7bb4-81bf-5dd0-b810-158169bbfe95"
---

# Patty Patties — 2D production style spec

**Source of truth:** `media/reference/patty-patties-style.png` (480×360; use PNG over JPG when both exist).  
**Character:** Patty Patties — modern U.S. federal employee, friendly “federal-employee-next-door,” professional and upbeat.  
**Render mode:** Fully articulated **2D illustrated cutout** (flat/cel fills, thin ink outlines, soft airbrush accents only where the sheet uses them). Must read as the **same illustrated character** in a 3D Blender scene — **not** stylized-realistic 3D, not a redesign, not a different face/body/wardrobe.

**Shape-key / action contract:** Names and sets match `internal/character-contract.md` (proxy kit): 20 actions, Rhubarb visemes `VISEME_A`–`VISEME_H` + `VISEME_X`, expressions `BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT`.

---

## 1. Art direction lock

| Principle | Rule |
|---|---|
| Line | Single consistent **thin dark ink** (~1–1.5 px at 480 px sheet scale); outer contour slightly heavier than interior fold lines. Ink reads **deep navy–graphite**, never pure `#000000` except intentional lash dots. |
| Color | **Flat cel** base fills + **one cel shadow step** per material; optional **soft gradient** on skin, hair curls, and sneaker highlights only (match sheet). No PBR, no normal maps, no photographic skin. |
| Face | Large warm **brown eyes**, thick upper lashes, **thin rectangular-round glasses**, medium-brown skin, closed friendly neutral mouth by default. |
| Hair | **High curly updo** (bun/ponytail mass) — **near-black base** with **magenta/pink highlight curls**; volume is a primary silhouette element. |
| Wardrobe | **Open navy utility/bomber jacket** (rolled sleeves → **teal lining**), **white turtleneck** under **teal collar/shirt**, **navy cargo trousers** with **magenta drawstring**, **chunky sneakers** (white/navy/electric blue/magenta). **Blue lanyard + federal ID badge** on chest. **Black smartwatch** left wrist. **US patch** upper arm; **large silver eagle crest** on jacket back + **magenta collar stripe** (back). |
| Attitude | Approachable, competent, teaching/presenting energy — never stern, never sarcastic, never “action hero.” |

### Proportions (match turnaround)

- **~7–7.5 heads** tall (sole to crown); **+1 head** to tip of tallest hair curl in neutral.
- **Head:** slightly large vs. realistic adult (sheet style), but **not chibi** — full teen/adult neck and shoulders visible.
- **Shoulders:** moderately broad; jacket sits **open** with visible white/teal center column.
- **Legs:** long, **tapered cargo jogger** silhouette; cuffs sit above **chunky sneaker** collar.
- **Hands:** simplified but readable **five-finger** hands; fingers taper; nails not detailed.
- **Feet:** sneakers **~1.2×** natural foot length in side view (sheet chunkiness).

---

## 2. Exact palette (hex sampled from style sheet)

Values below are **median RGB eyedrops** from `patty-patties-style.png` (palette row ~y=300 and character fills). **Lock these for production**; re-sample only if the PNG master is replaced.

### 2.1 Sheet “Color Palette” swatches (canonical)

| Token | Hex | Use |
|---|---|---|
| `NAVY_PRIMARY` | `#0E274A` | Jacket body, trouser base, sneaker navy panels, primary shadows on blue garments |
| `TEAL_SECONDARY` | `#088D94` | Shirt/collar, rolled-sleeve lining, teal accents on badge/graphic elements |
| `ELECTRIC_BLUE_ACCENT` | `#0A7FFF` | Jacket trim highlights, sneaker panels, hologram/UI accents in pose art |
| `MAGENTA_ACCENT` | `#F51496` | Hair highlight curls, waist drawstring, shoe accents, back collar stripe |
| `SILVER_NEUTRAL` | `#BCBBCA` | Eagle crest, metallic UI/bezel reads |
| `GRAPHITE_NEUTRAL` | `#424348` | Glasses frame, watch, tablet bezel, deep neutral props |
| `SOFT_WHITE_NEUTRAL` | `#F7F7FF` | Turtleneck, sneaker base, badge card field, spec highlights on white materials |

### 2.2 Character-specific fills (sampled + sheet-verified)

| Token | Hex | Use |
|---|---|---|
| `INK_OUTLINE` | `#1E2534` | Primary outer outline; lash clusters |
| `INK_INTERIOR` | `#2B2D41` | Interior garment folds, secondary outlines |
| `SKIN_BASE` | `#D28469` | Face/neck/hands midtone |
| `SKIN_SHADOW` | `#A8756A` | Cel shadow under jaw, nose side, knuckles (derive if needed ±8% luminance from base) |
| `SKIN_HIGHLIGHT` | `#E8A88C` | Forehead/nose bridge/cheek soft gradient peak |
| `HAIR_BLACK` | `#1F0710` | Updo mass, edges |
| `HAIR_MAGENTA_STREAK` | `#E986B4` | Curly highlight locks (may grade toward `#F51496` at streak core) |
| `EYE_IRIS` | `#7D4A35` | Iris fill (warm brown; sheet reads dark at small size) |
| `EYE_PUPIL` | `#2A1810` | Pupil |
| `EYE_SCLERA` | `#F5ECE8` | Sclera (warm off-white) |
| `LIP_NEUTRAL` | `#C97862` | Closed lip fill |
| `LIP_LINE` | `#8B4A3A` | Lip seam (subtle; not black) |
| `TEETH_BAND` | `#F0EDE8` | **Single continuous upper arc** when visible — not separate white blocks |
| `MOUTH_INTERIOR` | `#6B3D45` | Inside mouth when open (dark, low contrast) |
| `GLASSES_LENS` | `#E8EDF5` | Lens fill ~15% opacity over eye if layered |
| `LANYARD_STRAP` | `#0A7FFF` | Strap (electric-blue family, matches sheet) |
| `BADGE_HEADER` | `#0E274A` | “Federal ID Badge” bar |
| `JACKET_NAVY_FILL` | `#2B2D41` | On-character jacket midtone (slightly lifted from swatch for line art) |
| `TROUSER_NAVY_FILL` | `#0E274A` | Trouser flat fill |
| `CARGO_POCKET` | `#152A4A` | Pocket panel shadow |
| `SNEAKER_WHITE` | `#E1E8F5` | Upper base |
| `SNEAKER_EBLUE` | `#0A7FFF` | Side panels |
| `SNEAKER_MAGENTA` | `#F51496` | Heel/tab accent |

**Tolerance:** Perceptual ΔE ≤ 3 vs. table for flat fills at 100% zoom on PNG; cel shadow steps may shift ±5% luminance but **hue family must not change**.

---

## 3. Layer stack (2D cutout for Blender)

All layers are **coplanar billboards or thin orthographic meshes** parented to rig bones (see separate rig plan). **Sort back → front** along camera forward axis. Alpha edges **premultiplied**; no halos on `#F7F7FF` background exports.

| Order | Layer ID | Parent bone (typical) | Notes |
|---:|---|---|---|
| 1 | `HAIR_BACK` | `head` | Large updo/ponytail mass; magenta streak curls; extends below jacket collar in back/3-4 |
| 2 | `TORSO_SHIRT` | `chest` | Teal shirt + white turtleneck column; excludes jacket flaps |
| 3 | `TORSO_JACKET_BACK` | `chest` | Back panel when view ≥ 90°; eagle crest on separate sub-layer `JACKET_EAGLE` optional |
| 4 | `ARM_UPPER_L` / `ARM_UPPER_R` | `upper_arm.L/R` | Rolled sleeve volumes |
| 5 | `ARM_FORE_L` / `ARM_FORE_R` | `forearm.L/R` | Teal lining visible on rolled cuffs |
| 6 | `HAND_L` / `HAND_R` | `hand.L/R` | Includes watch on `HAND_L` sub-layer |
| 7 | `TROUSERS` | `pelvis` | Cargo pockets as drawn shapes; magenta cord on waist sub-layer |
| 8 | `SHOE_L` / `SHOE_R` | `foot.L/R` | Chunky sneaker; side panels swap for outer leg |
| 9 | `TORSO_JACKET_FRONT_L` / `_R` | `chest` | Open jacket flaps; US patch on `JACKET_PATCH_L` |
| 10 | `NECK` | `neck` | Skin bridge |
| 11 | `HEAD_SKIN` | `head` | Face oval; ears if not separate |
| 12 | `MOUTH_TEETH` | `head` | **Hidden at 0** neutral; teeth as **one merged upper band** |
| 13 | `MOUTH_INTERIOR` | `head` | Dark cavity; only when jaw open |
| 14 | `MOUTH_LIPS` | `head` | Lip shapes driven by visemes/expressions |
| 15 | `EYE_L` / `EYE_R` | `head` | Sclera + iris + pupil art (or split iris for `LOOK_*`) |
| 16 | `EYELID_L` / `EYELID_R` | `head` | Upper/lower lids; `BLINK` closes upper over lower |
| 17 | `BROW_L` / `BROW_R` | `head` | Full dark brows |
| 18 | `GLASSES` | `head` | Single frame; does not scale independently of head |
| 19 | `HAIR_FRONT` | `head` | Forecurls/fringe; must **sit above** glasses temples where sheet shows |
| 20 | `LANYARD_BADGE` | `chest` | Strap + card; **last** among torso props so it floats on jacket |

**View-dependent swaps:** Use discrete texture sets or mesh visibility for **front / 3-4 / side / back** (§4), not live perspective warp. `HAIR_BACK` + `HAIR_FRONT` must never z-fight; separate by ≥2 mm in rig space if needed.

---

## 4. Turnaround drawing rules

### 4.1 Front (0°)

- Feet **shoulder-width**, toes slightly out.
- Lanyard **centered**; badge readable.
- Jacket **open symmetrically**; teal shirt column aligned on body midline.
- Glasses **symmetric**; pupils ** centered** in lenses.
- Hair updo **centered**; magenta streaks on **viewer-left and viewer-right** as sheet.

### 4.2 Three-quarter (~35–45°, sheet “3/4 view”)

- **Left or right** as master sheet (character turned slightly to her **left** in reference).
- **Far eye** slightly narrower; **near cheek** fuller.
- Jacket lapel overlap: **near flap covers far**.
- Updo mass shifts **away from camera**; expose **one ear** if sheet does.
- Maintain **same ink weight** as front (do not thin lines on far side).

### 4.3 Side (90°)

- Profile matches sheet: **strong nose/lip projection**, glasses temple **straight back**.
- Updo silhouette **tallest** in this view.
- Sneaker **toe box + sole thickness** readable.
- US patch on **forward arm** only.

### 4.4 Back (180°)

- **Silver eagle crest** centered upper back; **magenta vertical stripe** at collar base per sheet.
- Hair mass **widest** view; no face layers visible except edge of ear if drawn.
- Jacket hem **level**; cargo pockets **symmetric**.

**Consistency:** Head scale, eye size, and shoulder width **constant** across views; only foreshortening allowed is baked into each view’s drawn art.

---

## 5. Neutral expression (Basis / `pose_neutral` / `idle_neutral_loop` face)

| Feature | Rule |
|---|---|
| Eyes | **Both irises/pupils on same horizontal line** (≤0.5 px at sheet scale); **equal size**; gaze **straight to camera** (production default). |
| Lids | Upper lid **rests on top ~10% of iris**; lower lid **touches iris**; no sclera gap above/below. |
| Brows | **Seated** on brow bone; inner brow **softly arched** (friendly, not worried); **no asymmetry >1 px**. |
| Mouth | **Lips fully closed**; **no teeth, no tongue**; corners **neutral to +2 px upturn** (approachable, not frown). |
| Cheeks | Rest volume; no smile crease at full strength. |
| Glasses | Level on bridge; no tilt. |

All expression/viseme keys at **0** except `Basis`.

---

## 6. Required facial controls — visual specification

Values assume **0.0 = neutral**, **1.0 = full** unless noted. Combine keys additively with clamp; **expressions override viseme mouth** when both driven (mouth winner: viseme during speech, expression between words).

### `BLINK`

- Upper lid rotates **down** to meet lower lid; **no vertical squash** of eye globe art.
- Duration in animation: **2–4 frames** close, **2–4** hold, **2–4** open at 24 fps.
- At 1.0: lashes **touch**; pupil **fully occluded**; glasses unchanged.

### `BROW_UP`

- Entire brow translates **up 3–4 px** (sheet scale) + slight arch increase.
- Used for **surprise** and **encouraging** reads; do not lift only outer third (sheet uses full brow).

### `BROW_DOWN`

- Brows move **down 2–3 px** and **pinch inward 1–2 px** total.
- **Focused/analytical** read; avoid angry V at 1.0 — keep inner brow **above** upper lid margin.

### `EXP_smile`

- Mouth corners **up and back**; upper lip may **thin slightly**; cheeks **lift 2–3 px**.
- **Default smile:** lips **remain closed** (Friendly Smile callout).
- **Strong smile (≤1.0):** lip part **≤2 px** optional; if teeth show, only **`TEETH_BAND` upper arc** — **no individual tooth gaps**.

### `EXP_frown`

- Corners **down 2–3 px**; brows may couple with **`BROW_DOWN` at 0.3** automatically in rig (optional).
- **No full lower lip push-out** (avoid duck face); keep competent/not sad-child.

### `EXP_surprise`

- Brows **`BROW_UP` at 0.7–1.0**; upper lids **raise** exposing **+10–15% iris**; jaw **drops 4–6 px**.
- Mouth: **small rounded “O”** (~ellipse taller than wide); **no teeth** at full surprise (sheet Problem-Solving callout).

### `LOOK_LEFT` / `LOOK_RIGHT`

- **Both eyes move together** (same direction); pupil/iris shift **2–3 px** max within sclera.
- Head mesh may add **0.5°** rotation; **glasses do not** slide on face.
- At 1.0: **no sclera cut-off**; no cross-eye.

---

## 7. Rhubarb visemes (friendly, no scary teeth)

Art rule: **Prefer lip/jaw shapes**; teeth appear only as **`TEETH_BAND`** (merged upper row). **Forbidden:** separated rectangular teeth, black inter-tooth gutters, lower full arch in normal speech, tongue filling entire mouth.

| Key | Mouth shape | Teeth / tongue |
|---|---|---|
| `VISEME_A` | Open **medium vertical oval** (“ah”); jaw down | Optional **thin upper band** only |
| `VISEME_B` | Lips **pressed flat** (MBP) | **Hidden** |
| `VISEME_C` | **Tight rounded purse** (CH/J/SH) | Hidden |
| `VISEME_D` | Wide spread **“eh”**; cheeks slight | **Upper band** ≤50% width |
| `VISEME_E` | **Smile spread** “ee”; lips thin | **Upper band** narrow |
| `VISEME_F` | Lower lip **tucked under upper teeth** | Upper edge only, **no gaps** |
| `VISEME_G` | **Open mid** with jaw hinge | Upper band; tongue **not** dominant |
| `VISEME_H` | **Wide open** for emphasis | Upper band + **dark mouth interior**; still **no peg teeth** |
| `VISEME_X` | **Closed rest** | Hidden |

`VISEME_X` must match neutral lip seal when not speaking.

---

## 8. Sheet expression callouts → controls

Reference: four headshots on style sheet.

| Sheet callout | Visual | Control mapping (recommended drive) |
|---|---|---|
| **Friendly Smile** | Warm eyes, **closed-lip** subtle smile | `EXP_smile` **0.45–0.65**; `BROW_UP` **0.1**; all visemes **0** |
| **Focused / Analytical** | Brows **lowered**, mouth **slightly parted**, thoughtful | `BROW_DOWN` **0.5–0.7**; `VISEME_A` or `VISEME_D` **0.15–0.25**; `EXP_frown` **0** |
| **Encouraging / Teaching** | **Wide smile**, **upper teeth** visible, bright eyes, slight head tilt (pose) | `EXP_smile` **0.85–1.0**; `BROW_UP` **0.35**; `VISEME_E` **0.2** optional; teeth = **`TEETH_BAND` only** |
| **Surprised / Problem-Solving** | Brows **high**, eyes **wide**, **small O** mouth | `EXP_surprise` **0.8–1.0**; `BROW_UP` **0.8**; **no teeth** |

Head tilt for Encouraging comes from **`pose_listen` / gesture** bones, not from asymmetric eye keys.

---

## 9. Pose readability — 20 proxy actions

Body must remain **recognizably Patty** (wardrobe colors, hair mass, glasses) at **128 px tall**. Face defaults to §5 unless action notes override.

| Action | Readability requirements |
|---|---|
| `idle_neutral_loop` | Subtle **breathing** in chest; **blink** every 3–5 s; weight **even**; lanyard slight sway; **neutral face**. |
| `walk_cycle` | **Arm swing opposite legs**; sneakers **clear contact/pass**; cargo pockets **stable**; head **minimal bob**; face neutral. |
| `turn_left_90` / `turn_right_90` | **Step through** turn; swap **view set** at 45° if using discrete turns; **hair mass** follows head; glasses stay on. |
| `gesture_present` | **Open palm** forward; tablet/hologram optional prop; **EXP_smile 0.4**; jacket flap **not** clipping hand. |
| `point_left` / `point_right` | **Index extended**, other fingers curled; wrist **straight**; gaze **`LOOK_*`** toward target; teaching energy. |
| `wave` | **Right hand** chest-high; **friendly smile 0.5**; updo **does not intersect** raised arm. |
| `head_nod` | **Two small yes arcs**; brows neutral; lanyard lags 1 frame. |
| `head_shake` | **Two no arcs**; hair front/back **do not z-fight**. |
| `reach_grab` | **Full extension**; fingers **pre-curl** before grab; analytical brow optional **0.3**. |
| `place_release` | **Downward place**; fingers **open**; return to neutral spine. |
| `pose_neutral` | **1-frame** hero: §5 face, front view, feet planted. |
| `pose_present` | Torso **open** to camera; one hand **presenting**; **Encouraging** expression map **0.6**. |
| `pose_listen` | Slight **head tilt**; **`BROW_UP` 0.15**; mouth closed; attentive eyes. |
| `pose_think` | Hand **chin or temple**; **`BROW_DOWN` 0.5**; **`VISEME_X`**. |
| `pose_point` | Strong **point**; **`LOOK_*` 0.7** toward indicated side. |
| `pose_hold` | Two-hand **hold** at waist/chest; neutral face. |
| `pose_ready` | Athletic-ready **slight crouch**; **feet wide**; **ready smile 0.3**. |
| `pose_end` | **Relax** from ready; exhale chest; return neutral face. |

---

## 10. Hard visual rejection list

Reject output (do not ship) if any of the following appear:

1. **3D realistic** skin shading, pores, normal-mapped fabric, or PBR metal on glasses/watch.
2. **Wrong identity:** different face shape, skin tone family, hair **without** magenta streak updo, **missing glasses**, wrong wardrobe (no cargo pants, no rolled teal sleeves, no lanyard/badge).
3. **Palette drift:** navy/teal/magenta/electric blue **hue families** swapped (e.g. purple jacket, orange teal).
4. **Outline break:** missing ink, inconsistent line weight, or **pure black** fill areas on skin.
5. **Neutral face wrong:** **Misaligned eyes**, **visible teeth**, **frown default**, **crossed gaze**, brows **absent or floating**.
6. **Scary mouth:** **Separated teeth**, **dark gaps** between teeth, **full lower arch**, **tongue as solid slab** in smile/surprise.
7. **Glasses errors:** asymmetric frames, **eyes outside lenses**, temples **not reaching ears**.
8. **Back view missing** eagle crest or **magenta collar stripe** when jacket back visible.
9. **Layer order bugs:** hair **under** face, lanyard **under** jacket, **hand under torso** in reach/point.
10. **View inconsistency:** front face pasted on 3/4 body with **wrong ear/glasses depth**.
11. **Chibi/mascot:** **<6 head heights**, giant head with tiny feet.
12. **Non-federal attitude:** aggressive pointing, angry brows, sarcastic smirk as default.
13. **Contract mismatch:** missing or renamed **viseme/expression** keys; actions not readable at thumbnail scale.

---

## 11. Production QA checklist

- [ ] Side-by-side overlay PNG at **480×360** and **1920×1440** — silhouette match ≥95% per view.
- [ ] Palette spot-check **7 swatches + skin + hair + ink**.
- [ ] All **9 visemes + 8 expressions** rendered at 1.0 with glasses on.
- [ ] **Four sheet expressions** reproduced via control mapping (§8).
- [ ] **20 actions** play with correct view swaps and no layer pops.
- [ ] **`idle_neutral_loop`** 5 s without blink/face drift.

---

## 12. References

- Style sheet: `/cursor/stores/bc-b80cc329-0c07-499f-9a51-00c871f014b4/media/reference/patty-patties-style.png`
- Action/viseme contract: `/cursor/stores/bc-b80cc329-0c07-499f-9a51-00c871f014b4/internal/character-contract.md`
