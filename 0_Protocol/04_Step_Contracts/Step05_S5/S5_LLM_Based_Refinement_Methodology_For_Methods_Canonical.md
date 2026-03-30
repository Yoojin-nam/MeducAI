# S5 LLM-Based Prompt Refinement Methodology (Methods Section)

**Status**: Canonical (Methods documentation for publication)  
**Version**: 1.0  
**Last Updated**: 2025-12-29  
**Scope**: LLM-as-a-judge validation and iterative prompt refinement methodology for publication Methods section  
**Primary Use**: Research paper Methods section, IRB documentation, reproducibility

---

## 1. Overview

This document describes the **LLM-based validation and iterative prompt refinement methodology** used in MeducAI to maintain content quality and improve generation prompts. This methodology follows the **LLM-as-a-judge** paradigm (Liu et al., 2023; Zheng et al., 2023) adapted for medical education content validation.

### Core Design Principles

1. **Separation of Validation and Generation**: Validation (S5) is read-only and does not modify generated content
2. **Structured Issue Classification**: Issues are classified using a hierarchical taxonomy (`issue_code`, `type`, `severity`)
3. **Actionable Feedback Loop**: Validation outputs include `recommended_fix_target` and `prompt_patch_hint` for direct prompt improvement
4. **Traceability**: All validation runs, prompt versions, and improvements are tracked via `run_tag`, `validation_timestamp`, and prompt version numbers (MI-CLEAR-LLM compliance)

---

## 2. LLM-as-a-Judge Validation (Step 5: S5)

### 2.1 Validation Scope

S5 validates two types of generated content:

- **S1 Master Tables**: Structured radiology curriculum tables (entities, imaging features, exam points)
- **S2 Question Cards**: Anki-style flash cards (Q1: Basic/diagnosis, Q2: MCQ/concept)

### 2.2 Validation Model and Configuration

- **Model**: Gemini 3 Pro Preview (for S1 table validation), Gemini 3 Flash Preview (for S2 card validation)
- **Retrieval Augmented Generation (RAG)**: Enabled for both S1 and S2 validation
  - Grounds validation judgments using Google Search results
  - Provides evidence citations in validation output
- **Thinking Mode**: Enabled for complex reasoning tasks
- **Output Format**: Structured JSON conforming to `S5_VALIDATION_v1.1` schema

### 2.3 Validation Criteria

#### For S1 Master Tables:

1. **Technical Accuracy** (0.0-1.0 scale)
   - Medical facts correctness
   - Guideline alignment (ACR, RSNA standards)
   - Terminology accuracy

2. **Educational Quality** (1-5 Likert scale)
   - Board exam relevance
   - Clarity and completeness
   - Appropriate level of detail

3. **Blocking Errors** (boolean)
   - Clinical safety-critical issues
   - Factual errors that could mislead learners
   - **Constraint**: `blocking_error=true` must imply `technical_accuracy=0.0`

#### For S2 Question Cards:

1. **Technical Accuracy** (0.0-1.0 scale)
   - Answer correctness
   - Option plausibility and homogeneity
   - Rationale consistency with answer

2. **Educational Quality** (1-5 Likert scale)
   - Question clarity
   - Distractor quality
   - Board exam fit

3. **Blocking Errors** (boolean)
   - Incorrect answers
   - Multiple correct options
   - Explanation contradicts stem
   - Missing key information making question unsolvable

### 2.4 Issue Classification Taxonomy

Each issue identified by S5 includes:

- **`type`**: High-level category (e.g., `terminology`, `clarity`, `clinical_safety`, `completeness`)
- **`severity`**: `blocking`, `major`, or `minor`
- **`issue_code`** (optional, v1.1+): Specific issue identifier for aggregation
  - Examples: `AMBIGUOUS_TERMINOLOGY`, `OUTDATED_TERM_BAC`, `TERM_MISTRANSLATION`, `MISSING_RATIONALE_ITEM`
- **`recommended_fix_target`** (optional, v1.1+): Where to apply the fix
  - Examples: `S1_TABLE_CONTENT`, `Back`, `Front`, `entity_id`
