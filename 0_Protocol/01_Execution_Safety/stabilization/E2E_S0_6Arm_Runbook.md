# E2E S0 6-Arm Runbook

**Status:** Canonical  
**Version:** 1.0  
**Frozen:** No  
**Supersedes:** N/A  
**Last Updated:** 2025-12-19 (Asia/Seoul)

## 1) Purpose

Run **E2E-only** comparisons for **S0 mode** across **6 arms (A–F)**, where **the entire chain is evaluated as a single deliverable**:

> **S1 → S1 Gate (fail-fast) → S0 Allocation (recording, 12 fixed cards) → S2 execution**

This runbook ensures:
- **Table is treated as a first-class deliverable** via S1 Gate enforcement.
- **Arm-level fairness** via **fixed payload size (12 cards per group)** in S0.
- **Deterministic selection and reproducible artifacts** sufficient for QA, audit, and debugging.

## 2) Scope and Non-Scope

### 2.1 Scope
- Mode: **S0**
- Comparison: **E2E-only** (do not attempt to “equalize entity sets” across arms)
- Arms: **A–F** (6 arms)
- Input: identical group objectives (same `groups_canonical.csv` row set / group set)

### 2.2 Non-Scope
- FINAL allocation policies (weights, quotas, optimization) are **forbidden** in S0.
- “Best arm” selection logic belongs to analysis/QC, not to allocation.
- Image pipeline (S3/S4) is out of this runbook unless explicitly added later.

## 3) Normative References

This runbook is an **operational wrapper**. The following canonical documents are binding:
- `0_Protocol/01_Execution_Safety/stabilization/s_1_gate_checklist_canonical.md` (S1 Gate)
- `0_Protocol/.../S0_Allocation_Artifact_Spec.md` (S0 Allocation Artifact Specification v2.1)

## 4) Key Definitions

- **RUN_TAG**: unique identifier for one experiment execution batch.
- **Arm**: model/provider configuration slot (A–F).
- **Group**: the unit of curriculum structuring (1 group → 1 table + N entities).
- **E2E-only**: evaluate the complete pipeline output (S1 table + chosen entities + S2 questions/cards).

## 5) Hard Invariants (E2E S0)

1) **S1 Gate must pass** before anything downstream runs.
2) **S0 allocation is a recording step**:
   - `set_target_cards == 12`
   - deterministic **3×4** policy:
     - If `E >= 4`: choose first 4 entities, assign 3 cards each.
     - If `E < 4`: deterministic even split across all entities.
3) **S2 must exactly honor allocation**:
   - must generate exactly `cards_for_entity_exact` per selected entity
   - must generate total cards == 12

## 6) Required Artifacts and Canonical Paths

### 6.1 S1 / Gate artifacts
- **Required**
  - `2_Data/metadata/generated/{RUN_TAG}/stage1_struct.jsonl`

### 6.2 S0 allocation artifact (required)
- **Canonical path**
```text
2_Data/metadata/generated/{RUN_TAG}/allocation/
└── allocation_s0__group_{GROUP_ID}__arm_{ARM}.json
```

### 6.3 S2 output (recommended to standardize)
- Recommended location/pattern (adapt to your repo’s current behavior):
```text
2_Data/metadata/generated/{RUN_TAG}/stage2/
└── output_stage2__group_{GROUP_ID}__arm_{ARM}.jsonl
```

## 7) Failure Codes (Operational Standard)

This section defines **run-level failure codes** used by the runner and summary CSV.

### 7.1 Exit codes

| Exit Code | Meaning | Notes |
| --- | --- | --- |
| 0 | PASS | PASS may still include warnings |
| 3 | S1 Gate FAIL | Must follow S1 Gate canonical recommendation |
| 4 | S0 Allocation FAIL | Artifact missing/invalid or violates v2.1 constraints |
| 5 | S2 Execution FAIL | Missing outputs, wrong card counts, schema break, etc. |
| 6 | Unexpected exception | Runtime crash, uncaught exception |

### 7.2 S1 Gate failure “levels” (for logging)

S1 Gate includes the following fail-fast levels. Log `s1_gate_level` when exit code is 3.

| s1_gate_level | Name |
| --- | --- |
| 0 | Existence |
| 1 | NDJSON parseability |
| 2 | Schema conformance |
| 3 | Master table hard constraints |
| 4 | Table↔Entity alignment |
| 5 | Backward compatibility & forbidden fields |
| 6 | Required warning policy for 15–20 rows (binding) |
| 7 | Minimal QA usability (warn-only) |

**Pass criterion (binding):** Levels 0–5 must pass, Level 6 must be satisfied when applicable; Level 7 is warn-only.

## 8) Preflight Checklist (Before Running)

### 8.1 Environment invariants
- You are in repo root:
  - `/path/to/workspace/workspace/MeducAI`
- `RUN_TAG` is unique for this batch (recommend timestamp).
- Same prompt bundle version, same code version, same environment across all arms.
- Group set is fixed (same groups for all arms).

