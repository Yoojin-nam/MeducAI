# FINAL QA Tools (AppSheet Integration)

> ⚠️ **CRITICAL MODULE**: This is a core component for the FINAL QA phase of the MeducAI study.
> It handles expert evaluation assignments and data export for the **6,000-card validation**.
> 
> Related documents:
> - `0_Protocol/06_QA_and_Study/FINAL_QA_Research_Design_Spec.md`
> - `0_Protocol/06_QA_and_Study/FINAL_QA_Form_Design.md`
> - `0_Protocol/06_QA_and_Study/Table_Infographic_Evaluation_Plan.md`

---

## Overview

This tool exports MeducAI pipeline outputs into **AppSheet-ingestable CSV tables** so you can run the QA website flow with **Google login**, **per-rater records**, and **image display**.

## Inputs (sample run)

Run directory example:

- `2_Data/metadata/generated/DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1/`

Expected files inside:

- `s2_results__s1armG__s2armG.jsonl` (card text)
- `stage1_struct__armG.jsonl` (group metadata + master table)
- `s5_validation__armG.jsonl` (S5 validations + per-card image paths)
- `s4_image_manifest__armG.jsonl` (optional fallback for images)
- `images/` (image files)

## Outputs

The exporter writes:

- `Cards.csv` (one row per card)
- `Groups.csv` (one row per group)
- `S5.csv` (one row per `card_uid`, S5 results)
- `Ratings.csv` (default: **header-only template**; AppSheet creates rows at runtime via Add(+))
- `Assignments.csv` (empty template; optional)
- `images/` (copied image files for Drive upload)

## AppSheet table design (recommended)

Create a Google Sheet with tabs (sheet names must match CSV filenames without extension):

- `Cards` (key = `card_uid`)
- `Groups` (key = `group_id`)
- `S5` (key = `card_uid`)
- `Ratings` (key = `rating_id`)
- `Assignments` (key = `assignment_id`)

### Why `card_uid` exists

`card_id` is **not globally unique** across groups (the same entity can appear in multiple groups), so we use:

- `card_uid = "{group_id}::{card_id}"`

as the **stable unique key** for AppSheet tables.

### Column types (AppSheet)

- `Cards[image_filename]`: **Image**
  - Put image files in Drive folder: `<spreadsheet_folder>/images/`
  - Store just the filename (e.g. `IMG__...__Q1.jpg`)
- `Ratings[rater_email]`: **Email** with `Initial value = USEREMAIL()`
- `Ratings[*_ts]`: **DateTime**
- `Ratings[..._pre]`, `Ratings[..._post]`: **Enum** / **Yes/No** depending on field

### Relationships

- `Ratings[card_uid]` Ref → `Cards[card_uid]`
- `Cards[group_id]` Ref → `Groups[group_id]`
- `S5[card_uid]` Ref → `Cards[card_uid]`
- `Assignments[card_uid]` Ref → `Cards[card_uid]`

## Export command

From repo root:

```bash
python 3_Code/src/tools/final_qa/export_appsheet_tables.py \
  --run_dir "/path/to/workspace/workspace/MeducAI/2_Data/metadata/generated/DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1" \
  --out_dir "/path/to/workspace/workspace/MeducAI/2_Data/processed/appsheet/DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1" \
  --copy_images true \
  --verbose
```

### Ratings.csv 정책 (중요)

- **권장(기본값)**: `Ratings.csv`는 **헤더만(0 rows)** 출력합니다.  
  AppSheet에서 평가자가 Add(+)로 평가를 시작하면, 그 시점에 Ratings row가 생성됩니다.
- **레거시(선택)**: Assignments에서 Ratings row를 미리 만들고 싶다면 아래 옵션을 사용하세요.

```bash
python 3_Code/src/tools/final_qa/export_appsheet_tables.py \
  --run_dir "<...>" \
  --out_dir "<...>" \
  --prefill_ratings true
```

## How the QA flow maps to AppSheet UX

This follows `0_Protocol/06_QA_and_Study/FINAL_QA_Form_Design.md`:

- **Pre-S5**: raters fill `blocking_error_pre`, `technical_accuracy_pre`, `educational_quality_pre`, `evidence_comment_pre`
  - After submit: set `pre_submitted_ts` and lock pre fields
- **S5 reveal**: only available after `pre_submitted_ts` exists
  - Action sets `s5_revealed_ts`
  - App shows joined `S5` row for that `card_id`
- **Post-S5**: raters fill `_post` fields; if changed vs pre, require change log


