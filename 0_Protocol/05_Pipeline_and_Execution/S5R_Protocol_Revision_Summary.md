# S5R Experiment Protocol Revision — Summary of Changes

**Date**: 2025-12-29  
**Purpose**: Document changes made to align S5R experiment protocol with preregistration-grade statistical standards (publication-ready Methods/Results).

---

## Overview

The protocol was revised to address key validity risks and ensure defensible causal claims for academic publication. The main changes separate two distinct causal questions (generation vs judge effects), reduce multiplicity, and add DEV/HOLDOUT split with cross-evaluation design.

---

## Key Changes (Diff-style Summary)

### 1. **Separated causal targets** (Critical for valid claims)
   - **Before**: Mixed claims about "quality improvement" without distinguishing generation-prompt changes from judge-prompt changes.
   - **After**: Explicitly defined **Target 1 (Generation effect)** and **Target 2 (Judge effect)** with distinct requirements:
     - Target 1 requires **fixed judge** for valid causal claim.
     - Target 2 requires **frozen content** to quantify judge behavior change.
   - **Why**: Prevents invalid causal claims that reviewers would reject.

### 2. **Reduced multiplicity** (Primary endpoint locked)
   - **Before**: Multiple primary endpoints (S1 issues/group, S2 issues/card, targeted codes) with no clear hierarchy.
   - **After**: **Single primary endpoint**: `S2_any_issue_rate_per_group` (proportion of cards with ≥1 issue per group). Key secondary limited to ≤3 endpoints.
   - **Why**: Avoids multiplicity correction issues and focuses statistical power on one defensible claim.

### 3. **Fixed statistical test** (No adaptive selection)
   - **Before**: Mentioned "paired t-test or Wilcoxon" with optional Shapiro-Wilk normality check (data-dependent test selection).
   - **After**: **Pre-specified Wilcoxon signed-rank test (paired)** with Hodges–Lehmann estimator + 95% CI. Sign test directionality as robustness check.
   - **Why**: Adaptive test selection is not prereg-friendly; Shapiro has low power at n=11.

### 4. **Added DEV vs HOLDOUT split** (Overfitting prevention)
   - **Before**: No explicit separation between development/tuning groups and confirmatory evaluation.
   - **After**: Current 11 groups = **DEV/pilot** (exploratory only; no confirmatory claims). Confirmatory requires **HOLDOUT** additional groups (target n=30–40).
   - **Why**: Prevents overfitting and invalid confirmatory claims on data used for prompt tuning.

### 5. **Cross-evaluation design** (Target 1 disentanglement)
   - **Before**: Single pipeline comparison (S5R0 vs S5R2) where both generation and judge changed simultaneously.
   - **After**: Recommended cross-evaluation: evaluate both before/after outputs with **same fixed judge version** to isolate generation effect.
   - **Why**: Allows valid causal claim for Target 1 (generation improvement) without judge-change confounding.

### 6. **Replicate handling clarified** (What replicates do/don't do)
   - **Before**: Ambiguous about whether replicates increase independent sample size.
   - **After**: Explicit rule: replicates **do not increase n**; they reduce measurement noise. Aggregation: **mean across replicates per group**; report replicate SD/min–max for stability.
   - **Why**: Prevents inflation of statistical claims; clarifies that n=11 remains n=11 even with replicates.

### 7. **Judge-only noise study** (Required component)
   - **Before**: Not mentioned.
   - **After**: Required study: freeze content, re-run S5 validator ≥5 times to quantify judge stochasticity (flip rate, agreement).
   - **Why**: Separates judge variability from true content quality differences.

### 8. **Expansion criteria** (Go/no-go rule)
   - **Before**: No explicit criteria for moving from pilot to confirmatory.
   - **After**: Preregistered rule: expand to HOLDOUT if **both** (1) ≥9/11 groups improve on primary endpoint, AND (2) median absolute reduction ≥5 percentage points.
   - **Why**: Prevents post-hoc expansion decisions; makes expansion transparent and defensible.

