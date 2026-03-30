# S6 Positive Instruction Agent Specification

**Status:** Canonical · Active  
**Applies to:** S6 Positive Instruction Agent  
**Purpose:** Convert S5 validation feedback (prompt_patch_hint) into positive, actionable instructions for image regeneration  
**Last Updated:** 2026-01-15

---

## 0. Overview

The S6 Positive Instruction Agent is a specialized LLM-based component that transforms negative feedback from S5 validation into positive, constructive instructions for S4 image regeneration.

**Key Principle:** S6 acts as a feedback translator, converting "what's wrong" into "what to generate" without adding new medical content.

---

## 1. Agent Role and Scope

### 1.1 Primary Function

Convert S5 validation feedback (`prompt_patch_hint`) into positive instructions that can be used to enhance S3 image specifications for regeneration.

### 1.2 Scope Boundaries

**In Scope:**
- Analyzing S5 `prompt_patch_hint` feedback
- Reviewing original S3 image specifications
- Viewing generated S4 images
- Generating positive, actionable modification instructions
- Producing enhanced S3 specs compatible with S4

**Out of Scope:**
- Adding new medical content or facts
- Changing modality, anatomy, or clinical intent
- Direct image generation (that's S4's role)
- RAG/retrieval operations (to prevent scope creep)

---

## 2. Input Schema

S6 requires three inputs for each regeneration target:

### 2.1 S5 Validation Results

**Source:** `s5_validation__arm{X}.jsonl`

**Relevant Fields:**
```json
{
  "group_id": "grp_xxx",
  "entity_id": "DERIVED_xxx",
  "card_role": "Q1" | "Q2",
  "image_regeneration_trigger_score": 85.0,
  "card_image_validation": {
    "prompt_patch_hint": [
      "Issue 1 description...",
      "Issue 2 description..."
    ]
  }
}
```

**Trigger Condition:**
- `image_regeneration_trigger_score < 80.0` (default threshold)

### 2.2 S3 Original Image Specification

**Source:** `s3_image_spec__arm{X}__original_diagram.jsonl`

**Required Fields:**
```json
{
  "run_tag": "...",
  "group_id": "...",
  "entity_id": "...",
  "card_role": "Q1" | "Q2",
  "spec_kind": "S1_TABLE_VISUAL" | "S2_CARD_IMAGE" | "S2_CARD_CONCEPT",
  "modality": "CT" | "MRI" | "...",
  "anatomy_region": "...",
  "key_findings_keywords": ["...", "..."],
  "view_or_sequence": "...",
  "exam_focus": "...",
  "prompt_en": "..."
}
```

### 2.3 S4 Generated Image

**Source:** Determined from S4 manifest

**Path Pattern:**
- Card images: `{RUN_TAG}/images/IMG__{RUN_TAG}__{group_id}__{entity_id}__{card_role}.jpg`
- Table visuals: `{RUN_TAG}/images/IMG__{RUN_TAG}__{group_id}__TABLE.jpg`

**Format:** JPG image file (passed to LLM as visual input)

---

## 3. Output Schema

S6 produces an enhanced S3 image specification ready for S4 consumption.

### 3.1 Enhanced Spec Structure

```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "run_tag": "...",
  "group_id": "...",
  "entity_id": "...",
  "card_role": "Q1" | "Q2",
  "spec_kind": "...",
  "image_placement_final": "...",
  "image_asset_required": true,
  "modality": "...",
  "anatomy_region": "...",
  "key_findings_keywords": ["..."],
  "template_id": "...",
  "prompt_en": "...",
  "positive_instructions": [
    "Instruction 1...",
    "Instruction 2...",
    "Instruction 3..."
  ],
  "prompt_en_enhanced": "...",
  "answer_text": "...",
  "view_or_sequence": "...",
  "exam_focus": "...",
  "regen_metadata": {
    "source_s5_score": 85.0,
    "regen_version": 1,
    "regen_timestamp": "2026-01-15T10:30:00Z"
  }
}
```

### 3.2 New Fields

**`positive_instructions`** (Array of strings):
- List of positive, actionable modification instructions
- Each instruction is 1-2 sentences
- Focuses on visual/technical aspects
- Uses affirmative phrasing ("Generate X" not "Don't generate Y")

**`prompt_en_enhanced`** (String):
- Original `prompt_en` enhanced with positive instructions
- Format: `{original_prompt}\n\nADDITIONAL REFINEMENTS:\n{instructions}`

**`regen_metadata`** (Object):
- Tracking information for regeneration lineage
- `source_s5_score`: Original image_regeneration_trigger_score
- `regen_version`: Version number (1 for first regen)
- `regen_timestamp`: ISO 8601 timestamp

---

## 4. Model Selection Policy

