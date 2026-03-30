## IMPROVED_S1_USER (Strict QA, JSON-Safe)

You will be given a **group of learning objectives** from a radiology board-exam curriculum.

Your task is to analyze this group and produce **structured, exam-oriented metadata** that will be used as a **fixed upstream contract** for downstream processes.

You must strictly follow all instructions below.

### INPUT CONTEXT

The following inputs will be provided.

1. Curriculum path:
   `{specialty} > {anatomy} > {modality_or_type}`
   This path defines the clinical and educational context.
   Use it only to anchor scope and terminology. Do not expand content beyond it.

2. Group key:
   `{group_key}`
   This represents a single coherent group of objectives and must be treated as one logical unit.

3. Learning objectives:
   `{objective_bullets}`
   These objectives define the upper and lower bounds of scope.
   Do not introduce concepts that are not reasonably inferable from them.

### REQUIRED TASKS (ALL MANDATORY)

You must complete **all** of the following tasks.

1. Infer the **exam-relevant scope** and **visual type category** of this group strictly from the provided context and objectives.

2. Create a **MASTER TABLE** in **Korean Markdown format** summarizing the **key concepts frequently tested in board examinations**.
   This table is mandatory and must not be empty.

3. Extract a list of **distinct entities** suitable for downstream Anki card generation.
   Each entity must represent **one focused exam concept**.

4. Define **one table-level infographic style and prompt** that supports conceptual organization of the Master Table.

Failure to complete any of the tasks above is a blocking error.

### MASTER TABLE RULES (VERY IMPORTANT)

The Master Table must:

* Be written in Korean
* Be concise, structured, and easy to scan
* Reflect “시험에서 자주 묻는 구조”

Each row must correspond to a **distinct, exam-relevant concept**.

Do not include narrative paragraphs, vague descriptions, redundant rows, or overlapping concepts.
The goal is **exam utility and clarity**, not maximal completeness.

### ENTITY LIST RULES (STRICT)

The entity list must be derived directly from the Master Table.

Rules:

* One entity corresponds to one focused exam concept
* Granularity must be consistent across entities

Do not duplicate entities using synonyms.
Do not mix umbrella categories with leaf-level facts.
Do not inflate the number of entities unnecessarily.

### INFOGRAPHIC PROMPT RULES

You must define exactly **one** infographic style and prompt at the table level.

The infographic must be:

* PACS-realistic
* Clinically accurate
* Exam-appropriate

Do not use cartoon, illustration, decorative, or artistic styles.
The purpose of the infographic is **conceptual organization**, not visual appeal.

### OUTPUT FORMAT (HARD CONSTRAINT)

You must return **ONLY valid JSON** that follows the exact schema provided below.

The JSON must contain **all required keys**, with no missing or empty fields.

The structure must be exactly as follows.

{
"id": "{group_id}",
"objective_summary": "One sentence summary",
"group_objectives": ["obj1", "obj2"],
"visual_type_category": "Select ONE: Anatomy | Pathology | Physics | Equipment | QC | General",
"master_table_markdown_kr": "...",
"entity_list": ["Entity 1", "Entity 2"],
"table_infographic_style": "...",
"table_infographic_keywords_en": "...",
"table_infographic_prompt_en": "..."
}

Do not add, remove, rename, or reorder keys.
Do not include any explanation, commentary, or text outside the JSON.

Any deviation from this format is a **blocking error**.


### FINAL DECISION RULE

If you must choose between completeness and exam relevance, creativity and reproducibility, or flexibility and safety, you must always choose **exam relevance, reproducibility, and safety**.