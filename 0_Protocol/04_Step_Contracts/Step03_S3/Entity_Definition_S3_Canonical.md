# Canonical Definition of Step03 (S3-Level)

**MeducAI Step03 Protocol — Entity Definition**

- **Status:** Canonical · Frozen
- **Applies to:** Step03 (S3: Policy Resolver & Image Spec Compilation)
- **Boundary:** S2 → **S3** → S4
- **Last Updated:** 2025-12-20
- **Compliance:** MI-CLEAR-LLM / IRB-ready
- **Implementation Status:** ✅ **완료** (2025-12-20, v1.5)
  - `03_s3_policy_resolver.py` 구현 완료
  - Image policy 적용 (Q1: FRONT/required, Q2: BACK/required, Q3: NONE)
  - Image spec 컴파일 (Q1/Q2 카드 이미지 + S1 테이블 비주얼)
  - 프롬프트 번들 시스템: System/User 템플릿 분리, visual_type_category 기반 동적 선택
  - 프롬프트 생성: image_hint만 사용 (answer_text는 스펙 저장용, 프롬프트에는 미사용)
  - Join key SSOT: `(run_tag, group_id, entity_id, card_role)`

---

## 1. Purpose (Normative)

This document defines the **canonical meaning, scope, authority, and prohibitions**
of **Step03 (S3)** in the MeducAI pipeline.

Its purpose is to **permanently fix S3 as a state-only selection and QA gate** and to
**eliminate all ambiguity** regarding:

- generation vs selection
- execution vs judgment
- content vs state
- S3 vs S4 responsibility boundaries

This definition is **binding** for all future
protocols, code, prompts, QA procedures, and research documents.
Any deviation constitutes a **protocol violation**.

---

## 2. Authoritative One-Line Definition (Binding)

> **Step03 (S3) is a state-only compiler (Policy Resolver & ImageSpec Compiler) that**
> **resolves image policies, compiles image generation specs from S2 outputs,**
> **and never generates, modifies, or interprets content.**

Corollaries (non-negotiable):

- S3 **does not generate** content (cards or images)
- S3 **does not interpret** medical meaning
- S3 **does not decide** policy or quota (policies are hardcoded)
- S3 **does not render** or visualize content
- S3 **does not call LLM** (deterministic compiler)

---

## 3. Structural Position in the Pipeline

| Dimension        | Definition                                   |
|------------------|----------------------------------------------|
| Ownership        | Stateless governance & QA stage              |
| Input authority  | S2 outputs + code-defined parameters         |
| Control unit     | Group (FINAL) or Set (S0)                    |
| Primary role     | Selection, rule enforcement, validation      |
| Output nature    | State-only artifacts                         |
| Downstream       | S4 (image rendering & packaging)             |

Formal position:

```

S1 (Structure)
→ S2 (Execution)
→ S3 (Selection & QA — State-only)
→ S4 (Rendering / Presentation)

```

---

## 4. What S3 **IS** (Positive Definition)

S3 **is**:

- A **selection gate** operating on pre-generated cards
- A **rule enforcement engine**
- A **QA decision point (PASS / FAIL)**
- A **state recorder** for auditability
- A **non-creative, non-interpreting stage**

Formal identity:

- **S3 = Selection**
- **S3 = Enforcement**
- **S3 = QA**
- **S3 ≠ Generation**
- **S3 ≠ Interpretation**
- **S3 ≠ Rendering**

---

## 5. What S3 **IS NOT** (Explicit Prohibitions)

S3 **must not** perform any of the following actions.

### 5.1 Generation / Modification (Forbidden)

- ❌ Generate new cards
- ❌ Edit or rewrite card text
- ❌ Modify answers, explanations, or structure
- ❌ Add or remove medical facts

### 5.2 Interpretation / Reasoning (Forbidden)

- ❌ Infer modality, plane, or sequence
- ❌ Derive lesion class or imaging features
- ❌ Summarize or reinterpret medical meaning
- ❌ Judge clinical importance

### 5.3 Policy / Allocation (Forbidden)

