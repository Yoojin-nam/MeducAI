# S5 S1 Table + Infographic Validation User Prompt v1.0

**Purpose:** Validate S1 master table AND its associated infographic for medical safety, exam fitness, and educational quality.

---

## Task

Evaluate the following S1 master table AND its infographic for:
1. Technical Accuracy (0/0.5/1.0 scale) - for both table and infographic
2. Educational Quality (1-5 Likert scale) - for table overall
3. **Blocking Errors (clinical safety-critical only)** - for both table and infographic
4. Issues and suggested fixes (actionable, minimal scope)
5. **Infographic-specific evaluation** (information clarity, anatomical accuracy, prompt compliance, table-visual consistency)

---

## Input Data

### Group Information
- **Group ID:** {group_id}
- **Group Path:** {group_path}
- **Objective Bullets:** {objective_bullets}

### Master Table (Markdown)
{master_table_markdown_kr}

### S3 Infographic Prompt (Reference)
**S3 infographic_prompt_en (what the infographic should show):**
{s3_infographic_prompt_en}

### Table Infographic
**Image file:** {infographic_path}

The infographic above should be evaluated together with the master table.

---

## Instructions

### 1. Table Evaluation (Standard)
1. **Clinical safety (blocking)**:
   - Set `blocking_error=true` ONLY if there is a safety-critical medical error that could mislead clinical decisions.
   - If `blocking_error=true`, you MUST set `technical_accuracy=0.0` and provide RAG evidence.
2. **Exam fitness / educational quality (non-blocking)**:
   - Prefer precise, current terminology used in board exams and clinical practice.
   - Flag outdated terminology (non-blocking) and suggest a modern replacement with "formerly …" if needed.
3. **List issues**:
   - Use `row_index` (0-based) and `entity_name` when applicable.
   - Provide minimal suggested fixes (do not rewrite the whole table).
4. **Actionable metadata (optional but recommended)**:
   - For each issue, include:
     - `issue_code` (stable code)
     - `recommended_fix_target` (e.g., `S1_SYSTEM`, `S1_USER_GROUP`, or `S1_TABLE_CONTENT`)
     - `prompt_patch_hint` (1–3 lines; rule-level patch hint)
     - `confidence` (0–1)

### 2. Infographic Evaluation (NEW)
Evaluate the infographic for:

1. **Information Clarity** (`information_clarity`): 1-5 Likert
   - Is the core information from the table clearly conveyed visually?
   - Is the layout organized and easy to read?
   - Is the information hierarchy clear?
   - **CRITICAL: Text/OCR Verification**:
     - Infographics typically contain text (labels, entity names, annotations, measurements, etc.)
     - **Use OCR to extract and read ALL visible text** in the infographic image
     - Verify text accuracy: Are medical terms, entity names, and values spelled correctly?
     - Verify text completeness: Are all entities from the S1 table represented with text labels?
     - Verify text readability: Is all text clear and legible?
     - Compare extracted text with S1 table content to ensure consistency
     - If text is missing, unreadable, or incorrect, flag as appropriate issue type
   - Issue types: `cluttered_layout`, `unclear_hierarchy`, `missing_text`, `unreadable_text`, `text_error`, `text_table_mismatch`

2. **Anatomical Accuracy** (`anatomical_accuracy`): 0.0 | 0.5 | 1.0
   - Are anatomical structures/relationships accurate?
   - Issue types: `anatomical_error`, `relationship_misrepresentation`

3. **Prompt Compliance** (`prompt_compliance`): 0.0 | 0.5 | 1.0
   - Does the infographic match the S3 `infographic_prompt_en` requirements?
   - Are all required elements from the prompt visible?

4. **Table-Visual Consistency** (`table_visual_consistency`): 0.0 | 0.5 | 1.0
   - Does the infographic content match the S1 table?
   - Are all entities from the table represented in the infographic?
   - **CRITICAL: Text-based Verification**:
     - Use OCR to extract entity names and key information from the infographic text
     - Compare extracted entity names with the S1 table entity list
     - Verify that all entities from the table appear in the infographic (either visually or as text labels)
     - If an entity is missing, flag as `entity_missing` issue type
     - If entity names in the infographic don't match the table, flag as `entity_name_mismatch` issue type
   - Issue types: `content_mismatch`, `entity_missing`, `entity_name_mismatch`

### 3. Combined Evaluation
- If infographic has blocking errors (anatomical_accuracy=0.0), this may affect the overall table `blocking_error`.
- If table-visual consistency is low (<0.5), this should be flagged as an issue affecting educational quality.

---

## Output

Return a JSON object with the following structure:

```json
{{
  "blocking_error": false,
  "technical_accuracy": 1.0,
  "educational_quality": 4,
  "issues": [...],
  "rag_evidence": [...],
  "table_visual_validation": {{
    "blocking_error": false,
    "information_clarity": 5,
    "anatomical_accuracy": 1.0,
    "prompt_compliance": 1.0,
    "table_visual_consistency": 1.0,
    "extracted_text": "Entity1: Description1\nEntity2: Description2\n...",
    "entities_found_in_text": ["Entity1", "Entity2", "..."],
    "issues": [
      {{
        "severity": "minor",
        "type": "entity_missing",
        "description": "Entity 'Venous reflux' from table is not shown in infographic",
        "issue_code": "TABLE_VISUAL_ENTITY_MISSING",
        "recommended_fix_target": "S3_PROMPT",
        "prompt_patch_hint": "Ensure all entities from S1 table are represented in infographic.",
        "confidence": 0.8
      }}
    ],
    "image_path": "/path/to/infographic.jpg"
  }}
}}
```

**Critical:** 
- If `blocking_error=true` (table-level), you MUST include at least one RAG evidence entry with `relevance="high"`.
- If `table_visual_validation.blocking_error=true`, include infographic-specific issues with appropriate severity.
- **OCR/Text Extraction**: 
  - Always use OCR to extract ALL visible text from the infographic image
  - Include extracted text in `extracted_text` field (newline-separated or structured format)
  - Extract entity names from the text and list them in `entities_found_in_text` array
  - Compare extracted entities with S1 table entities to verify completeness

---

**Version:** 1.0  
**Last Updated:** 2025-12-28

