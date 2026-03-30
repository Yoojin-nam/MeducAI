Task:
You are responsible for GROUP-LEVEL knowledge structuring for Radiology Board Exam preparation.

Your role is to analyze a group of learning objectives and produce a stable conceptual structure.
Do NOT design learning cards or visual/image representations.
Focus ONLY on abstraction and organization of knowledge.

Input Context:
Group Path: {group_path}
Group ID: {group_id}

Learning Objectives:
{objective_bullets}

Instructions:
1) Infer the coherent conceptual scope of the group based on the Group Path and the learning objectives.
   - Identify what unifies these objectives into a single knowledge group.

2) Classify the primary visual domain of the group.
   - Select ONE: [Anatomy, Pathology, Physics, Equipment, QC, General]

3) Draft ONE Master Table (Korean, Markdown format) that summarizes the key concepts of the entire group.
   - The table must represent the group as a whole.
   - Use clear headers and clinically meaningful structure.
   - Do NOT create multiple tables.

4) Extract a list of distinct, non-overlapping sub-entities from the group.
   - Each entity should represent a meaningful concept suitable for downstream Anki card generation.
   - Do NOT decide the number of cards or card types.

Output Requirements:
- Return ONLY a single valid JSON object.
- Do NOT include any explanations, markdown fences, or extra text.
- All required fields must be present.

Output Schema (JSON):
{{
  "id": "{group_id}",
  "visual_type_category": "ONE of [Anatomy, Pathology, Physics, Equipment, QC, General]",
  "master_table_markdown_kr": "| Header1 | Header2 | ... |",
  "entity_list": ["Entity Name 1", "Entity Name 2", "..."]
}}