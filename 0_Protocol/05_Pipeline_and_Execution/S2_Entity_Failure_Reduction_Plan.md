# S2 Entity Failure Reduction Plan

**Status**: Planning  
**Version**: 1.0  
**Date**: 2025-12-29  
**Related**: 
- `S2_Entity_Level_Error_Handling_Implementation_Report.md`
- `Why_S2_Fails_More_Than_S1.md`

---

## Problem Statement

During S2 execution, certain entity types consistently fail to generate cards:

### Observed Failures

1. **Comparison/Differential Entities** (e.g., "Lung Abscess vs Empyema")
   - Pattern: Entity name contains "vs" or comparison keywords
   - Issue: S2 prompts are optimized for single-diagnosis entities, not differential comparisons
   - Q1 requires `exam_focus = "diagnosis"` but comparison entities need different cognitive framing

2. **Standard Disease Entities** (e.g., "Primary Tuberculosis", "Enchondroma", "Simple Bone Cyst", "Intraosseous Lipoma")
   - Pattern: Standard disease names without special patterns
   - Issue: May fail due to:
     - Schema validation errors (card count mismatch, missing fields)
     - Timeout (complex entities requiring more thinking)
     - LLM errors (quota, API issues)

### Root Causes

1. **Prompt Mismatch for Comparison Entities**
   - Current S2 prompts assume single-diagnosis entities
   - "vs" entities require differential diagnosis framing
   - Q1 question format doesn't fit comparison entities well

2. **Schema Validation Strictness**
   - Exact card count requirement (`len(anki_cards) == cards_for_entity_exact`)
   - Missing fields cause hard failures
   - No graceful degradation for partial success

3. **No Special Handling for Complex Entity Names**
   - Entity names with "vs", "and", "or" are treated same as simple names
   - No prompt adaptation for comparison/differential entities

---

## Proposed Solutions

### Phase 1: Enhanced Entity Type Detection for Comparison Entities ✅ **IMMEDIATE**

**Goal**: Detect comparison/differential entities and adapt prompts accordingly.

#### 1.1 Extend `detect_entity_type_for_s2()` Function

**File**: `3_Code/src/01_generate_json.py`

**Changes**:
- Add detection for "comparison" entity type
- Detect "vs", "versus", "and", "or" patterns in entity names
- Map to appropriate `exam_focus` and question framing

**Implementation**:
```python
def detect_entity_type_for_s2(
    entity_name: str,
    visual_type_category: str,
    master_table_row: Optional[Dict] = None
) -> str:
    """
    Detect entity type for S2 prompt adaptation.
    Returns: "disease", "sign", "overview", "qc", "equipment", "comparison"
    """
    name_lower = str(entity_name).lower()

    # Comparison/Differential entities: "vs", "versus", "and", "or"
    comparison_keywords = [" vs ", " versus ", " and ", " or ", " vs. ", " vs "]
    if any(kw in name_lower for kw in comparison_keywords):
        return "comparison"

    # Sign entities: imaging patterns/signs
    sign_keywords = ["sign", "pattern", "finding", "소견", "징후"]
    if any(kw in name_lower for kw in sign_keywords):
        return "sign"

    # Overview entities: conceptual summaries
    overview_keywords = ["overview", "general", "총론", "개요", "원칙", "개념"]
    if any(kw in name_lower for kw in overview_keywords):
        return "overview"

    # QC/Equipment: from visual_type_category
    if visual_type_category == "QC":
        return "qc"
    if visual_type_category == "Equipment":
        return "equipment"

    # Default: disease/diagnosis entity
    return "disease"
```

#### 1.2 Update S2 System Prompt for Comparison Entities

**File**: `3_Code/prompt/S2_SYSTEM__v9.md` (or create v10)

**Add Section**: Q1 Adaptation for Comparison Entities

```markdown
-   **Comparison/Differential** (when Entity Type is "comparison"):
    *   `image_hint.exam_focus`: "diagnosis" (but frame as differential)
    *   Question: "이 영상 소견에서 가장 가능성이 높은 진단은?" or "다음 중 이 영상 소견과 가장 일치하는 진단은?"
    *   Cognitive Level: APPLICATION (differential diagnosis reasoning)
    *   Front: Describe imaging findings that help distinguish between the compared entities.
    *   Options: Include both entities in the comparison as options (e.g., "A. Lung Abscess", "B. Empyema", ...)
    *   Back: Explain key distinguishing features and why the correct answer is more likely.
```

#### 1.3 Update `image_hint.exam_focus` Enum

**File**: `3_Code/prompt/S2_SYSTEM__v9.md`

**Add to enum**: `"differential"` (optional, can use "diagnosis" with comparison framing)

---

### Phase 2: Improved Error Recovery and Retry Strategy ⚠️ **MEDIUM PRIORITY**

**Goal**: Reduce failures from transient errors and schema validation issues.

#### 2.1 Enhanced Retry Logic for Schema Validation

**Current**: 3 attempts with error feedback

**Proposed**: 
- Add entity-specific retry hints for comparison entities
- Detect card count mismatches and provide specific guidance
- Add timeout handling with exponential backoff

#### 2.2 Partial Success Handling (Optional)

**Consideration**: Allow partial card sets if full set generation fails
- **Risk**: May violate card count contracts
- **Benefit**: Better than complete failure
- **Decision**: Keep strict for now, but improve error messages

#### 2.3 Better Error Classification

