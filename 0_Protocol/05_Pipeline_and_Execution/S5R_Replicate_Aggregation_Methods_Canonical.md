# S5R Replicate Aggregation Methods (Canonical)

**Status**: Canonical (Statistical Analysis Specification)  
**Version**: 1.0  
**Applies to**: S5R Experiment (S5R0, S5R1, S5R2)  
**Related Documents**:
- `0_Protocol/05_Pipeline_and_Execution/S5R_Experiment_Power_and_Significance_Plan.md`
- `0_Protocol/05_Pipeline_and_Execution/S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md`

**Last Updated**: 2025-12-29

---

## 1. Purpose of This Document

This document specifies the **canonical methods for aggregating replicates (rep1, rep2)** in S5R experiments. Replicates are used to reduce measurement variability (especially in image generation) and provide measurement stability, but they **do not increase the independent sample size** (n remains the number of groups, not groups × replicates).

---

## 2. Replicate Purpose and Role

### 2.1 What Replicates Do

- **Reduce measurement variability**: Especially important for stochastic image generation (S4)
- **Provide measurement stability**: Multiple independent runs reduce the impact of random variation
- **Enable stability reporting**: SD or min-max across replicates can be reported per group

### 2.2 What Replicates Do NOT Do

- **Do NOT increase independent sample size**: n remains the number of groups (n=11 for DEV, n=30-40 for HOLDOUT)
- **Do NOT provide additional statistical power**: Replicates are aggregated before statistical testing

### 2.3 Minimum Recommendation

- **2 replicates (rep1, rep2)** are recommended for each condition
- Under cost constraints: 1 replicate + judge-only noise study is required

---

## 3. Aggregation Rule (Strict)

### 3.1 Core Principle

For each condition (Before/After) × group combination:

1. Calculate the endpoint separately for each replicate (rep1, rep2)
2. **Aggregate using the mean (average)** of replicate values
3. Use the aggregated mean as the group-level endpoint for statistical analysis

### 3.2 Mathematical Definition

For a given endpoint `E` and group `g`:

```
E_g = mean(E_g_rep1, E_g_rep2) = (E_g_rep1 + E_g_rep2) / 2
```

Where:
- `E_g_rep1` = endpoint value for group `g` from replicate 1
- `E_g_rep2` = endpoint value for group `g` from replicate 2
- `E_g` = aggregated endpoint value for group `g` (used in analysis)

### 3.3 Example: Primary Endpoint Aggregation

**Primary Endpoint**: `S2_any_issue_rate_per_group`

For group `grp_001`:
- rep1: `S2_any_issue_rate_per_group = 0.15` (15% of cards have issues)
- rep2: `S2_any_issue_rate_per_group = 0.18` (18% of cards have issues)
- **Aggregated**: `E_grp_001 = (0.15 + 0.18) / 2 = 0.165` (16.5%)

This aggregated value (0.165) is used as the group-level endpoint for statistical comparison.

---

## 4. Stability Reporting

### 4.1 Required Reporting

For each group, report **both**:
1. The aggregated mean (used in analysis)
2. A stability measure: **SD (standard deviation)** or **min-max range** across replicates

### 4.2 Standard Deviation (SD)

Calculate the standard deviation of replicate values:

```
SD_g = sqrt(mean((E_g_rep1 - E_g)^2, (E_g_rep2 - E_g)^2))
```

For 2 replicates, this simplifies to:
```
SD_g = |E_g_rep1 - E_g_rep2| / sqrt(2)
```

### 4.3 Min-Max Range (Alternative)

Report the minimum and maximum values across replicates:

```
min_g = min(E_g_rep1, E_g_rep2)
max_g = max(E_g_rep1, E_g_rep2)
```

### 4.4 Reporting Format

**Recommended table format**:

| Group ID | Endpoint (mean) | SD | rep1 | rep2 |
|----------|-----------------|----|----|----|
| grp_001  | 0.165           | 0.021 | 0.15 | 0.18 |
| grp_002  | 0.220           | 0.015 | 0.21 | 0.23 |
| ...      | ...             | ... | ... | ... |

Or using min-max:

| Group ID | Endpoint (mean) | Range (min-max) |
|----------|-----------------|-----------------|
| grp_001  | 0.165           | 0.15 - 0.18     |
| grp_002  | 0.220           | 0.21 - 0.23     |
| ...      | ...             | ...             |

---

## 5. Implementation Guidelines

### 5.1 Data Structure

Replicate data should be organized as:

```
2_Data/metadata/generated/
  ├── DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep1/
  │   ├── s5_validation__armG.jsonl (11 groups)
  │   └── reports/s5_report__armG.md
  └── DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep2/
      ├── s5_validation__armG.jsonl (11 groups)
      └── reports/s5_report__armG.md
```

### 5.2 Aggregation Workflow

1. **Load replicate data**: Read `s5_validation__armG.jsonl` from both rep1 and rep2 run tags
2. **Calculate endpoints per replicate**: For each group, calculate endpoints (e.g., `S2_any_issue_rate_per_group`) separately for rep1 and rep2
3. **Aggregate**: Calculate mean for each group
4. **Calculate stability**: Calculate SD or min-max for each group
5. **Report**: Include both aggregated values and stability measures in reports