S6 uses different LLM models based on image complexity:

### 4.1 Model Assignment Rules

| Condition | Model | Rationale |
|-----------|-------|-----------|
| `spec_kind == "S1_TABLE_VISUAL"` | `gemini-3-pro-preview` | Complex layouts require advanced reasoning |
| `spec_kind == "S2_CARD_IMAGE"` | `gemini-3-flash-preview` | Simpler conversion, faster processing |
| `spec_kind == "S2_CARD_CONCEPT"` | `gemini-3-flash-preview` | Conceptual diagrams are straightforward |

### 4.2 Model Configuration

**Common Settings:**
- **Thinking Mode:** Always ON (required for quality reasoning)
- **Temperature:** 0.2 (low variance for consistency)
- **RAG/Retrieval:** OFF (prevent scope creep)
- **Max Output Tokens:** 2048

**Rationale for Thinking Mode:**
- S6 needs to carefully analyze complex feedback
- Thinking helps maintain clinical accuracy
- Quality over speed for regeneration decisions

---

## 5. Processing Guidelines

### 5.1 Positive Instruction Generation

**Principles:**
1. **Affirmative Phrasing:** Use "Generate/Show/Include X" instead of "Don't show Y"
2. **Specificity:** Concrete, actionable instructions (not vague suggestions)
3. **Clinical Fidelity:** Address issues without changing medical intent
4. **Scope Preservation:** Stay within original modality/anatomy/view

**Example Transformations:**

| S5 Feedback (Negative) | S6 Instruction (Positive) |
|------------------------|---------------------------|
| "Text overlays present" | "Generate image without any text, labels, or annotations" |
| "Wrong imaging plane" | "Generate image in axial plane as specified" |
| "Findings not visible" | "Ensure key findings (저음영 lesion) are clearly visible in the center of the image" |
| "Multiple frames shown" | "Generate single-frame image showing one representative view" |

### 5.2 Instruction Categories

**Visual/Technical:**
- Image plane/view corrections
- Frame count specifications
- Contrast/visibility adjustments
- Artifact removal

**Content Refinement:**
- Anatomical positioning
- Finding prominence
- Clinical realism enhancement
- Layout optimization

**Prohibited:**
- Adding new medical facts
- Changing diagnosis/findings
- Modifying modality requirements
- Introducing new anatomy

### 5.3 Quality Criteria

**Valid Instructions:**
- ✅ Can be executed by S4 image generator
- ✅ Address specific S5 feedback points
- ✅ Maintain original clinical intent
- ✅ Use concrete, measurable terms

**Invalid Instructions:**
- ❌ Require medical interpretation
- ❌ Add content beyond original spec
- ❌ Too vague to implement
- ❌ Contradict original requirements

---

## 6. Integration with Pipeline

### 6.1 Workflow Position

```
S5 Validation Results
  ↓
  Filter: image_regeneration_trigger_score < 80.0
  ↓
[S6 Positive Instruction Agent]
  ├─ Input 1: S5 prompt_patch_hint
  ├─ Input 2: S3 original spec
  └─ Input 3: S4 generated image
  ↓
Enhanced S3 Spec (with positive_instructions)
  ↓
S4 Image Generator (--image_type regen)
  ↓
images_regen/IMG__*_regen.jpg
```

### 6.2 File Naming Conventions

**Input Specs:**
- Original: `s3_image_spec__arm{X}__original_diagram.jsonl`

**Output Specs:**
- Enhanced: `s3_image_spec__arm{X}__regen_positive_v{N}.jsonl`
  - `v{N}`: Version number (v1, v2, etc.)

**Output Images:**
- Folder: `{RUN_TAG}/images_regen/`
- Naming: `IMG__{RUN_TAG}__...{card_role}_regen.jpg`
- Manifest: `s4_image_manifest__arm{X}__regen.jsonl`

### 6.3 Run Tag Policy

**Critical:** Regenerated images use the **SAME RUN_TAG** as baseline.

**Discrimination:**
- **Folder:** `images/` (baseline) vs `images_regen/` (regen)
- **Suffix:** None (baseline) vs `_regen` (regen)
- **Manifest:** Separate files to avoid overwrite

**Rationale:** Simplifies S5 validation data reuse while maintaining clear asset segregation.

---

## 7. Error Handling and Validation

### 7.1 Input Validation

**Pre-conditions (FAIL-FAST):**
- S5 validation results must exist
- S3 original spec must be found
- S4 image file must be accessible
- Required fields must be present

### 7.2 Output Validation

**Post-conditions:**
- At least 1 positive instruction generated
- Enhanced prompt length < 8192 characters
- All original spec fields preserved
- `regen_metadata` correctly populated

### 7.3 Failure Modes

