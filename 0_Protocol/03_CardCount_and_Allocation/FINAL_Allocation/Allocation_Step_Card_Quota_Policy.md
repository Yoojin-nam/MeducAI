# Allocation Step — Card Quota Policy (v1.0, **CP-2 Compliant**)

**Status:** Canonical (Frozen once S0 starts)
**Applies to:** **FINAL generation only** (TOTAL_CARDS control) + downstream S3 quota enforcement
**Explicitly Excludes:** **Step S0 fixed payload (12 cards/set)**
**Single Authority:** Allocation step is the **only** component allowed to decide card counts in FINAL

---

## 0. One-line Principle (Non-negotiable)

> **All card counts are decided only in FINAL Allocation.**
> S1/S2/S3/S4 never decide card counts; they only execute or enforce them.

---

## 1. Scope and Boundaries

### 1.1 What Allocation DOES (FINAL ONLY)

Allocation produces **group-level quotas for FINAL generation**.

* **Input:** `groups.csv` (frozen) + `TOTAL_CARDS` (runtime parameter, FINAL only)
* **Output:** `group_target_cards` per group such that:

  * `sum(group_target_cards) == TOTAL_CARDS`
  * distribution reflects FINAL policies (coverage, weighting, curriculum balance)

### 1.2 What Allocation DOES NOT DO

* It does **not** generate cards
* It does **not** execute S2
* It does **not** perform QA
* It does **not** apply to S0 in any form

---

## 2. 🚫 Explicit Exclusion: Step S0 (Hard Rule)

> **This policy does NOT apply to Step S0.**

The following rules are **binding and non-negotiable**:

* **S0 does NOT compute, distribute, or optimize card counts.**
* **S0 always uses a fixed set-level payload (`q = 12`).**
* **S0 allocation is defined exclusively in `S0_Allocation_Artifact_Spec.md`.**
* Any appearance of FINAL allocation concepts (quota, ratio, weight, importance)
  in S0 context is a **policy violation**.

> **Rationale:**
> S0 exists solely for QA and arm comparison.
> FINAL allocation logic must not leak into S0.

---

## 3. Allocation Outputs (FINAL)

### 3.1 Group-level Targets

Allocation outputs the following FINAL-only artifacts:

* `group_target_cards` (integer = E × 3, where E is entity count)
* Entity-level allocation: 각 엔티티당 **정확히 3장** (S0의 3×4 규칙과 일관성 유지)
* optional explanatory metadata (human-readable)

These outputs are consumed by downstream steps **without reinterpretation**.

**Policy (v2.1):**
- `group_target_cards = (number of entities in group) × 3`
- 각 엔티티에 `cards_for_entity_exact = 3` 할당

---

## 4. Downstream Contract

### 4.1 S1 / S2

* **Must NOT** decide card counts
* **Must NOT** adjust quotas
* **Must ONLY** consume `group_target_cards`

### 4.2 S3

* Enforces quotas (QA gate)
* Must NOT modify counts

---

## 5. Prohibited Patterns (Zero-Tolerance)

The following are **forbidden outside FINAL Allocation**:

* quota calculation in S1/S2/S3/S4
* dynamic adjustment of card counts
* importance/weight-based redistribution
* any “optimization” language in non-FINAL context

Violations require **document correction before Canonical merge**.

---

## 6. Relationship to S0 Allocation (Firewall)

| Dimension          | S0 Allocation          | FINAL Allocation          |
| ------------------ | ---------------------- | ------------------------- |
| Purpose            | QA / arm comparison    | Production / distribution |
| Card count         | Fixed (12)             | Computed                  |
| Decision authority | None                   | Allocation                |
| Artifact           | S0 allocation artifact | FINAL allocation artifact |
| Policy overlap     | ❌ None                 | —                         |

> **S0 allocation is not a reduced version of FINAL allocation.**

---

## 7. Change Control

* This document is **frozen once S0 starts**
* Any modification requires:

  1. Explicit version bump
  2. CP re-validation
  3. Canonical merge record
