# S5R2 — S5 S2 Card Validation User Prompt v3.0 (Enhanced MCQ + Difficulty + Radiology Relevance + Q2 Cognitive)

**Purpose:** Validate S2 Anki card for medical safety, exam fitness, educational quality, and radiology relevance.

---

## Task

Evaluate the following S2 Anki card for:
1. Technical Accuracy (0/0.5/1.0 scale)
2. Educational Quality (1-5 Likert scale)
3. **Blocking Errors (clinical safety-critical only)**
4. Issues and suggested fixes (actionable, minimal scope)

---

## Input Data

### Card Information
- **Card ID:** {card_id}
- **Card Role:** {card_role} (Q1 or Q2)
  - Note: Q3 is deprecated in the current 2-card policy.
- **Card Type:** {card_type} (BASIC or MCQ)
- **Entity ID:** {entity_id}
- **Entity Name:** {entity_name}

### Card Content
**Front:**
{card_front}

**Back:**
{card_back}

### MCQ Structured Fields (Anki Convention)

**Important:** For Anki MCQ cards, the multiple-choice options are stored in structured JSON fields and may NOT appear in the Front text. Do NOT flag "options missing in Front" as an issue if options are provided below.

**Options (A–E, if MCQ):**
{card_options}

**Correct index (0–4, if MCQ):**
{correct_index}

### Entity Context (from S1 table; read-only)
{entity_context}

---

## Instructions

### Section 1: Clinical Safety (Blocking)

1. **Clinical safety (blocking)**:
   - Set `blocking_error=true` ONLY if there is a safety-critical medical error that could mislead clinical decisions.
   - If `blocking_error=true`, you MUST set `technical_accuracy=0.0` and provide RAG evidence.

### Section 2: Exam Fitness / Board-Style Quality (Non-blocking)

2. **Exam fitness / board-style quality (non-blocking)**:
   - Assess clarity, fairness (single best answer), distractor quality, alignment with typical board expectations.

### Section 3: MCQ Correctness (Enhanced Validation)

3. **MCQ correctness (use structured fields)**:
   - If `card_type=MCQ`:
     - Verify `options` has exactly 5 items and `correct_index` is within 0–4.
     - Do NOT require options to appear in Front; options belong to the structured field.
     
     - **CRITICAL: Answer-Explanation Consistency**:
       - Verify that the `back` explanation/rationale is **consistent** with the option at `options[correct_index]`
       - The explanation must clearly support why the option at `correct_index` is the correct answer
       - If the explanation contradicts or doesn't match the correct option, this is a **BLOCKING ERROR** (`blocking_error=true`)
       - Output field: `answer_explanation_consistency` (boolean)
       - Issue type: `answer_explanation_mismatch`
     
     - **CRITICAL: Multiple Answer Risk**:
       - Analyze all options to determine if multiple answers could be considered correct
       - Consider differential diagnosis scenarios and whether the question provides sufficient distinguishing information
       - If 2+ options could plausibly be correct based on the question stem, flag as `multiple_answer_risk=true`
       - Output field: `multiple_answer_risk` (boolean)
       - Issue type: `multiple_answer_possible` (severity: "major" or "blocking" if severe)

### Section 4: Difficulty Assessment (NEW)

4. **Difficulty problem detection**:
   - Evaluate whether the question difficulty is appropriate for the 영상의학과 전문의 시험 (Korean Radiology Board Examination) level.
   
   - **Too Easy (difficulty_too_easy)**:
     - Questions that can be solved by pure memorization without clinical reasoning
     - Questions where the answer is directly stated in the question stem
     - Questions testing trivial facts that any medical student would know
     - Example: "석회화는 CT에서 어떤 density로 보이는가?" (고밀도 - 너무 쉬움)
     - Flag as issue type: `difficulty_too_easy` (severity: "minor")
   
   - **Too Difficult (difficulty_too_hard)**:
     - Questions requiring subspecialty-level knowledge beyond general radiology
     - Questions about rare diseases with very low clinical prevalence
     - Questions requiring knowledge not covered in standard radiology training
     - Example: Questions about extremely rare tumor subtypes or esoteric genetic syndromes
     - Example: Deep technical physics questions beyond typical board level
     - Flag as issue type: `difficulty_too_hard` (severity: "minor")
   
   - **Appropriate Difficulty (Reference)**:
     - Should match 2024년 영상의학과 전문의 시험 기출문제 difficulty level
     - Requires integration of imaging findings with clinical context
     - Tests pattern recognition + differential diagnosis reasoning
     - Example: "간의 조영증강 CT에서 동맥기 고음영, 문맥기 저음영의 washout 패턴을 보이는 병변의 가장 가능성 높은 진단은?" (HCC - 적절한 난이도)

### Section 5: Radiology Relevance Assessment (NEW)

