# FINAL QA Form Design (2-Pass Workflow)

**Status:** Canonical  
**Version:** 1.4  
**Frozen:** No  
**Applies to:** FINAL QA evaluation phase  
**Last Updated:** 2025-12-29  
**Change Log**: 
- v1.2 - FINAL QA는 Q1(단답형 주관식)과 Q2(MCQ)만 평가하며, 둘 다 이미지가 BACK에 배치됨. Q3은 평가하지 않음.
- v1.3 - Q3은 S0(QA 실험)에서만 사용되었으며, FINAL 모드에서는 S2가 Q1과 Q2만 생성함을 명확히 함.
- v1.4 - FINAL gate QA 설계 확정 반영, major_error 정의, n=900 resident 2-rater, n=300 attending audit, adjudication 및 escalation 규칙, multi-agent evaluation 통합을 추가함.

---

## 0. Purpose (Normative)

This document defines the **FINAL QA form design** for the 2-pass human rating workflow that preserves clean endpoints for arm comparison.

The form implements:

- **Pre-S5 Pass**: Human rates content before seeing S5 results (primary endpoint)
- **S5 Reveal**: S5 validation results revealed after Pre-S5 lock
- **Post-S5 Pass**: Human may correct ratings with mandatory change logging (secondary endpoint)

**Critical Design Principle**: Pre-S5 ratings are **immutable** and used for all arm comparison analyses. Post-S5 ratings measure tool effect, not arm performance.

---

## 0.1 Design Summary (Coauthors, Publication, IRB)

This section pre-specifies the FINAL QA (gate) design for the finalized pool.

### 0.1.1 Protocol decisions (must be reflected verbatim)

- FINAL pool size: >= 6,000 items (each “item” = 1 question/card).
- Primary safety/quality outcome is an “error rate (%)” defined on MAJOR errors (binary yes/no).
- Attending (specialist) audit sample is FIXED at n=300 (stratified random sampling).
- Residents will do dual independent ratings on n=900 items (total 1,800 resident-ratings).
- Disagreements or “flagged/blocking suspicion” cases get attending adjudication.
- Additionally, attending reviews n=300 random audit items drawn from the resident “consensus-safe” pool to quantify residual FN risk and provide statistical assurance.
- Multi-agent repair evaluation is running in parallel; it must be integrated without contaminating the primary endpoints.
- Pre-specify escalation rules if audit indicates residents are unreliable (“if residents were often wrong, what then?”).

### 0.1.2 Primary endpoint and estimand, FINAL gate

- Primary endpoint is binary `major_error` at the item level.
- Primary reporting quantity is the major error rate, error rate (%), computed as `mean(major_error)` times 100.
- Pre-S5 ratings are immutable once submitted. The FINAL gate analyses and assurance statements use immutable Pre values only.

### 0.1.3 Major error variable (deterministic rule)

Define `major_error` for the FINAL gate as follows.

- `major_error` equals TRUE if any of the following are TRUE.
  - `blocking_error` equals Yes in the human form.
  - `technical_accuracy` equals 0.0 in the human form.
  - `image_blocking_error` equals Yes, for example, modality mismatch, anatomy grossly wrong, or image makes learning goal unattainable.
- `major_error` equals FALSE otherwise.

This definition is pre-specified before data collection. Claims about error rate (%) must use `major_error`. Other graded scales, including 0.0, 0.5, 1.0 and 1 to 5 Likert, are collected as secondary descriptors.

---

## 0.2 Sampling and workflow, FINAL gate QA (human)

### 0.2.1 Resident dual independent rating, fixed n equals 900 items

- Two residents independently rate each of the same 900 items.
- Each resident submits immutable Pre ratings for the assigned items.
- These immutable Pre ratings define resident-level `major_error` for screening and agreement checks.

### 0.2.2 Attending adjudication set

An item is added to the attending adjudication queue if any of the following holds.

- Residents disagree on `major_error`.
- Either resident marks flagged or blocking suspicion.

Attending adjudication produces an item-level adjudicated `major_error` label for those items. For FINAL gate assurance, adjudicated labels supersede resident labels on adjudicated items.

### 0.2.3 Attending audit set, fixed n equals 300 items

