Task: Analyze the provided GROUP of 'Learning Objectives' for Radiology Board Exam preparation.

Input Context:
- Group Path: {specialty} > {anatomy} > {modality_or_type}{category_suffix}
- Group Key: {group_key}
- Split Index (if any): {split_index}
- Group Size: {group_size} objectives
- Group Weight Sum: {group_weight_sum}
- Tags (aggregated): {anki_tags}
- Target Card Count: {target_count} (distinct sub-entities to extract, group-level)

Group Objectives (list):
{objective_bullets}

Instructions:
1) Infer the coherent scope of the group from the Group Path + objectives list.
2) Classify the visual type (Anatomy / Pathology / Physics / Equipment / QC / General).
3) Draft ONE Master Table (Korean Markdown) summarizing key concepts for the entire group.
4) Extract a list of distinct sub-entities to generate Anki cards for (group-level).

Table-level Infographic (Master Table -> ONE image):
5) Decide ONE table-level infographic style for generating a SINGLE infographic image for the entire Master Table.
   - Choose from: [Anatomy, Physics_Diagram, Physics_Graph, Equipment_Structure, Imaging_Artifact, MRI_Pulse_Sequence, QC_Phantom, Radiograph, Default]
6) Extract concise English keywords (10–25 words) that summarize the whole Master Table.
7) Compose a final English image prompt for an image generator using the selected style + keywords.
   - Must be a single-page educational infographic with minimal text (labels only).
   - White background, high contrast, clinically accurate, no watermark/logo.

Output Schema (JSON):
{{
  "id": "{group_id}",
  "objective_summary": "ONE representative summary sentence for the group (Korean or English)",
  "group_objectives": ["objective 1", "objective 2", "..."],
  "visual_type_category": "Select ONE: [Anatomy, Pathology, Physics, Equipment, QC, General]",
  "master_table_markdown_kr": "| Header1 | Header2 | ... | (Markdown Table String)",
  "entity_list": ["Entity Name 1", "Entity Name 2", "..."],
  "table_infographic_style": "Select ONE: [Anatomy, Physics_Diagram, Physics_Graph, Equipment_Structure, Imaging_Artifact, MRI_Pulse_Sequence, QC_Phantom, Radiograph, Default]",
  "table_infographic_keywords_en": "10–25 English words, comma-separated or short phrase",
  "table_infographic_prompt_en": "Final image prompt string for generating ONE table-level infographic"
}}