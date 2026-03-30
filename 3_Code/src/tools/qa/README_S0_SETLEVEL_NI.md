# S0 Set-Level Non-Inferiority Analysis

## Overview

This directory contains scripts for S0 non-inferiority analysis using **Set-level Overall Card Quality (1–5 Likert)** as the primary endpoint.

**Canonical Specification:** See `0_Protocol/06_QA_and_Study/QA_Operations/S0_Noninferiority_Criteria_Canonical.md`

## Key Design Decisions

- **Primary Endpoint:** Set-level Overall Card Quality (1–5 Likert)
- **Non-inferiority Margin (Δ):** 0.5 (half of one Likert step)
- **Baseline Arm:** E (High-End, assumed highest quality)
- **Candidate Arms:** A, B, C, D (primary decision targets)
- **Benchmark Arm:** F (ChatGPT, secondary reference, excluded from primary decision)
- **Statistical Method:** Group-cluster bootstrap (10,000 resamples, seed=123)
- **Multiple Comparisons:** Holm correction (default ON)

## Scripts

### 1. `build_set_long_from_google_form.py`

Converts Google Form export (wide format) to set_long format for analysis.

**Input:**
- Google Form CSV (wide format with columns like `[Q01] Overall Card Quality`, etc.)
- `assignment_map.csv` (reviewer_id, local_qid, set_id, group_id, arm_id, role)
- `reviewer_master.csv` (reviewer_id, reviewer_email, role, etc.)

**Output:**
- `set_long.csv` with columns: `run_tag`, `arm`, `group_id`, `set_id`, `rater_id`, `overall_quality_1to5`, ...

**Usage:**
```bash
python 3_Code/src/tools/qa/build_set_long_from_google_form.py \
  --google_form_csv data/google_form_responses.csv \
  --assignment_map_csv 1_Secure_Participant_Info/QA_Operations/assignment_map.csv \
  --reviewer_master_csv 1_Secure_Participant_Info/reviewer_master.csv \
  --run_tag S0_QA_2025-12-20 \
  --out_csv data/set_long.csv \
  --verbose
```

### 2. `s0_noninferiority_setlevel.py`

Performs set-level non-inferiority analysis.

**Input:**
- `set_long.csv` (set-long format, one row per set per rater)

**Output:**
- `s0_noninferiority_setlevel_summary.csv` (summary table)
- `s0_noninferiority_setlevel_results.json` (structured results)

**Usage:**
```bash
python 3_Code/src/tools/qa/s0_noninferiority_setlevel.py \
  --input_csv data/set_long.csv \
  --endpoint_col overall_quality_1to5 \
  --baseline_arm E \
  --candidate_arms A,B,C,D \
  --benchmark_arms F \
  --delta 0.5 \
  --n_boot 10000 \
  --seed 123 \
  --holm true \
  --out_json output/results.json \
  --out_csv output/summary.csv \
  --verbose
```

## Data Format

### Input: set_long.csv

Required columns:

| Column | Type | Description |
|--------|------|-------------|
| `run_tag` | str | Run identifier |
| `arm` | str | Arm identifier (A–F, E=baseline, F=benchmark) |
| `group_id` | str | Group identifier (1–18) |
| `set_id` | str | Set identifier (within group × arm) |
| `rater_id` | str | Rater identifier |
| `overall_quality_1to5` | int | Overall Card Quality score (1–5) |

Optional columns (future extensions):
- `blocking_error` (bool)
- `critical_error_table` (bool)
- `critical_error_infographic` (bool)
- `scope_failure` (bool)
- `editing_time_min` (float)
- `accuracy_set` (float) — **not used for primary NI**

### Output: summary.csv

| Column | Type | Description |
|--------|------|-------------|
| `arm` | str | Arm identifier |
| `role` | str | "baseline" \| "candidate" \| "benchmark" |
| `mean_score` | float | Mean Overall Card Quality score |
| `mean_diff_vs_baseline` | float | Mean difference vs baseline E |
| `lower_ci` | float | Lower CI bound (2.5th percentile) |
| `upper_ci` | float | Upper CI bound (97.5th percentile) |
| `ni_pass` | bool/NA | NI pass/fail (candidates only, benchmark=NA) |
| `n_groups_used` | int | Number of groups used in comparison |
| `groups_dropped_missing_baseline` | str | Comma-separated list of dropped groups |
| `holm_adjusted_p` | float/NA | Holm-adjusted p-value (candidates only) |
| `holm_pass` | bool/NA | Pass/fail after Holm correction (candidates only) |
| `note` | str | Additional notes |

