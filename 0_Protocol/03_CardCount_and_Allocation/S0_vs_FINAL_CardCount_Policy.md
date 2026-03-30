# S0 vs FINAL Card Count Policy

*(Step01 Anchoring Protocol — Final Canonical)*

**Status:** Canonical (Frozen)
**Applies to:** Step01 (S1 orchestration) → Step02 (S2 execution) → Allocation / Selection (FINAL)
**Last Updated:** 2025-12-19
**Version:** 2.1 (S0 allocation v2.1 정책 반영)
**Purpose:**
Fix the meaning of **“card count”** across **S0 vs FINAL**, prevent accidental reinterpretation in code, prompts, or documents, and enforce a single, auditable responsibility boundary.

---

## 0. One-Line Summary (Binding)

> **S0 fixes card count per set (group × arm) with a constant payload.
> FINAL fixes card count per group via allocation quotas.
> S2 never decides counts; it executes exactly `cards_for_entity_exact = N`.**

This sentence is the **primary interpretive anchor** for this document.

---

## 1. Definitions (Authoritative)

### 1.1 Control Units

* **Set (S0):** one execution instance = **group × arm**
* **Group (FINAL):** quota owner; group-level target `group_target_cards (q_i)` with fixed total

### 1.2 Meaning of `N` in S2

* `cards_for_entity_exact = N` is an **externally computed, binding integer**
* S2 output must satisfy:

```
len(anki_cards) == N
```

Violation → **Hard fail**

---

## 2. Policy: Step S0 (QA Experiment)

### 2.1 Purpose

S0 exists solely to support **fair arm comparison**
(e.g., safety, clarity, editing time, latency, cost).
**Deck size optimization is explicitly out of scope.**

### 2.2 Binding Rule (Non-Negotiable)

* **Control unit:** Set (= group × arm)
* **Card count:** Fixed per set
* **Canonical value:** `q = 12` (constant)

No other interpretation is permitted.

### 2.3 Entity Handling in S0 (Hard Rule, v2.1)

* **Deterministic 3×4 Entity Allocation (v2.1):**
  * If E >= 4: 첫 4개 엔티티 × 각 3장 = 12장 (표준 경로)
  * If E < 4: 모든 엔티티에 균등 분배하여 합계 12장 (fallback, 드문 케이스)
* Allocation artifact는 S2 실행을 위한 **기록(recording) 산출물**이며, 결정(decision)이 아니다.
* `cards_for_entity_exact`는 S2에 대한 **정확한 실행 지시**이다.

> **Clarification:**
> S0 allocation은 "최적화"나 "분배"가 아니라, **결정론적 규칙에 따른 기록**이다.
> E < 4인 경우는 QA 설계상 드문 케이스이며, 이 경우에만 3장 규칙을 위반할 수 있다.

---

## 3. Policy: FINAL (Deployment)

### 3.1 Global Target

* **TOTAL_CARDS = 6,000** (Canonical)

### 3.2 Binding Rule

* **Control unit:** Group
* **Control variable:** `group_target_cards (q_i)`
* **Entity-level allocation:** 각 엔티티당 **정확히 3장** (S0와 동일)
* **Invariant:**

```
Σ q_i = TOTAL_CARDS
Σ (cards_for_entity_exact per entity) = q_i (within each group)
```

### 3.3 Entity Allocation Policy (FINAL)

* **Canonical rule:** 각 엔티티당 **정확히 3장**
* Group-level quota `q_i`는 엔티티 수에 따라 결정됨:
  * `q_i = (number of entities in group) × 3`
* 이 정책은 S0의 3×4 규칙과 일관성을 유지한다.

### 3.4 Over-generation & Shortfall Guard

* Candidate generation may exceed `q_i`
* Selection enforces **exactly `q_i`**
* Any shortfall → **Hard fail**

---

## 4. Responsibility Boundaries (Non-Negotiable)

| Component                      | Responsibility                                                           |
| ------------------------------ | ------------------------------------------------------------------------ |
| **Allocation / Step01 (Code)** | Decide counts (S0 set payload; FINAL group quotas; derived per-entity N) |
| **S1 (LLM)**                   | Conceptual structuring only                                              |
| **S2 (LLM)**                   | Execute exactly `N` cards                                                |
| **S3**                         | Enforce selection counts                                                 |
| **S4**                         | Presentation / image pipeline only                                       |

Any deviation is a **protocol violation**.

---

## 5. Explicit Firewall: S0 vs FINAL

| Dimension             | S0                     | FINAL                      |
| --------------------- | ---------------------- | -------------------------- |
| Purpose               | QA / arm comparison    | Production / deployment    |
| Control unit          | Set (group × arm)      | Group                      |
| Card count            | Fixed constant (12)    | Computed quota             |
| Entity count          | Up to 4 (3×4 rule)     | One or more                |
| Allocation logic      | Deterministic 3×4     | Entity-level (3 cards each) |
| Artifact              | S0 allocation artifact | FINAL allocation artifacts |
| Conceptual continuity | ❌ None                 | —                          |

> **S0 is not a reduced or preliminary version of FINAL.**

---

## 6. Step01 Code Anchoring Points

### 6.1 Current State (Documented)

* Temporary knobs (e.g., `CARDS_PER_ENTITY`) may exist for development/smoke tests.

### 6.2 Required Invariants

* S2 remains **execution-only**
* Cardinality mismatch → **Hard fail**
* No importance, quota, image, or optimization logic in S2

### 6.3 Stabilization Path

* **P0 (Stabilization):** Temporary knobs allowed for smoke testing
* **P1 (Canonical):**

  * S0 uses `S0_FIXED_PAYLOAD_CARDS`
  * FINAL derives per-entity `N` strictly from group quotas and FINAL policies

---

## 7. Environment Variables (Minimal Contract)

### 7.1 Required Runtime

* `TEMPERATURE_STAGE1`, `TEMPERATURE_STAGE2`, `TEMPERATURE_STAGE4`, `TEMPERATURE_STAGE5`, `TIMEOUT_S`
* Provider-specific API keys

### 7.2 Card Count Knobs (Must Not Be Confused)

* `S0_FIXED_PAYLOAD_CARDS`
  → **Canonical S0 intent**
* `CARDS_PER_ENTITY` (deprecated)
  → **폐기됨. FINAL에서는 Entity당 3장으로 고정**

---

## 8. Change Policy (Hard Gate)

Any change to **Sections 0–5** requires:

1. Protocol-level review
2. CP re-validation
3. Canonical merge record

Silent modification is prohibited.

---

## 9. Canonical Handoff Sentence

> **Card counts are fixed per set in S0 and fixed per group in FINAL.
> Allocation code decides counts; LLM stages execute exactly and nothing more.**