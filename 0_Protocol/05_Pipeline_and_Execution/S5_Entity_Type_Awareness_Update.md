# S5 Entity Type Awareness Update

**Status**: Superseded  
**Version**: 1.0  
**Date**: 2025-12-29  
**Superseded By**: S5_Entity_Type_Awareness_Implementation_Report.md (v1.0)  
**Related**: S2_Entity_Level_Error_Handling_Implementation_Report.md (v2.0)

---

## Context

As of 2025-12-29, S2 card generation now includes **entity type detection** and **entity type-aware prompt adaptation** (see `S2_Entity_Level_Error_Handling_Implementation_Report.md`).

### Entity Types (from S2 Implementation)
- **`disease`** (default): Diagnosis-focused entities
- **`sign`**: Imaging pattern/sign entities (e.g., "Double stripe sign", "CT angiogram sign")
- **`overview`**: Conceptual summary entities (e.g., "Overview of lung cancer", "General principles")
- **`qc`**: QC/quality control entities
- **`equipment`**: Equipment/device entities

### Entity Type → exam_focus Mapping (v9 Prompts)

| Entity Type | Valid exam_focus Values | Invalid exam_focus |
|-------------|------------------------|-------------------|
| `disease` | `"diagnosis"` | Others |
| `sign` | `"pattern"`, `"sign"` | `"diagnosis"` |
| `overview` | `"concept"`, `"classification"` | `"diagnosis"` |
| `qc` | `"procedure"`, `"measurement"`, `"principle"` | `"diagnosis"` |
| `equipment` | `"procedure"`, `"principle"`, `"operation"` | `"diagnosis"` |

---

## S5 Validation Updates Required

### Current Gap

S5 validation does NOT currently:
1. ✅ Check if `exam_focus` matches entity type requirements
2. ✅ Validate entity type-specific prompt adherence
3. ✅ Flag mismatches (e.g., sign entity using `exam_focus="diagnosis"`)

### Required Changes

#### 1. Entity Type Detection in S5 Validator

**File**: `3_Code/src/05_s5_validator.py`

**Action**: Add entity type detection function (reuse logic from `01_generate_json.py` or access from S2 metadata if available).

**Options**:
- **Option A**: Reuse `detect_entity_type_for_s2()` from `01_generate_json.py` (if accessible)
- **Option B**: Extract entity type from S2 metadata if it's stored there
- **Option C**: Re-implement detection logic in S5 validator

**Recommendation**: Option B (if entity_type is stored in S2 records) or Option A (if code can be shared).

#### 2. exam_focus Validation Logic

**File**: `3_Code/src/05_s5_validator.py`

**Action**: After S5 LLM validation, add post-processing validation:

```python
def validate_exam_focus_for_entity_type(
    card: Dict[str, Any],
    entity_type: str,
    issues: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Validate that exam_focus matches entity type requirements.
    
    Returns: Updated issues list (may append new issues)
    """
    image_hint = card.get("image_hint", {})
    exam_focus = image_hint.get("exam_focus", "")
    
    # Valid mappings
    valid_mappings = {
        "disease": ["diagnosis"],
        "sign": ["pattern", "sign"],
        "overview": ["concept", "classification"],
        "qc": ["procedure", "measurement", "principle"],
        "equipment": ["procedure", "principle", "operation"],
    }
    
    valid_focuses = valid_mappings.get(entity_type, ["diagnosis"])  # Default to diagnosis
    
    if exam_focus not in valid_focuses:
        issues.append({
            "severity": "minor",
            "type": "entity_type_mismatch",
            "description": f"Entity type '{entity_type}' should use exam_focus in {valid_focuses}, but found '{exam_focus}'",
            "issue_code": "S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH",
            "recommended_fix_target": "S2_SYSTEM",
            "prompt_patch_hint": f"For {entity_type} entities, ensure exam_focus is one of: {', '.join(valid_focuses)}",
        })
    
    return issues
```

#### 3. New Issue Codes

**File**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`

**Action**: Add new issue codes to Section 5 (Issue Code Starter Set):

```markdown
### 5.4 Entity Type Alignment (S2_ENTITY_*)
- `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH`: exam_focus value does not match entity type requirements
  - Example: Sign entity using `exam_focus="diagnosis"` instead of `"pattern"` or `"sign"`
  - Example: QC entity using `exam_focus="diagnosis"` instead of `"procedure"`, `"measurement"`, or `"principle"`
