# MeducAI Human Rating Schema (2-Pass Workflow) (Canonical)

**Status:** Canonical  
**Version:** 1.2  
**Frozen:** No  
**Supersedes:** None (initial version)  
**Applies to:** `2_Data/metadata/generated/<RUN_TAG>/human_ratings__arm{arm}.jsonl`  
**Record unit:** 1 JSON object per line (NDJSON), one card rating per line  
**Last Updated:** 2025-12-29

---

## 0. Purpose (Normative)

This document defines the authoritative schema contract for **human ratings** collected via the **2-pass workflow** (Pre-S5 → S5 Reveal → Post-S5).

This schema is designed to:

- Preserve **endpoint purity**: Pre-S5 ratings (primary endpoint) are immutable and uncontaminated by S5 results
- Enable **tool effect measurement**: Post-S5 ratings (secondary endpoint) measure S5 tool effect
- Support **change tracking**: Change log records all modifications with reason codes
- Ensure **reproducibility**: S5 snapshot ID links ratings to exact S5 validation version

---

## 1. Top-Level Record Schema

Each NDJSON line is a single JSON object with the following required fields.

### 1.1 Required Fields

- `schema_version`: string, fixed value `"HUMAN_RATING_v1.0"`
- `card_id`: string, non-empty (card identifier, e.g., `"G0123__E01__C01"`)
- `group_id`: string, non-empty (group identifier, echoed from S1)
- `arm`: string, non-empty (arm identifier: A, B, C, D, E, F)
- `arm_blinded_code`: string, non-empty (blinded arm code for human raters, e.g., `"X3"`)
- `run_tag`: string, non-empty (RUN_TAG from pipeline execution)
- `rater_id`: string, non-empty (rater identifier, pseudonymized)
- `rater_role`: string, one of `"resident"`, `"attending"`
- `session_id`: string, non-empty (session identifier for this rating)
- `pre_s5_rating`: object, see Section 2 (immutable after lock)
- `s5_reveal`: object, see Section 3 (S5 reveal metadata)
- `post_s5_rating`: object, see Section 4 (editable, may differ from Pre-S5)
- `change_log`: array of change log objects, see Section 5 (required if Post-S5 differs from Pre-S5)
- `metadata`: object, see Section 6

### 1.2 Optional Fields

- `notes`: string (optional notes about rating process)
- `final_gate`: object (optional, FINAL gate QA assignment and adjudication audit metadata), see Section 6.4
- `multiagent_eval`: object (optional, multi-agent evaluation metadata for the 3-pass subset), see Section 6.5

---

## 2. Pre-S5 Rating Object

**Purpose**: Primary endpoint for arm comparison (immutable after lock).

### 2.1 Required Fields

- `blocking_error`: boolean (true if blocking error detected)
- `technical_accuracy`: number, one of `0.0`, `0.5`, `1.0` (required for FINAL, matches S5 evaluation scale)
- `overall_quality`: integer, one of `1`, `2`, `3`, `4`, `5` (Likert scale)
- `timestamp_submitted_ms`: integer, >= 0 (Unix timestamp in milliseconds when Pre-S5 submitted)
- `time_pre_ms`: integer, >= 0 (time from card view to Pre-S5 submission, milliseconds)

### 2.2 Optional Fields

- `evidence_comment`: string (required if `blocking_error=true` OR `overall_quality<=2`, otherwise optional)
- `image_blocking_error`: boolean (optional, true if image has a blocking error that makes the item unsafe or unanswerable)
- `flag_blocking_suspicion`: boolean (optional, true if rater suspects a blocking issue and requests adjudication, even if `major_error=false`)
- `major_error`: boolean (optional, may be stored for convenience, but can be deterministically derived, see Section 8.3)

### 2.3 Immutability

**Critical Constraint**: Pre-S5 rating fields are **immutable** after `timestamp_submitted_ms` is set.

- Database constraint prevents Pre-S5 field updates after lock
- UI prevents Pre-S5 field editing after submit
- Pre-S5 ratings are **final** for primary endpoint analysis

### 2.4 Example

```json
{
  "blocking_error": false,
  "technical_accuracy": 1.0,
  "overall_quality": 3,
  "evidence_comment": null,
  "timestamp_submitted_ms": 1703587200000,
  "time_pre_ms": 45000
}
```

---

## 3. S5 Reveal Object

**Purpose**: Metadata about S5 results reveal (for reproducibility and auditability).

### 3.1 Required Fields

