TASK:
Generate a SINGLE 16:9 pathology-pattern teaching slide from the master table.

LEAK + LAYOUT SAFETY (MANDATORY):
- Do NOT output any taxonomy/breadcrumb/group-path text (no subtitles with paths; no metadata-like tokens).
- Korean rule (STRICT, LIMITED):
  - Title / headers / entity-name lines / takeaways MUST be English-only (no Korean/Hangul).
  - Korean is allowed ONLY inside "Explanation:" lines, and ONLY by COPYING EXACT KR snippets from ENTITY_ROW_TEXT_BY_ENTITY for the matching entity (no translation, no rewriting).
- Enforce the SYSTEM no-clipping / safe-area rules: keep all text inside safe margins, no overlap, no cut-off.
- If space is tight, reduce the number of cards before shrinking fonts; drop OPTIONAL glyphs/legend/extra lines before shrinking; move overflow into "Others".

RICHER EXPLANATION + SUMMARY (MANDATORY):
- Each Pattern Card must include richer explanatory text while staying compact:
  - Target 2–4 short text lines per card (excluding the entity name line).
  - Include 1–2 short "Explanation:" lines derived ONLY from that row's master-table wording (no invented findings).
  - If space is tight, drop the 2nd explanation line first.
- Add a slide-level "Key takeaways:" section with 5–8 short bullet lines derived ONLY from the table.
- English text MUST be composed ONLY from ALLOWED_TEXT (English list).
- Korean text is OPTIONAL and allowed ONLY inside "Explanation:" lines, and ONLY if copied EXACTLY from ENTITY_ROW_TEXT_BY_ENTITY (KR list) for the matching entity.

DETERMINISTIC EXPANSION RULES:
- Expand ONLY the first 4–8 rows from the master table (in table order).
- If the table has more than 8 rows:
  - Render remaining entities in a compact "Others" section (entity name + 1 keyword each; no full panels).

DESIGN INTENT (NotebookLM-like lecture slide quality):
- Pattern-first visualization: show distribution/appearance as the PRIMARY information channel.
- Use illustrated grayscale thumbnails or clean pattern schematics (NOT text-only, NOT real scan screenshots).
- Clean 2×2 (preferred for 4) or 3×2 grid (for 5–6) or 4×2 grid (for 7–8) with generous whitespace.
- Increase study-utility density via visual structure (icons, micro-schematics); keep any extra label words limited to the allowed Zone 2 structural labels.
- Do NOT add section headers like "Pearls/Pitfalls/Differential" (not allowed for this category).

TEXT BUDGET (RELAXED FOR EDUCATIONAL VALUE):
- Pattern-first (visual), but allow brief explanatory phrases for clarity when directly supported by the table row.
- Any line of text: 3–6 words per line (max 8-10 words).
- Avoid paragraphs and multi-sentence explanations.

STRUCTURED TOKEN STACK (ALLOWED STRUCTURAL LABELS; Zone 2):
- You MAY use the following fixed labels to improve clarity (even if the labels are not in ALLOWED_TEXT):
  - "Distribution:"
  - "Appearance:"
  - "Key sign:"
  - "Modality:"
  - "Exam point:"
  - "Pitfall:"
- All words AFTER these labels MUST still come from ALLOWED_TEXT and MUST be directly supported by the row content.
- Do NOT introduce any other headers/labels beyond this list.

EXPLANATION LINE GRAMMAR (MANDATORY):
- After the token stack, add:
  - "Explanation:" + 1 short phrase line (REQUIRED)
  - Optional 2nd "Explanation:" line (ONLY if space permits)
- Keep each explanation phrase short (≤ 6–10 words) and directly supported by the row content.

LAYOUT (RECOMMENDED):
1) Top title bar:
   - Title: short, exam-oriented (use words from entity names / table wording only; do NOT use taxonomy strings or group paths)
   - Subtitle: OMIT (do not output taxonomy/group paths)
2) Main grid:
   - 4–8 "Pattern Cards" (expanded panels)
3) Optional micro-legend (NO TEXT):
   - If space permits, add a small icon-only legend showing ★ and ⚠ meaning.
4) "Others" list (if needed):
   - Small font list: entity name + 1 keyword each.

PATTERN CARD TEMPLATE (each expanded panel):
1. Entity name (English, bold) - REQUIRED
   - Extract from table "Entity name" column
   - Display as-is, no modification

