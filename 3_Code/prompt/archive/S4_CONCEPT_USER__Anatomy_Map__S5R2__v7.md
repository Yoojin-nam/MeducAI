TASK:
Generate a SINGLE 16:9 anatomy-reference teaching slide from the master table.

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
- Any arrows pointing to anatomical structures
- Meta-instruction text appearing on the slide
- Detailed anatomical drawings (vessels, organs, nerves)

SAFETY-FIRST DESIGN PHILOSOPHY (HIGHEST PRIORITY):
- This is an EDUCATIONAL REFERENCE slide, NOT a precise anatomical diagram.
- WRONG anatomy is WORSE than NO anatomy. Avoid detailed anatomical drawings entirely.
- Prioritize CLARITY, CORRECTNESS, and STUDY UTILITY over visual complexity.
- Use COLOR-CODING instead of arrows to show relationships (safer and clearer).

LEAK + LAYOUT SAFETY (MANDATORY):
- Do NOT output any taxonomy/breadcrumb/group-path text.
- Title / headers / entity names / takeaways: English-only.
- Korean allowed ONLY in "Explanation:" lines, copied EXACTLY from ENTITY_ROW_TEXT_BY_ENTITY.
- Keep all text inside safe margins; no overlap, no cut-off.

================================================================================
VISUAL APPROACH: HYBRID REGION LAYOUT (MANDATORY)
================================================================================

This slide uses a TWO-COLUMN layout for safe and effective anatomy learning:

LEFT COLUMN (30% width):
- A SIMPLE body-region silhouette showing 4-6 major regions ONLY.
- Use LARGE, ABSTRACT geometric shapes (rectangles or ovals) stacked vertically.
- Each region has a DISTINCT FILL COLOR (no anatomical detail inside).
- Region labels: Head/Neck, Thorax, Abdomen, Pelvis, Extremity (as applicable).
- NO internal organs, vessels, nerves, or anatomical structures drawn.
- This is a LOCATION REFERENCE only, not an anatomical diagram.

RIGHT COLUMN (70% width):
- Structure Cards arranged in a grid (2-column, 3-4 rows preferred).
- Each card displays one anatomical entity from the master table.
- Cards are visually linked to regions via COLOR TAGS (small colored squares/dots).

EXAMPLE REGION COLORS (use consistent, distinct colors):
- Head/Neck: Blue (#4A90D9)
- Thorax: Green (#4DAF4A)
- Abdomen: Orange (#FF7F0E)
- Pelvis: Purple (#9467BD)
- Extremity: Teal (#17BECF)
- General/Other: Gray (#7F7F7F)

================================================================================
NO ARROWS POLICY (CRITICAL - REPLACES ARROW/RELATIONSHIP SAFETY)
================================================================================

- Do NOT draw ANY arrows, leader lines, or pointer lines.
- Do NOT draw lines connecting cards to body regions.
- Do NOT draw vessel branching, nerve courses, or anatomical pathways.
- Instead, use COLOR TAGS on each Structure Card to indicate body region.
- Color tags are small colored squares (10-15px) at the corner of each card.
- This approach ELIMINATES incorrect arrow placement entirely.

================================================================================
STRUCTURE CARD TEMPLATE (each entity)
================================================================================

Each Structure Card MUST include:

1. COLOR TAG (small square in corner) - REQUIRED
   - Matches the body region color from the left silhouette
   - Provides instant visual association without arrows

2. Entity name (English, bold, large font) - REQUIRED
   - Extract from table "Entity name" column
   - Display as-is, no modification

3. Location line (English) - REQUIRED
   - Format: "Location: [brief anatomical position from table]"
   - Extract from "위치/인접 구조" column
   - Keep to 1 line, 4-8 words max
   - Example: "Location: posterior to ascending aorta"

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
- White/light gray background with subtle border
- Rounded corners (4-8px radius)
- Color tag in top-left or top-right corner
- Consistent card size across all entities
- Generous padding (do not crowd text)

================================================================================
CONTENT EXTRACTION STRATEGY
================================================================================

For each entity in the master table, extract:
1. Structure/Entity name
2. Body region (infer from 해부학적 구조 or 위치/인접 구조 columns)
3. Location/adjacency info (from 위치/인접 구조)
4. Clinical significance or exam point (from 시험포인트)
5. Modality if specified

Region assignment heuristics:
- Brain, skull, face, temporal, facial nerve → Head/Neck (Blue)
- Heart, lung, aorta, pulmonary, mediastinum → Thorax (Green)
- Liver, kidney, spleen, pancreas, GI tract → Abdomen (Orange)
- Bladder, prostate, uterus, rectum → Pelvis (Purple)
- Arm, leg, bone, joint → Extremity (Teal)
- If unclear, use General/Other (Gray)

================================================================================
DETERMINISTIC PANEL LIMIT
================================================================================

- MAX 8 Structure Cards (prefer 6).
- If master table rows exceed 8:
  - Expand ONLY the first 8 rows in table order.
  - Render remaining entities in compact "Others" section (name + 1 keyword each).
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
- Location line: 4-8 words
- Modality: 1-3 modality names
- Key cue: 1-2 words
- Explanation: 5-10 words
- Takeaway bullets: 6-12 words each

================================================================================
STRICT PROHIBITIONS
================================================================================

- NO detailed vessel/organ drawings or anatomical courses.
- NO arrows, leader lines, or pointer lines of any kind.
- NO internal anatomy inside body region silhouette (keep regions as simple filled shapes).
- NO invented anatomy or relationships not in the table.
- NO markdown syntax (no |, ---, #, *, etc.).
- NO Korean in titles/headers/entity names (only in Explanation lines if copied exactly).
- NO empty text boxes or placeholders.
- NO meta-instruction text (like "allowed tokens:").
- NO photorealistic images or real scan screenshots.

================================================================================
VISUAL STYLE
================================================================================

- 16:9 slide, clean white/light background, dark title bar.
- Large fonts, generous whitespace.
- Left: Simple color-coded body region silhouette (abstract shapes only).
- Right: Grid of Structure Cards with color tags.
- Bottom: Key takeaways section.
- Simple geometric shapes; avoid realistic anatomical detail.
- Consistent color palette across regions and cards.

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