- `s5_snapshot_id`: string, non-empty (S5 snapshot ID from S5 validation result)
- `timestamp_revealed_ms`: integer, >= 0 (Unix timestamp in milliseconds when S5 revealed)

### 3.2 Gating

S5 reveal MUST occur **after** Pre-S5 submission is locked:

- `timestamp_revealed_ms` MUST be >= `pre_s5_rating.timestamp_submitted_ms`
- Backend API verifies Pre-S5 lock exists before returning S5 results
- Frontend disables S5 reveal button until Pre-S5 submitted

### 3.3 Example

```json
{
  "s5_snapshot_id": "s5_TEST_20251226_G0123_A_gemini-2.0-pro-exp_v1_abc123def456",
  "timestamp_revealed_ms": 1703587250000
}
```

---

## 4. Post-S5 Rating Object

**Purpose**: Secondary endpoint for tool effect measurement (editable, may differ from Pre-S5).

### 4.1 Required Fields

- `blocking_error`: boolean (may differ from Pre-S5)
- `technical_accuracy`: number, one of `0.0`, `0.5`, `1.0` (required for FINAL, matches S5 evaluation scale)
- `overall_quality`: integer, one of `1`, `2`, `3`, `4`, `5` (may differ from Pre-S5)
- `timestamp_submitted_ms`: integer, >= 0 (Unix timestamp in milliseconds when Post-S5 submitted)
- `correction_time_ms`: integer, >= 0 (time from S5 reveal to final submission, milliseconds)

### 4.2 Optional Fields

- `evidence_comment`: string (optional, may differ from Pre-S5)

### 4.3 Default Values

Post-S5 fields are **pre-populated** with Pre-S5 values:

- `blocking_error_post` = `blocking_error_pre` (default)
- `technical_accuracy_post` = `technical_accuracy_pre` (default)
- `overall_quality_post` = `overall_quality_pre` (default)
- `evidence_comment_post` = `evidence_comment_pre` (default)

User may edit Post-S5 fields, but most cards remain unchanged (Post-S5 = Pre-S5).

### 4.4 Example

```json
{
  "blocking_error": true,
  "technical_accuracy": 0.0,
  "overall_quality": 2,
  "evidence_comment": "S5가 지적한 DWI 고신호 오해 확인. 진단 오류 위험 있음.",
  "timestamp_submitted_ms": 1703587300000,
  "correction_time_ms": 50000
}
```

---

## 5. Change Log Array

**Purpose**: Track all changes from Pre-S5 to Post-S5 with reason codes (for analysis and auditability).

### 5.1 When Required

Change log is **required** if **any** Post-S5 field differs from Pre-S5:

- If `blocking_error_post != blocking_error_pre` → change log required
- If `technical_accuracy_post != technical_accuracy_pre` → change log required
- If `overall_quality_post != overall_quality_pre` → change log required
- If `evidence_comment_post != evidence_comment_pre` → change log required
- If **no** fields differ → change log array is empty (no change log entry needed)

### 5.2 Change Log Object Schema

Each change log object MUST include:

- `field_changed`: string, one of `"blocking_error"`, `"overall_quality"`, `"evidence_comment"`, `"technical_accuracy"`
- `old_value`: any (Pre-S5 value)
- `new_value`: any (Post-S5 value)
- `reason_code`: string, one of the enum values (see Section 5.3)
- `change_note`: string, non-empty, max 200 chars (1-line explanation)
- `timestamp_ms`: integer, >= 0 (Unix timestamp in milliseconds, typically same as `post_s5_rating.timestamp_submitted_ms`)

### 5.3 Change Reason Codes (Enum)

```python
CHANGE_REASON_CODES = {
    "S5_BLOCKING_FLAG": "S5 flagged blocking error; confirmed after review",
    "S5_BLOCKING_FALSE_POS": "S5 flagged blocking error; determined to be false positive",
    "S5_QUALITY_INSIGHT": "S5 quality assessment provided useful insight",
    "S5_EVIDENCE_HELPED": "S5 evidence/suggestion helped identify issue",
    "S5_NO_EFFECT": "S5 results reviewed but no change needed",
    "RATER_REVISION": "Rater reconsidered without S5 influence (rare)",
    "OTHER": "Other reason (specify in note)"
}
```

**Special Case**: If `blocking_error` changes from `No→Yes` or `Yes→No`, `reason_code` is **mandatory** and must include explanation.

### 5.4 Example

