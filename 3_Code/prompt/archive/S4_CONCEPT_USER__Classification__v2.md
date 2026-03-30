TASK:
Generate a SINGLE 16:9 classification-style radiology teaching slide from the master table.

DETERMINISTIC EXPANSION RULES:
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows, render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT (MANDATORY):
- Mandatory decision tree/taxonomy diagram.
- Cap to max 6 leaf nodes shown; rest in Others section.

MANDATORY ELEMENTS:
- Title bar.
- Main: one structured classification block:
  - Category/Grade name (English, bold)
  - Key criteria keywords (English, ≤ 3 keywords per category)
  - "시험포인트" (Korean, EXACTLY one short line) per category or one global box

VISUAL REQUIREMENT:
- Decision tree/taxonomy diagram (flowchart style preferred).
- Large fonts, readable when downscaled.
- Clean white background, ample whitespace.
- Do NOT render the markdown table as a table.

RULES:
- Do NOT invent thresholds/cutoffs not explicitly present in the table.
- Keep it readable from a distance.
- Use ONLY table content.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

