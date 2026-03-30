TASK:
Generate a SINGLE 16:9 pathology-pattern teaching slide from the master table.

DETERMINISTIC EXPANSION RULES:
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows, render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT:
- Pattern-first pseudo-images/illustrations emphasizing distribution/appearance.
- Grid layout (2×2 or 3×2) for 4–6 expanded panels.

PANEL TEMPLATE (each expanded panel):
- Entity name (English, bold)
- ≤ 3 keywords (English; short phrases; no sentences)
- 1 boxed "시험포인트" (Korean, EXACTLY one short line)
- Pattern-first pseudo-image/illustration emphasizing distribution/appearance (not text-only).

WORD BUDGET:
- Enforce strict word budget: ≤ 3 keywords per panel.
- No paragraphs, no sentences.

VISUAL REQUIREMENTS:
- Large fonts, readable when downscaled.
- Clean white background, ample whitespace.
- Do NOT render the markdown table as a table.
- Transform into grid with pattern illustrations.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

