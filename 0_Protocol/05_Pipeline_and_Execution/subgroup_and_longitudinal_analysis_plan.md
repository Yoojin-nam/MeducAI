# Subgroup and Longitudinal Analysis Plan

Status: Canonical (Statistical Analysis Specification)
Version: 1.0
Applies to: QA Phase (S0, S1) and Exploratory User Evaluation
Related Documents:
- 00_Governance/Evaluation_Unit_and_Scope_Definition.md
- 05_Pipeline_and_Execution/QA_Metric_Definitions.md
- 05_Pipeline_and_Execution/Efficiency_Measurement_Exploratory.md

Last Updated: 2025-12-17

---

## 1. Purpose of This Document

This document specifies the **subgroup and longitudinal analysis strategy** for evaluating LLM-generated Anki cards. The primary goal is to ensure that subgroup comparisons and temporal analyses are **methodologically valid**, statistically interpretable, and aligned with known sources of inter-individual variability in educational outcomes.

The analysis plan explicitly prioritizes **within-subject change** over between-subject comparisons, recognizing substantial baseline heterogeneity among learners.

---

## 2. Rationale for Longitudinal and Subgroup Analyses

Educational outcomes derived from LLM-assisted content are influenced by:

- Baseline knowledge level
- Prior exposure to similar materials
- Individual study habits and speed

Accordingly, naïve between-group comparisons may be misleading. This plan adopts a longitudinal perspective to better isolate the effect of exposure to LLM-generated materials.

---

## 3. Unit of Analysis

### 3.1 Primary Unit

The primary unit of analysis remains the **individual Anki card**, scored for accuracy, educational quality, and (exploratory) efficiency.

### 3.2 Aggregation Level

For subgroup and longitudinal analyses, card-level metrics may be aggregated:

- Within individuals
- Within predefined learner subgroups

Aggregation rules are pre-specified to avoid post hoc bias.

---

## 4. Baseline Assessment

### 4.1 Baseline Definition

Baseline measures are collected prior to or independent of exposure to the LLM-generated content and may include:

- Self-reported experience level (e.g., junior resident, senior resident)
- Prior familiarity with the topic domain
- Existing study resources or habits

### 4.2 Purpose of Baseline Data

Baseline data are used to:

- Contextualize post-exposure outcomes
- Enable within-subject comparisons
- Reduce confounding due to inter-individual variability

---

## 5. Longitudinal Analysis Framework

### 5.1 Primary Longitudinal Comparison

The primary longitudinal analysis focuses on **within-subject change**, comparing outcomes:

- Before exposure (baseline)
- After exposure to LLM-generated Anki cards

Change scores may be calculated for accuracy, quality perception, or efficiency where applicable.

### 5.2 Statistical Approach

Depending on data structure and sample size:

- Paired comparisons (e.g., paired t-test or non-parametric equivalent)
- Mixed-effects models with subject-level random effects

The choice of method is guided by distributional assumptions and data completeness.

---

## 6. Subgroup Analyses

### 6.1 Predefined Subgroups

Subgroup analyses are limited to **a priori defined categories**, such as:

- Learner experience level (e.g., junior vs senior)
- Topic complexity (e.g., core vs advanced topics)

No exploratory post hoc subgrouping is planned.

### 6.2 Interpretation Principles

- Subgroup analyses are considered **exploratory** unless adequately powered
- Effect sizes and confidence intervals are emphasized over p-values
- Findings are interpreted cautiously and contextually

---

## 7. Sample Size and Power Considerations

Given the exploratory nature of subgroup analyses:

- Formal power calculations are not mandatory
- Minimum sample thresholds may be applied to avoid unstable estimates
- Subgroups with insufficient data are reported descriptively or omitted

---

## 8. Handling of Missing Data

- Missing baseline or follow-up data are documented
- No imputation is performed unless justified
- Analyses are conducted on available paired data

---

## 9. Reporting Principles

Results from subgroup and longitudinal analyses are:

- Clearly labeled as exploratory where appropriate
- Reported separately from primary QA outcomes
- Used to inform hypothesis generation and future study design

---

## 10. Summary Statement

This analysis plan adopts a conservative, longitudinally oriented approach to subgroup evaluation. By prioritizing within-subject comparisons and predefining subgroup categories, the framework mitigates bias from baseline heterogeneity and supports interpretable, methodologically sound exploratory analyses.

