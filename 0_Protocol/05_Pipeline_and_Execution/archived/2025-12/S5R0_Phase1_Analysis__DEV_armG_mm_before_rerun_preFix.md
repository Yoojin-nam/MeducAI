# S5R0 Phase 1 — S5 Report Analysis & Improvement Points (Arm G)

- **rep1 run_tag**: `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1`
- **rep2 run_tag**: `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_203653__rep2`
- **Arm**: `G`

## 0. Judge version information (for cross-evaluation)

### rep1 judge info
- **Generation S5R**: S5R0
- **Evaluation judge S5R**: None
- **Prompt bundle hash**: 0953d32464e0bdbe
- **S5 prompt files**: S5_SYSTEM, S5_USER_TABLE, S5_USER_CARD, S5_USER_CARD_IMAGE, S5_USER_TABLE_VISUAL
- **Judge consistency**: ✓ Consistent

### rep2 judge info
- **Generation S5R**: S5R0
- **Evaluation judge S5R**: None
- **Prompt bundle hash**: 0953d32464e0bdbe
- **S5 prompt files**: S5_SYSTEM, S5_USER_TABLE, S5_USER_CARD, S5_USER_CARD_IMAGE, S5_USER_TABLE_VISUAL
- **Judge consistency**: ✓ Consistent

## 1. Run-level summary (per replicate)

| replicate | groups | S2 total cards | cards with ≥1 issue | total issues | any-issue rate (by cards) | mean(any-issue rate) (by groups) |
|---|---|---|---|---|---|---|
| rep1 | 11 | 330 | 47 | 62 | 14.2% | 14.5% |
| rep2 | 11 | 348 | 48 | 56 | 13.8% | 13.7% |

- Notes:
  - **Primary endpoint unit is group-level** (n=11 groups); replicate count does not increase n.
  - **IMG numeric endpoints not computed here** because these S5 JSONL records do not include image-evaluation rubric fields (no `card_image_*` / `table_visual_*`).
    - However, many **image-related issues** are still present as `issue_code`s on S2 cards (e.g., view mismatch, excessive text).

## 2. Primary endpoint per group (S2_any_issue_rate_per_group)

| group_id | S2_any_issue_rate (rep1) | S2_any_issue_rate (rep2) | mean | SD | S2_total_cards (rep1/rep2) | S2_cards_with_issue (rep1/rep2) | S2_issues_per_card mean (rep1/rep2) |
|---|---|---|---|---|---|---|---|
| `grp_1c64967efa` | 0.0% | 3.3% | 1.7% | 2.4% | 28/30 | 0/1 | 0.000/0.033 |
| `grp_2c6fda981d` | 12.5% | 5.9% | 9.2% | 4.7% | 32/34 | 4/2 | 0.156/0.059 |
| `grp_6ae1e80a49` | 17.6% | 20.6% | 19.1% | 2.1% | 34/34 | 6/7 | 0.206/0.235 |
| `grp_929cf68679` | 7.1% | 3.6% | 5.4% | 2.5% | 28/28 | 2/1 | 0.071/0.036 |
| `grp_92ab25064f` | 30.0% | 46.7% | 38.3% | 11.8% | 20/30 | 6/14 | 0.450/0.567 |
| `grp_afe6e9c0b9` | 36.7% | 36.7% | 36.7% | 0.0% | 30/30 | 11/11 | 0.600/0.500 |
| `grp_baa12e0b6e` | 7.7% | 0.0% | 3.8% | 5.4% | 26/24 | 2/0 | 0.077/0.000 |
| `grp_c63d9a24cf` | 3.6% | 0.0% | 1.8% | 2.5% | 28/32 | 1/0 | 0.036/0.000 |
| `grp_cbcba66e24` | 17.9% | 11.5% | 14.7% | 4.5% | 28/26 | 5/3 | 0.250/0.115 |
| `grp_f073599bec` | 13.2% | 10.0% | 11.6% | 2.2% | 38/40 | 5/4 | 0.132/0.100 |
| `grp_fb292cfd1d` | 13.2% | 12.5% | 12.8% | 0.5% | 38/40 | 5/5 | 0.158/0.125 |

## 3. Issue taxonomy (rep1+rep2 combined; descriptive)

### 3.1 S1 (table) — top issue codes

