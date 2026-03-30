# MeducAI Step05 (S5) Validation Contract (Canonical)

**Status:** Canonical  
**Version:** 1.1  
**Frozen:** No  
**Applies to:** Step05 (S5: LLM-based Validation & Triage)  
**Boundary:** S4 → **S5** → S6  
**Last Updated:** 2025-12-28  
**Compliance:** MI-CLEAR-LLM / IRB-ready

---

## 0. Purpose (Normative)

This document defines the **canonical meaning, scope, authority, and prohibitions** of **Step05 (S5)** in the MeducAI pipeline.

Its purpose is to **permanently fix S5 as a triage/flagging stage** that provides evidence to human raters **without contaminating primary endpoints** and to **eliminate all ambiguity** regarding:

- validation vs auto-correction
- triage/flagging vs content modification
- information provision vs decision making
- S5 vs S1/S2/S3/S4 responsibility boundaries

This definition is **binding** for all future protocols, code, prompts, QA procedures, and research documents. Any deviation constitutes a **protocol violation**.

---

## 1. Authoritative One-Line Definition (Binding)

> **Step05 (S5) is an LLM-based triage/flagging stage that validates S1 tables and S2 cards for content quality,**
> **provides evidence and suggestions to human raters,**
> **and never generates, modifies, or auto-corrects upstream content.**

Corollaries (non-negotiable):

- S5 **does not generate** new content (tables or cards)
- S5 **does not modify** S1/S2 artifacts
- S5 **does not auto-correct** errors
- S5 **does not stop** the pipeline (no fail-fast)
- S5 **does not decide** deployment or selection (human raters decide)

---

## 2. Structural Position in the Pipeline

| Dimension | Definition |
|-----------|------------|
| Ownership | LLM-based validation & triage stage |
| Input authority | S1 tables (`stage1_struct__arm{arm}.jsonl`) + S2 cards (`s2_results__arm{arm}.jsonl`) (read-only) |
| Control unit | Group (for S1 table validation) + Card (for S2 card validation) |
| Primary role | Content quality validation, error flagging, evidence provision |
| Output nature | Validation results with flags, scores, issues, and RAG evidence |
| Downstream | S6 (export) + Human raters (via 2-pass workflow) |

Formal position:

```
S1 (Structure)
→ S2 (Execution)
→ S3 (Policy Resolution & Image Spec Compilation)
→ S4 (Image Generation)
→ S5 (Validation & Triage)
→ S6 (Export)
```

---

## 3. What S5 **IS** (Positive Definition)

S5 **is**:

- A **triage/flagging system** that identifies potential issues in S1 tables and S2 cards
- An **evidence provider** that supplies RAG-backed evidence when flagging blocking errors
- An **information assistant** that helps human raters identify issues more efficiently
- A **non-modifying validator** that reads and evaluates but never writes upstream artifacts
- A **reproducible validation step** with fixed model configuration (arm-independent)

Formal identity:

- **S5 = Triage**
- **S5 = Flagging**
- **S5 = Evidence Provision**
- **S5 ≠ Generation**
- **S5 ≠ Modification**
- **S5 ≠ Auto-Correction**
- **S5 ≠ Decision Making**

---

## 4. What S5 **IS NOT** (Explicit Prohibitions)

### 4.1 Content Generation / Modification (Forbidden)

- ❌ Generate new S1 tables or S2 cards
- ❌ Edit or rewrite table content
- ❌ Modify card text, answers, or structure
- ❌ Add or remove medical facts
- ❌ Regenerate content to fix errors

### 4.2 Auto-Correction (Forbidden)

- ❌ Automatically fix errors in S1/S2 artifacts
- ❌ Replace incorrect content with corrected versions
- ❌ Apply suggested fixes without human approval
- ❌ Modify upstream artifacts based on validation results

### 4.3 Decision Making (Forbidden)

- ❌ Decide whether content should be deployed
- ❌ Select or reject cards based on validation results
- ❌ Stop the pipeline (fail-fast) based on validation results
- ❌ Override human rater decisions

### 4.4 Schema / Format Validation (Out of Scope)

- ❌ Validate JSON schema (S1 Gate responsibility)
- ❌ Validate format constraints (S1 Gate responsibility)
- ❌ Validate structural integrity (S1 Gate responsibility)

---

## 5. Input Contracts

### 5.1 Required Input Artifacts

S5 MUST consume the following artifacts (read-only):

