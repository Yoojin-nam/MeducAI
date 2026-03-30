TASK:
Generate a SINGLE 16:9 equipment-focused radiology teaching slide from the master table.

LEAK + LAYOUT SAFETY (MANDATORY):
- Do NOT output any taxonomy/breadcrumb/group-path text (no subtitles with paths; no metadata-like tokens).
- Korean rule (STRICT, LIMITED):
  - Title / headers / entity-name lines / takeaways MUST be English-only (no Korean/Hangul).
  - Korean is allowed ONLY inside "Explanation:" lines, and ONLY by COPYING EXACT KR snippets from ENTITY_ROW_TEXT_BY_ENTITY for the matching entity (no translation, no rewriting).
- Enforce the SYSTEM no-clipping / safe-area rules: keep all text inside safe margins, no overlap, no cut-off.
- If space is tight, reduce the number of labeled blocks before shrinking fonts; drop OPTIONAL mini-map/extra lines before shrinking; move overflow into "Others".

RICHER EXPLANATION + SUMMARY (MANDATORY):
- For Equipment, include richer explanatory text for educational clarity, while staying compact and auto-fit safe:
  - Target 2–4 short text lines per component/callout (excluding the entity name line).
  - Include 1–2 short "Explanation:" lines derived ONLY from that row's master-table wording (no invented components, no invented functions).
  - If space is tight, drop the 2nd explanation line first.
- Add a slide-level "Key takeaways:" section with 5–8 short bullet lines derived ONLY from the table.
- English text MUST be composed ONLY from ALLOWED_TEXT (English list).
- Korean text is OPTIONAL and allowed ONLY inside "Explanation:" lines, and ONLY if copied EXACTLY from ENTITY_ROW_TEXT_BY_ENTITY (KR list) for the matching entity.

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–8 rows from the master table (in table order).
- If the table has more than 8 rows: "Others" list (entity name + 1 keyword; no extra modules).

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

5. Exam-point keywords (English only) - OPTIONAL when non-empty
   - Source: the exam-point column in the master table (English tokens only; do NOT output Korean)
   - If the cell is non-empty but only Korean tokens exist, OMIT (do NOT translate)
   - Format: 1–2 short lines, tokens only (no sentences)

NUMERIC TOKENS (EQUIPMENT-SPECIFIC RELAXATION):
- For Equipment category ONLY: numeric tokens/thresholds/settings MAY appear if and only if they appear anywhere in the master table row content for that entity (not only in the exam-point column).
- Still prohibit explanatory sentences around them.
- Do NOT invent numeric values.

"OTHERS" SECTION TOKEN SELECTION (DETERMINISTIC):
For each entity in the "Others" section, use this priority list to select ONE token:
1. Exam-point (if present, English only): take 1 word (or 1 short phrase ≤ 2 words)
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
- Do NOT output markdown (no pipes |, no markdown tables, no code fences, no headings with #, no emphasis markers *, no horizontal rules ---).
- Text per component: Entity name + Component block labels (Zone 2) + Modality keywords (if present) + Imaging cue token (if extractable) + optional exam-point keywords (English only; omit if Korean-only; no translation).
- Korean (if used) must be an exact copy-only snippet from ENTITY_ROW_TEXT_BY_ENTITY for that entity, and only inside "Explanation:" lines.

VISUAL REQUIREMENTS:
- Clean white background; dark title bar; large fonts; ample whitespace.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Visual Type Category: {visual_type_category}

MASTER ROWS (plain, non-markdown; use ONLY this content):
{table_rows_plain}

OUTPUT:
Return IMAGE ONLY.