- `OUTDATED_TERMINOLOGY`: 2
- `TERM_PRECISION`: 2
- `CLARITY_CELLULITIS_DELAYED`: 1
- `CLARITY_COMPARISON`: 1
- `CLINICAL_ACCURACY_MINOR`: 1
- `CLINICAL_NUANCE_FEEDING_VESSEL`: 1
- `MEDICAL_NUANCE`: 1
- `MRI_PHYSICS_CLARITY`: 1
- `OUTDATED_CRITERIA`: 1
- `OUTDATED_EPONYM`: 1
- `PHYSICS_TERM_PRECISION`: 1
- `REGULATORY_SYNTAX`: 1
- `TERMINOLOGY_DRIFT`: 1
- `TERM_CLARITY`: 1
- `TERM_MODERNIZATION`: 1

### 3.2 S2 (cards) — top issue codes

- `IMAGE_TEXT_EXCESSIVE`: 14
- `IMAGE_TEXT_COUNT_EXCEEDED`: 8
- `PROMPT_COMPLIANCE_VIEW_MISMATCH`: 8
- `IMAGE_VIEW_MISMATCH`: 7
- `IMAGE_TEXT_BUDGET_EXCEEDED`: 5
- `IMAGE_EXCESSIVE_TEXT`: 3
- `IMAGE_STYLE_EXCESSIVE_TEXT`: 2
- `IMAGE_TEXT_LENGTH`: 2
- `IMAGE_TEXT_TYPO`: 2
- `PROMPT_COMPLIANCE_MULTI_PANEL`: 2
- `PROMPT_COMPLIANCE_TEXT_BUDGET`: 2
- `PROMPT_VIOLATION_COLLAGE`: 2
- `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH`: 2
- `ANATOMICAL_ERROR_PATHOLOGY_MISREPRESENTATION`: 1
- `ANATOMICAL_LATERALITY_MISMATCH`: 1
- `ANATOMY_LATERALITY_SWAP`: 1
- `C1`: 1
- `CLARITY_DIAGNOSIS_VS_FINDING`: 1
- `CLARITY_DIFFERENTIAL`: 1
- `CLARITY_QUESTION_ANSWER_MISMATCH`: 1

### 3.3 recommended_fix_target distribution (combined)

**S1**:
- `S1_TABLE_CONTENT`: 21

**S2**:
- `S3_PROMPT`: 79
- `S3_IMAGE`: 4
- `UNKNOWN`: 4
- `card_front`: 4
- `Front text`: 3
- `Back`: 2
- `S2_CARD_TEXT`: 2
- `S2_SYSTEM`: 2
- `card_content`: 2
- `Back (Explanation for Option C)`: 1
- `Back rationale`: 1
- `Back text`: 1

## 4. Patch backlog (rep1+rep2 combined; top targets)

This is a compact, actionable view: **recommended_fix_target → issue_code → count (+ up to 2 patch hints)**.

### S2 target: `S3_PROMPT`
- `IMAGE_TEXT_EXCESSIVE`: 10
  - patch_hint: Enforce stricter label count limits in the S3 prompt instructions.
  - patch_hint: Reinforce 'Max 1-2 labels' constraint in the rendering policy.
- `IMAGE_TEXT_COUNT_EXCEEDED`: 8
  - patch_hint: Ensure text_budget is strictly followed if 1-2 labels is a hard constraint.
  - patch_hint: Reinforce the 'Max 1-2 labels' constraint in the S3 prompt if strict compliance is desired.
- `PROMPT_COMPLIANCE_VIEW_MISMATCH`: 7
  - patch_hint: Change 'view_plane': 'axial' to 'view_plane': 'sagittal' in the image_hint_v2 anatomy section.
  - patch_hint: Change view_or_sequence to 'Schematic anatomical diagram' or enforce axial slice geometry more strictly in the rendering policy.
- `IMAGE_VIEW_MISMATCH`: 6
  - patch_hint: Change view_or_sequence to 'Four-chamber view diagram' to match the didactic nature of the illustration.
  - patch_hint: Ensure the generated diagram strictly follows the 'axial' view plane by showing only structures visible in a single axial slice (e.g., frontal sinus and skull vault without orbits/maxillary sinuses visible simultaneously).
- `IMAGE_TEXT_BUDGET_EXCEEDED`: 5
  - patch_hint: Enforce the 'minimal_labels_only' policy more strictly in the rendering instructions.
  - patch_hint: Reinforce 'minimal_labels_only' constraint if strict limit is desired.
- `IMAGE_EXCESSIVE_TEXT`: 3
  - patch_hint: Reinforce the 'max 1-2 labels' constraint in the S3 prompt instructions.
  - patch_hint: Reinforce the 'max 1-2 labels' constraint in the S3 system prompt.
