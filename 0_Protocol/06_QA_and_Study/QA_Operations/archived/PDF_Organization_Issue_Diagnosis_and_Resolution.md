# PDF Organization Issue: Diagnosis and Resolution

**Status:** Diagnostic Report  
**Date:** 2025-12-22  
**Issue:** 36 PDFs missing from reviewer organization  
**Run Tag:** S0_QA_final_time

---

## 1. Executive Summary

### Current Status
- ✅ **180 PDFs successfully organized** into 18 reviewer folders
- ❌ **36 PDFs missing** (expected: 216, actual: 180)
- 📍 **Output location:** `6_Distributions/QA_Packets/by_reviewer_name/`

### Problem Statement
The `organize_pdfs_by_reviewer_name.py` script failed to locate 36 PDFs during organization. Analysis reveals a **mapping conflict** between `selected_18_groups.json` (authoritative for S0) and `groups_canonical.csv` (contains all 312 groups).

---

## 2. Actual Problem Investigation

### 2.1 Script Output Analysis

The script reported these missing PDFs:
```
⚠️  36 assignments with missing PDF files:
    rev_001 Q10: grp_c1a8dcbd3b armF
    rev_001 Q11: grp_bbeab54ed1 armC
    rev_001 Q12: grp_bbeab54ed1 armD
    ...
```

**Key Observation:**
- These group_ids (`grp_c1a8dcbd3b`, `grp_bbeab54ed1`, `grp_cbcba66e24`) are **NOT** in `selected_18_groups.json`
- They **DO** exist in `groups_canonical.csv`
- This suggests the script used **Method 4** (groups_canonical) instead of **Method 1** (selected_18_groups.json)

### 2.2 Why This Shouldn't Happen

**Expected Behavior:**
- All placeholders (`group_01` through `group_18`) should be found in `selected_18_groups.json`
- Method 1 should succeed for all 216 assignments
- Method 4 should never be used

**Possible Causes:**
1. **Script bug:** Method 1 result is being overwritten by Method 4
2. **Data issue:** `selected_18_groups.json` is missing some placeholders
3. **Logic error:** Method 4 is executed even when Method 1 succeeds

### 2.3 Verification Results

**Verification Completed:**
1. ✅ `selected_18_groups.json` contains all 18 placeholders (group_01 through group_18)
2. ✅ All placeholders map to correct group_ids
3. ❌ **Script is using wrong group_ids** - Method 4 is incorrectly overriding Method 1

**Example of the Problem:**
- `rev_001 Q11`: placeholder `group_18` → should map to `grp_6fc675936f` (Method 1)
- Script reported: `grp_bbeab54ed1` (Method 4 result - WRONG)
- `grp_bbeab54ed1` has group_key `lung_bronchus__radiologic_anatomy` (NOT in selected_18_groups)
- `grp_6fc675936f` has group_key `aorta_branch_vasculature__diagnostic_imaging` (CORRECT - group_18)

**Root Cause Confirmed:** Script logic allows Method 4 to override Method 1 result.

---

## 3. Root Cause Analysis

### 3.1 Data Source Hierarchy

**Authoritative Sources (Priority Order):**
1. **`selected_18_groups.json`** (S0-specific, 18 groups)
   - Location: `2_Data/metadata/generated/S0_QA_final_time/selected_18_groups.json`
   - Purpose: Defines the 18 groups selected for S0 QA
   - Format: `group_01` → `grp_xxx` mapping

2. **`groups_canonical.csv`** (All groups, 312 entries)
   - Location: `2_Data/metadata/groups_canonical.csv`
   - Purpose: Complete curriculum group registry
   - Format: `group_id` → `group_key` mapping

### 3.2 Script Logic Flow

The `organize_pdfs_by_reviewer_name.py` script uses **4 methods** to resolve placeholder → group_id:

