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
- Arrows pointing to unlabeled or empty regions
- Meta-instruction text appearing on the slide

SAFETY-FIRST DESIGN PHILOSOPHY (HIGHEST PRIORITY):
- This is an EDUCATIONAL REFERENCE slide, NOT a precise anatomical diagram.
- WRONG anatomy is WORSE than NO anatomy. When in doubt, use text labels only.
- Prioritize CLARITY and CORRECTNESS over visual complexity.

LEAK + LAYOUT SAFETY (MANDATORY):
- Do NOT output any taxonomy/breadcrumb/group-path text.
- Title / headers / entity names / takeaways: English-only.
- Korean allowed ONLY in "Explanation:" lines, copied EXACTLY from ENTITY_ROW_TEXT_BY_ENTITY.
- Keep all text inside safe margins; no overlap, no cut-off.

VISUAL APPROACH (MANDATORY):
- Use ONE central ABSTRACT region map (large) as the visual anchor.
- The region map must be a SIMPLE segmented silhouette / block map:
  - Examples: Left/Right, Superior/Mid/Inferior, Anterior/Posterior, 4-quadrant grid.
  - 4-6 segments total (simple geometry; no detailed organ shapes).
- Attach 4-8 callout cards around the map OR list as "Structure cards" below.
- Each callout/card: entity name + modality + 1-2 keyword lines + brief explanation.

ARROW/RELATIONSHIP SAFETY (CRITICAL):
- Leader lines may point ONLY to an ABSTRACT segment or numbered tag on the map.
- Do NOT draw arrows to specific anatomical structures, vessels, or organs.
- Do NOT draw vessel branching, anatomical courses, or detailed organ shapes.
- If placement is uncertain, use a "Structure card" with TEXT-ONLY relationships instead.
- When in doubt: NO arrow is better than a WRONG arrow.

CARD/CALLOUT TEMPLATE (each entity):
1. Entity name (English, bold) - REQUIRED (extract from table)
2. Modality (CT / MRI / US etc.) - OPTIONAL, only if in table
3. Key cue (1-2 words) - OPTIONAL, only if extractable from table
4. "Explanation:" + 1 short phrase (5-10 words) from table content - REQUIRED

CONTENT EXTRACTION STRATEGY:
- For each entity in the master table, extract:
  1. Structure/Entity name
  2. Location or anatomical relationship (if mentioned)
  3. Key imaging features or clinical significance
  4. Modality if specified
- If a row lacks detailed content, use: entity name + simple location label + schematic only

KEY TAKEAWAYS (MANDATORY):
- Add "Key takeaways:" section with 4-6 bullet points derived from table.
- Each bullet MUST be 6-12 words of actual educational content.
- English text from ALLOWED_TEXT or master table content only.
- NEVER leave bullets empty or with only abbreviations.

TEXT BUDGET:
- Any line: 3-8 words max.
- Avoid paragraphs.

STRICT PROHIBITIONS:
- NO detailed vessel/organ drawings or anatomical courses.
- NO arrows showing precise anatomical relationships (use abstract segment pointers only).
- NO invented anatomy or relationships not in the table.
- NO markdown syntax (no |, ---, #, *, etc.).
- NO Korean in titles/headers/entity names.
- NO empty text boxes or placeholders.
- NO meta-instruction text (like "allowed tokens:").

VISUAL STYLE:
- 16:9 slide, clean white/light background, dark title bar.
- Large fonts, generous whitespace.
- Central abstract region map (silhouette/block style) with callouts around it.
- Simple geometric shapes; avoid realistic anatomical detail.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Visual Type Category: {visual_type_category}

MASTER ROWS (plain, non-markdown; use ONLY this content):
{table_rows_plain}

OUTPUT:
Return IMAGE ONLY.

