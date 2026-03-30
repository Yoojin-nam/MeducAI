TASK:
Generate a SINGLE 16:9 board-review teaching slide image from the master table below.

SLIDE STRUCTURE (MANDATORY):
1) Top title bar (dark navy/charcoal): concise lecture title derived from group_path or group_title.
2) Optional subtitle (small): "Radiology Board Review" + 1 short Korean phrase (optional).
3) Main content: table-to-grid transformation that preserves the row-wise meaning.

LAYOUT RULES:
- Use a structured grid (e.g., 3×2, 4×2, or aligned rows) depending on the number of entities/rows.
- Each entity should be recognizable in 1–2 seconds.
- For each entity panel include:
  - Entity name (English, bold)
  - 2–4 high-yield imaging keywords (English)
  - 1 boxed "시험포인트" (Korean, one short line)

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

