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

TASK (S5R3 REALISTIC; follow SYSTEM constraints exactly):
- Generate ONE realistic {modality_preferred} image centered on {anatomy_region} with a standard clinical field-of-view (include adjacent anatomic landmarks; avoid unnaturally tight cropping).
- Use {view_or_sequence} orientation/sequence when applicable. If missing/unknown, choose the most typical clinical/board-exam view/sequence for {modality_preferred} and {anatomy_region} (conservative default; do not over-specify).
- Depict ONLY abnormalities implied by key_findings_keywords. Do NOT add any other findings. If ambiguous, prefer omission over guessing.
- The image should be consistent with the question/answer, but it does NOT need to make the diagnosis obvious.
- Verify consistency: if the card text says 'X must be visible', the image must show X (without using overlays/text to "cheat").

SEVERITY CALIBRATION (AUTHORITATIVE):
- Default severity: 4/10 (mild-to-moderate, subtle but detectable).
- Finding conspicuity: radiologist-level visibility (not obvious to medical students).
- Pattern completeness: 60-70% of textbook description (partial, imperfect, heterogeneous).
- Contrast difference: subtle relative to surrounding tissue (avoid high-contrast "poster" appearance).
- For any "sign" keyword: depict as it would appear in an average clinical case, not a teaching file example.

HARD REMINDERS (NO EXCEPTIONS):
- Single panel only (no multi-panel, no split screen, no collage).
- Zero overlays: no text and no shapes (no arrows/circles/boxes/callouts; no UI).

ANATOMY PLAUSIBILITY (DO NOT GUESS):
- Do NOT invent extra structures or impossible anatomy. Keep continuity and plausible boundaries.
- If laterality is not explicitly required, avoid arbitrary left/right-specific asymmetry.

MODALITY REALISM (CONSERVATIVE):
- Keep texture/windowing realistic for {modality_preferred}; avoid "diagram edges", glow, posterization, or overly clean CG look.
- If CONSTRAINT_BLOCK contains WINDOWING_HINT (CT-only), follow it. If absent/unclear, do not guess—use a generic conservative look.
- Do NOT "make it obvious": avoid exaggerated contrast, edge outlines, halos, or perfectly sharp lesion borders.

OUTPUT:
Return IMAGE ONLY.


