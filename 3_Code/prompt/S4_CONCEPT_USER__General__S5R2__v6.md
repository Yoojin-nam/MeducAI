TASK:
Generate a SINGLE 16:9 board-review teaching slide image from the master table.

NO EMPTY CONTENT RULE (CRITICAL - READ FIRST):
- EVERY text element you output MUST contain meaningful content (at least 4 words).
- NEVER output empty placeholders, "...", or labels followed by nothing.
- NEVER output only modality abbreviations without explanation (e.g., "XR." alone is FORBIDDEN).
- If you cannot fill a text element with meaningful content, OMIT that element entirely.
- "Key takeaways:" section MUST have 5-8 bullets, each with 6-12 words of actual learning content.
- "Explanation:" lines MUST contain actual explanatory phrases (5-10 words), not just modality names.

FAIL CONDITIONS (IMMEDIATE REJECTION):
- Empty "Key takeaways:" bullets (just dots without text)
- "Explanation:" lines containing only modality abbreviations (e.g., "Explanation: CT")
- Panels with only entity name and no other content
- Any placeholder text like "...", "TBD", or repeated single tokens

LEAK + LAYOUT SAFETY (MANDATORY):
- Do NOT output any taxonomy/breadcrumb/group-path text (no subtitles with paths; no metadata-like tokens).
- Korean rule (STRICT, LIMITED):
  - Title / headers / entity-name lines / takeaways MUST be English-only (no Korean/Hangul).
  - Korean is allowed ONLY inside "Explanation:" lines, and ONLY by COPYING EXACT KR snippets from ENTITY_ROW_TEXT_BY_ENTITY for the matching entity (no translation, no rewriting).
- Enforce the SYSTEM no-clipping / safe-area rules: keep all text inside safe margins, no overlap, no cut-off.
- If space is tight, wrap lines and remove OPTIONAL lines before shrinking fonts; reduce panels and move overflow into "Others" before shrinking.

RICHER EXPLANATION + SUMMARY (MANDATORY):
- Each expanded panel must include richer explanatory text while staying compact:
  - Target 2–4 short text lines per panel (excluding the entity name line).
  - Include 1–2 short "Explanation:" lines derived ONLY from that row's master-table wording (no invented facts).
  - Each explanation line MUST be 5-10 words (not just modality names).
  - If space is tight, drop the 2nd explanation line first.
- Add a slide-level "Key takeaways:" section with 5–8 short bullet lines derived ONLY from the table.
- Each takeaway bullet MUST be 6-12 words of actual educational content.
- English text MUST be composed ONLY from ALLOWED_TEXT (English list) plus words directly from the master table.
- Korean text is OPTIONAL and allowed ONLY inside "Explanation:" lines, and ONLY if copied EXACTLY from ENTITY_ROW_TEXT_BY_ENTITY (KR list) for the matching entity.

CONTENT EXTRACTION STRATEGY:
- For each entity, extract from the master table row:
  1. Entity name (required)
  2. Modality (CT/MRI/US/etc.) if mentioned
  3. Key imaging finding or cue (1-2 words describing appearance/pattern)
  4. Clinical context or significance (for explanation lines)
- If the master table lacks sufficient content for a panel, use a text-minimal visual approach with:
  - Entity name + schematic diagram + brief label only
  - Skip "Explanation:" if no meaningful content can be extracted

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–8 rows from the master table (in table order).
- If the table has more than 8 rows: add compact "Others" section (entity name + 1 keyword; no full panels).

DESIGN INTENT (MANDATORY):
- Convert table content into a structured grid of "entity panels" (board-review lecture-slide style).
- Maximize study-utility density WITHOUT adding any new facts; keep any extra label words limited to the allowed Zone 2 structural labels.
- Ensure high readability when downscaled (mobile/thumbnail safe).

HIGH-YIELD PANEL GRAMMAR (MANDATORY):
- Each expanded panel must read like a "rapid recall card":
  - A schematic thumbnail (primary)
  - A tight token stack (secondary)
  - Optional icon-coded emphasis (no text labels)
- Do NOT add large section headers like "Pearls/Pitfalls/Differential" (not allowed for this category).

TEXT BUDGET (RELAXED FOR EDUCATIONAL VALUE):
- Diagram-first, but allow brief explanatory phrases for clarity when supported by the table row.
- Any line of text: 3–6 words per line (max 8-10 words).
- Avoid paragraphs and multi-sentence explanations.

