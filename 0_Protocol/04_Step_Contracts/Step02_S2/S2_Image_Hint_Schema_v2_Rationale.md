## Purpose and scope
This document explains **why** `image_hint_v2` exists, what each field is for, and how it maps to the MeducAI pipeline (S2 → S3 → S4) to reduce common anatomical errors in generated medical illustrations (Nano Banana Pro target).

- **S2**: uses surplus token budget to emit **structured constraints** (not a free-form prompt).
- **S3**: remains a **compiler** (no medical generation). It deterministically converts v2 fields into a short **CONSTRAINT BLOCK** and passes it through to S4 prompt templates.
- **S4**: remains **render-only**; it must follow the structured constraints and avoid “guessing”.

Schema file: `0_Protocol/04_Step_Contracts/Step02_S2/S2_Image_Hint_Schema_v2.json`.

## Why v1 is insufficient (observed failure modes)
The current v1 `image_hint` (modality/anatomy_region/view/keywords) is often too thin to prevent:
- **Laterality errors**: left/right inversion, bilateral depiction when unilateral was intended.
- **Adjacency errors**: wrong neighbor relationships (e.g., duct/vascular structures placed in the wrong order).
- **Topology errors**: wrong connectivity (e.g., post-operative anastomosis connections, loop configurations).
- **Over-specific hallucination**: model adds “typical” associated findings not requested.
- **Wrong omission**: key landmarks missing, making localization ambiguous and encouraging guessing.

`image_hint_v2` addresses this by making constraints **explicit, structured, and compressible**.

## Design principles
- **Minimal but constraining**: short lists and enums; avoid long prose.
- **Prefer omission over guessing**: if constraints cannot be stated confidently, mark `requires_human_review=true`.
- **Backward compatible**: v2 is optional; v1 remains required for existing EXAM lane checks.
- **Compiler-friendly**: fields should be easy to stringify into a stable CONSTRAINT BLOCK.

## Field-by-field rationale

### `anatomy`
- **organ_system / organ / subregion**: moves beyond a single `anatomy_region` string, enabling more precise constraints (e.g., “Stomach: antrum/pylorus” vs “Upper Abdomen”).
- **laterality**: directly targets the most frequent class of “obvious” anatomy errors (L/R).
- **orientation (view_plane/projection/patient_position)**: reduces view ambiguity that can cause incorrect spatial relationships.
- **key_landmarks_to_include**: ensures the model includes enough landmarks to localize findings without inventing detail.
- **forbidden_structures**: prevents common hallucinations (extra organs, wrong side structures, irrelevant anatomy).
- **adjacency_rules**: explicitly states relationships that should not be left to implicit “common sense”.
- **topology_constraints**: allows short, high-value rules for connectivity (especially postoperative anatomy).

### `pathology_depiction` (optional)
Used only when the card truly requires lesion depiction constraints. The intent is to **limit degrees of freedom** (location relative to landmarks, count, coarse size) without forcing detailed pathology illustration.

### `rendering_policy`
This exists to reduce a separate (but correlated) failure mode: when style drifts into photorealistic or PACS-like artifacts, the model tends to “fill in” details. A strict rendering policy supports conservative depiction.

### `safety`
- **requires_human_review**: allows a soft gate when constraints are insufficient.
- **fallback_mode**: enables deterministic “safer” prompt behaviors when uncertainty is high.

## How S3 should use v2 (compiler-only behavior)
S3 must not interpret medicine. It should:
- Pass through v2 fields into ImageSpec for auditability.
- Deterministically compile a short `constraint_block` (stable ordering, max lines).
- Set `requires_human_review` if v2 indicates it (or if required core fields are missing).

## Contract compatibility notes
- v1 `image_hint` remains the canonical minimal contract for EXAM lane prompts.
- v2 is additive; validators should **preserve** v2 fields rather than dropping them.