1. **S1 Structure** (`stage1_struct__arm{arm}.jsonl`)
   - Required fields: `group_id`, `master_table_markdown_kr`, `objective_bullets`, `group_path`, `entity_list`
   - Schema version: `S1_STRUCT_v1.3` (frozen)

2. **S2 Cards** (`s2_results__arm{arm}.jsonl`)
   - Required fields: `group_id`, `entity_id`, `entity_name`, `anki_cards`
   - Schema version: `S2_RESULTS_v3.2` (or compatible)

### 5.2 Input Validation

S5 MUST:

- Verify input artifacts exist and are readable
- Handle missing artifacts gracefully (log warning, continue)
- **NOT** validate schema/format (assumes S1 Gate passed)

---

## 6. Output Contracts

### 6.1 Output Artifact

**File**: `2_Data/metadata/generated/<RUN_TAG>/s5_validation__arm{arm}.jsonl`

**Format**: NDJSON (one JSON object per line, one group per line)

**Schema Version**: `S5_VALIDATION_v1.0`

### 6.2 Required Output Fields

Each output record MUST include:

- `schema_version`: `"S5_VALIDATION_v1.0"`
- `group_id`: string (echoed from S1)
- `arm`: string (arm identifier)
- `validation_timestamp`: ISO 8601 timestamp
- `s5_snapshot_id`: string (unique identifier for reproducibility)
- `s5_model_info`: object (model configuration, arm-independent)
- `s1_table_validation`: object (S1 table validation results)
- `s2_cards_validation`: object (S2 cards validation results)

### 6.3 S5 Snapshot ID

**Purpose**: Ensure reproducibility and version tracking

**Format**: `s5_{run_tag}_{group_id}_{arm}_{s5_model_version}_{hash}`

**Hash**: SHA256 of (S5 validation result JSON + model configuration)

**Inclusion**: MUST be included in every S5 validation result

---

## 7. LLM Model Configuration (Arm-Independent)

### 7.1 S1 Table Validation

- **Model**: Pro model (e.g., `models/gemini-2.0-pro-exp`)
- **Configuration**:
  - `thinking=True` (reasoning process enabled)
  - `rag_enabled=True` (RAG knowledge base enabled)
- **Call Frequency**: 1 call per table (per group)
- **Rationale**: Tables are complex, warrant Pro model; RAG provides evidence for validation

### 7.2 S2 Card Validation

- **Model**: Flash model (e.g., `models/gemini-2.0-flash-exp`)
- **Configuration**:
  - `thinking=True` (reasoning process enabled)
  - `rag_enabled=True` (RAG knowledge base enabled)
- **Call Frequency**: 1 call per card
- **Rationale**: Cards are simpler, Flash sufficient; RAG provides evidence for validation

### 7.3 Arm Independence

**Critical Constraint**: S5 model configuration is **fixed across all arms**.

- Same model (Pro for tables, Flash for cards) for all arms
- Same configuration (thinking=on, RAG=on) for all arms
- Same prompt templates for all arms

**Rationale**: S5 tool effect must be measured separately from arm performance. Varying S5 models across arms would confound arm comparison.

---

## 8. RAG Evidence Logging Requirements

### 8.1 When RAG Evidence is Required

RAG evidence MUST be logged when:

- S5 flags a **blocking error** (Technical Accuracy = 0.0)
- S5 claims a factual error that could mislead learners

### 8.2 RAG Evidence Structure

When required, RAG evidence MUST include:

- `source_id`: string (RAG document identifier)
- `source_excerpt`: string (relevant excerpt from RAG source, max 500 chars)
- `relevance`: string (one of: "high" | "medium" | "low")

### 8.3 Purpose

- **Auditability**: Human raters can verify S5 claims against RAG sources
- **Transparency**: S5 blocking error flags are backed by evidence
- **Reproducibility**: RAG evidence enables verification of S5 validation results

---

## 9. No Fail-Fast Policy

### 9.1 Pipeline Continuation

S5 validation **MUST NOT** stop the pipeline, regardless of validation results.

- S5 errors (LLM API failures, parsing errors) are logged but do not block S6
- S5 blocking error flags do not stop the pipeline
- S5 validation failures are logged but pipeline continues

### 9.2 Error Handling

S5 MUST:

- Handle LLM API errors gracefully (retry with backoff, log error, continue)
- Handle parsing errors gracefully (log error, continue with partial results)
- Handle missing input artifacts gracefully (log warning, skip group, continue)

### 9.3 Downstream Impact

- S6 (export) runs regardless of S5 validation results
- Human raters receive S5 results (if available) but can rate without S5 results
- Missing S5 results do not block human rating workflow

