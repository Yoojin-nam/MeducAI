# MeducAI S5 Validation Output JSON Schema (s5_validation__arm{arm}.jsonl)

**Status:** Canonical  
**Version:** 1.1  
**Frozen:** No  
**Supersedes:** None (initial version)  
**Applies to:** `2_Data/metadata/generated/<RUN_TAG>/s5_validation__arm{arm}.jsonl`  
**Record unit:** 1 JSON object per line (NDJSON), one group per line  
**Last Updated:** 2025-12-28

---

## 0. Purpose (Normative)

This document defines the authoritative schema contract for **S5 validation output**, `s5_validation__arm{arm}.jsonl`.

Downstream consumers (S6, human rating workflow) MUST assume this schema and MUST handle missing or malformed S5 results gracefully (S5 does not block pipeline).

This schema is intentionally focused on:
- Reproducibility (`s5_snapshot_id`)
- Validation results (blocking errors, quality scores, issues)
- RAG evidence (for auditability when blocking errors are flagged)
- Model configuration (arm-independent, for reproducibility)

---

## 1. Top-Level Record Schema

Each NDJSON line is a single JSON object with the following required fields.

### 1.1 Required Fields

- `schema_version`: string, fixed value `"S5_VALIDATION_v1.0"`
- `group_id`: string, non-empty (echoed from S1)
- `arm`: string, non-empty (arm identifier: A, B, C, D, E, F)
- `validation_timestamp`: string, ISO 8601 format (e.g., `"2025-12-26T10:00:00Z"`)
- `s5_snapshot_id`: string, non-empty (format: `s5_{run_tag}_{group_id}_{arm}_{s5_model_version}_{hash}`)
- `s5_model_info`: object, see Section 2
- `s1_table_validation`: object, see Section 3
- `s2_cards_validation`: object, see Section 4

### 1.2 Optional Fields

- `warnings`: array of strings (validation warnings, non-blocking)
- `notes`: string (optional notes about validation process)

---

## 2. S5 Model Info Object

**Purpose**: Document S5 model configuration for reproducibility (arm-independent).

### 2.1 Required Fields

- `s1_table_model`: string, non-empty (e.g., `"models/gemini-2.0-pro-exp"`)
- `s1_table_thinking`: boolean (true if thinking enabled)
- `s1_table_rag_enabled`: boolean (true if RAG enabled)
- `s2_card_model`: string, non-empty (e.g., `"models/gemini-2.0-flash-exp"`)
- `s2_card_thinking`: boolean (true if thinking enabled)
- `s2_card_rag_enabled`: boolean (true if RAG enabled)

### 2.2 Example

```json
{
  "s1_table_model": "models/gemini-2.0-pro-exp",
  "s1_table_thinking": true,
  "s1_table_rag_enabled": true,
  "s2_card_model": "models/gemini-2.0-flash-exp",
  "s2_card_thinking": true,
  "s2_card_rag_enabled": true
}
```

---

## 3. S1 Table Validation Object

**Purpose**: Validation results for S1 master table.

### 3.1 Required Fields

- `blocking_error`: boolean (true if blocking error detected)
- `technical_accuracy`: number, one of `0.0`, `0.5`, `1.0`
- `educational_quality`: integer, one of `1`, `2`, `3`, `4`, `5`
- `issues`: array of issue objects (see Section 3.2)
- `rag_evidence`: array of RAG evidence objects (see Section 5, required if `blocking_error=true`)
- `table_visual_validation`: object, optional (see Section 3.1.1, present if infographic exists and evaluation enabled)

### 3.0.1 Optional Fields (Backward-Compatible)

- `table_regeneration_trigger_score`: number, optional (0-100, composite score for regeneration decision)
  - 계산: weighted average of `technical_accuracy` (50%) + `educational_quality` (50%)
  - Hard triggers (returns 30.0): `blocking_error=true` OR `technical_accuracy=0.0`
  - < 90점: Text Repair (S1R) 대상
  - 이 점수는 S2 cards의 `card_regeneration_trigger_score`와 동일한 공식 사용하여 일관성 확보
  - 참조: `3_Code/src/tools/multi_agent/score_calculator.py::calculate_s1_table_regeneration_trigger_score()`

### 3.1.1 Table Visual Validation Object Schema (Optional)

If `table_visual_validation` is present, it contains infographic evaluation results:

