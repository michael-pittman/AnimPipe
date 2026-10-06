---
cursor:
  subagentId: "bc-a2e945bd-663a-55e0-99d7-8ba901002914"
---

# V3 facial builder pass (2026-09-30)

## Output

| Item | Value |
|---|---|
| sha256 | `751fd05872f4730ef39cec3160395b431693304a91a5283e6448199739f6f6bc` |
| Triangles | 66,402 |
| Verify | `internal/avery-chen-v3-verify.txt` → PASS |
| Builder | `docs/avery-chen/scripts/build_avery_chen.py` |
| Log | `/tmp/avery-v3-face-build4.log` |

## Builder changes (authoritative)

- `sculpt_integrated_face`: stronger Basis lip seal; EXP_smile upper-lip-only arch; EXP_surprise rounded O with sealed lower lip; removed VISEME_G central opening baked into EXP_smile.
- `rebuild_dental`: single upper curved band behind lip shell; no lower row; no `GEO_AVERY_TONGUE` / `GEO_AVERY_MOUTH_CAVITY`; SMILE/F/SURPRISE/JAW drivers on upper only.
- `make_iris_mesh`: shared `z_center` + left-eye `z_bias_left` for pupil vertical alignment.

## Re-test set (regenerated)

All 24 sheets rebuilt from one pass; minimum facial set per `v3-face-qa.md`:

`front-closeup.png`, `eye-brow-alignment.png`, `neutral-calibration.png`, `expression-sheet.png`, `dental-sheet.png`, `facial-angle-matrix.png`, `eye-brow-matrix.png`, `viseme-strip.png`, `expression-viseme-combos.png`, `transition-strips.png`, `closeup-profile.png`, `closeup-three-quarter.png`.

## Worker assessment vs `v3-face-qa.md`

| Gate | Expected improvement |
|---|---|
| Dental exterior bars / G chin | Chin bars removed (cavity/tongue/lower row gone) |
| SMILE tear / pink junk | Smile lip keys stabilized; dental behind shell in dental-sheet |
| Basis neutral enamel | Lower z + deeper y; expression NEUTRAL reads sealed in inspection |
| SURPRISE lower band | No lower dental mesh |
| Pupil vertical delta | z_bias applied — re-measure on 960×1200 |

Independent face QA should re-run on this hash; not claimed PASS here.
