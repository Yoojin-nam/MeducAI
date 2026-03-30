TASK:
Generate a SINGLE 16:9 board-review teaching slide image from the master table.

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–8 rows from the master table (in table order).
- If > 8 rows: add compact "Others" section (entity name + 1 keyword; no full panels).

DESIGN INTENT (MANDATORY):
- Convert table content into a structured grid of "entity panels" (lecture-slide style).
- Ensure high readability when downscaled.

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
   - Extract from table "핵심 영상 단서(키워드+모달리티)" or "모달리티별 핵심 영상 소견" column
   - Format: "CT / MRI" or "CT, MRI" (use "/" or "," separator)
   - Include ONLY modality names (CT, MRI, X-ray, US, PET, etc.)
   - Maximum 3 modalities per entity
   - If no modality information in table, OMIT this element (do NOT force)

3. Imaging cue token (English) - OPTIONAL
   - 1-2 word English imaging cue token (e.g., "ring enhancement", "dural tail", "ground-glass")
   - Extract from table "핵심 영상 단서(키워드+모달리티)" OR "모달리티별 핵심 영상 소견" column
   - If you cannot confidently extract a 1-2 word cue from those fields, OMIT the cue line (do NOT invent)
   - Do NOT prepend labels ("Cue:"). The line should be the token only.

4. 시험포인트 keywords (Korean or English) - MANDATORY when non-empty
   - Extract from table "시험포인트" column
   - If table "시험포인트" cell for this entity is non-empty and not "unknown/unclear", you MUST include 1–2 시험포인트 lines (each 1-3 words, Korean or English)
   - If 시험포인트 is empty/unclear, omit it
   - Format: single line, no sentences

Visual anchor (thumbnail/schematic) with minimal highlight - REQUIRED

"OTHERS" SECTION TOKEN SELECTION (DETERMINISTIC):
For each entity in the "Others" section, use this priority list to select ONE token:
1. 시험포인트 (if present) -> take 1 word (or 1 short phrase ≤ 2 words)
2. else imaging cue token (if extractable as defined above)
3. else modality name (one modality token)
4. else omit token and list name only (do NOT invent)

TEXT PROHIBITIONS (STRICT):
- DO NOT include "Key finding:", "Location:", "Pitfall:" labels
- DO NOT include disease definitions or explanations
- DO NOT include differential diagnoses
- DO NOT create sentences or phrases
- DO NOT add information not present in the table
- DO NOT force modality when absent from table

RULES:
- Use ONLY table content; do not invent details.
- Do NOT render the markdown table as a table.
- Avoid paragraphs; keep tokens short.
- Text per panel: Entity name + Modality keywords (if present) + Imaging cue token (if extractable) + 시험포인트 keywords (mandatory when non-empty).

VISUAL REQUIREMENTS:
- Dark title bar; clean white/light gray background; ample whitespace; large fonts.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.
