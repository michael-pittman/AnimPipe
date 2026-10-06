---
cursor:
  subagentId: "bc-259c45b8-43ba-5981-ad30-80a6f8d618e9"
---

# Avery flat deliverables

Original 2D cel illustrations (generated + normalized), not cropped from `patty-patties-style.png`.

| File | Size | Notes |
|---|---|---|
| `media/avery-flat/front.png` | 1280×720 | Full front, connected body |
| `media/avery-flat/side.png` | 1280×720 | Profile, watermark scrubbed |
| `media/avery-flat/back.png` | 1280×720 | Back, magenta collar stripe only |
| `media/avery-flat/three-quarter.png` | 1280×720 | 3/4 view |
| `media/avery-flat/expression-sheet.png` | 1536×864 | 3×3 bust grid, no labels |
| `media/avery-flat/viseme-strip.png` | 2560×1440 | 9 mouth shapes |

Pipeline: `/tmp/postprocess_avery_flat.py`, `/tmp/fix_expression_sheet.py`.

**2026-10-01:** Replaced bottom-right `LOOK_RIGHT` cell only (bbox-aligned to look-left cell); turnaround PNGs unchanged.