```json
[
  {
    "field_changed": "blocking_error",
    "old_value": false,
    "new_value": true,
    "reason_code": "S5_BLOCKING_FLAG",
    "change_note": "S5 flagged blocking error; confirmed after review of RAG evidence",
    "timestamp_ms": 1703587300000
  },
  {
    "field_changed": "overall_quality",
    "old_value": 3,
    "new_value": 2,
    "reason_code": "S5_QUALITY_INSIGHT",
    "change_note": "S5 quality assessment (2) aligned with revised blocking error assessment",
    "timestamp_ms": 1703587300000
  }
]
```

---

## 6. Metadata Object

**Purpose**: Additional metadata about rating session.

### 6.1 Required Fields

- `ui_version`: string, non-empty (UI version identifier)
- `device_type`: string, one of `"web"`, `"tablet"`, `"mobile"`
- `total_session_duration_ms`: integer, >= 0 (total time from card view to final submission, milliseconds)

### 6.2 Optional Fields

- `browser_info`: string (browser user agent, if available)
- `screen_resolution`: string (screen resolution, if available)

### 6.4 FINAL gate metadata (optional)

`final_gate` is optional and is used when this rating record participates in the FINAL gate QA design (dual resident screening, attending adjudication, and attending audit).

Recommended fields:

- `sample_type`: string, one of `"resident_double_900"`, `"attending_adjudication"`, `"attending_audit_300"`
- `seed`: integer (the protocol seed used for sampling, for example, 20260101)
- `stratum`: object (optional, echo of sampling keys), may include `subspecialty`, `item_type`, `image_type`
- `linked_record_ids`: array of strings (optional, record IDs of paired resident ratings, or the adjudication target ratings)

### 6.5 Multi-agent evaluation metadata (optional)

`multiagent_eval` is optional and is used only for the pre-specified multi-agent evaluation subset, to support the 3-pass evaluation layer without contaminating the primary endpoints.

Recommended fields:

- `subset_member`: boolean
- `pass_id`: integer, one of 1, 2, 3
- `repair_applied`: boolean
- `repair_snapshot_id`: string (optional, identifier for repaired artifact snapshot if applicable)

### 6.3 Example

```json
{
  "ui_version": "v1.0",
  "device_type": "web",
  "total_session_duration_ms": 100000
}
```

---

## 7. Complete Example

```json
{
  "schema_version": "HUMAN_RATING_v1.0",
  "card_id": "G0123__E01__C02",
  "group_id": "G0123",
  "arm": "A",
  "arm_blinded_code": "X3",
  "run_tag": "FINAL_20251226",
  "rater_id": "R001",
  "rater_role": "resident",
  "session_id": "session_abc123",
  "pre_s5_rating": {
    "blocking_error": false,
    "technical_accuracy": 1.0,
    "overall_quality": 3,
    "evidence_comment": null,
    "timestamp_submitted_ms": 1703587200000,
    "time_pre_ms": 45000
  },
  "s5_reveal": {
    "s5_snapshot_id": "s5_TEST_20251226_G0123_A_gemini-2.0-pro-exp_v1_abc123def456",
    "timestamp_revealed_ms": 1703587250000
  },
  "post_s5_rating": {
    "blocking_error": true,
    "technical_accuracy": 0.0,
    "overall_quality": 2,
    "evidence_comment": "S5가 지적한 DWI 고신호 오해 확인. 진단 오류 위험 있음.",
    "timestamp_submitted_ms": 1703587300000,
    "correction_time_ms": 50000
  },
  "change_log": [
    {
      "field_changed": "blocking_error",
      "old_value": false,
      "new_value": true,
      "reason_code": "S5_BLOCKING_FLAG",
      "change_note": "S5 flagged blocking error; confirmed after review of RAG evidence",
      "timestamp_ms": 1703587300000
    },
    {
      "field_changed": "overall_quality",
      "old_value": 3,
      "new_value": 2,
      "reason_code": "S5_QUALITY_INSIGHT",
      "change_note": "S5 quality assessment (2) aligned with revised blocking error assessment",
      "timestamp_ms": 1703587300000
    }
  ],
  "metadata": {
    "ui_version": "v1.0",
    "device_type": "web",
    "total_session_duration_ms": 100000
  }
}
```

---

## 8. Endpoint Usage

### 8.1 Primary Endpoint (Arm Comparison)

**Use Pre-S5 ratings only**:

