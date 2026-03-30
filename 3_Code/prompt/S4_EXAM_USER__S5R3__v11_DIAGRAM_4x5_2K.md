TARGET (READ-ONLY):
- Group ID: {group_id}
- Entity: {entity_name}
- Card Role: {card_role}

CARD CONTEXT (for consistency only, DO NOT expand findings):
- Question (front): {card_front_short}
- Correct answer: {card_answer_short}
- Explanation keywords: {card_back_keywords}

IMAGE_HINT (AUTHORITATIVE; use ONLY this):
- modality_preferred: {modality_preferred}
- anatomy_region: {anatomy_region}
- view_or_sequence: {view_or_sequence}
- key_findings_keywords: {key_findings_keywords}
- exam_focus: {exam_focus}

CONSTRAINT_BLOCK (image_hint_v2; OPTIONAL but AUTHORITATIVE when present):
{constraint_block}

MANDATORY IMAGE CONSTRUCTION (v8 CONSERVATIVE DIAGRAM):
- Generate ONE board-exam medical illustration DIAGRAM styled as a {modality_preferred} depiction, centered on {anatomy_region}.
- Use a standardized textbook/atlas field-of-view (include adjacent anatomic landmarks; avoid unnaturally tight cropping).
- Use {view_or_sequence} orientation/sequence when applicable. If missing/unknown, choose the most typical board-exam view/sequence for {modality_preferred} and {anatomy_region}.
- Depict ONLY abnormalities implied by key_findings_keywords. Do NOT add any other findings.
- If any keyword is ambiguous, depict the most generic, minimal representation that still matches it. Prefer omission over guessing.
- The diagram should be consistent with the question and correct answer, but it does NOT need to show secondary details.
- Verify: Does the image show what the card text requires? If the text says 'X must be visible', the image must show X, not label it as 'NOT VISIBLE'.

TEXT BUDGET (CRITICAL):
- Default: NO text labels (prefer arrows/circles/visual cues).
- Default (allowed): A short TITLE + a few short labels is OK (keep total text elements small).
- Exception (rare): For simple educational diagrams like the reference examples, allow a SMALL, CAPPED amount of text:
  - Max ~7 text elements total (includes title + labels).
  - Labels must be short: 1–2 words preferred (max 3), ASCII-only preferred, no parentheses.
  - Never label laterality (forbidden: "Left", "Right", "L", "R").
  - No sentences, no paragraphs, no measurements, no captions.
- FORBIDDEN: Dense text blocks, captions, multi-sentence explanations, measurements, or labels like "A", "B", "Finding 1", "Finding 2".
- If text is unreadable/garbled, OMIT TEXT.

TEXT VALIDATION STEP (MANDATORY):
- After generation, verify: text_count < 8 (target <= ~7)
- If text_count >= 8, regenerate with fewer/shorter labels
- Count ALL text elements: labels, captions, annotations, measurements

DIAGRAM STYLE (STRICT, ERROR-REDUCTION):
- Vector-like line art + flat grayscale tone blocks (about 3–5 tones), crisp edges.
- NO photorealistic scan look: no scan noise, no film grain, no fluoroscopy texture, no realistic speckle, no micro-texture.
- Reduce anatomic micro-detail; keep only essential silhouettes and 1–3 key landmarks.
- Avoid "artistic" rendering: no dramatic lighting, no 3D shading, no painterly effects.

DIDACTIC EMPHASIS (VERY CONTROLLED):
- Allowed emphasis: gentle outline, mild tone contrast, one or two arrows/circles pointing to the finding.
- Forbidden emphasis: glowing rims, neon colors, exaggerated size, dramatic contrast, hard posterization, cartoon effects.

ANNOTATION RULES (VISUAL PREFERRED):
- Prefer arrows/circles over text labels.
- Text labels are OPTIONAL and should be avoided unless absolutely necessary for disambiguation (keep total text <= ~7 elements; see TEXT BUDGET).

CONSISTENT FRAMING ("SAME ANGLE"):
- Keep a stable, standard framing for this modality + anatomy (consistent zoom and margins).
- Avoid random rotation, perspective changes, or inconsistent cropping.

NEGATIVE CONSTRAINTS:
- No patient identifiers, no timestamps, no PACS UI, no scales, no R/L markers, no slice numbers, no watermarks.
- Default: single panel. Exception (rare, allowed): up to 2–3 panels for phase/before-after/comparison diagrams (NO 4+ panels, no collage).
- No excessive text (>=8 text elements), no paragraphs, no captions, no measurements.

AXIAL ORIENTATION SAFETY (when applicable):
- If view_or_sequence indicates axial CT/MRI, depict a single axial slice (cross-section), viewed from feet-to-head.
- Ensure anatomy is consistent with standard axial convention (viewer-left = patient-right).

VIEW CONSISTENCY CHECKLIST (MANDATORY):
- [ ] Does view_or_sequence match view_plane/projection?
- [ ] If view_or_sequence = "axial", is the image an axial cross-section?
- [ ] If view_or_sequence = "coronal", is the image a coronal slice?
- [ ] If view_or_sequence = "sagittal", is the image a sagittal slice?
- [ ] If mismatch exists, regenerate with aligned specifications

LATERALITY CHECKLIST (MANDATORY):
- [ ] Does the entity require specific laterality? (Check IMAGE_HINT and card text)
- [ ] If yes, verify: Is the structure on the correct side relative to viewer?
- [ ] For coronal: patient's left = viewer's right
- [ ] For axial: patient's right = viewer's left
- [ ] If uncertain, use a non-laterality-dependent view or request clarification

PANEL COUNT CHECKLIST (MANDATORY):
- [ ] Default: single panel
- [ ] If multi-panel is used, is panel_count <= 3 and layout simple/consistent (not a collage)?
- [ ] If panel_count >= 4, regenerate with <= 3 panels

MODALITY CONSISTENCY CHECKLIST (MANDATORY):
- [ ] Does IMAGE_HINT.modality_preferred match the card text modality?
- [ ] If card text says "Bone Scan" but IMAGE_HINT says "MRI", align the specifications first
- [ ] If card text says "CT" but IMAGE_HINT says "XR", align the specifications first
- [ ] If mismatch exists, regenerate with aligned specifications

PRE-OUTPUT COMPLIANCE CHECKLIST (VERIFY ALL):
[ ] text_count < 8 (count all text elements; if >= 8, regenerate with fewer/shorter labels)
[ ] view matches specification (view_or_sequence matches view_plane/projection)
[ ] laterality correct (if applicable, verify patient's side = viewer's side convention)
[ ] single panel (no multi-panel layouts, collages, or split screens)
[ ] modality consistent (IMAGE_HINT.modality_preferred matches card text modality)
[ ] no contradictions (image shows what card text requires)
- If any item fails, regenerate the image.

OUTPUT:
Return IMAGE ONLY.

