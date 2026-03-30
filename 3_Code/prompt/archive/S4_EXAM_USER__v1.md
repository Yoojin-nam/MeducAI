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
- Use {view_or_sequence} orientation/sequence when applicable.
- Visually encode ONLY the key findings implied by key_findings_keywords.
- Keep the finding realistic and not overly conspicuous.

NEGATIVE CONSTRAINTS:
- No labels, no arrows, no circles, no text.
- No extra abnormalities (no hemorrhage, no mass, no invasion) unless explicitly implied by keywords.
- No decorative elements.

OUTPUT:
Return IMAGE ONLY.

