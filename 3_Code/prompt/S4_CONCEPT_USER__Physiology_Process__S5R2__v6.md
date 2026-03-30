TASK:
Generate a SINGLE 16:9 physiology/process teaching slide from the master table.

NO EMPTY CONTENT RULE (CRITICAL - READ FIRST):
- EVERY text element you output MUST contain meaningful content (at least 4 words).
- NEVER output empty placeholders, "...", or labels followed by nothing.
- NEVER output only modality abbreviations without explanation (e.g., "NM" alone is FORBIDDEN).
- If you cannot fill a text element with meaningful content, OMIT that element entirely.
- "Key takeaways:" section MUST have 4-6 bullets, each with 6-12 words of actual learning content.
- "Explanation:" lines MUST contain actual explanatory phrases (5-10 words), not just abbreviations.
- Stage/step labels MUST be meaningful names or descriptions, not placeholders.

FAIL CONDITIONS (IMMEDIATE REJECTION):
- Empty "Key takeaways:" bullets (just dots without text)
- "Explanation:" lines containing only modality abbreviations (e.g., "Explanation: NM")
- Stage boxes with only abbreviations and no actual content
- Any placeholder text like "...", "TBD", or repeated single tokens
- Process diagram with unlabeled or empty stages
- Visual elements without meaningful labels

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–8 rows from the master table (in table order).
- If table has > 8 rows: render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT (MANDATORY):
- One central process diagram with arrows:
  - Prefer 4–7 stages total.
  - Stage sequence MUST be derived from table order/content ONLY.
- Each stage communicates imaging manifestation/process link visually-first.
- The diagram MUST have labeled stages with meaningful content.

CONTENT EXTRACTION STRATEGY:
- For each stage/entity from the master table, extract:
  1. Stage/Process name (required)
  2. Key mechanism or action (what happens at this stage)
  3. Imaging manifestation if mentioned (modality + finding)
  4. Clinical significance or exam point
- If a row lacks sufficient content:
  - Use entity name as stage label
  - Add a brief descriptive phrase from any available column
  - Include schematic icon representing the concept

TEXT BUDGET (RELAXED FOR EDUCATIONAL VALUE):
- Diagram-first, but allow brief explanatory phrases per stage for clarity when directly supported by the table row.
- Any line of text: 3–6 words per line (max 8-10 words).
- Avoid paragraphs and multi-sentence explanations.

STRUCTURED TEXT (ALLOWED STRUCTURAL LABELS; Zone 2):
- You MAY use the following fixed labels to improve clarity (even if the labels are not in ALLOWED_TEXT):
  - "Stage:"
  - "Key cue:"
  - "Modality:"
  - "Exam point:"
  - "Pitfall:"
  - "Mechanism:"
  - "Finding:"
- All words AFTER these labels MUST still come from ALLOWED_TEXT or master table content and MUST be directly supported by the row content.
- Do NOT introduce any other headers/labels beyond this list.

SCHEMATIC REQUIREMENT (MANDATORY):
- MUST include at least ONE of: flowchart, block diagram, loop diagram, axes chart, process arrows.
- "Text-only slide" is a FAIL condition.
- Each stage/block MUST have a visual icon or schematic representing the concept.

STAGE CONSTRUCTION RULE (STRICT):
- If the table explicitly provides a natural stage sequence, use that sequence.
- Otherwise, map stages to the expanded rows in table order:
  - Stage label: derived from entity name or a short phrase directly supported by the row (ALLOWED as Zone 2 structural label)
  - Stage content: brief descriptive text from table content (5-10 words)

STAGE BOX TEMPLATE:
1. Entity name / Stage label (English, bold; short) - REQUIRED
   - Extract from table "Entity name" column
   - Display as-is, no modification
   - Stage labels are ALLOWED as Zone 2 structural labels (short tokens derived from table wording)

2. Modality keywords (English) - OPTIONAL
   - Extract from the master table imaging-expression / manifestation column if modality is mentioned
   - Format: "CT / MRI" or "CT, MRI"
   - Include ONLY modality names (CT, MRI, X-ray, US, PET, NM, etc.)
   - Maximum 3 modalities per entity
   - If no modality information in table, OMIT this element (do NOT force)

3. Key finding or mechanism (English) - RECOMMENDED
   - 2-5 word phrase describing what happens at this stage
   - Extract from table content (mechanism, finding, or description columns)
   - If not extractable, use a brief description from entity name context

4. Imaging cue token (English) - OPTIONAL
   - 1-2 word English imaging cue token (e.g., "ring enhancement", "hot spot", "uptake pattern")
   - Extract from the master table imaging-expression / manifestation column if an imaging-related cue is mentioned
   - If you cannot confidently extract a 1-2 word cue from that field, OMIT the cue line (do NOT invent)
   - Do NOT prepend labels ("Cue:"). The line should be the token only.

5. Exam-point keywords (English only) - OPTIONAL when non-empty
   - Source: the exam-point column in the master table (English tokens only; do NOT output Korean)
   - If the cell is non-empty but only Korean tokens exist, OMIT (do NOT translate)
   - Format: 1–2 short lines, tokens only (no sentences)
   - Can be added per stage OR as one compact box for the whole slide

Optional tiny schematic icon per stage (encouraged; must not add new facts)

KEY TAKEAWAYS (MANDATORY):
- Add "Key takeaways:" section with 4-6 bullet points.
- Each bullet MUST be 6-12 words of actual educational content derived from the table.
- NEVER leave bullets empty or with only abbreviations.

"OTHERS" SECTION TOKEN SELECTION (DETERMINISTIC):
For each entity in the "Others" section, use this priority list to select ONE token:
1. Exam-point (if present, English only) -> take 1 word (or 1 short phrase ≤ 2 words)
2. else imaging cue token (if extractable from the imaging-expression / manifestation column)
3. else modality name (one modality token)
4. else omit token and list name only (do NOT invent)

TEXT PROHIBITIONS (STRICT):
- DO NOT include long process descriptions or long explanations
- DO NOT include imaging manifestation details beyond modality and cue token
- DO NOT create paragraphs or multi-sentence explanations
- DO NOT add information not present in the table
- DO NOT include numeric thresholds/settings unless present in the exam-point column (strict rule for Physiology_Process)
- DO NOT force modality when absent from table
- DO NOT output empty placeholders or abbreviation-only content

RULES:
- Use ONLY table content. Do NOT invent extra stages, causal links, thresholds, or numeric settings.
- Do NOT render the markdown table as a table.
- Do NOT output markdown (no pipes |, no markdown tables, no code fences, no headings with #, no emphasis markers *, no horizontal rules ---).
- No paragraphs.
- Text per stage: Entity name / Stage label + Modality keywords (if present) + Imaging cue token (if extractable) + optional exam-point keywords (English only; omit if Korean-only; no translation).

VISUAL REQUIREMENTS:
- Large fonts, readable when downscaled.
- Clean white background, ample whitespace.
- Dark title bar with concise title derived from table content.
- Process flow arrows connecting stages.
- Each stage box with icon/schematic + text labels.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Visual Type Category: {visual_type_category}

MASTER ROWS (plain, non-markdown; use ONLY this content):
{table_rows_plain}

OUTPUT:
Return IMAGE ONLY.

