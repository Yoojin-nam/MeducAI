# S1_USER_GROUP__v9.md

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
   - Choose EXACTLY ONE visual_type_category from the allowed list in the SYSTEM instructions.

3) Create ONE master table (Korean, Markdown) using the strict fixed columns defined in SYSTEM.
   - Keep it compact (prefer 8–14 rows, minimum 5).
   - Follow anti-redundancy rules for Pathology_Pattern and General categories.
   - Use Neuro-style high-density formatting:
     - Non-'시험포인트' cells: 3–6 atomic facts per cell.
     - '시험포인트' cell: 4–8 atomic facts in micro-template form (Trigger→**Answer**, Pitfall **A** vs B, Classic association).
   - Use Markdown bold **...** to emphasize board-critical discriminators:
     - Each row's '시험포인트' MUST include ≥1 bold phrase.
     - Limit ≤2 bold phrases per cell.

4) Extract entity_list.
   - entity_list must match the table's "Entity name" column (first column) EXACTLY, in the same order.
   - Use the exact text from the first column, character-for-character.