- ❌ Decide card counts
- ❌ Adjust quotas or relax rules
- ❌ Apply weighting, importance, or optimization logic

### 5.4 Visual / Presentation (Forbidden)

- ❌ Generate image prompts from scratch (S3 compiles prompts from templates, but does not create new prompt content)
- ❌ Decide image layout or style beyond template selection
- ❌ Reclassify `IMG_REQ / IMG_OPT / IMG_NONE`

Formal negation:

- **S3 ≠ Policy**
- **S3 ≠ Optimization**
- **S3 ≠ Medical reasoning**
- **S3 ≠ Image pipeline**

Any violation is a **governance breach**.

---

## 6. Canonical Inputs (Read-Only)

S3 operates exclusively on **read-only inputs**.

### 6.1 From S1 (Authoritative Context)

- `group_id`
- `group_path`
- `entity_name`
- `visual_type_category`
- `master_table_markdown_kr`

These inputs are **immutable**.

---

### 6.2 From S2 (Candidate Card Pool)

Pre-generated cards including:

- `card_id`
- `front`
- `back`
- `card_type`
- `row_image_necessity`
- optional QA flags (e.g., `blocking_error`)

Cards may be **selected or excluded only**.
They must never be edited.

---

### 6.3 From Code (Control Parameters)

- `group_target_cards` (FINAL) or fixed payload (S0)
- `qa_mode` (S0 / FINAL)

S3 **does not compute** these values.

---

## 7. Canonical Outputs (State-Only)

S3 produces **state and evidence only**, never content.

### 7.1 Required Outputs

- PASS / FAIL decision
- Failure reason codes (if any)
- `selected_card_ids` (manifest)
- Selection trace (included / excluded with reasons)
- QA summary statistics

### 7.2 Explicitly Forbidden in Output

- Card text modifications
- New medical fields
- Modality / plane / sequence (must come from S2 image_hint)
- Imaging feature lists (must come from S2 image_hint)
- Image prompts created from scratch (S3 compiles prompts from templates using image_hint only)

Presence of any forbidden field → **Immediate FAIL**

---

## 8. Fail-Fast Rules (Hard Constraints)

S3 **must fail immediately** if any of the following occurs:

1. Schema violation in candidate cards
2. Image hard-rule violation
3. Blocking error in selected cards
4. Quota shortfall after exclusions
5. Quota mismatch after selection
6. Forbidden field detected in output

Fail-fast behavior is **mandatory**.

---

## 9. Relationship to Step02 (S2)

| Dimension | S2 | S3 |
|---------|----|----|
| Role | Execution | Selection & QA |
| Creativity | Allowed (within constraints) | ❌ Forbidden |
| Card count | Executes exact N | Enforces exact N |
| Content authority | Generates candidates | ❌ None |
| State recording | ❌ | ✅ |

> **S2 creates candidates.  
> S3 judges eligibility and completeness — not quality.**

---

## 10. Relationship to Step04 (S4)

| Dimension | S3 | S4 |
|---------|----|----|
| Output type | State-only | Rendered artifacts |
| Medical meaning | ❌ None | ❌ None |
| Image logic | ❌ Forbidden | ✅ Allowed (render-only) |
| Source-of-truth | Upstream | S1 + S3 manifest |

S3 hands off **only a manifest and state** to S4.
S4 must not request additional meaning from S3.

---

## 11. Governance & Violation Policy

- S3 is intentionally **non-creative**
- Any attempt to improve quality, clarity, or pedagogy at this stage
  constitutes a **protocol violation**
- Violations require:
  1. Immediate run failure
  2. Protocol review
  3. CP re-validation if Canonical change is proposed

Silent deviation is prohibited.

---

## 12. Canonical Handoff Summary (One Sentence)

> **Step03 (S3) is a state-only selection and QA gate.
> It selects existing cards, enforces rules, records PASS/FAIL and trace artifacts,
> and performs no generation, interpretation, policy, or rendering actions.**

---

**This definition is canonical and frozen.**