- `blocking_error`: boolean (true if infographic has blocking error)
- `information_clarity`: integer, one of `1`, `2`, `3`, `4`, `5` (Likert scale: clarity of information delivery)
- `anatomical_accuracy`: number, one of `0.0`, `0.5`, `1.0` (anatomical accuracy of infographic)
- `prompt_compliance`: number, one of `0.0`, `0.5`, `1.0` (compliance with S3 infographic_prompt_en requirements)
- `table_visual_consistency`: number, one of `0.0`, `0.5`, `1.0` (consistency between S1 table and infographic)
- `issues`: array of issue objects (infographic-specific issues)
- `image_path`: string, optional (path to evaluated infographic file)

**Infographic Issue Types:**
- `cluttered_layout`: layout is cluttered and hard to read
- `unclear_hierarchy`: information hierarchy is unclear
- `anatomical_error`: anatomical structure/relationship is incorrect
- `relationship_misrepresentation`: anatomical relationships are misrepresented
- `content_mismatch`: infographic content doesn't match S1 table
- `entity_missing`: entities from S1 table are missing in infographic

### 3.2 Issue Object Schema

Each issue object in `issues` array MUST include:

- `severity`: string, one of `"blocking"`, `"minor"`, `"warning"`
- `type`: string (e.g., `"factual_error"`, `"ambiguity"`, `"scope_mismatch"`, `"information_density"`)
- `description`: string, non-empty (human-readable description of issue)
- `row_index`: integer, optional (0-based index of table row, if applicable)
- `entity_name`: string, optional (entity name from table row, if applicable)
- `suggested_fix`: string, optional (suggestion for fixing issue)

#### 3.2.1 Optional Actionable Fields (Backward-Compatible)
To support repeatable prompt/schema refinement (offline), issue objects MAY include the following optional fields.
Downstream consumers MUST ignore unknown fields (see Section 8).

- `issue_code`: string, optional (stable code such as `FATAL_MEDICAL_FALSE`, `S2_MCQ_OPTIONS_INVALID`)
- `affected_stage`: string, optional, one of `"S1"`, `"S2"`, `"S3"`, `"S4"`, `"S5"`
- `confidence`: number, optional, 0.0–1.0 (validator confidence)
- `recommended_fix_target`: string, optional (e.g., `S2_SYSTEM`, `S2_USER_ENTITY`, `S5_SYSTEM`, `S5_USER_CARD`)
- `prompt_patch_hint`: string, optional (1–3 lines; actionable rule-level patch hint)
- `evidence_ref`: string, optional (reference to a `rag_evidence[].source_id` or other traceable evidence pointer)

**Normative note**: `blocking_error` at the parent object level is reserved for clinical safety-critical issues. Non-safety structural/exam-fit issues should be encoded as non-blocking `issues[]` entries.

### 3.3 Example

```json
{
  "blocking_error": false,
  "technical_accuracy": 1.0,
  "educational_quality": 4,
  "table_regeneration_trigger_score": 90.0,
  "issues": [
    {
      "severity": "minor",
      "type": "ambiguity",
      "description": "조건(소아/성인)이 명시되지 않음",
      "row_index": 3,
      "entity_name": "Entity Name"
    }
  ],
  "rag_evidence": []
}
```

---

## 4. S2 Cards Validation Object

**Purpose**: Validation results for S2 cards.

### 4.1 Required Fields

- `cards`: array of card validation objects (see Section 4.2)
- `summary`: object (see Section 4.3)

### 4.2 Card Validation Object Schema

Each card validation object in `cards` array MUST include:

- `card_id`: string, non-empty (echoed from S2)
- `card_role`: string, one of `"Q1"`, `"Q2"` (echoed from S2)
  - **Note**: `Q3` is **deprecated / not used** in the current 2-card policy (Q1/Q2 only). Legacy artifacts may still contain Q3.
- `blocking_error`: boolean (true if blocking error detected)
- `card_image_validation`: object, optional (see Section 4.2.1, present if image exists and evaluation enabled)
- `technical_accuracy`: number, one of `0.0`, `0.5`, `1.0`
- `educational_quality`: integer, one of `1`, `2`, `3`, `4`, `5`
- `difficulty`: number, one of `0.0`, `0.5`, `1.0` (optional, see Section 4.2.3 for definition)
- `issues`: array of issue objects (see Section 3.2, same schema as S1 table issues)
- `rag_evidence`: array of RAG evidence objects (see Section 5, required if `blocking_error=true`)

#### 4.2.1 Card Image Validation Object Schema (Optional)

If `card_image_validation` is present, it contains image evaluation results:

