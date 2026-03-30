# S4_Image_Cost_and_Resolution_Policy.md

**Path**
`04_Step_Contracts/Step04_S4/S4_Image_Cost_and_Resolution_Policy.md`

**Status**: Canonical · Frozen
**Applies to**: Step04 (S4 — Image Rendering & Presentation)
**Last Updated**: 2025-12-20
**Compliance**: MI-CLEAR-LLM / IRB-ready
**Implementation Status**: ✅ **완료** (2025-12-20)
- `04_s4_image_generator.py` 구현 완료
- Fixed image model: `gemini-2.5-flash-image` (arm-independent)
- Aspect ratio: 4:5 (S4_EXAM)
- Image size: 1K (1024x1280)
- Deterministic filename mapping 구현

---

## 1. Purpose (Normative)

This document defines the **canonical policy** governing:

* image **resolution**
* image **aspect ratio**
* image **model selection**
* image **cost control**
* **arm-level consistency** requirements

for **Step04 (S4)** in the MeducAI pipeline.

Its purpose is to **prevent silent experimental bias, cost drift, and arm-dependent artifacts** by fixing all image-related degrees of freedom **outside model comparison**.

This policy is **binding** for:

* all S4 code paths
* all experimental arms (S0–FINAL)
* all QA and audit procedures

Any deviation constitutes a **protocol violation**.

---

## 2. Foundational Principle (Binding)

> **Images in MeducAI are presentation artifacts, not experimental variables.**

Corollaries (non-negotiable):

* Image resolution **must not differ across arms**
* Image model choice **must not differ across arms**
* Image cost **must be predictable before execution**
* No image parameter may encode or imply model superiority

---

## 3. Dual-Lane Cost & Resolution Model (Canonical)

S4 operates under a **strict dual-lane architecture**, with **lane-specific resolution policies**.

| Lane       | Control Unit | Purpose                 | Cost Profile  |
| ---------- | ------------ | ----------------------- | ------------- |
| S4_CONCEPT | Group        | Conceptual illustration | High, fixed   |
| S4_EXAM    | Card         | Exam-style realism      | Low, scalable |

---

## 4. Resolution Policy (Why These Resolutions)

### 4.1 S4_CONCEPT (Group-Level Infographic)

**Canonical Resolution**

* **Aspect ratio**: 16:9
* **Resolution**: 3840 × 2160 (4K)

**Rationale**

1. **Single image per group**

   * Cost amortized over all cards in the group
2. **Table-like layout**

   * Requires horizontal space for structure
3. **Distribution-safe**

   * Supports slide, PDF, and large-screen viewing
4. **No cost explosion**

   * Group count is fixed and small

> Therefore, **high resolution is justified and controlled**.

---

### 4.2 S4_EXAM (Card-Level Exam Image)

**Canonical Resolution**

* **Aspect ratio**: 4:5
* **Resolution**: 1024 × 1280 (≈1K)
* **JPEG Quality**: 85 (optimized for Anki)
* **Target File Size**: ≤ 100KB per image

**Rationale**

1. **Many images**

   * Cost scales linearly with card count
   * 2-card policy: Entity당 2개 이미지 (Q1, Q2 각각 독립적)
2. **Exam realism**

   * Clinical exam images are not ultra-high-res
3. **Mobile-first review**

   * Optimized for Anki / handheld viewing
   * Anki recommendation: 파일 크기 ≤ 100KB
4. **Cost containment**

   * Higher resolution provides no educational gain
5. **Anki App Compatibility**

   * File size optimization via JPEG quality=85
   * CSS-based responsive sizing (`max-height: 45vh`)

> Therefore, **low but sufficient resolution with optimized compression is mandatory**.

---

## 5. Model Selection Policy (Why This Model)

### 5.1 Canonical Rule

> **All S4 images must be generated using a single, fixed image model per run.**

The image model is:

* **declared once**
* **identical across all arms**
* **independent of LLM provider**

---

### 5.2 Rationale

1. **Arm fairness**

   * Image quality must not advantage any arm
2. **Experimental validity**

   * Model comparison concerns **text & reasoning**, not visuals
3. **Cost predictability**

   * Mixed models obscure cost accounting
4. **Governance clarity**

   * One model → one audit trail

---

### 5.3 Explicit Prohibitions

* ❌ Arm-specific image models
* ❌ Adaptive model switching
* ❌ Resolution-dependent model choice
* ❌ “Better model for better arm” logic

Any of the above → **Immediate FAIL**

---

## 6. Cost Control Policy (Why This Is Safe)

### 6.1 Cost Predictability Formula

Total image cost per run is computable **before execution**:

```
Total Cost
= (# Groups × Cost_S4_CONCEPT_4K)
+ (# Cards with IMG_REQ/OPT × Cost_S4_EXAM_1K)
```

There is **no stochastic multiplier**.

---

### 6.2 Hard Caps (Binding)

* No upscaling beyond canonical resolution
* No retry-based quality escalation
* No prompt-driven resolution inflation

S4 is **non-creative by design**.

---

## 7. Arm-Level Consistency Policy

### 7.1 Binding Rule

> **Image artifacts must be identical in specification across all arms.**

This includes:

* resolution
* aspect ratio
* model
* rendering parameters
* retry policy

---

### 7.2 Rationale

Without this rule:

* Arm comparison becomes confounded
* Reviewer perception bias is introduced
* MI-CLEAR-LLM compliance is violated

Therefore, **image parameters are removed from the experimental degrees of freedom**.

---

## 8. Relationship to S4 Canonical Definition

This policy **does not expand S4 authority**.

S4 remains:

* render-only
* non-interpretive
* non-decisional

This document answers **how S4 renders**, not **what S4 decides**.

---

## 9. Governance & Failure Conditions

### 9.1 Hard Fail Conditions

Any of the following triggers **immediate run failure**:

* Resolution mismatch across arms
* Lane mixing (CONCEPT vs EXAM)
* Image model variation
* Undeclared image parameters
* Cost-affecting parameter drift

---

### 9.2 Auditability

All image parameters must be recorded in:

* runtime manifest
* S4 metadata
* CP-0 checklist

Silent deviation is prohibited.

---

## 10. One-Sentence Canonical Summary

> **S4 image resolution, model choice, and cost are fixed, lane-specific, and arm-invariant, ensuring that images function solely as presentation artifacts and never as experimental variables.**