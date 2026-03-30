TASK:
Generate a SINGLE 16:9 comparison-style radiology teaching slide from the master table.

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows: include an "Others" list (entity name + 1 keyword; no full panels).

DESIGN INTENT (MANDATORY):
- Make differentiators visual-first (thumbnail/schematic + axis-style comparison).
- Choose ONE coherent comparison layout and keep it consistent across entities.

LAYOUT OPTIONS (choose ONE that best fits the table):
A) 2×2 grid (best for 4)
B) 3×2 grid (best for 5–6)
C) Aligned rows: each row = one entity; columns = 2–3 differentiator axes

MANDATORY VISUAL ANCHOR (PER PANEL/ROW):
- Each expanded entity MUST include at least one radiology-like grayscale thumbnail OR a clean schematic that conveys its distinguishing pattern.
- Text-only comparison is a FAIL.

PANEL/ROW TEMPLATE (each expanded entity):
- Entity name (English, bold)
- Visual anchor (thumbnail/schematic) with subtle highlight (outline/overlay) only
- ≤ 3 short tokens total (English; no sentences), preferably as labeled fields:
  - Key pattern: <token>
  - Distribution / Location: <token>
  - Differentiator: <token>
- Optional "시험포인트" (Korean, EXACTLY one short line) ONLY if table-supported; otherwise omit.

RULES:
- Use ONLY table content (no invented criteria, no fabricated "classic" differences unless stated).
- Do NOT render the markdown table as a table.
- Keep readable when downscaled; avoid dense text.

VISUAL REQUIREMENTS:
- Clean white background; dark title bar; ample whitespace.
- Simple axis markers or small comparison bars are allowed (without invented numbers).

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

