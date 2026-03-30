TASK:
Generate a SINGLE 16:9 classification-style radiology teaching slide from the master table.

DESIGN INTENT:
- Show a clear taxonomy/grades/classes with boundaries and exam-relevant cutoffs IF present in the table.
- Prefer ladder/tiers or a clean classification table.

MANDATORY ELEMENTS:
- Title bar.
- Main: one structured classification block:
  - Category/Grade name (English)
  - Key criteria keywords (English)
  - "시험포인트" (Korean one-liner)

RULES:
- Do NOT invent thresholds/cutoffs not explicitly present in the table.
- Keep it readable from a distance.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