```

#### 4. S5 System Prompt Update (Optional)

**File**: `3_Code/prompt/S5_SYSTEM__v2.md`

**Action**: Add guidance about entity type-aware validation:

```markdown
### Entity Type-Aware Validation (v9+ Prompts)

When evaluating S2 cards, consider entity type:
- **Sign entities**: Should use `exam_focus="pattern"` or `"sign"`, NOT `"diagnosis"`
- **Overview entities**: Should use `exam_focus="concept"` or `"classification"`, NOT `"diagnosis"`
- **QC entities**: Should use `exam_focus="procedure"`, `"measurement"`, or `"principle"`, NOT `"diagnosis"`
- **Equipment entities**: Should use `exam_focus="procedure"`, `"principle"`, or `"operation"`, NOT `"diagnosis"`

If you detect a mismatch, add an issue with `issue_code="S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH"`.
```

**Note**: This is optional if post-processing validation is implemented (recommended approach).

---

## Implementation Plan

### Phase 1: Schema and Issue Code Update
1. ✅ Add `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH` to `S5_Validation_Schema_Canonical.md`
2. ✅ Document entity type → exam_focus mappings

**Timeline**: 30 minutes

### Phase 2: Entity Type Detection in S5
1. Add entity type detection to S5 validator
2. Extract entity type from S2 records or re-implement detection

**Timeline**: 1-2 hours

### Phase 3: exam_focus Validation
1. Add post-processing validation function
2. Integrate into card validation flow
3. Test with sign/overview/QC entities

**Timeline**: 1-2 hours

### Phase 4: Prompt Update (Optional)
1. Update S5_SYSTEM prompt to include entity type guidance
2. Test LLM-based detection vs. post-processing

**Timeline**: 1 hour (optional)

---

## Testing Strategy

### Test Cases

1. **Sign entity with correct exam_focus**:
   - Entity: "Double stripe sign"
   - exam_focus: "pattern"
   - Expected: No issue

2. **Sign entity with incorrect exam_focus**:
   - Entity: "Double stripe sign"
   - exam_focus: "diagnosis"
   - Expected: `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH` issue

3. **Overview entity with correct exam_focus**:
   - Entity: "Overview of lung cancer staging"
   - exam_focus: "classification"
   - Expected: No issue

4. **QC entity with correct exam_focus**:
   - Entity: "Water CT Number"
   - exam_focus: "measurement"
   - Expected: No issue

5. **Disease entity (unchanged behavior)**:
   - Entity: "Osteoid Osteoma"
   - exam_focus: "diagnosis"
   - Expected: No issue (existing behavior)

---

## Files to Modify

### Schema Documentation
- `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`
  - Add `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH` to issue codes

### Code
- `3_Code/src/05_s5_validator.py`
  - Add entity type detection
  - Add exam_focus validation function
  - Integrate into card validation

### Prompts (Optional)
- `3_Code/prompt/S5_SYSTEM__v2.md`
  - Add entity type-aware validation guidance

---

## Benefits

- ✅ S5 validation now aware of entity type requirements
- ✅ Flags prompt adherence issues (entity type vs. exam_focus mismatch)
- ✅ Provides actionable feedback for prompt improvements
- ✅ Maintains backward compatibility (existing behavior unchanged for disease entities)

---

## Notes

- This update assumes S2 v9 prompts are in use (entity type-aware)
- If entity_type is stored in S2 records, prefer extracting from metadata
- Post-processing validation is recommended over LLM-based detection (more reliable)
- Issue severity should be "minor" (not blocking) since this is a prompt adherence issue, not a safety issue

---

## References

- **S2 Implementation**: `0_Protocol/05_Pipeline_and_Execution/S2_Entity_Level_Error_Handling_Implementation_Report.md`
- **S5 Schema**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`
- **S5 System Prompt**: `3_Code/prompt/S5_SYSTEM__v2.md`
- **S2 System Prompt v9**: `3_Code/prompt/S2_SYSTEM__v9.md`

