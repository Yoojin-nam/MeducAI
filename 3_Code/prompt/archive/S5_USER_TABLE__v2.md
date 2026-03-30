# S5 S1 Table Validation User Prompt v2.0 (actionable signals)

**Purpose:** Validate S1 master table for medical safety, exam fitness, and educational quality.

---

## Task

Evaluate the following S1 master table for:
1. Technical Accuracy (0/0.5/1.0 scale)
2. Educational Quality (1-5 Likert scale)
3. **Blocking Errors (clinical safety-critical only)**
4. Issues and suggested fixes (actionable, minimal scope)

---

## Input Data

### Group Information
- **Group ID:** {group_id}
- **Group Path:** {group_path}
- **Objective Bullets:** {objective_bullets}

### Master Table (Markdown)
{master_table_markdown_kr}

---

## Instructions

1. **Clinical safety (blocking)**:
   - Set `blocking_error=true` ONLY if there is a safety-critical medical error that could mislead clinical decisions.
   - If `blocking_error=true`, you MUST set `technical_accuracy=0.0` and provide RAG evidence.
2. **Exam fitness / educational quality (non-blocking)**:
   - Prefer precise, current terminology used in board exams and clinical practice.
   - Flag outdated terminology (non-blocking) and suggest a modern replacement with “formerly …” if needed.
3. **List issues**:
   - Use `row_index` (0-based) and `entity_name` when applicable.
   - Provide minimal suggested fixes (do not rewrite the whole table).
4. **Actionable metadata (optional but recommended)**:
   - For each issue, include:
     - `issue_code` (stable code)
     - `recommended_fix_target` (e.g., `S1_SYSTEM`, `S1_USER_GROUP`, or `S1_TABLE_CONTENT`)
     - `prompt_patch_hint` (1–3 lines; rule-level patch hint)
     - `confidence` (0–1)

---

## Output

Return a JSON object following the S5 Validation System Prompt format.

**Critical:** If `blocking_error=true`, you MUST include at least one RAG evidence entry with `relevance="high"`.

---

**Version:** 2.0  
**Last Updated:** 2025-12-28


