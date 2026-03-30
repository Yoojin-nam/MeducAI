# S5 Entity Type Validation Feedback Guide

**Status**: Canonical  
**Version**: 1.0  
**Date**: 2025-12-29  
**Related**: 
- `S5_Validation_Schema_Canonical.md` (v1.1, Section 5.3)
- `S2_Entity_Level_Error_Handling_Implementation_Report.md` (v2.0)
- `S5_Prompt_Refinement_Methodology_Canonical.md`

---

## Purpose

This document provides guidance for incorporating **entity type-aware validation** into the S5 feedback and prompt refinement process. It documents the new `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH` issue code and how to handle it in the iterative refinement loop.

---

## Context: Entity Type-Aware S2 Generation (v9 Prompts)

As of 2025-12-29, S2 card generation now supports entity type detection and adaptive prompt usage:

- **Entity Types**: `disease`, `sign`, `overview`, `qc`, `equipment`, `comparison`
- **Entity Type → exam_focus Mapping**: Each entity type has specific valid `exam_focus` values for Q1 cards
- **S2 Prompts**: S2_SYSTEM__v9.md and S2_USER_ENTITY__v9.md handle entity types

---

## New Issue Code: S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH

### Definition

**Issue Code**: `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH`  
**Location**: `S5_Validation_Schema_Canonical.md` Section 5.3  
**Severity**: `minor` (non-blocking, prompt adherence issue)  
**Affected Stage**: `S2`

### Meaning

This issue code flags when a Q1 card's `image_hint.exam_focus` value does not match the entity type requirements.

### Valid Entity Type → exam_focus Mappings

| Entity Type | Valid exam_focus Values | Invalid exam_focus |
|-------------|------------------------|-------------------|
| `disease` | `["diagnosis"]` | Others |
| `sign` | `["pattern", "sign"]` | `"diagnosis"` |
| `overview` | `["concept", "classification"]` | `"diagnosis"` |
| `qc` | `["procedure", "measurement", "principle"]` | `"diagnosis"` |
| `equipment` | `["procedure", "principle", "operation"]` | `"diagnosis"` |
| `comparison` | `["diagnosis"]` (but frame as differential diagnosis) | Others |

**Note**: Only applies to Q1 cards. Q2 cards always use `exam_focus="concept"` (or `"management"`/`"mechanism"`).

### Examples

**Example 1: Sign Entity Using Wrong exam_focus**
```json
{
  "severity": "minor",
  "type": "entity_type_mismatch",
  "description": "Sign entity 'Double stripe sign' uses exam_focus='diagnosis', but sign entities should use 'pattern' or 'sign'",
  "issue_code": "S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH",
  "recommended_fix_target": "S2_SYSTEM",
  "prompt_patch_hint": "For sign entities, ensure exam_focus is 'pattern' or 'sign', not 'diagnosis'",
  "affected_stage": "S2"
}
```

**Example 2: QC Entity Using Wrong exam_focus**
```json
{
  "severity": "minor",
  "type": "entity_type_mismatch",
  "description": "QC entity 'Water CT Number' uses exam_focus='diagnosis', but QC entities should use 'procedure', 'measurement', or 'principle'",
  "issue_code": "S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH",
  "recommended_fix_target": "S2_SYSTEM",
  "prompt_patch_hint": "For QC entities, ensure exam_focus is one of: 'procedure', 'measurement', 'principle'. Do not use 'diagnosis'.",
  "affected_stage": "S2"
}
```

---

## Integration into S5 Feedback Process

### Step 1: S5 Report Analysis

When analyzing `s5_report__arm{arm}.md`, look for:

- **Patch Backlog** section → **Issue Codes** → `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH`
- Count occurrences by entity type
- Identify patterns (e.g., "sign entities consistently use 'diagnosis' instead of 'pattern'")

### Step 2: Prompt Patch Identification

**Target Prompts**:
- `S2_SYSTEM__v9.md`: Entity type detection and adaptation rules
- `S2_USER_ENTITY__v9.md`: Entity type-specific Q1 blueprints

**Common Patch Patterns**:

1. **Sign Entities**:
   - **Problem**: Using `exam_focus="diagnosis"` for sign entities
   - **Patch**: Emphasize in S2_SYSTEM that sign entities must use `exam_focus="pattern"` or `"sign"`
   - **Location**: Q1 requirements section, entity type adaptation rules

