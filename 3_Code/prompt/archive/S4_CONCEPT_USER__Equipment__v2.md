TASK:
Generate a SINGLE 16:9 equipment-focused radiology teaching slide from the master table.

DETERMINISTIC EXPANSION RULES:
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows, render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT (MANDATORY):
- Mandatory labeled block diagram of components.
- Add "artifact/limitation → mitigation" mini-map (tokens/keywords).
- Do not hallucinate numeric settings.

SCHEMATIC REQUIREMENT:
- MUST include at least ONE of: (1) flowchart, (2) block diagram, (3) loop diagram, (4) axes chart.
- "Text-only slide" is a FAIL condition.

MANDATORY:
- A labeled schematic block diagram (English component names).
- A small "시험포인트" box (Korean, EXACTLY one short line) with a common pitfall.
- Compact "artifact/limitation → mitigation" mini-map (short tokens/keywords).

RULES:
- Do NOT invent parameter values not in the table.
- Use ONLY table content.
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

