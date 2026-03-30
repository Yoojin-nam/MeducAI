# Image Accuracy Stabilization

**Date:** 2025-12-23  
**Purpose:** Document changes to improve image accuracy and stability for S1 (concept infographics) and S2 (exam card images)

---

## Overview

This document describes the stabilization improvements implemented to address image accuracy and reproducibility issues across the MeducAI pipeline. The changes focus on deterministic compilation, resolution alignment, schema strengthening, and fail-fast guards.

---

## 1. Resolution Policy

### Default Resolution Changes

**EXAM Card Images (S2_CARD_IMAGE, S2_CARD_CONCEPT):**
- **Previous:** 1K (1024×1280)
- **New Default:** 2K (2048×2560)
- **Rationale:** S4_EXAM prompts target 2K resolution, but code defaulted to 1K, causing line/label/detail instability

**Table Visuals (S1_TABLE_VISUAL):**
- **Unchanged:** 4K (3840×2160) - remains at 4K for high-quality digital viewing and PDF

### Environment Variables

- `S4_CARD_IMAGE_SIZE`: Controls card image resolution (default: "2K")
  - Valid values: "1K", "2K"
  - Backward compatibility: `S4_IMAGE_SIZE` env var takes precedence if set
  
- `S4_FLASH_IMAGE_SIZE`: Controls flash/entity-only images (default: "1K")
  - Reserved for future use

### Backward Compatibility

Existing runs using 1K will continue to work if `S4_CARD_IMAGE_SIZE` is not set. The new default is 2K, but users can override via environment variable.

---

## 2. Compact Concept Table Specification

### Problem

S4_CONCEPT expects short English tokens + minimal KR exam-point token, but the original master table has mixed KR/EN narrative cells causing unstable token extraction and layout.

### Solution

A deterministic post-processor in S3 creates a compact, image-oriented markdown table with exactly 4 columns:

| Column | Description | Example |
|--------|-------------|---------|
| `Entity_EN` | Entity name (English term only) | "Osteoid Osteoma" |
| `ModalityTokens_EN` | Modality keywords (EN only) | "CT / MRI" |
| `CueToken_EN` | First short imaging cue phrase (1-2 words) | "ring enhancement" |
| `ExamPointToken_KR` | First short KR token (1-3 words) from 시험포인트 | "야간통증" |

### Implementation

- Function: `build_concept_image_table()` in `03_s3_policy_resolver.py`
- Extraction rules:
  - If original provides explicit token columns, use them
  - Else: parse modality keywords from modality column (EN terms only)
  - CueToken_EN: pick first short imaging cue phrase if present; else blank
  - ExamPointToken_KR: pick first short KR token (1-3 words) if present; else blank
  - If uncertain, prefer blank over invention
- Used in: `compile_table_visual_spec()` for all CONCEPT categories
- Original table stored in spec metadata (`master_table_markdown_kr_original`) for auditability

### Backward Compatibility

Existing S1 tables without token columns will have blanks filled deterministically (no invention). Old runs remain valid.

---

## 3. S2 image_hint_v2 Schema Strengthening

### Required Fields (when image_hint_v2 is present)

When `IMG_REQ=true` (Q1/Q2), `image_hint_v2` MUST exist and include:

- `anatomy.laterality`: One of "L", "R", "Midline", "NA", or "unknown"
- `anatomy.orientation`: MUST include either `view_plane` OR `projection` (or both), or set to "unknown" if truly unknown
  - `view_plane`: "axial", "coronal", "sagittal", "oblique", or "NA"
  - `projection`: "AP", "PA", "lateral", "oblique", or "NA"
- `anatomy.key_landmarks_to_include`: ≤3 short landmarks (for localization/topology)
- `anatomy.forbidden_structures`: ≤5 structures that must NOT be shown
- `rendering_policy.style_target`: MUST be "flat_grayscale_diagram" (default depiction_mode: "schematic_minimal")
- `safety.requires_human_review`: Set to true if any ambiguity flags are true:
  - `missing_view`: view_plane and projection both missing/unknown
  - `uncertain_location`: anatomy_region is vague or ambiguous
  - `uncertain_modality`: modality_preferred is "Other" or unclear

### Prompt Updates

- `S2_SYSTEM__v8.md`: Strengthened requirements section with explicit field guidance
- `S2_USER_ENTITY__v8.md`: Added required fields documentation with examples

---

## 4. Deterministic View/Sequence Completion

### Problem

Missing `view_or_sequence` in `image_hint_v2` causes ambiguity and unstable image generation.

### Solution

Function `apply_default_view_sequence()` in S3 deterministically fills missing view/sequence based on modality and anatomy region.

### Mapping Table

Deterministic mapping: `(modality, anatomy_region) -> default_view_sequence`

Examples:
- `("CT", "Head") -> "axial"`
- `("MRI", "Spine") -> "sagittal"`
- `("XR", "Chest") -> "PA"`

### Implementation

- Called in `compile_image_spec()` and `compile_concept_image_spec()` before building constraint block
- Stores `view_or_sequence_source` field: "hint_v2" (if present) or "s3_default_map" (if filled)
- If no default found, marks as "unknown" but still returns "s3_default_map" source

---

## 5. Clustering → Multi-Slide Spec

### Stable Ordering

