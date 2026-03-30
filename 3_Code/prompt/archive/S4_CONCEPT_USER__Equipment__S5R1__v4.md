TASK:
Generate a SINGLE 16:9 equipment-focused radiology teaching slide from the master table.

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–8 rows from the master table (in table order).
- If > 8 rows: "Others" list (entity name + 1 keyword; no extra modules).

DESIGN INTENT (MANDATORY):
- Large labeled block diagram of the system/components (center).
- Add a compact "artifact/limitation → mitigation" mini-map (tokens only).
- No hallucinated numeric settings.

TEXT BUDGET (RELAXED FOR EDUCATIONAL VALUE):
- Equipment is schematic-first, but allow more explanatory text for clarity.
- Any component block label / mini-map token: 3–6 words per line (max 8-10 words).
- Blocks may use up to 4-5 short lines if needed (allow brief descriptive phrases).
- Allow 1-2 short explanatory lines per entity when needed for educational value.
- If space is tight, reduce the number of labeled blocks before shrinking fonts.

STYLE SAFETY (EQUIPMENT):
- Do NOT use photorealistic device photos or 3D product renders (CT gantry, MRI scanner, etc.).
- Do NOT use UI screenshots or futuristic HUD overlays.
- Use flat-tone block diagrams + simple icons only.

SCHEMATIC REQUIREMENT (MANDATORY):
- MUST include at least ONE diagram: block diagram / flowchart / loop diagram / axes chart.
- Text-only slide is a FAIL.

MANDATORY VISUAL ANCHOR:
- Central block diagram is REQUIRED.
- Additionally, include at least one small "artifact thumbnail/schematic" to visually show an artifact/limitation (no text-only).

COMPONENT LABELING:
1. Entity name (English, bold) - REQUIRED
   - Extract from table "Entity name" column
   - Display as-is, no modification

2. Component block labels (English, short) - ALLOWED as Zone 2 structural labels
   - Derived from entity names/table wording (1-3 word English tokens)
   - Use arrows for signal/energy/data flow if applicable (no invented parameters)

3. Modality keywords (English) - OPTIONAL
   - Extract from table if modality mentioned
   - Format: "CT / MRI" or "CT, MRI"
   - Include ONLY modality names (CT, MRI, X-ray, US, PET, etc.)
   - Maximum 3 modalities per entity
   - If no modality information in table, OMIT this element (do NOT force)

4. Imaging cue token (English) - OPTIONAL
   - 1-2 word English imaging cue token
   - Extract from table if imaging-related cue is mentioned
   - If you cannot confidently extract a 1-2 word cue, OMIT the cue line (do NOT invent)
   - Do NOT prepend labels ("Cue:"). The line should be the token only.

5. 시험포인트 keywords (Korean or English) - MANDATORY when non-empty
   - Extract from table "시험포인트" column
   - If table "시험포인트" cell for this entity is non-empty and not "unknown/unclear", you MUST include 1–2 시험포인트 lines (each 1-3 words, Korean or English)
   - If 시험포인트 is empty/unclear, omit it
   - Format: single line, no sentences

NUMERIC TOKENS (EQUIPMENT-SPECIFIC RELAXATION):
- For Equipment category ONLY: numeric tokens/thresholds/settings MAY appear if and only if they appear anywhere in the master table row content for that entity (not only in 시험포인트).
- Still prohibit explanatory sentences around them.
- Do NOT invent numeric values.

"OTHERS" SECTION TOKEN SELECTION (DETERMINISTIC):
For each entity in the "Others" section, use this priority list to select ONE token:
1. 시험포인트 (if present) -> take 1 word (or 1 short phrase ≤ 2 words)
2. else imaging cue token (if extractable from table)
3. else modality name (one modality token)
4. else omit token and list name only (do NOT invent)

TEXT PROHIBITIONS (RELAXED):
- Allow brief equipment descriptions or explanations IN ENGLISH (1-2 short lines per entity, ≤ 8-10 words per line).
- DO NOT create long paragraphs or multi-sentence explanations (keep concise).
- Field labels like "Component:", "Function:", "Limitation:" are ALLOWED when they improve clarity.
- DO NOT add information not present in the table
- DO NOT force modality when absent from table
- DO NOT invent numeric values

RULES:
- Use ONLY table content; no invented artifacts, no fabricated parameter values (except numeric relaxation as defined above).
- Do NOT render the markdown table as a table.
- Text per component: Entity name + Component block labels (Zone 2) + Modality keywords (if present) + Imaging cue token (if extractable) + 시험포인트 keywords (mandatory when non-empty).

VISUAL REQUIREMENTS:
- Clean white background; dark title bar; large fonts; ample whitespace.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.
