# MeducAI Pipeline Source Code (3_Code)

This directory contains the core Python scripts that implement the MeducAI generative pipeline.

**Design Principles:** Group-first, Reproducibility-first (MI-CLEAR-LLM compliant).  
**Execution Policy:** All execution must be performed using the project root as the current working directory, referencing scripts via `python3 3_Code/src/{script_name}.py`.

---

## Directory Structure

```
3_Code/
├── src/              # Core pipeline scripts
│   └── tools/        # Utility tools (anki, batch, final_qa, qa, regen, etc.)
├── Scripts/          # Execution scripts and utilities
├── prompt/           # LLM prompts (S1, S2, S4, S5, S6)
├── configs/          # Configuration files (tagging rules, styles)
├── archived/         # Archived scripts and workflows
│   └── translation_workflow_2026-01-07/  # Medical term translation scripts (completed)
└── notebooks/        # Jupyter notebooks for analysis
```

---

## Core Pipeline Flow (S1 → S2 → S3 → S4 → PDF/Anki)

The pipeline is sequential and idempotent, ensuring auditability at every stage.

| Step | Script | Input | Output | Role |
|------|--------|-------|--------|------|
| **S1/S2** | `01_generate_json.py` | `groups_canonical.csv`, objectives | `stage1_struct__arm{arm}.jsonl`, `s2_results__arm{arm}.jsonl` | **Content Generation.** S1: Master table and entity list. S2: Anki cards (Q1/Q2) with image hints (2-card policy; images on back). |
| **S3** | `03_s3_policy_resolver.py` | S1/S2 outputs | `image_policy_manifest__arm{arm}.jsonl`, `s3_image_spec__arm{arm}.jsonl` | **Policy Resolution & Image Spec Compilation.** Determines image requirements and compiles image generation specs. |
| **S4** | `04_s4_image_generator.py` | S3 image specs | `IMG__*.png`, `s4_image_manifest__arm{arm}.jsonl` | **Image Generation.** Generates images using Gemini API (card images and table visuals). |
| **S5** | `05_s5_validator.py` | S1/S2 outputs | `s5_validation__arm{arm}.jsonl` | **Validation & Triage.** LLM-based content quality validation with RAG evidence. Three-way decision: PASS/CARD_REGEN/IMAGE_REGEN. |
| **S6** | `06_s6_positive_instruction_agent.py` | S5 validation outputs | Regenerated images | **Positive Instruction Agent.** Visual regeneration with feedback based on S5 triage decisions. |
| **PDF** | `07_build_set_pdf.py` | S1/S2/S3/S4 outputs | `SET_{group_id}_arm{arm}_{run_tag}.pdf` | **PDF Distribution.** Builds QA packet PDFs with cards and images. |
| **Anki** | `07_export_anki_deck.py` | S1/S2/S4 outputs | `MeducAI_{run_tag}_arm{arm}.apkg` | **Anki Deck Export.** Creates Anki packages with cards and images. |

### Export Policy (Missing Images & Quality Gate)

- **Quality gate lives in Option C (S5 triage → S6 export gate)**, not in PDF/Anki exporters.
- **`07_build_set_pdf.py` / `07_export_anki_deck.py` are deterministic “render/export” tools** (no LLM calls). They may fail-fast when required artifacts (especially images) are missing.
- **Final export rule**: do **not** use `--allow_missing_images`. Instead, fix upstream (typically re-run S4 image generation) and then export again.
- **Preview/debug only**:
  - PDF: `--allow_missing_images` inserts placeholders instead of failing.
  - Anki: `--allow_missing_images` skips cards whose required images are missing (see also `--image_only`).

---

## Execution Scripts

### Full Pipeline

**Script:** `Scripts/run_full_pipeline_armA_sample_v8.sh`

Executes the complete pipeline (S1/S2 → S3 → S4 → PDF → Anki) for Arm A with sample 1.

```bash
# With auto-generated RUN_TAG
bash 3_Code/Scripts/run_full_pipeline_armA_sample_v8.sh

# With custom RUN_TAG
bash 3_Code/Scripts/run_full_pipeline_armA_sample_v8.sh FULL_PIPELINE_V8_20251220_180000
```

### PDF/Anki Only

**Script:** `Scripts/run_pdf_anki_only.sh`

