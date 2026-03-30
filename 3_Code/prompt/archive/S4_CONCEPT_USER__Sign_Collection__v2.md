TASK:
Generate a SINGLE 16:9 "sign collection" teaching slide from the master table.

DETERMINISTIC EXPANSION RULES:
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows, render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT:
- Uniform grid (max 6 expanded items).
- Each cell: sign name + tiny pseudo-image + ≤ 2 keywords + one-line 시험포인트.

EACH SIGN CELL MUST INCLUDE:
- Sign name (English, bold)
- Tiny pseudo-image/icon (schematic, not text-only)
- ≤ 2 keywords (English; short phrases)
- 1 "시험포인트" (Korean, EXACTLY one short line)

STYLE:
- Uniform grid (2×2, 2×3, or 3×2); consistent sizing.
- Large fonts, readable when downscaled.
- Clean white background, ample whitespace.
- Do NOT render the markdown table as a table.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

