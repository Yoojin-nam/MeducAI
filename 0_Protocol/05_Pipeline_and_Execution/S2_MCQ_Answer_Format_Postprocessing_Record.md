# S2 MCQ Answer Format Post-Processing Record

**Document Type:** Execution Record (Post-Processing Artifact)  
**Status:** Active  
**Created:** 2026-01-05  
**Applies to:** `s2_results__s1armG__s2armG.jsonl`  
**Compliance:** MI-CLEAR-LLM 2025 (Transparency Requirement)  
**Location:** `0_Protocol/05_Pipeline_and_Execution/S2_MCQ_Answer_Format_Postprocessing_Record.md`

---

## 1. Purpose

This document records a deterministic post-processing transformation applied to S2 MCQ card outputs, ensuring MI-CLEAR-LLM transparency and reproducibility requirements are satisfied.

---

## 2. Issue Description

### 2.1 Discovered Problem

S2 results contained MCQ cards where the `back` text "정답:" field was generated in incorrect formats:

| Error Type | Example | Affected Cards |
|------------|---------|----------------|
| Numeric index | "정답: 4" | Uses `correct_index` value directly |
| Option text | "정답: Petersen's space는..." | Uses first word(s) of correct option |

### 2.2 Affected Files

| File | Incorrect Cases | Action |
|------|-----------------|--------|
| `s2_results__s1armG__s2armG.jsonl` | 179 cards | **Post-processed** |
| `s2_results__s1armG__s2armP.jsonl` | 179 cards | **Archived** (experimental arm) |

### 2.3 Data Integrity Verification

Before post-processing, the following was verified:

- ✅ `correct_index` values are accurate (0-4 range)
- ✅ `options[correct_index]` matches the intended correct answer
- ✅ Only the `back` text format is incorrect (semantic accuracy preserved)
- ✅ No LLM-generated content is altered beyond format normalization

---

## 3. MI-CLEAR-LLM Compliance Analysis

### 3.1 Why Post-Processing Is Not a Violation

| MI-CLEAR-LLM Principle | Compliance Status | Justification |
|------------------------|-------------------|---------------|
| **Transparency** | ✅ Compliant | This document and the post-processing script serve as artifacts |
| **Reproducibility** | ✅ Compliant | Transformation is deterministic: `correct_index → ['A','B','C','D','E'][correct_index]` |
| **LLM Output Integrity** | ✅ Compliant | Original S2 file backed up; only format (not content) is modified |

### 3.2 Core Rationale

The post-processing performs **format normalization only**:

1. **No semantic change**: The `correct_index` and `options[]` array (LLM-generated content) remain unchanged
2. **Deterministic transformation**: The letter derivation is a pure function with no ambiguity
3. **Auditable**: All changes are logged with before/after comparison

---

## 4. Post-Processing Specification

### 4.1 Transformation Logic

```python
# Deterministic mapping (no LLM involvement)
LETTER_MAP = ['A', 'B', 'C', 'D', 'E']

def fix_answer_format(card):
    correct_index = card['correct_index']
    correct_letter = LETTER_MAP[correct_index]
    
    # Regex substitution in back text
    back_text = card['back']
    fixed_back = re.sub(r'정답:\s*\S+', f'정답: {correct_letter}', back_text, count=1)
    
    return fixed_back
```

### 4.2 Implementation

- **Script Location:** `3_Code/Scripts/fix_s2_mcq_answer_format.py`
- **Backup Location:** `2_Data/metadata/generated/FINAL_DISTRIBUTION/archive/s2_results__s1armG__s2armG__original_YYYYMMDD_HHMMSS.jsonl`
- **Change Log:** `2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_mcq_format_fix_log.jsonl`

---

## 5. Artifacts

### 5.1 Required Artifacts for Audit

| Artifact | Purpose | Location |
|----------|---------|----------|
| Original S2 backup | Preserve LLM output | `archive/s2_results__s1armG__s2armG__original_*.jsonl` |
| Post-processed S2 | Production file | `s2_results__s1armG__s2armG.jsonl` |
| Change log | Diff record | `s2_mcq_format_fix_log.jsonl` |
| This document | Transparency record | Current file |

### 5.2 arm P Archive

Files moved to archive (experimental arm, not part of final study):

```
2_Data/metadata/generated/FINAL_DISTRIBUTION/archive/
├── s2_results__s1armG__s2armP.jsonl
├── s3_image_spec__armP.jsonl
├── s4_image_manifest__armP.jsonl
├── s4_image_manifest__armP__repaired.jsonl
└── image_policy_manifest__armP.jsonl
```

---

## 6. Prevention Measures

### 6.1 Prompt Update

The following prompt files were updated to prevent recurrence:

| File | Change |
|------|--------|
| `S2_SYSTEM__S5R3__v12.md` | Added explicit "정답:" format requirement in Q2 section and RISK CONTROL section |
| `S2_SYSTEM__S5R2__v11.md` | Added explicit "정답:" format requirement in Q2 section and RISK CONTROL section |

### 6.2 Added Instruction (verbatim)

```markdown
- **CRITICAL MCQ back format**: The "정답:" field MUST be a single letter (A, B, C, D, or E), 
  NOT a number, NOT option text. 
  - ✅ CORRECT: "정답: B"
  - ❌ WRONG: "정답: 1" (using correct_index value)
  - ❌ WRONG: "정답: Petersen's space는..." (using option text)
```

---

## 7. Sign-off

| Role | Date | Signature |
|------|------|-----------|
| Lead Research Engineer | 2026-01-05 | (Documented via version control) |

---

## 8. References

- [MI-CLEAR-LLM 2025 Guide](../00_Governance/supporting/Prompt_governance/MI-CLEAR-LLM_2025_guide.md)
- [S2 MCQ Answer Fix Plan](.cursor/plans/s2_mcq_answer_fix_72efceb4.plan.md)
- [S2 Prompt v12](../../3_Code/prompt/S2_SYSTEM__S5R3__v12.md)

