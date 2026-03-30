TASK:
Generate a SINGLE 16:9 algorithm/flowchart-style radiology teaching slide from the master table.

DETERMINISTIC EXPANSION RULES:
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows, render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT (MANDATORY):
- Mandatory pipeline: Input → Steps(3–6) → Output.
- Each step ≤ 2 tokens.
- One "common pitfall" exam box (Korean one-liner).

SCHEMATIC REQUIREMENT:
- MUST include at least ONE of: (1) flowchart, (2) block diagram, (3) loop diagram, (4) axes chart.
- "Text-only slide" is a FAIL condition.

MANDATORY ELEMENTS:
- Title bar: "How to approach …" style (or similar).
- Stepwise diagnostic approach (3–6 steps).
- Central vertical dotted line or left-to-right flow; numbered steps.
- Each step: Step title (Korean + English in parentheses allowed, but keep short) + 1–2 branching criteria keywords (English).
- End with a small "시험포인트" box (Korean one-liner).

RULES:
- Use ONLY the table content to populate step titles/criteria.
- Do NOT invent extra steps beyond what can be justified by the table columns.
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

