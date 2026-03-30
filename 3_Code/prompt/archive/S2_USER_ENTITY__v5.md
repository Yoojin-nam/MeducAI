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
   - Not “up to N”, not “approximately N”.
3) Card quality:
   - Each card MUST have non-empty front and back.
   - Exam-relevant, concise, and correct.
4) Card types:
   - Use only standard radiology board-appropriate card types.
   - Do NOT invent new types or hybrid styles.
5) Prohibitions:
   - No image decisions or prompts.
   - No importance, quota, allocation, or policy fields.
   - No visual metadata or experiment information.

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
      "card_type": "string",
      "front": "string",
      "back": "string",
      "tags": ["string", "string"]
    }
  ]
}

HARD CHECKS:
- len(anki_cards) == {cards_for_entity_exact}
- group_id echoed verbatim
- No forbidden keys present

STOP AFTER OUTPUT.