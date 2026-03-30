TARGET (READ-ONLY):
- Group ID: {group_id}
- Entity: {entity_name}
- Card Role: {card_role}

IMAGE_HINT (AUTHORITATIVE; use ONLY this):
- modality_preferred: {modality_preferred}
- anatomy_region: {anatomy_region}
- view_or_sequence: {view_or_sequence}
- key_findings_keywords: {key_findings_keywords}
- exam_focus: {exam_focus}

MANDATORY IMAGE CONSTRUCTION:
- Generate a single realistic {modality_preferred} image focused on {anatomy_region}.
- Use {view_or_sequence} orientation/sequence when applicable (if empty/unspecified, use a standard exam-typical view/sequence for {modality_preferred} and {anatomy_region}).
- Visually encode ONLY the key findings implied by key_findings_keywords.
- Keep the finding realistic and not overly conspicuous.
- Apply the SHOOTING GRAMMAR section BELOW, but ONLY the block that matches {modality_preferred} (ignore other modality blocks).

SHOOTING GRAMMAR (RENDER-ONLY; DO NOT ADD NEW MEDICAL FINDINGS)

COMMON (ALL MODALITIES):
- PACS-like clinical acquisition look; avoid studio-like, perfectly clean rendering.
- Include typical adjacent anatomy within a realistic field-of-view; avoid unnaturally tight cropping.
- Do not exaggerate contrast or edges; avoid cartoonish clarity.
- No embedded text, no letters (R/L), no side markers, no arrows/labels, no watermarks, no UI overlays.
- Do NOT introduce additional incidental findings not implied by key_findings_keywords.

XR / X-RAY / CR / DR:
- Framing: include realistic surrounding anatomy for {anatomy_region}; avoid overly centered “studio” composition.
- Collimation: include plausible collimation borders and mild edge vignetting; avoid perfectly even illumination.
- Texture: maintain visible trabecular pattern and crisp cortical edges; include mild quantum mottle/noise.
- Prohibitions: no side markers, no embedded text, no labels.

CT:
- Geometry: maintain realistic axial CT appearance unless view_or_sequence specifies otherwise; avoid 3D-render feel.
- Slice: simulate finite slice thickness with mild partial-volume effect; avoid razor-thin, ultra-crisp edges everywhere.
- Texture: realistic quantum noise / slight mottling; avoid plastic-smooth gradients.
- Windowing: clinically typical dynamic range; avoid HDR-like over-contrast.
- Prohibitions: no HU scale bars, no scout view, no slice numbers, no annotations.

MRI / MR:
- Sequence fidelity: follow view_or_sequence if provided; do not invent a different sequence/plane.
- Noise: include subtle MR background noise; avoid perfectly clean background.
- Inhomogeneity: mild coil shading (bias field) is acceptable; keep it subtle and plausible.
- Resolution: realistic slice thickness impression; avoid photographic sharpness and global edge enhancement.
- Prohibitions: no sequence labels, no slice numbers, no orientation markers, no UI overlays.

US / ULTRASOUND:
- Texture: preserve realistic B-mode speckle; avoid CT-like smooth gradients.
- Depth: subtle depth-dependent attenuation/gain; avoid uniform clarity across depth.
- Field: maintain a plausible ultrasound footprint feel (sector/linear look) WITHOUT any UI/text scales.
- Prohibitions: no Doppler color unless explicitly implied/required by key_findings_keywords; no calipers; no measurement text; no UI overlays.

NEGATIVE CONSTRAINTS:
- No labels, no arrows, no circles, no text.
- No extra abnormalities (no hemorrhage, no mass, no invasion) unless explicitly implied by keywords.
- No decorative elements.
- No multi-panel layouts, no split screens, no collages.

OUTPUT:
Return IMAGE ONLY.