Regenerates PDF and Anki outputs from existing S1/S2/S3/S4 results.

```bash
bash 3_Code/Scripts/run_pdf_anki_only.sh <RUN_TAG>
```

### 6-Arm S1/S2 Execution

**Script:** `Scripts/run_6arm_s1_s2_full.py`

Executes S1/S2 for multiple arms (A-F).

```bash
python3 3_Code/Scripts/run_6arm_s1_s2_full.py \
  --run_tag test_6arm \
  --sample 1 \
  --arms A B C  # or omit for all arms
```

---

## Output Structure

All outputs are stored under:
```
2_Data/metadata/generated/<run_tag>/
├── stage1_struct__arm{arm}.jsonl      # S1 output
├── s2_results__arm{arm}.jsonl          # S2 output
├── image_policy_manifest__arm{arm}.jsonl  # S3 policy output
├── s3_image_spec__arm{arm}.jsonl      # S3 image spec output
├── s4_image_manifest__arm{arm}.jsonl  # S4 output
└── images/                             # Generated image files
    └── IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.png
```

Distribution outputs:
```
6_Distributions/
├── QA_Packets/
│   └── SET_{group_id}_arm{arm}.pdf    # PDF output
└── anki/
    └── MeducAI_{run_tag}_arm{arm}.apkg  # Anki output
```

---

## Key Scripts Details

### S1/S2: `01_generate_json.py`

**Purpose:** Generates structured content (S1) and Anki cards (S2).

**Key Features:**
- Group-first processing
- Entity-level card generation (Q1, Q2)
  - Note: Q3 is deprecated/removed in the current 2-card policy.
- Image hint generation for S3
- 6-arm experimental design support

**Usage:**
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm A \
  --mode S0 \
  --sample 1
```

### S3: `03_s3_policy_resolver.py`

**Purpose:** Resolves image policies and compiles image generation specs.

**Key Features:**
- Deterministic policy resolution (Q1: required, Q2: required)
  - Note: Q3 is deprecated/removed in the current 2-card policy.
- Image spec compilation from S2 image hints
- Table visual spec compilation from S1 master tables

**Usage:**
```bash
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm A
```

### S4: `04_s4_image_generator.py`

**Purpose:** Generates images using Gemini API.

**Key Features:**
- Card images (4:5 aspect ratio, 1K resolution)
- Table visuals (16:9 aspect ratio, 4K resolution)
- Fail-fast for required images (Q1, Q2, table visuals)

**Usage:**
```bash
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm A
```

### S5 Validation: `05_s5_validator.py`

**Purpose:** LLM-based content quality validation with RAG evidence.

**Key environment variables (reproducibility):**
- `TEMPERATURE_STAGE4`: S4 image generation temperature (default `0.2`)
- `TEMPERATURE_STAGE5`: S5 validation temperature (default `0.2`)

**Usage:**
```bash
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm A
```

### PDF: `07_build_set_pdf.py`

**Purpose:** Builds QA packet PDFs.

**Usage:**
```bash
python3 3_Code/src/07_build_set_pdf.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm A \
  --group_id <GROUP_ID> \
  --out_dir 6_Distributions/QA_Packets
```

**Missing images:** For final QA distribution, keep the default strict behavior (no `--allow_missing_images`) and fix missing images upstream (S4). Use `--allow_missing_images` only for preview/debug.

### Anki: `07_export_anki_deck.py`

**Purpose:** Exports Anki decks with cards and images.

**Usage:**
```bash
# 전체 덱 생성
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm A

# 특정 분과 덱 생성
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm A \
  --specialty thoracic_rad

# 11개 분과 일괄 생성
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm A \
  --all_specialties
