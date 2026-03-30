TASK:
Generate a SINGLE 16:9 anatomy-reference teaching slide from the master table using a THREE-COLUMN layout.

NO EMPTY CONTENT RULE (CRITICAL - READ FIRST):
- EVERY text element you output MUST contain meaningful content (at least 4 words).
- NEVER output empty placeholders, "...", or labels followed by nothing.
- NEVER output "allowed tokens:" or any meta-instruction text on the slide.
- NEVER output only modality abbreviations without explanation.
- If you cannot fill a text element with meaningful content, OMIT that element entirely.
- "Key takeaways:" section MUST have 4-6 bullets, each with 6-12 words of actual learning content.
- "Explanation:" lines MUST contain actual explanatory phrases (5-10 words).
- All anatomical labels MUST be meaningful structure names, not placeholder text.

FAIL CONDITIONS (IMMEDIATE REJECTION):
- Empty "Key takeaways:" bullets (just dots without text)
- "Explanation:" lines containing only modality abbreviations
- Panels with only entity name and no other content
- Any placeholder text like "...", "allowed tokens:", "TBD"
- Any arrows, leader lines, or pointer lines
- Meta-instruction text appearing on the slide
- Text or labels on the CENTER CONTEXT IMAGE
- Photorealistic images or real scan screenshots

SAFETY-FIRST DESIGN PHILOSOPHY (HIGHEST PRIORITY):
- This is an EDUCATIONAL REFERENCE slide, NOT a precise anatomical diagram.
- WRONG anatomy is WORSE than NO anatomy. Avoid detailed anatomical drawings entirely.
- Prioritize CLARITY, CORRECTNESS, and STUDY UTILITY over visual complexity.
- Use LOCATION TEXT in Entity Cards to show anatomical relationships (no arrows needed).

LEAK + LAYOUT SAFETY (MANDATORY):
- Do NOT output any taxonomy/breadcrumb/group-path text.
- Title / headers / entity names / takeaways: English-only.
- Korean allowed ONLY in "Explanation:" lines, copied EXACTLY from ENTITY_ROW_TEXT_BY_ENTITY.
- Keep all text inside safe margins; no overlap, no cut-off.

================================================================================
VISUAL APPROACH: THREE-COLUMN LAYOUT (MANDATORY)
================================================================================

This slide uses a THREE-COLUMN layout for elegant and effective anatomy learning:

LEFT COLUMN (25% width):
- Contains 2-4 ENTITY CARDS stacked vertically
- Each card includes an ISOLATED ANATOMICAL ILLUSTRATION + text content
- Cards have consistent size and styling
- Generous padding between cards

CENTER COLUMN (50% width):
- A single HIGH-QUALITY CONTEXT MAP image
- Shows the anatomical region where all entities are located
- ABSOLUTELY NO ARROWS, NO TEXT, NO LABELS on this image
- Style: "Clean, high-quality medical illustration, soft lighting, 3D render style"
- Purpose: Aesthetic context ONLY, not a teaching diagram
- The image should be beautiful and professional, NOT instructional
- NO lines connecting to entity cards

RIGHT COLUMN (25% width):
- Contains 2-4 ENTITY CARDS stacked vertically (matching left column style)
- Same card template as left column
- Balanced visual distribution (similar number of cards as left column)

ENTITY DISTRIBUTION:
- If 4 entities: 2 left, 2 right
- If 5-6 entities: 2-3 left, 2-3 right
- If 7-8 entities: 3-4 left, 3-4 right
- Maintain visual balance between columns

================================================================================
CENTER CONTEXT IMAGE REQUIREMENTS (CRITICAL)
================================================================================

The center image is for AESTHETIC CONTEXT ONLY:

MUST INCLUDE:
- High-quality 3D medical illustration style
- Soft, professional lighting
- The anatomical region relevant to all entities (e.g., thorax, abdomen, pelvis)
- Beautiful, clean rendering without instructional elements

MUST NOT INCLUDE:
- ANY text, labels, or annotations
- ANY arrows, lines, or pointers
- ANY leader lines or connection indicators
- ANY numbered markers or callouts
- ANY instructional overlay elements

IMAGE STYLE KEYWORDS:
- "Clean medical illustration"
- "Soft ambient lighting"
- "3D anatomical render"
- "Professional medical art"
- "Aesthetic visualization"

================================================================================
ENTITY CARD TEMPLATE (each entity)
================================================================================

Each Entity Card MUST include:

1. ISOLATED ANATOMICAL ILLUSTRATION (top portion of card) - REQUIRED
   - A small, detailed visualization of THIS SPECIFIC anatomical structure
   - Zoom-in / macro style showing the isolated entity
   - Style: "Isolated anatomical structure, detailed visualization"
   - Clean background (white or light gray)
   - NO arrows or connecting lines

