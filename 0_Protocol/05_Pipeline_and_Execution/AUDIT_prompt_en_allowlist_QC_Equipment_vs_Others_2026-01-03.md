# FINAL_DISTRIBUTION prompt_en + allowlist audit (QC/Equipment vs others)

- Source: `/path/to/workspace/workspace/MeducAI/2_Data/metadata/generated/FINAL_DISTRIBUTION/missing_table_cluster_specs__armG.jsonl`
- Total records: **703**

## Aggregate comparison (QC/Equipment vs others)

| group | n | prompt_len_mean | allow_en_mean | allow_kr_mean | exam_tokens_mean | exam_tokens_covered_kr_mean | exam_tokens_covered_en_mean | headings_% | mentions_16:9_% | mentions_4K_% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QC+Equipment | 83 | 2442 | 30.2 | 5.6 | 5.5 | 0.602 | 0.000 | 89.2 | 0.0 | 0.0 |
| Others | 620 | 2500 | 19.6 | 5.5 | 5.4 | 0.668 | 0.000 | 95.8 | 0.0 | 0.0 |

## Per visual_type_category summary

| visual_type_category | n | prompt_len_mean | allow_en_mean | allow_kr_mean | exam_tokens_mean | exam_tokens_covered_kr_mean | headings_% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Anatomy_Map | 121 | 2421 | 15.9 | 5.1 | 5.0 | 0.579 | 96.7 |
| Equipment | 64 | 2450 | 29.6 | 4.7 | 4.6 | 0.516 | 93.8 |
| General | 112 | 2305 | 19.3 | 5.1 | 4.9 | 0.625 | 92.0 |
| Pathology_Pattern | 366 | 2591 | 20.8 | 5.7 | 5.6 | 0.705 | 97.3 |
| Pattern_Collection | 16 | 2551 | 22.1 | 7.6 | 7.4 | 0.812 | 81.2 |
| Physiology_Process | 5 | 1970 | 15.4 | 4.4 | 4.4 | 0.600 | 100.0 |
| QC | 19 | 2413 | 32.4 | 8.7 | 8.5 | 0.895 | 73.7 |

## Example prompt heads (deterministic samples)

These are **first ~160 chars** of `prompt_en`, plus two allowlist coverage metrics:
- `allow_used_ratio`: prompt contains tokens from `allowed_text_en` (often ~1.0 if the allowlist block is embedded into the prompt)
- `exam_tokens_covered_kr_ratio`: fraction of `exam_point_tokens_by_entity` tokens present in `allowed_text_kr` (proxy for allowlist coverage of key points)

### QC

| group_id | cluster_id | allow_used_ratio | exam_tokens_covered_kr_ratio | headings | 16:9 | 4K | prompt_en_head |
| --- | --- | --- | --- | --- | --- | --- | --- |
| grp_04ebe2f561 | cluster_1 | 1.000 | 1.000 | Y | N | N | A schematic educational diagram comparing a 'Pass' vs 'Fail' Chest X-ray for Quality Control. The 'Pass' side shows perfect collimation, clear ID marker, scapul |
| grp_87b897b492 | cluster_2 | 1.000 | 1.000 | Y | N | N | A composite infographic showing a Mammography QC schedule calendar (Daily/Weekly/Quarterly), a wire mesh test pattern for screen-film contact, and a schematic o |
| grp_ab47b2ea4c | cluster_1 | 1.000 | 1.000 | Y | N | N | A technical diagram of a cylindrical MRI phantom (ACR style) with callouts indicating the 7 key quality control tests: geometric accuracy (grid), spatial resolu |

### Equipment

