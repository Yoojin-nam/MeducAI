# Infographic schema: current vs proposed (S3 → S4)

This document summarizes the **current** artifacts passed from S3 to S4 for infographic generation and the **proposed** additions to improve stability, text control, and profile-based behavior (QC/Equipment vs others).

## Current schemas (observed)

### S3 output: `S3_IMAGE_SPEC_v1.0`

S3 writes `s3_image_spec__arm{A|B}.jsonl` with multiple `spec_kind` values. For infographics, `spec_kind="S1_TABLE_VISUAL"` entries include:

- **Identity / routing**
  - `schema_version`: `"S3_IMAGE_SPEC_v1.0"`
  - `run_tag`, `group_id`
  - `spec_kind`: `"S1_TABLE_VISUAL"`
  - `cluster_id`: optional (present when clustering is used)
  - `visual_type_category`: e.g. `"QC"`, `"Pathology_Pattern"`, `"General"`, ...
  - `template_id`: e.g. `"TABLE_VISUAL_v1__QC"`

- **Prompt payload**
  - `prompt_en`: full system+user prompt for S4

- **Table audit payload**
  - `master_table_markdown_kr_original`: full table from S1 (audit)
  - `master_table_markdown_kr_compact`: compact 4-col table (audit)
  - `master_table_input_kind`: `"compact"` or `"full"`

- **Optional constraint payload (from S1 clustering, when present)**
  - `infographic_hint_v2`
  - `constraint_block`
  - `sufficiency_flags`
  - `requires_human_review`

### S4 output: `S4_IMAGE_MANIFEST_v1.0`

S4 writes `s4_image_manifest__arm{A|B}.jsonl`. For infographics:

- `schema_version`: `"S4_IMAGE_MANIFEST_v1.0"`
- `run_tag`, `group_id`
- `spec_kind`: `"S1_TABLE_VISUAL"`
- `cluster_id`: optional (present when clustering is used)
- `media_filename`, `image_path`
- `generation_success`, `image_required`
- RAG fields: `rag_enabled`, `rag_queries_count`, `rag_sources_count`

## Proposed additions (planned)

### Additions to `S1_TABLE_VISUAL` (S3)

Add deterministic metadata so downstream can enforce stronger contracts:

- **Profile routing**
  - `infographic_profile`: `"default"` | `"qc_equipment"`
  - `text_budget_profile`: `"default_exampoint2"` | `"qc_equipment_richer"`

- **Allowed text (for prompt contract / QA)**
  - `allowed_text_en`: list of allowed EN tokens/phrases (table-derived, deduped, sorted)
  - `allowed_text_kr`: list of allowed KR tokens/phrases from exam points (table-derived)
  - `allowed_text_hash`: short hash of allowed-text lists (audit)

- **Exam point expansion policy**
  - `exam_point_tokens_kr`: per-entity tokens up to 2 (deterministic)

- **Policy flags (if enabled)**
  - `ocr_gate_enabled`, `ocr_gate_max_retries`, `ocr_gate_strictness`

## Notes
- This document is descriptive and is safe to update as the contract evolves.