- `IMAGE_STYLE_EXCESSIVE_TEXT`: 2
  - patch_hint: Reinforce the 'Max 1-2 labels total' constraint in the rendering policy.
  - patch_hint: Strictly enforce the 'Max 1-2 labels total' constraint in the rendering policy.
- `IMAGE_TEXT_LENGTH`: 2
  - patch_hint: Enforce stricter word counts for labels in the S3 prompt.
  - patch_hint: Update the annotation rules to strictly enforce a 3-word limit for labels to ensure clarity and compliance with diagram standards.

### S2 target: `S3_IMAGE`
- `IMAGE_ANATOMICAL_ERROR`: 1
  - patch_hint: Ensure the prompt explicitly enforces the topology constraint: 'Morphologic RV must be on the LEFT side' and 'Aorta must be to the LEFT of the Pulmonary Artery'.
- `IMAGE_LABEL_MISPLACEMENT`: 1
  - patch_hint: Refine the prompt to specify that labels should only point to the vertebral body and not the spinal canal.
- `IMAGE_VIEW_MISMATCH`: 1
  - patch_hint: If an axial view is required for board-style MRI questions, the prompt should more strictly enforce cross-sectional rendering.
- `IMAGE_VISUAL_TERMINOLOGY_MISMATCH`: 1
  - patch_hint: Specify that 'metaphyseal lucent bands' must be depicted as darker (radiolucent) horizontal lines adjacent to the growth plate, not white/opaque lines.

### S2 target: `UNKNOWN`
- `FORMAT_SPACING`: 1
- `IMAGE_TEXT_EXCESSIVE`: 1
- `IMAGE_TEXT_NON_STANDARD`: 1
- `PROMPT_VIOLATION_COLLAGE`: 1

### S1 target: `S1_TABLE_CONTENT`
- `OUTDATED_TERMINOLOGY`: 2
- `TERM_PRECISION`: 2
  - patch_hint: Ensure anatomical origin of skin calcifications aligns with BI-RADS (sebaceous glands).
  - patch_hint: Ensure calcification size thresholds match BI-RADS 5th ed definitions strictly (<0.5mm vs 0.5-1mm).
- `CLARITY_CELLULITIS_DELAYED`: 1
  - patch_hint: Ensure Cellulitis delayed phase emphasizes 'no focal bone uptake' rather than just 'decreased uptake'.
- `CLARITY_COMPARISON`: 1
- `CLINICAL_ACCURACY_MINOR`: 1
- `CLINICAL_NUANCE_FEEDING_VESSEL`: 1
- `MEDICAL_NUANCE`: 1
  - patch_hint: Clarify PMP origin (usually appendiceal) when discussing ovarian mucinous tumors.
- `MRI_PHYSICS_CLARITY`: 1

## 5. Phase-2 (S5R1) improvement points (from S5R0 issues)

### 5.1 Image-spec / image-generation prompt improvements (highest frequency in S5R0)

- **Reduce image text load**: enforce a strict text budget and label-count limit in S3/S4 prompts to address `IMAGE_TEXT_*` failures.
- **View compliance**: enforce explicit view tokens (AP/PA/Lateral/etc.) and validate they match the requested view (`*_VIEW_MISMATCH`).
- **Laterality & anatomy sanity checks**: add a minimal self-check step for laterality inversion and label placement.

### 5.2 S2 prompt/system improvements (next highest leverage)

- **Diagnosis vs descriptor / vague answers**: tighten instruction to ensure `Answer` matches the question intent (diagnosis vs imaging finding/descriptor).
- **Entity type ↔ exam_focus alignment**: enforce `exam_focus` allowed values by entity type (e.g., disease → diagnosis) to prevent `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH`.
- **Korean terminology + typos**: add explicit “medical Korean spell-check + avoid near-homophone slips” step (e.g., 분만/분산, 하하지/하지).
- **Circular answers**: forbid answers that restate the question; require a direct 'why' / purpose when asked.

### 5.3 S1 table improvements (quality + exam fidelity)

- **Definition precision**: codify numeric thresholds precisely when they are canonical exam points (e.g., BI-RADS calcification size cutoffs).
- **Modern terminology**: update outdated eponyms/terms (optionally keep '(formerly …)' for recall).
- **Physics/wording clarity**: clarify terms that are easily misread (e.g., washout vs photopenia; DWI shine-through vs ADC).
