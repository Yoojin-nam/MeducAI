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

TEXT MINIMIZATION (CRITICAL; addresses S5 excessive_text):
- Default: output **NO text labels** (labels=0). Use arrows/circles only.
- Exception: at most **1** short label total, only if essential for disambiguation.
- Never output laterality labels or tokens: \"Left\", \"Right\", \"L\", \"R\", \"(Left)\", \"(Right)\".

DIAGRAM STYLE (STRICT, ERROR-REDUCTION):
- Vector-like line art + flat grayscale tone blocks (about 3–5 tones), crisp edges.
- NO photorealistic scan look: no scan noise, no film grain, no fluoroscopy texture, no realistic speckle, no micro-texture.
- Reduce anatomic micro-detail; keep only essential silhouettes and 1–3 key landmarks.
- Avoid “artistic” rendering: no dramatic lighting, no 3D shading, no painterly effects.

DIDACTIC EMPHASIS (VERY CONTROLLED):
- Allowed emphasis: gentle outline, mild tone contrast, one or two arrows/circles pointing to the finding.
- Forbidden emphasis: glowing rims, neon colors, exaggerated size, dramatic contrast, hard posterization, cartoon effects.

ANNOTATION RULES (TEXT-AVOIDANT):
- Prefer arrows/circles only.
- Labels are OPTIONAL and should be avoided unless you are confident they render cleanly:
  - Max 1 label total, each 1–2 words preferred (max 3).
  - Large, clean sans-serif look, high contrast against background.
  - Prefer ASCII characters; avoid special symbols and long phrases.
  - If text is likely to distort, OMIT TEXT.
- If you use labels, derive them from key_findings_keywords (do NOT introduce new findings).

CONSISTENT FRAMING (“SAME ANGLE”):
- Keep a stable, standard framing for this modality + anatomy (consistent zoom and margins).
- Avoid random rotation, perspective changes, or inconsistent cropping.

NEGATIVE CONSTRAINTS:
- No patient identifiers, no timestamps, no PACS UI, no scales, no R/L markers, no slice numbers, no watermarks.
- No multi-panel layouts, no split screens, no collages.

AXIAL ORIENTATION SAFETY (when applicable):
- If view_or_sequence indicates axial CT/MRI, depict a single axial slice (cross-section), viewed from feet-to-head.
- Ensure anatomy is consistent with standard axial convention (viewer-left = patient-right).

OUTPUT:
Return IMAGE ONLY.