- The audit frame is the resident consensus-safe pool, items where both residents have `major_error` equals FALSE.
- Draw an attending audit sample of n equals 300 items by stratified random sampling from the consensus-safe pool.
- Stratify across 11 subspecialties, plus optional item type (Q1, Q2) and image type (illustration, infographic, equipment) as feasible.

### 0.2.4 Statistical assurance statement (pre-specified interpretation)

The attending audit is used to estimate and upper-bound the residual major error rate within the resident consensus-safe pool, and to monitor resident false negative risk. The protocol uses assurance language and upper confidence bound language. It does not claim proof of zero errors.

---

## 0.3 Sampling and escalation rules (pre-specified, deterministic)

### 0.3.1 Deterministic sampling specification

- Input manifest: a CSV or JSONL listing all eligible FINAL items, pool size at least 6,000, with fields:
  - `item_id` or `card_id`
  - `subspecialty`
  - `item_type` (Q1, Q2)
  - `image_type` (illustration, infographic, equipment, or none)
  - `run_tag` and `arm`
  - `repair_applied` (boolean)
- Random seed fixed in protocol: `SEED=20260101`.
- Outputs:
  - `resident_double_sample_900.csv`
  - `attending_audit_sample_300.csv`
  - `attending_adjudication_queue.csv`, generated after resident submissions.

### 0.3.2 Audit false negative counter

Define:

- `FN_audit` equals the count of items in the attending audit sample where residents were consensus-safe, both residents have `major_error` equals FALSE, but the attending finds `major_error` equals TRUE.

### 0.3.3 Escalation actions based on FN_audit (pre-committed)

The following rule set is pre-committed before data collection.

- If `FN_audit` is less than or equal to 2: proceed, correct identified items, keep the current workflow.
- If `FN_audit` is between 3 and 5 inclusive: trigger enhanced audit by adding plus 300 audit items, total 600, and perform mandatory resident recalibration, short training plus rubric review.
- If `FN_audit` is greater than or equal to 6: declare resident screening unreliable, switch to an expanded attending review plan, for example, attending review of all items in affected strata plus additional audit until false negative risk is controlled.

All escalation actions, strata definitions, and additional sampling runs must use the same seed and deterministic sampling script, and must be logged as protocol-defined actions, not post-hoc choices.

---

## 0.4 Multi-agent evaluation integration (parallel, non-contaminating)

Multi-agent repair evaluation runs in parallel as a tool-effect study layer. It must not alter the FINAL gate primary endpoint or gate conclusions.

### 0.4.1 Subset selection and separation from FINAL gate

- Multi-agent evaluation is run only on a defined subset with an explicit sampling frame and fixed seed.
- The subset should include all items with `repair_applied` equals TRUE, plus stratified random fill to a fixed total as feasible, without changing the resident n equals 900 requirement.

### 0.4.2 Three-pass workflow summary (subset only)

- Pass 1, Pre-Multiagent: This is the primary endpoint pass for tool-effect comparisons. Raters are blinded to multi-agent outputs and S5 outputs. Pass 1 values are immutable once submitted.
- Pass 2, Reveal: Multi-agent diffs plus an S5 snapshot are revealed for reference only.
- Pass 3, Post-Multiagent: Raters record whether the repair is accepted and whether quality improved or degraded. These measures are secondary tool-effect outcomes.

FINAL gate quality assurance conclusions are anchored on attending audit and attending adjudication. They are not based on the multi-agent system self-reported checks.

---

## 0.5 Implementation checklist (FINAL gate)

### 0.5.1 Required data fields, minimum

- Item manifest fields: `item_id` or `card_id`, `subspecialty`, `item_type`, `image_type`, `run_tag`, `arm`, `repair_applied`.
- Resident fields, immutable Pre: `blocking_error_pre`, `technical_accuracy_pre`, `image_blocking_error_pre`, plus `major_error_pre` derived or stored, plus `flag_blocking_suspicion_pre`.
- Attending fields: adjudication or audit assignment flag, and an attending `major_error` label derived or stored.
- Audit bookkeeping: `sample_type`, `seed`, `stratum`, and an `FN_audit` computation output.

### 0.5.2 Sampling scripts and reproducible outputs

- Deterministic sampling script that reads the manifest and writes:
  - `resident_double_sample_900.csv`
  - `attending_audit_sample_300.csv`
