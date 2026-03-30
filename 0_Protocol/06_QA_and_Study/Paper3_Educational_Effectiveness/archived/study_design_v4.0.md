# Study Design – MeducAI (v4.1)

**Date:** 2025-12-23  
**Status:** Archived (Prospective; pre-specified)  
**Superseded by:** `0_Protocol/06_QA_and_Study/Study_Design/Study_Design.md`
**Do not use this file for new decisions or execution.**
**Supersedes:** Study_Design_MeducAI_v4.0  
**Aligned with:** QA Framework v2.0, SAP v2.1, Survey Overview v2.1, EDA Decision Interpretation

---

## 1. Overall Study Architecture

MeducAI is designed as a **two-pipeline, prospectively pre-specified study**, explicitly separating **content generation & safety validation** from **educational effectiveness evaluation**. This separation is intentional and central to methodological validity.

- **Pipeline-1 (Paper-1): Expert QA & Deployment Model Selection**  
  Objective: Select and freeze a single, safe, and efficient LLM deployment configuration for large-scale content generation.

- **Pipeline-2 (Paper-2): Prospective Observational UX Study**  
  Objective: Evaluate the real-world educational impact of MeducAI-generated materials on radiology residents’ cognitive load, self-efficacy, satisfaction, and technology acceptance.

The two pipelines are **analytically independent**. Results from Pipeline-1 determine the deployment configuration but are **not pooled** with Pipeline-2 outcome analyses.

---

## 2. Conceptual Rationale

### 2.1 Group-first Educational Modeling

Based on EDA of 1,767 radiology learning objectives collapsed into **312 semantically coherent groups**, MeducAI adopts a **Group-first deployment strategy**.

Key justifications:
- Objective-level deployment is impractical and noisy.
- Curriculum weight is highly concentrated (top 20% of groups ≈ 50% of total weight).
- Group-level handling enables scalable QA, representative sampling, and reproducible allocation.

All downstream processes—QA sampling, card budgeting, table/infographic generation—operate at the **Group** level.

---

## 3. Pipeline-1: Expert QA & Deployment Model Selection (Paper-1)

### 3.1 Design Overview

Pipeline-1 employs a **two-stage QA framework**:

1. **Step S0:** 6-arm factorial expert QA for deployment model selection
2. **Step S1:** One-shot acceptance sampling for full-scale release approval

This pipeline prioritizes **patient safety analogues**, operational efficiency, and reproducibility.

---

### 3.2 Step S0 – Expert QA (Model Selection)

#### 3.2.1 Design

- **Design type:** Factorial, non-inferiority-oriented expert evaluation
- **Arms:** 6 fixed arms varying by model scale, reasoning, and retrieval configuration
- **Unit of analysis:** Set (= group × arm artifact bundle)

Each Set includes:
- One master table (or summary table)
- A fixed **12-card Anki payload**
- Infographic (if applicable)

The 12-card payload is fixed to standardize workload and reduce variance across arms.

---

#### 3.2.2 Sampling Strategy

- **Sampling frame:** All 312 groups
- **Sample size:** 18 groups (canonical)
- **Sampling method:** Weight-stratified sampling based on EDA-derived group weights

Hard coverage constraints ensure representation across:
- Subspecialties
- Imaging modalities
- High- and low-weight (tail) groups

---

#### 3.2.3 Evaluation & Roles

- **Per set:** 2-person paired cross-evaluation
  - 1 board-certified attending radiologist (safety authority)
  - 1 senior radiology resident (usability and clarity evaluator)

Primary endpoints:
1. **Technical accuracy (blocking error rate)** – safety hard gate

Secondary endpoints:
- **Overall Card Quality (Likert 1–5)** – used for non-inferiority analysis
- Clarity, relevance, cost, and latency

---

#### 3.2.4 Decision Logic

- Arms exceeding a **1% blocking error rate** are immediately excluded.
- Among safety-passing arms, candidate arms (A–D) are compared to the reference arm (E, High-End) using a **one-sided non-inferiority framework** on Overall Card Quality (Δ = 0.5 on 1–5 Likert scale).
- Low-cost arms are eligible for selection only if non-inferiority is demonstrated.

The selected arm is **conditionally frozen** as the deployment model.

---

### 3.3 Step S1 – Full-scale Release Gate

