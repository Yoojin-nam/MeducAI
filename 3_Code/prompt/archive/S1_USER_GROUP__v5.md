Task:
Analyze the following GROUP of learning objectives for Radiology Board Exam preparation
and produce a stable GROUP-LEVEL knowledge structure.

Input Context:
- Group Path: {group_path}
- Group ID: {group_id}

Learning Objectives:
{objective_bullets}

Instructions:

1) Infer the coherent conceptual scope of this group.
   - Identify the unifying theme that binds these objectives into a single group.
   - Exclude concepts that are peripheral or better suited to another group.

2) Assign the primary visual domain of the group.
   - Select EXACTLY ONE from:
     [Anatomy, Pathology, Physics, Equipment, QC, General]

3) Create ONE master table (Korean, Markdown).
   - The table must summarize the core concepts of the entire group.
   - Use clear, exam-oriented headers.
   - Ensure rows are conceptually distinct and clinically meaningful.
   - Do NOT create multiple tables.

4) Extract a list of distinct sub-entities.
   - Each entity must represent a meaningful, exam-relevant concept.
   - Avoid duplication, synonym inflation, or mixed granularity.
   - Do NOT decide card counts, card types, or image usage.

Output Requirements:
- Return ONLY a single valid JSON object.
- Do NOT include explanations, comments, markdown fences, or extra text.
- Follow the predefined schema EXACTLY.

Output Schema:
{
  "id": "{group_id}",
  "visual_type_category": "ONE of [Anatomy, Pathology, Physics, Equipment, QC, General]",
  "master_table_markdown_kr": "| Header1 | Header2 | ... |",
  "entity_list": ["Entity 1", "Entity 2", "..."]
}