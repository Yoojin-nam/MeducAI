# S1 Output JSON Schema Extension v1.4

**Status:** Extension to v1.3  
**Version:** 1.4  
**Supersedes:** `S1_Stage1_Struct_JSON_Schema_Canonical.md` (v1.3, 2025-12-19)  
**Applies to:** `2_Data/metadata/generated/<RUN_TAG>/stage1_struct.jsonl`  
**Last Updated:** 2025-12-23 (KST)

---

## 0. Purpose

This document defines the **extension** to S1 output schema v1.3, adding optional clustering fields for multi-infographic support.

**Important**: This is an **extension**, not a replacement. All v1.3 fields remain required. New fields are **optional** and only present when clustering is beneficial.

---

## 1. Schema Version

### 1.1 Version String

- **v1.3**: `"S1_STRUCT_v1.3"` (FROZEN, unchanged)
- **v1.4**: `"S1_STRUCT_v1.4"` (extension, backward compatible)

### 1.2 Backward Compatibility

- **v1.3 records** are valid v1.4 records (optional fields absent)
- **v1.4 records** can be processed by v1.3 consumers (optional fields ignored)

---

## 2. New Optional Fields

### 2.1 `entity_clusters` (Optional Array)

**Type**: `Array<EntityCluster>` or `null` or absent

**Presence**:
- **Present**: When LLM determines that clustering is beneficial (3+ related entities can be grouped)
- **Absent**: When all entities are best represented in a single infographic (default behavior)

**Structure**:
```json
"entity_clusters": [
  {
    "cluster_id": "cluster_1",
    "entity_names": ["Entity Name 1", "Entity Name 2", "Entity Name 3", ...],
    "cluster_theme": "Brief theme description"
  },
  {
    "cluster_id": "cluster_2",
    "entity_names": ["Entity Name 4", "Entity Name 5", ...],
    "cluster_theme": "Brief theme description"
  }
]
```

**Validation Rules**:
1. **Length**: 1-4 clusters (if present)
2. **Cluster size**: Each cluster must contain 3-8 entities
3. **Entity coverage**: All entities in `entity_list` must be included in exactly one cluster
4. **Cluster ID format**: `cluster_{index}` (1-based, e.g., `cluster_1`, `cluster_2`)
5. **Entity name matching**: `entity_names` must exactly match `entity_list[].entity_name` values

**EntityCluster Object**:
- `cluster_id` (string, required): Unique identifier within the group
- `entity_names` (array<string>, required): List of entity names (3-8 items)
- `cluster_theme` (string, required): Brief description of the cluster theme

### 2.2 `infographic_clusters` (Optional Array)

**Type**: `Array<InfographicCluster>` or `null` or absent

**Presence**:
- **Present**: When `entity_clusters` is present (must have same length)
- **Absent**: When `entity_clusters` is absent

**Structure**:
```json
"infographic_clusters": [
  {
    "cluster_id": "cluster_1",
    "infographic_style": "Anatomy_Map",
    "infographic_keywords_en": "keyword1, keyword2, keyword3, ...",
    "infographic_prompt_en": "Full English prompt for image generation"
  },
  {
    "cluster_id": "cluster_2",
    "infographic_style": "Pathology_Pattern",
    "infographic_keywords_en": "keyword1, keyword2, ...",
    "infographic_prompt_en": "Full English prompt for image generation"
  }
]
```

**Validation Rules**:
1. **Length**: Must match `entity_clusters` length (if both present)
2. **Cluster ID matching**: `cluster_id` must match corresponding `entity_clusters[].cluster_id`
3. **Style enum**: `infographic_style` must be one of the allowed values (see Section 2.3)
4. **Keywords**: `infographic_keywords_en` should be 10-25 words, comma-separated
5. **Prompt**: `infographic_prompt_en` must be non-empty

**InfographicCluster Object**:
- `cluster_id` (string, required): Must match `entity_clusters[].cluster_id`
- `infographic_style` (string, required): Style identifier (see Section 2.3)
- `infographic_keywords_en` (string, required): 10-25 words, comma-separated
- `infographic_prompt_en` (string, required): Full English prompt for image generation

### 2.3 Infographic Style Enum