2. **QC/Equipment Entities**:
   - **Problem**: Using `exam_focus="diagnosis"` for QC/Equipment entities
   - **Patch**: Clarify that QC/Equipment entities use procedure/measurement/principle focus
   - **Location**: Visual type adaptations section

3. **Overview Entities**:
   - **Problem**: Using `exam_focus="diagnosis"` for overview/conceptual entities
   - **Patch**: Emphasize that overview entities use concept/classification focus
   - **Location**: Entity type adaptation rules

### Step 3: Prompt Patch Creation

Follow the standard prompt refinement process:

1. **Identify Affected Prompt Section**:
   - Locate entity type adaptation rules in `S2_SYSTEM__v9.md`
   - Locate entity type-specific Q1 blueprints in `S2_USER_ENTITY__v9.md`

2. **Add/Strengthen Rules**:
   - Use concrete examples from S5 reports
   - Emphasize entity type → exam_focus mapping
   - Add explicit prohibitions (e.g., "Do NOT use 'diagnosis' for sign entities")

3. **Version Update**:
   - Create `S2_SYSTEM__v10.md` (or next version)
   - Create `S2_USER_ENTITY__v10.md` (or next version)
   - Update `_registry.json`

4. **Patch Hint Template**:
   ```
   For {entity_type} entities, ensure exam_focus is one of: {valid_values}. 
   Do NOT use '{invalid_value}' (reserved for {reserved_for} entities).
   ```

### Step 4: Re-Validation

After applying prompt patches:

1. Re-run S1/S2 generation with new prompts (new dev run_tag)
2. Re-run S5 validation
3. Check for reduction in `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH` issue count
4. Verify entity type-specific exam_focus values are now correct

---

## Patch Backlog Aggregation

### Grouping by Entity Type

When aggregating `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH` issues in the patch backlog:

- **Group by**: `entity_type` (if available) or infer from entity name patterns
- **Count**: Frequency of mismatch per entity type
- **Pattern Detection**: Identify if specific entity types consistently fail

### Example Patch Backlog Entry

```markdown
## Patch Backlog

### S2_SYSTEM (Entity Type Adaptation)

#### S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH (12 occurrences)

**Pattern**: Sign entities using `exam_focus="diagnosis"` instead of `"pattern"` or `"sign"`

**Affected Entity Types**:
- `sign`: 8 occurrences (e.g., "Double stripe sign", "CT angiogram sign")
- `qc`: 3 occurrences (e.g., "Water CT Number", "Noise")
- `overview`: 1 occurrence (e.g., "Overview of lung cancer staging")

**Patch Hints**:
1. For sign entities: Ensure exam_focus is 'pattern' or 'sign', not 'diagnosis'
2. For QC entities: Ensure exam_focus is one of: 'procedure', 'measurement', 'principle'
3. For overview entities: Ensure exam_focus is 'concept' or 'classification'

**Recommended Fix Target**: `S2_SYSTEM`
**Affected Sections**: Entity Type Detection and Adaptation, Q1 requirements
```

---

## Validation Checklist

When reviewing S5 reports for entity type issues:

- [ ] Check for `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH` in Patch Backlog
- [ ] Count occurrences by entity type (if available)
- [ ] Identify patterns (which entity types consistently fail)
- [ ] Review entity type detection logic (if issues are systematic)
- [ ] Create prompt patches targeting specific entity type failures
- [ ] Test patches with re-validation run
- [ ] Verify reduction in mismatch issue count

---

## Related Documents

- **S5 Validation Schema**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md` (Section 5.3)
- **S2 Entity Type Implementation**: `0_Protocol/05_Pipeline_and_Execution/S2_Entity_Level_Error_Handling_Implementation_Report.md`
- **S5 Prompt Refinement Methodology**: `0_Protocol/05_Pipeline_and_Execution/S5_Prompt_Refinement_Methodology_Canonical.md`
- **S5 Entity Type Awareness Update**: `0_Protocol/05_Pipeline_and_Execution/S5_Entity_Type_Awareness_Update.md`

---

## Notes

- This issue code is **non-blocking** (severity: `minor`) since it's a prompt adherence issue, not a clinical safety issue
- Only applies to **Q1 cards** (Q2 cards always use `exam_focus="concept"`)
- Entity type detection may need refinement if mismatches are systematic (see S2 Entity Level Error Handling Implementation Report)
- Schema validation may need updates to accept new `exam_focus` enum values (currently schema may only allow `"diagnosis"` and `"concept"`)

---

## Change Log

- **2025-12-29**: Initial version, documenting `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH` integration into feedback process

