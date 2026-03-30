# S5 S2 Card Validation User Prompt v1.0

**Purpose:** Validate S2 Anki card for medical accuracy and educational quality

---

## Task

Evaluate the following S2 Anki card for:
1. Technical Accuracy (0/0.5/1.0 scale)
2. Educational Quality (1-5 Likert scale)
3. Blocking Errors (if any)
4. Issues and suggested fixes

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

### Entity Context (from S1 table)
{entity_context}

---

## Instructions

1. **Review the card** for medical accuracy, clarity, and educational value
2. **Check alignment** with entity context from S1 table
3. **Identify any blocking errors** (Technical Accuracy = 0.0)
4. **Assess overall quality** (Educational Quality 1-5)
5. **List specific issues** with severity, type, description, and suggested fixes
6. **Cite RAG evidence** if blocking errors are identified

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
      "type": string (e.g., "factual_error", "ambiguity", "structure_quality", "image_dependency"),
      "description": string,
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