### 9. **Effect size emphasis** (n=11 interpretation)
   - **Before**: Focus on p-values and "statistical significance."
   - **After**: Primary emphasis on **effect size (median paired difference) + 95% CI + directionality** (improved groups / total). P-values are supportive, not primary.
   - **Why**: n=11 is underpowered for traditional significance; effect size + CI is more informative and defensible.

### 10. **Targeted issue codes** (Descriptive only)
   - **Before**: Per-code hypothesis testing (Fisher's exact, Chi-square) mentioned.
   - **After**: Targeted codes are **descriptive only** (or single prespecified composite as secondary). No per-code hypothesis testing.
   - **Why**: Avoids multiplicity explosion; keeps focus on primary endpoint.

### 11. **Manuscript templates updated** (Conservative language)
   - **Before**: Example Results sections claimed "quality improved" without judge-fixed caveat.
   - **After**: Templates emphasize "under fixed judge" cross-evaluation, median + CI reporting, and directionality over p-values.
   - **Why**: Ensures manuscript language matches preregistered design and avoids invalid claims.

### 12. **Run tag naming** (Cross-evaluation support)
   - **Before**: No notation for which judge version produced evaluation outputs.
   - **After**: Added `__evalS5R<k>` suffix pattern for cross-evaluation runs (e.g., `...__evalS5R2` = "S5R0 content evaluated with S5R2 judge").
   - **Why**: Prevents overwriting/mixing of evaluation outputs when same content is evaluated with different judge versions.

### 13. **Removed hardcoded effect sizes** (Template-only)
   - **Before**: Example Results sections included specific numbers (e.g., "60% reduction") that could be misinterpreted as expected outcomes.
   - **After**: Replaced with placeholders and explicit note that scenarios are "interpretation templates," not pre-committed numbers.
   - **Why**: Prevents accidental commitment to specific effect sizes; keeps focus on analysis structure.

### 14. **Canonical prereg document** (Single source of truth)
   - **Before**: Power/significance guidance was mixed with evaluation plan and methods.
   - **After**: Created dedicated canonical prereg document (`S5R_Experiment_Power_and_Significance_Plan.md`) with Status/Version/Frozen fields and all prereg requirements.
   - **Why**: Provides single authoritative source for reviewers; other docs reference it for consistency.

### 15. **Aligned dependent documents** (Consistency)
   - **Before**: Three protocol documents had inconsistent endpoint lists, test choices, and causal language.
   - **After**: All three documents (`Power_and_Significance_Plan.md`, `Quantitative_Evaluation_Plan.md`, `Hypothesis_and_Methods.md`) now reference the canonical prereg and use consistent endpoints/tests/language.
   - **Why**: Ensures Methods/Results sections can be written consistently across documents without contradictions.

---

## Files Modified

1. `0_Protocol/05_Pipeline_and_Execution/S5R_Experiment_Power_and_Significance_Plan.md` — **Complete rewrite** (canonical prereg document)
2. `0_Protocol/05_Pipeline_and_Execution/S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md` — **Minimal alignment edits** (endpoints, tests, cross-eval language)
3. `0_Protocol/05_Pipeline_and_Execution/S5_Prompt_Improvement_Hypothesis_and_Methods.md` — **Minimal alignment edits** (hypotheses split, DEV/HOLDOUT, manuscript templates)
4. `0_Protocol/05_Pipeline_and_Execution/S5_Version_Naming_S5R_Canonical.md` — **Small addition** (cross-evaluation run tag pattern)

---

## Next Steps

1. Execute DEV (n=11) experiment following preregistered design.
2. Report results using effect size + CI + directionality (not p-value dependent).
3. Apply expansion criteria to decide go/no-go for HOLDOUT (n=30–40).
4. If expanding, use identical endpoints/tests (no changes to analysis plan).

---

**Note**: This revision aligns the protocol with best practices for preregistration and publication-grade statistical analysis, while remaining practical for immediate execution.