- Deterministic post-submission script that writes:
  - `attending_adjudication_queue.csv`, based on resident disagreement on `major_error` or flagged or blocking suspicion.
- Summary outputs for IRB reporting:
  - Resident agreement summary for `major_error`.
  - Audit `FN_audit`, plus a confidence bound summary for the consensus-safe pool.

---

## 1. One-Screen Layout Concept

**Design Principle**: Minimal friction, clear separation of Pre-S5 and Post-S5 phases.

### 1.1 Layout Structure

```
┌─────────────────────────────────────────────────┐
│ Card Content (Top)                              │
│ - Front / Back text                              │
│ - Card metadata (card_id, entity_name)          │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ Pre-S5 Rating Section (Initially Active)        │
│ - B1: Blocking Error (Yes/No)                   │
│ - B1.5: Technical Accuracy (0/0.5/1)            │
│ - B2: Overall Quality (1-5)                     │
│ - B3: Evidence Comment (conditional)             │
│ [Submit Pre-S5 Rating] button                   │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ S5 Results Panel (Hidden until reveal)           │
│ - S5 Blocking Error Flag (if any)               │
│ - S5 Quality Assessment                          │
│ - S5 Evidence/Suggestions                        │
│ [Reveal S5 Results] button (disabled until      │
│  Pre-S5 submitted)                               │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ Post-S5 Rating Section (Hidden until S5 reveal)  │
│ - Pre-S5 values (read-only, grayed)             │
│ - Post-S5 fields (editable, pre-filled)          │
│ - Change reason (required if changed)            │
│ [Submit Final Rating] button                    │
└─────────────────────────────────────────────────┘
```

### 1.2 Visual Design Principles

- **Clear separation**: Pre-S5, S5 reveal, and Post-S5 sections are visually distinct
- **Progressive disclosure**: S5 results and Post-S5 form appear only after Pre-S5 submission
- **Minimal scrolling**: All sections fit on one screen (or minimal scrolling)
- **Color coding**: Red for blocking errors, Yellow for warnings, Green for no issues

---

## 2. Pre-S5 Rating Fields (Exact Specification)

### 2.1 B1. Blocking Error (Required)

- **Type**: Radio button (Yes/No)
- **Label**: "Does this card contain a blocking error?"
- **Tooltip**: "Blocking error = factual error that could mislead learners or cause incorrect clinical decisions"
- **Required**: Yes
- **Default**: None (must select)
- **Field Name**: `blocking_error_pre`

### 2.2 B1.5. Technical Accuracy (Required)

- **Type**: Radio button (three options)
- **Label**: "Technical Accuracy"
- **Options**: 
  - 1.0 = Core concept and explanation are fully correct; suitable for board-level learning without revision
  - 0.5 = Core concept is correct, but explanation contains minor omissions, imprecise phrasing, or missing nuance
  - 0.0 = Core concept is incorrect, misleading, or likely to cause misunderstanding
- **Tooltip**: "Technical accuracy reflects factual correctness and clinical validity. See QA_Metric_Definitions.md for detailed definitions."
- **Required**: Yes
- **Default**: None (must select)
- **Field Name**: `technical_accuracy_pre`
- **Definition Source**: `QA_Metric_Definitions.md` Section 3 (Technical Accuracy Metric)

### 2.3 B2. Overall Card Quality (Required)

- **Type**: Likert scale (1-5)
- **Label**: "Overall Card Quality"
- **Options**: 
  - 1 = 매우 나쁨 (Very Poor)
  - 2 = 나쁨 (Poor)
  - 3 = 보통 (Average)
  - 4 = 좋음 (Good)
  - 5 = 매우 좋음 (Very Good)
- **Required**: Yes
- **Default**: None (must select)
- **Field Name**: `overall_quality_pre`

### 2.4 B3. Evidence Comment (Conditional)

- **Type**: Text area (1-line, max 200 chars)
- **Label**: "Evidence/Comment"
- **Condition**: Required if `B1=Yes` OR `B2<=2`
- **Placeholder**: "Brief explanation of issue or evidence"
- **Validation**: Must be non-empty if condition met
- **Field Name**: `evidence_comment_pre`

### 2.5 Submit Pre-S5 Rating Button