### 5.3 Group ID Matching

**Critical**: Ensure that rep1 and rep2 use the **same 11 groups** (same `group_id` values). Verify group_id matching before aggregation.

---

## 6. Statistical Analysis After Aggregation

### 6.1 Analysis Unit

After aggregation, the analysis unit is:
- **n = number of groups** (n=11 for DEV, n=30-40 for HOLDOUT)
- **NOT** n = number of groups × replicates

### 6.2 Paired Comparison

For Before/After comparison:
- Each group has one aggregated Before value and one aggregated After value
- Paired difference: `diff_i = After_i - Before_i` (where `i` indexes groups)
- Statistical test: Wilcoxon signed-rank test (paired) on `diff_i`

### 6.3 Effect Size and CI

- **Hodges–Lehmann estimator** (paired location shift) + 95% CI
- Or **bootstrap 95% CI** on paired differences

---

## 7. Endpoints Requiring Aggregation

All group-level endpoints must be aggregated across replicates:

### 7.1 Primary Endpoint
- **S2_any_issue_rate_per_group**: Rate of cards with `issue >= 1` per group

### 7.2 Key Secondary Endpoints
- **IMG_any_issue_rate_per_group**: Rate of images with `issue >= 1` per group
- **S2_issues_per_card_per_group**: Average number of issues per card per group
- **TA_bad_rate_per_group**: Percentage of cards with `technical_accuracy < 1.0` per group
  - OR **Difficulty_bad_rate_per_group**: Percentage of cards with `difficulty == 0.0` per group
  - (Only one of these should be selected as a key secondary endpoint)

### 7.3 Targeted Issue Codes (Descriptive)
- **targeted_issue_composite_per_group**: Sum or rate of targeted issue code occurrences per group
- Note: Per-code tests are not performed (multiplicity concerns); only descriptive or one prespecified composite

---

## 8. Example: Complete Aggregation Workflow

### 8.1 Input Data

**rep1** (`s5_validation__armG.jsonl`):
```json
{"group_id": "grp_001", "S2_any_issue_rate": 0.15, ...}
{"group_id": "grp_002", "S2_any_issue_rate": 0.21, ...}
...
```

**rep2** (`s5_validation__armG.jsonl`):
```json
{"group_id": "grp_001", "S2_any_issue_rate": 0.18, ...}
{"group_id": "grp_002", "S2_any_issue_rate": 0.23, ...}
...
```

### 8.2 Aggregation

| group_id | rep1 | rep2 | mean | SD |
|----------|------|------|------|-----|
| grp_001  | 0.15 | 0.18 | 0.165 | 0.021 |
| grp_002  | 0.21 | 0.23 | 0.220 | 0.014 |
| ...      | ...  | ...  | ...   | ...  |

### 8.3 Statistical Analysis

Use aggregated `mean` values for Before/After comparison:
- Before (S5R0): `[0.165, 0.220, ...]` (n=11 groups)
- After (S5R2): `[0.120, 0.180, ...]` (n=11 groups)
- Paired differences: `[-0.045, -0.040, ...]`
- Statistical test on paired differences

---

## 9. Validation and Quality Checks

### 9.1 Pre-Aggregation Checks

- [ ] Verify rep1 and rep2 have the same set of `group_id` values
- [ ] Verify rep1 and rep2 were generated with the same prompt versions
- [ ] Verify rep1 and rep2 used the same S5 validator version (for Target 1: Generation effect)

### 9.2 Post-Aggregation Checks

- [ ] Verify aggregated means are within expected ranges
- [ ] Check for unusually large SD values (may indicate data quality issues)
- [ ] Verify group_id matching in Before/After comparisons

---

## 10. Reporting Checklist

When reporting results, include:

- [ ] Aggregation method clearly stated (mean of replicates)
- [ ] Stability measures reported (SD or min-max) per group
- [ ] Sample size clearly stated as number of groups (n=11), not groups × replicates
- [ ] Replicate run tags documented
- [ ] Group ID matching verified and documented

---

## 11. Related Scripts and Tools

### 11.1 Comparison Script

The comparison script (`tools/s5/s5_compare_mm.py`) should:
- Accept multiple run tags (rep1, rep2 for Before and After)
- Aggregate replicates per group before comparison
- Report both aggregated values and stability measures

### 11.2 Report Generation

The report generation script (`tools/s5/s5_report.py`) should:
- Generate reports per replicate (rep1, rep2 separately)
- Optionally generate aggregated reports (mean across replicates)

---

## 12. Summary Statement

Replicate aggregation is a **required step** in S5R experiments to reduce measurement variability while maintaining the correct statistical analysis unit (groups, not groups × replicates). The canonical method is to:

1. Calculate endpoints separately for each replicate
2. Aggregate using the **mean** (average)
3. Report **SD or min-max** as stability measures
4. Use aggregated values for statistical analysis (n = number of groups)

This approach ensures measurement stability while preserving the correct interpretation of statistical tests and effect sizes.

