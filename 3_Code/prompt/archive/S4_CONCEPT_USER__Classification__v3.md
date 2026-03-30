TASK:
Generate a SINGLE 16:9 classification/taxonomy teaching slide from the master table.

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If > 6 rows: include "Others" list (entity name + 1 keyword; no extra branches).

DESIGN INTENT (MANDATORY):
- One taxonomy/decision-tree block that is readable at a distance.
- Show up to 6 leaves/classes; keep hierarchy shallow (1–2 levels) unless table clearly supports deeper.

MANDATORY VISUAL ANCHOR:
- Each leaf/class SHOULD include a small thumbnail/schematic (radiology-like or pattern icon) that conveys the class.
- At minimum: the overall tree must be a true diagram (not text list). Text-only is a FAIL.

LEAF TEMPLATE (each expanded row as a class/leaf):
- Class/Category name (English, bold)
- ≤ 3 criteria tokens (English; no sentences), preferably labeled:
  - Core criterion: <token>
  - Imaging clue: <token>
  - Pitfall/DDx: <token>
- Optional "시험포인트" (Korean, EXACTLY one short line) ONLY if table-supported.

RULES:
- Do NOT invent thresholds/cutoffs or staging rules unless explicitly present in the table.
- Do NOT render the markdown table as a table.
- Keep it compact and visually structured.

VISUAL REQUIREMENTS:
- Clean white background; dark title bar; large fonts; ample whitespace.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

