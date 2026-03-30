TASK:
Generate exactly N text-only Anki cards for the specified entity.
All structure and meaning are defined upstream by S1.

AUTHORITATIVE READ-ONLY CONTEXT:

[Master Table — S1 Output]
{master_table_md}

EXECUTION TARGET:
- Group ID: {group_id}
- Entity Name: {entity_name}
- Exact Card Count: {cards_for_entity_exact}

ENTITY CONTEXT (READ-ONLY):
{entity_context}

EXECUTION RULES (ABSOLUTE):
1) Interpret the entity strictly as defined by S1.
   - Do NOT rename, merge, split, or reinterpret.
   - Do NOT introduce concepts absent from the master table.
2) Generate exactly {cards_for_entity_exact} cards.
   - Not "up to N", not "approximately N".
   - For 3-card policy: generate Q1, Q2, Q3 in order.
3) Card quality:
   - Each card MUST have non-empty front and back.
   - Exam-relevant, concise, and correct.
4) Card types and roles:
   - Q1: BASIC card type
   - Q2: MCQ card type (exactly 5 options A–E)
   - Q3: MCQ card type (exactly 5 options A–E)
   - Each card MUST have card_role field (Q1, Q2, or Q3).
   - For Q2/Q3 MCQ: MUST include "options" array (5 strings) and "correct_index" (0-4).
5) Image hint requirements:
   - Q1: MUST include image_hint object (required).
   - Q2: STRONGLY RECOMMENDED to include image_hint object.
   - Q3: MUST NOT include image_hint (must be null or absent).
   - image_hint is minimal structured metadata, NOT a full image prompt.
6) Prohibitions:
   - No full image prompts (only minimal image_hint allowed).
   - No importance, quota, allocation, or policy fields.
   - No visual metadata or experiment information beyond image_hint.
   - Q2/Q3 MUST NOT use deictic image references in text (e.g., "this image", "shown here", "이 영상에서", "보이는 이미지").
     Q2/Q3 must be solvable from text alone without referencing a specific image.

OUTPUT REQUIREMENTS:
- Return ONLY one valid JSON object.
- No explanations, no markdown, no extra text.
- JSON must be directly machine-parseable.

CANONICAL OUTPUT SCHEMA:
{
  "group_id": "{group_id}",
  "entity_name": "{entity_name}",
  "anki_cards": [
    {
      "card_role": "Q1|Q2|Q3",
      "card_type": "BASIC|MCQ",
      "front": "string",
      "back": "string",
      "tags": ["string", "string"],
      "image_hint": {
        "modality_preferred": "XR|CT|MRI|US|Angio|NM|PETCT|Other",
        "anatomy_region": "string (short)",
        "key_findings_keywords": ["keyword1", "keyword2", "keyword3"],
        "view_or_sequence": "string (optional)",
        "exam_focus": "string (optional: diagnosis|sign|pattern|differential)"
      },
      "options": ["option A", "option B", "option C", "option D", "option E"],
      "correct_index": 0
    }
  ]
}

MCQ FORMAT REQUIREMENTS (Q2/Q3):
- For MCQ card_type (Q2 and Q3), you MUST include:
  - "options": array of exactly 5 strings (options A through E)
  - "correct_index": integer (0-4) indicating which option is correct (0=A, 1=B, 2=C, 3=D, 4=E)
- Q1 (BASIC) does NOT need options or correct_index.
- The front text may also contain the question stem, but options must be in the structured "options" array.

IMAGE HINT RULES:
- Q1: image_hint is REQUIRED (non-null object).
- Q2: image_hint is STRONGLY RECOMMENDED (non-null object preferred).
- Q3: image_hint is FORBIDDEN (must be null or absent).
- image_hint.modality_preferred: one of XR, CT, MRI, US, Angio, NM, PETCT, Other.
- image_hint.anatomy_region: short free text describing the anatomical region.
- image_hint.key_findings_keywords: array of 1-3 key imaging findings keywords.
- image_hint.view_or_sequence: optional (e.g., "axial T2", "PA view").
- image_hint.exam_focus: optional (one of: "diagnosis", "sign", "pattern", "differential").

HARD CHECKS:
- len(anki_cards) == {cards_for_entity_exact}
- group_id echoed verbatim
- Each card has card_role (Q1, Q2, or Q3)
- Q1 has non-null image_hint
- Q3 has null or absent image_hint
- No forbidden keys present

STOP AFTER OUTPUT.