```

**Specialty Options:**
- `--specialty <ID>`: 특정 분과만 필터링 (예: `abdominal_rad`, `thoracic_rad`)
- `--all_specialties`: 11개 분과 개별 덱 일괄 생성

**Supported Specialties:** `abdominal_rad`, `breast_rad`, `cv_rad`, `gu_rad`, `ir`, `msk_rad`, `neuro_hn_rad`, `nuclear_medicine`, `ped_rad`, `phys_qc_medinfo`, `thoracic_rad`

**Missing images:** For final decks, keep the default strict behavior and fix missing images upstream. For sample/debug, use `--allow_missing_images` (or `--image_only`) to avoid hard failure.

**Detailed Guide:** See `3_Code/src/tools/docs/ANKI_EXPORT_GUIDE.md` for comprehensive usage examples.

---

## Naming Conventions

- **Run Tag:** Unique identifier for each pipeline execution (e.g., `FULL_PIPELINE_V8_20251220_180000`)
- **Arm:** Experimental configuration (A, B, C, D, E, F)
- **Group ID:** Format `G{number}` (e.g., `G001`)
- **Entity ID:** Format `{group_id}__E{number}` (e.g., `G001__E01`)
- **Image Files:** `IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.png`

---

## Prompt Management

Prompts are stored in `prompt/` directory and managed via `prompt/_registry.json`.

**Current Versions:**
- S1: v8 (`S1_SYSTEM__v8.md`, `S1_USER_GROUP__v8.md`)
- S2: v7 (`S2_SYSTEM__v7.md`, `S2_USER_ENTITY__v7.md`)
- S4: v1/v3 (concept and exam prompts)

---

## Dependencies

See `requirements.txt` for Python dependencies.

**Key Dependencies:**
- `google-genai` (Gemini API)
- `reportlab` (PDF generation)
- `genanki` (Anki deck export)
- `pandas` (data processing)

---

## Related Documentation

- **Protocol Documentation:** `0_Protocol/`
- **Implementation Change Log:** `0_Protocol/00_Governance/Implementation_Change_Log_2025-12-20.md`
- **Step Contracts:** `0_Protocol/04_Step_Contracts/`
- **Pipeline Execution:** `0_Protocol/05_Pipeline_and_Execution/`
- **Anki Export Guide:** `3_Code/src/tools/docs/ANKI_EXPORT_GUIDE.md` (분과별 덱 생성 포함)
- **Translation Workflow Archive:** `3_Code/archived/translation_workflow_2026-01-07/README.md`
- **Handoff Documentation:**
  - Execution Safety: `0_Protocol/01_Execution_Safety/handoffs/`
  - Pipeline Execution: `0_Protocol/05_Pipeline_and_Execution/handoffs/`
  - QA Operations: `0_Protocol/06_QA_and_Study/QA_Operations/handoffs/`

---

## Recent Updates

### 2026-01-09: Translation Workflow Completion & Consolidation

**Translation Workflow Completed:**
- Medical term English-only policy fully implemented
- 27 translation/debugging scripts archived to `archived/translation_workflow_2026-01-07/`
- Production export scripts remain in `src/tools/anki/`:
  - `export_final_anki_integrated.py` - Production Anki export
  - `merge_anki_decks_with_regen.py` - Deck merging with regenerated cards
  - `update_anki_with_regen.py` - Card updates with regeneration

**Archived Scripts (Reference Only):**
- Translation modules, retranslation tools, debugging scripts
- See `archived/translation_workflow_2026-01-07/README.md` for complete inventory
- Handoff document: `0_Protocol/01_Execution_Safety/handoffs/HANDOFF__MEDTERM_ENGLISH_ONLY__S2_APPSHEET_ANKI__2026-01-07.md`

**Language Policy:**
- All Anki decks and AppSheet exports now use English medical terminology
- Sentence structure and formatting preserved during translation
- Applied consistently to baseline and regenerated cards

**Tools Organization:**
- `src/tools/anki/` - Active Anki export and deck management
- `src/tools/batch/` - Batch processing for S5 validation, image generation, text repair
- `src/tools/final_qa/` - AppSheet export and QA assignment generation
- `src/tools/qa/` - QA validation and comparison reports
- `src/tools/regen/` - Regeneration workflow tools (S1R, S2R, positive regen)
- `src/tools/s4/` - S4 realistic image generation
- `src/tools/s5/` - S5 backfill and validation tools

### 2025-12-20: S3/S4 Implementation Updates

See `0_Protocol/00_Governance/Implementation_Change_Log_2025-12-20.md` for detailed change log.

**Key Updates:**
- S1/S2 prompts updated (v8/v7)
- S2 options field preservation bug fix
- PDF/Anki export improvements
- Script improvements (RUN_TAG support, error checking)
- S5/S6 validation and regeneration pipeline implemented
