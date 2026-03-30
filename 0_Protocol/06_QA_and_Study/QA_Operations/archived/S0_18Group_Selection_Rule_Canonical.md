# S0 18-Group Selection Rule (Canonical)

**Status:** Canonical  
**Version:** 1.0  
**Date:** 2025-12-20  
**Applies to:** Step S0 QA (18 groups × 6 arms = 108 sets)  
**Supersedes:** None

---

## 0. Purpose

This document defines the **canonical rule** for selecting 18 groups for S0 QA evaluation. The rule ensures:
- All specialties are represented (minimum 1 group per specialty)
- Weight-based selection preserves curricular representativeness
- Simple and deterministic selection process

**Note:** The requirement "≥6 subspecialties" is automatically satisfied since all 11 specialties are included (11 > 6).

---

## 1. Selection Rule (Two-Stage)

### 1.1 Stage 1: Minimum Coverage Guarantee

**Rule:** Each specialty must contribute **at least 1 group**.

**Procedure:**
1. For each specialty, select the group with the **highest weight** (from EDA weight data)
2. If multiple groups have the same weight, use deterministic tie-breaking (seed-based random selection)

**Output:** 11 groups (one per specialty)

---

### 1.2 Stage 2: Weight-Based Selection

**Rule:** Select the remaining 7 groups by **weight (highest first)**.

**Procedure:**
1. **Exclude** groups already selected in Stage 1
2. Sort remaining groups by weight (descending)
3. Select the **top 7 groups** by weight

**Output:** 7 groups

**Rationale:** Simple and straightforward. High-weight groups are educationally more important, so selecting the highest-weight remaining groups preserves curricular representativeness.

---

## 2. Final Output

**Total:** 18 groups

**Constraints satisfied:**
- ✅ All 11 specialties included (minimum 1 group each)
- ✅ ≥6 subspecialties (automatically satisfied: 11 > 6)
- ✅ Weight-based selection (high-weight groups prioritized)
- ✅ Deterministic selection (seed-based for tie-breaking)

---

## 3. Weight Data Source

**Source:** `2_Data/eda/EDA_1780_Decision/tables/groups_weight_expected_cards.csv`

## 3.1 Group Universe Input (Operational Rule)

- **S0 interpretability rule:** S0 selection/interpretation MAY use the **legacy frozen group universe** snapshot
  under `2_Data/metadata/legacy/` when S0 was historically generated on that snapshot.
- **Default pipeline rule:** Ongoing S1–S4/FINAL runs MUST consume the operational SSOT
  `2_Data/metadata/groups_canonical.csv` (which may be promoted from `groups_canonical_v2.csv`).

**Required fields:**
- `_group_key`: Group identifier (matches `groups_canonical.csv`)
- `group_weight_sum`: Total weight for the group

**Matching:**
- Groups in `groups_canonical.csv` are matched with weight data by `group_key`
- Groups without weight data are excluded from selection

---

## 4. Implementation Notes

### 4.1 Deterministic Selection

- Use fixed random seed (default: 42) for reproducibility
- Same seed must produce identical selection

### 4.2 Tie-Breaking

- When multiple groups have identical weight, use seed-based random selection
- Within same specialty in Stage 1, select the group with highest weight (deterministic)

### 4.3 Edge Cases

- If a specialty has no groups with weight data, skip that specialty (should not occur in normal operation)
- If total groups with weight data < 18, select all available groups and log warning

---

## 5. Validation Checklist

After selection, verify:

- [ ] Total selected groups = 18
- [ ] All 11 specialties represented (≥1 group each)
- [ ] Selection is deterministic (same seed → same result)
- [ ] Weight data source is documented

---

## 6. Example Output

```
Stage 1: Minimum Coverage (11 groups)
  - abdominal_rad: 1 group (highest weight in specialty)
  - breast_rad: 1 group (highest weight in specialty)
  - cv_rad: 1 group (highest weight in specialty)
  - gu_rad: 1 group (highest weight in specialty)
  - ir: 1 group (highest weight in specialty)
  - msk_rad: 1 group (highest weight in specialty)
  - neuro_hn_rad: 1 group (highest weight in specialty)
  - nuclear_medicine: 1 group (highest weight in specialty)
  - ped_rad: 1 group (highest weight in specialty)
  - phys_qc_medinfo: 1 group (highest weight in specialty)
  - thoracic_rad: 1 group (highest weight in specialty)

Stage 2: Weight-Based Selection from Remaining Groups (7 groups)
  - Exclude 11 groups already selected in Stage 1
  - Remaining groups: 301 groups
  - Sort remaining groups by weight (descending)
  - Select top 7 groups by weight

Total: 18 groups (11 + 7 = 18)
```

---

## 7. Relationship to QA Framework v2.0

This rule implements the **18-Group Selection Rule** specified in:
- `0_Protocol/06_QA_and_Study/QA_Framework.md` (Section 2.3.3)

### 7.1 Original QA Framework Rule

**Original specification:**
- Weight-stratified sampling only
- Strata allocation: **6 / 5 / 4 / 3** (Top 20% → Tail)
- Total: 18 groups (6+5+4+3=18)
- No minimum coverage guarantee per specialty

### 7.2 Modified Rule (This Document)

**Key differences:**
- **Stage 1:** Minimum coverage guarantee (all 11 specialties, 1 group each)
- **Stage 2:** Simple weight-based selection (top 7 by weight from remaining groups)
- **Total:** 18 groups (11+7=18)

**Rationale:** 
- Ensures all specialties are represented (including low-weight specialties like nuclear_medicine)
- Maintains weight-based representativeness (high-weight groups prioritized)
- Simpler implementation while preserving educational importance

---

## 8. Status

**This document is Canonical and Frozen.**

Any changes to the selection rule must:
1. Update this document with version increment
2. Update implementation code
3. Document rationale for change
4. Verify selection results match new rule

---

**End of Document**