- `blocking_error`: boolean (true if image has blocking error)
- `anatomical_accuracy`: number, one of `0.0`, `0.5`, `1.0` (anatomical accuracy of image)
- `prompt_compliance`: number, one of `0.0`, `0.5`, `1.0` (compliance with S3 prompt_en requirements)
- `text_image_consistency`: number, one of `0.0`, `0.5`, `1.0` (consistency between card text and image)
- `image_quality`: integer, one of `1`, `2`, `3`, `4`, `5` (Likert scale: resolution, readability, artifacts)
- `safety_flag`: boolean (true if inappropriate content or patient identifiers detected)
- `issues`: array of issue objects (image-specific issues)
- `image_path`: string, optional (path to evaluated image file)
- `image_regeneration_trigger_score`: number, optional (0-100, composite score for regeneration decision)
- `prompt_patch_hints`: array of strings, optional (positive instructions for image regeneration)

**Positive Regen Fields (Option C Image Regeneration, 구현 완료 2026-01-05):**
- `image_regeneration_trigger_score`: 이미지 재생성 트리거 점수 (기본 threshold: 90점)
  - 계산: weighted average of `anatomical_accuracy`, `prompt_compliance`, `text_image_consistency`, `image_quality`
  - < 90점: Positive Regen 대상
- `prompt_patch_hints`: S5가 제안한 이미지 개선사항 (1-3개 문장)
  - 예: "Ensure the MRI slice shows clear T2-weighted hyperintensity in the right frontal lobe."
  - S3 원본 `prompt_en`에 delta로 추가하여 S4 재호출
  - 참조: `S5_Positive_Regen_Procedure.md`

**Image Issue Types:**
- `anatomical_error`: anatomical structure is incorrect
- `landmark_missing`: required anatomical landmark is missing
- `laterality_error`: laterality (L/R/Midline) is incorrect or unclear
- `modality_mismatch`: image modality doesn't match S3 prompt requirement
- `view_mismatch`: image view/sequence doesn't match S3 prompt requirement
- `key_finding_missing`: key finding from S3 prompt is not visible in image
- `diagnosis_mismatch`: image contradicts card diagnosis
- `finding_contradiction`: image finding contradicts card text
- `low_resolution`: image resolution is too low
- `artifacts`: image contains artifacts that affect interpretation
- `poor_contrast`: image contrast is insufficient
- `inappropriate_content`: image contains inappropriate content
- `patient_identifier`: image may contain patient-identifying information

#### 4.2.2 Anki MCQ Convention (Normative)
For MCQ cards, multiple-choice options are stored in structured fields (e.g., `options[]`, `correct_index`) in the S2 artifacts and may not appear verbatim in `front`.

S5 validators SHOULD evaluate MCQ integrity using the structured fields when available, and MUST NOT treat "options missing in front text" as a blocking error if options exist in the structured fields.

#### 4.2.3 Difficulty Metric (Optional)
The `difficulty` field evaluates whether the card's difficulty level is appropriate for specialist-level radiology board examination.

**Scoring Scale**:
- `1.0`: Appropriate difficulty for specialist-level board exam. Requires image interpretation and clinical reasoning.
- `0.5`: Slightly too easy or slightly too difficult, but still acceptable. Minor adjustments needed.
- `0.0`: Inappropriate difficulty: Too easy (can be solved without image or with excessive hints) OR too difficult (requires subspecialty-level knowledge).

**Common Issues**:
- **Too Easy (0.0)**: Card can be solved without looking at the image (text description gives away the answer), front text contains excessive hints, or card tests only terminology recall.
- **Too Difficult (0.0)**: Requires subspecialty-level knowledge or research-level knowledge beyond general radiology specialist scope.

**For Q1/Q2 (2-card policy; IMAGE_ON_BACK)**:
- Cards are **text-first**: the Front should be solvable from text alone (no deictic image references).
- Difficulty evaluates **exam-appropriateness** under this constraint:
  - Too easy (0.0): the stem gives away the diagnosis/answer with excessive hints or trivial recall.
  - Too difficult (0.0): requires subspecialty/research-level knowledge beyond general radiology specialist scope.
  - Acceptable (0.5/1.0): board-appropriate reasoning is required, without being solved by a single giveaway phrase.

**Note**: Q3/NO_IMAGE is deprecated in the current pipeline.

See `QA_Metric_Definitions.md` Section 5 for detailed definition.

---

## 5. Issue Code Starter Set (Non-Normative, Recommended)
This section provides a recommended initial `issue_code` set. Codes may evolve during development, but SHOULD be stabilized (frozen) before formal evaluation runs.

### 5.1 Clinical Safety (FATAL_*)
- `FATAL_MEDICAL_FALSE`: medically false claim with safety risk
- `FATAL_ANSWER_INCONSISTENT`: answer/explanation contradicts the stem or correct option
- `FATAL_MULTIPLE_CORRECT`: more than one option plausibly correct / no single best answer
- `FATAL_UNSOLVABLE`: missing key information makes item not solvable as stated

