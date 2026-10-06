---
cursor:
  subagentId: "bc-d50ccbb9-5975-5935-9203-a9c38956a23b"
---

# Avery toon visual QA rebuild (a23b)

## Deliverables updated

- `docs/avery-toon/build_avery_toon.py` — V3 patch + postprocess (no `GEO_TOON_*`)
- `docs/avery-toon/AveryToon.blend`
- `docs/avery-toon/README.md`
- `media/avery-toon/*.png` (five renders)

## Pipeline changes

1. **`patch_v3_for_toon`** before `v3.build()`: disable armscye shredding, jacket lapel cards, and front face deletion; swap tube sleeves for **fitted skinned sleeves** (+ wider extraction); keep raglan shoulder patches.
2. **Postprocess**: jacket + forearm skin material slots on `GEO_AVERY_BODY`; restore **V3 curve hair** with thicker bevel; flat unlit eyes/glasses; hide scrap objects; ribbon tee stripe; facial scale reset (fixes floating pupils).
3. **Verified**: zero `GEO_TOON_*` in output blend; contract validation passes; automated front render continuity check passes.

## Remaining visual gaps vs `media/avery-flat/`

- Coherent vendor body has **open armscye topology** (~300 boundary edges); fitted sleeves + raglans cover but Freestyle still reads jagged armhole silhouettes.
- Chest opening read comes from **white shirt loft** vs closed jacket — not a full solidify shell (shell duplicate path was reverted after modifier-order artifacts).
- Hair is V3 curve updo with increased bevel — denser than wire spheres but not yet full flat-plate volume.
- Footwear remains V3 **skinned shoe meshes** (chunky sneaker read).

## Rebuild

```bash
blender --background --factory-startup \
  --python docs/avery-toon/build_avery_toon.py
```

No git commit (per user).
