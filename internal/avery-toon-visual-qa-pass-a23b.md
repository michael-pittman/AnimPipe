---
cursor:
  subagentId: "bc-d50ccbb9-5975-5935-9203-a9c38956a23b"
---

# Avery toon — hair/jacket visual QA pass (a23b)

## Shipped artifacts (overwritten)

- `media/avery-toon/full-body-front.png`, `full-body-three-quarter.png`, `full-body-side.png`, `expression-sheet.png`, `action-wave.png`
- `docs/avery-toon/AveryToon.blend`, `docs/avery-toon/build_avery_toon.py`, `docs/avery-toon/README.md`

## Hair (mandate)

- Removed single-mesh / boolean hair; `build_hair_curl_spheres()` places ~80 icospheres (subdiv 1) with `MAT_AVERY_HAIR` / `MAT_AVERY_HAIR_PLUM`, head bone only.
- Placement samples scalp vertices on `GEO_AVERY_HEAD` with outward offset; face window preserved.
- Front PNG check (manual): curl cluster at ears/crown, not shoulder-wide disk; eyes/glasses/mouth visible.

## Jacket (mandate)

- Torso loft + pelvis filler + front waist block; shirt single quad + horizontal teal ribbon; navy sleeve tubes enlarged; forearm-only skin extraction.
- Lanyard/badge hidden for cleaner chest read; shirt/teal materials flat unlit after cel pass.
- Builder exits with `AVERY_TOON_COMPLETE` and pixel QA (waist band, wave sleeve, hair sides).

## Remaining visual risk (do not ship without re-check)

- Cel + Freestyle still reads **boxy** at shoulders (shoulder bridge quads + loft silhouette).
- Midriff may still show a thin skin line in some views depending on pose; waist block may need side arcs, not front quad only.
- Hair automated QA uses display-space heuristics; tune if palette shifts.

## Rebuild

```bash
cd /cursor/stores/bc-b80cc329-0c07-499f-9a51-00c871f014b4
/tmp/blender-5.2.1-linux-x64/blender --background --factory-startup \
  --python docs/avery-toon/build_avery_toon.py
```

No git commit (per user).
