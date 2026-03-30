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

TEXT BUDGET (RELAXED FOR EDUCATIONAL VALUE):
- Bucket panels are visual-first, but allow brief explanatory phrases for clarity when directly supported by the table rows assigned to the bucket.
- Any line of text: 3–6 words per line (max 8-10 words).
- Avoid paragraphs and multi-sentence explanations.

STRUCTURED TEXT (ALLOWED STRUCTURAL LABELS; Zone 2):
- You MAY use the following fixed labels to improve clarity (even if the labels are not in ALLOWED_TEXT):
  - "Pattern:"
  - "Shared cue:"
  - "Modality:"
  - "Exam point:"
  - "Pitfall:"
- All words AFTER these labels MUST still come from ALLOWED_TEXT and MUST be directly supported by the assigned rows.
- Do NOT introduce any other headers/labels beyond this list.

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
    1. Exam-point (if present, English only) -> take 1 word (or 1 short phrase ≤ 2 words)
    2. else imaging cue token (if extractable from the master table key-cue / modality-cue columns)
    3. else modality name (one modality token)
    4. else omit token and list name only (do NOT invent)
  - Tiny icon is allowed only if it is schematic (not decorative) and does not add new facts.
- Optional small exam-point keywords (English only) - OPTIONAL when non-empty for expanded entities
  - Source: the exam-point column in the master table (English tokens only; do NOT output Korean)
  - If the cell is non-empty but only Korean tokens exist, OMIT (do NOT translate)
  - Format: 1–2 short lines, tokens only (no sentences)

"OTHERS" SECTION TOKEN SELECTION (DETERMINISTIC):
For each entity in the "Others" section, use this priority list to select ONE token:
1. Exam-point (if present, English only) -> take 1 word (or 1 short phrase ≤ 2 words)
2. else imaging cue token (if extractable from the master table key-cue / modality-cue columns)
3. else modality name (one modality token)
4. else omit token and list name only (do NOT invent)

TEXT PROHIBITIONS (STRICT):
- DO NOT include differential diagnoses
- DO NOT create paragraphs or multi-sentence explanations
- DO NOT add information not present in the table
- DO NOT require modality for mini-items (it is optional)

READABILITY RULES:
- No paragraphs. No long sentences.
- Keep bucket headers short (Zone 2 structural labels only).
- Keep mini-items concise (name + 1 token only).

DO NOT RENDER MARKDOWN TABLE:
- Do NOT output markdown (no pipes |, no markdown tables, no code fences, no headings with #, no emphasis markers *, no horizontal rules ---).

VISUAL REQUIREMENTS:
- 16:9 slide, clean white/light gray background, ample whitespace.
- Large fonts, readable when downscaled.
- Dark title bar with concise title (from entity names / table wording only; no taxonomy/group paths).

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Visual Type Category: {visual_type_category}

MASTER ROWS (plain, non-markdown; use ONLY this content):
{table_rows_plain}

OUTPUT:
Return IMAGE ONLY.