### 5.2 MCQ Structural Integrity (S2_MCQ_*)
- `S2_MCQ_OPTIONS_INVALID`: missing/incorrect number of options (must be 5)
- `S2_MCQ_CORRECT_INDEX_INVALID`: correct_index missing or out of range
- `S2_MCQ_RATIONALE_MISMATCH`: rationale supports a different option than correct_index

### 5.3 Entity Type Alignment (S2_ENTITY_*)
- `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH`: exam_focus value does not match entity type requirements
  - Example: Sign entity using `exam_focus="diagnosis"` instead of `"pattern"` or `"sign"`
  - Example: QC entity using `exam_focus="diagnosis"` instead of `"procedure"`, `"measurement"`, or `"principle"`
  - Example: Overview entity using `exam_focus="diagnosis"` instead of `"concept"` or `"classification"`
  - **Entity Type → exam_focus Mappings**:
    - `disease`: `["diagnosis"]`
    - `sign`: `["pattern", "sign"]`
    - `overview`: `["concept", "classification"]`
    - `qc`: `["procedure", "measurement", "principle"]`
    - `equipment`: `["procedure", "principle", "operation"]`
    - `comparison`: `["diagnosis"]` (but frame as differential diagnosis)
  - **Note**: Only applies to Q1 cards. Q2 cards always use `exam_focus="concept"` (or `"management"`/`"mechanism"`).

### 5.4 Validator Consistency (S5_*)
- `S5_INCONSISTENT_OUTPUT`: internal inconsistency (e.g., blocking_error and technical_accuracy mismatch)

### 4.3 Summary Object Schema

The `summary` object MUST include:

- `total_cards`: integer, >= 0 (total number of cards validated)
- `blocking_errors`: integer, >= 0 (number of cards with blocking errors)
- `mean_technical_accuracy`: number, 0.0 to 1.0 (mean technical accuracy across all cards)
- `mean_educational_quality`: number, 1.0 to 5.0 (mean educational quality across all cards)

### 4.4 Example

```json
{
  "cards": [
    {
      "card_id": "G0123__E01__C01",
      "card_role": "Q1",
      "blocking_error": false,
      "technical_accuracy": 1.0,
      "educational_quality": 4,
      "issues": [],
      "rag_evidence": []
    },
    {
      "card_id": "G0123__E01__C02",
      "card_role": "Q2",
      "blocking_error": true,
      "technical_accuracy": 0.0,
      "educational_quality": 2,
      "issues": [
        {
          "severity": "blocking",
          "type": "factual_error",
          "description": "MRI DWI 고신호를 T2 shine-through로 오해 → 진단 오류 위험",
          "suggested_fix": "DWI 고신호는 acute infarction을 의미하며, T2 shine-through와 구분 필요"
        }
      ],
      "rag_evidence": [
        {
          "source_id": "rag_doc_001",
          "source_excerpt": "DWI high signal indicates acute infarction, not T2 shine-through...",
          "relevance": "high"
        }
      ]
    }
  ],
  "summary": {
    "total_cards": 12,
    "blocking_errors": 1,
    "mean_technical_accuracy": 0.92,
    "mean_educational_quality": 3.8
  }
}
```

---

## 6. RAG Evidence Object Schema

**Purpose**: Provide RAG source citations when S5 flags blocking errors (for auditability).

### 5.1 When Required

RAG evidence MUST be provided when:

- `blocking_error=true` in S1 table validation OR
- `blocking_error=true` in any S2 card validation

### 5.2 Required Fields

- `source_id`: string, non-empty (RAG document identifier)
- `source_excerpt`: string, non-empty, max 500 chars (relevant excerpt from RAG source)
- `relevance`: string, one of `"high"`, `"medium"`, `"low"`

### 5.3 Example

```json
{
  "source_id": "rag_doc_001",
  "source_excerpt": "DWI high signal indicates acute infarction, not T2 shine-through. T2 shine-through occurs when T2-weighted hyperintensity is visible on DWI, but ADC map shows no restriction.",
  "relevance": "high"
}
```

---

## 7. S5 Snapshot ID Format

**Purpose**: Ensure reproducibility and version tracking.

### 6.1 Format

```
s5_{run_tag}_{group_id}_{arm}_{s5_model_version}_{hash}
```

### 6.2 Components

- `run_tag`: RUN_TAG from pipeline execution
- `group_id`: Group identifier (echoed from S1)
- `arm`: Arm identifier (A, B, C, D, E, F)
- `s5_model_version`: S5 model version string (e.g., `"gemini-2.0-pro-exp_v1"`)
- `hash`: SHA256 hash (first 12 hex characters) of (S5 validation result JSON + model config)