### 8.2 Quick sanity checks
- `groups_canonical.csv` exists and is the single source of truth for group inputs.
- S1 gate validator script is available and corresponds to the canonical checklist.
- Allocation writer/validator implements v2.1 structural/arithmetic/referential rules.

## 9) Execution Checklist (Per RUN_TAG)

### 9.1 RUN_TAG naming (recommended)
```bash
export RUN_TAG="E2E_S0_6ARM_$(date +%Y%m%d_%H%M%S)"
```

### 9.2 Execution order (recommended)
For each **group** in the fixed group set, run arms **A → F** in a stable order.

For each (group, arm):

1) **Run S1** (and/or full generator step that produces `stage1_struct.jsonl`)
2) **Run S1 Gate** (fail-fast)
3) **If PASS:** write **allocation artifact** for (group, arm) under canonical path
4) **Run S2** strictly using the allocation artifact
5) **Validate S2 counts** against allocation artifact
6) **Append a summary row** to run summary CSV

### 9.3 Fail-fast rules
- If S1 Gate FAIL (exit 3): record failure and **skip S0 allocation and S2** for that (group, arm).
- If allocation FAIL (exit 4): record failure and **skip S2**.
- If S2 FAIL (exit 5/6): record failure and continue to next arm (unless you choose to stop entire batch).

## 10) Minimal Validation Checklists (Binding)

### 10.1 S1 Gate (binding)
- Must produce `stage1_struct.jsonl`
- Must pass S1 Gate validator (Levels 0–5 + Level 6 when applicable)

### 10.2 S0 Allocation (binding)
- Artifact exists at canonical path
- Must satisfy:
  - `mode == "S0"`
  - `allocation_version == "S0-Allocation-v2.1"`
  - `set_target_cards == 12`
  - `selected_entities.length == min(4, len(entities_from_s1))`
  - `Σ(cards_for_entity_exact) == 12`
  - Referential integrity: `selected_entities ⊆ entities_from_s1`, allocations refer only to selected entities
  - If `len(entities_from_s1) >= 4`: exactly 4 entities and all `cards_for_entity_exact == 3`

### 10.3 S2 (binding)
- S2 must honor allocation artifact:
  - For each `entity_allocations[]`, generated cards == `cards_for_entity_exact`
  - Total generated cards == 12

## 11) Summary CSV (One file per RUN_TAG)

Write a single summary CSV that can be analyzed without opening raw jsonl files.

### 11.1 Canonical path (recommended)
```text
2_Data/metadata/generated/{RUN_TAG}/summary/
└── e2e_s0_6arm_summary.csv
```

### 11.2 Required columns

| Column | Type | Description |
| --- | --- | --- |
| run_tag | str | RUN_TAG |
| group_id | str | Group identifier |
| arm | str | A–F |
| status | str | PASS / FAIL |
| exit_code | int | 0/3/4/5/6 |
| failed_stage | str | S1 / S1_GATE / ALLOC / S2 / RUNTIME |
| s1_gate_level | int | 0–7 (only if exit_code==3) |
| s1_gate_reason | str | Short reason string |
| table_rows | int | Data row count (from S1 integrity) |
| entity_count | int | len(entity_list) |
| selected_entities | str | JSON-string list of selected entity_names or ids |
| allocation_total_cards | int | Must be 12 if PASS beyond allocation |
| allocation_policy | str | e.g., deterministic_prefix / fallback_even_split |
| s2_cards_expected | int | Always 12 when allocation exists |
| s2_cards_generated | int | Derived from S2 output |
| warnings_count | int | Count of warnings (gate + allocation + s2) |
| notes | str | Free text (optional) |

### 11.3 Optional but highly useful columns
- `table_fingerprint_sha256` (sha256 of `master_table_markdown`)
- `entity_fingerprint_sha256` (sha256 of ordered selected_entities list)
- `latency_s1_sec`, `latency_s2_sec`, `latency_total_sec`
- `cost_estimate_usd` (if available)
- `model_stage1`, `model_stage2` (resolved model identifiers)
- `provider` (gemini/openai/etc.)

## 12) S0 Non-Inferiority Analysis (Post-Execution)

After QA evaluation data is collected, run non-inferiority analysis to select the deployment arm.

### 12.1 Canonical Reference

- **Criteria:** `0_Protocol/06_QA_and_Study/QA_Operations/S0_Noninferiority_Criteria_Canonical.md`
- **Script:** `3_Code/src/tools/qa/s0_noninferiority.py`

### 12.2 Input Data Format

Input CSV must be in "long format" (one row per card) with columns:
- `run_tag`, `arm`, `group_id`, `rater_id`, `card_id`, `accuracy_score` (required)
- `entity_id`, `editing_time_sec` (optional)

### 12.3 Analysis Command

```bash
python 3_Code/src/tools/qa/s0_noninferiority.py \
  --input_csv 2_Data/metadata/generated/{RUN_TAG}/qa/qa_long_format.csv \
  --baseline_arm A \
  --delta 0.05 \
  --ci 0.90 \
  --bootstrap_n 5000 \
  --seed 20251220 \
  --out_dir 2_Data/metadata/generated/{RUN_TAG}/qa/
```

