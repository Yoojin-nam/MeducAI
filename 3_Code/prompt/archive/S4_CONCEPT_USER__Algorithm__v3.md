TASK:
Generate a SINGLE 16:9 algorithm/flowchart-style radiology teaching slide from the master table.

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If > 6 rows: compact "Others" list (entity name + 1 keyword; no full nodes).

DESIGN INTENT (MANDATORY):
- One clear pipeline: Input → Steps (3–6) → Output.
- Prefer left-to-right flow with numbered steps.
- Branching is allowed ONLY if justified by table-provided criteria.

SCHEMATIC REQUIREMENT (MANDATORY):
- MUST include a flowchart/block diagram/loop diagram/axes chart.
- Text-only slide is a FAIL.

STEP BUDGET:
- Each step: ≤ 2 tokens (English preferred; short Korean allowed only for step title).
- No paragraphs; no sentences.

NODE TEMPLATE:
- Step title (short; Korean allowed with English in parentheses if needed)
- Criteria tokens (English; 1–2 tokens)
- Optional small thumbnail/schematic icon that conveys the imaging decision (recommended, not decorative)

EXAM TIP:
- Optional "시험포인트" box (Korean, EXACTLY one short line) ONLY if the table supports a specific pitfall/pearl.
- If not clearly supported, OMIT (do NOT hallucinate).

RULES:
- Use ONLY table content; do NOT invent extra steps, thresholds, or decision rules.
- Do NOT render the markdown table as a table.

VISUAL REQUIREMENTS:
- Clean white background; dark title bar; large fonts; generous whitespace.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.

