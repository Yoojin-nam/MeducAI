TARGET (READ-ONLY):
- Group ID: {group_id}
- Entity: {entity_name}
- Card Role: {card_role}

CARD CONTEXT (for consistency only; DO NOT expand findings):
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

MANDATORY IMAGE CONSTRUCTION (S5R3 REALISTIC; SINGLE PANEL + ZERO OVERLAYS):
- Generate ONE realistic {modality_preferred} image centered on {anatomy_region} with a standard clinical field-of-view
  (include adjacent anatomic landmarks; avoid unnaturally tight cropping).
- Use {view_or_sequence} orientation/sequence when applicable. If missing/unknown, choose the most typical clinical/board-exam view/sequence for {modality_preferred} and {anatomy_region}.
- Depict ONLY abnormalities implied by key_findings_keywords. Do NOT add any other findings.
- If any keyword is ambiguous, depict the most generic, minimal representation that still matches it. Prefer omission over guessing.
- The image should be consistent with the question and correct answer, but it does NOT need to make the diagnosis obvious.
- Use {card_back_keywords} only as a consistency check; do NOT introduce any additional findings beyond key_findings_keywords.
- Verify: Does the image show what the card text requires? If the text says 'X must be visible', the image must show X, not hide it or replace it with any overlay/text.

ZERO-OVERLAY POLICY (S5R3 CRITICAL):
- MANDATORY: overlay_count = 0 (text_count = 0 AND shape_overlay_count = 0). NO EXCEPTIONS.
- Forbidden text: any letters/numbers/words (including "L/R", "Left/Right"), captions, measurements, slice numbers, timestamps, patient identifiers, UI.
- Forbidden shapes: arrows, circles, boxes, callouts, pointers, highlight markers, drawn annotations of any kind.
- If ANY overlay exists, it is a FAILURE and must be regenerated with overlays removed.

SINGLE-PANEL POLICY (S5R3 CRITICAL):
- The output must be a single, unified image (no multi-panel layouts, no split screens, no collages, no side-by-side images).
- If 2+ panels are present, regenerate as a single panel.

VIEW CONSISTENCY CHECKLIST (MANDATORY; view_mismatch prevention):
- [ ] Does view_or_sequence match view_plane/projection (if present in CONSTRAINT_BLOCK)?
- [ ] If view_or_sequence = "axial", is the image an axial cross-section?
- [ ] If view_or_sequence = "coronal", is the image a coronal slice?
- [ ] If view_or_sequence = "sagittal", is the image a sagittal slice?
- [ ] If mismatch exists, regenerate with aligned specifications.

AXIAL ORIENTATION SAFETY (when applicable):
- If view_or_sequence indicates axial CT/MRI, the image MUST follow standard axial convention (viewer-left = patient-right).
- Ensure anatomy is not mirrored.
- Do NOT add any R/L markers.

PRE-OUTPUT COMPLIANCE CHECKLIST (VERIFY ALL):
- [ ] overlay_count = 0 (no text, no shapes)
- [ ] single panel (no multi-panel layouts)
- [ ] view matches specification (view_or_sequence matches view_plane/projection)
- [ ] laterality correct (if applicable, verify patient's side = viewer's side convention)
- [ ] no contradictions (image shows what card text requires)
- If any item fails, regenerate the image.

OUTPUT:
Return IMAGE ONLY.


