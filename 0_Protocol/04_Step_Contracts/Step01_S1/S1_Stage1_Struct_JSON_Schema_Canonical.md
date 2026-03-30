# MeducAI S1 Output JSON Schema (stage1_struct.jsonl)

**Status:** Canonical (FINAL FREEZE)  
**Version:** 1.3  
**Frozen:** Yes (Complete Freeze - No further structural changes)  
**Supersedes:** `S1_Stage1_Struct_JSON_Schema_Canonical.md` (v1.2, 2025-12-18)  
**Applies to:** `2_Data/metadata/generated/<RUN_TAG>/stage1_struct.jsonl`  
**Record unit:** 1 JSON object per line (NDJSON), one group per line  
**Last Updated:** 2025-12-19 (KST)

**⚠️ IMPORTANT: Schema and Structure Freeze Declaration**

This schema and structure are **completely frozen** as of 2025-12-19. No further structural changes to the S1 output format are permitted. The pipeline is ready to proceed to downstream stages (S2, S3, S4) with this schema as the stable contract.

**Note on Prompts:** While the schema is frozen, **prompt improvements are allowed and planned** for future iterations. Prompt changes must not alter the output schema structure defined in this document.

---

## 0. Purpose (Normative)

This document defines the authoritative schema contract for **S1 output**, `stage1_struct.jsonl`.

Downstream stages (S2, S3, S4) MUST assume this schema and MUST **fail-fast** when the contract is violated.

This schema is intentionally focused on:
- Deterministic **join keys** (group/entity identity)
- Deterministic **structure** (types, required keys)
- Deterministic **table↔entity alignment** (to prevent S2+ collapse)

---

## 1. Operating SSOT Alignment (Binding)

This canonical schema is aligned to the current “Weekly Integrated Conclusion (Operating SSOT)” decisions:
- **Input to S1 must be objective_bullets** (normalized from objective_list upstream)
- **S1 must output a single master table** with hard format constraints
- **Entity-level join uses entity_id**, which is code-owned and deterministic

---

## 2. Key Decisions and Invariants (Binding)

### 2.1 Group identity key (SSOT)

- `group_id` is the single authoritative group key across the pipeline.

Backward compatibility:
- Consumers MAY warn if it is present and differs from `group_id`.

### 2.2 Entity identity key (SSOT)

- `entity_id` is REQUIRED for every entity in `entity_list`.
- `entity_id` is **code-owned and deterministic**. The LLM MUST NOT invent or change `entity_id`.

Recommended deterministic format:
- `entity_id = f"{group_id}__E{index:02d}"`, where `index` is 1-based in the final stored entity order.

### 2.3 Visual type category (canonical enum)

- `visual_type_category` MUST be exactly one value from the canonical enum list in Section 4.
- No other values are allowed.

### 2.4 Row/Entity limits (stability invariant)

- **Hard max:** 20 data rows (and therefore max 20 entities)
- **Preferred range:** 10–14
- **15–20:** allowed but MUST add a warning

---

## 3. Top-level Record Schema

Each NDJSON line is a single JSON object with the following required fields.

### 3.1 Required fields

- `schema_version`: string, fixed value `"S1_STRUCT_v1.3"`
- `group_id`: string, non-empty
- `group_path`: string, non-empty
- `objective_bullets`: array of strings, length >= 1
- `visual_type_category`: string, enum, see Section 4
- `master_table_markdown_kr`: string, exactly one markdown table, see Section 5
- `entity_list`: array of objects, length >= 1, see Section 6
- `integrity`: object, must include at least the keys in Section 7

### 3.2 Optional fields (allowed, must not be required downstream)

- `group_title`: string
- `warnings`: array of strings
- `notes`: string
- `prompt_fingerprint`: string
- `model_info`: object
- `source_objectives_count`: integer, recommended diagnostics

---

## 4. Canonical Enum: visual_type_category

`visual_type_category` MUST be exactly one of the following strings:

- `Anatomy_Map`
- `Pathology_Pattern`
- `Pattern_Collection`
- `Physiology_Process`
- `Equipment`
- `QC`
- `General`

**Note:** 
- `Comparison`, `Algorithm`, `Classification`, and `Sign_Collection` have been removed (v11) as they were not used in the study.
- `Other` and additional categories (Treatment_Workflow, Modality_Protocol, Normal_Variants, Artifacts_Pitfalls, Reporting_Template) have been deprecated and are no longer supported.

---

## 5. Master Table: `master_table_markdown_kr` (Binding)

### 5.1 Hard format constraints (fail-fast)

The master table MUST satisfy all of the following:

1) Exactly **one** markdown table is present.  
2) The header row MUST be an **exact match** to the project's canonical header set (defined by the S1 prompt bundle / validator constants).  
3) Fixed column count: **exactly 6 columns** (first column: "Entity name", last column: "시험포인트", middle 4 columns vary by `visual_type_category`).  
4) Every data row MUST have **exactly 6 cells** (same as header).  
5) No empty cells.  
6) No multiline cells (no embedded newlines inside a cell).  
7) No raw `|` characters inside cells (cells must be pre-sanitized or escaped by an agreed rule).  
8) Data rows <= 20.
9) No ellipsis or placeholder text ("...", "etc", "and so on") in cells. All cells must contain concrete, specific content.

### 5.2 Row count policy

- `data_rows > 20` → FAIL  
- `15–20` → PASS with warning (add a warning string)  
- `10–14` → target  
- `<10` → allowed, but MAY warn if the group is broad