5. **Radiology relevance (영상의학과 적합성)**:
   - Verify that the question content is appropriate for radiology specialty examination.
   
   - **Core Radiology Domains (적합)**:
     - 영상 판독 (Image interpretation)
     - 영상의학 물리 (Imaging physics: X-ray, CT, MRI, US principles)
     - 중재적 시술 (Interventional radiology)
     - 조영제 및 안전 (Contrast agents and safety)
     - 방사선 방어 (Radiation protection)
     - 영상 프로토콜 및 최적화 (Imaging protocols and optimization)
     - 해부학 (영상에서 보이는 해부학적 구조)
   
   - **Non-Radiology Content (부적합)**:
     - Pure pathology questions without imaging correlation
     - Internal medicine treatment protocols
     - Surgical technique details
     - Drug pharmacology (except contrast agents)
     - Laboratory test interpretation without imaging context
   
   - **Detection Criteria**:
     - If the question can be answered without any imaging knowledge → flag
     - If the question focuses on treatment rather than diagnosis → flag
     - If the question is about another specialty's core competency → flag
   
   - Flag as issue type: `radiology_relevance_concern` (severity: "minor")
   - Provide description explaining why the content may not be radiology-appropriate

### Section 6: Q2 Cognitive Objective Verification (NEW)

6. **Q2 cognitive objective verification**:
   - This section applies ONLY when `card_role=Q2`.
   - Q2 cards should test different cognitive objectives than Q1 (진단) cards.
   
   - **Q2 Diagnostic Overlap (Q2_DIAGNOSTIC_OVERLAP)**:
     - Q2 should NOT be another diagnostic question if Q1 already tests diagnosis
     - If Q2 asks "가장 가능성 높은 진단은?" or similar diagnostic phrasing → flag
     - Q2 should test: 치료, 예후, 기전, 합병증, 추가검사 등
     - Flag as issue type: `Q2_DIAGNOSTIC_OVERLAP` (severity: "minor")
     - Description: "Q2 appears to test diagnosis, which may overlap with Q1's cognitive objective"
   
   - **Q2 Image Dependency (Q2_IMAGE_DEPENDENCY)**:
     - Q2 questions should be answerable based on the diagnosis/findings established in Q1
     - Q2 should NOT require viewing the image to answer (image is on BACK)
     - If Q2 requires image interpretation to answer → flag
     - Flag as issue type: `Q2_IMAGE_DEPENDENCY` (severity: "minor")
     - Description: "Q2 appears to require image interpretation, which is not accessible during the question"

### Section 7: Issue Listing

7. **List issues**:
   - **MAXIMUM 5 ISSUES**: Report only the most important/severe issues for individual cards.
   - **Concise descriptions**: Keep each description under 150 characters.
   - Use `severity` to reflect impact (`blocking` reserved for clinical safety only).
   - Provide minimal suggested fixes (do not rewrite the entire card).

8. **Actionable metadata (optional but recommended)**:
   - Include `issue_code`, `recommended_fix_target`, and `prompt_patch_hint` when you can point to a systematic upstream fix.

---

## Output

Return a JSON object following the S5 Validation System Prompt format:

```json
{{
  "blocking_error": false,
  "technical_accuracy": 1.0,
  "educational_quality": 4,
  "issues": [
    {{
      "type": "difficulty_too_easy",
      "severity": "minor",
      "description": "Question tests basic memorization without clinical reasoning"
    }},
    {{
      "type": "radiology_relevance_concern",
      "severity": "minor",
      "description": "Question focuses on surgical technique rather than imaging"
    }},
    {{
      "type": "Q2_DIAGNOSTIC_OVERLAP",
      "severity": "minor",
      "description": "Q2 appears to test diagnosis, which may overlap with Q1's cognitive objective"
    }}
  ],
  "rag_evidence": [...],
  "answer_explanation_consistency": true,
  "multiple_answer_risk": false
}}
```

**Note on New Issue Types:**
- `difficulty_too_easy`, `difficulty_too_hard`: Flagged in issues array only (no separate score field)
- `radiology_relevance_concern`: Flagged in issues array only
- `Q2_DIAGNOSTIC_OVERLAP`, `Q2_IMAGE_DEPENDENCY`: Flagged for Q2 cards only

**Critical:** If `blocking_error=true`, you MUST include at least one RAG evidence entry with `relevance="high"`.

---

**Version:** 3.0  
**Last Updated:** 2026-01-05  
**Changes in v3.0 (from v2.0):**
- Added MCQ Answer-Explanation Consistency validation (Section 3)
- Added MCQ Multiple Answer Risk detection (Section 3)
- Added Difficulty Assessment: Too Easy / Too Hard detection (Section 4)
- Added Radiology Relevance Assessment (Section 5)
- Added Q2 Cognitive Objective Verification: Diagnostic Overlap and Image Dependency (Section 6)


