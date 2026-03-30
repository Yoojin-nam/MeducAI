TASK:
Generate a SINGLE 16:9 QC/quality-control teaching slide from the master table.

DETERMINISTIC EXPANSION RULES:
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows, render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT (MANDATORY):
- Mandatory QC loop diagram: Acquire → Measure → Compare → Action (ONLY table content).
- Add compact metrics panel (keywords only; ranges only if provided in table).
- Add "failure → fix" mini-map (tokens/keywords).
- No bullet-only dashboards.

SCHEMATIC REQUIREMENT:
- MUST include at least ONE of: (1) flowchart, (2) block diagram, (3) loop diagram, (4) axes chart.
- "Text-only slide" is a FAIL condition.

MANDATORY ELEMENTS:
- QC loop diagram (flowchart/block diagram style).
- Compact metrics panel (keywords only).
- "failure → fix" mini-map (short tokens).
- "시험포인트" box (Korean one-liner) if relevant.

RULES:
- Use ONLY table content. No invented thresholds/ranges.
- Do NOT render the markdown table as a table.
- If numbers/ranges are not in the table, DO NOT invent them.

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

