# MeducAI Initial Research Rationale (Archived)

**Status:** Frozen  
**Version:** 0.1  
**Derived from:** Initial IRB Proposal (Ver.4.0, 2025-12-13)  
**Role:** Historical / Rationale reference only  
**Executable Protocol:** NO

---

## 0. Document Purpose

This document preserves the **original conceptual, ethical, and educational rationale** underlying the MeducAI project as first articulated in the initial IRB research proposal.  
It is **not an execution protocol**, and it **must not be used** as an operational or analytical reference for current S0 / FINAL pipelines.

Its sole purposes are:
- To retain the intellectual and ethical origin of the study
- To support IRB, reviewer, or collaborator inquiries regarding *why* the study was designed as it is
- To serve as a historical scaffold for manuscript Introduction and Discussion sections

---

## 1. Why This Study Was Necessary

### 1.1 Structural burden of radiology board preparation

Radiology board preparation requires the rapid integration of:
- Vast quantities of heterogeneous information
- Continuously updated diagnostic frameworks and guidelines
- Visual pattern recognition tightly coupled to textual reasoning

Within limited training periods and high clinical workloads, residents are forced to self-structure largely uncurated materials. This environment predictably induces **excessive extraneous cognitive load**, impairing learning efficiency and increasing burnout risk.

### 1.2 Cognitive Load Theory as a central lens

Based on Cognitive Load Theory (Sweller, 1988; Leppink et al., 2013), learning failure in this context is not due to lack of motivation, but to **misalignment between information structure and working memory constraints**.

The initial proposal therefore framed MeducAI not as a content-expanding tool, but as a **cognitive load–reducing scaffold**, explicitly targeting:
- Reduction of extraneous load
- Support of germane load through structured repetition

---

## 2. Why Generative AI — and Why Carefully

### 2.1 Educational potential of LLMs and MLLMs

Generative AI offers capabilities uniquely suited to medical education:
- Automated summarization of complex knowledge
- Structural reorganization aligned with learning objectives
- Multimodal visualization of abstract diagnostic concepts

In radiology, where visual abstraction is central, MLLMs enable conversion of dense textual knowledge into **infographics, flow diagrams, and visual mnemonics** that support dual coding and retrieval practice.

### 2.2 Inherent risks: hallucination and automation bias

The initial proposal explicitly recognized that:
- LLM outputs are probabilistic and context-sensitive
- Hallucinated or subtly incorrect information poses unacceptable educational risk
- Automation bias and de-skilling are realistic downstream threats

Therefore, **direct deployment of AI-generated content without human verification was deemed ethically unacceptable**.

---

## 3. Why UX-Centered Evaluation (Not Accuracy)

### 3.1 Misalignment of traditional AI metrics

Conventional AI evaluation focuses on accuracy, benchmarks, or model-level performance. However, these metrics:
- Do not reflect learning efficiency
- Fail to capture cognitive and emotional burdens
- Are poorly aligned with educational outcomes

The initial study reframed effectiveness as a **learner-centered phenomenon**.

### 3.2 Core UX domains selected

The proposal therefore centered evaluation on:
- Cognitive load (primary)
- Academic self-efficacy
- Learning satisfaction
- Technology acceptance

Additionally, behavioral and emotional modifiers were included:
- Stress
- Sleep
- Mood
- Exercise

These were treated as **essential contextual variables**, not noise, enabling responsible interpretation of heterogeneous outcomes.

---

## 4. Why QA Was Separated from the User Study

### 4.1 Ethical and methodological separation

A key architectural decision was to **strictly separate**:
- User experience research (Track A)
- Content quality verification (Track B)

Expert QA was defined as:
- A safety and quality gate
- Not human-subject research
- Not performance evaluation of individuals

This separation minimized:
- Coercion risks
- Conflicts of interest
- Ethical ambiguity regarding expert contributors

### 4.2 QA as a Quality Gate, not an outcome

QA outputs were intentionally limited to:
- Technical accuracy
- Clinical relevance
- Coverage and clarity
- Inter-rater agreement (IRR)

All QA results were framed as **descriptive quality indicators**, not inferential study outcomes.

---

## 5. What Has Changed Since This Document

This document reflects the *conceptual origin* of MeducAI. Since its creation, substantial structural evolution has occurred:

- Introduction of **S0 vs FINAL** experimental separation
- Formal allocation artifacts and card-count governance
- Canonical document hierarchy and merge checkpoints
- Deterministic run tagging and reproducibility controls
- Explicit MI-CLEAR-LLM–aligned prompt governance

These changes do **not contradict** the original rationale; rather, they represent its **operational maturation**.

---

## 6. How This Document Should Be Used

Permitted uses:
- IRB clarification
- Reviewer response background
- Manuscript conceptual grounding
- Internal onboarding context

Prohibited uses:
- Execution guidance
- Statistical analysis reference
- Pipeline or code validation

---

## Final Note

This document exists to answer a single enduring question:

> *Why was MeducAI designed this way in the first place?*

It should remain frozen as a historical anchor, while all executable logic resides exclusively in canonical protocol documents.
