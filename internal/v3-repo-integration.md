---
cursor:
  subagentId: "bc-2c44c5eb-6576-598e-a0e8-b6d48fad6ffe"
---

# Avery Chen V3 repository integration

## Recommendation

Add Avery Chen V3 as a new, directly tracked authored asset tree beside the three existing release archives. Do **not** unpack the whole pipeline into this PR, do **not** change any existing ZIP, and do **not** put the character inside a ZIP.

The exact target paths should be:

```text
.gitattributes
README.md                                      # expand the existing two-line repository README
assets/assets.yaml                             # authoritative runtime manifest
assets/characters/AveryChen.blend              # final V3, through Git LFS
scripts/build_avery_chen.py                     # deterministic Blender 5.2.1 builder
docs/characters/avery-chen/README.md            # contract, provenance, license, rebuild notes
```

Manifest identity:

```text
assets/assets.yaml
└── assets.char.avery_chen
    └── file: characters/AveryChen.blend
```

This is the smallest change that both preserves the repository's immutable release snapshots and follows the current pipeline's authored-asset contract. If a distributable pipeline-plus-character bundle is wanted later, generate a **new versioned archive** in a separate release PR; never rewrite `blender_training_pipeline_proxy_v1.zip`, `blender_training_pipeline_proxy_slim.zip`, or `AnimPipe_gpu_wave_hardened_v3_1.zip`.

## Inspected state

Inspection was read-only at commit `6deb099cff5b820f6847fab4d656d8ec26c8c2a8`; local `main` and `origin/main` resolve to the same commit and the worktree is clean.

### Outer repository

- Remote: `https://github.com/michael-pittman/AnimPipe`
- Default/current/only branch: `main`
- `main` is currently unprotected.
- No tags or GitHub releases.
- Tracked files are only `README.md` and the three ZIP archives.
- Root `README.md` contains only “AnimPipe / Blender pipeline.”
- No root `.gitattributes`, `.gitignore`, workflow, PR template, or issue template.
- Git LFS 3.7.1 is installed locally, but `git lfs ls-files --all` is empty.
- Existing ZIPs are ordinary Git blobs, not LFS pointers.
- Prior PRs #1 and #2 were merge commits from a fork's `main`; there is no useful feature-branch or commit-message convention to inherit.

### Archive comparison

| Archive | Git blob bytes | SHA-256 | Contents and role |
|---|---:|---|---|
| `AnimPipe_gpu_wave_hardened_v3_1.zip` | 9,555,058 | `ffccf8be1ab966f40f2290191ed5e42de3753abdb6154dc962cf6da55af3cf02` | Current hardened release, package 0.6.1, 214 files, root `MANIFEST.sha256`, source CI, release packager, and current asset schema. No `.blend` and no live `assets/assets.yaml`. |
| `blender_training_pipeline_proxy_v1.zip` | 10,631,650 | `6018128d293c49c7190ba542e350184ffddd5d9fd5b743d1115b90dce1fff172` | Older 0.3.0 release. Its paths are a subset of the hardened archive. No `.blend` and no live `assets/assets.yaml`. |
| `blender_training_pipeline_proxy_slim.zip` | 845,245 | `08aba8c9debbcc640869b7b342a03e9cbf9dc8191d92ddcb8336d6539aba0f8b` | Development/graft export: generated proxy manifest, reports, `__pycache__`/`.pyc`, no root checksum manifest, and no vendor tree. Not a release or source-of-truth target. |

All three wrap a `blender_training_pipeline_proxy/` root. The newest archive was added under a new versioned filename while the older archives were retained. That is evidence for additive, immutable snapshots—not in-place archive rewriting.

The hardened archive's release packager (`scripts/120_package_release.py`) recursively packages source, generates an internal `MANIFEST.sha256`, and deliberately excludes generated proxy assets, build/cache/output trees, environment reports, and secrets. Injecting Avery into that ZIP would require a new release identity and regenerated checksums. It would also hide the `.blend` inside a normal Git ZIP blob, defeating the archive's own Git LFS policy.

## Source-of-truth decision

There are two relevant conventions:

