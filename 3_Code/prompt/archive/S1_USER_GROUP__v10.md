# S1_USER_GROUP__v10.md

Task:
Analyze the following GROUP of learning objectives for Radiology Board Exam preparation
and produce a stable GROUP-LEVEL knowledge structure.

Input Context:
- Group Path: {group_path}

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
   - STRICTLY obey Verbosity Budget:
     - Each cell: AT MOST 2 micro-bullets (prefer 1–2)
     - Line breaks: Use "<br>", newline, or separate as needed (PDF builder normalizes automatically)
     - Each micro-bullet: short (≤90 chars OR 12–16 tokens), fragment style (no paragraphs)
     - Pack 2–4 atomic facts per micro-bullet using ";", "/", ","
   - Language policy:
     - Korean for connectors/explanations
     - English only for medical terms (diagnosis, modality/sequence/view, sign, key descriptors, abbreviations)
     - Do NOT output raw slugs/tags (snake_case/kebab-case) in visible text.
   - Bold emphasis:
     - Optional: You may use **bold** or __bold__ markdown for emphasis in '시험포인트' or any cell.
     - PDF builder will auto-bold important terms (medical abbreviations, numbers with units, terms in parentheses) if no explicit bold is used.
     - If using explicit bold, limit to ≤2 bold phrases per cell (1–2 lines).

4) Extract entity_list.
   - entity_list must match the table's "Entity name" column (first column) EXACTLY, in the same order.
   - Use the exact text from the first column, character-for-character.