### 6.3 Example

```
s5_TEST_20251226_G0123_A_gemini-2.0-pro-exp_v1_abc123def456
```

### 6.4 Generation

S5 snapshot ID MUST be generated deterministically from:
- S5 validation result (JSON string, sorted keys)
- S5 model configuration (from `s5_model_info`)

---

## 8. Complete Example

```json
{
  "schema_version": "S5_VALIDATION_v1.0",
  "group_id": "G0123",
  "arm": "A",
  "validation_timestamp": "2025-12-26T10:00:00Z",
  "s5_snapshot_id": "s5_TEST_20251226_G0123_A_gemini-2.0-pro-exp_v1_abc123def456",
  "s5_model_info": {
    "s1_table_model": "models/gemini-2.0-pro-exp",
    "s1_table_thinking": true,
    "s1_table_rag_enabled": true,
    "s2_card_model": "models/gemini-2.0-flash-exp",
    "s2_card_thinking": true,
    "s2_card_rag_enabled": true
  },
  "s1_table_validation": {
    "blocking_error": false,
    "technical_accuracy": 1.0,
    "educational_quality": 4,
    "table_regeneration_trigger_score": 90.0,
    "issues": [
      {
        "severity": "minor",
        "type": "ambiguity",
        "description": "조건(소아/성인)이 명시되지 않음",
        "row_index": 3,
        "entity_name": "Entity Name"
      }
    ],
    "rag_evidence": []
  },
  "s2_cards_validation": {
    "cards": [
      {
        "card_id": "G0123__E01__C01",
        "card_role": "Q1",
        "blocking_error": false,
        "technical_accuracy": 1.0,
        "educational_quality": 4,
        "issues": [],
        "rag_evidence": []
      },
      {
        "card_id": "G0123__E01__C02",
        "card_role": "Q2",
        "blocking_error": true,
        "technical_accuracy": 0.0,
        "educational_quality": 2,
        "issues": [
          {
            "severity": "blocking",
            "type": "factual_error",
            "description": "MRI DWI 고신호를 T2 shine-through로 오해 → 진단 오류 위험",
            "suggested_fix": "DWI 고신호는 acute infarction을 의미하며, T2 shine-through와 구분 필요"
          }
        ],
        "rag_evidence": [
          {
            "source_id": "rag_doc_001",
            "source_excerpt": "DWI high signal indicates acute infarction, not T2 shine-through...",
            "relevance": "high"
          }
        ]
      }
    ],
    "summary": {
      "total_cards": 12,
      "blocking_errors": 1,
      "mean_technical_accuracy": 0.92,
      "mean_educational_quality": 3.8
    }
  }
}
```

---

## 9. Schema Versioning Policy

### 8.1 Version Bumping

Schema version MUST be bumped when:

- Adding new required fields
- Removing required fields
- Changing field types
- Changing field semantics

### 8.2 Backward Compatibility

- Adding optional fields does NOT require version bump
- Changing optional field semantics requires version bump
- Consumers MUST handle unknown fields gracefully

### 8.3 Migration

When schema version is bumped:

- Old schema version MUST remain valid for existing data
- New schema version MUST be documented with migration guide
- Code MUST handle both old and new schema versions during transition

---

## 10. Fail-Fast Conditions (Validator MUST NOT FAIL)

**Note**: S5 does NOT fail-fast. S5 validation errors are logged but do not stop the pipeline.

However, S5 output SHOULD be validated for:

- Schema conformance (warn if invalid, but continue)
- Required fields presence (warn if missing, but continue)
- Type correctness (warn if wrong type, but continue)

---

## 11. Related Documents

- `S5_Validation_Contract_Canonical.md`: S5 role and contract definition
- `Human_Rating_Schema_Canonical.md`: Human rating schema (2-pass workflow)
- `S1_Stage1_Struct_JSON_Schema_Canonical.md`: S1 input schema
- `S2_Contract_and_Schema_Canonical.md`: S2 input schema

---

## 12. Version History

- **v1.0** (2025-12-26): Initial canonical schema definition
- **v1.1** (2025-12-28): Added optional actionable issue fields; clarified Anki MCQ convention and blocking semantics (no schema_version bump; backward-compatible)
- **v1.2** (2026-01-06): Added `table_regeneration_trigger_score` to S1 table validation (optional field; backward-compatible)

---

**Document Status**: Canonical  
**Last Updated**: 2026-01-06  
**Owner**: MeducAI Research Team