1. The outer repository currently acts as a distribution shell for immutable ZIP snapshots.
2. Inside the current hardened pipeline, `assets/**`, `scripts/**`, and `docs/**` are explicitly authored source of truth; production `.blend` files under `assets/` are the permitted authored-binary exception. Runtime references use logical manifest IDs, not paths.

The direct tree recommended above combines those conventions without a 200-file source migration. The root README must make the boundary explicit:

- the three existing ZIPs are frozen historical pipeline snapshots;
- `assets/`, `scripts/`, and `docs/characters/` are the authored Avery V3 source of truth;
- the hardened ZIP is transient validation tooling until/unless the pipeline source is migrated in a separate PR.

Unpacking the entire hardened archive now would mix a pipeline-source migration with character admission, duplicate the existing release payload, and make review substantially harder. Repacking an archive is worse: it obscures the final character and bypasses per-file LFS review and delivery.

## Git LFS and file-size constraints

The hardened archive contains this policy:

```gitattributes
*.blend filter=lfs diff=lfs merge=lfs -text
*.exr filter=lfs diff=lfs merge=lfs -text
*.hdr filter=lfs diff=lfs merge=lfs -text
*.ktx2 filter=lfs diff=lfs merge=lfs -text
*.wav filter=lfs diff=lfs merge=lfs -text
*.mp4 filter=lfs diff=lfs merge=lfs -text
```

Copy that policy to the repository root before staging `AveryChen.blend`. At minimum the `*.blend` line is mandatory.

GitHub rejects ordinary Git blobs larger than 100 MiB and warns above 50 MiB. Git LFS per-file limits depend on the repository owner's plan; the conservative GitHub Free/Pro ceiling is 2 GiB. The owner's effective LFS quota is not exposed by this checkout, so the clean-clone/LFS pull check below is a required delivery gate.

The manifest `sha256` must equal the SHA-256 of the materialized `.blend`; for a correctly staged LFS file, it will also equal the `oid sha256:` in the Git LFS pointer.

## Manifest entry

Create `assets/assets.yaml` with `char.avery_chen` as its only entry unless another direct authored asset has landed first. Use this shape:

```yaml
assets:
  char.avery_chen:
    kind: character
    version: 3.0.0
    sha256: <sha256-of-final-AveryChen.blend>
    blender_min: 5.2.1
    file: characters/AveryChen.blend
    collection: COL_AVERY_CHEN
    coordinates: {units: meters, up: Z, forward: -Y, scale: 1.0}
    interaction_points:
      hand_left: hand.L
      hand_right: hand.R
    material_roles: [character, focus]
    complexity:
      triangles: <measured-render-triangle-count>
      texture_memory_estimate_mb: <measured-uncompressed-texture-memory>
    source: <verified-V3-provenance>
    license: <verified-SPDX-license>
    style_id: avery_chen_v3
    tags: [instructor, rigged, lip-sync, stylized-realism]
    rig:
      armature: RIG_AVERY_CHEN
      retarget_profile: proxy_rig_v1
      required_actions: [<all-actions-actually-present-in-V3>]
      action_metadata:
        <each-required-action>: {duration_frames: <measured>, category: <category>, loop: <true-or-false>}
      visemes:
        A: VISEME_A
        B: VISEME_B
        C: VISEME_C
        D: VISEME_D
        E: VISEME_E
        F: VISEME_F
        G: VISEME_G
        H: VISEME_H
        X: VISEME_X
      facial_controls:
        [BLINK, BROW_UP, BROW_DOWN, EXP_smile, EXP_frown, EXP_surprise, LOOK_LEFT, LOOK_RIGHT]
```

Do not copy placeholder values into the final manifest. The V2 handoff used the collection, armature, retarget profile, 20-action vocabulary, visemes, facial controls, interaction points, and `CC0-1.0` asset license shown above, but every value—especially the final hash, complexity, action inventory, provenance, and license—must be re-read from the completed V3 build report. The schema permits `source` and `license` to be null, but the architecture contract requires provenance and license; they are merge gates.

The current schema requires `kind`, `version`, `sha256`, and `file`; model-level validators additionally require a character collection, rig, and retarget profile. Static Asset Doctor additionally fails a character without actions or visemes. Blender Asset Doctor checks the collection, armature object type, Blender 5.2 action slots, action names, viseme shape keys, and configured facial controls.

