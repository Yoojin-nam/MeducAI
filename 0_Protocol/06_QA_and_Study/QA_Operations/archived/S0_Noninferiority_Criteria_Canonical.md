# S0 Non-Inferiority Criteria (Canonical)

**Status:** Canonical  
**Version:** 2.0  
**Frozen:** No  
**Supersedes:** v1.0 (archived as `archived/S0_Noninferiority_Criteria_Canonical_v1.0_cardlevel.md`)  
**Last Updated:** 2025-12-20  
**Aligned with:**
- QA Framework v2.0
- QA Evaluation Rubric v2.0
- S0 Allocation Artifact Specification v2.1
- S0 vs FINAL CardCount Policy
- S0 QA Survey Questions v2.0

---

## 0. Purpose

This document defines the **statistically meaningful non-inferiority (NI) decision rules** for S0 arm selection, using **Set-level Overall Card Quality (1–5 Likert scale)** as the primary endpoint.

The decision framework:
1. **Primary NI endpoint**: Set-level Overall Card Quality (1–5 Likert) non-inferiority test
2. **Baseline arm**: E (High-End, assumed to be the most expensive and highest quality reference)
3. **Candidate arms**: A, B, C, D (primary decision targets)
4. **External benchmark**: F (ChatGPT, secondary benchmark, excluded from primary decision)

This ensures that arm selection is **statistically justified** and **operationally safe** under S0's evaluation design.

---

## 1. S0 Payload Context (Invariant)

### 1.1 Fixed Payload Design

- **Unit of analysis:** Set = group × arm
- **Fixed card count:** Exactly 12 cards per set (invariant)
- **Allocation policy:** Deterministic 3×4 rule (4 entities × 3 cards each, when E≥4)
- **Scoring scale:** Set-level Overall Card Quality = 1–5 Likert (per set, per rater)

### 1.2 Why Δ = 0.5 is Appropriate

Under a 1–5 Likert scale:
- Δ = 0.5 represents **half of one Likert step** (e.g., from 4 to 3.5, or from 3 to 2.5)
- This is educationally meaningful: allowing up to half a step degradation is operationally acceptable
- Larger Δ values (e.g., 1.0) would allow a full step degradation, which may be too permissive
- Smaller Δ values (e.g., 0.1) would be too strict for practical arm selection

**Therefore:** Δ = 0.5 (Likert scale) is the canonical non-inferiority margin for S0.

---

## 2. Primary NI Endpoint: Set-level Overall Card Quality

### 2.1 Metric Definition

- **Overall Card Quality:** 1–5 Likert scale score assigned to each set by each rater
  - 1 = 매우 나쁨 (Very Poor)
  - 2 = 나쁨 (Poor)
  - 3 = 보통 (Average)
  - 4 = 좋음 (Good)
  - 5 = 매우 좋음 (Very Good)
- **Set-level aggregation:** If multiple raters evaluate the same set (group_id × arm × set_id), use the **mean across raters** within that set
- **Notation:**
  - `score_j` = mean Overall Card Quality for arm j (averaged across groups and raters)
  - `score_E` = mean Overall Card Quality for baseline arm E
  - `d_j` = `score_j - score_E` (difference for candidate arm j)

### 2.2 Non-Inferiority Margin (Δ)

**Canonical:** Δ = 0.5 (Likert scale)

**Interpretation:**
- Δ = 0.5 means "half of one Likert step"
- This allows candidates to be up to 0.5 points lower than baseline E on average, while still being considered non-inferior
- Example: If E has mean score 4.0, a candidate with mean score ≥ 3.5 can pass NI (if LowerCI > -0.5)

**Fixed:** This value is **canonical** and should not be changed without explicit justification and version bump.

### 2.3 CI-Based NI Rule

**Hypothesis:**
- H0: `d_j ≤ -Δ` (candidate j is inferior to baseline E)
- H1: `d_j > -Δ` (candidate j is non-inferior to baseline E)

**Decision rule:**
- Compute CI for `d_j` using group-cluster bootstrap
- **NI PASS if:** `LowerCI(d_j) > -Δ` (i.e., LowerCI > -0.5)
- **NI FAIL if:** `LowerCI(d_j) ≤ -Δ` (i.e., LowerCI ≤ -0.5)

**CI level:**
- **Default:** 95% two-sided CI (one-sided α = 0.025) for LowerCI
- LowerCI is the 2.5th percentile of the bootstrap distribution

