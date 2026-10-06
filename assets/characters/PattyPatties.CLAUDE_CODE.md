# Claude Code — Patty Patties drop-in eval + improve

Paste this whole file into Claude Code from the **AnimPipe repo root** (or `@` this path). The drop-in lives beside this prompt:

- `assets/characters/PattyPatties.blend` — pipeline character to evaluate / rebuild
- `assets/characters/PattyPatties.CLAUDE_CODE.md` — this brief

You own **evaluate → critique → improve → rebuild → doctor → evidence → commit**. Fan work across **AI agent teams**. Use **skills + MCP** (especially graft). Do not redesign the character or break the link-and-play contract.

---

## Role

You are the lead on shipping a better `char.patty_patties` 2D cutout that still plugs into AnimPipe exactly like `char.avery_chen` (same collection / armature / actions / visemes / expressions). Judge the current drop-in against the style sheet, close the known soft limits, and leave a doctor-clean `.blend` plus updated renders.

## Non-negotiables

1. **Look source of truth:** `media/reference/patty-patties-style-hires.png` (prefer over smaller PNG/JPG copies). Palette + cutout rules: `internal/patty-2d-style-spec.md`. Rig/link plan: `internal/patty-2d-rig-plan.md`. Contract: `internal/character-contract.md`.
2. **Do not redesign** face, body, wardrobe, or attitude. Match the sheet: curly near-black updo + magenta streaks, glasses, open navy jacket / teal lining / rolled sleeves, white turtleneck, navy cargos + magenta drawstring, chunky sneakers, blue lanyard + federal ID, smartwatch, tablet, silver eagle (back), magenta collar stripe.
3. **Pipeline contract must stay:**
   - File: `assets/characters/PattyPatties.blend`
   - Manifest: `char.patty_patties` in `assets/assets.yaml`
   - Collection `COL_AVERY_CHEN`, armature `RIG_AVERY_CHEN`, retarget `proxy_rig_v1`
   - 18 bones, exact names/parents already used by the builder
   - 20 slotted actions `idle_neutral_loop` … `pose_end` (fake-user; do not rename)
   - Visemes `VISEME_A`…`VISEME_H`, `VISEME_X` and expressions `BLINK`, `BROW_UP`, `BROW_DOWN`, `EXP_smile`, `EXP_frown`, `EXP_surprise`, `LOOK_LEFT`, `LOOK_RIGHT` on **mesh** shape keys of `GEO_AVERY_HEAD`
   - Materials `MAT_PROXY_CHARACTER`, `MAT_PROXY_FOCUS`
   - Meters, Z up, forward −Y; packed images; **no** linked libraries; **no** machine-local paths
   - Facial show/hide via **shape-key drivers** (or equivalent datablock drivers) — **never** app handlers (linked shots do not run them)
   - Blender **5.2.1 LTS** only
4. Keep the existing mechanisms; improve how they look:
   - Elbow split: `docs/avery-2d/patty_elbow.py` (upper_arm / forearm / hand cards)
   - Mouths: `docs/avery-2d/patty_viseme.py` (cel cards driven off head keys)
   - Orchestrator: `docs/avery-2d/build_patty_dropin.py` + `docs/avery-2d/patty_parts.py`

## Known soft limits to close (priority)

These are already documented as remaining gaps — treat them as **must-fix** unless a team proves a hard pipeline blocker:

1. **Elbow joint art** — sleeve hinge works mechanically, but the joint still reads as two flat drawings butting. Improve crop seams, overlap/underlap, hinge padding, or bent-elbow alternate art so `wave` / `point_*` / `gesture_present` / `reach_grab` look intentional, not torn.
2. **Mouth / expression fidelity** — mouths are painted cel cards; they cover the lips but do not yet match expression-row bust crops from the sheet. Prefer sheet-derived mouth/expression crops (or higher-fidelity cel that matches sheet proportions) for visemes + `EXP_*`, still driven by head shape keys + `hide_render` (or equivalent) so inactive cards never blot the face.
3. **Silhouette / prop QA** — badge, lanyard, tablet parenting, eagle crest on back, no doubled limbs, no holes at joints, no floating props, palette ΔE vs style-spec tokens.

Do **not** spend cycles on 3D sculpt, Grease Pencil as the rigged medium, or renaming the proxy contract.

---

## Skills + MCP (use these)

### Graft (required first pass)

This repo is indexed by graft. Load the **graft** skill (`.claude/skills/graft/SKILL.md`). Prefer graft CLI or graft MCP over blind greps:

| Goal | Tool |
|---|---|
| Where builders / doctor / contract live | `graft ask "…" --source` or MCP `graft_find_code` |
| Every use of a symbol | `graft grep` / `graft_find_all` |
| File API before edit | `graft skeleton` / `graft_file_api` |
| Blast radius before multi-file change | `graft callers … --depth all` / `graft_trace_calls` |
| Orientation | `graft map` / `graft_repo_map` |

Start with asks such as:

- `graft ask "Patty Patties 2D drop-in build and elbow split" --source --in docs/avery-2d/`
- `graft ask "proxy character doctor visemes expressions COL_AVERY_CHEN" --source`
- `graft callers build_patty_dropin --depth 2` (or the actual symbol names graft returns)

Report graft token savings per the skill. After builder edits, trust graft’s live refresh; do not hand-edit `graft/` markdown.

### Other skills / MCP

Use any installed Claude Code skills that help (image critique, Python, Blender scripting, git safety). If image MCP / vision is available, **open the PNG pixels** — do not critique from filenames alone. If web/docs MCP is available, use only for Blender 5.2.1 API facts you cannot confirm in-repo.

---

## Agent teams (fan out)

Create a **lead coordinator** plus parallel specialized agents. Teams report back with findings + concrete patch plans; the lead merges patches, rebuilds once, and gates on doctor.