- **`prompt_patch_hint`** (optional, v1.1+): Suggested prompt rule addition or modification
- **`confidence`** (optional, 0.0-1.0): LLM's confidence in the issue identification
- **`evidence_ref`** (optional): RAG evidence citation or S1 table reference

---

## 3. Validation Output Schema

### 3.1 Schema Version

- **Current**: `S5_VALIDATION_v1.1`
- **Location**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`

### 3.2 Key Schema Elements

```json
{
  "schema_version": "S5_VALIDATION_v1.1",
  "run_tag": "...",
  "group_id": "...",
  "arm": "...",
  "validation_timestamp": "ISO8601",
  "s5_model_info": {
    "s1_table_model": "...",
    "s1_table_rag_enabled": true,
    "s2_card_model": "...",
    "s2_card_rag_enabled": true
  },
  "s1_table_validation": {
    "blocking_error": false,
    "technical_accuracy": 1.0,
    "educational_quality": 5,
    "issues": [...],
    "rag_evidence": [...]
  },
  "s2_cards_validation": {
    "cards": [...],
    "summary": {
      "total_cards": 8,
      "blocking_errors": 0,
      "mean_technical_accuracy": 1.0,
      "mean_educational_quality": 5.0
    }
  }
}
```

---

## 4. Report Generation and Patch Backlog Extraction

### 4.1 Report Generation

Validation outputs are aggregated into human-readable Markdown reports:

```bash
python3 -m tools.s5.s5_report \
  --base_dir <BASE_DIR> \
  --run_tag <RUN_TAG> \
  --arm <ARM>
```

**Output**: `2_Data/metadata/generated/<RUN_TAG>/reports/s5_report__arm<ARM>.md`

### 4.2 Report Structure

1. **Summary**: Aggregate statistics (blocking rates, mean scores)
2. **Per-group Summary**: Latest validation result per group (table format)
3. **Issue Taxonomy**: Distribution of issue types and codes
4. **Blocking Items**: List of items with `blocking_error=true`
5. **Recommended Improvements**: High-level suggestions
6. **Patch Backlog** (v1.1+): Actionable issue groupings
   - Groups issues by `recommended_fix_target` × `issue_code`
   - Includes `prompt_patch_hint` for each group
   - Enables direct translation to prompt patches

### 4.3 Patch Backlog Example

```markdown
### Target: `S1_TABLE_CONTENT` (n=11)
- **TERM_CONFUSION**: 1
  - patch_hint: Avoid using 'Double stripe sign' for Shin Splints; reserve for HPOA.
- **CLINICAL_NUANCE_UPDATE**: 1
  - patch_hint: Update Porcelain GB cancer risk to reflect modern lower estimates.

### Target: `Back` (n=1)
- **MISSING_RATIONALE_ITEM**: 1
  - patch_hint: Ensure all distractors (A-E) are addressed in the explanation.
```

---

## 5. Iterative Prompt Refinement Loop

### 5.1 Workflow

1. **Generate Content** (S1/S2)
   - Execute generation pipeline with current prompts
   - Save outputs with `run_tag`

2. **Validate Content** (S5)
   - Run S5 validation on generated content
   - Generate validation report

3. **Analyze Report**
   - Review Patch Backlog section
   - Prioritize issues by frequency and severity
   - Identify patterns (e.g., recurring terminology errors)

4. **Apply Prompt Patches**
   - Update prompt files (e.g., `S1_SYSTEM__v12.md` → `S1_SYSTEM__v13.md`)
   - Add specific rules with examples
   - Update prompt registry (`3_Code/prompt/_registry.json`)

5. **Re-validate** (Optional)
   - Generate new content with updated prompts
   - Re-run S5 validation
   - Compare metrics (blocking rate, issue counts)

6. **Freeze** (When Satisfied)
   - Document prompt version freeze
   - Record freeze rationale
   - Prepare for formal study run

### 5.2 Prompt Patch Examples

This section presents **real examples** from actual S5 validation runs (December 2025) showing the issue detection, patch hint extraction, and prompt improvement process.

#### Example 1: Terminology Specificity - Double Stripe Sign (S1)

**S5 Detection** (`DEV_armG_s5loop_diverse_20251229_065718`):
- **Issue Code**: `TERM_CONFUSION`
- **Severity**: `minor`
- **Type**: `terminology`
- **Description**: "Using 'Double stripe sign' for Shin Splints creates confusion. This sign is classically reserved for Hypertrophic Pulmonary Osteoarthropathy (HPOA)."
- **Recommended Fix Target**: `S1_TABLE_CONTENT`
- **Patch Hint**: "Avoid using 'Double stripe sign' for Shin Splints; reserve for HPOA."
- **Group**: Multiple groups affected

**Prompt Patch** (`S1_SYSTEM__v12.md`, added December 2025):

```markdown
- **Terminology Specificity**: Reserve specific radiological signs and terms 
  for their correct clinical entities.
  - Example: "Double stripe sign" is specific to **Hypertrophic Pulmonary 
    Osteoarthropathy (HPOA)**. Do NOT use this term for other conditions 
    like Shin Splints (which have different imaging characteristics).
