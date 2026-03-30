TASK:
Generate a SINGLE 16:9 anatomy-map teaching slide from the master table.

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–8 rows from the master table (in table order).
- If table has > 8 rows: render remaining rows in a compact "Others" strip (entity name + 1 keyword each; no full callouts).

DESIGN INTENT (MANDATORY):
- This is a SAFETY-FIRST anatomy map: prioritize avoiding misleading/incorrect anatomy over realism.
- Use ONE central ABSTRACT "region map" (large), NOT a detailed anatomical drawing.
- The region map must be a simple segmented silhouette / block map:
  - Examples of allowed segmentation: Left/Right, Superior/Mid/Inferior, Anterior/Posterior, 4-quadrant grid.
  - 4–9 segments total (simple geometry; no detailed organ shapes).
  - Up to 8 expanded items (first 4–8 rows) should be attached to the region map OR listed as "Structure cards" below the map.
- Priority is "readable when downscaled" (mobile/thumbnail safe).

MANDATORY VISUAL ANCHOR:
- The central ABSTRACT region map is REQUIRED.
- Each expanded row MUST have a visual anchor, using ONE of:
  (A) a callout anchored to a segment on the region map (arrow/leader line), OR
  (B) a small "Structure card" (mini schematic/icon) placed in a list/grid under the map.
- Text-only lists without either (A) or (B) are a FAIL.

ANATOMY SAFETY RULES (HIGHEST PRIORITY):
- DO NOT draw realistic anatomy, organs, vessels, bones, or accurate anatomic courses.
- DO NOT attempt “precise” anatomical localization beyond the abstract segments.
- Reduce micro-detail aggressively: only simple silhouettes + segment boundaries + leader lines.
- If unsure about anatomy, fall back to segment-only mapping and structure cards (do NOT guess anatomy).

CALLOUT TEMPLATE (each expanded row):
1. Entity name (English, bold) - REQUIRED
   - Extract from table "Entity name" column
   - Display as-is, no modification

2. Modality keywords (English) - OPTIONAL if present in table
   - Extract from table "위치/인접 구조" or "임상 적용" column if modality mentioned
   - Format: "CT / MRI" or "CT, MRI" (use "/" or "," separator)
   - Include ONLY modality names (CT, MRI, X-ray, US, PET, etc.)
   - Maximum 3 modalities per entity
   - If no modality information in table, OMIT this element (do NOT force)

3. Imaging cue token (English) - OPTIONAL
   - 1-2 word English imaging cue token (e.g., "ring enhancement", "dural tail", "ground-glass")
   - Extract from table "위치/인접 구조" or "임상 적용" column if imaging-related cue is mentioned
   - If you cannot confidently extract a 1-2 word cue from those fields, OMIT the cue line (do NOT invent)
   - Do NOT prepend labels ("Cue:"). The line should be the token only.

4. 시험포인트 keywords (Korean or English) - MANDATORY when non-empty
   - Extract from table "시험포인트" column
   - If table "시험포인트" cell for this entity is non-empty and not "unknown/unclear", you MUST include 1–2 시험포인트 lines (each 1-3 words, Korean or English)
   - If 시험포인트 is empty/unclear, omit it
   - Format: single line, no sentences

"OTHERS" SECTION TOKEN SELECTION (DETERMINISTIC):
For each entity in the "Others" section, use this priority list to select ONE token:
1. 시험포인트 (if present) -> take 1 word (or 1 short phrase ≤ 2 words)
2. else imaging cue token (if extractable as defined above)
3. else modality name (one modality token)
4. else omit token and list name only (do NOT invent)

TEXT PROHIBITIONS (STRICT):
- DO NOT include "Region:", "Landmark:" labels
- DO NOT include anatomical descriptions
- DO NOT include clinical applications
- DO NOT create sentences or phrases
- DO NOT add information not present in the table
- DO NOT force modality when absent from table
 - DO NOT use detailed anatomic location phrases not present in the table

RULES:
- Use ONLY table content; do NOT invent additional anatomy, variants, or measurements.
- Do NOT render the markdown table as a table.
- Avoid paragraphs; use only Entity name + Modality keywords (if present) + Imaging cue token (if extractable) + 시험포인트 keywords (mandatory when non-empty).

VISUAL REQUIREMENTS:
- 16:9 slide, clean white/light gray background, dark title bar.
- Large fonts, generous whitespace, minimal decoration.
- Subtle outlines/arrows are allowed; avoid clutter.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.
