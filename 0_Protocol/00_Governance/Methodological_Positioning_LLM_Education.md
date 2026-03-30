# Methodological Proposal

Status: Canonical (Methodological Rationale)
Version: 1.0
Applies to: S0–FINAL (Global)
Purpose: Literature-grounded justification of MeducAI design

## A Governed, Reproducible Framework for LLM-Assisted Radiology Education

---

## 1. Background and Unmet Methodological Needs

Recent advances in large language models (LLMs) and vision–language models (VLMs) have demonstrated substantial progress in radiologic reasoning when high-quality inputs are provided. However, **three critical methodological gaps** remain unresolved in the current literature.

### 1.1 Reliability without governance is insufficient

Large-scale evaluations of contemporary VLMs have consistently shown that, although semantic reasoning is strong once accurate visual information is supplied, **unsupervised or autonomous use remains unreliable for clinical deployment** . Current studies primarily evaluate diagnostic accuracy under controlled conditions, but do not address how LLM outputs should be **constrained, audited, and operationalized** in real educational or clinical pipelines.

### 1.2 Assistance quality, not mere availability, determines human outcomes

Human–AI interaction studies demonstrate that **the quality of LLM assistance fundamentally alters radiologist performance**, influencing both diagnostic accuracy and susceptibility to misleading suggestions . Importantly, these effects are modulated by expertise, with domain experts showing resistance to low-quality assistance, whereas less experienced readers are more vulnerable .

Despite this, most educational LLM applications treat “AI assistance” as a binary condition, rather than a **structured, gradable intervention**.

### 1.3 Input modality and repeatability are underappreciated in educational design

Benchmarking studies reveal that **textual descriptions substantially outperform raw images alone**, not only in diagnostic accuracy but also in repeatability across runs . Variability increases markedly when image-only inputs are used, especially in difficult cases, highlighting a reproducibility risk that is rarely addressed in educational content generation .

However, existing studies largely frame this as a model performance issue, rather than an **educational design problem**.

---

## 2. Rationale for a New Methodological Framework

Taken together, these studies converge on a key insight:

> **The central challenge is no longer whether LLMs can reason, but how their reasoning should be constrained, staged, and translated into reliable educational artifacts.**

Current approaches lack:

1. Explicit separation between **generation, selection, and presentation**
2. Formal constraints preventing LLMs from making implicit pedagogical decisions
3. Reproducible audit trails linking prompts, outputs, and learner-facing materials

This gap motivates the present study.

---

## 3. Proposed Methodological Framework

We propose a **governed, stepwise LLM pipeline** for radiology education, explicitly designed to address the methodological shortcomings identified in prior work.

### 3.1 Principle 1: Decision authority is externalized from the LLM

Consistent with evidence that low-quality assistance can mislead users , the proposed framework **prohibits LLMs from making educational or quantitative decisions**, including:

* Number of learning items
* Item selection or prioritization
* Curriculum weighting

All such decisions are instead determined by **predefined policies and code-level rules**, ensuring that the LLM functions strictly as a *generator*, not a *decision-maker*.

---

### 3.2 Principle 2: Assistance quality is treated as a controlled experimental variable

Inspired by human–AI interaction studies distinguishing high- vs low-quality assistance , the framework defines each LLM configuration as a formally specified **arm**, comprising:

* Model identity
* Input modality (text, image, combined)
* Prompt constraints
* Post-processing rules

This enables **fair, auditable comparison** of assistance strategies, rather than informal experimentation.

---

### 3.3 Principle 3: Text-centric generation to maximize repeatability

Given the strong association between textual descriptions and repeatability , the framework prioritizes **structured text generation** as the primary educational artifact. Image generation, when used, is explicitly relegated to a downstream presentation step, preventing visual variability from contaminating core learning content.

This design directly addresses the repeatability limitations reported in prior VLM evaluations .

---

### 3.4 Principle 4: Stage separation to prevent automation bias

Automation bias arises when users implicitly trust AI outputs without understanding their provenance. To mitigate this risk, the pipeline enforces **strict stage separation**:

* Content structuring
* Content instantiation
* Quality gating
* Presentation

By ensuring that no single stage has end-to-end control, the framework aligns with calls for safer human–AI collaboration models .

---

## 4. Methodological Contribution Beyond Prior Studies

Unlike prior work that evaluates **model performance** or **human–AI interaction outcomes** in isolation, this study contributes a **methodological artifact**:

* A reproducible, governed pipeline
* Explicit failure modes and abort criteria
* Audit-ready artifacts linking prompts to learner-facing outputs

This reframes LLM-assisted radiology education from a question of *accuracy* to one of **system design and governance**.

---

## 5. Anticipated Impact

By grounding its design in empirically observed risks—misleading assistance, variability across inputs, and lack of repeatability—this framework provides a **generalizable methodology** for safely integrating LLMs into medical education.

Rather than asking *“Which model performs best?”*, the proposed study asks:

> **“Under what constraints can LLMs be reliably used as educational infrastructure?”**

---

## 6. Positioning Statement (for Introduction or Discussion)

> Building on recent evidence that LLM assistance quality, input modality, and repeatability critically influence human outcomes, we propose a governed, stepwise framework that transforms large language models from opaque advisors into reproducible educational instruments.