# QA Metric Definitions

Status: Canonical (QA Metric Specification)  
Version: 1.1  
Applies to: QA Phase (S0, S1) and FINAL gate QA (FINAL)  
Related Documents:  
- `00_Governance/Evaluation_Unit_and_Scope_Definition.md`  
- `QA_Methodological_Checkpoints.md`  
- `06_QA_and_Study/QA_Operations/QA_Evaluation_Rubric.md` (operational rubric based on these definitions)

Last Updated: 2025-12-29

---

## 1. Purpose of This Document

This document defines the **quantitative and qualitative metrics** used in the QA phase of this study.
The goal is to ensure that all evaluative judgments regarding LLM-generated Anki cards are:

- Operationally defined
- Reproducible across evaluators
- Suitable for statistical analysis and IRB review

All metrics are applied **at the individual Anki card level**, as defined in the evaluation unit document.

---

## 2. Overview of QA Metrics

QA metrics are grouped into three domains:

1. **Technical Accuracy** (primary quantitative outcome for S0 and S1)
2. **Educational Quality** (primary quantitative outcome for S0 and S1)
3. **Efficiency** (exploratory quantitative outcome)

Qualitative assessments are used as supportive context and are not treated as primary endpoints.

### 2.1 PRIMARY endpoint for FINAL gate assurance, binary major_error

For FINAL gate QA, the primary safety and quality outcome is an error rate (%), defined on MAJOR errors as a binary item-level variable `major_error`.

Define `major_error` as follows, deterministically and pre-specified before data collection:

- `major_error` equals TRUE if any of the following are TRUE.
  - `blocking_error` equals true.
  - `technical_accuracy` equals 0.0.
  - `image_blocking_error` equals true, for example, modality mismatch, anatomy grossly wrong, or image makes the learning goal unattainable.
- `major_error` equals FALSE otherwise.

Reporting rule:

- Claims about error rate (%) must use `major_error`. Graded scales, including 0.0, 0.5, 1.0 and 1 to 5 Likert, are secondary descriptors for interpretation and tool-effect analyses.

---

## 3. Technical Accuracy Metric

### 3.1 Definition

Technical accuracy reflects the **factual correctness and clinical validity** of an Anki card, including:

- Accuracy of the core concept or diagnosis
- Correctness of the explanatory rationale
- Absence of misleading or incorrect statements

### 3.2 Scoring Scale (Graded Item-Level Accuracy)

Accuracy is scored using a **three-level ordinal scale**:

| Score | Definition |
|------:|------------|
| **1.0** | Core concept and explanation are fully correct; suitable for board-level learning without revision |
| **0.5** | Core concept is correct, but explanation contains minor omissions, imprecise phrasing, or missing nuance |
| **0.0** | Core concept is incorrect, misleading, or likely to cause misunderstanding |

### 3.3 Scoring Principles

- Scoring is performed **per card**, not per group or topic
- Partial credit (0.5) is permitted only when the **central learning objective is preserved**
- Any error that may plausibly mislead a learner results in a score of **0.0**

### 3.4 Use in Analysis

- Accuracy scores are summarized as mean ± SD and distribution
- Inter-rater agreement (e.g., weighted κ) may be reported when applicable
- Accuracy is treated as a **primary QA outcome**

---

## 4. Educational Quality Metric

### 4.1 Definition

Educational quality reflects the **pedagogical value** of a card, independent of factual correctness.
A technically correct card may still have low educational quality.

### 4.2 Domains of Educational Quality

Evaluators consider the following dimensions:

- Board examination relevance
- Coverage of topic core concepts
- Appropriateness of content depth
- Learning efficiency (signal-to-noise ratio)

### 4.3 Scoring Scale (Likert-Type)

Educational quality is scored on a **five-point Likert scale**:

| Score | Interpretation |
|------:|----------------|
| **5** | Highly valuable; directly targets core concepts essential for examination |
| **4** | Valuable; addresses important concepts with minor limitations |
| **3** | Adequate; correct but marginally useful or overly generic |
| **2** | Limited value; peripheral or inefficient for exam-oriented learning |
| **1** | Poor value; unlikely to aid learning despite possible correctness |

### 4.4 Scoring Principles

- Quality is scored **independently of accuracy**
- Evaluators are instructed to prioritize **educational usefulness**, not stylistic preference
- Scores of 1–2 trigger mandatory qualitative comments during QA

### 4.5 Use in Analysis

- Quality scores are summarized descriptively and inferentially
- Associations between accuracy and quality are explored but not assumed
- Quality is treated as a **co-primary QA outcome**

---

## 5. Difficulty Metric (Exam Appropriateness)

### 5.1 Definition

Difficulty reflects the **appropriateness of the card's difficulty level** for the target board examination (specialist-level radiology board exam).

This metric evaluates whether the card:
- Is appropriately challenging for specialist-level examination
- Is too easy (can be solved without image or with excessive hints)
- Is too difficult (requires subspecialty-level knowledge)

### 5.2 Target Difficulty Level

