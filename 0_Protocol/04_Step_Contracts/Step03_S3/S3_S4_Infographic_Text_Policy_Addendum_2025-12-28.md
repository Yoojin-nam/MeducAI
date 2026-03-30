# S3→S4 Infographic Text Policy Addendum (2025-12-28)

- Status: Addendum (Operational) · Non-breaking to the frozen canonical contract
- Applies to: `spec_kind="S1_TABLE_VISUAL"` only (infographic lane)
- Scope: Text stability + richer exam-point signaling (up to 2 tokens) **without OCR**
- Implementation: `3_Code/src/03_s3_policy_resolver.py`, `3_Code/prompt/S4_CONCEPT_*__v3.md`

## 0) Why this addendum exists
`0_Protocol/04_Step_Contracts/S3_to_S4_Input_Contract_Canonical.md` is marked **Frozen** (2025-12-20).
Since then, we added **new optional fields** to `S1_TABLE_VISUAL` specs to:
- reduce infographic typos/hallucinated text,
- allow **more useful exam-point text** (1–2 short tokens),
- strengthen QC/Equipment infographic behavior via **profile metadata**,
- keep deterministic compilation (S3 is still a compiler; no OCR step).

This addendum documents those extensions so QA and operators can audit runs.

## 1) What changed (normative for new runs)

### 1.1 S3 adds text-policy metadata to `S1_TABLE_VISUAL`
S3 now outputs these additional keys in each `S1_TABLE_VISUAL` spec (in `s3_image_spec__armX.jsonl`):
- `infographic_profile`: `default` | `qc_equipment`
- `text_budget_profile`: `default_exampoint2` | `qc_equipment_richer`
- `allowed_text_en`: list[str] (table-derived, conservative allowlist)
- `allowed_text_kr`: list[str] (table-derived exam-point tokens)
- `exam_point_tokens_by_entity`: dict[str, list[str]] (0–2 tokens per entity)
- `allowed_text_hash`: short hash for audit/debug

**Notes**
- These fields are computed **deterministically** from `master_table_markdown_kr_original` / compact table artifacts.
- No OCR is performed. Enforcement is **prompt-level** + S3 smoke checks.

### 1.2 S3 injects an `ALLOWED_TEXT` block into `prompt_en`
For `S1_TABLE_VISUAL`, S3 appends a final block:
- `ALLOWED_TEXT (AUTHORITATIVE): ...`
- `EXAM_POINT_TOKENS_BY_ENTITY ...`

S4 must treat `prompt_en` as read-only (same as the canonical contract).

### 1.3 S4_CONCEPT prompts allow 1–2 exam-point lines
All `S4_CONCEPT_USER__*__v3.md` prompts were updated:
- 시험포인트 line count: **EXACTLY ONE → 1–2 lines** (each 1–3 words)

`S4_CONCEPT_SYSTEM__v3.md` additionally states:
- the model will receive an **ALLOWED_TEXT** block and MUST compose text only from allowed tokens/phrases.

## 2) QC/Equipment behavior (profile-based)
S3 sets:
- `infographic_profile=qc_equipment` when `visual_type_category in ("QC","Equipment")`
- `text_budget_profile=qc_equipment_richer`

The allowed-text allowlist for EN additionally includes **safe structural labels** (e.g., `Acquire/Measure/Compare/Action`, `Metric:`).

## 3) Compatibility and risk notes
- This addendum does **not** require a schema bump because the JSONL is tolerant of additional keys.
- Downstream consumers that ignore unknown keys continue to function.
- The stronger enforcement is *prompt-level*; without OCR, image text may still deviate in rare cases, but this reduces drift substantially.

## 4) Operator verification checklist (quick)
- Confirm `S1_TABLE_VISUAL` specs contain:
  - `allowed_text_en`, `allowed_text_kr`, `exam_point_tokens_by_entity`
  - `prompt_en` contains `ALLOWED_TEXT (AUTHORITATIVE):`
- Confirm `S4` generated all table visuals:
  - `s4_image_manifest__armX.jsonl` has `spec_kind="S1_TABLE_VISUAL"` entries with `generation_success=true`