```

**Impact**: Prevents misuse of radiological sign terminology, improving exam accuracy.

---

#### Example 2: Clinical Guideline Updates - Porcelain Gallbladder Risk (S1)

**S5 Detection** (`DEV_armG_s5loop_diverse_20251229_065718`):
- **Issue Code**: `CLINICAL_NUANCE_UPDATE`
- **Severity**: `minor`
- **Type**: `guideline_update`
- **Description**: "Porcelain gallbladder cancer risk estimate appears outdated. Modern literature suggests 5-10% lifetime risk rather than higher historical estimates."
- **Recommended Fix Target**: `S1_TABLE_CONTENT`
- **Patch Hint**: "Update Porcelain GB cancer risk to reflect modern lower estimates while retaining exam relevance."

**Prompt Patch** (`S1_SYSTEM__v12.md`, added December 2025):

```markdown
- **Clinical Guideline Updates**: When stating risk estimates, prevalence, 
  or clinical associations, reflect current evidence-based guidelines 
  rather than outdated estimates.
  - Example: Porcelain gallbladder cancer risk should reflect modern lower 
    estimates (approximately 5-10% lifetime risk, rather than older higher 
    estimates) while retaining exam relevance.
```

**Impact**: Ensures content reflects current evidence-based guidelines.

---

#### Example 3: Distractor Completeness in MCQ Explanations (S2)

**S5 Detection** (`DEV_armG_s5loop_diverse_20251229_065718`):
- **Issue Code**: `MISSING_RATIONALE_ITEM`
- **Severity**: `minor`
- **Type**: `completeness`
- **Description**: "The rationale (오답 포인트) explains options A, C, and D but omits an explanation for option E."
- **Recommended Fix Target**: `Back`
- **Patch Hint**: "Ensure all distractors (A-E) are addressed in the explanation for better educational value."
- **Card**: Q2 card in `grp_cbcba66e24`

**Prompt Patch** (`S2_USER_ENTITY__v8.md`, added December 2025):

```markdown
- "오답 포인트:" 1–2 bullets (why the closest distractor is wrong)
  - Example: "C는 오히려 RFA의 금기증일 수 있음 (척추는 신경 손상 위험)"
  - **IMPORTANT**: If the MCQ has 5 options (A–E), ensure the explanation 
    addresses all distractors. If not covered in "오답 포인트:", mention them 
    briefly or note that other options are clearly incorrect from context. 
    Educational completeness requires all options to be accounted for.
