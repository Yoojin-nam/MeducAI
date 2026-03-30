TASK:
Generate a SINGLE 16:9 board-review teaching slide image from the master table below.

DETERMINISTIC EXPANSION RULES:
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows, render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

SLIDE STRUCTURE (MANDATORY):
1) Top title bar (dark navy/charcoal): concise lecture title derived from group_path or group_title.
2) Optional subtitle (small): "Radiology Board Review" + 1 short Korean phrase (optional).
3) Main content: table-to-grid transformation (NOT a markdown table).

LAYOUT RULES:
- Use a structured grid (e.g., 2×2, 2×3, 3×2, or aligned rows) depending on the number of expanded entities (4–6).
- Each expanded entity panel MUST include:
  - Entity name (English, bold)
  - ≤ 3 keywords (English; short phrases; no sentences)
  - 1 boxed "시험포인트" (Korean, EXACTLY one short line)
- Optional small schematic icon/pseudo-image per panel ONLY if it improves recognition.
- If > 6 rows exist, add compact "Others" section (keywords only, no full panels).

VISUAL REQUIREMENTS:
- Large fonts, readable when downscaled.
- Clean white background, ample whitespace.
- Do NOT render the markdown table as a table.
- Transform into diagram/grid/flow.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

