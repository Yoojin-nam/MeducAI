# PDF Packet Builder for S0 QA

**Status:** Canonical  
**Date:** 2025-12-20  
**Purpose:** Documentation for set-level PDF packet builder

---

## Overview

The PDF Packet Builder (`07_build_set_pdf.py`) generates **one PDF per Set** (group × arm artifact bundle) for S0 QA evaluation. Each PDF contains:

1. **Master Table** (text table from S1)
2. **Infographic** (group-level visual from S4)
3. **Cards** (exactly 12 cards from S2, with images placed according to S3 policy)

---

## Usage

### Basic Command (Non-blinded Mode)

```bash
python 3_Code/src/07_build_set_pdf.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm <A-F> \
  --group_id <Gxxxx> \
  --out_dir 6_Distributions/QA_Packets
```

**Example:**
```bash
python 3_Code/src/07_build_set_pdf.py \
  --base_dir . \
  --run_tag TEST_S2_V7_20251220_105343 \
  --arm A \
  --group_id G0123 \
  --out_dir 6_Distributions/QA_Packets
```

**Output:** `6_Distributions/QA_Packets/SET_G0123_armA.pdf`

### Blinded Mode

```bash
python 3_Code/src/07_build_set_pdf.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm <A-F> \
  --group_id <Gxxxx> \
  --out_dir 6_Distributions/QA_Packets \
  --blinded \
  --set_surrogate_csv 0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv
```

**Output:** `6_Distributions/QA_Packets/SET_<surrogate>.pdf`

**Blinding Features:**
- PDF header does NOT include run_tag/arm/provider/model
- Output filename uses surrogate set_id only
- Within PDF, shows only content + minimal structural labels (section titles)
- Footer removed (no group_id/arm visible)

### Allow Missing Images (Preview/Debug Only)

```bash
python 3_Code/src/07_build_set_pdf.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm <A-F> \
  --group_id <Gxxxx> \
  --out_dir 6_Distributions/QA_Packets \
  --allow_missing_images
```

When `--allow_missing_images` is set:
- Missing images are replaced with "(IMAGE MISSING)" placeholder text
- Does not raise RuntimeError for missing images
- Useful for testing/debugging when images are not yet generated

**Policy note:**
- This flag is an **operational escape hatch**, not a quality gate.
- **Final QA distribution PDFs should be generated without `--allow_missing_images`**; if required images are missing, fix upstream (typically re-run S4).
- Content-quality gating/promotion decisions belong to **Option C (S5 triage → S6 export gate)**, not the PDF builder.

---

## Input Artifacts

The builder reads from `2_Data/metadata/generated/<RUN_TAG>/`:

| File | Purpose | Required |
|------|---------|----------|
| `stage1_struct__arm{ARM}.jsonl` | Master table (markdown) | Yes |
| `s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` (new format, 2025-12-23) 또는 `s2_results__arm{ARM}.jsonl` (legacy) | Cards (12 cards per set) | Yes |
| `image_policy_manifest__arm{ARM}.jsonl` | Image placement policy (FRONT/BACK/NONE) | Yes |
| `s4_image_manifest__arm{ARM}.jsonl` | Image file paths | Yes |
| `images/IMG__*.png` | Actual image files | Yes (unless `--allow_missing_images`) |

---

## PDF Layout

### Page Structure

- **Page size:** A4 (portrait)
- **Margins:** 2cm on all sides
- **Fonts:** Helvetica (consistent across arms)

### Section Order

1. **Master Table**
   - Rendered as a grid table
   - Wraps long text within cells
   - Header row with gray background

2. **Infographic**
   - Group-level visual (16:9 aspect ratio)
   - Scaled to fit page width while preserving aspect ratio

3. **Cards** (12 cards total)
   - Stable order: entity order from S1, then card_role (Q1→Q2→Q3)
   - Each card includes:
     - Header: `Entity: <name> | Role: Q1/Q2/Q3 | Type: BASIC/MCQ`
     - Question (labeled "Q:")
     - Image (if applicable, based on `image_placement`)
     - Answer/explanation (labeled "A:")

### Image Placement

Images are placed according to S3 policy manifest (`image_placement`):

- **FRONT:** Image ABOVE the question (front text)
- **BACK:** Image BELOW the question (between Q and A)
- **NONE:** No image

---

## Surrogate Mapping (Blinded Mode)

For blinded mode, a CSV file maps `(group_id, arm)` to `surrogate_set_id`:

