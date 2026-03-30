TASK:
Generate a SINGLE 16:9 algorithm/flowchart-style radiology teaching slide from the master table.

DESIGN INTENT (match "6-step guide" style):
- A stepwise diagnostic approach (4–8 steps).
- Minimal icons per step (simple line icons).
- A central vertical dotted line or left-to-right flow; numbered steps.

MANDATORY ELEMENTS:
- Title bar: "How to approach …" style.
- Steps must be short:
  - Step title (Korean + English in parentheses allowed, but keep short)
  - 1–2 branching criteria keywords (English)
- End with a small "시험포인트" box (Korean one-liners).

RULES:
- Use ONLY the table content to populate step titles/criteria.
- Do NOT invent extra steps beyond what can be justified by the table columns.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