```python
# Method 1: selected_18_groups.json (PREFERRED)
if placeholder_group_id in placeholder_to_id:
    actual_group_id = placeholder_to_id[placeholder_group_id]

# Method 2: Extract from set_id
# ...

# Method 3: Already a real group_id
# ...

# Method 4: groups_canonical.csv (FALLBACK)
if not actual_group_id:
    group_key = placeholder_to_key[placeholder_group_id]
    for gid, gkey in groups_canonical.items():
        if gkey == group_key:
            actual_group_id = gid  # ← PROBLEM: May select wrong group_id
            break
```

### 3.3 The Problem

**Issue:** Method 4 can select **incorrect group_id** when:
- `selected_18_groups.json` has `group_16` → `grp_1ef3e276b7`
- `groups_canonical.csv` has multiple group_ids with same `group_key`
- Script finds first match in `groups_canonical.csv`, which may be different from `selected_18_groups.json`

**Example Conflict:**
- `group_16` in `selected_18_groups.json`: `grp_1ef3e276b7` (bone_soft_tissue__diagnostic_imaging__trauma)
- `groups_canonical.csv` may have: `grp_c1a8dcbd3b` (urinary_system__normal_anatomy_variations) with same or similar key
- Script selects wrong one → PDF not found

### 3.4 Why Method 1 Should Work But Doesn't

**Expected Behavior:**
- Method 1 should find all 18 groups from `selected_18_groups.json`
- All PDFs should exist (18 groups × 6 arms = 108 PDFs)
- All assignments should map correctly

**Actual Behavior:**
- Method 1 works correctly
- But script reports missing PDFs with group_ids like `grp_c1a8dcbd3b`, `grp_bbeab54ed1`, `grp_cbcba66e24`
- These group_ids are **NOT in selected_18_groups.json**

**Conclusion:** Script is using Method 4 incorrectly, or there's a bug in the logic flow.

---

## 4. Detailed Diagnosis

### 4.1 Missing PDF Analysis

**Reported Missing Group IDs:**
- `grp_c1a8dcbd3b` (urinary_system__normal_anatomy_variations)
- `grp_bbeab54ed1` (lung_bronchus__radiologic_anatomy)
- `grp_cbcba66e24` (specific_objectives__diagnostic_imaging__benign_breast_disease)

