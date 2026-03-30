## IMPROVED_S1_USER (Strict QA, JSON-Safe)

You will be given a group of learning objectives from a radiology board-exam curriculum.

Your task is to analyze this group and produce structured, exam-oriented metadata that will be used as a fixed upstream contract for downstream processes.

You must strictly follow all instructions below.

INPUT CONTEXT

The following inputs will be provided.

1) Curriculum path
- Input variable: {specialty} > {anatomy} > {modality_or_type}
- Purpose: anchors clinical scope and terminology only.
- Rule: do not expand beyond this scope.

2) Group key
- Input variable: {group_key}
- Rule: treat this as one coherent logical unit.

3) Learning objectives
- Input variable: {objective_bullets}
- Rule: objectives define the upper and lower bounds of scope.

REQUIRED TASKS (ALL MANDATORY)

You must complete all of the following tasks.

1) Infer the exam-relevant scope and visual type category of this group strictly from the provided context and objectives.

2) Create a MASTER TABLE in Korean Markdown format summarizing key concepts frequently tested in board examinations.
- Mandatory: master_table_markdown_kr must be present and must not be empty.

3) Extract a list of distinct entities suitable for downstream Anki card generation.
- Each entity represents one focused exam concept.
- Entities must be derived directly from the Master Table.

4) Define exactly one table-level infographic style and prompt that supports conceptual organization of the Master Table.

Failure to complete any task above is a blocking error.

MASTER TABLE RULES (VERY IMPORTANT)

- Write in Korean Markdown table format.
- Concise, structured, easy to scan.
- Reflect “시험에서 자주 묻는 구조”.
- Each row is a distinct, exam-relevant concept.
- Do not include narrative paragraphs or redundant/overlapping rows.

ENTITY LIST RULES (STRICT)

- Derived directly from the Master Table.
- One entity = one focused exam concept.
- Granularity must be consistent across entities.
- Do not duplicate synonyms.
- Do not mix umbrella categories with leaf-level facts.
- Do not inflate the number of entities unnecessarily.

INFOGRAPHIC PROMPT RULES

Define exactly one table-level infographic style and prompt.

- PACS-realistic
- Clinically accurate
- Exam-appropriate
- No cartoon, illustration, decorative, artistic styles.

OUTPUT FORMAT (HARD CONSTRAINT)

Return ONLY valid JSON that follows the exact schema. Do not output any text outside JSON.

Schema invariance rules:

- Do not add, remove, rename, or reorder keys.
- Do not change nesting or types.
- All required keys must exist.
- Required content fields must not be empty strings.
- If a field is nullable by schema, null is allowed and may be appropriate.

The JSON object MUST include these keys in this exact order:

1) id
2) objective_summary
3) group_objectives
4) visual_type_category
5) master_table_markdown_kr
6) entity_list
7) table_infographic_style
8) table_infographic_keywords_en
9) table_infographic_prompt_en

Do not include any explanation, commentary, or any text outside the JSON.

FINAL DECISION RULE

If you must choose between completeness and exam relevance, creativity and reproducibility, or flexibility and safety, always choose exam relevance, reproducibility, and safety.
