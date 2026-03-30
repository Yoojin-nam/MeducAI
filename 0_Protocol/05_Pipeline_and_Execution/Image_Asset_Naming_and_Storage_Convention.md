# Image Asset Naming & Storage Convention (Run-Scoped) — Handoff Spec

**Status:** Execution Reference (Handoff)  
**Applies to:** Image assets used in QA (Realistic), S5 post-REGEN image regeneration, and Anki-optimized resizing  
**Primary Goal:** Prevent operator confusion by making *asset type* and *lineage* obvious from **filename** (AppSheet-friendly) while remaining fully compatible with existing pipeline conventions in `2_Data/metadata/generated/*`.

---

## 1) Non-negotiable principles

1. **RUN_TAG scope is the unit of storage.**  
   All artifacts for a run must live under:
   - `2_Data/metadata/generated/{RUN_TAG}/`

2. **Filename is the primary discriminator (AppSheet-safe).**  
   The canonical image filename begins with `IMG__{RUN_TAG}__...`, so even if a tool/export strips folder paths, the filename alone still encodes the run/type.

3. **Do not change basenames across derivatives.**  
   If you create an Anki-resized version, keep the *exact same* basename and only change the directory (`images/` → `images_anki/`). This enables deterministic mapping without extra lookup tables.

4. **Manifest-first + recoverable from filenames.**  
   `s4_image_manifest__armX.jsonl` is the authoritative index, but if missing, it can be **regenerated** by scanning `images/` for `IMG__*.jpg` (see Section 7).

---

## 2) Directory convention (inside each RUN_TAG)

Canonical layout:

```
2_Data/metadata/generated/{RUN_TAG}/
├── images/                # primary images referenced by s4_image_manifest__armX.jsonl
├── images_anki/           # Anki-optimized copies (same basename as images/)
├── images_regen/          # positive regen images (same RUN_TAG, _regen suffix)
├── batch_tmp/             # transient batch artifacts (may be deleted)
├── image_bk/              # backups / recovery (as needed)
├── s3_image_spec__armX__original_diagram.jsonl  # original spec (never modify)
├── s3_image_spec__armX__realistic_v{N}.jsonl    # realistic conversion spec (optional)
├── s3_image_spec__armX__regen_positive_v{N}.jsonl  # positive regen spec (optional)
├── s4_image_manifest__armX.jsonl                # baseline manifest
└── s4_image_manifest__armX__regen.jsonl         # regen manifest (separate)
```

Optional (only if you truly need to keep original external files):

```
2_Data/metadata/generated/{RUN_TAG}/
└── images_src/            # raw originals from external generator (e.g., nano banana pro)
```

**Rule:** AppSheet / QA operations should point to `images_anki/` whenever feasible (smaller + faster sync), while `images/` remains the “primary render output.”

---

## 3) Canonical filename formats (MUST)

This repository already uses deterministic filenames that encode card mapping.

### 3.1 Card images (Q1/Q2)

Format:

```
IMG__{RUN_TAG}__{group_id}__{entity_id}__{card_role}.jpg
```

Example (from `FINAL_DISTRIBUTION`):
- `IMG__FINAL_DISTRIBUTION__grp_1ef3e276b7__DERIVED_9476912daad9__Q2.jpg`

Notes:
- `group_id` is of the form `grp_...`
- `entity_id` is typically like `DERIVED_...` in the filename (underscore form)
- `card_role` is `Q1` or `Q2`

### 3.2 Table visuals

Clustered table visual (common):

```
IMG__{RUN_TAG}__{group_id}__TABLE__{cluster_id}.jpg
```

Example:
- `IMG__FINAL_DISTRIBUTION__grp_043427ea12__TABLE__cluster_2.jpg`

Unclustered table visual:

```
IMG__{RUN_TAG}__{group_id}__TABLE.jpg
```

---

## 4) RUN_TAG naming: how we encode "Realistic vs REGEN" safely

Because `RUN_TAG` is embedded in every image filename (`IMG__{RUN_TAG}__...`), the **cleanest** way to distinguish workflows in AppSheet/Excel is to adopt a strict prefix convention.

