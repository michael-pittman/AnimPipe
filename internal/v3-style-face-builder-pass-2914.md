---
cursor:
  subagentId: "bc-a2e945bd-663a-55e0-99d7-8ba901002914"
---

# V3 style + facial builder pass (worker)

## Output

| Item | Value |
|---|---|
| Blend sha256 | `6b4e64ec715979278d1f00c643e546fb11884bd2f5eb5a24f71ed59358dcc12e` |
| Triangles | 66,792 |
| Verify | `internal/avery-chen-v3-verify.txt` → PASS |
| Renders | 24/24 in `media/avery-chen-v3/` (2026-09-30 20:03–20:15 UTC) |
| Builder | `docs/avery-chen/scripts/build_avery_chen.py` |

## Style QA mapping (worker assessment)

| Gate | Status | Notes |
|---|---|---|
| Orphan shoulder bars/rings | Partial | Sleeve tubes + raglan restored; magenta cuff flash and patch chevrons still read as bands at arm scale |
| Open jacket + rolled sleeves | Partial | Sleeves/cuffs visible; armscye still gaps on raise |
| Lapels + shirt | Improved | Lapels + shirt loft + wider open front |
| Braided updo | Partial | Scalp channels + 3-lobe crown; still curve-based |
| Spark/chevron patches | Improved | Single mesh patches vs separate bars |
| Material separation | Partial | Cloth vs skin vs hair shaders differentiated; still AgX-flat at sheet scale |

## Facial QA mapping (worker assessment)

| Gate | Status |
|---|---|
| Basis lip seal | Partial |
| Smile dental | Not re-verified this pass |
| Surprise lower teeth | Improved (hide driver retained) |
| Pupils/brows | Prior builder offsets retained |

## Coordinator

Re-run independent `v3-style-qa.md` and `v3-face-qa.md` on hash above. No git commit/push.
