---
cursor:
  subagentId: "bc-93051903-3d28-5175-a879-86bc73117ff9"
---

VERDICT: PASS WITH NOTES

# Avery Chen V3 — reproducibility audit (facial-only builder refresh)

Read-only inspection after facial-only builder changes. No deliverables modified. No git commit or push.

## Hero output

| Check | Expected | Result |
|---|---|---|
| Blend sha256 | `751fd05872f4730ef39cec3160395b431693304a91a5283e6448199739f6f6bc` | **Match** on `docs/avery-chen/AveryChen.blend` and `assets/characters/AveryChen.blend` (`cmp` identical, **2280443** bytes) |
| Triangles | **66402** | **Match** in `build.json` and `internal/avery-chen-v3-verify.txt` |
| Objects | **58** | **Match** in `build.json` and verify log |
| Renders | **24** | **Match** count in `build.json`; all PNGs present under `media/avery-chen-v3/` with sha256 **match** |
| Verify reopen | **PASS** | `internal/avery-chen-v3-verify.txt` — `RESULT: PASS` (Blender 5.2.1; 20 actions; 9 visemes + 8 facial controls; no external images; no linked libraries) |

## Builder alignment

| Path | Role | Status |
|---|---|---|
| `docs/avery-chen/scripts/build_avery_chen.py` | **Authoritative** (README rebuild command) | Present; sha256 `7e808d54…` |
| `docs/avery-chen/build_avery_chen.py` | Declared mirror | **Drift** — same byte length (118873) but content differs (brow arch constants ~lines 876–877: stale `1.5260/1.5236` vs authoritative `1.5274/1.5244`) |

**Note:** Hero hash and verify log are consistent with the **scripts/** builder (facial-only pass). Sync or remove the root mirror before git integration to avoid dual entrypoints.

### Runtime dependencies (authoritative builder)

- **No** `/cursor/stores`, MPFB import, `build_character.py`, or `archive/` reads on the build path.
- Sole blend input: checksum-pinned `vendor/avery-chen/coherent-base.blend` (`SOURCE_SHA256` / manifest).
- `build.json` `source.runtime_dependencies`: `[]`; `packed_dependencies`: true; empty `linked_libraries` / `external_images`.

## Source manifest and licenses

| Artifact | Alignment |
|---|---|
| `vendor/avery-chen/coherent-base.blend` | sha256 `22fb0364e20c84cd3b886b9f9f665cec3abc898adb6afee9b1ee282dca161f2d` matches `SOURCE_MANIFEST.json` and `build.json` `source.sha256` |
| `vendor/avery-chen/LICENSES.md` | CC0-1.0; MPFB not a runtime requirement |
| `docs/avery-chen/README.md` | Rebuild paths, contract, source inventory; defers sha256/triangles/objects to `build.json` |

## `build.json` contract snapshot

- `collection`: `COL_AVERY_CHEN`; `file`: `characters/AveryChen.blend`; `retarget_profile`: `proxy_rig_v1`
- 20 actions, 9 visemes, 8 facial controls
- `output_path` in report is absolute store metadata from build host (not a rebuild input)

## Two-build reproducibility

**Not executed** on this VM (`blender` unavailable). Prior passes rely on builder-run verify gates embedded in `scripts/build_avery_chen.py`.

## Integration-only gate (not re-run)

AnimPipe git `main@6deb099` still tracks only README + three pipeline ZIPs:

- No `scripts/build_avery_chen.py`, `vendor/avery-chen/`, LFS `.blend`, or `assets/assets.yaml` on branch
- **Asset Doctor**, **clean-clone LFS pull**, and manifest hash vs pointer proof **deferred** until integration PR

## Non-input clutter (prune before git)

`build_character.py`, `build_v3.py`, `archive/`, `AveryChen.blend@`, `AveryChen.blend1`, `__pycache__/` — not build inputs.

## Blockers for merge PASS (integration)

1. Land full V3 tree on AnimPipe with manifest sha256 = `751fd058…` materialized blend.
2. **Sync or drop** stale `docs/avery-chen/build_avery_chen.py` mirror; single authoritative `scripts/build_avery_chen.py`.
3. Run Asset Doctor + clean-clone LFS on integration branch.
4. Optional: independent two-build on Blender **5.2.1**.

## Summary

Facial-only refresh **751fd058…** / **66402** tris / **58** objects / **24** renders / verify **PASS** is internally consistent across both blend copies, `build.json`, verify log, vendored source, and media checksums. Local runtime dependency rules hold on the authoritative builder. **PASS WITH NOTES:** root builder mirror drift; integration and two-build confirmation still outstanding.
