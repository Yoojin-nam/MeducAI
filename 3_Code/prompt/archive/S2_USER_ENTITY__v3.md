## S2_USER_ENTITY (Strict QA, JSON-Safe)

You will be given:

- Upstream group metadata (fixed contract from S1)
- One specific entity to generate Anki-ready content for
- Card-type quota lines as plain text input

Your task:

Generate ONLY valid JSON for a single entity record, strictly following the schema. This JSON will be parsed automatically.

INPUTS YOU WILL RECEIVE

1) Upstream group context
- Includes curriculum path, objective summary, master table, and table infographic fields.
- Use this ONLY as anchor context; do not expand beyond it.

2) Entity
- One entity string representing one focused exam concept.
- Treat scope as closed. Do not introduce unrelated concepts.

3) Card type quota lines
- Input variable: {card_type_quota_lines}
- This input is plain text to guide distribution.
- Do not reprint or reformat these lines outside JSON.
- Follow quotas as closely as possible within the entity scope.

REQUIRED OUTPUT BEHAVIOR

- Output MUST be valid JSON only.
- Do NOT output markdown, code fences, headings, or any text outside JSON.
- Do NOT add, remove, rename, or reorder keys.
- Do NOT change types or nesting.

NULL AND EMPTY STRING RULES

- Required non-nullable string fields must be non-empty strings.
- If a field is nullable by schema, null is allowed and may be appropriate.
- Specifically: if row_image_necessity is IMG_NONE, then row_image_prompt_en must be null (when schema allows string or null).

IMAGE RULES (VERY IMPORTANT)

- All image prompts must be PACS-realistic and clinically accurate.
- No cartoon, illustration, decorative, artistic styles.
- If row_image_necessity is IMG_REQ, row_image_prompt_en must be a non-empty English prompt that is realistic and exam-appropriate.
- If row_image_necessity is IMG_NONE, row_image_prompt_en must be null (if schema allows).

OUTPUT FORMAT (HARD CONSTRAINT)

Return ONLY a single JSON object for this entity record, following the exact schema required by the pipeline.

Schema invariance rules:

- Do not add/remove/rename/reorder keys.
- Do not change nesting or types.
- All required keys must exist.
- Required content fields must not be empty strings.
- Nullable fields may be null when appropriate.

Important:

- Do not include any example JSON structures in your output.
- Do not include any explanation, commentary, or text outside the JSON object.

FINAL DECISION RULE

If you must choose between completeness and exam relevance, creativity and reproducibility, or flexibility and safety, always choose exam relevance, reproducibility, and safety.
