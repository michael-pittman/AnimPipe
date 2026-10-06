# Avery toon — style sheet pass (code only, not yet rendered)

Follows `avery-toon-crown-band-fix.md`. The user tested that fix on a real
Blender machine and sent back the render: crown bug was fixed (hair now
covers the scalp), but compared against the actual target reference — the
"Patty Patties" federal-employee style sheet, not `media/avery-flat/` — it was
clearly short: blank face, flat-dome hair, plain-sweater wardrobe, olive
pants.

Three parallel subagents each diagnosed and proposed a fix for one subsystem
(face, hair, wardrobe). All three proposals are applied below. **Still not
render-verified** — Blender isn't on this machine; this is the second
best-effort round reasoned from code, not from a live scene.

Full proposals, with evidence and reasoning, are preserved in:
- `internal/fix-face-features-proposal.md`
- `internal/fix-hair-style-proposal.md`
- `internal/fix-wardrobe-proposal.md`

## Ground-truth change

The real target is the Patty Patties style sheet (a navy flight-suit
silhouette: matching jacket + trousers, magenta/pink piping, badge/lanyard,
smartwatch), not `media/avery-flat/front.png` (olive cargo pants + open blue
jacket), which this pipeline was previously built against. This is a
deliberate pivot, confirmed with the user, not a bug fix — flagged
prominently because it changes an established, documented look
(`docs/avery-toon/README.md` used to say "stay olive").

The style sheet's official labeled palette (navy `#0E254A`, teal `#058E94`)
was already near-identical to the code's existing values — color wasn't the
core gap, missing/wrong structure was.

## What changed, by subsystem

### Face (medium confidence — see caveat)
- `fix_facial_materials()` now nudges `GEO_AVERY_EYES/IRISES/PUPILS/BROWS`
  0.0015m toward the camera (idempotent, guarded by a custom property) and
  logs each object's evaluated world-space Y bounds every call
  (`_log_face_depth_diagnostics`).
- New `verify_face_features()` QA gate actually samples for eye color in the
  render — neither prior gate did, which is how a fully blank face shipped
  silently. Wired into `main()` as a hard gate.
- New `build_mouth_decal()` — a small flat lip-colored mesh, same pattern as
  the existing iris/pupil decals. Confirmed gap, not a guess: the base V3
  head paints a lip tone into a per-vertex color attribute, but the toon cel
  conversion discards it (no `ShaderNodeAttribute` reads it), so the mouth
  was genuinely blank at rest, not just occluded.
- **Caveat**: the investigating agent could not pin the blank-face root cause
  to one line without a live Blender session — it ruled out deletion,
  mis-parenting, and color/alpha issues with direct evidence, and
  independently confirmed the shared V3 face-building code is already
  QA-verified correct, which is why the fix stays toon-local. But the nudge
  is a reasoned mitigation for the leading hypothesis (eroded depth margin),
  not a confirmed fix. **Read the new `face-diag` console lines on the next
  run** — if eyes are still blank, those logs should make the real cause
  legible instead of requiring another guess.

### Hair
- `build_solid_afro_mesh()` rewritten: the single smooth ellipsoid now gets
  silhouette noise plus ~11 smaller overlapping "puff" spheres (seeded
  RNG, biased to crown/side/back) for actual curl texture, instead of one
  perfectly smooth dome.
- New `MAT_AVERY_HAIR_MAGENTA` material (reusing the existing but previously
  unused `hair_magenta` token) assigned to ~32% of puffs — real streak
  clumps, not a flat single color. The QA color mask already tolerated this
  color; it was just never wired into geometry until now.
- The face-window clip boundary is now noise-jittered
  (`_hair_face_window_margins`) instead of a flat plane, so it reads as an
  irregular fringe edge instead of a hard bowl-cut line. A few explicit
  "temple fringe" puffs straddle the window edges so the clip trims them into
  loose wisps.
- The old "exactly one island" / left-right-split self-checks (which would
  false-positive on an intentionally multi-island puff cluster) are replaced
  by `_hair_islands_overlap_cluster`, a bounding-box overlap check.
- No QA gate threshold changes — the magenta reuses an already-tolerated
  color, so existing coverage floors/ceilings count it the same as before.
- Scoped to a symmetric curl-cloud, **not** the style sheet's pulled-back
  pouf/bun — this pipeline never renders a back view, so that detail would be
  invisible in every graded image. Not worth the added geometric risk.

### Wardrobe
- `patch_v3_for_toon()` no longer stubs `build_jacket_lapels` (the other two
  stubs — `soften_armscye_edges`, `open_jacket_front` — stay; they protect
  the closed-body-topology redesign and are unrelated). Lapels are
  independent standalone meshes, not a body-topology change.