## Builder and documentation contract

`scripts/build_avery_chen.py` should:

- run under Blender 5.2.1 with `--background --factory-startup`;
- accept `--output PATH` and `--report PATH` after Blender's `--`;
- resolve only repository-relative or checksum-pinned inputs;
- reject `/cursor/stores`, `/tmp`, home-directory, network, and other machine-local source dependencies;
- fix all random seeds and create datablocks in stable order with stable names;
- pack textures and leave no missing/absolute external file or library dependency;
- validate the collection, armature, actions, action slots, visemes, controls, dimensions, triangle count, and texture memory before saving;
- emit a deterministic JSON report containing the values used by the manifest;
- save exactly the same bytes on two clean builds with the pinned Blender version.

`docs/characters/avery-chen/README.md` should preserve the V3 model card: visual intent, collection/rig contract, full action and shape-key vocabulary, rebuild command, provenance/license, measured complexity, packed dependencies, known limitations, and final SHA-256. The root `README.md` should stay short and link to it.

Do not commit raw style/reference sheets by default. Redistribution rights are not established by this repository, which has no repository-wide license. A preview is useful for PR review but should be attached to the PR as an artifact rather than committed. If maintainers explicitly want a durable catalog image, use `docs/characters/avery-chen/preview.png`, label it non-authoritative, record its render command in the character README, and keep raw references out of Git.

## Exact validation commands

The following assumes the builder contract and paths above.

### 1. Build twice and prove reproducibility

```bash
set -euo pipefail

repo="$(git rev-parse --show-toplevel)"
cd "$repo"
asset="assets/characters/AveryChen.blend"
manifest="assets/assets.yaml"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

test "$(blender --version | awk 'NR == 1 { print $2 }')" = "5.2.1"

for run in 1 2; do
  blender --background --factory-startup \
    --python scripts/build_avery_chen.py -- \
    --output "$tmp/AveryChen-$run.blend" \
    --report "$tmp/build-$run.json"
done

cmp --silent "$tmp/AveryChen-1.blend" "$tmp/AveryChen-2.blend"
cmp --silent "$tmp/build-1.json" "$tmp/build-2.json"
cmp --silent "$asset" "$tmp/AveryChen-1.blend"
```

If identical `.blend` bytes cannot be produced under pinned Blender 5.2.1, do not claim byte-reproducibility. Change the documented contract to deterministic scene inventory plus deterministic preview comparison and explain the binary variance before merge.

### 2. Validate with the current archived pipeline

```bash
unzip -q AnimPipe_gpu_wave_hardened_v3_1.zip -d "$tmp/pipeline"
pipeline="$tmp/pipeline/blender_training_pipeline_proxy"

python3.11 -m venv "$tmp/venv"
"$tmp/venv/bin/pip" install "$pipeline"

(
  cd "$pipeline"
  NO_COLOR=1 "$tmp/venv/bin/pipe" asset doctor char.avery_chen \
    --manifest "$repo/$manifest" \
    --assets-root "$repo/assets" \
    --blender \
    --report "$tmp/blender-doctor.json"
) > "$tmp/asset-doctor.json"

jq -e '.passed == true' "$tmp/asset-doctor.json"
jq -e '.passed == true and (.blender_version | startswith("5.2.1"))' \
  "$tmp/blender-doctor.json"

(
  cd "$pipeline"
  "$tmp/venv/bin/pipe" asset export-manifest \
    --manifest "$repo/$manifest" \
    --output "$tmp/assets.resolved.json"
)
```

### 3. Reject unpacked or missing dependencies

```bash
blender --background "$asset" --python-expr '
import bpy
external_images = sorted(
    image.name for image in bpy.data.images
    if image.source == "FILE" and image.packed_file is None
)
external_libraries = sorted(lib.filepath for lib in bpy.data.libraries)
assert not external_images, external_images
assert not external_libraries, external_libraries
print("PACKED_DEPENDENCIES_OK")
'
```

### 4. Validate manifest hash and staged LFS pointer

Run this only after `.gitattributes` has been added and the final asset/manifest are staged:

