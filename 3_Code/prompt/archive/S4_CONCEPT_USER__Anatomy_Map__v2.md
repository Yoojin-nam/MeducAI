TASK:
Generate a SINGLE 16:9 anatomy-map teaching slide from the master table.

DETERMINISTIC EXPANSION RULES:
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows, render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT:
- Central schematic map + max 6 callouts.
- Others list for additional regions if > 6.

MANDATORY:
- Central anatomy figure (schematic acceptable).
- Callouts with short labels (English terms).
- 1 boxed "시험포인트" (Korean, EXACTLY one short line) for key pitfalls/variants if present.

RULES:
- No invented anatomy beyond table scope.
- Prefer clarity over detail.
- Do NOT render the markdown table as a table.

VISUAL REQUIREMENTS:
- Large fonts, readable when downscaled.
- Clean white background, ample whitespace.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

