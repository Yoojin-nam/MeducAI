# S1_USER_GROUP__v11.md

**Note**: Master tables must follow the **S1_SYSTEM** column headers exactly (current spec: **strict 6 columns**).
You **MUST** prioritize objective coverage completeness while preventing out-of-scope drift.

**Task**:
Analyze the following GROUP of learning objectives for Radiology Board Exam preparation
and produce a stable GROUP-LEVEL knowledge structure.

**Input Context**:
- Group Path: {group_path}

**Learning Objectives**:
{objective_bullets}

**Hard requirements**:
1) **Coverage completeness**:
- Every learning objective bullet **must** be covered by at least one entity row.
- If a bullet is not covered, add/adjust entity rows until it is covered.

2) **Scope control**:
- **Do NOT** introduce entities that are not traceable to the objectives.
- Exception: allow at most **ONE** prerequisite entity if strictly necessary.

3) **Two-pass self-check** (internal only, do not output mapping):
- Pass 1 (Coverage): map each objective bullet to entity rows; add missing entities.
- Pass 2 (Scope): remove any row that lacks objective traceability or prerequisite justification.

**Formatting**:
- Cells **MUST** be single-line plain text.
- **No** HTML tags, **no** "<br>" or "<br/>", **no** newline characters inside cells.
- Use "; " only to separate micro-points within a cell.
- **Do NOT** use '|' inside any cell.
- **Markdown formatting**: You may use markdown bold (**text** or __text__) in cell content to emphasize important terms. The PDF builder automatically converts this to bold formatting.

**Content quality requirements**:
1) Column 2 (질환 정의/패턴 정의/개념 설명/etc.) **MUST** be substantial:
   - Provide meaningful details that go beyond the entity name.
   - Include classification, key characteristics, or context that adds exam-relevant value.
   - Avoid generic labels that merely repeat the category.

2) For **Pathology_Pattern** column 3 (모달리티별 핵심 영상 소견):
   - Structure by modality: **"CT: [specific findings]; MRI: [specific findings]; X-ray: [specific findings]"**
   - Include **2-3 key findings** per relevant modality.
   - Provide modality-specific measurements, signs, or patterns.

3) **Language mixing** (**MANDATORY**):
   - Every cell **MUST** contain **BOTH Korean** (for context/connections) **AND English** (for medical terms).
   - **Do NOT** write entire cells in English-only.
   - Example **CORRECT**: "골단(Epiphysis)에 발생하며, CT에서 nidus 관찰 시 특징적" ✓
   - Example **WRONG**: "Epiphysis location; nidus on CT" ✗

**Entity list**:
- **entity_list** must match the table's **"Entity name"** column **EXACTLY** and in the same order.

**Infographic Clustering (OPTIONAL)**:
- Analyze all entities in the master table.
- If 3 or more entities are semantically related enough to share one infographic, 
  group them into a cluster.
- Create 1-4 clusters, each containing 3-8 related entities.
- For each cluster, generate:
  - cluster_id: "cluster_1", "cluster_2", etc.
  - entity_names: list of entity names in this cluster
  - cluster_theme: brief theme description (e.g., "Benign bone tumors", "Lung cancer staging")
  - infographic_style: appropriate style for this cluster
  - infographic_keywords_en: 10-25 words, comma-separated
  - infographic_prompt_en: full English prompt for image generation
  - infographic_hint_v2 (OPTIONAL but recommended when tokens allow): structured constraints to reduce anatomy/topology errors
    - Keep it compact (short lists, no long prose). If uncertain, set safety.requires_human_review=true.
- If all entities are best represented in a single infographic, omit entity_clusters and infographic_clusters fields.

**Output**:
Return **ONLY** the single JSON object required by **S1_SYSTEM**.

If clustering is beneficial (3+ related entities can share one infographic):
- Include entity_clusters and infographic_clusters fields
- Each cluster should have a distinct theme and infographic prompt
- CRITICAL: The number of entity_clusters MUST equal the number of infographic_clusters.
  - If you create 2 entity_clusters, create exactly 2 infographic_clusters.
  - If you create 3 entity_clusters, create exactly 3 infographic_clusters.
  - Each entity_cluster.cluster_id must have a matching infographic_cluster.cluster_id.

If single infographic is best:
- Omit entity_clusters and infographic_clusters fields (default behavior)