**Verification:**
- ❌ Not in `selected_18_groups.json`
- ✅ Exist in `groups_canonical.csv`
- ❌ PDFs do not exist (correctly, since these groups weren't selected for S0)

### 4.2 Assignment Map Verification

**Total Assignments:** 216 (18 reviewers × 12 assignments each)

**Assignment Format:**
```csv
reviewer_id,local_qid,set_id,group_id,arm_id,role
rev_001,Q01,set_group_02_C,group_02,C,resident
```

**All assignments use placeholders:** `group_01` through `group_18`

### 4.3 PDF File Verification

**Existing PDFs:** 108 files
- Format: `SET_grp_{group_hash}_arm{arm}_S0_QA_final_time.pdf`
- Coverage: 18 groups × 6 arms = 108 PDFs ✅

**All PDFs correspond to groups in `selected_18_groups.json`** ✅

---

## 5. Root Cause: Script Logic Bug

### 5.1 The Bug

The script's Method 4 fallback is **incorrectly triggered** or **incorrectly implemented**:

1. **Scenario A:** Method 1 fails silently (shouldn't happen)
2. **Scenario B:** Method 4 is used even when Method 1 succeeds (logic error)
3. **Scenario C:** Method 4 selects wrong group_id due to multiple matches

### 5.2 Evidence

When tracing `rev_001 Q10`:
- Placeholder: `group_16`
- Method 1 result: `grp_1ef3e276b7` ✅
- PDF exists: `SET_grp_1ef3e276b7_armF_S0_QA_final_time.pdf` ✅
- But script reports: `grp_c1a8dcbd3b armF` ❌

**This indicates:** Script is not using Method 1 result correctly, or Method 4 is overriding it.

---

## 6. Resolution Options (Principle-Based)

### Option 1: Fix Script Logic (RECOMMENDED)

**Principle:** `selected_18_groups.json` is the authoritative source for S0. Method 4 should never override Method 1.

**Changes Required:**
1. Ensure Method 1 result is **never overridden** by Method 4
2. Add validation: If Method 1 succeeds, skip Method 4 entirely
3. Add error logging when Method 4 selects different group_id than Method 1

**Code Fix:**
```python
# Method 1: Use selected_18_groups.json mapping (PREFERRED - has group_id directly)
actual_group_id = None
if placeholder_group_id in placeholder_to_id:
    actual_group_id = placeholder_to_id[placeholder_group_id]

# CRITICAL: If Method 1 succeeded, DO NOT use Method 4
if actual_group_id:
    # Use Method 1 result - do not fallback to Method 4
    pass
else:
    # Only use Method 4 if Method 1 failed
    # Method 4: Try to get group_id from groups_canonical using group_key
    # ...
```

### Option 2: Remove Method 4 for S0

**Principle:** S0 should only use `selected_18_groups.json`. `groups_canonical.csv` is for FINAL runs.

**Changes Required:**
1. Add parameter: `--s0_mode` flag
2. When `--s0_mode` is set, skip Method 4 entirely
3. Fail-fast if Method 1 doesn't find mapping

### Option 3: Generate Missing PDFs

**Principle:** If assignments require these PDFs, generate them.

**Analysis Required:**
- Verify if `grp_c1a8dcbd3b`, `grp_bbeab54ed1`, `grp_cbcba66e24` are actually needed
- Check if these are in `selected_18_groups.json` but with different placeholders
- If not in selected_18_groups, these assignments are **incorrect**

**Action:**
- If assignments are wrong → Fix `assignment_map.csv`
- If groups are wrong → Regenerate `selected_18_groups.json`
- If PDFs are missing → Generate them

---

## 7. Recommended Resolution Plan

### Phase 1: Immediate Fix (Script Logic)

**Priority:** HIGH  
**Effort:** Low (30 minutes)

1. **Fix Method 4 logic** to never override Method 1
2. **Add validation** to detect conflicts
3. **Re-run organization** script

**Expected Outcome:** All 216 PDFs organized correctly

### Phase 2: Verification

**Priority:** HIGH  
**Effort:** Low (15 minutes)

1. Verify all 216 assignments map correctly
2. Verify all PDFs are found
3. Verify reviewer folders contain 12 PDFs each

### Phase 3: Long-term Improvement

**Priority:** MEDIUM  
**Effort:** Medium (2 hours)

1. Add `--s0_mode` flag to script
2. Add comprehensive validation
3. Add unit tests for mapping logic
4. Document data source hierarchy

---

## 8. Implementation Steps

### Step 1: Fix Script

**File:** `3_Code/src/tools/qa/organize_pdfs_by_reviewer_name.py`

**Change:** Ensure Method 1 result is never overridden

```python
# Around line 299-330
actual_group_id = None

# Method 1: Use selected_18_groups.json mapping (PREFERRED)
if placeholder_group_id in placeholder_to_id:
    actual_group_id = placeholder_to_id[placeholder_group_id]

# Method 2: Extract from set_id if available
if not actual_group_id and set_id:
    # ... existing code ...

# Method 3: If placeholder_group_id is already a real group_id
if not actual_group_id and placeholder_group_id.startswith("grp_"):
    actual_group_id = placeholder_group_id

# Method 4: ONLY if Method 1-3 all failed
if not actual_group_id:
    group_key = None
    if placeholder_group_id in placeholder_to_key:
        group_key = placeholder_to_key[placeholder_group_id]
    
    if group_key:
        # Find group_id from groups_canonical by group_key
        # BUT: Validate it matches selected_18_groups if available
        for gid, gkey in groups_canonical.items():
            if gkey == group_key:
                # VALIDATION: Check if this conflicts with selected_18_groups
                if placeholder_group_id in placeholder_to_id:
                    expected_gid = placeholder_to_id[placeholder_group_id]
                    if gid != expected_gid:
                        print(f"WARNING: Method 4 conflict for {placeholder_group_id}: "
                              f"expected {expected_gid}, found {gid}")
                        # Use Method 1 result instead
                        actual_group_id = expected_gid
                        break
                actual_group_id = gid
                break
```

### Step 2: Re-run Organization

```bash
python3 3_Code/src/tools/qa/organize_pdfs_by_reviewer_name.py \
  --base_dir . \
  --pdf_source_dir 6_Distributions/QA_Packets/S0_final_time \
  --assignment_map 0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv \
  --reviewer_master 1_Secure_Participant_Info/reviewer_master.csv \
  --groups_canonical 2_Data/metadata/groups_canonical.csv \
  --run_tag S0_QA_final_time
```

### Step 3: Verify Results

```bash
# Count PDFs per reviewer
find 6_Distributions/QA_Packets/by_reviewer_name -name "*.pdf" | wc -l
# Expected: 216

# Verify each reviewer has 12 PDFs
for reviewer in 6_Distributions/QA_Packets/by_reviewer_name/*/; do
    count=$(ls "$reviewer"/*.pdf 2>/dev/null | wc -l)
    if [ "$count" -ne 12 ]; then
        echo "⚠️  $(basename "$reviewer"): $count PDFs"
    fi
done
```

---

## 9. Data Source Authority (Canonical)

### For S0 QA Runs

**Authoritative Source:** `selected_18_groups.json`
- **Location:** `2_Data/metadata/generated/{RUN_TAG}/selected_18_groups.json`
- **Purpose:** Defines groups selected for S0
- **Format:** Array of 18 group objects with `group_id` and `group_key`
- **Mapping:** `group_01` → `grp_xxx` (deterministic, by array index)

**Fallback Source:** `groups_canonical.csv` (use with caution)
- **Location:** `2_Data/metadata/groups_canonical.csv`
- **Purpose:** Complete curriculum registry (312 groups)
- **Warning:** May contain groups NOT selected for S0
- **Usage:** Only when `selected_18_groups.json` is unavailable

### For FINAL Runs

**Authoritative Source:** `groups_canonical.csv`
- All groups are available
- No selection needed

---

## 10. Validation Checklist

After implementing the fix, verify:

- [ ] All 216 assignments map to correct group_ids
- [ ] All group_ids are from `selected_18_groups.json`
- [ ] All 108 PDFs are found and organized
- [ ] Each reviewer folder contains exactly 12 PDFs
- [ ] PDF filenames match expected pattern
- [ ] No warnings about Method 4 conflicts

---

## 11. Prevention Measures

### 11.1 Code-Level

1. **Add validation** in script to detect Method 1/4 conflicts
2. **Add unit tests** for mapping logic
3. **Add logging** to track which method was used

### 11.2 Process-Level

1. **Document** data source hierarchy in script docstring
2. **Validate** `assignment_map.csv` against `selected_18_groups.json` before running
3. **Pre-flight check:** Verify all required PDFs exist before organization

### 11.3 Documentation

1. Update script documentation with data source priority
2. Add troubleshooting guide for missing PDFs
3. Document when to use `--s0_mode` vs normal mode

---

## 12. Appendix: File Locations

### Input Files
- `assignment_map.csv`: `0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv`
- `reviewer_master.csv`: `1_Secure_Participant_Info/reviewer_master.csv`
- `groups_canonical.csv`: `2_Data/metadata/groups_canonical.csv`
- `selected_18_groups.json`: `2_Data/metadata/generated/S0_QA_final_time/selected_18_groups.json`

### Source PDFs
- `6_Distributions/QA_Packets/S0_final_time/`

### Output
- `6_Distributions/QA_Packets/by_reviewer_name/`

---

## 13. Next Steps

1. **Immediate:** Fix script logic (Option 1)
2. **Short-term:** Re-run organization and verify
3. **Long-term:** Add `--s0_mode` flag and comprehensive validation

---

**Document Status:** Ready for implementation  
**Last Updated:** 2025-12-22