2. Modality keywords (English) - REQUIRED if present in table
   - Extract from the master table imaging-finding / modality-cue columns
   - Format: "CT / MRI" or "CT, MRI" (use "/" or "," separator)
   - Include ONLY modality names (CT, MRI, X-ray, US, PET, etc.)
   - Maximum 3 modalities per entity
   - If no modality information in table, OMIT this element (do NOT force)

3. Imaging cue token (English) - OPTIONAL
   - 1-2 word English imaging cue token (e.g., "ring enhancement", "dural tail", "ground-glass")
   - Extract from the master table imaging-finding / modality-cue columns
   - If you cannot confidently extract a 1-2 word cue from that field, OMIT the cue line (do NOT invent)
   - Do NOT prepend labels ("Cue:"). The line should be the token only.

4. Optional 2nd imaging cue token (English) - OPTIONAL (HIGH-YIELD BOOST)
   - Only if the table row clearly contains TWO distinct short cue tokens
   - Same extraction source as above
   - 1-2 words only; omit if not confidently extractable (do NOT invent)
   - No labels; token only

5. Exam-point keywords (English only) - OPTIONAL when non-empty
   - Source: the exam-point column in the master table (English tokens only; do NOT output Korean)
   - If the cell is non-empty but only Korean tokens exist, OMIT (do NOT translate)
   - Format: 1–2 short lines, tokens only (no sentences)

Visual anchor (MANDATORY):
- At least one illustrated grayscale thumbnail OR a simplified schematic mimicking radiology contrast.
- The anchor MUST be schematic/illustrated (flat tones, simple shapes), NOT a real CT/MRI/X-ray/US scan screenshot and NOT a monitor/UI image.
- The thumbnail/schematic must express:
  - distribution (where),
  - appearance (what it looks like),
  - key sign (recognizable shape/pattern),
  using subtle highlights (outline/overlay) only.

PATTERN DENSITY BOOST (MANDATORY VISUAL SUBSTRUCTURE, NO EXTRA TEXT):
- Inside each Pattern Card, add 2–3 tiny pattern glyphs (icon-only) next to/under the thumbnail:
  - A small abstract distribution map (e.g., rim/central/peripheral/segmental) using simple geometry
  - A simple shape cue (e.g., ring / tail / nodules) as an icon
  - Optional contrast cue (light/dark blocks) to hint at signal/intensity WITHOUT labels or numbers
- These glyphs must be generic and non-misleading; if unsure, omit glyphs rather than guessing.

ICON-CODED EMPHASIS (OPTIONAL, NO TEXT LABELS):
- If two exam-point lines exist:
  - Render line 1 inside a small ★ badge (high-yield recall)
  - Render line 2 inside a small ⚠ badge (pitfall/trap)
- If only one exam-point line exists: use ★ only.

"OTHERS" SECTION TOKEN SELECTION (DETERMINISTIC):
For each entity in the "Others" section, use this priority list to select ONE token:
1. Exam-point (if present, English only): take 1 word (or 1 short phrase ≤ 2 words)
2. else imaging cue token (if extractable as defined above)
3. else modality name (one modality token)
4. else omit token and list name only (do NOT invent)

TEXT PROHIBITIONS (STRICT):
- DO NOT include disease definitions or long explanations
- DO NOT include differential diagnoses
- DO NOT create paragraphs or multi-sentence explanations
- DO NOT add information not present in the table
- DO NOT force modality when absent from table

WORD BUDGET (STRICT):
- Entity name: As-is from table
- Modality: 1-3 modality names only (e.g., "CT / MRI") if present
- Imaging cue(s): 1-2 words each only (if extractable; max 2 cue lines)
- Exam-point: 1-3 words maximum (English only; optional when non-empty; omit if Korean-only; no translation)
- Total text per panel: Entity name + Modality keywords (if present) + up to 2 imaging cue tokens (if extractable) + optional exam-point keywords (English only; omit if Korean-only; no translation)
- Any word not present in the provided ALLOWED_TEXT must be omitted (do NOT paraphrase or translate).
- Korean (if used) must be an exact copy-only snippet from ENTITY_ROW_TEXT_BY_ENTITY for that entity, and only inside "Explanation:" lines.

VISUAL REQUIREMENTS:
- Large fonts, readable when downscaled.
- Clean white background, ample whitespace.
- Do NOT render the markdown table as a table.
- Do NOT output markdown (no pipes |, no markdown tables, no code fences, no headings with #, no emphasis markers *, no horizontal rules ---).
- Avoid loud colors; use one subtle accent color for highlights only.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Visual Type Category: {visual_type_category}

MASTER ROWS (plain, non-markdown; use ONLY this content):
{table_rows_plain}

OUTPUT:
Return IMAGE ONLY.