---

## 10. Validation Criteria

### 10.1 S1 Table Validation Criteria

S5 validates S1 tables against:

- **Technical Accuracy** (0/0.5/1 scale):
  - 1.0: No factual errors
  - 0.5: Minor inaccuracies, ambiguous expressions
  - 0.0: **Blocking error (clinical safety-critical)**: factual error or unsafe guidance that could mislead clinical decisions
- **Educational Quality** (1-5 Likert scale):
  - 5: Highly valuable, directly targets core exam concepts
  - 4: Valuable, addresses important concepts
  - 3: Adequate, marginally useful
  - 2: Limited value, peripheral
  - 1: Poor value, unlikely to aid learning
- **Scope/Alignment**: Alignment with educational objectives
- **Information Density**: Appropriate information density (not too simple/complex)

### 10.2 S2 Card Validation Criteria

S5 validates S2 cards against:

- **Technical Accuracy** (0/0.5/1 scale): Same as S1 table validation
- **Educational Quality** (1-5 Likert scale): Same as S1 table validation
- **Structure Quality**: Question-answer structure clarity (**non-blocking unless it causes clinical unsafe content**)
- **Image Dependency**: Whether card requires image for understanding (**non-blocking**)

#### 10.2.1 Anki MCQ convention (normative)
For MCQ cards, multiple-choice options are stored in structured fields (e.g., `options[]`, `correct_index`) and may not appear verbatim in `front`.

- S5 MAY evaluate MCQ validity using these structured fields when available.
- S5 MUST NOT flag “options missing in front” as a blocking error if options are present in the structured fields.

#### 10.2.2 Blocking semantics (normative)
`blocking_error=true` is reserved for **clinical safety-critical** issues only.

- If `blocking_error=true`, S5 MUST set `technical_accuracy=0.0`.
- If an item is educationally weak, ambiguous, or structurally imperfect but not clinically unsafe, S5 MUST use `issues[]` and non-blocking severities instead of `blocking_error`.

### 10.3 Reference Standards

Validation criteria are based on:

- **QA Evaluation Rubric v2.0** (`06_QA_and_Study/QA_Operations/QA_Evaluation_Rubric.md`)
- **QA Metric Definitions** (`05_Pipeline_and_Execution/QA_Metric_Definitions.md`)
- **QA Framework v2.0** (`06_QA_and_Study/QA_Framework.md`)

---

## 11. Human Rater Integration

### 11.1 2-Pass Workflow

S5 validation results are provided to human raters via a **2-pass workflow**:

1. **Pre-S5 Pass**: Human rates content **before** seeing S5 results (primary endpoint)
2. **S5 Reveal**: S5 validation results are revealed after Pre-S5 submission is locked
3. **Post-S5 Pass**: Human may correct ratings with mandatory change logging (secondary endpoint)

### 11.2 S5 Results Display

S5 validation results are displayed to human raters with:

- S5 blocking error flag (if any)
- S5 quality assessment (if any)
- S5 issues list (structured display)
- RAG evidence citations (if blocking error claimed)

### 11.3 Endpoint Purity

**Critical Constraint**: Pre-S5 ratings (primary endpoint) are **never** influenced by S5 results.

- S5 results are **hidden** until Pre-S5 submission is locked
- Pre-S5 ratings are **immutable** after lock
- Post-S5 ratings (secondary endpoint) measure tool effect, not arm performance

---

## 12. Responsibility Boundary Summary

| Decision | Owner |
|----------|-------|
| Entity definition | S1 |
| Card generation | S2 |
| Image policy | S3 |
| Image generation | S4 |
| **Content validation** | **S5** |
| **Error flagging** | **S5** |
| **Evidence provision** | **S5** |
| Content modification | Human raters (via Post-S5 pass) |
| Deployment decision | Human raters / QA process |
| Export/packaging | S6 |

---

## 13. Related Documents

- `S5_Validation_Schema_Canonical.md`: S5 output schema specification
- `Human_Rating_Schema_Canonical.md`: Human rating schema (2-pass workflow)
- `Pipeline_Canonical_Specification.md`: Pipeline overview
- `S5_Validation_Plan_OptionB_Canonical.md`: Detailed implementation plan
- `QA_Evaluation_Rubric.md`: QA evaluation criteria
- `QA_Metric_Definitions.md`: QA metric definitions

---

## 14. Version History

- **v1.0** (2025-12-26): Initial canonical definition

---

**Document Status**: Canonical  
**Last Updated**: 2025-12-26  
**Owner**: MeducAI Research Team

