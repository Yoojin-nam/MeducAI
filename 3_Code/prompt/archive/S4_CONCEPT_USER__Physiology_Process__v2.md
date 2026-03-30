TASK:
Generate a SINGLE 16:9 physiology/process slide from the master table.

DETERMINISTIC EXPANSION RULES:
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows, render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT (MANDATORY):
- Mandatory 4–7 stage arrow flow diagram.
- Stages MUST be derived from table order/content.
- Each stage: ≤ 2 tokens for imaging manifestation.

MANDATORY ELEMENTS:
- Central flow diagram with arrows connecting stages (flowchart style).
- Stage boxes with stage name (English, bold) + ≤ 2 imaging manifestation keywords.
- One compact "exam pitfalls" box for the whole slide (≤ 3 lines total, Korean).

SCHEMATIC REQUIREMENT:
- MUST include at least ONE of: (1) flowchart, (2) block diagram, (3) loop diagram, (4) axes chart.
- "Text-only slide" is a FAIL condition.

RULES:
- Use ONLY table content to justify stages/sequence.
- Do NOT invent extra stages beyond what can be justified by the table.
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