2. Entity name (English, bold, large font) - REQUIRED
   - Extract from table "Entity name" column
   - Display as-is, no modification

3. Location line (English) - REQUIRED (CRITICAL FOR CONTEXT)
   - Format: "Location: [brief anatomical position from table]"
   - Extract from "위치/인접 구조" column
   - Keep to 1-2 lines, 4-10 words max
   - Example: "Location: posterior to ascending aorta"
   - This replaces arrows for showing anatomical relationships

4. Modality (English) - OPTIONAL, only if in table
   - Format: "CT / MRI" (use "/" separator)
   - Maximum 2-3 modalities

5. Key cue (English) - OPTIONAL
   - 1-2 word imaging cue token if extractable
   - Example: "horizontal course", "bifurcation level"

6. Explanation line (English or Korean) - REQUIRED
   - Format: "Explanation:" + 1 short phrase (5-10 words)
   - Derive from table content (임상 적용, 시험포인트, etc.)
   - Korean allowed ONLY if copied exactly from ENTITY_ROW_TEXT_BY_ENTITY

CARD VISUAL STYLE:
- White/light gray background with subtle border or soft shadow
- Rounded corners (6-10px radius)
- Consistent card size across all entities
- Generous padding (do not crowd text)
- Illustration takes top 40-50% of card
- Text content in bottom 50-60% of card

================================================================================
CONTENT EXTRACTION STRATEGY
================================================================================

For each entity in the master table, extract:
1. Structure/Entity name
2. Anatomical region (for center context image reference)
3. Location/adjacency info (from 위치/인접 구조) - CRITICAL for Location line
4. Clinical significance or exam point (from 시험포인트)
5. Modality if specified

Region identification for center image:
- Brain, skull, face, temporal, facial nerve → Head/Neck region
- Heart, lung, aorta, pulmonary, mediastinum → Thoracic region
- Liver, kidney, spleen, pancreas, GI tract → Abdominal region
- Bladder, prostate, uterus, rectum → Pelvic region
- Arm, leg, bone, joint → Extremity region

================================================================================
DETERMINISTIC PANEL LIMIT
================================================================================

- MAX 8 Entity Cards (prefer 6).
- If master table rows exceed 8:
  - Expand ONLY the first 8 rows in table order.
  - Render remaining entities in compact "Others" section at bottom (name + 1 keyword each).
- Do NOT subjectively choose "important" ones. Selection is table-order top-N only.

================================================================================
KEY TAKEAWAYS (MANDATORY)
================================================================================

- Add "Key takeaways:" section at the bottom with 4-6 bullet points.
- Each bullet MUST be 6-12 words of actual educational content.
- Derive ONLY from table content (시험포인트 column preferred).
- English text from ALLOWED_TEXT or master table content only.
- NEVER leave bullets empty or with only abbreviations.

================================================================================
TEXT BUDGET
================================================================================

- Entity name: As-is from table (bold)
- Location line: 4-10 words (REQUIRED - this is how we show position without arrows)
- Modality: 1-3 modality names
- Key cue: 1-2 words
- Explanation: 5-10 words
- Takeaway bullets: 6-12 words each

================================================================================
STRICT PROHIBITIONS
================================================================================

- NO arrows, leader lines, or pointer lines of any kind.
- NO text, labels, or annotations on the center context image.
- NO lines connecting entity cards to the center image.
- NO detailed vessel/organ drawings or anatomical courses in center image.
- NO internal anatomy details (keep center image as aesthetic context only).
- NO invented anatomy or relationships not in the table.
- NO markdown syntax (no |, ---, #, *, etc.).
- NO Korean in titles/headers/entity names (only in Explanation lines if copied exactly).
- NO empty text boxes or placeholders.
- NO meta-instruction text (like "allowed tokens:").
- NO photorealistic images or real scan screenshots.

================================================================================
VISUAL STYLE
================================================================================

- 16:9 slide, clean white/light background, dark title bar at top.
- Large fonts, generous whitespace.
- LEFT COLUMN: Stack of Entity Cards with isolated illustrations.
- CENTER COLUMN: Beautiful anatomical context image (no text/arrows).
- RIGHT COLUMN: Stack of Entity Cards with isolated illustrations.
- BOTTOM: Key takeaways section spanning full width.
- Simple, elegant design with professional medical illustration aesthetic.
- Consistent card styling and spacing throughout.

================================================================================
INPUT (AUTHORITATIVE; READ-ONLY)
================================================================================

Group ID: {group_id}
Visual Type Category: {visual_type_category}

MASTER ROWS (plain, non-markdown; use ONLY this content):
{table_rows_plain}

================================================================================
OUTPUT
================================================================================

Return IMAGE ONLY.