- **Label**: "Submit Pre-S5 Rating"
- **State**: Enabled when B1, B1.5, and B2 are filled (and B3 if required)
- **Action**: 
  - Validate all required fields
  - Lock Pre-S5 fields (make read-only)
  - Save Pre-S5 data to backend
  - Enable "Reveal S5 Results" button
  - Show confirmation: "Pre-S5 rating submitted. You may now reveal S5 results."
- **Visual Feedback**: Button changes to "Pre-S5 Rating Submitted" (disabled, grayed)

---

## 3. S5 Results Panel (Reveal Logic)

### 3.1 Initial State (Hidden)

- **Visibility**: Hidden/collapsed
- **Indicator**: "S5 results will be revealed after Pre-S5 submission"
- **Button**: "Reveal S5 Results" (disabled, grayed out)
- **Visual**: Collapsed panel with expand icon

### 3.2 After Pre-S5 Submission

- **Button State**: "Reveal S5 Results" (enabled)
- **Action on Click**:
  - Fetch S5 validation result from backend (using `card_id`)
  - Display S5 results panel (expand)
  - Log `s5_reveal_timestamp_ms`
  - Show Post-S5 rating section
- **Visual Feedback**: Panel expands with animation

### 3.3 S5 Results Display

#### 3.3.1 S5 Blocking Error Flag

- **If S5 flagged blocking**: 
  - Red badge: "S5: Blocking Error Detected"
  - Icon: Warning symbol
  - Prominent display (top of panel)
- **If S5 did not flag**: 
  - Green badge: "S5: No Blocking Error"
  - Icon: Checkmark
  - Subtle display

#### 3.3.2 S5 Technical Accuracy Assessment

- **Display**: "S5 Technical Accuracy: {score}" (0.0 / 0.5 / 1.0)
- **Visual**: Badge or indicator
- **Color**: Green (1.0), Yellow (0.5), Red (0.0)

#### 3.3.3 S5 Quality Assessment

- **Display**: "S5 Quality: {score}/5" (if available)
- **Visual**: Progress bar or star rating
- **Color**: Green (4-5), Yellow (3), Red (1-2)

#### 3.3.4 S5 Evidence/Suggestions

- **Display**: S5 issues list (if any)
  - Each issue: severity badge + description + suggested fix
  - Collapsible sections for detailed view
- **RAG Evidence Citations** (if blocking error claimed):
  - Source ID: `rag_doc_001`
  - Excerpt: "DWI high signal indicates acute infarction..."
  - Relevance: High/Medium/Low badge
  - Expandable for full excerpt

#### 3.3.5 Visual Design

- **Panel Style**: Distinct panel with border/background color (light blue/gray)
- **Header**: "S5 Validation Results (for reference only)"
- **Footer**: "These results are for your reference. Your Pre-S5 rating is locked and will be used for analysis."
- **Color Coding**: 
  - Red: Blocking errors
  - Yellow: Minor issues/warnings
  - Green: No issues

---

## 4. Post-S5 Rating Fields (Exact Specification)

### 4.1 Pre-S5 Values Display (Read-Only)

- **Layout**: Grayed out, with "Pre-S5" label
- **Fields**: 
  - `blocking_error_pre` (read-only, displayed as Yes/No)
  - `technical_accuracy_pre` (read-only, displayed as 0.0 / 0.5 / 1.0)
  - `overall_quality_pre` (read-only, displayed as 1-5)
  - `evidence_comment_pre` (read-only, if exists)
- **Visual**: Light gray background, italic text, "Pre-S5" badge

### 4.2 Post-S5 Fields (Editable)

- **Default Values**: Pre-filled with Pre-S5 values
- **Fields**:
  - `blocking_error_post` (Yes/No, editable, default = `blocking_error_pre`)
  - `technical_accuracy_post` (0.0 / 0.5 / 1.0, editable, default = `technical_accuracy_pre`)
  - `overall_quality_post` (1-5 Likert, editable, default = `overall_quality_pre`)
  - `evidence_comment_post` (text area, editable, default = `evidence_comment_pre`)
- **Visual**: Normal styling, "Post-S5" label, editable inputs

### 4.3 Change Detection

- **Trigger**: Any Post-S5 field differs from Pre-S5 value
- **Action**: 
  - Highlight changed fields (yellow border)
  - Show change log form (see Section 5)
  - Require change reason code and note