When clustering exists:
- Entities within each cluster are sorted alphabetically by `entity_name` before creating cluster table
- Ensures stable ordering across reruns
- Logging added to show cluster ordering for auditability

### Filenames

Filenames already include `cluster_id` suffix:
- Single infographic: `IMG__{run_tag}__{group_id}__TABLE.jpg`
- Clustered: `IMG__{run_tag}__{group_id}__TABLE__{cluster_id}.jpg`

### Backward Compatibility

Existing clustering behavior preserved; only adds stable ordering within clusters.

---

## 6. Ambiguity Handling

### High Ambiguity Detection

If `requires_human_review=true` AND `image_asset_required=true`:
- Logs warning with reasons (sufficiency_flags, view_or_sequence_source)
- Continues with image generation (does not skip unless explicitly configured)
- Stores `requires_human_review=true` in spec for downstream processing

### Logging Format

```
[S3] Warning: High ambiguity for Q1 (Entity: {entity_name}, Group: {group_id}). 
Reasons: {reasons}. Image generation will proceed but may require human review.
```

---

## 7. RAG Fail-Fast

### Problem

RAG is currently enabled but not implemented, which could mislead users.

### Solution

If `S4_RAG_ENABLED=true`, pipeline now fails fast with clear error message:

```
RuntimeError: RAG augmentation not implemented; disable S4_RAG_ENABLED flag. 
S4 is render-only and does not support RAG augmentation.
```

### Backward Compatibility

If `S4_RAG_ENABLED=true`, pipeline will now fail-fast instead of silently ignoring. Users must disable flag.

---

## 8. Smoke Checks / Validation

### Validation Function

`validate_image_specs()` performs the following checks:

1. **Placeholder Check:** No `{placeholders}` remain in `prompt_en` strings (critical error)
2. **Resolution Hint Check:** EXAM images should have 2K resolution hints in prompts (warning)
3. **Compact Table Format:** Concept table specs should have exactly 4 columns (critical error)

### Integration

- Called in `process_s3()` after all specs are written
- Critical errors cause fail-fast
- Warnings are logged but do not stop processing

---

## Environment Variables Summary

| Variable | Default | Description |
|----------|---------|-------------|
| `S4_CARD_IMAGE_SIZE` | "2K" | Card image resolution (1K or 2K) |
| `S4_FLASH_IMAGE_SIZE` | "1K" | Flash/entity-only image resolution |
| `S4_IMAGE_SIZE` | (deprecated) | Legacy variable, takes precedence if set |
| `S4_RAG_ENABLED` | false | RAG flag (must be false, fail-fast if true) |
| `S4_EXAM_PROMPT_PROFILE` | "v8_diagram" | EXAM prompt profile (`v8_diagram` or `v8_realistic`) |
| `S2_REQUIRE_IMAGE_HINT_V2` | false | Require image_hint_v2 in S2 output |

---

## Backward Compatibility Summary

| Change | Backward Compatible? | Notes |
|--------|---------------------|-------|
| Resolution default (1K → 2K) | Yes | Can override via `S4_CARD_IMAGE_SIZE` |
| RAG fail-fast | Breaking | Must disable `S4_RAG_ENABLED` if previously enabled |
| Compact concept table | Yes | Old tables processed deterministically |
| Clustering stable order | Yes | Only adds ordering, preserves behavior |
| image_hint_v2 strengthening | Yes | Guidance in prompts, not hard requirement (unless `S2_REQUIRE_IMAGE_HINT_V2=1`) |

---

## Testing Recommendations

1. **Resolution:** Run existing pipeline with new defaults, verify 2K images generated
2. **RAG Fail-Fast:** Set `S4_RAG_ENABLED=1`, verify RuntimeError
3. **Compact Table:** Verify S4_CONCEPT receives 4-column table
4. **Clustering:** Verify multiple infographics with stable ordering
5. **View/Sequence Completion:** Verify missing views filled deterministically
6. **Smoke Checks:** Verify validation catches placeholder errors

---

## Files Modified

1. `3_Code/src/04_s4_image_generator.py` - Resolution policy, RAG fail-fast
2. `3_Code/src/03_s3_policy_resolver.py` - Compact table, clustering ordering, view/sequence completion, validation
3. `3_Code/prompt/S2_SYSTEM__v8.md` - Strengthen image_hint_v2 requirements
4. `3_Code/prompt/S2_USER_ENTITY__v8.md` - Strengthen image_hint_v2 requirements
5. `0_Protocol/04_Step_Contracts/Step04_S4/S4_Image_Accuracy_Stabilization.md` - This documentation file

---

## References

- S2 image_hint_v2 schema: `0_Protocol/04_Step_Contracts/Step02_S2/S2_Image_Hint_Schema_v2.json`
- S4_EXAM prompts:
  - Diagram: `3_Code/prompt/S4_EXAM_SYSTEM__v8_DIAGRAM_4x5_2K.md`, `S4_EXAM_USER__v8_DIAGRAM_4x5_2K.md`
  - Realistic: `3_Code/prompt/S4_EXAM_SYSTEM__v8_REALISTIC_4x5_2K.md`, `S4_EXAM_USER__v8_REALISTIC_4x5_2K.md`
- S4_CONCEPT prompts: `3_Code/prompt/S4_CONCEPT_SYSTEM__v3.md`, `S4_CONCEPT_USER__*.md`

