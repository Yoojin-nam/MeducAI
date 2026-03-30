# MeducAI Pipeline Canonical Specification v1.0

**Status:** Archived · Frozen
**Superseded by:** `0_Protocol/05_Pipeline_and_Execution/Pipeline_Canonical_Specification.md`
**Do not use this file for new decisions or execution.**
**Applies to:** Step01 (S1) → Step02 (S2) → Step03 (S3) → Step04 (S4) → Step05 (S5)
**Compliance:** MI-CLEAR-LLM 2025
**Last Updated:** 2025-12-20 (v1.5: S3/S4/S5 업데이트 반영)

**⚠️ S1 Schema/Structure Complete Freeze (2025-12-19):**

As of 2025-12-19, the S1 output schema (`stage1_struct.jsonl`) and structure are **completely frozen** at version 1.3. No further structural changes to the S1 output format are permitted. The pipeline is ready to proceed to downstream stages (S2, S3, S4) with this schema as the stable contract.

**Note:** While the schema is frozen, **S1 prompt improvements are allowed and planned** for future iterations. Prompt changes must not alter the output schema structure defined in `S1_Stage1_Struct_JSON_Schema_Canonical.md` (v1.3).

---

## 0. Purpose and Scope

본 문서는 MeducAI 파이프라인에서 사용되는 **개념 단위(Entity)**,
**실행 단계(S1/S2)**,
**프롬프트·JSON·안전성 계약**을 **단일 기준 문서**로 정의한다.

**Related Documents:**
- `Pipeline_Execution_Plan.md` - JSONL contract and execution details
- `04_Step_Contracts/` - Step-specific contracts and schemas

본 문서는 다음을 목적으로 한다.

1. S1–S2 책임 경계의 고정
2. 카드 수·이미지·정책 판단의 위치를 사전 명시
3. 프롬프트 변경에 따른 사후 해석 분쟁 방지
4. QA, IRB, 논문에서 그대로 인용 가능한 규약 제공

---

## 1. Pipeline Overview

```
Curriculum Objectives
        ↓
Step01 (S1): Group-level Structuring
        ↓
Entities (Conceptual Units)
        ↓
Step02 (S2): Execution-only Card Generation
        ↓
Candidate Cards (Q1, Q2, Q3 per entity)
        ↓
Step03 (S3): Policy Resolution & Image Spec Compilation
        ↓
Image Specifications (Q1/Q2 card images + S1 table visuals)
        ↓
Step04 (S4): Image Generation & Manifest Creation
        ↓
Rendered Images (PNG files)
        ↓
Step05 (S5): Export (PDF Builder for S0 QA / Anki Deck Packaging)
        ↓
Distribution Artifacts
```
Pipeline Overview (One-line)
S1 (Structure-only entity definition) → S2 (Exact-N execution) → S3 (State-only compiler: policy resolution & image spec) → S4 (Render-only image generation) → S5 (Packaging: PDF/Anki)

Each step has strictly bounded authority: no step generates, modifies, or interprets responsibilities owned by another.

---

## 2. Canonical Definition of Entity (S1-Level)

### 2.1 Authoritative Definition

**An Entity is a minimal, exam-meaningful concept unit defined in S1,
designed to be independently expanded into candidate cards in S2.**

* Entity ≠ Objective
* Entity ≠ Card

---

### 2.2 Entity Properties (Binding)

| Property       | Rule               |
| -------------- | ------------------ |
| Ownership      | Exactly one Group  |
| Mutability     | Immutable after S1 |
| Quota          | None               |
| Learner-facing | No                 |

---

### 2.3 Entity Criteria (All Required)

1. **Exam independence**
2. **Multi-card generatability**
3. **Semantic coherence**
4. **Granularity balance**

Too broad → split
Too narrow → discard

---

## 3. Step01 (S1): Group-Level Structuring

### 3.1 Role of S1

S1 is the **single authority for structure definition**.

S1 MUST:

* Infer group scope
* Generate ONE master table
* Define entity list

S1 MUST NOT:

* Decide card counts
* Assign importance
* Decide image necessity
* Select card types

---

### 3.2 S1 Mandatory Outputs (JSON)

```json
{
  "group_id": "...",
  "objective_summary": "...",
  "group_objectives": [...],
  "visual_type_category": "...",
  "master_table_markdown_kr": "...",
  "entity_list": [...],
  "table_infographic_style": "...",
  "table_infographic_prompt_en": "..."
}
```

---

## 4. Step02 (S2): Execution-Only Card Generation

### 4.1 Authoritative Definition

**Step02 (S2) is a policy-agnostic execution stage that generates
exactly N text-only Anki cards for a given entity, and nothing more.**

---

### 4.2 Canonical Input

```
(entity_name, cards_for_entity_exact = N)
```

* entity_name: immutable
* N: externally computed (from Allocation)

---

### 4.3 Hard Rules (Binding)

1. `len(anki_cards) == N` (typically N=3: Q1, Q2, Q3)
2. Text-only output (no image files)
3. `image_hint` field for Q1/Q2 (required), forbidden for Q3
4. No entity reinterpretation
5. No policy inference

**Card Roles:**
- Q1: BASIC card with `image_hint` (required)
- Q2: MCQ card with `image_hint` (required, v1.5)
- Q3: MCQ card without `image_hint` (forbidden)

Violation → hard failure

---

## 5. Step03 (S3): Policy Resolution & Image Spec Compilation

### 5.1 Authoritative Definition