| group_id | cluster_id | allow_used_ratio | exam_tokens_covered_kr_ratio | headings | 16:9 | 4K | prompt_en_head |
| --- | --- | --- | --- | --- | --- | --- | --- |
| grp_142d2d4f96 | cluster_1 | 1.000 | 1.000 | Y | N | N | A schematic diagram of a pediatric fluoroscopy setup focusing on radiation safety. Show an immobilization device (Octostop) on the table. Highlight technical ad |
| grp_7810a86b7b | cluster_1 | 1.000 | 0.000 | N | N | N | A comparative medical imaging diagram showing Pancreas CT phases and MRI sequences. Top panel: Timeline of CT enhancement showing 'Parenchymal Phase' (pancreas  |
| grp_7810a86b7b | cluster_2 | 1.000 | 0.000 | Y | N | N | A side-by-side comparison diagram of MRCP and ERCP. Left side (MRCP): A high-contrast black-and-white 3D rendering of the biliary tree and pancreatic duct, labe |

### Anatomy_Map

| group_id | cluster_id | allow_used_ratio | exam_tokens_covered_kr_ratio | headings | 16:9 | 4K | prompt_en_head |
| --- | --- | --- | --- | --- | --- | --- | --- |
| grp_01eafd919c | cluster_1 | 1.000 | 1.000 | Y | N | N | Schematic diagram of axial brain MRI slices at multiple levels (basal ganglia, midbrain, centrum semiovale). Highlight locations of physiological calcification  |
| grp_83c32c3b78 | cluster_1 | 1.000 | 0.000 | Y | N | N | A set of axial brain diagrams representing normal perfusion SPECT anatomy. The images should highlight and label the Frontal, Temporal, Parietal, and Occipital  |
| grp_83c32c3b78 | cluster_2 | 1.000 | 0.000 | Y | N | N | An axial brain map illustrating the major cerebral vascular territories. The diagram should clearly demarcate the Anterior Cerebral Artery (ACA) territory along |

### General

| group_id | cluster_id | allow_used_ratio | exam_tokens_covered_kr_ratio | headings | 16:9 | 4K | prompt_en_head |
| --- | --- | --- | --- | --- | --- | --- | --- |
| grp_023bfc5260 | cluster_1 | 1.000 | 1.000 | Y | N | N | A detailed medical diagram illustrating the mechanism of MIBG uptake. Central focus on a chromaffin cell membrane with the Norepinephrine Transporter (NET/Uptak |
| grp_6d0f5b77d8 | cluster_2 | 1.000 | 0.000 | Y | N | N | Cross-sectional anatomical diagram of the chest wall during thoracentesis. Shows a needle entering the pleural space just SUPERIOR to the lower rib to avoid the |
| grp_6d0f5b77d8 | cluster_3 | 1.000 | 0.000 | Y | N | N | Comparative CT schematic of pleural pathologies. Panel A: 'Split Pleura Sign' showing thickened, enhancing visceral and parietal pleura separated by fluid (Empy |

### Pathology_Pattern

| group_id | cluster_id | allow_used_ratio | exam_tokens_covered_kr_ratio | headings | 16:9 | 4K | prompt_en_head |
| --- | --- | --- | --- | --- | --- | --- | --- |
| grp_00f47434c9 | cluster_1 | 1.000 | 1.000 | Y | N | N | Schematic diagram comparing mechanical complications after gastrectomy. Panel A: Afferent Loop Syndrome showing a dilated, fluid-filled duodenal C-loop blocked  |
| grp_8447fb3679 | cluster_1 | 1.000 | 1.000 | Y | N | N | Medical illustration set of cervical spine fractures: Jefferson fracture (C1 burst) in open mouth view, Hangman's fracture (C2 pars) in lateral view, Flexion Te |
| grp_8447fb3679 | cluster_2 | 1.000 | 1.000 | Y | N | N | Medical illustration comparison of spinal trauma: Burst fracture with retropulsion vs Benign compression wedge vs Pathologic compression with convex border. Inc |

## Notes on interpretation

- `allow_used_ratio` can be artificially high if the spec builder appends the allowlist into the prompt as a literal block (i.e., the prompt *contains* the allowlist).
- `exam_tokens_covered_kr_ratio` is a more direct check: whether the *key exam-point tokens* are actually included in the KR allowlist.
- `headings_%` is a heuristic for template-like prompts (multiple `Heading:` patterns). QC/Equipment templates often show up as higher here.
- If future specs add explicit markers (e.g., `ALLOWED_TEXT` blocks inside `prompt_en`), this audit can be tightened to parse those sections directly.