**Format (`surrogate_map.csv`):**
```csv
group_id,arm,surrogate_set_id
G0123,A,SET_001
G0123,B,SET_002
...
```

If the surrogate map is missing, the builder falls back to a hash-based surrogate (not recommended for production).

---

## Error Handling

### Fail-Fast Conditions

The builder will raise `RuntimeError` if:

1. S1 record not found for the specified `group_id`
2. S2 records not found for the specified `group_id`
3. Expected 12 cards but found different count (unless `--allow_missing_images`)
4. Required image missing (Q1/Q2 images, infographic) unless `--allow_missing_images`
5. Surrogate not found in mapping (blinded mode)

Note: These are **structural/artifact validation checks** (inputs exist and can be rendered), not content-quality evaluation.

### Validation

- Card count: Must be exactly 12 for S0 (configurable via `--allow_missing_images`)
- Image placement: Validated against S3 policy manifest
- Image files: Checked for existence (unless `--allow_missing_images`)

---

## Output Location

PDFs are written to:
```
6_Distributions/QA_Packets/
```

**Naming:**
- Non-blinded: `SET_{group_id}_arm{arm}.pdf`
- Blinded: `SET_{surrogate_set_id}.pdf`

---

## Dependencies

- `reportlab` (PDF generation)
- Standard library: `argparse`, `csv`, `json`, `pathlib`

Install with:
```bash
pip install reportlab
```

---

## Related Documents

- `QA_Framework.md` - Overall QA framework
- `QA_Blinding_Procedure.md` - Blinding requirements
- `S3_S4_Code_Documentation.md` - Image policy and manifest structure

---

## Smoke Test

**Command:**
```bash
python 3_Code/src/07_build_set_pdf.py \
  --base_dir . \
  --run_tag TEST_S2_V7_20251220_105343 \
  --arm A \
  --group_id G0123 \
  --out_dir 6_Distributions/QA_Packets
```

**Expected Output:**
- `6_Distributions/QA_Packets/SET_G0123_armA.pdf`

**Basic Checks:**
- Page count > 0
- Contains "Master Table" section
- Contains "Infographic" section
- Contains "Cards" section
- Exactly 12 cards
- Images placed correctly (FRONT/BACK/NONE)

---

## Combined PDF Generation

### Multi-Group Combined PDF

For generating a single PDF containing content from multiple groups (e.g., all specialties):

**Script:** `3_Code/Scripts/generate_sample_all_specialties.py`

**Features:**
- Selects one random group per specialty
- Generates one combined PDF with all selected groups
- Each group section includes: Master Table → Infographic → Cards
- Header format: `Specialty - region - category` (top left, minimal)

**Usage:**
```bash
python3 3_Code/Scripts/generate_sample_all_specialties.py \
  --base_dir . \
  --run_tag SAMPLE_ALL_20251220_180008 \
  --arm A \
  --skip_s1_s2 \
  --skip_s3_s4
```

**Output:**
- Combined PDF: `6_Distributions/QA_Packets/SAMPLE_ALL_SPECIALTIES_armA_{run_tag}.pdf`
- Combined Anki: `6_Distributions/anki/MeducAI_{run_tag}_armA.apkg`

---

## Entity ID Format Normalization

### Issue

Image filenames use `DERIVED_xxx` (underscore) format due to filename sanitization, but S2 records use `DERIVED:xxx` (colon) format. This mismatch causes image mapping failures.

### Solution

**Normalization in `load_s4_image_manifest()`:**
- Converts `DERIVED:xxx` → `DERIVED_xxx` when creating mapping keys
- Handles both formats for compatibility

**Normalization in `build_cards_section()`:**
- Converts S2's `entity_id` from `DERIVED:xxx` to `DERIVED_xxx` for lookup

**Result:**
- Works with both normally-generated manifests (colon format) and regenerated manifests (underscore format)
- Consistent image mapping across PDF and Anki export

**Related Code:**
- `07_build_set_pdf.py`: `load_s4_image_manifest()`, `build_cards_section()`
- `07_export_anki_deck.py`: `process_card()` (also normalized)

---

## Notes

- **No LLM calls:** The builder is purely deterministic, reading from frozen schemas
- **No network calls:** All data is read from local files
- **Identical layout:** Fonts, spacing, and page structure are identical across arms to avoid provenance cues
- **Read-only:** Does not modify any frozen schemas (S1, S2, S3, S4)
- **Entity ID normalization:** Handles both colon and underscore formats for compatibility

