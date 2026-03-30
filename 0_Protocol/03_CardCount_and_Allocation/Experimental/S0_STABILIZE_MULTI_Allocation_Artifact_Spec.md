# S0_STABILIZE_MULTI Allocation Artifact Specification

**Status:** **EXPERIMENTAL** (Non‑Canonical, Draft)  
**Version:** 0.1  
**Applies to:** Stabilization / Pilot runs only (NOT Canonical S0)  
**Last Updated:** 2025‑12‑18  
**Purpose:** Execution-level stabilization of Step02 (S2) by distributing fixed payload across multiple entities

**⚠️ IMPORTANT:** This document is **EXPERIMENTAL** and **NOT Canonical**. It must not be used for arm-fairness inference or final QA reporting. The canonical S0 allocation is defined in `S0_Allocation/S0_Allocation_Artifact_Spec.md` (v2.1).

---

## 0. Purpose and Scope

This document defines the **allocation artifact schema** for the `S0_STABILIZE_MULTI` mode.

The purpose of this mode is **execution‑level stabilization of Step02 (S2)** by avoiding large single‑batch generation (e.g., 12 cards from a single entity) and instead distributing the same fixed payload across multiple entities.

**Key intent**:
- Preserve **set‑level payload = 12 cards** (unchanged)
- Reduce S2 failure probability by generating **3 cards per entity × 4 entities**
- Maintain strict **decision authority separation**: allocation decides counts; S2 executes exactly as instructed

This mode is **explicitly not Canonical S0** and must not be used for arm‑fairness inference or final QA reporting.

---

## 1. Design Principles (Invariant)

The following principles are non‑negotiable within this mode:

1. **Set‑level payload is fixed**
   - Total cards per (group, arm) set is exactly **12**

2. **Entity‑level execution granularity**
   - Exactly **4 entities** are selected
   - Each entity produces exactly **3 cards**

3. **Deterministic entity selection**
   - No random sampling
   - Selection must be reproducible from S1 output alone

4. **Fail‑fast on insufficiency**
   - If fewer than 4 entities are available from S1, the set **HARD FAILS**

5. **S2 remains a pure execution engine**
   - S2 must not infer, adjust, or optimize card counts
   - `cards_for_entity_exact` is authoritative

---

## 2. File Location and Naming

### 2.1 File Name

```
allocation_s0_stabilize_multi__group_{GROUP_ID}__arm_{ARM}.json
```

### 2.2 Storage Location

```
2_Data/metadata/generated/{RUN_TAG}/allocation/
```

This mirrors Canonical S0 paths for auditability while remaining mode‑distinct.

---

## 3. Top‑Level Schema

```json
{
  "allocation_version": "S0_STABILIZE_MULTI-Allocation-v0.1",
  "mode": "S0_STABILIZE_MULTI",
  "run_tag": "S0_STABILIZE_MULTI_YYYYMMDD_HHMMSS",
  "group_id": "G0001",
  "arm": "A",

  "set_target_cards": 12,

  "payload_policy": {
    "entities_selected_exact": 4,
    "cards_per_entity_exact": 3,
    "card_type_plan_per_entity": ["SHORT_ANSWER", "MCQ", "CLOZE"],
    "order_within_entity": "FIXED",
    "insufficient_entities_behavior": "HARD_FAIL"
  },

  "entities_from_s1": [],

  "entity_selection_policy": {
    "source": "S1_OUTPUT",
    "selection_rule": "FIRST_K_AFTER_DETERMINISTIC_SORT",
    "k": 4,
    "deterministic_sort_key": "entity_id_then_entity_name",
    "fallbacks": "DERIVE_ENTITY_ID_IF_MISSING",
    "insufficient_entities_behavior": "HARD_FAIL"
  },

  "entity_allocations": [],

  "allocation_checksum": {
    "sum_cards": 12,
    "entity_count_used": 4
  }
}
```

---

## 4. `entities_from_s1` Definition

This field records **all entities observed from S1 output**, prior to selection.

Each entry must include a stable identifier.

```json
{
  "entity_name": "Pulmonary cavity",
  "entity_id": "E003",
  "entity_id_source": "S1_EXPLICIT"
}
```

### 4.1 Entity ID Resolution Rules

Resolution order:
1. Use explicit ID from S1 if present (`entity_id`, `entity_key`, etc.)
2. Otherwise derive deterministically:

```
entity_id = "DERIVED:" + sha1(normalize(entity_name))[:12]
```

Normalization must be stable and documented (strip, collapse whitespace, lowercase for ASCII).

---

## 5. Entity Selection Policy

Entities are selected deterministically as follows:

1. Sort `entities_from_s1` by:
   - Primary: `entity_id` (lexicographic)
   - Secondary: `entity_name` (lexicographic)
2. Select the **first 4 entities**
3. If fewer than 4 entities exist → **HARD FAIL**

No randomness, weighting, or semantic prioritization is permitted in this mode.

---

## 6. `entity_allocations` Definition

Each selected entity produces exactly **3 cards**.

```json
{
  "entity_slot_id": 1,
  "entity_name": "Pulmonary cavity",
  "entity_id": "E003",
  "cards_for_entity_exact": 3,
  "card_type_plan": [
    {"card_slot_id": 1, "card_type": "SHORT_ANSWER"},
    {"card_slot_id": 2, "card_type": "MCQ"},
    {"card_slot_id": 3, "card_type": "CLOZE"}
  ]
}
```

### 6.1 Constraints

- `len(entity_allocations) == 4`
- For every entity:
  - `cards_for_entity_exact == 3`
  - `card_type_plan` length == 3
  - Card types exactly match the declared order

---

## 7. Integrity Checks (Fail‑Fast)

The following conditions MUST be verified before Step02 execution:

- `set_target_cards == 12`
- `Σ(cards_for_entity_exact) == 12`
- `allocation_checksum.sum_cards == 12`
- `allocation_checksum.entity_count_used == 4`
- Mode must equal `S0_STABILIZE_MULTI`

Any violation results in immediate abort.

---

## 8. Relationship to Canonical S0

- This specification **does not modify or supersede Canonical S0**
- Canonical S0 continues to enforce:
  - Single representative entity
  - Single‑batch payload execution

`S0_STABILIZE_MULTI` exists solely to:
- Stabilize execution
- Diagnose S2 failure modes
- Support prompt and runner iteration

Results generated under this mode must be clearly labeled and excluded from arm‑fairness claims.

---

## 9. Summary Statement

`S0_STABILIZE_MULTI` preserves the **semantic meaning of a 12‑card set** while changing only the **execution topology**.

It trades single‑entity depth for multi‑entity breadth to reduce large‑batch generation risk, without delegating any decision authority to the LLM.

