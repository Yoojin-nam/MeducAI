# S0 Non-Inferiority Criteria (Canonical)

**Status:** Canonical  
**Version:** 1.0  
**Frozen:** No  
**Supersedes:** N/A  
**Last Updated:** 2025-12-20  
**Aligned with:**
- QA Framework v2.0
- QA Evaluation Rubric v2.0
- S0 Allocation Artifact Specification v2.1
- S0 vs FINAL CardCount Policy

---

## 0. Purpose

This document defines the **statistically meaningful non-inferiority (NI) decision rules** for S0 arm selection, specifically designed for S0's **fixed 12-card payload per set**.

The decision framework uses a **two-layer gate**:
1. **Safety endpoint** (gatekeeper): prevents unacceptable increases in major errors (0-score cards)
2. **Primary NI endpoint**: mean accuracy score non-inferiority test

This ensures that arm selection is both **safe** and **statistically justified** under S0's constrained evaluation design.

---

## 1. S0 Payload Context (Invariant)

### 1.1 Fixed Payload Design

- **Unit of analysis:** Set = group × arm
- **Fixed card count:** Exactly 12 cards per set (invariant)
- **Allocation policy:** Deterministic 3×4 rule (4 entities × 3 cards each, when E≥4)
- **Scoring scale:** Card-level accuracy = 0 / 0.5 / 1 (per card)

### 1.2 Why Δ Must Be Small

Under a fixed 12-card payload:
- Mean accuracy is computed as: `mean = Σ(accuracy_score) / 12`
- A large Δ (e.g., 0.5 or 1.0) would imply allowing **6–12 points per set degradation**
- This is educationally unacceptable and statistically meaningless for a 12-card sample

**Therefore:** Δ must be small (0.03–0.08) to be meaningful under S0 constraints.

---

## 2. Two-Layer Decision Framework

### 2.1 Layer 1: Safety Endpoint (Gatekeeper)

**Purpose:** Prevent "mean score NI pass" despite unacceptable increases in major errors (0-score cards).

#### 2.1.1 Metric Definition

- **Major error rate:** Proportion of cards scored 0 (per-card accuracy == 0)
- **Notation:**
  - `p0_T` = proportion of 0-score cards in candidate arm T
  - `p0_A` = proportion of 0-score cards in baseline arm A
  - `RD0` = `p0_T - p0_A` (risk difference, absolute)

#### 2.1.2 Safety Pass Criterion

- Compute **one-sided upper bound** via two-sided 95% CI for `RD0`
- **Safety PASS if:** `UpperCI(RD0) ≤ +0.02`
- **Interpretation:** Candidate must not increase 0-score rate by more than **2 percentage points**, with 95% confidence

#### 2.1.3 Rationale

- A 2%p increase in 0-score rate on a 12-card set ≈ 0.24 additional major errors per set
- This is operationally acceptable as a safety margin
- If safety fails, the arm is **immediately disqualified** regardless of mean score performance

---

### 2.2 Layer 2: Primary NI Endpoint (Non-Inferiority Test)

**Purpose:** Determine if candidate arm is non-inferior to baseline on mean accuracy score.

#### 2.2.1 Metric Definition

- **Mean accuracy score:** Card-level accuracy (0/0.5/1) averaged across all cards in the set
- **Notation:**
  - `mean_T` = mean accuracy in candidate arm T
  - `mean_A` = mean accuracy in baseline arm A
  - `d` = `mean_T - mean_A` (difference)

#### 2.2.2 Non-Inferiority Margin (Δ)

**Default:** Δ = 0.05 (mean score scale)

**Configuration options:**
- **Conservative:** Δ = 0.03 (stricter, for high-stakes decisions)
- **Default:** Δ = 0.05 (recommended, balances rigor and practicality)
- **Cost-driven:** Δ = 0.08 (more permissive, for cost optimization scenarios)

**Why Δ = 0.05 is appropriate:**
- On a 12-card set, Δ = 0.05 implies allowing up to **0.6 points degradation** (≈ 1 card dropping from 1.0 to 0.4, or 2 cards from 0.5 to 0.0)
- This is educationally meaningful and statistically defensible
- Larger Δ values (0.5, 1.0) are **invalid** for S0 because they would allow 6–12 points per set degradation

