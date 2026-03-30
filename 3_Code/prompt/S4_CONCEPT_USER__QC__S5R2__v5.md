TASK:
Generate a SINGLE 16:9 QC/quality-control teaching slide from the master table.

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–8 rows from the master table (in table order).
- If table has > 8 rows: render remaining entities in a compact "Others" section (entity names + 1 keyword each; no full panels).

DESIGN INTENT (MANDATORY):
- QC must be visual and workflow-based (NOT a text checklist/dashboard).
- Include all of the following, derived ONLY from table content:
  (1) QC loop diagram: Acquire → Measure → Compare → Action (exact tokens, ALLOWED as Zone 2 structural labels)
  (2) Compact metrics panel (keywords only; ranges ONLY if present in table)
  (3) "Failure → Fix" mini-map (tokens only; no invented actions)

TEXT BUDGET (RELAXED FOR EDUCATIONAL VALUE):
- QC is diagram-first, but allow more explanatory text for clarity.
- Any diagram box / metric label / mini-map item: 3–6 words per line (max 8-10 words).
- Boxes may use up to 4-5 short lines if needed (allow brief descriptive phrases).
- Allow 1-2 short explanatory lines per entity when needed for educational value.
- If space is tight, reduce the number of boxes before shrinking fonts.

STYLE SAFETY (QC):
- Do NOT use real CT/MRI/US/X-ray screenshots, PACS/DICOM overlays, monitor photos, or futuristic HUD UI.
- Use flat-tone schematic icons/plots/diagrams only.

SCHEMATIC REQUIREMENT (MANDATORY):
- MUST include at least ONE of: flowchart, block diagram, loop diagram, axes chart.
- "Text-only slide" is a FAIL condition.

MANDATORY VISUAL ANCHORS (STRICT):
- QC loop diagram is REQUIRED (central).
- Add at least one additional visual anchor beyond the loop:
  - Recommended: a schematic control chart / trend plot with labeled lines
    (e.g., Target / Upper limit / Lower limit) WITHOUT any numeric values unless present in table.
  - Or a phantom/artifact schematic if explicitly supported by table content.
- No bullet-only dashboards.

QC ITEM CALLOUTS (OPTIONAL, only if space permits):
- For each expanded row, you may add a small callout anchored to either the loop step or the chart:
  1. Entity name (English, bold) - REQUIRED
     - Extract from table "Entity name" column
     - Display as-is, no modification

  2. Modality keywords (English) - OPTIONAL
     - Extract from table if modality mentioned
     - Format: "CT / MRI" or "CT, MRI"
     - Include ONLY modality names (CT, MRI, X-ray, US, PET, etc.)
     - Maximum 3 modalities per entity
     - If no modality information in table, OMIT this element (do NOT force)

  3. Imaging cue token (English) - OPTIONAL
     - 1-2 word English imaging cue token
     - Extract from table if imaging-related cue is mentioned
     - If you cannot confidently extract a 1-2 word cue, OMIT the cue line (do NOT invent)
     - Do NOT prepend labels ("Cue:"). The line should be the token only.

4. Exam-point keywords (English only) - OPTIONAL when non-empty
     - Source: the exam-point column in the master table (English tokens only; do NOT output Korean)
     - If the cell is non-empty but only Korean tokens exist, OMIT (do NOT translate)
     - Format: 1–2 short lines, tokens only (no sentences)

NUMERIC TOKENS (QC-SPECIFIC RELAXATION):
- For QC category ONLY: numeric tokens/thresholds/settings MAY appear if and only if they appear anywhere in the master table row content for that entity (not only in the exam-point column).
- Still prohibit explanatory sentences around them.
- Do NOT invent numeric values.

"OTHERS" SECTION TOKEN SELECTION (DETERMINISTIC):
For each entity in the "Others" section, use this priority list to select ONE token:
1. Exam-point (if present, English only) -> take 1 word (or 1 short phrase ≤ 2 words)
2. else imaging cue token (if extractable from table)
3. else modality name (one modality token)
4. else omit token and list name only (do NOT invent)

TEXT PROHIBITIONS (RELAXED):
- Field labels like "Metric/Focus:", "Failure mode:", "Action:" are ALLOWED when they improve clarity.
- Allow brief QC descriptions or explanations IN ENGLISH (1-2 short lines per entity, ≤ 8-10 words per line).
- DO NOT create long paragraphs or multi-sentence explanations (keep concise).
- DO NOT add information not present in the table
- DO NOT force modality when absent from table
- DO NOT invent numeric values

RULES:
- Use ONLY table content. No invented thresholds/ranges/numbers (except numeric relaxation as defined above).
- Do NOT render the markdown table as a table.
- Do NOT output markdown (no pipes |, no markdown tables, no code fences, no headings with #, no emphasis markers *, no horizontal rules ---).
- Text per callout: Entity name + Modality keywords (if present) + Imaging cue token (if extractable) + optional exam-point keywords (English only; omit if Korean-only; no translation).

VISUAL REQUIREMENTS:
- Large fonts, readable when downscaled.
- Clean white background, ample whitespace.
- Dark title bar with concise title.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Visual Type Category: {visual_type_category}

MASTER ROWS (plain, non-markdown; use ONLY this content):
{table_rows_plain}

OUTPUT:
Return IMAGE ONLY.