### 5.3 Cell content density and formatting

For categories that benefit from high information density:
- Each non-'시험포인트' cell should contain 2–4 atomic facts separated by ";", "/", "·", or ",".
- HTML tags (including `<br>` and `<br/>`) are FORBIDDEN inside cells. Use "; " to separate micro-points.
- All content must be concrete and specific—no vague references or omissions.
- Cells MUST be single-line plain text with no embedded newline characters.

---

## 6. Entity Schema

### 6.1 Required keys per entity object

Each object in `entity_list` MUST include:

- `entity_id`: string, non-empty, unique within the record
- `entity_name`: string, non-empty, human readable display name

### 6.2 Table↔Entity alignment (binding)

- `len(entity_list)` MUST equal the number of **data rows** in `master_table_markdown_kr`.
- The entity order MUST follow the master table data row order.
- `entity_name` MUST be derived from the designated "entity label" column (first column: "Entity name") of the master table.  
  - The entity_name MUST match the first column text **exactly**, character-for-character, in the same order.
  - This is a stability contract: entity_name is treated as a **display label**, while the join key is `entity_id`.

### 6.3 Optional keys per entity object (allowed)

- `entity_scope_note`: string, 1–2 sentences
- `linked_objective_indices`: array of integers, 0-based indices into `objective_bullets`

### 6.4 Anti-redundancy rules (for Pathology_Pattern and General categories)

For `visual_type_category` in {"Pathology_Pattern", "General"}:
- The first column "Entity name" is the canonical entity label.
- The second column (Pathology_Pattern: "질환 정의 및 분류"; General: "핵심 개념 설명") MUST provide substantial, informative content that goes beyond the entity name.
- For Pathology_Pattern: Column 2 must include disease category (benign/malignant/aggressive), WHO classification if relevant, and key clinical characteristics.
- For Pathology_Pattern: Column 3 "모달리티별 핵심 영상 소견" must be structured by modality (e.g., "CT: [findings]; MRI: [findings]; X-ray: [findings]").
- This prevents redundant information between columns and ensures each column adds value.

---

## 7. Integrity Object (Fail-fast)

`integrity` MUST be an object that contains at least:

- `entity_count`: integer, MUST equal `len(entity_list)`
- `table_row_count`: integer, MUST equal master table data row count
- `objective_count`: integer, MUST equal `len(objective_bullets)`

Recommended additional fields (optional):
- `row_policy`: string (e.g., `"target" | "warn_15_20" | "fail_over_20"`)

---

## 8. Required Fail-fast Conditions (Validator MUST FAIL)

A record MUST fail validation if any of the following are true:

- `schema_version` missing or not `"S1_STRUCT_v1.3"`
- `group_id` missing or empty
- `group_path` missing or empty
- `objective_bullets` missing, not an array, or empty
- `master_table_markdown_kr` missing, not a string, or not exactly one valid table
- Master table violates any hard constraints in Section 5.1
- `entity_list` missing, not an array, or empty
- Any entity missing `entity_id` or `entity_name`
- Duplicate `entity_id` within the record
- `visual_type_category` not in the canonical enum
- `integrity.entity_count != len(entity_list)`
- `integrity.table_row_count != (data rows in master table)`
- `integrity.objective_count != len(objective_bullets)`
- `len(entity_list) != (data rows in master table)`

---

## 9. Minimal Example (Non-normative)

```json
{
  "schema_version": "S1_STRUCT_v1.3",
  "group_id": "G0123",
  "group_path": "Chest > TB > Severity",
  "objective_bullets": ["Objective 1", "Objective 2"],
  "visual_type_category": "Pathology_Pattern",
  "master_table_markdown_kr": "| Entity name | 질환 정의 및 분류 | 모달리티별 핵심 영상 소견 | 병리·기전/특징 | 감별 질환 | 시험포인트 |\n|---|---|---|---|---|---|\n| Miliary pattern | 혈행성 전파에 의한 전신 결핵 형태로, 미세 결절이 양측 폐에 무작위 분포 | CT: 무작위 분포(Random)의 1-3mm 미세 결절; 양측 폐 전반 | 육아종성 염증 반응; 결절 크기 균일 | 전이; 진균 감염 | 무작위 분포 패턴이 결핵 진단의 핵심 |\n| Cavitation burden | 진행된 결핵의 특징으로 공기 충진 공동 형성 | CT: 공기 충진 공동; 벽 두께 평가; 파괴성 변화 | 치즈성 괴사(Caseous necrosis); 공동 내부 공기 | 폐농양; 괴사성 폐렴 | 공동 벽 특징이 진단 및 중증도 평가 핵심",
  "entity_list": [
    {"entity_id": "G0123__E01", "entity_name": "Miliary pattern"},
    {"entity_id": "G0123__E02", "entity_name": "Cavitation burden"}
  ],
  "integrity": {
    "entity_count": 2,
    "table_row_count": 2,
    "objective_count": 2
  }
}
```

---

## 10. File Replacement Workflow Notes (Operational)

After download, replace the canonical file in your repo:

```bash
cd /path/to/workspace/workspace/MeducAI
mv /path/to/workspace/Downloads/S1_Stage1_Struct_JSON_Schema_Canonical.REPLACEMENT.md 00_Governance/S1_Stage1_Struct_JSON_Schema_Canonical.md
```

If you bump the `schema_version` constant in code, update **validator + prompt bundle + any downstream consumers** in the same commit.