**Allowed values**:
- `Anatomy_Map`
- `Pathology_Pattern`
- `Pattern_Collection`
- `Physiology_Process`
- `Equipment`
- `QC`
- `General`
- `Physics_Diagram`
- `Physics_Graph`
- `Equipment_Structure`
- `Imaging_Artifact`
- `MRI_Pulse_Sequence`
- `QC_Phantom`
- `Radiograph`
- `Default`

**Note**: This enum is broader than `visual_type_category` to allow cluster-specific styles.

---

## 3. Complete Schema Example

### 3.1 Example: No Clustering (v1.3 compatible)

```json
{
  "schema_version": "S1_STRUCT_v1.4",
  "group_id": "G001",
  "group_path": "Chest > Lung > CT",
  "objective_bullets": ["Objective 1", "Objective 2"],
  "visual_type_category": "Pathology_Pattern",
  "master_table_markdown_kr": "| Entity name | ... |\n| --- | ... |\n| ... |",
  "entity_list": [
    {"entity_id": "G001__E01", "entity_name": "Entity 1"},
    {"entity_id": "G001__E02", "entity_name": "Entity 2"}
  ],
  "integrity": {
    "entity_count": 2
  }
}
```

**Note**: `entity_clusters` and `infographic_clusters` are absent → single infographic (default).

### 3.2 Example: With Clustering (v1.4 extension)

```json
{
  "schema_version": "S1_STRUCT_v1.4",
  "group_id": "G002",
  "group_path": "Musculoskeletal > Bone > X-ray",
  "objective_bullets": ["Objective 1", "Objective 2", "Objective 3"],
  "visual_type_category": "Pathology_Pattern",
  "master_table_markdown_kr": "| Entity name | ... |\n| --- | ... |\n| ... |",
  "entity_list": [
    {"entity_id": "G002__E01", "entity_name": "Osteoid osteoma"},
    {"entity_id": "G002__E02", "entity_name": "Osteoblastoma"},
    {"entity_id": "G002__E03", "entity_name": "Osteosarcoma"},
    {"entity_id": "G002__E04", "entity_name": "Ewing sarcoma"},
    {"entity_id": "G002__E05", "entity_name": "Chondrosarcoma"},
    {"entity_id": "G002__E06", "entity_name": "Giant cell tumor"},
    {"entity_id": "G002__E07", "entity_name": "Aneurysmal bone cyst"},
    {"entity_id": "G002__E08", "entity_name": "Simple bone cyst"}
  ],
  "entity_clusters": [
    {
      "cluster_id": "cluster_1",
      "entity_names": ["Osteoid osteoma", "Osteoblastoma", "Osteosarcoma"],
      "cluster_theme": "Bone-forming tumors"
    },
    {
      "cluster_id": "cluster_2",
      "entity_names": ["Ewing sarcoma", "Chondrosarcoma"],
      "cluster_theme": "Round cell and cartilage tumors"
    },
    {
      "cluster_id": "cluster_3",
      "entity_names": ["Giant cell tumor", "Aneurysmal bone cyst", "Simple bone cyst"],
      "cluster_theme": "Benign bone lesions"
    }
  ],
  "infographic_clusters": [
    {
      "cluster_id": "cluster_1",
      "infographic_style": "Pathology_Pattern",
      "infographic_keywords_en": "bone-forming tumors, osteoid osteoma, osteoblastoma, osteosarcoma, radiology",
      "infographic_prompt_en": "Create a clean pathology pattern diagram showing bone-forming tumors including osteoid osteoma, osteoblastoma, and osteosarcoma. Include key imaging findings, typical locations, and distinguishing features."
    },
    {
      "cluster_id": "cluster_2",
      "infographic_style": "Pathology_Pattern",
      "infographic_keywords_en": "round cell tumors, cartilage tumors, Ewing sarcoma, chondrosarcoma, radiology",
      "infographic_prompt_en": "Create a clean pathology pattern diagram showing round cell and cartilage tumors including Ewing sarcoma and chondrosarcoma. Include key imaging findings and differential features."
    },
    {
      "cluster_id": "cluster_3",
      "infographic_style": "Pathology_Pattern",
      "infographic_keywords_en": "benign bone lesions, giant cell tumor, bone cysts, radiology",
      "infographic_prompt_en": "Create a clean pathology pattern diagram showing benign bone lesions including giant cell tumor, aneurysmal bone cyst, and simple bone cyst. Include key imaging findings and typical locations."
    }
  ],
  "integrity": {
    "entity_count": 8
  }
}
```

