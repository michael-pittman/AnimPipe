---
cursor:
  subagentId: "bc-d50ccbb9-5975-5935-9203-a9c38956a23b"
---

# Avery toon — solid wardrobe pass (QA fix)

## Change

Replaced visible V3 wardrobe with bone-aligned `GEO_TOON_*` shells; all other `GEO_AVERY_*` meshes (except head/brows/teeth/tongue/glasses) are render-hidden. Legacy shredded fragments no longer draw.

## Front render (`media/avery-toon/full-body-front.png`)

Single connected figure: navy jacket + waist/hip bridge, white tee + teal band, rolled sleeves (teal/magenta cuffs), olive cargos + pockets, sneakers, lanyard/badge, magenta–black updo, dark iris/pupil discs + frame mesh. Cel + Freestyle ink.

## Remaining vs `media/avery-flat/`

Blocky proxy geometry (not hand-painted curves); face is V3 sculpt + toon eye discs; glasses are thin but present. Style is “solid 3D toon,” not a traced 2D plate.

## Rebuild

`blender --background --factory-startup --python docs/avery-toon/build_avery_toon.py`
