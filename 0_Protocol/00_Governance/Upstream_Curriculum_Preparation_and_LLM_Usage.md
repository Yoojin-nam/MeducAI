# Upstream Curriculum Preparation and LLM Usage Protocol

## Status
- **Status:** Canonical
- **Applies to:** MeducAI (Radiology Board Exam Preparation)
- **Scope:** Upstream Curriculum & Law Corpus Preparation (Pre–S0)
- **Last Updated:** 2025-12-18

---

## 1. Purpose and Positioning

This document defines the **upstream data preparation process** used prior to the MeducAI S0–S4 pipeline.

This upstream process:
- Prepares curriculum and examination scope data
- Is **not** part of model comparison, evaluation, or allocation experiments
- Serves solely to establish a **single source of truth (SSOT)** for downstream canonical processing

All experimental, comparative, or evaluative claims begin **after** this upstream stage.

---

## 2. Source Documents (Frozen)

The following documents constitute the authoritative source corpus for curriculum scope and exam weighting.

### 2.1 Board Examination Plan
- **Document:** Board_Exam_Plan.pdf
- **Description:** Official examination blueprint for the 69th Korean Radiology Board Examination (2026)
- **Usage:** Domain-level and category-level exam weight reference
- **Status:** Frozen (read-only)

### 2.2 Radiology Curriculum
- **Document:** Radiology_Curriculum.pdf
- **Description:** Official radiology curriculum defining learning objectives and topic coverage
- **Usage:** Extraction of learning objectives and topic taxonomy
- **Status:** Frozen (read-only)

No modification or reinterpretation of these source documents occurs after freezing.

---

## 3. Upstream Processing Overview

The upstream preparation pipeline consists of the following conceptual steps:

1. **Parsing**
   - Curriculum documents were parsed into structured units (sections, objectives).
2. **Enrichment**
   - Objectives were augmented with tags, domain labels, and metadata.
3. **Translation**
   - Korean curriculum objectives were translated into English for LLM compatibility.
4. **Weight Integration**
   - Examination blueprint data were merged to assign relative weight factors.

These steps were initially conducted using exploratory Jupyter notebooks for rapid iteration and expert review.

---

## 3.1 v2 Preprocess Pipeline (Operational; Code SSOT)

This repository maintains an explicit, versioned upstream preprocessing pipeline (v2) to improve
traceability and reduce silent objective loss from PDF parsing.

**Code SSOT (authoritative implementation):**
- `3_Code/src/preprocess/run_pipeline_v2.py` (orchestrator)
- `3_Code/src/preprocess/parse_curriculum_pdf_v2.py` (PDF → structured rows)
- `3_Code/src/preprocess/merge_weights_v2.py` (weight integration)
- `3_Code/src/preprocess/build_groups_canonical_v2.py` (canonical group construction)

**Audit (required output):**
- `3_Code/Scripts/audit_curriculum_parsing_coverage.py`
  - Compares `groups_canonical*.csv` against raw `Radiology_Curriculum.xlsx` using normalization rules
  - Reports (a) true missing objectives, (b) objectives present but classified under different specialties
  - Generates a run-tagged markdown audit artifact under `2_Data/processed/`

**Normalization rule (binding):**
- Difficulty suffix markers like `(A).`, `(B).`, `(S).` MUST be treated as non-semantic formatting and stripped
  for objective text matching during audits and canonicalization.

---

## 4. LLM Usage and MI-CLEAR-LLM Compliance

### 4.1 Logged LLM Execution

A formally logged MI-CLEAR-LLM run is used during upstream enrichment and translation steps (v2 pipeline).

- **Model (v2 standard):** `gemini-3-flash-preview`
- **Decoding (deterministic):** `temperature=0.0`, `top_p=1.0`, `top_k=1`
- **Logged artifacts (v2 standard):**
  - `2_Data/processed/logs/<run_id>.jsonl` (batch-by-batch provenance + retries + durations)
  - `2_Data/processed/logs/<run_id>.system_prompts.txt` (system prompt snapshot)
- **Input Data (v2):** `Radiology_Curriculum_Enriched_v2_norm.xlsx` (for translate) and upstream SSOT tables
- **Purpose:**
  - Structured analysis of learning objectives
  - Visual type classification
  - Educational content scaffolding (non-evaluative)

All prompts, parameters, and metadata are preserved as run-tagged artifacts under:
- `2_Data/processed/logs/`

This execution satisfies MI-CLEAR-LLM transparency requirements for:
- Model identification
- Prompt disclosure
- Parameter disclosure
- Input/output traceability

---

### 4.2 Translation and Tag Canonicalization

A controlled translation and tagging dictionary is maintained in versioned form:

- `2_Data/metadata/translation_map_v2.json` (versioned)
- Promoted to `2_Data/metadata/translation_map.json` when v2 becomes the operational default.

This file defines:
- Korean → English label mappings
- Stable tag identifiers (slugs)

Rules:
- Tags are **never regenerated dynamically**
- All downstream tagging must reference this canonical mapping
- Synonyms are resolved to existing tags only

---

## 5. Single Source of Truth (SSOT)

The final output of upstream preparation is a single frozen dataset:

- **File:** `Radiology_Curriculum_Weight_Factor.xlsx`
- **Role:** Sole input to Group Canonical construction

### 5.2 Operational SSOT (v2)

- **File:** `2_Data/processed/Radiology_Curriculum_Weight_Factor_v2.xlsx`
- **Role:** Current operational SSOT for canonical group construction (`groups_canonical_v2.csv`)

### 5.1 Data Semantics

The dataset includes:
- Raw curriculum text (Korean)
- Curated English translations
- Controlled tags and scope labels
- Examination-driven weight factors
- Auxiliary metadata (notes, levels)

No downstream process reads:
- PDFs
- Jupyter notebooks
- Intermediate artifacts

---

## 6. Freeze and Provenance Policy

Once frozen:
- The SSOT dataset is immutable
- Any modification requires:
  - Explicit protocol revision
  - New frozen snapshot
  - Updated provenance record

A snapshot including:
- Frozen SSOT
- MI-CLEAR-LLM run report
- Translation/tag canonical map

is stored under a run-tagged provenance directory.

---

## 7. Boundary to Downstream Pipeline

The MeducAI experimental pipeline (S0–S4 and FINAL):

- **Begins after this protocol**
- Treats the SSOT as an external, fixed input
- Does not influence or modify upstream data

Therefore:
- No experimental outcome can affect curriculum scope
- No LLM decision within S0–S4 alters weights or objectives

---

## 8. Summary Declaration

The upstream curriculum preparation process is:
- Transparent
- Reproducible
- MI-CLEAR-LLM compliant
- Logically and temporally separated from experimental pipelines

This protocol establishes a clean and auditable boundary between
**data preparation** and **LLM-based educational experimentation**.

---