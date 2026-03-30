# Infographic text policy (no OCR)

This policy describes how we stabilize infographic text for `S1_TABLE_VISUAL` while allowing richer **exam-point** signaling (up to 2 tokens) and keeping medical accuracy.

## Summary
- **Source of truth**: S1 master table content only (no invention).
- **Text contract**: S3 computes **allowed-text** deterministically and injects an `ALLOWED_TEXT` block into the S4_CONCEPT prompt.
- **No OCR**: There is **no image-side OCR validation**. Quality is enforced by **prompt contract + S3 smoke checks**.

## What S3 adds to each `S1_TABLE_VISUAL` spec
In `s3_image_spec__arm*.jsonl`, each infographic spec includes:
- `infographic_profile`: `default` or `qc_equipment`
- `text_budget_profile`: `default_exampoint2` or `qc_equipment_richer`
- `allowed_text_en`: list of allowed English tokens/phrases (table-derived, conservative)
- `allowed_text_kr`: list of allowed Korean tokens/phrases (from 시험포인트 extraction)
- `exam_point_tokens_by_entity`: `{entity_name: [token1, token2]}` (0–2 tokens, deterministic)
- `allowed_text_hash`: short hash for audit/debug

## Exam-point rule (up to 2 tokens)
- For each entity, S3 extracts **up to 2 short tokens** from the table `"시험포인트"` cell.
- Each token is capped to **≤ 3 words** (deterministic truncation).
- If the 시험포인트 is empty/unclear, the list can be empty.

## Prompt-side enforcement
S4_CONCEPT prompts are updated to:
- Expect an `ALLOWED_TEXT` block
- Require that **all text on the slide is composed only from allowed tokens/phrases**
- Allow **1–2 시험포인트 lines** when non-empty (instead of exactly 1)

## QC/Equipment profile behavior
- `infographic_profile=qc_equipment` enables a **richer text budget** (still table-derived).
- Structural labels (e.g., `Acquire / Measure / Compare / Action`) are allowed as part of the policy (and included in allowed EN tokens).

## Troubleshooting
- If an infographic contains unexpected text, first check the corresponding `S1_TABLE_VISUAL` spec:\n
  - Confirm `allowed_text_en/kr` look correct\n
  - Confirm `exam_point_tokens_by_entity` looks reasonable\n
  - Confirm the prompt contains the appended `ALLOWED_TEXT` block\n
- If tokens are missing:\n
  - Ensure the source master table includes `"시험포인트"` column\n
  - Ensure the table rows are valid markdown table rows (pipes align)\n