### 4.1 Recommended prefixes

- **QA Realistic image run**: `QA_REALISTIC__...`
- **S5 post-decision regen image run**: Use **same RUN_TAG as baseline**, distinguished by:
  - **Folder**: `images_regen/` (instead of `images/`)
  - **Suffix**: `_regen` (in filename)
  - **Manifest**: `s4_image_manifest__armX__regen.jsonl` (separate from baseline)

**Example (Positive Regen):**
- Baseline: `FINAL_DISTRIBUTION/images/IMG__FINAL_DISTRIBUTION__grp_...Q1.jpg`
- Regen: `FINAL_DISTRIBUTION/images_regen/IMG__FINAL_DISTRIBUTION__grp_...Q1_regen.jpg`

**Rationale:** Keeping the same RUN_TAG simplifies S5 validation data reuse while folder/suffix segregate regen assets for AppSheet/QA workflows.

### 4.2 Tie-back to a base run (recommended)

When a run is derived from a base pipeline run (e.g., `FINAL_DISTRIBUTION`), include it in the RUN_TAG to preserve lineage:

- `QA_REALISTIC__from__FINAL_DISTRIBUTION__20260103_120000`

This makes it obvious in filename-only contexts:
- `IMG__QA_REALISTIC__from__FINAL_DISTRIBUTION__20260103_120000__...`

### 4.3 If the base run tag is very long

If the base run tag is already long (e.g., DEV tags), you may shorten the "from" portion **only if** you keep a stable reference elsewhere (e.g., a CSV/NDJSON mapping in the same run directory).

---

## 5) Anki resizing convention (images → images_anki)

For each image under:
- `.../{RUN_TAG}/images/{BASENAME}.jpg`

Produce the Anki-optimized version at:
- `.../{RUN_TAG}/images_anki/{BASENAME}.jpg`

**BASENAME MUST be identical** (including `IMG__{RUN_TAG}__...`).

This guarantees:
- `images_anki/` is a pure drop-in replacement by directory swap
- no confusion between realistic vs regen vs baseline because `{RUN_TAG}` remains embedded

---

## 6) AppSheet / Excel export guidance (what to store)

### 6.1 Best practice (robust)

Store **path-like strings** (relative) rather than “bare filename”:

- `generated/{RUN_TAG}/images_anki/{media_filename}`

Where `media_filename` is the canonical `IMG__...jpg` basename.

This way, even if AppSheet/Excel shows only the column string, you still retain:
- **RUN_TAG**
- **asset type** (via RUN_TAG prefix)
- **which variant** (via `images` vs `images_anki`)

### 6.2 If AppSheet only preserves filename

You are still safe because the filename itself contains `{RUN_TAG}`:
- `IMG__QA_REALISTIC__from__FINAL_DISTRIBUTION__...`
- `IMG__S5_REGEN__from__FINAL_DISTRIBUTION__...`

---

## 7) Recovery / handoff operations (manifest regeneration)

If images exist but `s4_image_manifest__armX.jsonl` is missing or outdated, regenerate it from filenames:

```
python3 3_Code/src/tools/regenerate_s4_manifest.py \
  --base_dir . \
  --run_tag {RUN_TAG} \
  --arm {ARM}
```

**Important:** This assumes the images are stored under:
- `2_Data/metadata/generated/{RUN_TAG}/images/`
and named with the canonical `IMG__...` formats in Section 3.

---

## 8) Practical do/don’t checklist

**DO**
- Keep the `IMG__{RUN_TAG}__...` prefix intact (AppSheet-friendly discriminator).
- Use `RUN_TAG` prefixes (`QA_REALISTIC__...`, `S5_REGEN__...`) to separate workflows.
- Keep Anki derivatives in `images_anki/` with identical basenames.

**DON’T**
- Don’t rely on “folder only” for meaning (exports often drop path context).
- Don’t rename images after manifest creation without updating/regenerating the manifest.
- Don’t mix different workflows under the same RUN_TAG unless you deliberately want them inseparable in filename-only contexts.