**Step03 (S3) is a state-only compiler that resolves image policies
and compiles image generation specs from S2 outputs, without generating or modifying content.**

---

### 5.2 Canonical Input

* S2 results (`s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` (new format, 2025-12-23) 또는 `s2_results__arm{X}.jsonl` (legacy, backward compatible))
* S1 structure (`stage1_struct__arm{X}.jsonl`)

---

### 5.3 Hard Rules (Binding)

1. **Policy Resolution (Hardcoded):**
   - Q1: `image_placement="FRONT"`, `card_type="BASIC"`, `image_required=true`
   - Q2: `image_placement="BACK"`, `card_type="MCQ"`, `image_required=true` (v1.5)
   - Q3: `image_placement="NONE"`, `card_type="MCQ"`, `image_required=false`

2. **Image Spec Compilation:**
   - Q1/Q2: Compile `image_hint` → `prompt_en` (includes card text and answer)
   - S1 Table Visual: Compile `master_table_markdown_kr` → table visual spec

3. **No LLM calls** (deterministic compiler)
4. **No content generation/modification**

Violation → hard failure

---

## 6. Step04 (S4): Image Generation & Manifest Creation

### 6.1 Authoritative Definition

**Step04 (S4) is a render-only stage that generates images from S3 specs
using a fixed image model, without medical interpretation or content modification.**

---

### 6.2 Canonical Input

* S3 image spec (`s3_image_spec__arm{X}.jsonl`)

---

### 6.3 Hard Rules (Binding)

1. **Fixed Image Model:** `models/nano-banana-pro-preview` (arm-independent)
2. **Image Specifications:**
   - Card images: `aspect_ratio="4:5"`, `image_size="1K"` (1024x1280)
   - Table visuals: `aspect_ratio="16:9"`, `image_size="2K"`
3. **Deterministic Filenames:**
   - Card images: `IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.png`
   - Table visuals: `IMG__{run_tag}__{group_id}__TABLE.png`
4. **Fail-Fast Rules:**
   - Q1 image generation failure → FAIL-FAST
   - Q2 image generation failure → FAIL-FAST (v1.5)
   - Table visual image generation failure → FAIL-FAST
   - Q3 image existence → FAIL (forbidden)

5. **No prompt modification** (use S3 `prompt_en` as-is)
6. **No medical interpretation**

Violation → hard failure

---

## 7. Step05 (S5): Export & Packaging

### 7.1 Authoritative Definition

**Step05 (S5) consists of two export tools: PDF Builder for S0 QA and Anki Deck Exporter.**

---

### 7.2 PDF Builder (S0 QA)

**Purpose:** Build PDF packets for S0 QA evaluation

**Input:**
* S1 structure, S2 results, S3 policy manifest, S4 image manifest

**Output:**
* `SET__{group_id}__{arm}__{set_id}.pdf`

**Structure:**
1. Master Table (from S1)
2. Infographic image (S1 table visual from S4)
3. Cards (12 cards with images based on `image_placement`)

**Rules:**
* Read-only consumption of frozen schemas
* Identical layout across arms
* Blinded mode support (surrogate set_id)

---

### 7.3 Anki Export

**Purpose:** Export Anki deck with images

**Input:**
* S2 results (must include `group_path` field), S4 image manifest

**Output:**
* `anki_deck__{run_tag}__arm{X}.apkg`

**Image Placement (Hardcoded):**
* Q1: Image in Front
* Q2: Image in Back
* Q3: No image

**Tagging:**
* Card type tags: `Basic` or `MCQ` (MCQ_Vignette included in MCQ)
* Metadata tags from `group_path`: `Specialty:{specialty}`, `Anatomy:{anatomy}`, `Modality:{modality}`, `Category:{category}`
* **Requirement:** `group_path` field MUST be present in S2 results for proper tagging. Missing `group_path` will generate warnings and tags will only include card type.

**Fail-Fast Rules:**
* Q1 image missing → FAIL
* Q2 image missing → FAIL (v1.5)
* Q3 image exists → FAIL

**Warnings:**
* Missing `group_path` in S2 results → WARNING (tags incomplete, but export continues)

---

## 5. Prompt Contract (Applies to S1 & S2)

### 5.1 Global Enumerations (Frozen)

**Image necessity**

```
IMG_REQ | IMG_OPT | IMG_NONE
```

**Card types**

```
Basic_QA
MCQ_Vignette
Cloze_Finding
Image_Diagnosis
Physics_Concept
```

Hard rule:
IMG_NONE → Image_Diagnosis forbidden

---

### 5.2 Mathematical Expression Policy

* LaTeX ❌
* ASCII operators ❌
* Unicode symbols only ✅

---

### 5.3 Safety Rules

* Invented statistics forbidden
* Controversial topics → textbook consensus only
* Absolute wording discouraged unless universally true

---

## 8. Responsibility Boundary Summary

| Decision          | Owner             |
| ----------------- | ----------------- |
| Entity definition | S1                |
| Card count        | Code (Allocation) |
| Card generation   | S2                |
| Image policy      | S3 (hardcoded)    |
| Image spec        | S3 (compiler)     |
| Image generation | S4 (render-only)  |
| Image model       | S4 (fixed, arm-independent) |
| Packaging         | S5                |

---

## 7. Canonical Statement (Final)

> This document defines the single canonical specification of the MeducAI pipeline,
> fixing the meaning of entities, the execution role of S2, and the non-negotiable prompt and safety contracts.
> Any deviation must be versioned and explicitly justified prior to QA or deployment.
