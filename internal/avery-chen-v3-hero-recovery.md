---
cursor:
  subagentId: "bc-a2e945bd-663a-55e0-99d7-8ba901002914"
---

# Avery Chen V3 hero recovery (worker summary)

## What was on disk at takeover

| Artifact | Role |
|---|---|
| Rejected procedural `docs/avery-chen/AveryChen.blend` (552 KB, sha256 `8d92e984…`) | Style/facial QA fail — **not reused** |
| `docs/avery-chen/scripts/build_avery_chen.py` | Coherent MakeHuman-based hero builder from vendored `coherent-base.blend` |
| `docs/avery-chen/vendor/avery-chen/coherent-base.blend` | Checksum-pinned CC0 source (`22fb0364…`) |
| Mixed `media/avery-chen-v3/` | Primitive-era renders; **replaced** in final pass |
| `docs/avery-chen/build_avery_chen.py` (procedural) | Superseded by copy of `scripts/build_avery_chen.py` |

## Final generation (facial QA pass, 2026-09-30 UTC)

| Field | Value |
|---|---|
| sha256 | `751fd05872f4730ef39cec3160395b431693304a91a5283e6448199739f6f6bc` |
| Triangles (render) | 66,402 |
| Objects | 58 (upper dental only; tongue/cavity removed) |
| Texture memory est. | 0.0 MB |
| Verify | `internal/avery-chen-v3-verify.txt` → **RESULT: PASS** |
| Builder log | `/tmp/avery-v3-face-build4.log` → `AVERY_CHEN_V3_COMPLETE` |
| Contact sheets | **24/24** PNGs under `media/avery-chen-v3/` (single unified rebuild) |

## Builder contract (clean-clone ready)

- Entry: `docs/avery-chen/scripts/build_avery_chen.py` (byte-identical mirror at `docs/avery-chen/build_avery_chen.py` for store layout)
- Inputs: `vendor/avery-chen/coherent-base.blend` + `vendor/avery-chen/SOURCE_MANIFEST.json` only
- No `/cursor/stores`, MPFB, or archive blend reads in `build()`
- Pillow required for render sheets; `blender 5.2.1` pinned
- Post-save reopen validation + full `media/avery-chen-v3/` contact set

## Fixes applied this session

1. **Facial (builder):** Removed VISEME_G→EXP_smile key pollution; rebuilt EXP_smile / EXP_surprise lip keys; upper-only curved dental arc seated in oral depth; removed tongue + mouth cavity meshes (chin bar artifacts); pupil z bias for vertical alignment.
2. **Wardrobe (preserved):** Sleeve/raglan/cuff, patches, hair, and shirt/jacket stack unchanged from style-pass builder (`6b4e64ec…` lineage).
3. **Pipeline:** `link_only()` collection linking; safe render temp cleanup.

## Honest limitations (visual QA)

- **Shoulder raise:** Residual armscye gap and cuff/patch accent read at 90°–120° (`shoulder-tests.png`); improved but not reference-closed.
- **Hair:** Braid routing improved at turntable distance; still curve-proxy, not sculpted mesh updo.
- **Facial neutral:** Residual enamel peek possible in `front-closeup.png`; smile/surprise drivers need independent re-gate (`v3-face-qa.md`).
- **Style/facial numeric gates:** Contract verify **PASS**; `v3-style-qa.md` / `v3-face-qa.md` should be re-run on this hash — **not claimed PASS here**.
- **Repro:** Two-build byte compare and Asset Doctor not run on this VM; integration PR still per `internal/v3-repo-integration.md`.

## Deliverables touched

- `assets/characters/AveryChen.blend`
- `docs/avery-chen/AveryChen.blend`, `build.json`, `README.md`, `build_avery_chen.py`, `scripts/build_avery_chen.py`, `docs/reference/patty-patties-style.jpg`
- `media/avery-chen-v3/*.png` (24 sheets)
- `internal/avery-chen-v3-verify.txt`

No git commit/push (per assignment).
