TASK:
Generate a SINGLE 16:9 pathology-pattern teaching slide from the master table.

DETERMINISTIC EXPANSION RULES:
- Expand ONLY the first 4–8 rows from the master table (in table order).
- If table has > 8 rows:
  - Render remaining entities in a compact "Others" section (entity name + 1 keyword each; no full panels).

DESIGN INTENT (NotebookLM-like lecture slide quality):
- Pattern-first visualization: show distribution/appearance as the PRIMARY information channel.
- Use illustrated grayscale thumbnails or clean pattern schematics (NOT text-only, NOT real scan screenshots).
- Clean 2×2 (preferred for 4) or 3×2 grid (for 5–6) or 4×2 grid (for 7–8) with generous whitespace.

LAYOUT (RECOMMENDED):
1) Top title bar:
   - Title: short, exam-oriented (use words from Group Path / entity names; do NOT invent new taxonomy)
   - Optional small subtitle: Group Path (if fits)
2) Main grid:
   - 4–8 "Pattern Cards" (expanded panels)
3) Bottom strip (optional, if space):
   - A small "Key differentiator / Pitfall" box with 2–3 tokens (English) ONLY if table supports it.
4) "Others" list (if needed):
   - Small font list: entity name + 1 keyword each.

PATTERN CARD TEMPLATE (each expanded panel):
1. Entity name (English, bold) - REQUIRED
   - Extract from table "Entity name" column
   - Display as-is, no modification

2. Modality keywords (English) - REQUIRED if present in table
   - Extract from table "모달리티별 핵심 영상 소견" column
   - Format: "CT / MRI" or "CT, MRI" (use "/" or "," separator)
   - Include ONLY modality names (CT, MRI, X-ray, US, PET, etc.)
   - Maximum 3 modalities per entity
   - If no modality information in table, OMIT this element (do NOT force)

3. Imaging cue token (English) - OPTIONAL
   - 1-2 word English imaging cue token (e.g., "ring enhancement", "dural tail", "ground-glass")
   - Extract from table "모달리티별 핵심 영상 소견" column
   - If you cannot confidently extract a 1-2 word cue from that field, OMIT the cue line (do NOT invent)
   - Do NOT prepend labels ("Cue:"). The line should be the token only.

4. 시험포인트 keywords (Korean or English) - MANDATORY when non-empty
   - Extract from table "시험포인트" column
   - If table "시험포인트" cell for this entity is non-empty and not "unknown/unclear", you MUST include 1–2 시험포인트 lines (each 1-3 words, Korean or English)
   - If 시험포인트 is empty/unclear, omit it
   - Format: single line, no sentences

Visual anchor (MANDATORY):
- At least one illustrated grayscale thumbnail OR a simplified schematic mimicking radiology contrast.
- The anchor MUST be schematic/illustrated (flat tones, simple shapes), NOT a real CT/MRI/X-ray/US scan screenshot and NOT a monitor/UI image.
- The thumbnail/schematic must express:
  - distribution (where),
  - appearance (what it looks like),
  - key sign (recognizable shape/pattern),
  using subtle highlights (outline/overlay) only.

"OTHERS" SECTION TOKEN SELECTION (DETERMINISTIC):
For each entity in the "Others" section, use this priority list to select ONE token:
1. 시험포인트 (if present) -> take 1 word (or 1 short phrase ≤ 2 words)
2. else imaging cue token (if extractable as defined above)
3. else modality name (one modality token)
4. else omit token and list name only (do NOT invent)

TEXT PROHIBITIONS (STRICT):
- DO NOT include "Distribution:", "Appearance:", "Key sign:" labels
- DO NOT include disease definitions or explanations
- DO NOT include differential diagnoses
- DO NOT create sentences or phrases
- DO NOT add information not present in the table
- DO NOT force modality when absent from table

WORD BUDGET (STRICT):
- Entity name: As-is from table
- Modality: 1-3 modality names only (e.g., "CT / MRI") if present
- Imaging cue: 1-2 words only (if extractable)
- 시험포인트: 1-3 words maximum (mandatory when non-empty)
- Total text per panel: Entity name + Modality keywords (if present) + Imaging cue token (if extractable) + 시험포인트 keywords (mandatory when non-empty)

VISUAL REQUIREMENTS:
- Large fonts, readable when downscaled.
- Clean white background, ample whitespace.
- Do NOT render the markdown table as a table.
- Avoid loud colors; use one subtle accent color for highlights only.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.
