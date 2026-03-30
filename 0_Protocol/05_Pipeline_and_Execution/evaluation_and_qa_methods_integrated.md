# Evaluation and QA Methods (Integrated Protocol)

Status: Canonical (Protocol – Evaluation & QA Methods)
Version: 1.0
Applies to: QA Phase (S0, S1) and Exploratory User Evaluation
Last Updated: 2025-12-17

---

## 1. Overview

This section describes the integrated **evaluation and quality assurance (QA) methodology** for assessing LLM-generated educational content in this study. The methods are designed to ensure **methodological rigor, reproducibility, educational validity, and safety**, while explicitly addressing known risks of LLM-assisted learning such as automation bias, variability, and subjective evaluator dependence.

All evaluation procedures are predefined, protocol-driven, and independent of downstream analytical results.

---

## 2. Evaluation Unit and Scope

**Reference:** See `00_Governance/Evaluation_Unit_and_Scope_Definition.md` for the canonical definition of evaluation units and scope.

The primary unit of evaluation is the **individual Anki-style question–answer card**. Visual materials are treated as secondary educational artifacts and excluded from primary quantitative evaluation.

---

## 3. QA Workflow and Governance

QA is conducted in a structured, multi-step workflow:

1. **Initial screening** to confirm consistency with predefined generation policies
2. **Methodological checkpoint review** to identify risks related to assistance quality, misleading content, expertise mismatch, repeatability, and scope alignment
3. **Quantitative scoring** using predefined QA metrics
4. **Documentation of QA outcomes** (approve, revise, or exclude)

QA functions as a **governance mechanism**, not merely a scoring exercise, and may override quantitative scores when safety or methodological concerns are identified.

---

## 4. Methodological Checkpoints

Before quantitative scoring, each card undergoes mandatory checkpoint evaluation addressing:

- **Assistance quality classification** (structured, expert-like vs generic or weakly grounded)
- **Misleading risk assessment** to mitigate automation bias
- **Expertise sensitivity** relative to the intended learner level
- **Repeatability risk**, particularly dependence on image-only cues
- **Scope alignment**, ensuring educational rather than clinical framing

Cards failing critical checkpoints are revised or excluded regardless of numerical scores.

---

## 5. Quantitative QA Metrics

**Reference:** See `QA_Metric_Definitions.md` for detailed definitions of all QA metrics.

QA metrics are grouped into three domains:
1. **Technical Accuracy** (primary quantitative outcome) - scored using a three-level ordinal scale (1.0, 0.5, 0.0)
2. **Educational Quality** (co-primary quantitative outcome) - scored on a five-point Likert scale
3. **Efficiency** (exploratory quantitative outcome) - time-related measures collected when feasible

---

## 6. Inter-Rater Agreement

To assess the reliability of human evaluation, inter-rater agreement is formally analyzed:

- **Technical accuracy**: weighted Cohen’s kappa or Fleiss’ kappa, depending on the number of raters
- **Educational quality**: intraclass correlation coefficient (two-way random-effects, absolute agreement)

Inter-rater agreement is reported as a methodological quality indicator and does not determine content validity.

---

## 7. Subgroup and Longitudinal Analysis

Given substantial baseline heterogeneity among learners, analyses prioritize **within-subject longitudinal change** rather than between-subject comparisons.

Baseline characteristics are collected prior to exposure. Subgroup analyses (e.g., by learner experience level) are predefined and treated as exploratory unless adequately powered. Effect sizes and confidence intervals are emphasized over p-values.

---

## 8. Data Handling and Missing Data

- All QA decisions and scores are logged at the item level
- Missing data are documented; no imputation is performed unless justified
- Analyses are conducted on available paired data where applicable

---

## 9. Ethical and Methodological Considerations

The evaluation framework explicitly acknowledges limitations of LLM-generated content and human judgment. By separating governance checkpoints from scoring, restricting efficiency to exploratory analyses, and quantifying inter-rater reliability, the protocol minimizes overinterpretation and supports transparent reporting.

---

## 10. Summary Statement

This integrated evaluation and QA methodology provides a structured, reproducible framework for assessing LLM-generated Anki-style educational content. By combining governance-based checkpoints, standardized quantitative metrics, reliability analysis, and conservative longitudinal evaluation, the protocol ensures that conclusions are methodologically sound and suitable for IRB review and peer-reviewed publication.

