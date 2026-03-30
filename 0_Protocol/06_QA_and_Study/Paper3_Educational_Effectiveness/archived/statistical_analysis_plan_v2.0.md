# Statistical Analysis Plan (SAP)
## MeducAI Pipeline-1 & Pipeline-2 Study – Version 2.0

**Version:** 2.0  
**Status:** Archived (Pre-specified; Frozen prior to analysis)  
**Superseded by:** `0_Protocol/06_QA_and_Study/Study_Design/Statistical_Analysis_Plan.md`
**Do not use this file for new decisions or execution.**
**Supersedes:** Statistical_Analysis_Plan_v1.0  
**Applies to:**
- **Pipeline-1:** Expert QA (Step S0, Step S1) – Paper-1
- **Pipeline-2:** Prospective Observational UX Study – Paper-2

---

## 1. Purpose and Scope

This Statistical Analysis Plan (SAP) defines all statistical analyses for the MeducAI project **a priori**, aligned with **QA Framework v2.0**, to ensure:

- Protection against data-driven analytic decisions,
- Full reproducibility and auditability (MI-CLEAR-LLM compliant),
- Methodological defensibility for IRB and peer-reviewed publication.

All analyses described herein are **pre-specified**. Any deviation will be explicitly documented, versioned, and justified.

---

## 2. Study Architecture Overview (v2.0 Aligned)

MeducAI comprises **two analytically distinct pipelines**, each with independent objectives and statistical logic.

### 2.1 Pipeline-1: Expert QA (Paper-1)

- **Design:** Two-stage QA framework
  - **Step S0:** 6-arm factorial expert QA (deployment model selection)
  - **Step S1:** One-shot acceptance sampling (release gate)
- **Unit of Analysis:**
  - S0: **Set** (= group × arm artifact bundle)
  - S1: **Card** (individual Anki item)
- **Primary Objective:**
  - Select and freeze a single deployment configuration under safety and efficiency constraints

### 2.2 Pipeline-2: Prospective Observational UX Study (Paper-2)

- **Design:** Prospective observational cohort study
- **Comparison:** Naturalistic MeducAI users vs non-users
- **Unit of Analysis:** Individual participant
- **Primary Objective:**
  - Evaluate educational and usability impact of MeducAI usage

The two pipelines are **analytically independent**; results from Pipeline-1 determine deployment configuration but are **not pooled** with Pipeline-2 outcomes.

---

## 3. Analysis Populations

### 3.1 Pipeline-1 (QA)

- **Full QA Set (FQS):**
  - All evaluated Sets (S0) and Cards (S1) that completed blinded expert review

No per-protocol exclusion is applied in Pipeline-1; all generated QA data are analyzed as observed.

### 3.2 Pipeline-2 (UX Study)

#### 3.2.1 Full Analysis Set (FAS)

Includes participants who:
- Provided informed consent,
- Completed the post-intervention survey,
- Have non-missing primary outcome data.

#### 3.2.2 Per-Protocol Set (Exploratory)

Subset of FAS excluding:
- Minimal MeducAI exposure (<5 total usage hours),
- Incomplete covariate data.

Per-protocol analyses are explicitly labeled **exploratory**.

---

## 4. Outcomes

### 4.1 Pipeline-1 Outcomes (QA)

#### 4.1.1 Primary Endpoints (S0)

1. **Safety (Hard Gate)**
   - Card-level blocking error rate (Accuracy = 0.0)
   - Threshold: ≤1%

#### 4.1.2 Primary Endpoint (S1)

- **Blocking Error Count** in acceptance sample (n = 838)
  - Acceptance criterion: ≤2 errors (one-sided 99% CI)

#### 4.1.3 Secondary QA Outcomes

- Overall Card Quality (Likert 1–5) — used for non-inferiority analysis
- Editing Time (minutes per set, self-reported via survey) — used for decision criteria among non-inferior arms
- Clarity & readability score (Likert 1–5)
- Clinical/Exam Relevance score (Likert 1–5)
- Expertise Discrepancy Index (EDI)
- Disagreement rate (Resident vs Attending)
- Cost per set (USD)
- Latency per set (seconds)