## Statistical Methods

### Set-Level Aggregation

If multiple raters evaluate the same set `(group_id, arm, set_id)`, the mean across raters is used as the set-level score.

### Group-Cluster Bootstrap

1. **Resampling unit:** `group_id` (clusters)
2. For each bootstrap replicate:
   - Sample `group_id` values with replacement
   - Compute mean Overall Card Quality for each arm across sampled groups
   - Compute `d_j = mean_j - mean_E` for each candidate arm j
3. **CI construction:** Percentile CI
   - LowerCI: 2.5th percentile (one-sided α = 0.025)
   - UpperCI: 97.5th percentile

### Non-Inferiority Decision Rule

For each candidate arm j:
- **NI PASS if:** `LowerCI(d_j) > -0.5`
- **NI FAIL if:** `LowerCI(d_j) ≤ -0.5`

### Holm Correction

- Applied to candidates A, B, C, D only (4 comparisons)
- Controls family-wise error rate
- Default: ON (recommended)

## Example Workflow

### Step 1: Convert Google Form to set_long

```bash
python 3_Code/src/tools/qa/build_set_long_from_google_form.py \
  --google_form_csv "1_Secure_Participant_Info/raw_identifiable/[연구 참여 동의서] 전문의 시험 대비 MeducAI 사용자 평가 연구(응답).gsheet" \
  --assignment_map_csv 1_Secure_Participant_Info/QA_Operations/assignment_map.csv \
  --reviewer_master_csv 1_Secure_Participant_Info/reviewer_master.csv \
  --run_tag S0_QA_2025-12-20 \
  --out_csv 2_Data/processed/set_long.csv \
  --verbose
```

### Step 2: Run NI Analysis

```bash
python 3_Code/src/tools/qa/s0_noninferiority_setlevel.py \
  --input_csv 2_Data/processed/set_long.csv \
  --endpoint_col overall_quality_1to5 \
  --baseline_arm E \
  --candidate_arms A,B,C,D \
  --benchmark_arms F \
  --delta 0.5 \
  --n_boot 10000 \
  --seed 123 \
  --holm true \
  --out_json 2_Data/metadata/generated/S0_QA_2025-12-20/qa/s0_noninferiority_setlevel_results.json \
  --out_csv 2_Data/metadata/generated/S0_QA_2025-12-20/qa/s0_noninferiority_setlevel_summary.csv \
  --verbose
```

## Output Interpretation

### Summary CSV

- **Candidates (A–D):** Check `ni_pass` and `holm_pass` columns
  - Both must be `True` for arm to be eligible for final selection
  - Among passing arms, choose lowest cost

- **Benchmark (F):** 
  - `ni_pass` is `NA` (not applicable)
  - `mean_diff_vs_baseline` and CI are reported for reference only
  - **Not included in primary decision**

- **Baseline (E):**
  - `mean_diff_vs_baseline = 0.0` (reference)
  - All comparisons are relative to E

### Results JSON

Structured JSON with:
- Configuration parameters
- Results per arm (with all statistics)
- Metadata (timestamp, input file hash)

## Important Notes

1. **Set-level aggregation:** Multiple raters per set are averaged. Do NOT replicate set-level scores to card-level (this would inflate sample size).

2. **Benchmark F handling:** F is excluded from:
   - Primary NI pass/fail decisions
   - Final arm selection logic
   - Holm correction

3. **Missing data:** Groups where baseline E is missing are excluded from comparisons. Dropped groups are reported in `groups_dropped_missing_baseline`.

4. **Reproducibility:** Fixed seed (default 123) ensures reproducible results.

## Troubleshooting

### Error: "No common groups between baseline E and candidate X"

- Check that both arms have data for at least some common groups
- Verify group_id values are consistent across arms
- Check for typos in group_id values

### Warning: "No reviewer_id found for email: ..."

- Verify reviewer_email in Google Form matches reviewer_master.csv
- Check for email formatting differences (case, spaces, etc.)

### Warning: "No assignment found for reviewer_id=..., local_qid=..."

- Verify assignment_map.csv contains entries for all reviewer_id × local_qid combinations
- Check that local_qid extraction from Google Form columns is working correctly

## References

- **Canonical Specification:** `0_Protocol/06_QA_and_Study/QA_Operations/S0_Noninferiority_Criteria_Canonical.md`
- **QA Framework:** `0_Protocol/06_QA_and_Study/QA_Framework.md`
- **Survey Questions:** `0_Protocol/06_QA_and_Study/QA_Operations/S0_QA_Survey_Questions.md`

---

