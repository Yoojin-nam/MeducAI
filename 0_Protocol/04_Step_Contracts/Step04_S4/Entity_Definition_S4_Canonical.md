# Canonical Definition of Step04 (S4-Level)

**MeducAI Step04 Protocol — Rendering & Presentation**

* **Status:** Canonical · Frozen
* **Applies to:** Step04 (S4: Image Rendering & Packaging)
* **Boundary:** S3 → **S4** → Distribution
* **Last Updated:** 2025-12-20
* **Compliance:** MI-CLEAR-LLM / IRB-ready
* **Implementation Status:** ✅ **완료** (2025-12-20, v1.5)
  - `04_s4_image_generator.py` 구현 완료
  - Gemini 이미지 생성 API 통합 (`models/nano-banana-pro-preview`)
  - Deterministic 파일명 매핑 (카드 이미지 + 테이블 비주얼)
  - 스펙 종류별 분기: 카드 이미지(4:5, 1K) vs 테이블 비주얼(16:9, 2K)
  - Q1/Q2/테이블 비주얼 이미지 누락 시 FAIL-FAST
  - Fixed image model (arm-independent)

---

## 1. Purpose (Normative)

This document defines the **canonical meaning, scope, authority, and prohibitions**
of **Step04 (S4)** in the MeducAI pipeline.

Its purpose is to **permanently fix S4 as a render-only presentation stage** and to
**eliminate all ambiguity** regarding:

* generation vs rendering
* medical reasoning vs visualization
* concept illustration vs exam realism
* S4 vs S1/S2/S3 responsibility boundaries

This definition is **binding** for all future
protocols, code, prompts, QA procedures, and research documents.
Any deviation constitutes a **protocol violation**.

---

## 2. Authoritative One-Line Definition (Binding)

> **Step04 (S4) is a render-only stage that converts**
> **upstream-approved content and manifests into images and presentation artifacts,**
> **without generating, modifying, or interpreting medical meaning.**

Corollaries (non-negotiable):

* S4 **does not generate** medical content
* S4 **does not interpret** medical meaning
* S4 **does not decide** selection, quota, or importance
* S4 **does not feed information back** upstream

---

## 3. Structural Position in the Pipeline

| Dimension       | Definition                               |
| --------------- | ---------------------------------------- |
| Ownership       | Stateless rendering & presentation stage |
| Input authority | S1 context + S3 manifest (read-only)     |
| Control unit    | Card (selected) or Group (concept image) |
| Primary role    | Image rendering (using S3-compiled prompts) |
| Output nature   | Rendered visual artifacts                |
| Downstream      | Packaging / distribution only            |

Formal position:

```
S1 (Structure)
→ S2 (Execution)
→ S3 (Selection & QA — State-only)
→ S4 (Rendering / Presentation)
→ Distribution
```

---

## 4. What S4 **IS** (Positive Definition)

S4 **is**:

* A **rendering engine**
* A **presentation-layer transformer**
* A **style- and layout–controlled image generator**
* A **downstream-only consumer** of upstream state

Formal identity:

* **S4 = Rendering**
* **S4 = Visualization**
* **S4 ≠ Generation**
* **S4 ≠ Interpretation**
* **S4 ≠ Selection**
* **S4 ≠ Policy**

---

## 5. What S4 **IS NOT** (Explicit Prohibitions)

S4 **must not** perform any of the following actions.

### 5.1 Medical Generation / Interpretation (Forbidden)

* ❌ Generate new medical facts
* ❌ Infer diagnosis, modality, plane, or sequence
* ❌ Add imaging features not present upstream
* ❌ Summarize, reinterpret, or “improve” explanations

---

### 5.2 Selection / Policy (Forbidden)

* ❌ Select or exclude cards
* ❌ Decide card counts or quotas
* ❌ Reclassify `IMG_REQ / IMG_OPT / IMG_NONE`
* ❌ Apply importance, weighting, or optimization logic

