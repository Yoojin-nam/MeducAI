# MeducAI EDA Decision Interpretation (Based on EDA_1780_Decision)

## Purpose

This document records the **official interpretation and decisions derived from the EDA results**, serving as a stable reference for subsequent steps (S0 QA design, deployment model selection, and full-scale generation).

This file is **not an analysis artifact** but a **decision-level record** that freezes the rationale behind key architectural and experimental choices.

---

## EDA Snapshot (Frozen Facts)

* **Total objectives analyzed**: 1,767
* **Grouping rule**: Category-aware group-first (Anatomy – Modality/Type – Category; fallback without Category)
* **Total groups**: 312
* **Total curriculum weight sum**: 1,535.654

### Weight Distribution

* **Top 20% of groups** account for **49.9%** of total weight
* **Gini coefficient**: **0.47**

Interpretation:

* Curriculum weight is **moderately to highly concentrated**
* A small subset of groups dominates educational importance

---

## Primary Decision Derived from EDA

### Decision 1: Objective-level deployment is impractical

Given that:

* 1,767 objectives collapse into 312 semantically coherent groups
* The top quintile of groups contributes approximately half of the total weight

➡️ **Deploying, sampling, or validating content at the individual-objective level would be inefficient, noisy, and unscalable.**

### Decision 2: Group-first deployment is structurally justified

EDA directly supports the following design choice:

> **All downstream processes (QA sampling, deployment, allocation, and generation) shall operate at the Group level, not the Objective level.**

This justifies:

* Group-based QA sampling (S0)
* Group-level table/infographic generation
* Group-level card allocation

---

## Weight-informed Allocation Rationale

Given the observed weight concentration:

* Uniform group sampling would under-represent high-impact groups
* Objective-count–based allocation would ignore curricular priorities

➡️ **Weight-proportional allocation is required** to preserve curricular representativeness.

This applies to:

* QA sample selection (S0)
* Expected card allocation (e.g., ~6,000 total cards)
* Image and infographic generation load

---

## Implications for S0 QA Design

The EDA results directly motivate the following S0 design principles:

* **Sampling unit**: Group
* **Sampling strategy**: Weight-stratified (not uniform)
* **Purpose**: Validate deployment model choice, not exhaustively evaluate all objectives

Transition statement (approved):

> *Based on this structural concentration, the S0 QA phase was designed to sample representative groups across the weight spectrum rather than individual objectives.*

---

## Implications for Deployment Model Selection

The EDA establishes a fixed constraint for model selection:

* The deployment model must perform reliably across **heterogeneous group weights**
* Errors or inefficiencies in high-weight groups have disproportionate impact

Therefore, deployment model selection prioritizes:

1. **Technical accuracy (blocking error avoidance)**
2. **Editing time minimization**, especially in high-weight groups

EDA explicitly does **not** justify:

* Model switching by subspecialty
* Objective-level model tuning

---

## What EDA Does *Not* Decide

To prevent overreach, the following are **out of scope for EDA**:

* Final QA arm outcomes
* Final deployment model choice
* Absolute card count per group (only proportional guidance)

These are deferred to:

* S0 QA results
* Deployment Decision Rule

---

## Status

* **EDA phase**: ✅ Closed
* **Structural assumptions**: Frozen
* **Next dependency**: S0 QA results → Deployment Model Decision

This document is intended to be cited or referenced (not regenerated) in:

* QA Framework documentation
* README / Notion project overview
* Methods section (design rationale)