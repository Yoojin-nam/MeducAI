# Inter-Rater Agreement Analysis Plan

Status: Canonical (Reliability Analysis Specification)
Version: 1.0
Applies to: QA Phase (S0, S1)
Related Documents:
- 00_Governance/Evaluation_Unit_and_Scope_Definition.md
- 05_Pipeline_and_Execution/QA_Metric_Definitions.md
- 05_Pipeline_and_Execution/QA_Methodological_Checkpoints.md

Last Updated: 2025-12-17

---

## 1. Purpose of This Document

This document specifies the **inter-rater agreement (IRA) analysis plan** for the QA evaluation of LLM-generated Anki cards. The goal is to quantify the **reliability and consistency** of human expert judgments across predefined QA metrics, thereby strengthening the methodological rigor and interpretability of the study results.

Inter-rater agreement is treated as a **supportive methodological quality indicator**, not as a direct measure of content validity.

---

## 2. Rationale

QA metrics in this study include graded accuracy scores and Likert-type educational quality scores, both of which involve expert judgment. Without formal assessment of agreement, observed scores may reflect rater-specific bias rather than properties of the evaluated content.

Accordingly, inter-rater agreement analysis is incorporated to:

- Assess the consistency of expert evaluations
- Identify metrics or domains with high subjective variability
- Provide transparency for IRB and peer reviewers

---

## 3. Raters and Rating Procedure

### 3.1 Rater Characteristics

- Raters are board-certified radiologists or senior trainees with domain expertise
- All raters receive standardized written instructions and scoring rubrics
- No rater is involved in the generation of the evaluated content

### 3.2 Rating Independence

- Raters score cards **independently**
- No discussion or consensus-building occurs prior to initial scoring

---

## 4. Metrics Subject to Inter-Rater Agreement Analysis

Inter-rater agreement is assessed for the following metrics:

1. **Technical Accuracy** (3-level ordinal scale: 1.0 / 0.5 / 0.0)
2. **Educational Quality** (5-point Likert scale)

Efficiency metrics are excluded from formal agreement analysis due to their exploratory and optional nature.

---

## 5. Statistical Methods

### 5.1 Accuracy Metric

- Agreement for technical accuracy is assessed using **weighted Cohen’s kappa** (for two raters) or **Fleiss’ kappa** (for more than two raters)
- Quadratic or linear weights are applied to reflect the ordinal nature of the scale

### 5.2 Educational Quality Metric

- Agreement for educational quality is assessed using **intraclass correlation coefficient (ICC)**
- A two-way random-effects model with absolute agreement is preferred

---

## 6. Interpretation of Agreement Statistics

Agreement statistics are interpreted using conventional thresholds:

| Statistic | Interpretation |
|----------:|----------------|
| < 0.20 | Poor agreement |
| 0.21–0.40 | Fair agreement |
| 0.41–0.60 | Moderate agreement |
| 0.61–0.80 | Substantial agreement |
| > 0.80 | Excellent agreement |

These thresholds are used descriptively and do not determine study validity.

---

## 7. Handling of Discrepant Ratings

- Discrepant ratings are retained for agreement analysis
- For downstream analyses, consensus scores may be derived through structured adjudication
- The adjudication process is documented separately and does not affect agreement statistics

---

## 8. Sample Size Considerations

- Formal sample size calculation for agreement statistics is not mandatory
- Agreement analysis is performed only when a minimum number of commonly rated items is available
- Agreement estimates with wide confidence intervals are reported with appropriate caution

---

## 9. Reporting Principles

Inter-rater agreement results are:

- Reported separately from primary QA outcomes
- Presented with confidence intervals where applicable
- Used to contextualize the reliability of human evaluation

---

## 10. Summary Statement

This inter-rater agreement analysis plan provides a transparent and standardized approach to assessing the reliability of expert QA judgments. By explicitly defining metrics, statistical methods, and interpretation principles, the framework enhances the credibility and reproducibility of the study’s evaluation process.

