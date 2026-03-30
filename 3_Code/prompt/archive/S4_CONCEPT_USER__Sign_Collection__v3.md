TASK:
Generate a SINGLE 16:9 "sign collection" teaching slide from the master table.

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows: render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT:
- Uniform grid (max 6 expanded sign cells).
- Each cell is a "sign card": visual-first + minimal tokens.
- Consistent sizing and alignment (2×2, 3×2, or 2×3).

MANDATORY VISUAL ANCHOR (PER CELL):
- Each sign cell MUST include a tiny pseudo-image/icon:
  - schematic (not text-only), showing the sign shape/region/pattern
  - subtle outline/overlay allowed
- "Text-only sign cells" are a FAIL condition.

SIGN CELL TEMPLATE (STRICT):
- Sign / Entity name (English, bold)
- Tiny pseudo-image/icon (schematic, grayscale-like)
- ≤ 2 keywords (English; short phrases; no sentences)
- Optional "시험포인트" (Korean, EXACTLY one short line) ONLY if clearly supported by table content
  - If not supported, OMIT (do NOT hallucinate)

STYLE:
- Clean white background, ample whitespace.
- Large fonts, readable when downscaled.
- Dark title bar with concise title.
- Do NOT render the markdown table as a table.

RULES:
- Use ONLY table content. Do NOT add famous associations unless present in the table.
- No paragraphs.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

