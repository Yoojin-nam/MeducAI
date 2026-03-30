# S5 S1 Table Validation User Prompt v1.0

**Purpose:** Validate S1 master table for medical accuracy and educational quality

---

## Task

Evaluate the following S1 master table for:
1. Technical Accuracy (0/0.5/1.0 scale)
2. Educational Quality (1-5 Likert scale)
3. Blocking Errors (if any)
4. Issues and suggested fixes

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

1. **Review the master table** for medical accuracy, alignment with objectives, and educational value
2. **Identify any blocking errors** (Technical Accuracy = 0.0)
3. **Assess overall quality** (Educational Quality 1-5)
4. **List specific issues** with severity, type, description, and suggested fixes
5. **Cite RAG evidence** if blocking errors are identified

---

## Output

Return a JSON object following the S5 Validation System Prompt format:

```json
{
  "blocking_error": boolean,
  "technical_accuracy": 0.0 | 0.5 | 1.0,
  "educational_quality": 1 | 2 | 3 | 4 | 5,
  "issues": [
    {
      "severity": "blocking" | "minor" | "warning",
      "type": string (e.g., "factual_error", "ambiguity", "scope_mismatch", "information_density"),
      "description": string,
      "row_index": integer (optional, 0-based index of table row),
      "entity_name": string (optional, entity name from table row),
      "suggested_fix": string (optional)
    }
  ],
  "rag_evidence": [
    {
      "source_id": string,
      "source_excerpt": string (max 500 chars),
      "relevance": "high" | "medium" | "low"
    }
  ]
}
```

**Critical:** If `blocking_error=true`, you MUST include at least one RAG evidence entry with `relevance="high"`.

---

**Version:** 1.0  
**Last Updated:** 2025-12-26