**Enhance**: `_classify_error_type()` to detect:
- Comparison entity failures (prompt mismatch)
- Schema validation failures (card count, missing fields)
- Timeout failures (complex entities)
- LLM errors (quota, API)

**Use**: Better retry strategies based on error type

---

### Phase 3: Prompt Examples for Comparison Entities ✅ **HIGH PRIORITY**

**Goal**: Provide clear examples in S2_USER_ENTITY prompt.

**File**: `3_Code/prompt/S2_USER_ENTITY__v9.md` (or create v10)

**Add Example**:
```markdown
### Example: Comparison Entity (Entity Type: "comparison")

**Entity**: "Lung Abscess vs Empyema"

**Q1 Card**:
```json
{
  "card_role": "Q1",
  "card_type": "MCQ",
  "front": "다음 CT 영상에서 가장 가능성이 높은 진단은?",
  "options": [
    "Lung Abscess",
    "Empyema",
    "Pneumonia",
    "Pleural effusion",
    "Lung cancer"
  ],
  "correct_index": 0,
  "back": "Answer: Lung Abscess\n\n근거:\n* 내부에 공기-액체 수평면(air-fluid level)이 보임\n* 벽이 두껍고 불규칙함\n* 주변 폐실질에 염증 소견\n\n함정/감별:\n* Empyema는 흉막강 내 위치, 얇은 벽, 주변 폐실질 정상\n* 공기-액체 수평면은 Abscess에서 더 흔함",
  "image_hint": {
    "exam_focus": "diagnosis",
    "modality": "CT",
    "anatomy": "Lung",
    "key_findings": ["air-fluid level", "thick irregular wall", "surrounding inflammation"]
  }
}
```
```

---

### Phase 4: Monitoring and Analysis ⚠️ **ONGOING**

**Goal**: Track failure patterns and identify root causes.

#### 4.1 Enhanced Failure Logging

**Current**: `s2_failure_summary__arm{arm}.jsonl` includes entity_type

**Enhance**: Add failure pattern analysis
- Entity name patterns (vs, and, or)
- Error type breakdown by entity type
- Retry attempt counts
- Timeout occurrences

#### 4.2 Failure Analysis Script

**Enhance**: `3_Code/scripts/analyze_s2_failures.py`
- Group failures by entity type
- Identify patterns (comparison entities, complex names)
- Generate recommendations

---

## Implementation Priority

### Immediate (This Week)
1. ✅ **Phase 1.1**: Extend entity type detection for "comparison"
2. ✅ **Phase 1.2**: Update S2 system prompt for comparison entities
3. ✅ **Phase 3**: Add comparison entity examples to user prompt

### Short-term (Next Week)
4. ⚠️ **Phase 2.1**: Enhanced retry logic
5. ⚠️ **Phase 4.1**: Enhanced failure logging

### Medium-term (Future)
6. ⚠️ **Phase 2.2**: Partial success handling (if needed)
7. ⚠️ **Phase 4.2**: Failure analysis enhancements

---

## Expected Impact

### Comparison Entities
- **Current**: High failure rate (prompt mismatch)
- **Expected**: Reduced failures (prompt adaptation)
- **Target**: <10% failure rate for comparison entities

### Standard Disease Entities
- **Current**: Variable failure rate (schema, timeout, LLM errors)
- **Expected**: Better error recovery (retry logic)
- **Target**: <5% failure rate for standard entities

### Overall
- **Current**: ~5-10% entity failure rate
- **Target**: <3% entity failure rate

---

## Testing Plan

### Test Cases

1. **Comparison Entity Test**
   - Entity: "Lung Abscess vs Empyema"
   - Expected: Successful generation with differential framing
   - Verify: Q1 question asks for differential diagnosis
   - Verify: Options include both entities

2. **Standard Entity Test**
   - Entities: "Primary Tuberculosis", "Enchondroma", "Simple Bone Cyst", "Intraosseous Lipoma"
   - Expected: Successful generation (no special handling needed)
   - Verify: Standard Q1 format

3. **Failure Recovery Test**
   - Simulate schema validation failure
   - Verify: Retry with improved error feedback
   - Verify: Success on retry

---

## Risks and Mitigations

### Risk 1: Comparison Entity Detection False Positives
- **Mitigation**: Use strict keyword matching (" vs " with spaces)
- **Fallback**: Default to "disease" if uncertain

### Risk 2: Prompt Changes Break Existing Entities
- **Mitigation**: Test with existing successful entities
- **Fallback**: Version prompts (v9 → v10) for gradual rollout

### Risk 3: Increased Complexity
- **Mitigation**: Keep detection logic simple and well-documented
- **Fallback**: Maintain backward compatibility

---

## References

- **S2 Entity Error Handling**: `0_Protocol/05_Pipeline_and_Execution/S2_Entity_Level_Error_Handling_Implementation_Report.md`
- **S2 Failure Analysis**: `0_Protocol/03_CardCount_and_Allocation/Design Rationale/Why_S2_Fails_More_Than_S1.md`
- **S2 System Prompt**: `3_Code/prompt/S2_SYSTEM__v9.md`
- **S2 User Prompt**: `3_Code/prompt/S2_USER_ENTITY__v9.md`
- **Entity Type Detection**: `3_Code/src/01_generate_json.py` (line ~3589)

---

## Notes

- Comparison entities are a special case that requires prompt adaptation
- Standard disease entities may fail for various reasons (schema, timeout, LLM errors)
- Focus on prompt adaptation first (Phase 1, 3), then error recovery (Phase 2)
- Monitoring (Phase 4) should be ongoing to identify new patterns

