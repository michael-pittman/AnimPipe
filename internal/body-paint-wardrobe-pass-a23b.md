---
cursor:
  subagentId: "bc-d50ccbb9-5975-5935-9203-a9c38956a23b"
---

# Body-paint wardrobe + UV hair (a23b)

Pivot away from `GEO_AVERY_JKT_*` / icosphere hair per user stop-ship.

## Builder changes (`docs/avery-toon/build_avery_toon.py`)

- Deletes all `GEO_AVERY_JKT_*`, `GEO_AVERY_SHIRT*`, extra `GEO_AVERY_HAIR*` meshes.
- Paints **`GEO_AVERY_BODY`** + visible skin envelope **`GEO_AVERY_HEAD`** via face `material_index` (navy `#0E274A`, white chest band, teal `#088D94` stripe, skin hands/face).
- Single **`GEO_AVERY_HAIR`**: joined UV spheres, subsurf 2, head-weighted, magenta `#C43B8C` + small black back lobe.
- V3 patch: no separate sleeves / shirt loft.

## Deliverables overwritten

- `media/avery-toon/*.png` (5), `docs/avery-toon/AveryToon.blend`, `README.md`

## Manual front PNG check

No floating white quad, no chest oval hole, no cheek hair balls; navy sleeves on painted body.

No git commit.
