# MeducAI Step02 (S2) Contract and Output Schema (Canonical)

**Status:** Canonical  
**Version:** 3.2  
**Frozen:** No  
**Supersedes:** `S2_Contract_and_Schema_Canonical.md` (Version 3.1)  
**Last Updated:** 2025-12-26

**⚠️ S1 Input Schema Freeze (2025-12-19):**

As of 2025-12-19, S1 output schema (`stage1_struct.jsonl`) is **completely frozen** at version 1.3. S2 can now assume a stable S1 contract and proceed with implementation. S2 MUST consume `stage1_struct.jsonl` that conforms to `S1_STRUCT_v1.3`.  

---

## 1. Purpose (Normative)

This document defines the binding interface for S2.

S2 consumes schema-validated S1 output and produces entity-level, text-only Anki candidate cards for downstream consumers.

---

## 2. Identity and Keys (Binding)

- `group_id` is the single authoritative group key.
- `entity_id` is the single authoritative entity key.

---

## 3. Execution Unit (Binding)

The S2 execution unit is:

- `(group_id, entity_id)`

`entity_name` is a required display field, not an identity key.

---

## 4. Input Dependency

S2 MUST consume `stage1_struct.jsonl` that conforms to `S1_STRUCT_v1.3`.

---

## 5. Output Artifact Schema

Recommended output file:

- New format (preferred): `2_Data/metadata/generated/<RUN_TAG>/s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl`
- Legacy format (backward compatible): `2_Data/metadata/generated/<RUN_TAG>/s2_results__arm{ARM}.jsonl`

Each JSON line is one entity result record.

### 5.1 Required fields

- `schema_version`: `"S2_RESULTS_v3.2"`
- `group_id`: string, non-empty
- `group_path`: string, non-empty (**Required for Step05 Anki export tagging**: Used to generate Specialty/Anatomy/Modality/Category tags. Missing `group_path` will generate warnings in Step05.)
- `entity_id`: string, non-empty
- `entity_name`: string, non-empty
- `cards_for_entity_exact`: integer, >= 1
- `anki_cards`: array[object], `len(anki_cards) == cards_for_entity_exact`
- `integrity`: object, includes `card_count`

### 5.2 Required constraints

- `integrity.card_count == len(anki_cards)`
- `entity_id` and `entity_name` MUST be echoed verbatim from S1

Violation is a HARD FAIL.

---

## 6. Anki Card Object Schema (Minimal)

Each object in `anki_cards` MUST include:

- `card_id`: string, recommended `f"{entity_id}__C{index:02d}"`
- `card_role`: string, one of `Q1`, `Q2` (required, indicates card position in the 2-card set)
- `card_type`: string, one of `BASIC`, `MCQ`
- `front`: string, non-empty
- `back`: string, non-empty
- `tags`: array[string], must exist
- `image_hint`: object or null (conditionally required, see Section 6.1)

### 6.1 Image Hint Schema (Conditional)

The `image_hint` field is **conditionally required** based on `card_role`:

- **Q1**: `image_hint` is **REQUIRED** (must be a non-null object) - Back-only infographic 생성에 사용됨
- **Q2**: `image_hint` is **REQUIRED** (must be a non-null object) - Q1과 독립적인 Back-only infographic 생성에 사용됨
- **Q3**: 제거됨 (2-card policy)

When present, `image_hint` MUST be an object with the following structure:

```json
{
  "modality_preferred": "XR|CT|MRI|US|Angio|NM|PETCT|Other",
  "anatomy_region": "string (short, free text)",
  "key_findings_keywords": ["string", "string", "string"],
  "view_or_sequence": "string (optional, e.g., 'axial T2', 'PA view')",
  "exam_focus": "string (optional, one of: 'diagnosis', 'sign', 'pattern', 'differential')"
}
```

**Field requirements:**
- `modality_preferred`: string, one of the enum values
- `anatomy_region`: string, non-empty when `image_hint` is present
- `key_findings_keywords`: array of strings, length >= 1, each string non-empty
- `view_or_sequence`: string, optional (may be empty string or omitted)
- `exam_focus`: string, optional (may be empty string or omitted)

---

### 6.2 Image Hint v2 (Structured Anatomy Constraints; Optional but Supported)

S2 MAY additionally emit a richer, structured image hint object:

- `image_hint_v2`: object (optional)

**Normative intent:**
- `image_hint_v2` exists to reduce anatomical hallucinations in downstream image generation by encoding
  laterality / landmarks / adjacency / topology constraints as structured fields.
- S2 MUST remain text-only; `image_hint_v2` is metadata, not a full image prompt.
- Backward compatibility: absence of `image_hint_v2` MUST NOT break the pipeline.

**Runtime enforcement (operational toggle):**
- During rollout/experiments, validation MAY require `image_hint_v2` to be present on both Q1 and Q2.
  - Env flag: `S2_REQUIRE_IMAGE_HINT_V2=1`

**Schema source of truth (binding for v2 object):**
- JSON Schema: `0_Protocol/04_Step_Contracts/Step02_S2/S2_Image_Hint_Schema_v2.json`
- Rationale: `0_Protocol/04_Step_Contracts/Step02_S2/S2_Image_Hint_Schema_v2_Rationale.md`

**Key fields (non-exhaustive):**
- `anatomy`: `organ_system`, `organ`, `subregion`, `laterality`, `orientation.view_plane`,
  `key_landmarks_to_include`, `forbidden_structures`, `adjacency_rules`, `topology_constraints`
- `rendering_policy`: `style_target`, `text_budget`, `label_whitelist`, `forbidden_styles`
- `safety`: `requires_human_review`, `fallback_mode`

**Preservation requirement (binding):**
- If `image_hint_v2` is present in the model output, Step01/S2 normalization MUST preserve it into
  `s2_results__*.jsonl` for downstream S3/S4 consumption.

---

## 7. Fail-fast Rules

S2 MUST fail immediately when:

- S1 input violates the S1 schema
- entity_id cannot be resolved
- output length constraints are violated
- any required field is missing or type mismatched
- **Q1 card missing `image_hint`** (Q1 requires image_hint)
- **Q2 card missing `image_hint`** (Q2 requires image_hint)
- **`card_role` is missing or not one of `Q1`, `Q2`**
- **`anki_cards` array does not contain exactly 2 cards with roles Q1, Q2** (for 2-card policy)

---

## 8. File Replacement Workflow Notes (Operational)

```bash
cd /path/to/workspace/workspace/MeducAI
mv /path/to/workspace/Downloads/S2_Contract_and_Schema_Canonical.REPLACEMENT.md 00_Governance/S2_Contract_and_Schema_Canonical.md
```
