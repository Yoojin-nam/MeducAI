# S5R1 — S5 S2 Card Validation User Prompt v2.0 (Anki MCQ-aware)

**Purpose:** Validate S2 Anki card for medical safety, exam fitness, and educational quality.

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

**Important:** For Anki MCQ cards, the multiple-choice options are stored in structured JSON fields and may NOT appear in the Front text. Do NOT flag “options missing in Front” as an issue if options are provided below.

**Options (A–E, if MCQ):**
{card_options}

**Correct index (0–4, if MCQ):**
{correct_index}

### Entity Context (from S1 table; read-only)
{entity_context}

---

## Instructions

1. **Clinical safety (blocking)**:
   - Set `blocking_error=true` ONLY if there is a safety-critical medical error that could mislead clinical decisions.
   - If `blocking_error=true`, you MUST set `technical_accuracy=0.0` and provide RAG evidence.
2. **Exam fitness / board-style quality (non-blocking)**:
   - Assess clarity, fairness (single best answer), distractor quality, alignment with typical board expectations.
3. **MCQ correctness (use structured fields)**:
   - If `card_type=MCQ`:
     - Verify `options` has exactly 5 items and `correct_index` is within 0–4.
     - Verify the explanation/rationale is consistent with the correct option.
     - Do NOT require options to appear in Front; options belong to the structured field.
4. **List issues**:
   - Use `severity` to reflect impact (`blocking` reserved for clinical safety only).
   - Provide minimal suggested fixes (do not rewrite the entire card).
5. **Actionable metadata (optional but recommended)**:
   - Include `issue_code`, `recommended_fix_target`, and `prompt_patch_hint` when you can point to a systematic upstream fix.

---

## Output

Return a JSON object following the S5 Validation System Prompt format.

**Critical:** If `blocking_error=true`, you MUST include at least one RAG evidence entry with `relevance="high"`.

---

**Version:** 2.0  
**Last Updated:** 2025-12-28


