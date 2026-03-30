# S2 Entity-Level Error Handling Improvement Plan

**Status**: Superseded  
**Version**: 1.0  
**Date**: 2025-12-29  
**Supersedes**: None  
**Superseded By**: S2_Entity_Level_Error_Handling_Implementation_Report.md (v2.0)  

---

## Problem Statement

During FINAL mode S2 card generation, when an entity fails to generate (e.g., due to schema validation errors, timeout, or LLM errors), the current implementation:

1. **Continues to the next entity** (correct behavior) - `if not s2_json: continue` in `process_single_group`
2. **However, the group record is still written** even if all entities failed, potentially creating incomplete or empty group records
3. **No explicit logging** of which entities failed and why, making debugging difficult
4. **QC/Equipment groups may have higher failure rates** if prompts are pathology-focused

## Current Behavior Analysis

### Code Flow (from `01_generate_json.py`)

```python
# Sequential processing (line 4613-4665)
for idx, tgt in enumerate(s2_targets, 1):
    s2_json, err2, rt_s2_dict = process_single_entity(...)
    
    if not s2_json:
        # Error already logged in process_single_entity
        continue  # ✅ Correct: continues to next entity
    
    entities_out.append(s2_json)

# Record assembly (line 4667-4751)
record = {
    "metadata": {...},
    "curriculum_content": {
        "entities": entities_out,  # May be empty if all entities failed
    },
}
```

### Key Observations

1. **Entity-level failures are handled gracefully** (continue to next entity)
2. **Group record is always written** even if `entities_out` is empty
3. **No explicit tracking** of failed entities per group
4. **Schema retry logs exist** (`llm_schema_retry_log.jsonl`) but may not capture all failure types

## Root Causes for QC/Equipment Entity Failures

### Potential Issues

1. **Prompt Pathology Bias**: S2 prompts may be optimized for pathology entities, making QC/Equipment entities harder to generate
   - Example: Q1 prompt emphasizes "diagnostic reasoning" and "imaging findings to diagnostic concepts"
   - QC entities may not fit this pattern (e.g., "Water CT Number", "Noise", "Uniformity")

2. **Cognitive Level Mismatch**: Q1 is designed for "APPLICATION (Bloom's Taxonomy Level 3)" with diagnostic reasoning
   - QC/Equipment concepts may require different cognitive approaches (procedural knowledge, technical specifications)

3. **Image Hint Requirements**: Q1 requires `image_hint.exam_focus = "diagnosis"`
   - QC entities may not have a clear "diagnosis" focus (e.g., phantom test procedures)

4. **Master Table Context**: If S1 master table lacks sufficient detail for QC/Equipment entities, S2 may struggle to generate appropriate content

## Proposed Improvements

### Option 1: Enhanced Error Logging and Reporting (Recommended)

**Goal**: Make failures visible and actionable without changing core logic.

**Implementation**:

1. **Track failed entities per group**:
   ```python
   failed_entities = []
   for idx, tgt in enumerate(s2_targets, 1):
       s2_json, err2, rt_s2_dict = process_single_entity(...)
       
       if not s2_json:
           failed_entities.append({
               "entity_name": str(tgt.entity_name),
               "entity_id": tgt.entity_id,
               "error": err2,
               "index": idx,
           })
           continue
       
       entities_out.append(s2_json)
   ```

2. **Add failure metadata to group record**:
   ```python
   record["metadata"]["s2_generation"] = {
       "total_entities": len(s2_targets),
       "successful_entities": len(entities_out),
       "failed_entities": len(failed_entities),
       "failed_entity_details": failed_entities,  # Only if failures > 0
   }
   ```

3. **Post-generation failure report**:
   - Create a summary JSONL file: `s2_failure_summary__arm{arm}.jsonl`
   - Include: group_id, entity_name, error_type, error_message, retry_count, visual_type_category

**Benefits**:
- No breaking changes to existing logic
- Makes failures visible for debugging
- Enables targeted re-runs for failed entities
- Helps identify patterns (e.g., QC groups have higher failure rates)

### Option 2: Visual Type-Aware Prompt Adaptation

**Goal**: Adjust Q1/Q2 prompts based on visual_type_category.

**Implementation**:

1. **Detect visual type from S1**:
   ```python
   visual_type = s1_json.get("visual_type_category", "General")
   ```

2. **Adapt prompt instructions for QC/Equipment**:
   - If `visual_type == "QC"`:
     - Q1: Focus on "test procedure" or "measurement interpretation" rather than "diagnostic reasoning"
     - Q1 image_hint.exam_focus: Allow "procedure" or "measurement" instead of requiring "diagnosis"
   - If `visual_type == "Equipment"`:
     - Q1: Focus on "equipment operation" or "principle application"
     - Q1 image_hint.exam_focus: Allow "principle" or "operation"

3. **Update S2_SYSTEM prompt**:
   - Add section: "Visual Type Adaptations"
   - Explicitly handle QC, Equipment, Physics, General categories