```

**Impact**: Improves educational completeness by ensuring all options are addressed in explanations.

---

#### Example 4: Question-Answer Type Alignment (S2)

**S5 Detection** (`DEV_armG_s5loop_diverse_20251229_065718`):
- **Issue Code**: `TERM_MISMATCH`
- **Severity**: `minor`
- **Type**: `phrasing_clarity`
- **Description**: "The question asks for a 'diagnosis' when the answer is actually a test/procedure or physical object (e.g., physics equipment)."
- **Recommended Fix Target**: `Front text`
- **Patch Hint**: "Ensure the question asks for the name of the tool/object rather than a 'diagnosis' when referring to physics equipment."

**Prompt Patch** (`S2_SYSTEM__v8.md`, added December 2025):

```markdown
- **Question-Answer Type Alignment**: Ensure the question prompt matches 
  the nature of the answer.
  - If asking for a diagnosis, use diagnostic phrasing (e.g., "가장 가능성이 
    높은 진단은?").
  - If asking for a test/procedure/equipment name, use appropriate phrasing 
    (e.g., "이 검사 방법은?", "이 기구의 이름은?").
  - Do NOT ask for a "diagnosis" when the answer is a test, procedure, 
    or physical object/tool.
```

**Impact**: Ensures question phrasing matches answer type, improving clarity and exam appropriateness.

---

#### Example 5: Entity ID Mapping Precision (S2)

**S5 Detection** (`DEV_armG_s5loop_diverse_20251229_065718`):
- **Issue Code**: `ENTITY_MISMATCH`
- **Severity**: `minor`
- **Type**: `metadata_alignment`
- **Description**: "Card's answer field references a specific entity, but entity_id maps to a broader parent entity."
- **Recommended Fix Target**: `entity_id`
- **Patch Hint**: "Map the card to the most specific S1 row matching the 'Answer' field."

**Prompt Patch** (`S2_SYSTEM__v8.md`, added December 2025):

```markdown
- **Entity ID Mapping**: Map each card to the most specific S1 row entity 
  that matches the card's answer. The `entity_id` must correspond to the 
  exact entity for which the card's content (especially the answer) is 
  most relevant.
```

**Impact**: Improves traceability and ensures cards are correctly linked to their source entities.

---

#### Example 6: Anatomical Description Precision (S2)

**S5 Detection** (`DEV_armG_s5loop_diverse_20251229_065718`):
- **Issue Code**: `ANATOMICAL_PRECISION`
- **Severity**: `minor`
- **Type**: `clarity`
- **Description**: "Description of right-sided heart chamber enlargement on PA view lacks clarity about specific radiographic appearance."
- **Recommended Fix Target**: `Front`
- **Patch Hint**: "Clarify the radiographic appearance of right-sided heart chamber enlargement on PA view."

**Prompt Patch** (`S2_SYSTEM__v8.md`, added December 2025):

```markdown
- **Anatomical Description Precision**: When describing radiographic 
  appearances (especially for anatomical structures), be precise and clear. 
  Include specific anatomical landmarks, orientation (view/plane), and 
  spatial relationships when relevant. Avoid vague descriptions that could 
  apply to multiple structures.
```

**Impact**: Improves anatomical precision and clarity of imaging descriptions.

---

### 5.3 Patch Effectiveness Tracking

After applying patches, the same groups were re-generated and re-validated:

- **Before patches**: Issue frequency tracked in `DEV_armG_s5loop_diverse_20251229_065718`
- **After patches**: Re-validation run (planned) to measure:
  - Reduction in specific `issue_code` frequencies
  - Improvement in mean `technical_accuracy` and `educational_quality`
  - Decrease in `blocking_error` rates

**Example tracking**:
- `TERM_CONFUSION` issues: Before → After (target: 50%+ reduction)
- `MISSING_RATIONALE_ITEM` issues: Before → After (target: elimination)
- Mean educational quality scores: Before vs After comparison

---

## 6. Traceability and Reproducibility

### 6.1 Versioning

- **Prompt Versions**: Filenames include version numbers (e.g., `S1_SYSTEM__v12.md`)
- **Schema Versions**: Validation schema includes `schema_version` field
- **Run Tags**: Each generation/validation run uses a unique `run_tag` (format: `<PREFIX>_<DATE>_<TIME>`)

### 6.2 MI-CLEAR-LLM Compliance

All validation outputs include:

- **Model Identification**: `s5_model_info.s1_table_model`, `s5_model_info.s2_card_model`
- **Prompt Versioning**: Prompt filenames stored in registry, traceable via `run_tag`
- **Parameters**: Temperature, RAG settings logged in model info
- **Timing**: `validation_timestamp` in ISO8601 format
- **RAG Logging**: `rag_evidence` array with source citations
- **Failure Logging**: `blocking_error` flags and issue descriptions

### 6.3 Documentation Chain

```
Generation Run (run_tag)
  → S1/S2 outputs (JSONL)
  → S5 validation (JSONL)
  → S5 report (Markdown)
  → Prompt patches (Markdown)
  → Updated prompt versions (Markdown)
  → Registry update (JSON)
  → Freeze documentation (Markdown)
```

---

## 7. Statistical Metrics and Evaluation

### 7.1 Aggregate Metrics

- **Blocking Rate**: `blocking_items / total_items`
- **Mean Technical Accuracy**: Average across all items
- **Mean Educational Quality**: Average Likert score
- **Issue Frequency**: Counts by `issue_code` or `type`

### 7.2 Comparison Across Iterations

When comparing pre- and post-patch performance:

1. Use same `group_id` set (or stratified sample)
2. Compare:
   - Blocking rate reduction
   - Issue code frequency changes
   - Mean score improvements
3. Report with `run_tag` pairs for full traceability

---

## 8. Limitations and Considerations

### 8.1 LLM-as-a-Judge Limitations

- **Judge Bias**: LLM judges may have verbosity bias, self-preference bias
- **Reliability**: Single-judge evaluation (multi-judge consensus is optional future work)
- **Calibration**: No explicit calibration for medical domain

### 8.2 Mitigation Strategies

- **RAG Grounding**: Reduces hallucination by grounding judgments in search results
- **Structured Schema**: Constrains outputs to reduce variability
- **Human Oversight**: Blocking errors flagged for human review
- **Iterative Refinement**: Repeated validation and patch cycles improve prompts

### 8.3 Ethical and Regulatory Considerations

- **IRB Compliance**: All LLM usage logged and traceable (MI-CLEAR-LLM)
- **Content Safety**: Blocking errors catch clinical safety issues before deployment
- **Human-in-the-Loop**: Formal study uses human ratings as primary endpoint; S5 is for development

---

## 9. References and Related Work

### 9.1 Key Methodological References

- **LLM-as-a-Judge**: Liu et al. (2023). G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment. arXiv:2303.16634
- **Judge Reliability**: Zheng et al. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. NeurIPS 2023
- **Iterative Refinement**: Madaan et al. (2023). Self-Refine: Iterative Refinement with Self-Feedback. NeurIPS 2023

### 9.2 Internal Documentation

- **S5 Validation Contract**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Contract_Canonical.md`
- **S5 Validation Schema**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`
- **S5 Prompt Refinement Methodology**: `0_Protocol/05_Pipeline_and_Execution/S5_Prompt_Refinement_Methodology_Canonical.md`
- **S5 Multi-agent Repair Plan**: `0_Protocol/05_Pipeline_and_Execution/S5_Multiagent_Repair_Plan_OptionC_Canonical.md`

---

## 10. Usage in Methods Section

### 10.1 Recommended Subsection Structure

1. **Step 5: LLM-Based Content Validation**
   - Validation scope and criteria
   - Model configuration
   - Output schema

2. **Issue Classification and Reporting**
   - Issue taxonomy
   - Report generation
   - Patch backlog extraction

3. **Iterative Prompt Refinement**
   - Workflow
   - Patch examples
   - Versioning and traceability

4. **Statistical Evaluation**
   - Aggregate metrics
   - Comparison methodology

### 10.2 Key Points to Emphasize

- **Separation of Development and Formal Study**: S5 is used for prompt refinement in development; formal study uses human ratings as primary endpoint
- **Structured Feedback Loop**: Automated issue classification enables systematic prompt improvement
- **Traceability**: Full lineage from generation → validation → report → patch → re-validation
- **MI-CLEAR-LLM Compliance**: All LLM usage logged for IRB audit

---

## 11. Document Status

- **Status**: Canonical
- **Intended Audience**: Research paper Methods section authors, IRB reviewers, reproducibility researchers
- **Update Policy**: Versioned; changes tracked via version number and last updated date

---

**End of Document**