| Failure Type | Handling |
|--------------|----------|
| Missing S5 feedback | Skip target (log warning) |
| Missing S3 spec | Skip target (log warning) |
| Missing S4 image | Skip target (log warning) |
| LLM call failure | Retry 3x with exponential backoff |
| Invalid output format | Skip target (log error) |
| Empty instructions | Skip target (log warning) |

---

## 8. Acceptance Criteria

### 8.1 Functional Requirements

- [ ] S6 successfully loads S5 validation results
- [ ] S6 finds matching S3 specs and S4 images
- [ ] S6 generates positive instructions for low-score images
- [ ] Enhanced specs are S4-compatible
- [ ] Regenerated images are saved to `images_regen/`
- [ ] Separate regen manifest is created

### 8.2 Quality Requirements

- [ ] Positive instructions are actionable
- [ ] Clinical intent is preserved
- [ ] No new medical content added
- [ ] Instructions address S5 feedback points
- [ ] Model selection follows policy (Pro/Flash)

### 8.3 Integration Requirements

- [ ] S6 works with existing S3/S4/S5 pipeline
- [ ] Same RUN_TAG strategy works correctly
- [ ] Manifest separation prevents overwrite
- [ ] File naming follows conventions

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Positive Instruction Generation:**
- Test negative → positive transformation
- Verify affirmative phrasing
- Check specificity and actionability

**Model Selection:**
- Verify TABLE → Pro
- Verify CARD → Flash

### 9.2 Integration Tests

**Full Pipeline:**
1. Run S5 validation → get low scores
2. Run S6 agent → get enhanced specs
3. Run S4 with `--image_type regen`
4. Verify `images_regen/` populated
5. Verify separate manifest created

### 9.3 Quality Tests

**Manual Review:**
- Sample 10-20 regenerated images
- Compare baseline vs regen
- Verify S5 feedback addressed
- Check clinical accuracy maintained

---

## 10. Change Control

This specification is **Active** and may be updated as the positive regen workflow is refined.

**Approval Required For:**
- Schema changes (input/output structure)
- Model selection policy changes
- Scope boundary modifications
- Integration contract changes

**No Approval Needed For:**
- Prompt template refinements
- Error message improvements
- Logging enhancements
- Documentation clarifications

---

## 11. References

**Related Documents:**
- `S3_to_S4_Input_Contract_Canonical.md` - S4 input spec format
- `S5_Validation_and_Repair_Spec.md` - S5 output format
- `Image_Asset_Naming_and_Storage_Convention.md` - File naming rules
- `S5_Multiagent_Repair_Plan_OptionC_Canonical.md` - Overall repair strategy

**Implementation Files:**
- `3_Code/src/06_s6_positive_instruction_agent.py` - Core agent logic
- `3_Code/src/tools/regen/positive_regen_runner.py` - Orchestrator
- `3_Code/prompt/S6_POSITIVE_INSTRUCTION__v1.md` - LLM prompt template

---

## Appendix A: Example Input/Output

### Input Example

**S5 Feedback:**
```json
{
  "card_image_validation": {
    "prompt_patch_hint": [
      "Image contains text labels and annotations",
      "Multiple frames shown instead of single representative view",
      "Key findings (저음영 lesion) not prominently visible"
    ]
  },
  "image_regeneration_trigger_score": 82.0
}
```

**S3 Original Spec:**
```json
{
  "modality": "CT",
  "anatomy_region": "뇌",
  "key_findings_keywords": ["저음영", "삼각형 모양"],
  "view_or_sequence": "axial",
  "prompt_en": "Generate a realistic CT image of 뇌 showing 저음영 lesion..."
}
```

### Output Example

**Enhanced S3 Spec:**
```json
{
  "modality": "CT",
  "anatomy_region": "뇌",
  "key_findings_keywords": ["저음영", "삼각형 모양"],
  "view_or_sequence": "axial",
  "prompt_en": "Generate a realistic CT image of 뇌 showing 저음영 lesion...",
  "positive_instructions": [
    "Generate image without any text, labels, arrows, or annotations",
    "Generate single-frame image showing one representative axial view",
    "Ensure 저음영 lesion is prominently visible in the center of the image with clear contrast"
  ],
  "prompt_en_enhanced": "Generate a realistic CT image of 뇌 showing 저음영 lesion...\n\nADDITIONAL REFINEMENTS:\n- Generate image without any text, labels, arrows, or annotations\n- Generate single-frame image showing one representative axial view\n- Ensure 저음영 lesion is prominently visible in the center of the image with clear contrast"
}
```

---

**Document Version:** 1.0  
**Status:** Canonical · Active  
**Last Updated:** 2026-01-15  
**Next Review:** After Phase 4 testing completion