---

### 5.3 Upstream Boundary Violation (Forbidden)

* ❌ Modify card text (`front`, `back`)
* ❌ Modify `row_image_necessity`
* ❌ Request additional meaning from S3
* ❌ Write back decisions to upstream stages

Formal negation:

* **S4 ≠ Policy**
* **S4 ≠ QA**
* **S4 ≠ Medical reasoning**
* **S4 ≠ Content authority**

Any violation is a **governance breach**.

---

## 6. Canonical Inputs (Read-Only)

S4 operates exclusively on **read-only inputs**.

### 6.1 From S3 (Authoritative Manifest)

* `selected_card_ids`
* PASS / FAIL decision
* selection trace
* QA log

S4 **must not** request additional information beyond this manifest.

---

### 6.2 From Upstream Context (Pass-through)

Depending on lane:

**Common**

* `group_id`
* `group_path`
* `entity_name`

**Concept lane**

* `visual_type_category`
* `master_table_markdown_kr`

**Exam lane**

* modality / sequence / plane
* lesion class
* exam function

> These fields are **assumed correct** and **must not be inferred or altered**.

---

## 7. Dual-Lane Architecture (Canonical)

S4 is explicitly divided into **two non-overlapping lanes**.

---

### 7.1 S4_CONCEPT (Conceptual / Infographic Lane)

**Source:** S1-derived context
**Purpose:** Conceptual understanding

Characteristics:

* Infographic / schematic style
* Labels and minimal text allowed
* Clean, educational layout
* No exam realism

Key invariant:

> **S4_CONCEPT illustrates structure, not exams.**

---

### 7.2 S4_EXAM (Exam-Style / Realistic Lane)

**Source:** S3-selected cards
**Purpose:** Exam simulation

Characteristics:

* Realistic radiology-exam style
* No labels, arrows, or text overlays
* Typical modality appearance
* Neutral grayscale

Key invariant:

> **If it looks like a slide, it is wrong.
> If it looks like a test question image, it is correct.**

---

### 7.3 Lane Separation (Hard Rule)

* CONCEPT and EXAM **must never mix**
* A single image belongs to **exactly one lane**
* Style crossover is a **hard failure**

---

## 8. Canonical Outputs

S4 outputs **rendered artifacts only**.

### 8.1 Allowed Outputs

* Image files (PNG/WebP/etc.)
* Image manifest with generation metadata
* Deterministic image specs (resolution, ratio) - inherited from S3

### 8.2 Explicitly Forbidden Outputs

* Modified card text
* New medical metadata
* Selection decisions
* QA judgments
* Any upstream-facing control signal

Presence of forbidden output → **Immediate FAIL**

---

## 9. Relationship to Upstream Steps

### 9.1 Relationship to S3

| Dimension       | S3             | S4               |
| --------------- | -------------- | ---------------- |
| Role            | Selection & QA | Rendering        |
| Output          | State-only     | Visual artifacts |
| Medical meaning | ❌              | ❌                |
| Authority       | Upstream       | None             |

> **S3 decides “what survives.”
> S4 decides “how it looks,” and nothing else.**

---

### 9.2 Relationship to S1/S2

* S1/S2 define **content**
* S4 defines **presentation**
* No backward dependency is allowed

---

## 10. Governance & Violation Policy

* S4 is intentionally **non-creative**
* Any attempt to improve pedagogy, correctness, or clarity at this stage
  constitutes a **protocol violation**
* Violations require:

  1. Immediate run failure
  2. Protocol review
  3. CP re-validation if Canonical change is proposed

Silent deviation is prohibited.

---

## 11. Canonical Handoff Summary (One Sentence)

> **Step04 (S4) is a render-only presentation stage.
> It consumes upstream-approved content and manifests,
> produces visual artifacts,
> and performs no generation, interpretation, selection, or policy decisions.**

---

**This definition is canonical and frozen.**