All secondary QA outcomes are **descriptive or exploratory**, except Overall Card Quality (used for non-inferiority testing) and Editing Time (used for decision criteria).

---

### 4.2 Pipeline-2 Outcomes (UX Study)

#### 4.2.1 Co-Primary Outcomes

The study employs **multiple co-primary outcomes** to capture both theoretical constructs (cognitive load) and clinically/educationally intuitive measures (learning efficiency, exam readiness, knowledge retention).

**Co-Primary Outcome 1: Extraneous Cognitive Load**
- Leppink et al. scale
- Continuous (1–7), mean of predefined items
- **Rationale:** Measures instructional design quality and structural support

**Co-Primary Outcome 2: Learning Efficiency (Time to Achievement)**
- Self-reported time efficiency metric
- **Definition:** Perceived time reduction to achieve the same learning outcome, compared to traditional methods
- **Measurement:** 
  - Continuous scale: "Compared to studying without MeducAI, how much time did you save to achieve the same level of understanding?" (0–100% time reduction, or absolute hours saved)
  - Alternative: Ratio of actual study time to estimated time without MeducAI
- **Rationale:** Directly addresses educational efficiency, a key concern for learners and educators

**Co-Primary Outcome 3: Perceived Exam Readiness Improvement**
- Self-reported improvement in exam preparation confidence
- **Measurement:**
  - Change score: Post-intervention exam readiness (1–7 Likert) minus baseline exam readiness (1–7 Likert)
  - Or: Single-item post-intervention assessment: "How much has MeducAI improved your confidence in passing the board examination?" (1–7 Likert)
- **Rationale:** Captures learners' perceived improvement in exam-specific preparation, directly relevant to educational goals

**Co-Primary Outcome 4: Knowledge Retention (Long-term)**
- Self-reported or objective measure of knowledge retention
- **Measurement options:**
  - **Option A (Self-reported):** "How well do you feel you retained the information learned using MeducAI compared to traditional methods?" (1–7 Likert)
  - **Option B (Objective, if feasible):** Follow-up knowledge assessment (e.g., 4–6 weeks post-intervention) using a standardized quiz covering topics studied with MeducAI vs. traditional methods
  - **Option C (Hybrid):** Self-reported retention confidence combined with spaced repetition performance metrics from Anki logs
- **Rationale:** Addresses long-term learning outcomes, critical for medical education

#### 4.2.2 Key Secondary Outcomes

These outcomes provide additional evidence of educational impact and are analyzed with appropriate statistical consideration:

- **Intrinsic cognitive load** (Leppink et al. scale)
- **Germane cognitive load** (Leppink et al. scale)
- **Academic self-efficacy** (MSLQ-derived)
- **Learning satisfaction** (validated online learning satisfaction scale)
- **Technology acceptance (TAM)** (perceived usefulness, ease of use, behavioral intention)
- **Trust in AI-generated content** (custom scale)
- **Perceived exam score improvement** (self-reported): "How much do you expect MeducAI to improve your actual board examination score?" (1–7 Likert or percentage points)
- **Study time efficiency** (objective): Total study hours logged via MeducAI vs. self-reported total study time, adjusted for learning outcomes

#### 4.2.3 Exploratory Outcomes

- Item-level survey responses
- Open-ended qualitative feedback (descriptive only)
- Dose–response relationships between usage intensity and outcomes
- Subgroup analyses by baseline characteristics

---

## 5. Exposure Variables (Pipeline-2)

### 5.1 Primary Exposure

- **MeducAI use status:** User vs non-user (binary)

### 5.2 Dose–Response Exposures

- Total usage time (hours)
- Review frequency
- Composite usage intensity score (log-transformed if skewed)

---

## 6. Covariates (Pipeline-2)

Pre-specified covariates included in adjusted analyses:

- Age group
- Sex
- Training status
- Hospital type
- Baseline learning stress
- Sleep quality
- Mood stability
- Physical activity

Covariates were selected **a priori** based on educational theory and prior literature.

---

## 7. Descriptive Statistics

- Continuous variables:
  - Mean ± SD or median (IQR), depending on distribution
- Categorical variables:
  - Frequency and percentage

Baseline characteristics will be summarized by exposure group.

---

## 8. Statistical Analyses

### 8.1 Pipeline-1 Analyses (QA)

#### 8.1.1 Step S0: Non-Inferiority Analysis

**Canonical Reference:** `0_Protocol/06_QA_and_Study/QA_Operations/S0_Noninferiority_Criteria_Canonical.md`

**Two-Layer Decision Framework:**

1. **Layer 1: Safety Endpoint (Gatekeeper)**
   - **Metric:** Major error rate (proportion of cards scored 0)
   - **Notation:** `RD0 = p0_T - p0_A` (risk difference)
   - **Safety Pass Criterion:** `UpperCI(RD0) ≤ +0.02` (two-sided 95% CI)
   - **Purpose:** Prevents unacceptable increases in major errors (0-score cards)

2. **Layer 2: Primary NI Endpoint**
   - **Endpoint:** **Mean Accuracy Score** (card-level accuracy 0/0.5/1 averaged across all cards in the set)
   - **Baseline Arm:** Arm A (Baseline, Flash Low) — default configuration
     - **Alternative:** Arm E (High-End) can be configured as reference if needed
   - **Comparison:** Candidate arms (A–D) vs baseline arm (A, default)
   - **Framework:** One-sided non-inferiority
   - **Margin:** Δ = 0.05 (mean score scale, default)
     - **Configuration options:** Δ = 0.03 (conservative), 0.05 (default), 0.08 (cost-driven)
     - **Rationale:** On a 12-card set, Δ = 0.05 implies allowing up to 0.6 points degradation, which is educationally meaningful and statistically defensible

Hypotheses:
- H0: `d ≤ -Δ` (candidate is inferior)
- H1: `d > -Δ` (candidate is non-inferior)

**Decision Rule:**
- Compute CI for `d` (difference in mean accuracy)
- **NI PASS if:** `LowerCI(d) > -Δ`
- **CI Level:** 90% two-sided CI (default) for operational selection

**Statistical Method:**
- **Primary:** Clustered paired bootstrap over `(rater_id, group_id)` pairs
- **CI construction:** Percentile CI
- **Fixed seed:** Default = 20251220 (configurable)

**Note:** Arm F (GPT-5.2) serves as an external benchmark/anchor but is not the primary reference for non-inferiority testing. Arm E (High-End) is recommended as reference for vendor consistency but implementation defaults to Arm A for operational simplicity.

#### 8.1.2 Step S1: Acceptance Sampling

- Method: Exact Clopper–Pearson upper bound
- Confidence level: One-sided 99%
- Decision rule fixed (n = 838, c ≤ 2)

#### 8.1.3 Inter-Rater Reliability

- Accuracy (0 / 0.5 / 1.0): Fleiss’ κ
- Likert outcomes: Weighted κ

---

### 8.2 Pipeline-2 Analyses (UX Study)

#### 8.2.1 Co-Primary Outcome Analyses

**Analysis Strategy:** Each co-primary outcome is analyzed independently. Given multiple co-primary outcomes, a **hierarchical testing procedure** is applied to control family-wise error rate while maintaining statistical power.

**Hierarchical Testing Order:**
1. **Extraneous Cognitive Load** (theoretical construct)
2. **Learning Efficiency** (intuitive, learner-centered)
3. **Perceived Exam Readiness Improvement** (educationally relevant)
4. **Knowledge Retention** (long-term outcome)

**Stopping Rule:** If a co-primary outcome fails to reach significance (p > 0.05), subsequent co-primary outcomes are still tested but interpreted with appropriate caution regarding multiplicity.