**Note**: `entity_clusters` and `infographic_clusters` are present → multiple infographics (one per cluster).

---

## 4. Validation Rules

### 4.1 Co-presence Rules

1. **Both present or both absent**:
   - If `entity_clusters` is present, `infographic_clusters` MUST be present
   - If `entity_clusters` is absent, `infographic_clusters` MUST be absent

2. **Length matching**:
   - `entity_clusters.length == infographic_clusters.length` (if both present)

3. **Cluster ID matching**:
   - `entity_clusters[i].cluster_id == infographic_clusters[i].cluster_id` (for all i)

### 4.2 Entity Coverage Rules

1. **All entities included**:
   - Every `entity_list[].entity_name` MUST appear in exactly one `entity_clusters[].entity_names` (if clustering present)

2. **No extra entities**:
   - Every `entity_clusters[].entity_names[]` MUST match an `entity_list[].entity_name`

3. **No duplicates**:
   - No entity name appears in multiple clusters

### 4.3 Cluster Size Rules

1. **Minimum cluster size**: 3 entities per cluster
2. **Maximum cluster size**: 8 entities per cluster
3. **Minimum clusters**: 1 cluster (if clustering present)
4. **Maximum clusters**: 4 clusters

### 4.4 Cluster ID Rules

1. **Format**: `cluster_{index}` where index is 1-based integer
2. **Uniqueness**: Each `cluster_id` must be unique within the group
3. **Sequential**: Should be `cluster_1`, `cluster_2`, `cluster_3`, `cluster_4` (if present)

---

## 5. Migration Guide

### 5.1 For S1 (Generation)

**No changes required**:
- Existing S1 prompts continue to work (will not generate clustering fields)
- New S1 prompts can optionally include clustering instructions

**To enable clustering**:
- Add clustering instructions to S1 prompt
- LLM will generate `entity_clusters` and `infographic_clusters` when beneficial

### 5.2 For S2 (Consumption)

**No changes required**:
- S2 ignores `entity_clusters` and `infographic_clusters`
- S2 only uses `entity_list` (unchanged)

### 5.3 For S3 (Policy Resolution)

**Required changes**:
- Check for `entity_clusters` presence
- If present, generate multiple `S1_TABLE_VISUAL` specs (one per cluster)
- If absent, generate single `S1_TABLE_VISUAL` spec (existing behavior)

### 5.4 For S4 (Image Generation)

**Required changes**:
- Process all `S1_TABLE_VISUAL` specs (not just one)
- Include `cluster_id` in filename when present

### 5.5 For S5 (PDF Building)

**Required changes**:
- Check for `entity_clusters` presence
- If present, include all cluster infographics in PDF
- If absent, include single infographic (existing behavior)

---

## 6. Error Handling

### 6.1 Invalid Clustering Data

**If `entity_clusters` present but invalid**:
- **Option 1**: Fail-fast (recommended for production)
- **Option 2**: Fallback to single infographic (warn and continue)

**Validation failures**:
- Missing entities in clusters → FAIL
- Extra entities in clusters → FAIL
- Cluster size < 3 or > 8 → FAIL
- Cluster count > 4 → FAIL
- Mismatched cluster IDs → FAIL

### 6.2 Missing Infographic Clusters

**If `entity_clusters` present but `infographic_clusters` absent**:
- **Option 1**: Fail-fast (recommended)
- **Option 2**: Generate default infographic prompts (warn and continue)

---

## 7. Testing Checklist

- [ ] v1.3 record (no clustering) → processed correctly
- [ ] v1.4 record (with clustering) → processed correctly
- [ ] v1.4 record (invalid clustering) → fails validation
- [ ] Mixed v1.3/v1.4 records → all processed correctly
- [ ] 1 cluster → 1 infographic generated
- [ ] 2 clusters → 2 infographics generated
- [ ] 4 clusters (max) → 4 infographics generated
- [ ] All entities covered in clusters
- [ ] No duplicate entities in clusters
- [ ] Cluster IDs match between entity_clusters and infographic_clusters

---

## 8. Notes

- This extension maintains **full backward compatibility** with v1.3
- Clustering is **optional** and determined by LLM
- When clustering is not beneficial, behavior is identical to v1.3
- All v1.3 validation rules still apply