Suggested teams (run in parallel after the graft orientation pass):

| Team | Mission | Inputs | Output |
|---|---|---|---|
| **T1 Visual QA** | Pixel critique vs hires sheet | `media/reference/patty-patties-style-hires.png`, all `media/patty-patties/*.png`, `internal/patty-2d-style-spec.md` | Ranked defect list (severity, file/pixel cue, owner team) |
| **T2 Elbow / limb hinge** | Close flat-elbow limit without breaking bone parenting | `patty_elbow.py`, `patty_parts.py`, `wave.png`, `link-wave.png`, `action-sheet.png` | Patch plan + code edits for seam/overlap/alternate bent art |
| **T3 Viseme / expression** | Sheet-faithful mouths; no black blot; linked-shot safe drivers | `patty_viseme.py`, expression row on style sheet, `viseme-a.png`, `smile.png`, `surprise.png`, `expression-sheet.png` | Patch plan + code edits; keep keys on `GEO_AVERY_HEAD` |
| **T4 Contract / doctor** | Prove link-and-play still admits | `internal/character-contract.md`, `assets/assets.yaml`, doctor scripts via graft | Pass/fail checklist; exact doctor commands for this machine |
| **T5 Rebuild / evidence** | Single rebuild, renders, report, manifest sync | `build_patty_dropin.py`, `docs/characters/patty-patties/` | New `.blend`, `media/patty-patties/*`, `build-report.json`, README + yaml sha256/tris/tex mem |

Rules for teams:

- No team renames contract bones, actions, or shape keys.
- No team commits alone; lead commits once after green doctor + visual spot-check.
- Prefer editing the **Python builders** so the `.blend` is reproducible. Do not hand-sculpt a one-off `.blend` that cannot be rebuilt from scripts.
- If two teams touch the same file, serialize through the lead.

---

## Evaluate first (before editing)

Open and compare:

**Reference**

- `media/reference/patty-patties-style-hires.png`

**Current evidence**

- `media/patty-patties/front.png`
- `media/patty-patties/three-quarter.png`
- `media/patty-patties/side.png`
- `media/patty-patties/back.png`
- `media/patty-patties/wave.png`
- `media/patty-patties/link-wave.png`
- `media/patty-patties/viseme-a.png`
- `media/patty-patties/smile.png`
- `media/patty-patties/surprise.png`
- `media/patty-patties/expression-sheet.png`
- `media/patty-patties/action-sheet.png`

**Status docs**

- `docs/characters/patty-patties/README.md`
- `docs/characters/patty-patties/build-report.json`

Write a short critique (bullet list) covering: silhouette match, wardrobe/props, elbow hinge readability, mouth size/placement/style, blink, turnaround cards, palette drift, pose readability on `wave`/`link-wave`. Then implement fixes.

---

## Rebuild + verify

```bash
blender --background --factory-startup --python docs/avery-2d/build_patty_dropin.py
```

Requirements:

- Blender **5.2.1** on PATH (or install official linux-x64 from `https://download.blender.org/release/Blender5.2/blender-5.2.1-linux-x64.tar.xz` and put it on PATH).
- Pillow available inside that Blender’s Python.
- Builder must pass its own reopen checks + link-and-play `wave` test and refresh `media/patty-patties/` + `docs/characters/patty-patties/build-report.json`.

Then run pipeline doctor for `char.patty_patties` (static + `--blender` when the unpacked pipeline / venv is available):

```bash
# Prefer whatever graft / repo docs name for this host, e.g.:
.venv/bin/pipe asset doctor char.patty_patties
.venv/bin/pipe asset doctor char.patty_patties --blender
```

If the slim zip must be unpacked first, do that; do not skip doctor when Blender is present. Update `assets/assets.yaml` (`sha256`, `complexity.triangles`, `texture_memory_estimate_mb`, `version` bump if the look materially changes) from the build report. Keep `docs/characters/patty-patties/README.md` honest about remaining limits (only list limits that still exist after your pass).

Acceptance bar:

- [ ] Rebuild script exits 0; `failures: []` in build-report
- [ ] Link-wave render exists and elbow reads as a hinge (not a single rigid arm card)
- [ ] Viseme/expression renders show mouth on lips; inactive mouths do not leave black blotches
- [ ] Doctor (static + blender) PASS for `char.patty_patties`
- [ ] Packed images; no linked libraries
- [ ] Visual QA vs hires sheet: no missing badge/eagle/tablet parenting, no doubled limbs, palette within style-spec tolerance

---

## Git

Work on a fresh branch from up-to-date `main` (e.g. `cursor/patty-patties-improve`). Do not force-push.

Commit the drop-in + builders + evidence + manifest/README updates together. `*.blend` is Git LFS — confirm the LFS object for `PattyPatties.blend` uploads on push.

Push the branch. Merge to `main` and sync `origin/main` only after doctor + visual acceptance pass. Leave unrelated dirty files unstaged.

Also keep this prompt file (`assets/characters/PattyPatties.CLAUDE_CODE.md`) next to the `.blend` unless you replace it with a short “last-run notes” addendum at the bottom.

### Optional last-run notes (append below after you finish)

```md
## Last run
- Date:
- Branch / commit:
- Doctor: PASS/FAIL
- Soft limits closed:
- Soft limits remaining:
- Notes:
```

---

## Done looks like

1. Critique written; teams’ findings merged.
2. Builder code improved; `.blend` rebuilt from scripts.
3. New renders under `media/patty-patties/` beat the prior soft limits.
4. `char.patty_patties` doctor-clean; yaml/README/report in sync.
5. Branch pushed (and main synced if acceptance passed).
6. Brief handoff summarizing what changed and what (if anything) is still flat/cel-limited.