STRUCTURED TOKEN STACK (ALLOWED STRUCTURAL LABELS; Zone 2):
- You MAY use the following fixed labels to improve clarity (even if the labels are not in ALLOWED_TEXT):
  - "Modality:"
  - "Key cue:"
  - "Location:"
  - "Exam point:"
  - "Pitfall:"
  - "Distribution:"
  - "Appearance:"
- All words AFTER these labels MUST still come from ALLOWED_TEXT or master table content and MUST be directly supported by the row content.
- Do NOT introduce any other headers/labels beyond this list.

EXPLANATION LINE GRAMMAR (MANDATORY):
- After the token stack, add:
  - "Explanation:" + 1 short phrase line (5-10 words) (REQUIRED)
  - Optional 2nd "Explanation:" line (ONLY if space permits)
- Keep each explanation phrase short (5–10 words) and directly supported by the row content.
- NEVER use only modality abbreviations as explanation content.
- Korean (if used) must be an exact copy-only snippet from ENTITY_ROW_TEXT_BY_ENTITY for that entity.

GRID:
- Prefer 2×2 for 4, 3×2 for 5–6, 4×2 for 7–8.
- Keep panel templates identical across entities.

MANDATORY VISUAL ANCHOR (PER PANEL):
- Each expanded panel MUST include a small illustrated thumbnail OR a clean schematic icon conveying the key pattern.
- The thumbnail MUST be schematic/illustrated (flat tones, simple shapes), NOT a real CT/MRI/X-ray/US scan screenshot and NOT a monitor/UI image.
- Text-only panels are a FAIL.

PANEL TEMPLATE (each expanded panel):
1. Entity name (English, bold) - REQUIRED
   - Extract from table "Entity name" column
   - Display as-is, no modification

2. Modality keywords (English) - REQUIRED if present in table
   - Extract from the master table key-cue / modality-cue / imaging-finding columns
   - Format: "CT / MRI" or "CT, MRI" (use "/" or "," separator)
   - Include ONLY modality names (CT, MRI, X-ray, US, PET, etc.)
   - Maximum 3 modalities per entity
   - If no modality information in table, OMIT this element (do NOT force)

3. Imaging cue token (English) - OPTIONAL
   - 1-2 word English imaging cue token (e.g., "ring enhancement", "dural tail", "ground-glass")
   - Extract from the master table key-cue / modality-cue / imaging-finding columns
   - If you cannot confidently extract a 1-2 word cue from those fields, OMIT the cue line (do NOT invent)
   - Do NOT prepend labels ("Cue:"). The line should be the token only.

4. Optional 2nd imaging cue token (English) - OPTIONAL (HIGH-YIELD BOOST)
   - Only if the table row clearly contains TWO distinct short cue tokens
   - Same extraction sources as above
   - 1-2 words only; omit if not confidently extractable (do NOT invent)
   - No labels; token only

5. Exam-point keywords (English only) - OPTIONAL when non-empty
   - Source: the exam-point column in the master table (English tokens only; do NOT output Korean)
   - If the cell is non-empty but only Korean tokens exist, OMIT (do NOT translate)
   - Format: 1–2 short lines, tokens only (no sentences)

ICON-CODED EMPHASIS (OPTIONAL, NO TEXT LABELS):
- If two exam-point lines exist:
  - Render line 1 inside a small ★ badge (high-yield recall)
  - Render line 2 inside a small ⚠ badge (pitfall/trap)
- If only one exam-point line exists: use ★ only.
- Badges must be purely icon + the token line (no extra words like "Pearl"/"Pitfall").

Visual anchor (thumbnail/schematic) with minimal highlight - REQUIRED

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
- DO NOT output empty text elements or placeholders

RULES:
- Use ONLY table content; do not invent details.
- Do NOT output markdown (no pipes |, no markdown tables, no code fences, no headings with #, no emphasis markers *, no horizontal rules ---).
- Avoid paragraphs; keep tokens short.
- Text per panel: Entity name + Modality keywords (if present) + up to 2 imaging cue tokens (if extractable) + optional exam-point keywords (English only; omit if Korean-only; no translation).
- Any word not present in the provided ALLOWED_TEXT or master table must be omitted (do NOT paraphrase or translate).

VISUAL REQUIREMENTS:
- Dark title bar; clean white/light gray background; ample whitespace; large fonts.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Visual Type Category: {visual_type_category}

MASTER ROWS (plain, non-markdown; use ONLY this content):
{table_rows_plain}

OUTPUT:
Return IMAGE ONLY.