- `SCRAP_OBJECTS` no longer hides `GEO_AVERY_LAPEL_L/R`,
  `GEO_AVERY_PATCH_CHEST`, `GEO_AVERY_PATCH_SLEEVE_L/R`,
  `GEO_AVERY_BADGE_BAR_0/1/2`, `GEO_AVERY_BADGE_CLIP`,
  `GEO_AVERY_BADGE_PORTRAIT`, `GEO_AVERY_LANYARD_BREAKAWAY` — all of this
  already exists, already carries roughly correct navy/teal/magenta
  materials, and was just hidden under "scrap"/"clutter" labels.
- `postprocess_toon_cohesion()`'s separate badge/lanyard "clutter" hide-loop
  is removed outright (same objects, different hide mechanism).
- `CHEST_BAND_WHITE_SIZE`/`CHEST_LOOP_BOTTOM`/`CHEST_LOOP_TEAL_LOW/HIGH`
  shrunk the chest band from an 18cm×16.6cm banner to a ~7cm×8cm collar
  strip, anchored at the same collar top (`CHEST_LOOP_TOP` unchanged).
- `MAT_AVERY_TROUSER`/`MAT_AVERY_SOCK` repointed from `cargo`/`cargo_shadow`
  to `navy`/`navy_deep`. The now-unused `cargo`/`cargo_shadow` palette
  entries are left in place (harmless).
- `TOON_PALETTE["magenta"]` bumped from `#C43B8C` to the style sheet's exact
  `#F51496` for garment/accessory accents (note: hair's streak color,
  `hair_magenta`/`hair_magenta_accent`, is a **separate** token and was
  deliberately left at the more muted `#C43B8C` — the hair agent's call, see
  its proposal).
- Smartwatch and tablet: confirmed not to exist anywhere in the build
  scripts. Not built — sketched as optional future work, out of scope here.
- **Known required follow-up, not yet done**: `verify_chest_band_front()`'s
  fixed pixel-sample window was tuned against the old, larger band. It very
  likely needs recalibration now — flagged with an inline warning comment in
  the function itself. If it fails on the next render, check whether the
  band *looks* right first; if so, recalibrate the row/col fractions against
  where it actually lands, don't loosen the thresholds blindly.

## Integration notes (orchestrator's own pass, not from any proposal)

- All three proposals were verified against the live file state before
  applying (line numbers had not drifted — same file the agents read).
- No true line-level conflicts between the three proposals. The only
  functions more than one touched (`TOON_PALETTE`, `MATERIAL_TINT`,
  `postprocess_toon_cohesion`) touched different keys/regions within them.
- Removed `_hair_island_split_left_right` as dead code — the hair rewrite's
  own scope note said it was "replaced" by the new cluster-overlap check but
  didn't explicitly ask for deletion; it had zero remaining callers after the
  rewrite, so left in place it would've been inert dead code.
- Added one thing beyond the three proposals: a sanity check
  (`len(bm.faces) != len(mesh.polygons)`) guarding the face-index continuity
  assumption the hair proposal's own write-up flagged as its weakest link
  (face order surviving a bmesh→mesh→bmesh round-trip). If that assumption
  ever breaks, this raises a clear error instead of silently mis-tagging
  streak colors onto the wrong faces.
- `pyflakes` clean versus the pre-change baseline — no new warnings
  introduced, only the same pre-existing cosmetic ones from before this
  round.

## Rebuild

```bash
blender --background --factory-startup \
  --python docs/avery-toon/build_avery_toon.py
```

## What to watch on the next run, in priority order

1. **Does it complete at all.** The hair rewrite is the biggest structural
   change in this round (new bmesh merge/tagging logic); if it raises, the
   error should be specific (face-index mismatch, cluster-overlap failure,
   crown-clearance failure) rather than a generic crash.
2. **`face-diag` console lines** (3x per run) — compare eye/iris/pupil/brow Y
   ranges against the head's. If a decal's Y sits behind (less negative than)
   the head surface at the same region, that confirms the occlusion
   hypothesis and tells us how much more nudge is needed.
3. **`verify_chest_band_front`** may fail even if the band looks correct —
   see "known required follow-up" above. Don't read a failure here as "the
   band is wrong" without looking at the actual pixels first.
4. **Visual check against the style sheet**: solid textured crown with visible
   magenta streaks (not a flat purple dome), visible eyes/brows/mouth, lapels
   framing an open-collar read, narrow white/teal strip at the collar (not a
   banner), navy trousers.

No git commit (per the standing instruction on this work).