**For Each Co-Primary Outcome:**

- **Unadjusted comparison:**
  - Independent t-test or Mann–Whitney U test (depending on distribution)
  - Effect size: Mean difference with 95% CI
- **Adjusted analysis:**
  - Multivariable linear regression (or logistic regression for binary outcomes)
  - Pre-specified covariates included (see Section 6)
  - Effect size: Adjusted mean difference or standardized β with 95% CI

**Primary Predictor:** MeducAI use (binary: user vs. non-user)

**For Change Scores (e.g., Exam Readiness Improvement):**
- Paired t-test or Wilcoxon signed-rank test for within-subject change
- Linear regression with baseline value as covariate (ANCOVA approach)
- Effect size: Mean change with 95% CI

#### 8.2.2 Key Secondary Outcome Analyses

- Similar regression models for each key secondary outcome
- Effect sizes:
  - Mean difference
  - Standardized β
  - 95% confidence intervals
- **Interpretation:** Key secondary outcomes are analyzed with awareness of multiple comparisons but without formal multiplicity correction, as they provide supportive evidence for co-primary findings.

#### 8.2.3 Dose–Response Analysis

- Linear regression among MeducAI users only
- Exposure variables: Total usage time (hours), review frequency, composite usage intensity
- Non-linearity assessed using restricted cubic splines (if sample size permits, n ≥ 50)
- Effect sizes: β coefficients per unit increase in exposure, with 95% CI

#### 8.2.4 Sensitivity Analyses

- **Per-protocol analysis:** Restricted to participants with ≥5 hours of MeducAI exposure
- **Complete-case vs. imputed analysis:** Comparison of results with and without imputation (if applicable)
- **Subgroup analyses:** By baseline characteristics (training level, prior LLM experience, baseline stress)

---

## 9. Missing Data Handling

- Primary approach: Complete-case analysis
- Scale-level imputation:
  - Mean imputation if ≥80% of items completed
- Multiple imputation is **not planned** due to sample size constraints

---

## 10. Reliability and Consistency Checks

- Internal consistency: Cronbach’s α
- Distribution checks: ceiling/floor effects
- Inter-item correlation review

---

## 11. Statistical Software

- **R** (≥ 4.3.0): tidyverse, lme4, rms, psych
- **Python**: preprocessing, visualization, QA logs

---

## 12. Significance Thresholds

- **Co-primary outcomes:** Two-sided α = 0.05 for each co-primary outcome, with hierarchical testing procedure to control family-wise error rate
- **Key secondary outcomes:** Two-sided α = 0.05 (interpreted with awareness of multiple comparisons)
- **Exploratory outcomes:** Descriptive or hypothesis-generating; p-values reported but not used for formal inference
- Confidence intervals at 95% for all effect estimates
- P-values reported exactly (no dichotomization)

---

## 13. Deviations from SAP

Any deviation from this SAP will be:
- Prospectively documented,
- Versioned,
- Transparently reported in the final manuscript.

---

## 14. Version History

- **v1.0:** Initial SAP (Pipeline-2 only)
- **v2.0:** Full alignment with QA Framework v2.0; unified Pipeline-1 and Pipeline-2 SAP
- **v2.1:** Enhanced endpoints based on co-author feedback; added co-primary outcomes (Learning Efficiency, Exam Readiness Improvement, Knowledge Retention) and key secondary outcomes to strengthen clinical/educational relevance

## Appendix D. Human–Human Disagreement as an Irreducible Uncertainty Baseline

Inter-human disagreement observed in Pipeline-1 QA (e.g., resident–attending disagreement, IRR estimates) is interpreted as an empirical estimate of irreducible uncertainty in expert evaluation.

In subsequent system comparison studies, this disagreement rate serves as an empirical ceiling for achievable agreement, rather than as noise to be eliminated.

System performance that falls within the observed human–human disagreement range may be considered theoretically acceptable, even if not identical to individual human judgments.
