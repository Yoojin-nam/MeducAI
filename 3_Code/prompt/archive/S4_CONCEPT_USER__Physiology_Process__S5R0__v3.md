TASK:
Generate a SINGLE 16:9 physiology/process teaching slide from the master table.

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–8 rows from the master table (in table order).
- If table has > 8 rows: render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT (MANDATORY):
- One central process diagram with arrows:
  - Prefer 4–7 stages total.
  - Stage sequence MUST be derived from table order/content ONLY.
- Each stage communicates imaging manifestation/process link visually-first.

SCHEMATIC REQUIREMENT (MANDATORY):
- MUST include at least ONE of: flowchart, block diagram, loop diagram, axes chart.
- "Text-only slide" is a FAIL condition.

STAGE CONSTRUCTION RULE (STRICT):
- If the table explicitly provides a natural stage sequence, use that sequence.
- Otherwise, map stages to the expanded rows in table order:
  - Stage label: derived from entity name or a short phrase directly supported by the row (ALLOWED as Zone 2 structural label)
  - Stage content: minimal text tokens only

STAGE BOX TEMPLATE:
1. Entity name / Stage label (English, bold; short) - REQUIRED
   - Extract from table "Entity name" column
   - Display as-is, no modification
   - Stage labels are ALLOWED as Zone 2 structural labels (short tokens derived from table wording)

2. Modality keywords (English) - OPTIONAL
   - Extract from table "영상 표현" column if modality mentioned
   - Format: "CT / MRI" or "CT, MRI"
   - Include ONLY modality names (CT, MRI, X-ray, US, PET, etc.)
   - Maximum 3 modalities per entity
   - If no modality information in table, OMIT this element (do NOT force)

3. Imaging cue token (English) - OPTIONAL
   - 1-2 word English imaging cue token (e.g., "ring enhancement", "dural tail", "ground-glass")
   - Extract from table "영상 표현" column if imaging-related cue is mentioned
   - If you cannot confidently extract a 1-2 word cue from that field, OMIT the cue line (do NOT invent)
   - Do NOT prepend labels ("Cue:"). The line should be the token only.

4. 시험포인트 keywords (Korean or English) - MANDATORY when non-empty
   - Extract from table "시험포인트" column
   - If table "시험포인트" cell for an expanded entity is non-empty and not "unknown/unclear", you MUST include 1–2 시험포인트 lines (each 1-3 words, Korean or English)
   - If 시험포인트 is empty/unclear, omit it
   - Format: single line, no sentences
   - Can be added per stage OR as one compact box for the whole slide

Optional tiny schematic icon per stage (allowed; must not add new facts)

"OTHERS" SECTION TOKEN SELECTION (DETERMINISTIC):
For each entity in the "Others" section, use this priority list to select ONE token:
1. 시험포인트 (if present) -> take 1 word (or 1 short phrase ≤ 2 words)
2. else imaging cue token (if extractable from "영상 표현" column)
3. else modality name (one modality token)
4. else omit token and list name only (do NOT invent)

TEXT PROHIBITIONS (STRICT):
- DO NOT include process descriptions or explanations
- DO NOT include imaging manifestation details beyond modality and cue token
- DO NOT create sentences or phrases
- DO NOT add information not present in the table
- DO NOT include numeric thresholds/settings unless present in 시험포인트 (strict rule for Physiology_Process)
- DO NOT force modality when absent from table

RULES:
- Use ONLY table content. Do NOT invent extra stages, causal links, thresholds, or numeric settings.
- Do NOT render the markdown table as a table.
- No paragraphs.
- Text per stage: Entity name / Stage label + Modality keywords (if present) + Imaging cue token (if extractable) + 시험포인트 keywords (mandatory when non-empty).

VISUAL REQUIREMENTS:
- Large fonts, readable when downscaled.
- Clean white background, ample whitespace.
- Dark title bar with concise title.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.