#### 2.2.3 CI-Based NI Rule

**Hypothesis:**
- H0: `d ≤ -Δ` (candidate is inferior)
- H1: `d > -Δ` (candidate is non-inferior)

**Decision rule:**
- Compute CI for `d` (difference in mean accuracy)
- **NI PASS if:** `LowerCI(d) > -Δ`
- **NI FAIL if:** `LowerCI(d) ≤ -Δ`

**CI level options:**
- **Default:** 90% two-sided CI (operational one-sided α = 0.05) for S0 selection
- **Stricter option:** 95% two-sided CI (one-sided α = 0.025) for high-stakes scenarios

**Default rationale:** 90% CI is standard for non-inferiority testing in operational selection contexts.

---

### 2.3 Layer 3: Editing Time Non-Inferiority (Optional Tie-Breaker)

**Purpose:** Ensure candidate does not require excessive editing time compared to baseline.

#### 2.3.1 Metric Definition

- **Editing time:** Self-reported minutes per set (from survey)
- **Notation:**
  - `time_T` = mean editing time in candidate arm T
  - `time_A` = mean editing time in baseline arm A
  - `diff_time` = `time_T - time_A`

#### 2.3.2 Pass Criterion

- **Soft gate:** Candidate not worse than baseline by more than **+10%** (relative) or **+2 minutes** (absolute, whichever is larger)
- **Status:** Optional tie-breaker; does not block selection if safety and NI pass

---

## 3. Statistical Handling of Repeated Measures

### 3.1 Data Structure

S0 data has repeated measures:
- Same rater scores multiple sets
- Same group appears across arms
- Within-pair comparisons (rater × group) should be preserved

### 3.2 Primary Implementation: Clustered Paired Bootstrap

**Method:**
- **Unit of resampling:** `(rater_id, group_id)` pairs
- For each bootstrap replicate:
  1. Sample `(rater_id, group_id)` pairs with replacement
  2. For each arm: compute mean accuracy and `p0` within sampled pairs
  3. Compute `d` and `RD0` vs baseline A
- **CI construction:** Percentile CI
  - 90% CI: 5th–95th percentiles
  - 95% CI: 2.5th–97.5th percentiles

**Fixed seed:** Default = 20251220 (configurable)

**Rationale:**
- Preserves within-pair structure
- Robust to distributional assumptions
- Deterministic given fixed seed

### 3.3 Secondary Method (Optional)

- Mixed effects model (LMM for mean score; logistic mixed model for 0-score)
- **Status:** Optional enhancement; do not block delivery if implementation is complex

---

## 4. Input Data Format

### 4.1 Required Format (Long Format)

One row per card, with at least:

| Column | Type | Description |
|--------|------|-------------|
| `run_tag` | str | Run identifier |
| `arm` | str | Arm identifier (A–F) |
| `group_id` | str | Group identifier |
| `rater_id` | str | Rater identifier |
| `card_id` | str | Card identifier |
| `accuracy_score` | float | 0.0, 0.5, or 1.0 |

### 4.2 Optional Columns

- `entity_id` (optional): Entity identifier
- `editing_time_sec` (optional): Editing time in seconds

### 4.3 Column Mapping

If input CSV uses different column names, implement an adapter layer and document the mapping clearly.

---

## 5. Output Artifacts

### 5.1 Output Location

Write outputs under existing run_tag folders:
```
2_Data/metadata/generated/{RUN_TAG}/qa/
├── qa_s0_noninferiority_summary.csv
├── qa_s0_noninferiority_decision.md
└── qa_s0_noninferiority_bootstrap_meta.json
```

### 5.2 Summary CSV (`qa_s0_noninferiority_summary.csv`)

Required columns (minimum):