```bash
test "$(git check-attr filter -- "$asset" | awk '{print $3}')" = "lfs"
test "$(git check-attr text -- "$asset" | awk '{print $3}')" = "unset"

materialized_sha="$(sha256sum "$asset" | awk '{print $1}')"
manifest_sha="$("$tmp/venv/bin/python" - "$manifest" <<'PY'
import sys
import yaml

with open(sys.argv[1], encoding="utf-8") as handle:
    entry = yaml.safe_load(handle)["assets"]["char.avery_chen"]

assert entry["kind"] == "character"
assert entry["version"] == "3.0.0"
assert entry["file"] == "characters/AveryChen.blend"
assert entry["collection"]
assert entry["rig"]["armature"]
assert entry["rig"]["retarget_profile"]
assert entry["rig"]["required_actions"]
assert entry["rig"]["action_metadata"]
assert entry["rig"]["visemes"]
assert entry["source"]
assert entry["license"]
print(entry["sha256"])
PY
)"
test "$materialized_sha" = "$manifest_sha"

git show ":$asset" | git lfs pointer --check --strict --stdin
pointer_sha="$(git show ":$asset" | awk -F: '/^oid sha256:/ {print $2}')"
test "$pointer_sha" = "$manifest_sha"
git lfs fsck
```

### 5. Validate PR scope and archive immutability

After commits are created:

```bash
git diff --check origin/main...HEAD
git diff --quiet origin/main...HEAD -- '*.zip'

git diff --name-only --diff-filter=ACMR origin/main...HEAD | sort > "$tmp/actual-paths"
cat > "$tmp/expected-paths" <<'EOF'
.gitattributes
README.md
assets/assets.yaml
assets/characters/AveryChen.blend
docs/characters/avery-chen/README.md
scripts/build_avery_chen.py
EOF
sort -o "$tmp/expected-paths" "$tmp/expected-paths"
diff -u "$tmp/expected-paths" "$tmp/actual-paths"

git lfs push --dry-run origin HEAD
git status --short
```

### 6. Prove the pushed LFS object from a clean clone

```bash
branch="cursor/add-avery-chen-v3-6ffe"
clone_dir="$(mktemp -d)"
git clone --single-branch --branch "$branch" \
  https://github.com/michael-pittman/AnimPipe.git "$clone_dir/repo"
(
  cd "$clone_dir/repo"
  git lfs pull
  git lfs fsck
  test "$(sha256sum assets/characters/AveryChen.blend | awk '{print $1}')" \
    = "$(awk '$1 == "sha256:" {print $2; exit}' assets/assets.yaml)"
)
rm -rf "$clone_dir"
```

This clean-clone check is the proof that the full final character—not only an LFS pointer—was pushed.

## Commit and PR plan

1. Fetch current `main`, then create `cursor/add-avery-chen-v3-6ffe` from `origin/main`.
2. Commit `chore: configure LFS for Blender assets`
   - add root `.gitattributes`;
   - run `git lfs install --local`;
   - ensure this commit exists before the `.blend` is ever staged.
3. Commit `feat: add reproducible Avery Chen V3 build`
   - add `scripts/build_avery_chen.py`;
   - add `docs/characters/avery-chen/README.md`;
   - expand root `README.md` with source-of-truth and rebuild instructions.
4. Commit `feat: add Avery Chen V3 character asset`
   - add the materialized final file through LFS at `assets/characters/AveryChen.blend`;
   - add `assets/assets.yaml` atomically with its exact hash and verified contract.
5. Push with `git push -u origin cursor/add-avery-chen-v3-6ffe`.
6. Open one draft PR against `main`: `Add Avery Chen V3 character asset`.
7. Because there is no PR template, include:
   - materialized byte size and SHA-256;
   - LFS pointer OID;
   - Blender/MPFB or other authoring-tool versions;
   - collection, armature, retarget profile, actions, visemes, and facial controls;
   - provenance and license;
   - two-build reproducibility result;
   - Asset Doctor and clean-clone LFS results;
   - explicit statement that all three ZIP archives are unchanged.
8. Preserve the three commits for review. Existing PR history uses merge commits, but no policy requires a merge method; leave final merge choice to the maintainer.

No repository files, branches, commits, remotes, PRs, or archives were changed during this inspection.