**Benefits**:
- Reduces failure rate for non-pathology entities
- Maintains cognitive alignment for each entity type
- Improves overall generation quality

**Risks**:
- Requires prompt version update and testing
- May need S2_SYSTEM__v9.md

### Option 3: Fallback Generation Strategy

**Goal**: Attempt simplified generation if standard generation fails.

**Implementation**:

1. **First attempt**: Standard generation with full prompts
2. **On failure**: Retry with simplified prompt (e.g., Q2-only for QC entities)
3. **Log both attempts** in retry metadata

**Benefits**:
- Improves coverage (fewer missing entities)
- Degrades gracefully

**Risks**:
- May produce lower-quality cards
- Increases token usage
- Complexity in tracking "original" vs "fallback" cards

### Option 4: Entity Pre-filtering (Not Recommended)

**Goal**: Skip entities that are likely to fail (e.g., based on entity name patterns).

**Drawbacks**:
- May skip valid entities
- Reduces coverage
- Doesn't solve root cause

## Recommended Action Plan

### Phase 1: Immediate (Error Visibility)
1. ✅ Implement Option 1 (Enhanced Error Logging)
   - Add `failed_entities` tracking in `process_single_group`
   - Add failure metadata to group record
   - Create `s2_failure_summary__arm{arm}.jsonl` report
   - Update `generate_missing_entities_s2_s5.py` to use failure summary

**Timeline**: 1-2 hours

### Phase 2: Short-term (Prompt Improvement)
2. Implement Option 2 (Visual Type-Aware Prompts)
   - Analyze S2_SYSTEM__v8.md for pathology bias
   - Create S2_SYSTEM__v9.md with QC/Equipment adaptations
   - Test on QC/Equipment groups
   - Validate with S5

**Timeline**: 2-3 hours

### Phase 3: Medium-term (Fallback Strategy)
3. Consider Option 3 if failure rates remain high after Phase 2
   - Design simplified prompt templates for QC/Equipment
   - Implement fallback retry logic
   - Add fallback metadata to cards

**Timeline**: 3-4 hours

## Implementation Details for Phase 1

### Code Changes

**File**: `3_Code/src/01_generate_json.py`

**Location**: `process_single_group` function, around line 4613

**Change**:
```python
# Before:
entities_out: List[Dict[str, Any]] = []
for idx, tgt in enumerate(s2_targets, 1):
    ...
    if not s2_json:
        continue
    entities_out.append(s2_json)

# After:
entities_out: List[Dict[str, Any]] = []
failed_entities: List[Dict[str, Any]] = []

for idx, tgt in enumerate(s2_targets, 1):
    ...
    if not s2_json:
        failed_entities.append({
            "entity_name": str(tgt.entity_name),
            "entity_id": tgt.entity_id,
            "error": err2,
            "index": idx,
        })
        continue
    entities_out.append(s2_json)

# Add to record metadata (around line 4683):
record["metadata"]["s2_generation"] = {
    "total_entities": total_entities,
    "successful_entities": len(entities_out),
    "failed_entities": len(failed_entities),
}
if failed_entities:
    record["metadata"]["s2_generation"]["failed_entity_details"] = failed_entities
```

### Output File Format

**File**: `2_Data/metadata/generated/{run_tag}/s2_failure_summary__arm{arm}.jsonl`

**Schema**:
```json
{
  "run_tag": "...",
  "arm": "...",
  "group_id": "...",
  "group_path": "...",
  "visual_type_category": "...",
  "entity_name": "...",
  "entity_id": "...",
  "entity_index": 1,
  "error_type": "schema_validation|timeout|llm_error|other",
  "error_message": "...",
  "retry_count": 3,
  "timestamp": "..."
}
```

## Validation and Testing

### Acceptance Criteria

1. ✅ All entity failures are logged in group record metadata
2. ✅ `s2_failure_summary__arm{arm}.jsonl` is generated for runs with failures
3. ✅ `generate_missing_entities_s2_s5.py` can read failure summary to identify missing entities
4. ✅ No breaking changes to existing successful generation paths

### Test Cases

1. **Normal case**: All entities succeed → no failures logged
2. **Partial failure**: Some entities fail → failures logged, successful entities written
3. **Complete failure**: All entities fail → failures logged, empty group record written (current behavior preserved)
4. **QC group**: Generate S2 for QC group → verify failures are logged appropriately

## References

- `3_Code/src/01_generate_json.py`: `process_single_group` function (line ~3776)
- `3_Code/prompt/S2_SYSTEM__v8.md`: Current S2 system prompt
- `3_Code/scripts/generate_missing_entities_s2_s5.py`: Entity detection script

## Notes

- This plan addresses **error visibility** first, then **root cause mitigation**
- Phase 1 can be implemented immediately without prompt changes
- Phase 2 requires prompt engineering and validation
- Option 3 is optional and should be evaluated after Phase 2 results