**Target**: Specialist-level radiology board examination
- Appropriate for **board-certified radiologist** candidates
- Should require **image interpretation skills** and **clinical reasoning**
- Should NOT be solvable from text description alone (for image-dependent cards)
- Should NOT require **subspecialty-level** knowledge (e.g., interventional radiology subspecialty)

### 5.3 Scoring Scale (Ordinal)

Difficulty is scored using a **three-level ordinal scale**:

| Score | Definition | Examples |
|------:|------------|----------|
| **1.0** | Appropriate difficulty for specialist-level board exam. Requires image interpretation and clinical reasoning. | Card requires analyzing image features, comparing findings, or applying clinical knowledge |
| **0.5** | Slightly too easy or slightly too difficult, but still acceptable. Minor adjustments needed. | Card is solvable with minimal image analysis, or requires slightly advanced knowledge |
| **0.0** | Inappropriate difficulty: Too easy (can be solved without image or with excessive hints) OR too difficult (requires subspecialty-level knowledge). | Card can be solved from text description alone, or requires interventional radiology subspecialty knowledge |

### 5.4 Common Difficulty Issues

#### 5.4.1 Too Easy (0.0)

**Symptoms**:
- Card can be solved **without looking at the image** (text description gives away the answer)
- Front text contains **excessive hints** (e.g., "sonographic Murphy sign is positive, what is the diagnosis?")
- Image description in front text **directly states the finding** (e.g., "CT shows popcorn calcification, what is the diagnosis?")
- Card tests only **recall of terminology** rather than **image interpretation skills**

**Examples**:
- ❌ "Sonographic Murphy sign is positive. What is the diagnosis?" (Answer: Acute cholecystitis - can be solved without image)
- ❌ "CT shows popcorn-like calcification. What is the diagnosis?" (Answer: Osteochondroma - can be solved without image)
- ❌ "Functional cyst or endometrioma?" (Tests only terminology recall, not image interpretation)

**Fix**: Remove excessive hints from front text. Make image essential for solving the question.

#### 5.4.2 Too Difficult (0.0)

**Symptoms**:
- Requires **subspecialty-level knowledge** (e.g., interventional radiology procedures, advanced techniques)
- Requires **research-level** or **rare exception** knowledge
- Tests knowledge beyond **general radiology specialist** scope

**Examples**:
- ❌ "What is the optimal catheter size for this interventional procedure?" (Requires interventional radiology subspecialty knowledge)
- ❌ "What is the rare variant of this condition that occurs in 0.1% of cases?" (Requires research-level knowledge)

**Fix**: Focus on high-yield, commonly tested topics for general radiology specialist examination.

### 5.5 Scoring Principles

- Difficulty is scored **per card**, considering both text and image (if present)
- **Current 2-card policy (Q1/Q2 only; images on BACK)**:
  - Evaluate whether the **Front is solvable from text alone** (no deictic image references), while remaining board-appropriate.
  - For **Q1 (BASIC, IMAGE_ON_BACK)**: penalize excessive “giveaway” phrasing that collapses the reasoning.
  - For **Q2 (MCQ, IMAGE_ON_BACK)**: penalize stems where the correct choice is obvious without meaningful reasoning, or requires missing image-only info.
  - **Q3/NO_IMAGE is deprecated** in the current pipeline.
- **Blocking error consideration**: Cards with difficulty 0.0 may be flagged as blocking errors if they significantly undermine educational value

### 5.6 Use in Analysis

- Difficulty scores are summarized as mean ± SD and distribution
- Association with educational quality is explored
- Difficulty is treated as a **secondary QA outcome** (informative for prompt improvement)

---

## 6. Efficiency Metric (Exploratory)

### 6.1 Definition

Efficiency reflects the **time-related cost or benefit** associated with using an Anki card for learning.

### 6.2 Measurement Options

Depending on feasibility, efficiency may be assessed using one or more of the following:

- Self-reported time to understand a card
- Time required for expert editing or correction
- Relative comparison to baseline materials for the same topic

### 6.3 Scoring and Analysis

- Efficiency metrics are treated as **exploratory outcomes**
- No single efficiency measure is mandatory
- Results are reported descriptively and interpreted cautiously

---

## 7. Qualitative Annotations

### 6.1 Purpose

Qualitative annotations are used to:

- Explain low accuracy or quality scores
- Identify systematic error patterns
- Support discussion and interpretation

### 6.2 Role in Analysis

- Qualitative data are **not used for hypothesis testing**
- They inform revision decisions and contextualize quantitative findings

---

## 8. Handling of Ambiguous Cases

When evaluators encounter ambiguity:

- Conservative scoring is applied
- Uncertain cases are flagged for consensus review
- Final decisions are documented for auditability

---

## 9. Summary Statement

This document establishes standardized, item-level QA metrics for evaluating LLM-generated Anki cards.
By separating **technical accuracy**, **educational quality**, and **efficiency**, the framework ensures that evaluation reflects both factual correctness and pedagogical value, while maintaining reproducibility and statistical rigor.