| Column | Type | Description |
|--------|------|-------------|
| `arm` | str | Arm identifier |
| `baseline_arm` | str | Baseline arm identifier |
| `n_pairs` | int | Number of unique (rater_id, group_id) pairs |
| `n_cards` | int | Total number of cards |
| `mean_accuracy` | float | Mean accuracy score |
| `diff_vs_baseline` | float | Difference vs baseline (d) |
| `diff_ci_low` | float | Lower CI bound for d |
| `diff_ci_high` | float | Upper CI bound for d |
| `delta` | float | Non-inferiority margin (Δ) |
| `ci_level` | float | CI level (0.90 or 0.95) |
| `ni_pass` | bool | NI pass/fail |
| `p0` | float | Proportion of 0-score cards |
| `rd0_vs_baseline` | float | Risk difference vs baseline (RD0) |
| `rd0_ci_low` | float | Lower CI bound for RD0 |
| `rd0_ci_high` | float | Upper CI bound for RD0 |
| `major_error_margin` | float | Safety margin (default 0.02) |
| `safety_pass` | bool | Safety pass/fail |
| `final_pass` | bool | safety_pass AND ni_pass |
| `mean_edit_time` | float | Mean editing time (optional) |
| `diff_edit_time` | float | Difference in editing time (optional) |
| `edit_time_pass` | bool | Editing time pass/fail (optional) |

### 5.3 Decision Markdown (`qa_s0_noninferiority_decision.md`)

A short, copy-paste-ready decision summary:

```markdown
# S0 Non-Inferiority Analysis Results

**Baseline Arm:** A
**Delta (Δ):** 0.05
**CI Level:** 90%
**Bootstrap N:** 5000
**Seed:** 20251220

## Results by Arm

### Arm B
- **Safety:** PASS (RD0 UpperCI = 0.015 ≤ 0.02)
- **NI:** PASS (LowerCI = -0.03 > -0.05)
- **Final:** PASS

### Arm C
- **Safety:** PASS (RD0 UpperCI = 0.018 ≤ 0.02)
- **NI:** FAIL (LowerCI = -0.07 ≤ -0.05)
- **Final:** FAIL

## Recommendation

Among final_pass arms, choose lowest cost.
```

### 5.4 Bootstrap Metadata (`qa_s0_noninferiority_bootstrap_meta.json`)

```json
{
  "seed": 20251220,
  "bootstrap_n": 5000,
  "ci_level": 0.90,
  "delta": 0.05,
  "timestamp": "2025-12-20T12:00:00Z",
  "input_file": "path/to/input.csv",
  "input_file_hash": "sha256:...",
  "baseline_arm": "A"
}
```

---

## 6. Failure Rules

### 6.1 Fail-Fast Conditions

The script must **FAIL immediately** if:
- Baseline arm is missing from data
- Required columns cannot be mapped
- `n_pairs` (unique rater×group pairs with baseline + candidate) < minimum threshold (default = 20; allow override)

### 6.2 Warn-Only Conditions

The script should **WARN but continue** if:
- Some arms have partial missingness (report coverage per arm)
- Editing time column missing (skip edit-time evaluation)

---

## 7. Relationship to QA Framework v2.0

### 7.1 Alignment

This document **supersedes** the Δ specification in QA Framework v2.0 Section 2.7 for S0:
- **Old:** Δ_quality = 0.5 (on 1–5 Likert scale)
- **New:** Δ = 0.05 (on mean accuracy 0/0.5/1 scale)

**Rationale:** The new specification is:
- Meaningful under S0's fixed 12-card payload
- Uses card-level accuracy (already collected) rather than Likert scores
- Provides a two-layer safety gate

### 7.2 Reference Arm

- **Baseline for NI:** Arm A (Baseline, Flash Low) as specified in user requirements
- **Alternative:** Can be configured to use Arm E (High-End) if needed

---

## 8. Change Control

Any change to this document requires:
- Version bump
- Explicit justification
- Update to analysis script if needed
- Update to SSOT index

---

## Official Statement

> S0 non-inferiority analysis uses a two-layer decision framework: (1) Safety gate prevents unacceptable increases in major errors (0-score cards); (2) Primary NI test ensures mean accuracy is non-inferior to baseline within a small, educationally meaningful margin (Δ = 0.03–0.08). The framework is designed specifically for S0's fixed 12-card payload and uses CI-based decision rules with clustered paired bootstrap to handle repeated measures.

