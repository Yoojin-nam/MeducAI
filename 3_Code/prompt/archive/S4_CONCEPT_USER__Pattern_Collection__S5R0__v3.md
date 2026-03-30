TASK:
Generate a SINGLE 16:9 "pattern collection" teaching slide from the master table.
Goal: group the first 4–8 entities into 3–5 defensible pattern buckets (lecture-slide style).

DETERMINISTIC EXPANSION RULES (MANDATORY):
- Expand ONLY the first 4–8 rows from the master table (in table order).
- Total expanded items must be ≤ 8 (top-N only).
- If table has > 8 rows: render remaining entities in a compact "Others" section (entity name + 1 keyword each; no full panels).

BUCKETING RULES (STRICT):
- Create 3–5 buckets max (e.g., Pattern A/B/C…).
- Bucketing MUST be defensible using the table wording; do NOT invent a new taxonomy.
- If table content does not support meaningful bucketing, fall back to simple buckets based on repeated table wording (still defensible), not external knowledge.

MANDATORY VISUAL ANCHOR (CRITICAL):
- Treat EACH BUCKET as an expanded panel.
- Each bucket panel MUST include a visual anchor:
  - One representative illustrated grayscale thumbnail OR a clean schematic that conveys the bucket's shared pattern.
  - The anchor MUST be schematic/illustrated (flat tones, simple shapes), NOT a real scan screenshot and NOT a monitor/UI image.
- "Text-only buckets" are a FAIL condition.

BUCKET PANEL TEMPLATE (each bucket):
- Bucket header (short, English; e.g., "Pattern: Periventricular ovoid lesions") - ALLOWED as Zone 2 structural label
  - Derived from table wording only
  - Do NOT invent new taxonomy
- Visual anchor (representative thumbnail/schematic)
- Mini-items list (from the expanded entities assigned to this bucket):
  - Each mini-item: Entity name (English, bold) - REQUIRED
    - Extract from table "Entity name" column
    - Display as-is, no modification
  - ONE token only (use deterministic priority list below):
    1. 시험포인트 (if present) -> take 1 word (or 1 short phrase ≤ 2 words)
    2. else imaging cue token (if extractable from "핵심 영상 단서(키워드+모달리티)" column)
    3. else modality name (one modality token)
    4. else omit token and list name only (do NOT invent)
  - Tiny icon is allowed only if it is schematic (not decorative) and does not add new facts.
- Optional small "시험포인트" keywords (Korean or English) - MANDATORY when non-empty for expanded entities
  - Extract from table "시험포인트" column
  - If table "시험포인트" cell for an expanded entity is non-empty and not "unknown/unclear", you MUST include 1–2 시험포인트 lines (each 1-3 words, Korean or English)
  - If 시험포인트 is empty/unclear, omit it
  - Format: single line, no sentences

"OTHERS" SECTION TOKEN SELECTION (DETERMINISTIC):
For each entity in the "Others" section, use this priority list to select ONE token:
1. 시험포인트 (if present) -> take 1 word (or 1 short phrase ≤ 2 words)
2. else imaging cue token (if extractable from "핵심 영상 단서(키워드+모달리티)" column)
3. else modality name (one modality token)
4. else omit token and list name only (do NOT invent)

TEXT PROHIBITIONS (STRICT):
- DO NOT include pattern descriptions or explanations
- DO NOT include differential diagnoses
- DO NOT create sentences or phrases
- DO NOT add information not present in the table
- DO NOT require modality for mini-items (it is optional)

READABILITY RULES:
- No paragraphs. No long sentences.
- Keep bucket headers short (Zone 2 structural labels only).
- Keep mini-items concise (name + 1 token only).

DO NOT RENDER MARKDOWN TABLE:
- Do NOT render the markdown table as a table.

VISUAL REQUIREMENTS:
- 16:9 slide, clean white/light gray background, ample whitespace.
- Large fonts, readable when downscaled.
- Dark title bar with concise title (from Group Path / table wording only).

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.