### 4.4 Submit Final Rating Button

- **Label**: "Submit Final Rating"
- **State**: Enabled when all required fields are filled (including change log if changed)
- **Action**:
  - Validate all required fields (including change log if changed)
  - Calculate `correction_time_ms`
  - Save Post-S5 data and change log to backend
  - Mark session as complete
  - Show confirmation: "Final rating submitted. Thank you!"
- **Visual Feedback**: Button changes to "Final Rating Submitted" (disabled, grayed)

---

## 5. Change Log Form (Conditional)

### 5.1 Trigger

- **Condition**: Any Post-S5 field differs from Pre-S5 value
- **Display**: Change log form appears below Post-S5 fields

### 5.2 Fields

#### 5.2.1 Change Reason Code (Required if Changed)

- **Type**: Dropdown (single select)
- **Label**: "Reason for Change"
- **Options**: 
  - `S5_BLOCKING_FLAG`: "S5 flagged blocking error; confirmed after review"
  - `S5_BLOCKING_FALSE_POS`: "S5 flagged blocking error; determined to be false positive"
  - `S5_QUALITY_INSIGHT`: "S5 quality assessment provided useful insight"
  - `S5_EVIDENCE_HELPED`: "S5 evidence/suggestion helped identify issue"
  - `S5_NO_EFFECT`: "S5 results reviewed but no change needed"
  - `RATER_REVISION`: "Rater reconsidered without S5 influence (rare)"
  - `OTHER`: "Other reason (specify in note)"
- **Required**: Yes (if any field changed)
- **Field Name**: `change_reason_code`

#### 5.2.2 Change Note (Required if Changed)

- **Type**: Text area (1-line, max 200 chars)
- **Label**: "Change Note"
- **Placeholder**: "Brief explanation of change (1 line)"
- **Required**: Yes (if any field changed)
- **Validation**: Must be non-empty, max 200 chars
- **Field Name**: `change_note`

### 5.3 Multiple Field Changes

- **If multiple fields changed**: One change log entry per changed field
- **Display**: List of change log entries (one per field)
- **Each entry**: Field name + old value → new value + reason code + note

### 5.4 Validation

- **Backend**: Rejects submission if changes exist without change log
- **Frontend**: Validates change log before enabling submit button
- **Error Message**: "Please provide reason and note for all changes"

---

## 6. Conditional Logic Summary

### 6.1 Pre-S5 Phase

- **B3 (Evidence Comment) required if**: `B1=Yes` OR `B2<=2`
- **Submit button enabled if**: 
  - B1 filled AND 
  - B1.5 filled AND
  - B2 filled AND 
  - (B3 filled if required)

### 6.2 S5 Reveal Phase

- **Reveal button enabled if**: Pre-S5 submitted (locked)
- **Backend check**: Verifies Pre-S5 lock exists before returning S5 results

### 6.3 Post-S5 Phase

- **Change log required if**: Any Post-S5 field differs from Pre-S5
- **Change log fields required if**: Change log is required
- **Submit button enabled if**: 
  - All Post-S5 fields filled AND 
  - (Change log filled if changed)

---

## 7. Time Measurement

### 7.1 Pre-S5 Time (Auto-Logged)

- **Field**: `time_pre_ms`
- **Calculation**: `timestamp_submitted_ms - timestamp_viewed_ms`
- **No user input required**
- **Fallback**: If timestamp logging fails, use time bins (see Section 7.3)

### 7.2 Correction Time (Auto-Logged)

- **Field**: `correction_time_ms`
- **Calculation**: `timestamp_final_submitted_ms - s5_reveal_timestamp_ms`
- **No user input required**
- **Fallback**: If timestamp logging fails, use time bins (see Section 7.3)

### 7.3 Time Bins (Fallback)

If auto-logging fails, use self-reported time bins:

- **Pre-S5 Time**: `<2분 / 2-5분 / 5-7분 / 7-10분 / >10분`
- **Correction Time**: `<30초 / 30초-1분 / 1분-3분 / 3분-5분 / >5분`

---

## 8. Endpoint Variables

### 8.1 Primary Endpoints (Pre-S5 Ratings Only)

**For Arm Comparison**:

- **Major Error Rate (MER_pre)**: `mean(major_error_pre)` per arm, where `major_error_pre` is deterministically derived as defined in Section 0.1.3
- **Blocking Error Rate (BER_pre)**: `mean(blocking_error_pre)` per arm
- **Technical Accuracy Mean (TAM_pre)**: `mean(technical_accuracy_pre)` per arm
- **Overall Card Quality (GCR_pre)**: `mean(overall_quality_pre)` per arm

**Usage**: All arm comparison decisions use Pre-S5 ratings only.

### 8.2 Secondary Endpoints (Post-S5 Ratings)

**For Tool Effect Measurement**:

- **Blocking Error Correction Rate (BER_delta)**: `BER_post - BER_pre`
- **Technical Accuracy Change (TAM_delta)**: `TAM_post - TAM_pre`
- **Quality Score Change (GCR_delta)**: `GCR_post - GCR_pre`
- **Correction Time (CT_post)**: `mean(correction_time_ms)` per card

**Usage**: Measure S5 tool effectiveness (exploratory).

### 8.3 Change Log Analysis

**For Tool Performance**:

- **Change Reason Distribution**: Frequency of each `change_reason_code`
- **Blocking Error Change Pattern**: How often S5 flags lead to blocking error corrections
- **False Positive Rate**: `change_reason_code="S5_BLOCKING_FALSE_POS"` frequency

---

## 9. UI/UX Guidelines

### 9.1 Minimal Friction

- **Pre-fill Post-S5**: Most cards unchanged, so Post-S5 pre-filled with Pre-S5 values
- **Conditional inputs**: Only require inputs when necessary (B3, change log)
- **One-screen layout**: Minimize scrolling
- **Clear labels**: "Pre-S5" and "Post-S5" clearly labeled

### 9.2 Visual Feedback

- **Pre-S5 submitted**: Fields grayed, button disabled, confirmation message
- **S5 revealed**: Panel expands, Post-S5 form appears
- **Fields changed**: Yellow border, change log form appears
- **Final submitted**: All fields locked, confirmation message

### 9.3 Error Handling

- **Validation errors**: Inline error messages below fields
- **Network errors**: Retry button, error message at top
- **S5 fetch errors**: Warning message, allow Post-S5 without S5 results

---

## 10. Implementation Checklist

### 10.1 Frontend Components

- [ ] `PreS5RatingForm` component
- [ ] `S5ResultsPanel` component
- [ ] `PostS5RatingForm` component
- [ ] `ChangeLogForm` component
- [ ] Time measurement hooks

### 10.2 Backend API Integration

- [ ] Pre-S5 submission endpoint integration
- [ ] S5 reveal endpoint integration
- [ ] Post-S5 submission endpoint integration
- [ ] Error handling and retry logic

### 10.3 Validation Logic

- [ ] Pre-S5 field validation (B3 conditional)
- [ ] Change detection logic
- [ ] Change log validation
- [ ] Time calculation logic

---

## 11. Related Documents

- `S5_Validation_Contract_Canonical.md`: S5 role and contract definition
- `Human_Rating_Schema_Canonical.md`: Human rating schema
- `S0_QA_Form_One-Screen_Layout.md`: S0 QA form reference
- `S5_Validation_Plan_OptionB_Canonical.md`: Detailed implementation plan

---

## 12. Version History

- **v1.0** (2025-12-26): Initial canonical form design
- **v1.1** (2025-12-29): Added B1.5 Technical Accuracy field (required) to align with QA_Metric_Definitions.md and enable S5 vs Human Rater comparison analysis
- **v1.2** (2025-12-29): Clarified that FINAL QA evaluates only Q1 (단답형 주관식) and Q2 (MCQ), both with images on BACK. Q3 is not evaluated in FINAL QA.
- **v1.3** (2025-12-29): Clarified that Q3 was only used in S0 (QA experiment) and is not generated in FINAL mode. S2 generates only Q1 and Q2 in FINAL mode.
- **v1.4** (2025-12-29): Added FINAL gate QA design summary, deterministic sampling and escalation rules, binary major_error endpoint definition, and multi-agent evaluation integration without contaminating primary endpoints.

---

**Document Status**: Canonical  
**Last Updated**: 2025-12-29  
**Owner**: MeducAI Research Team