**Rationale:** 95% CI (one-sided α = 0.025) is standard for non-inferiority testing in clinical/educational research.

---

## 3. Statistical Handling of Repeated Measures

### 3.1 Data Structure

S0 data has repeated measures:
- Same rater scores multiple sets (across different groups/arms)
- Same group appears across arms
- Within-set aggregation: If multiple raters evaluate the same set, use mean across raters

### 3.2 Primary Implementation: Group-Cluster Bootstrap

**Method:**
- **Unit of resampling:** `group_id` (clusters)
- For each bootstrap replicate:
  1. Sample `group_id` values with replacement (bootstrap resample of groups)
  2. For each arm: compute mean Overall Card Quality across sampled groups
  3. Compute `d_j = mean_j - mean_E` for each candidate arm j
- **CI construction:** Percentile CI
  - LowerCI: 2.5th percentile of bootstrap distribution (one-sided α = 0.025)
  - UpperCI: 97.5th percentile of bootstrap distribution

**Fixed seed:** Default = 123 (configurable via `--seed`)

**Rationale:**
- Preserves group-level clustering structure
- Robust to distributional assumptions
- Deterministic given fixed seed
- Respects the 18 groups as independent units

### 3.3 Set-Level Aggregation Rule

**Within-set aggregation (if multiple raters):**
- For each unique `(group_id, arm, set_id)` combination:
  - If multiple `rater_id` values exist, compute **mean** of `overall_quality_1to5`
  - Use this mean as the set-level score for that `(group_id, arm, set_id)`
- This aggregated score is then used in group-level bootstrap

**Rationale:** Cross-rater evaluation is designed to reduce rater-specific bias. The mean across raters within a set is the appropriate set-level score.

---

## 4. Input Data Format

### 4.1 Required Format (Set-Long Format)

One row per set per rater, with at least:

| Column | Type | Description |
|--------|------|-------------|
| `run_tag` | str | Run identifier |
| `arm` | str | Arm identifier (A–F, E=baseline, F=benchmark) |
| `group_id` | str | Group identifier (1–18) |
| `set_id` | str | Set identifier (within group × arm) |
| `rater_id` | str | Rater identifier (or reviewer_email) |
| `overall_quality_1to5` | int | Overall Card Quality score (1–5) |

### 4.2 Optional Columns (Future Extensions)

- `blocking_error` (bool): Whether blocking error exists
- `critical_error_table` (bool): Critical error in table
- `critical_error_infographic` (bool): Critical error in infographic
- `scope_failure` (bool): Scope/alignment failure
- `editing_time_min` (float): Editing time in minutes
- `accuracy_set` (float): Set-level accuracy (0/0.5/1.0) — **not used for primary NI**

### 4.3 Data Preprocessing

**Missing data handling:**
- Rows with missing `overall_quality_1to5` are excluded
- Groups where baseline E is missing are excluded from comparisons involving that group
- Excluded groups are reported in output (`groups_dropped_missing_baseline`)

**Set-level aggregation:**
- If multiple raters evaluate the same `(group_id, arm, set_id)`, compute mean
- If only one rater per set, use that rater's score directly

---

## 5. Arm Classification and Decision Rules

### 5.1 Arm Roles

- **Baseline (E):** Reference arm for all comparisons. Assumed to be highest quality (most expensive).
- **Candidates (A, B, C, D):** Primary decision targets. NI pass/fail determines eligibility for final selection.
- **Benchmark (F):** External benchmark (ChatGPT). **Excluded from primary NI decision.** Only reported for reference.

### 5.2 Decision Rules (Candidates Only)

For each candidate arm j ∈ {A, B, C, D}:

1. **Compute mean difference:** `d_j = mean_over_groups(Score_j - Score_E)`
2. **Bootstrap CI:** Group-cluster bootstrap to get `LowerCI(d_j)`
3. **NI Pass/Fail:**
   - **PASS if:** `LowerCI(d_j) > -0.5`
   - **FAIL if:** `LowerCI(d_j) ≤ -0.5`

### 5.3 Multiple Comparisons Correction

**Holm correction (default ON, recommended):**
- 4 comparisons: A vs E, B vs E, C vs E, D vs E
- Apply Holm step-down procedure to control family-wise error rate
- Output includes:
  - `holm_adjusted_p`: Adjusted p-value for each candidate
  - `holm_pass`: Pass/fail after Holm correction

**Rationale:** Multiple comparisons correction is essential when making multiple NI decisions simultaneously.

