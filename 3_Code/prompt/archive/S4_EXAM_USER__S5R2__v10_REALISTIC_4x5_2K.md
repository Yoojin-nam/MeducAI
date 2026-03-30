TARGET (READ-ONLY):
- Group ID: {group_id}
- Entity: {entity_name}
- Card Role: {card_role}

CARD CONTEXT (for specificity; DO NOT expand findings):
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

MANDATORY IMAGE CONSTRUCTION (v8 REALISTIC):
- Generate ONE realistic {modality_preferred} image centered on {anatomy_region} with a standard clinical field-of-view
  (include adjacent anatomic landmarks; avoid unnaturally tight cropping).
- Use {view_or_sequence} orientation/sequence when applicable. If missing/unknown, choose the most typical clinical/board-exam view/sequence for {modality_preferred} and {anatomy_region}.
- Depict ONLY abnormalities implied by key_findings_keywords. Do NOT add any other findings.
- If any keyword is ambiguous, depict the most generic, minimal representation that still matches it. Prefer omission over guessing.
- The image should be consistent with the question and correct answer, but it does NOT need to make the diagnosis obvious.
- Use {card_back_keywords} only as a consistency check; do NOT introduce any additional findings beyond key_findings_keywords.
- Verify: Does the image show what the card text requires? If the text says 'X must be visible', the image must show X, not label it as 'NOT VISIBLE'.

TEXT MINIMIZATION (CRITICAL; addresses S5 excessive_text):
- Default: output **NO text labels** (labels=0). Use arrows/circles only.
- Exception: at most **1** short label total, only if essential for disambiguation.
- Never output laterality labels or tokens: "Left", "Right", "L", "R", "(Left)", "(Right)".

TEXT VALIDATION STEP (MANDATORY):
- After generation, verify: text_count <= 1
- If text_count > 1, regenerate with zero labels
- Count ALL text elements: labels, captions, annotations, measurements

CONSPICUITY CONTROL (HARD):
- Default to mild-to-moderate severity; do NOT enlarge or intensify findings for clarity.
- Preserve realistic modality-appropriate noise/texture; avoid "clean", noiseless, vector-like looks.
- Avoid saturated "glowing" highlights, neon rims, or graphic edges.

MODALITY-SPECIFIC REALISM:

XR / RADIOGRAPH:
- Exposure: typical clinical exposure; avoid extreme contrast or "posterized" blacks/whites.
- Texture: preserve trabecular pattern and mild quantum mottle.
- Composition: include sufficient surrounding bone/soft tissue for localization.

CT:
- Appearance: realistic CT noise and partial-volume effect; avoid HDR-like over-contrast.
- Windowing: typical clinical window/level feel (but do NOT display any UI, scale, or numbers).
  - If CONSTRAINT_BLOCK includes WINDOWING_HINT (brain|lung|bone|soft_tissue), follow it. If missing/unclear, do not guess—keep it generic.
- Slices: single-slice look; avoid perfectly uniform, noiseless tissue.

MRI:
- Signal: subtle background noise and mild coil shading; avoid perfectly uniform signal.
- Enhancement/bright signal: avoid saturation (no "pure white paint"); avoid glowing rims unless explicitly implied by key_findings_keywords.
- Ensure signal relationships are plausible for the weighting (do not flip expected bright/dark relationships).

US / ULTRASOUND:
- Texture: preserve realistic B-mode speckle; avoid CT-like smooth gradients.
- Depth: subtle depth-dependent attenuation/gain; avoid uniform clarity across depth.
- Footprint: maintain a plausible ultrasound footprint feel WITHOUT any UI/text scales.
- Prohibitions: no Doppler color unless explicitly implied/required by key_findings_keywords; no calipers; no measurement text; no UI overlays.

NEGATIVE CONSTRAINTS:
- No labels, no arrows, no circles, no text.
- No extra abnormalities (no hemorrhage, no mass, no invasion) unless explicitly implied by keywords.
- No multi-panel layouts, no split screens, no collages.
- No patient identifiers, no timestamps, no PACS UI, no R/L markers, no watermarks.

AXIAL ORIENTATION SAFETY (when applicable):
- If view_or_sequence indicates axial CT/MRI, the image MUST follow standard axial convention (viewer-left = patient-right).
- Ensure anatomy is not mirrored.

PRE-OUTPUT COMPLIANCE CHECKLIST (VERIFY ALL):
[ ] text_count <= 1 (count all text elements)
[ ] view matches specification (view_or_sequence matches view_plane/projection)
[ ] laterality correct (if applicable, verify patient's side = viewer's side convention)
[ ] single panel (no multi-panel layouts)
[ ] no contradictions (image shows what card text requires)
- If any item fails, regenerate the image.

OUTPUT:
Return IMAGE ONLY.


