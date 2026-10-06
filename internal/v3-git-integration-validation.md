---
cursor:
  subagentId: "bc-f838f7ce-6afe-504c-a3d4-25ab6db7dd7d"
---

# Avery Chen V3 — git integration validation

Branch: `cursor/add-avery-chen-v3-dd7d`  
Tip commit: `2194ffb6a42b8d91ee1af0a558cfd909f9d3b962`  
Remote: `origin/cursor/add-avery-chen-v3-dd7d`

## Pre-copy hero verify

| Check | Result |
|---|---|
| Store `assets/characters/AveryChen.blend` sha256 | `751fd05872f4730ef39cec3160395b431693304a91a5283e6448199739f6f6bc` |
| Expected contract (QA) | 66402 tris, 58 objects — matches `build-report.json` / store `build.json` |
| Post-copy repo blend sha256 | Match |

## Git LFS

- `.gitattributes` tracks `*.blend` (and sibling media types from hardened pipeline policy).
- Staged pointer strict check: **PASS** (`git lfs pointer --check --strict`).
- Pointer OID equals manifest sha256: **PASS**
- `git lfs fsck`: **PASS**
- `git lfs push --dry-run`: both blend OIDs listed for push (completed on push).

## Manifest

- Materialized blend sha256 equals `assets/assets.yaml` `char.avery_chen.sha256`: **PASS**
- Required contract fields populated (collection, rig, actions, visemes, source, license): **PASS**

## Asset Doctor

| Mode | Result |
|---|---|
| Static (`asset_system.doctor.static_doctor` via unpacked hardened zip + pydantic) | **PASS** — all checks true including `sha256_matches` |
| `pipe asset doctor` CLI | **SKIP** — package requires Python `<3.12`; VM has 3.12.3 |
| `--blender` | **SKIP** — `blender` not installed on integration VM |

## Builder reproducibility (two-run)

**SKIP** — Blender 5.2.1 not available on VM. Prior store QA (`internal/v3-repro-qa.md`) documents semantic determinism; `build-report.json` notes blend bytes may vary by host.

## Contract verify on blend (Blender reopen)

**SKIP** — no Blender. Store log `internal/avery-chen-v3-verify.txt` records **RESULT: PASS** for the shipped hero hash.

## Archive immutability

- `git diff --quiet origin/main...HEAD -- '*.zip'`: **PASS**
- ZIP sha256 unchanged: hardened `ffccf8be…`, v1 `6018128d…`, slim `08aba8c9…`

## Clean clone (post-push)

```bash
git clone --single-branch --branch cursor/add-avery-chen-v3-dd7d \
  https://github.com/michael-pittman/AnimPipe.git && cd repo && git lfs pull && git lfs fsck
```

- Materialized `assets/characters/AveryChen.blend` sha256: **751fd058…** **PASS**
- `vendor/avery-chen/coherent-base.blend` sha256: **22fb0364…** **PASS**

## Builder hygiene

- Shipped `scripts/build_avery_chen.py`: no `/cursor/stores`, MPFB import, or archive reads on build path (comments only mention exclusions).
- Vendored inputs at repo-relative `vendor/avery-chen/*`.

## PR

None opened (per assignment).
