TASK:
Generate a SINGLE 16:9 comparison-style radiology teaching slide from the master table.

DETERMINISTIC EXPANSION RULES:
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows, render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT:
- Choose ONE coherent layout; cap expanded items (max 4–6).
- Emphasize differentiator axes; avoid dense text.

MANDATORY LAYOUT OPTIONS (choose ONE that best fits the table):
A) 3-panel vertical split (Left vs Center vs Right).
B) 2×2 comparison grid with consistent panel templates.
C) Aligned comparison rows: each row = one entity, columns = differentiator axes.

EACH PANEL MUST INCLUDE:
- Entity name (English, bold)
- ≤ 3 keywords (English; short phrases; no sentences)
- 1 boxed "시험포인트" (Korean, EXACTLY one short line)

STYLE:
- Clean white background; dark title bar.
- Large fonts, readable when downscaled.
- Do NOT render the markdown table as a table.
- Emphasize visual differentiators (axes, comparison layout).

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