### 12.4 Output Artifacts

Outputs are written to `{out_dir}/`:
- `qa_s0_noninferiority_summary.csv` - Per-arm results with pass/fail flags
- `qa_s0_noninferiority_decision.md` - Copy-paste-ready decision summary
- `qa_s0_noninferiority_bootstrap_meta.json` - Reproducibility metadata

### 12.5 Decision Rules

1. **Safety gate:** `UpperCI(RD0) ≤ 0.02` (prevents unacceptable major error increases)
2. **NI gate:** `LowerCI(d) > -Δ` (ensures non-inferiority on mean accuracy)
3. **Final pass:** Both safety and NI must pass
4. **Selection:** Among final_pass arms, choose lowest cost

**Note:** The NI margin Δ is set to 0.05 (default) to be meaningful under S0's fixed 12-card payload. Larger values (0.5, 1.0) are invalid as they would allow 6–12 points per set degradation.

## 13) Triage Guide (What to do when it fails)

### 13.1 Frequent failure clusters
- **Level 3 (table hard constraints):** header mismatch, wrong column count, empty cells, multiline, `|` inside cells, rows>20
- **Level 4 (alignment):** entity_list length differs from rows; entity_name not sourced from entity label column; ordering mismatch
- **Allocation fail:** missing artifact, wrong version, sum != 12, wrong 3×4 enforcement
- **S2 fail:** generated cards count mismatch vs allocation

### 13.2 First triage actions
1) Open validator output log (keep the exact failure reason).
2) Open the failing `stage1_struct.jsonl` record for that group.
3) Confirm table markdown complies (exact header & 6 columns).
4) Confirm entity_list matches table rows 1:1.
5) Confirm allocation artifact sums to 12 and respects 3×4.
6) For S2 mismatch, compute counts per entity and compare to `entity_allocations`.

## 14) Example Commands (Single group / single arm)

> Adapt flags to your current scripts; this section is illustrative.

### 14.1 S1 + S2 통합 실행 (기본)

```bash
cd /path/to/workspace/workspace/MeducAI
export RUN_TAG="E2E_S0_6ARM_$(date +%Y%m%d_%H%M%S)"

# 1) Run generation for one group (S1 + S2)
python 3_Code/src/01_generate_json.py --base_dir . --run_tag "$RUN_TAG" --arm A --mode S0 --row_index 25

# 2) S1 Gate
python 3_Code/src/validate_stage1_struct.py --base_dir . --run_tag "$RUN_TAG"
echo $?
```

### 14.2 S1 → S2 분리 실행 (권장)

```bash
cd /path/to/workspace/workspace/MeducAI
export RUN_TAG="E2E_S0_6ARM_$(date +%Y%m%d_%H%M%S)"

# 1) Stage 1만 실행
python 3_Code/src/01_generate_json.py --base_dir . --run_tag "$RUN_TAG" --arm A --mode S0 --stage 1 --row_index 25

# 2) S1 Gate
python 3_Code/src/validate_stage1_struct.py --base_dir . --run_tag "$RUN_TAG"
echo $?

# 3) Allocation 생성 (S0 모드)
python 3_Code/src/tools/allocation/s0_allocation.py --base_dir . --run_tag "$RUN_TAG" --arm A

# 4) Stage 2만 실행 (기존 S1 출력 사용)
python 3_Code/src/01_generate_json.py --base_dir . --run_tag "$RUN_TAG" --arm A --mode S0 --stage 2 --row_index 25
```

### 14.3 6 Arm 순차 실행 (S1 → S2 분리)

```bash
cd /path/to/workspace/workspace/MeducAI
export RUN_TAG="E2E_S0_6ARM_$(date +%Y%m%d_%H%M%S)"

# Stage 1: 모든 arm 실행
for arm in A B C D E F; do
  python 3_Code/src/01_generate_json.py --base_dir . --run_tag "$RUN_TAG" --arm $arm --mode S0 --stage 1 --sample 1
done

# S1 Gate 검증
python 3_Code/src/validate_stage1_struct.py --base_dir . --run_tag "$RUN_TAG"

# Allocation 생성
for arm in A B C D E F; do
  python 3_Code/src/tools/allocation/s0_allocation.py --base_dir . --run_tag "$RUN_TAG" --arm $arm
done

# Stage 2: 모든 arm 실행
for arm in A B C D E F; do
  python 3_Code/src/01_generate_json.py --base_dir . --run_tag "$RUN_TAG" --arm $arm --mode S0 --stage 2 --sample 1
done
```

## 15) File Replacement Workflow (Download → Move into repo)

After downloading the updated runbook into your default Downloads folder:

```bash
cd /path/to/workspace/workspace/MeducAI
mv /path/to/workspace/Downloads/E2E_S0_6Arm_Runbook.md \
  0_Protocol/01_Execution_Safety/stabilization/E2E_S0_6Arm_Runbook.md
```

---