### 5.4 Benchmark Arm (F) Handling

**Important:** F is **NOT** included in:
- Primary NI pass/fail decisions
- Final arm selection logic
- Holm correction (only candidates A–D are corrected)

**F is included in:**
- Mean difference vs baseline E calculation
- CI calculation (for reference)
- Output reporting (with `is_benchmark=true` flag)

**F comparison:**
- Only computed on groups where both F and E have data (intersection)
- `n_groups_used` is reported separately for F

---

## 6. Output Artifacts

### 6.1 Output Location

Write outputs to specified paths:
```
{out_dir}/
├── s0_noninferiority_setlevel_summary.csv
├── s0_noninferiority_setlevel_results.json
└── (optional) s0_noninferiority_setlevel_decision.md
```

### 6.2 Summary CSV (`s0_noninferiority_setlevel_summary.csv`)

Required columns:

| Column | Type | Description |
|--------|------|-------------|
| `arm` | str | Arm identifier |
| `role` | str | "baseline" \| "candidate" \| "benchmark" |
| `mean_diff_vs_baseline` | float | Mean difference vs baseline E |
| `lower_ci` | float | Lower CI bound (2.5th percentile) |
| `upper_ci` | float | Upper CI bound (97.5th percentile) |
| `ni_pass` | bool/NA | NI pass/fail (candidates only, benchmark=NA) |
| `n_groups_used` | int | Number of groups used in comparison |
| `groups_dropped_missing_baseline` | str | Comma-separated list of dropped groups (or count) |
| `holm_adjusted_p` | float/NA | Holm-adjusted p-value (candidates only) |
| `holm_pass` | bool/NA | Pass/fail after Holm correction (candidates only) |
| `note` | str | Additional notes (e.g., "benchmark only") |

### 6.3 Results JSON (`s0_noninferiority_setlevel_results.json`)

Structured JSON with:
- Configuration (delta, seed, n_boot, etc.)
- Results per arm (with all statistics)
- Metadata (timestamp, input file hash, etc.)

### 6.4 Decision Markdown (Optional)

Human-readable summary with:
- Configuration summary
- Results by arm (candidates and benchmark)
- Final recommendation (among passing candidates, choose lowest cost)

---

## 7. Failure Rules

### 7.1 Fail-Fast Conditions

The script must **FAIL immediately** if:
- Baseline arm E is missing from data
- Required columns cannot be mapped
- No valid set-level scores exist after preprocessing

### 7.2 Warn-Only Conditions

The script should **WARN but continue** if:
- Some groups have missing baseline E (exclude from comparison, report in output)
- Some arms have partial missingness (report coverage per arm)
- Benchmark F has limited overlap with E (report `n_groups_used`)

---

## 8. Relationship to Previous Versions

### 8.1 Version 2.0 Changes from v1.0

**v1.0 (archived):**
- Primary endpoint: Card-level accuracy (0/0.5/1)
- Δ = 0.05 (on accuracy scale)
- Baseline: Arm A
- Two-layer framework: Safety gate + NI gate

**v2.0 (current):**
- Primary endpoint: **Set-level Overall Card Quality (1–5 Likert)**
- Δ = 0.5 (on Likert scale, half of one step)
- Baseline: **Arm E** (High-End)
- Candidates: A, B, C, D
- Benchmark: F (ChatGPT, secondary only)
- Single-layer framework: Primary NI endpoint only

**Rationale for change:**
- Set-level Likert score is the primary metric collected in S0 QA survey
- Δ = 0.5 is educationally meaningful (half a Likert step)
- Baseline E represents the "gold standard" high-cost option
- Benchmark F provides external context but does not influence primary decision

---

## 9. Change Control

Any change to this document requires:
- Version bump
- Explicit justification
- Update to analysis script if needed
- Update to SSOT index
- Archive previous version (do not delete)

---

## Official Statement

> S0 non-inferiority analysis uses **Set-level Overall Card Quality (1–5 Likert)** as the primary endpoint, with Δ = 0.5 (half of one Likert step) as the non-inferiority margin. Baseline arm E (High-End) is compared against candidates A, B, C, D using group-cluster bootstrap (10,000 resamples, seed=123). NI pass requires LowerCI(mean_diff) > -0.5. Multiple comparisons are corrected using Holm procedure (default ON). External benchmark F (ChatGPT) is reported for reference but excluded from primary NI decision and final arm selection.

---

