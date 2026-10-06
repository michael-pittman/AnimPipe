# Avery Chen — Toon / Cel Humanoid

Illustrated **2D-in-3D** Avery on the coherent V3 skinned body. Cel flat fills + Freestyle ink outlines.

## Outputs

| Artifact | Path |
|---|---|
| Blend | `docs/avery-toon/AveryToon.blend` |
| Renders | `media/avery-toon/` |

## Rebuild

Requires **Blender 5.2.1 LTS** (same as V3).

```bash
blender --background --factory-startup \
  --python docs/avery-toon/build_avery_toon.py
```

Optional flags after `--`: `--source`, `--output`, `--render-dir`, `--skip-build`, `--skip-renders`.

## Pipeline contract (preserved)

| Field | Value |
|---|---|
| Collection | `COL_AVERY_CHEN` |
| Armature | `RIG_AVERY_CHEN` |
| Retarget | `proxy_rig_v1` |
| Actions | 20 canonical slotted actions |
| Visemes | `VISEME_A` … `VISEME_X` |
| Expressions | `BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT` |

`style_id` in the blend is `avery_chen_toon`.

## Look (toon pass)

Visual lock: **`media/.../Patty Patties` style sheet** (a US-federal-employee
uniform reference) — a deliberate departure from the earlier `media/avery-flat/`
full-body plates, which the pipeline was originally built against. The olive
cargo pants and wide flat chest band documented in prior revisions of this
file matched `avery-flat`, not the style sheet; see
`internal/fix-wardrobe-proposal.md` sub-issue 3 for that decision.

- **Wardrobe** — painted on **`GEO_AVERY_BODY`** face material slots (no `GEO_AVERY_JKT_*` / `GEO_AVERY_SHIRT_*` meshes): navy `#0E274A` on torso and arms to the wrist, skin on hands, white upper-chest band with horizontal teal `#088D94` stripe on body faces. **`GEO_AVERY_TROUSERS`** are now **navy** (matching the jacket) and meet navy at the waist — **not olive**.
- **Jacket open-front read** — sold without a garment mesh (QA hard-fails any `GEO_AVERY_JKT_*`/`GEO_AVERY_SHIRT_*` object): `GEO_AVERY_LAPEL_L/R` (standalone meshes, chest-bone parented) are un-hidden, plus the narrower chest band below.
- **Accessories** — badge, lanyard, and chest/sleeve patches (already built by the base V3 character with roughly correct navy/teal/magenta materials) are un-hidden rather than hidden as "clutter". Smartwatch/tablet are not built (no geometry exists for either; see proposal for why).
- **Hair** — **`GEO_AVERY_HAIR`** is a **curl-clump cluster**, not a smooth dome: a plum `#6B2D5B` base ellipsoid (measured off the head: width **1.55 ×** head width, depth **1.35 ×**, top **5.5 cm above the measured scalp**) with silhouette noise, plus ~11 smaller overlapping "puff" spheres biased to crown/side/back for curl texture. About a third of the puffs carry a second material, magenta `#C43B8C` (`MAT_AVERY_HAIR_MAGENTA`), for visible streak clumps. The face-window clip boundary is noise-jittered (`HAIR_FRINGE_EDGE_NOISE_M`) so it reads as an irregular fringe edge rather than a flat bowl-cut line, with explicit temple-fringe puffs straddling the window edges. No shrinkwrap, solidify, or face culling. **100% `head` weights**. Preview PNGs: **Freestyle off**.
- **Face** — eyes/iris/pupil/brows are built by the shared V3 character code and nudged slightly toward the camera in the toon pass (`FACE_DECAL_NUDGE_M`) to guard against a depth-margin regression that was making them render invisible; `GEO_AVERY_MOUTH` is new toon-only geometry (the base V3 lip paint is discarded by the cel material conversion, so a small flat mouth decal fills that gap). See `internal/fix-face-features-proposal.md` — this one is a best-effort fix made without a live Blender session to confirm, not a verified-correct one yet.
- **Chest bands** — curved shell following the **measured torso front** (`CHEST_BAND_ARC_SEGMENTS` columns), now a **narrow ~7cm×8cm collar strip** (`CHEST_LOOP_BOTTOM → CHEST_LOOP_TOP`, `1.205 → 1.288` m) rather than a wide banner, with the teal stripe at **`1.235 → 1.250`** m. Not an axis-aligned slab — the flat slab read as a pasted-on sticker.
- **Ankles** — sock/piping/cuff clutter removed; navy trousers run into sneakers (no white ankle patches).

## Renders shipped

- `full-body-front.png`, `full-body-three-quarter.png`, `full-body-side.png`
- `expression-sheet.png`
- `action-wave.png` (wave action, frame 15)

## License

Same as V3 hero: **CC0-1.0** on authored toon materials and docs; coherent base remains CC0 per `vendor/avery-chen/SOURCE_MANIFEST.json`.
