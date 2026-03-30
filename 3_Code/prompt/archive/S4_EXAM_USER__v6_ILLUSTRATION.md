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

MANDATORY IMAGE CONSTRUCTION (ILLUSTRATION):
- Generate a single board-exam medical illustration styled as a {modality_preferred} depiction, centered on {anatomy_region}, using a standardized textbook/atlas field-of-view (include adjacent anatomic landmarks, avoid unnaturally tight cropping).
- Use {view_or_sequence} orientation/sequence when applicable. If missing/unknown, choose the most typical board-exam view/sequence for {modality_preferred} and {anatomy_region}.
- Depict ONLY abnormalities implied by key_findings_keywords. Do NOT add any other findings.
- The illustration should be consistent with the question: "{card_front_short}" and the correct answer: "{card_answer_short}", but it does NOT need to show every secondary detail.
- Use {card_back_keywords} only as a consistency check, do NOT introduce additional findings beyond key_findings_keywords.

DIDACTIC EMPHASIS (CONTROLLED):
- Because this is an illustration, you MAY make the key finding more clearly visible than a real PACS image, but keep it clinically plausible.
- Allowed emphasis methods: gentle outline, subtle shading contrast, one or two arrows/circles pointing to the finding.
- Forbidden emphasis: glowing rims, neon colors, exaggerated size, “posterized” hard edges, or cartoon effects.

ANNOTATION RULES (KEEP TEXT LEGIBLE):
- You MAY use arrows/circles freely within reason (recommend ≤ 2 pointers).
- Text labels are OPTIONAL and must be minimal:
  - Max 2 labels total, each 1–3 words.
  - Large, clean sans-serif look, high contrast against background.
  - Prefer ASCII characters, avoid special symbols and long phrases.
- If text is likely to be distorted, OMIT TEXT and use arrows/circles only.

CONSISTENT FRAMING (“SAME ANGLE”):
- Keep a stable, standard framing for this modality + anatomy (consistent zoom and margins).
- Avoid random rotation, perspective changes, or inconsistent cropping.

NEGATIVE CONSTRAINTS:
- No patient identifiers, no timestamps, no PACS UI, no scales, no R/L markers, no slice numbers, no watermarks.
- No multi-panel layouts, no split screens, no collages.

OUTPUT:
Return IMAGE ONLY.
