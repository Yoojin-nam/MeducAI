## Purpose
This document audits the **S2 → S3 → S4 data contract** used for medical illustration generation and identifies which missing/under-specified fields are most likely responsible for anatomical failures (laterality, adjacency, topology, connectivity).

It also proposes a backward-compatible **Schema v2** (`image_hint_v2`) and describes where enforcement gates should live while preserving the principle that **S3 is a compiler, not a generator**.

## Fixtures audited (as-run artifacts)
All numbers below are computed from this run directory:
- `2_Data/metadata/generated/RANDOM_3GRP_20251227_080551/s2_results__s1armA__s2armA.jsonl`
- `2_Data/metadata/generated/RANDOM_3GRP_20251227_080551/s3_image_spec__armA.jsonl`
- `2_Data/metadata/generated/RANDOM_3GRP_20251227_080551/s4_image_manifest__armA.jsonl`

## Field coverage (observed)

### S2 record-level fields (n=21)
| Field | Present | Missing |
|---|---:|---:|
| schema_version | 21 | 0 |
| run_tag | 21 | 0 |
| arm | 21 | 0 |
| group_id | 21 | 0 |
| group_path | 21 | 0 |
| entity_id | 21 | 0 |
| entity_name | 21 | 0 |
| cards_for_entity_exact | 21 | 0 |
| anki_cards | 21 | 0 |

### S2 card-level fields (n=42 cards)
| Field | Present | Missing |
|---|---:|---:|
| card_role | 42 | 0 |
| card_type | 42 | 0 |
| front | 42 | 0 |
| back | 42 | 0 |
| tags | 42 | 0 |
| image_hint (v1) | 42 | 0 |
| image_hint_v2 | 0 | 42 |
| options (MCQ only) | 21 | 21 |
| correct_index (MCQ only) | 21 | 21 |

### S2 `image_hint` subfields (n=42 image_hint objects)
| Field | Present | Missing |
|---|---:|---:|
| modality_preferred | 42 | 0 |
| anatomy_region | 42 | 0 |
| key_findings_keywords | 42 | 0 |
| view_or_sequence | 42 | 0 |
| exam_focus | 42 | 0 |

### S3 ImageSpec fields (n=47 specs; includes clustered table visuals)
| Field | Present | Missing |
|---|---:|---:|
| schema_version / run_tag / group_id / spec_kind / template_id / prompt_en | 47 | 0 |
| entity_id / entity_name / card_role (card specs only) | 42 | 5 |
| modality / anatomy_region / key_findings_keywords / view_or_sequence / exam_focus (card specs only) | 42 | 5 |
| cluster_id (table cluster visuals only) | 4 | 43 |
| constraint_block | 0 | 47 |
| image_hint_v2 | 0 | 47 |
| requires_human_review | 0 | 47 |

### S4 manifest fields (n=47)
| Field | Present | Missing |
|---|---:|---:|
| schema_version / run_tag / group_id / spec_kind / media_filename / image_path / generation_success / image_required / rag_enabled | 47 | 0 |
| entity_id / card_role (card specs only) | 42 | 5 |
| cluster_id (cluster table visuals only) | 4 | 43 |

**Key take-away**: The current pipeline is structurally stable for v1 fields, but provides **no structured constraints for anatomy grounding** (`image_hint_v2` absent), and therefore cannot reliably prevent laterality/adjacency/topology errors.

## Data-flow diagram (contract)

```mermaid
flowchart LR
  S1[S1_struct.json] -->|visual_type_category, master_table_markdown_kr| S3
  S1 -->|optional: entity_clusters + infographic_clusters| S3

  S2[S2_results.jsonl] -->|anki_cards[].image_hint| S3
  S2 -->|anki_cards[].image_hint_v2 (v2)| S3

  S3[S3 compiler] -->|s3_image_spec.jsonl: prompt_en, template_id, spec_kind| S4
  S3 -->|image_policy_manifest.jsonl| Exporters

  S4[S4 image generator] -->|s4_image_manifest.jsonl| Exporters
  Exporters --> PDF[PDF/Anki export]
```

## Where fields are used / enforced (code audit)

### S3 enforcement for EXAM card images
S3 requires a minimal v1 `image_hint` for Q1/Q2 in the EXAM lane:

```570:603:3_Code/src/03_s3_policy_resolver.py
    # P0: Q1 and Q2 must meet minimum modality/anatomy/keywords or FAIL (EXAM lane only)
    if card_role in ("Q1", "Q2"):
        if not modality or modality == "Other":
            raise ValueError(
                f"S3 ImageSpec FAIL: {card_role} must have valid modality_preferred. "
                f"Entity: {entity_name}, Got: {modality}"
            )
        if not anatomy_region:
            raise ValueError(
                f"S3 ImageSpec FAIL: {card_role} must have anatomy_region. "
                f"Entity: {entity_name}"
            )
        if not key_findings:
            raise ValueError(
                f"S3 ImageSpec FAIL: {card_role} must have key_findings_keywords. "
                f"Entity: {entity_name}"
            )
```

### S4 prompt consumption
S4 uses `prompt_en` from S3 ImageSpec; the EXAM prompt template already enforces a conservative diagram style and forbids UI/photorealism, but **does not encode spatial/topology constraints unless we add them**:
- Template: `3_Code/prompt/S4_EXAM_USER__v8_DIAGRAM_4x5_2K.md`

## Failure analysis: which missing fields likely cause anatomy errors?

### Most likely root causes (high leverage)
- **Laterality** missing: v1 provides no explicit L/R constraint; anatomy_region strings are often ambiguous.
- **Landmarks** missing: without required landmarks, localization becomes underconstrained and the model “guesses”.
- **Adjacency/ordering** missing: many errors are relationship errors (what touches what), not just object identity errors.
- **Topology/connectivity** missing: post-op anatomy and conduits (anastomoses, bypass limbs) are fundamentally graph constraints.

### Secondary contributors
- **Rendering policy**: style drift (scan-like) can encourage the model to invent detail. Explicit “diagrammatic” constraints help reduce hallucination.

## Proposed Schema v2 (backward compatible)
We introduce an additive field on S2 card objects:
- `image_hint_v2` (schema: `0_Protocol/04_Step_Contracts/Step02_S2/S2_Image_Hint_Schema_v2.json`)

S3 behavior:
- If `image_hint_v2` exists, S3 compiles a short deterministic `constraint_block` and injects it into S4 prompts.
- If constraints are insufficient, S3 sets `requires_human_review=true` (soft gate) and keeps prompts conservative.

S1 clustering behavior (optional):
- `infographic_clusters[].infographic_hint_v2` provides cluster-level constraints for table visuals.

## Verification gates (proposed)
To preserve “S3 is a compiler”, we propose **soft gates** that only mark/reroute:
- **S2 gate (generation-time)**: encourage `requires_human_review=true` when laterality/topology cannot be stated.
- **S3 gate (compile-time)**: deterministic sufficiency flags; do not invent constraints.
- **S5 gate (evaluation-time)**: human/VLM checks for laterality/adjacency/topology categories (recommended for paper). 