- `pre_s5_rating.blocking_error` → Blocking Error Rate (BER_pre)
- `pre_s5_rating.technical_accuracy` → Technical Accuracy Mean (TAM_pre)
- `pre_s5_rating.overall_quality` → Overall Card Quality (GCR_pre)

**Critical Constraint**: Post-S5 ratings MUST NOT be used for arm comparison.

### 8.2 Secondary Endpoint (Tool Effect)

**Use Post-S5 ratings and change log**:

- `post_s5_rating.blocking_error - pre_s5_rating.blocking_error` → BER_delta
- `post_s5_rating.technical_accuracy - pre_s5_rating.technical_accuracy` → TAM_delta
- `post_s5_rating.overall_quality - pre_s5_rating.overall_quality` → GCR_delta
- `post_s5_rating.correction_time_ms` → Correction Time (CT_post)
- `change_log` → Change reason analysis

### 8.3 FINAL gate primary endpoint, major_error (attending anchored)

For FINAL gate assurance, the primary endpoint is binary `major_error` at the item level. `major_error` can be deterministically derived from Pre fields:

- `major_error` equals true if any of the following are true:
  - `pre_s5_rating.blocking_error` equals true
  - `pre_s5_rating.technical_accuracy` equals 0.0
  - `pre_s5_rating.image_blocking_error` equals true

FINAL gate decision logic:

- For items with attending adjudication, the attending label for `major_error` is used as the final label for assurance.
- For items in the attending audit sample, the attending label is used to compute audit false negatives among resident consensus-safe items.
- Post-S5 ratings and multi-agent evaluation passes are not used for FINAL gate endpoint purity.

---

## 9. Validation Rules

### 9.1 Pre-S5 Validation

- `blocking_error`, `technical_accuracy`, and `overall_quality` are **required**
- `evidence_comment` is **required** if `blocking_error=true` OR `overall_quality<=2`
- `timestamp_submitted_ms` MUST be set when Pre-S5 is submitted

### 9.2 S5 Reveal Validation

- `s5_snapshot_id` MUST match an existing S5 validation result
- `timestamp_revealed_ms` MUST be >= `pre_s5_rating.timestamp_submitted_ms`

### 9.3 Post-S5 Validation

- `blocking_error`, `technical_accuracy`, and `overall_quality` are **required**
- `correction_time_ms` MUST be >= 0
- If **any** Post-S5 field differs from Pre-S5, `change_log` is **required**
- If `change_log` is non-empty, each entry MUST have `reason_code` and `change_note`

---

## 10. Schema Versioning Policy

### 10.1 Version Bumping

Schema version MUST be bumped when:

- Adding new required fields
- Removing required fields
- Changing field types
- Changing field semantics

### 10.2 Backward Compatibility

- Adding optional fields does NOT require version bump
- Changing optional field semantics requires version bump
- Consumers MUST handle unknown fields gracefully

---

## 11. Related Documents

- `S5_Validation_Contract_Canonical.md`: S5 role and contract definition
- `S5_Validation_Schema_Canonical.md`: S5 validation result schema
- `FINAL_QA_Form_Design.md`: FINAL QA form design (2-pass workflow)
- `S5_Validation_Plan_OptionB_Canonical.md`: Detailed implementation plan
- `QA_Metric_Definitions.md`: Technical Accuracy and Educational Quality metric definitions
- `Multiagent_Evaluation_Workflow_Design.md`: Future 3-pass workflow for multiagent evaluation (when multiagent system is implemented)

---

## 12. Future Extensibility

This schema supports the current 2-pass workflow (Pre-S5 → S5 Reveal → Post-S5). When the multiagent repair system (S5R/S1R/S2R) is implemented, a separate 3-pass workflow may be introduced for evaluating multiagent repair results. See `Multiagent_Evaluation_Workflow_Design.md` for the future workflow design. The current 2-pass workflow remains the canonical workflow for arm comparison analysis.

---

## 13. Version History

- **v1.0** (2025-12-26): Initial canonical schema definition
- **v1.1** (2025-12-29): Technical Accuracy field changed from optional to required (aligned with QA_Metric_Definitions.md and S5_vs_FINAL_QA_Alignment_Analysis.md recommendations)
- **v1.2** (2025-12-29): Added optional FINAL gate and multi-agent evaluation metadata fields, plus optional image_blocking_error and major_error fields, while preserving Pre rating immutability for primary endpoints.

---

**Document Status**: Canonical  
**Last Updated**: 2025-12-29  
**Owner**: MeducAI Research Team