After S0 freeze, the selected deployment model is used to generate the full content set (≈6,000–12,000 cards).

#### 3.3.1 Design

- **Design type:** Acceptance sampling (one-shot)
- **Unit of analysis:** Individual card
- **Sample size:** n = 838 cards

#### 3.3.2 Decision Rule

- Blocking errors ≤ 2 in the sample guarantees a population blocking error rate < 1% with one-sided 99% confidence.
- PASS → final release approval and deployment freeze.
- FAIL → targeted remediation or regeneration.

---

## 4. Pipeline-2: Prospective Observational UX Study (Paper-2)

### 4.1 Design Overview

- **Design type:** Prospective observational cohort study
- **Population:** Radiology residents preparing for the 2026 board examination
- **Comparison:** Naturalistic MeducAI users vs non-users
- **Intervention:** Voluntary use of MeducAI-generated study materials

No randomization or enforced usage is applied, preserving ecological validity.

---

### 4.2 Outcomes

#### 4.2.1 Co-Primary Outcomes

The study employs **multiple co-primary outcomes** to comprehensively evaluate MeducAI's educational impact, balancing theoretical constructs with clinically and educationally intuitive measures.

**Co-Primary Outcome 1: Extraneous Cognitive Load**
- Leppink et al. scale (1–7 continuous)
- **Rationale:** Measures instructional design quality and structural support provided by MeducAI

**Co-Primary Outcome 2: Learning Efficiency (Time to Achievement)**
- Self-reported time efficiency: perceived time reduction to achieve the same learning outcome
- **Measurement:** Continuous scale (0–100% time reduction) or absolute hours saved
- **Rationale:** Directly addresses educational efficiency, a key concern for learners and educators

**Co-Primary Outcome 3: Perceived Exam Readiness Improvement**
- Self-reported improvement in exam preparation confidence
- **Measurement:** Change score (post-intervention minus baseline) or single-item post-assessment
- **Rationale:** Captures learners' perceived improvement in exam-specific preparation

**Co-Primary Outcome 4: Knowledge Retention (Long-term)**
- Self-reported retention confidence or objective follow-up assessment (if feasible)
- **Measurement:** Likert scale (1–7) or standardized quiz 4–6 weeks post-intervention
- **Rationale:** Addresses long-term learning outcomes, critical for medical education

#### 4.2.2 Key Secondary Outcomes

- Intrinsic and germane cognitive load (Leppink et al. scale)
- Academic self-efficacy (MSLQ-derived)
- Learning satisfaction (validated online learning satisfaction scale)
- Technology acceptance (TAM)
- Trust in AI-generated educational content
- Perceived exam score improvement (self-reported)
- Study time efficiency (objective, from usage logs)

#### 4.2.3 Covariates

- Stress, sleep quality, mood stability, physical activity
- Training level and institutional characteristics
- Baseline exam readiness, prior LLM experience

---

### 4.3 Data Sources

- **Survey data:** Single post-exposure survey
- **Objective usage logs:** Time, frequency, and intensity of MeducAI usage

Survey and log data are linked via anonymized identifiers.

---

## 5. Statistical Considerations

- All hypotheses, endpoints, and analyses are pre-specified in **SAP v2.0**.
- Pipeline-1 and Pipeline-2 analyses are conducted independently.
- No multiplicity correction is applied; secondary analyses are exploratory.

---

## 6. Bias Control and Reproducibility

- **Full rater blinding** in Pipeline-1
- **MI-CLEAR-LLM compliance** for all generation and QA steps
- Version-controlled prompts, configuration logs, and freeze declarations

---

## 7. Ethical and Governance Considerations

- Pipeline-1 involves expert evaluators and contains no human subject outcomes.
- Pipeline-2 is conducted under IRB approval with informed consent.
- QA evaluators are explicitly excluded from Pipeline-2 participation.

---

## 8. Summary Statement

This study design enables MeducAI to be evaluated both as:
1. A **safe, reproducible AI content generation system** (Pipeline-1), and
2. A **real-world educational support tool** with measurable cognitive and experiential impact (Pipeline-2).

The strict separation of pipelines, pre-specified decision rules, and theory-grounded outcomes together ensure methodological rigor suitable for high-impact radiology and medical education journals.
