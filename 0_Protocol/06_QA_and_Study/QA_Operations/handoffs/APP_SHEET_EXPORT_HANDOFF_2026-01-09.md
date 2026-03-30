# AppSheet Export Handoff (FINAL_QA) — 2026-01-09

## Final output location (canonical)

**Final AppSheet package directory (canonical name):**
- `6_Distributions/Final_QA/AppSheet_Export/`

This folder is the **single source of truth** to upload into AppSheet.

## What’s inside

- `Assignments.csv` (kept as-is; assignment history preserved)
- `Cards.csv` (updated to use translated card content)
- `S5.csv` (updated; regen/image_regen fields and regen image filename populated)
- `Groups.csv`
- `Ratings.csv` (template-only; AppSheet creates rows at runtime)
- `images_anki/`, `images_regen/`, `images_realistic/` (copied media assets)
- `group_table_pdfs/` (present)

## Translation sources used (fixed)

We intentionally fixed to **raw (no post-processing) batch translations**:

- **Baseline translated (raw v4):**
  - `2_Data/metadata/generated/FINAL_DISTRIBUTION/archive_medterm_20260109/s2_results__s1armG__s2armG__medterm_en_v4.jsonl`
- **Regen translated (raw v3):**
  - `2_Data/metadata/generated/FINAL_DISTRIBUTION/archive_medterm_20260109/s2_results__s1armG__s2armG__regen__medterm_en_v3.jsonl`

For AppSheet export auto-discovery, these were staged (copied) into the run_dir root as:
- `2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__medterm_en.jsonl`
- `2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen__medterm_en.jsonl`

## Logic used (must match Anki integration)

- **PASS**: baseline content + baseline image
- **CARD_REGEN**: regen content + regen image
- **IMAGE_REGEN**: baseline content + regen image

Notes:
- AppSheet `Cards.csv` uses **baseline translated text** for `front/back`.
- AppSheet `S5.csv` uses `s5_decision` and fills:
  - `CARD_REGEN`: `s5_regenerated_front/back` from translated regen JSONL
  - `IMAGE_REGEN`: keeps regenerated text empty; sets `s5_regenerated_image_filename`

## Integrity checks performed

### Card set consistency (assignment-safe)
- `Cards.csv`: **1284** rows
- `S5.csv`: **1284** rows
- `Assignments.csv`: **1284** rows
- `Assignments ⊆ Cards`: **OK (0 missing)**
- `Cards == S5` by `card_uid`: **OK (0 missing/extra)**

### Media existence
- `Cards.csv.image_filename`: **0 missing files**
- `Cards.csv.realistic_image_filename`: **0 missing files**
- `S5.csv.s5_regenerated_image_filename` for `CARD_REGEN/IMAGE_REGEN`: **0 missing files**

### IMAGE_REGEN specific check
- Total IMAGE_REGEN rows: **62**
- `s5_regenerated_image_filename`:
  - missing: **0**
  - not `images_regen/` prefix: **0**
  - missing file on disk: **0**

## Archiving

To avoid confusion, other AppSheet export folders were archived:
- Archive root: `6_Distributions/Final_QA/archive_appsheet_20260109_105507/`
  - `AppSheet_Export__old_20260109_105507/`
  - `AppSheet_Export_TRANSLATED_FINAL__bak_20260109_104032/`
  - `archive_translation_testing/`

## Primary scripts referenced

- `3_Code/src/tools/final_qa/export_appsheet_tables.py`

