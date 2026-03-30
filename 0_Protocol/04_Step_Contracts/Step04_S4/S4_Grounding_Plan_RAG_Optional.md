## Goal
Reduce anatomical errors (laterality, adjacency, topology/connectivity) by optionally grounding image generation with **retrieved “anatomy blueprints”**.

Constraint: **No external web dependency at runtime**.

This document proposes an internal retrieval mechanism (RAG-like) that plugs into MeducAI while preserving:
- **S3 is a compiler, not a generator**
- **S4 is render-only**

## Core idea: Internal “Anatomy Blueprint Library”
We maintain a curated library of short, text-only “blueprints” that encode high-value constraints (landmarks, adjacency, topology) for common regions/procedures.

### Blueprint format
Recommended: YAML or JSON (text-only) stored in-repo.

Example (YAML-ish):
- `blueprint_id`: `gi_roux_en_y_topology_v1`
- `keys`:
  - `modality`: `CT`
  - `anatomy_region`: `Upper abdomen`
  - `procedure`: `Roux-en-Y gastric bypass`
  - `view_plane`: `axial/coronal`
- `constraint_lines`:
  - `Roux limb connects_to gastric pouch`
  - `biliopancreatic_limb connects_to jejunojejunostomy`
  - `exclude: gallbladder surgery hardware`

### Retrieval keys (deterministic)
Minimal key set:
- `modality_preferred` (v1)
- `anatomy.organ_system/organ/subregion` (v2)
- `exam_focus` (v1)
- optional `procedure` token (S2 can supply explicitly in v2 when relevant)

## Integration options

### Option A (preferred): Retrieval in S3 (compiler selects blueprint_id)
- S3 selects `blueprint_id` deterministically (lookup table / string match).
- S3 appends retrieved `constraint_lines` into the compiled `constraint_block`.
- **Pros**: deterministic, auditable, single source of truth.
- **Cons**: requires maintaining a stable mapping (acceptable for reproducibility).

### Option B: Retrieval in S4 (prompt composer loads blueprint text)
- S4 loads blueprint text based on `blueprint_id` in ImageSpec.
- **Pros**: keeps S3 thinner.
- **Cons**: pushes non-trivial logic into S4 (we currently keep S4 render-only).

## Phased plan

### Phase 0: Schema v2 + deterministic checks (current work)
- Implement `image_hint_v2` and propagate through validators.
- S3 compiles `constraint_block` and sets `requires_human_review` (soft gate).
- Evaluate via S5 categories: laterality/adjacency/topology errors.

### Phase 1: Blueprint library + deterministic retrieval
- Add `blueprints/` directory with a small starter set (self-authored or open-licensed).
- Implement deterministic retrieval (Option A).
- Add audit tooling: record `blueprint_id` per image spec/manifest.

### Phase 2: Optional verification gate
- Add verification (VLM self-check or human-in-the-loop) triggered by `requires_human_review`.
- Output structured error categories compatible with S5 rating schema.

## Verification gates (recommended)
- **Soft gate**: if `requires_human_review=true`, still generate conservative diagram but mark for review.
- **Hard gate (future, selective)**: for high-risk topology tasks (post-op anatomy), require blueprint grounding or human approval.


