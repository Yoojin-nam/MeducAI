# S5R2 — S5 S2 Card + Image Validation User Prompt v1.0

**Purpose:** Validate S2 Anki card AND its associated image for medical safety, exam fitness, and educational quality.

---

## Task

Evaluate the following S2 Anki card AND its image for:
1. Technical Accuracy (0/0.5/1.0 scale) - for both text and image
2. Educational Quality (1-5 Likert scale) - for card overall
3. **Blocking Errors (clinical safety-critical only)** - for both text and image
4. Issues and suggested fixes (actionable, minimal scope)
5. **Image-specific evaluation** (anatomical accuracy, prompt compliance, text-image consistency, image quality, safety)

---

## Input Data

### Card Information
- **Card ID:** {card_id}
- **Card Role:** {card_role} (Q1 or Q2)
  - Note: Q3 is deprecated in the current 2-card policy.
- **Card Type:** {card_type} (BASIC or MCQ)
- **Entity ID:** {entity_id}
- **Entity Name:** {entity_name}
- **Image Placement:** BACK (Q1 and Q2 both use back-only images in 2-card policy)

### Card Content
**Front:**
{card_front}

**Back:**
{card_back}

### MCQ Structured Fields (Anki Convention)

**Important:** For Anki MCQ cards, the multiple-choice options are stored in structured JSON fields and may NOT appear in the Front text. Do NOT flag "options missing in Front" as an issue if options are provided below.

**Options (A–E, if MCQ):**
{card_options}

**Correct index (0–4, if MCQ):**
{correct_index}

### Entity Context (from S1 table; read-only)
{entity_context}

### S3 Image Prompt (Reference)
**S3 prompt_en (what the image should show):**
{s3_prompt_en}

**S3 image_hint_v2 (anatomical constraints):**
{s3_image_hint_v2}

**S3 exam_prompt_profile (image style):**
{exam_prompt_profile}
- **CRITICAL**: This indicates whether the image was generated using REALISTIC or DIAGRAM prompt profile.
- If `exam_prompt_profile` is "realistic", "v8_realistic", "pacs", "v8_realistic_4x5_2k", or "s5r2_realistic", then this is a REALISTIC image and you MUST evaluate realistic_appearance, modality_appropriate_texture, and conspicuity_control metrics.
- If `exam_prompt_profile` is "diagram" or any other value (or missing), then this is a DIAGRAM image and you MUST skip realistic evaluation metrics (set them to 1.0 or omit them).

### S2 Image Hint (Original Specification)
**S2 image_hint (original card specification):**
{s2_image_hint}

**Key landmarks to include (from image_hint_v2.anatomy.key_landmarks_to_include):**
{key_landmarks_list}

### Source Text for Comparison (S1/S2)
**S1 Table Context (entity row data):**
The entity_context above contains S1 table row data for this entity. Use this to identify if image text is directly copied from S1 without proper adaptation.

**S2 Card Text:**
- Front: {card_front}
- Back: {card_back}
- Key findings keywords (from image_hint): {key_findings_keywords}

**Important**: Image text may be derived from S1 table or S2 card text. When evaluating image text quality, compare extracted text with:
1. S1 table row values (entity_context)
2. S2 card front/back text
3. key_findings_keywords from image_hint

Flag issues if:
- Text is verbatim copied from S1/S2 without adaptation to the visual context
- Text mixes Korean and English in a confusing way (e.g., "Popcorn-like 석회화")
- Text doesn't accurately describe what is shown in the image

### Card Image
**Image file:** {image_path}

The image above should be evaluated together with the card text.

---

## Instructions

### 1. Card Text Evaluation (Standard)
1. **Clinical safety (blocking)**:
   - Set `blocking_error=true` ONLY if there is a safety-critical medical error that could mislead clinical decisions.
   - If `blocking_error=true`, you MUST set `technical_accuracy=0.0` and provide RAG evidence.
2. **Exam fitness / board-style quality (non-blocking)**:
   - Assess clarity, fairness (single best answer), distractor quality, alignment with typical board expectations.

**Note**: Difficulty (난이도 적절성) evaluation is performed in card text evaluation (S5_USER_CARD__v2.md), not in image evaluation. Since Q1 and Q2 images are placed on the BACK of cards, the image itself does not affect difficulty assessment. Difficulty is evaluated based on whether the card front text gives away the answer, which is independent of the image.
3. **MCQ correctness (use structured fields)**:
   - If `card_type=MCQ`:
     - Verify `options` has exactly 5 items and `correct_index` is within 0–4.
     - **CRITICAL: Answer-Explanation Consistency**:
       - Verify that the `back` explanation/rationale is **consistent** with the option at `options[correct_index]`
       - The explanation must clearly support why the option at `correct_index` is the correct answer
       - If the explanation contradicts or doesn't match the correct option, this is a **BLOCKING ERROR** (`blocking_error=true`)
       - Issue type: `answer_explanation_mismatch`
     - **CRITICAL: Multiple Answer Risk**:
       - Analyze all options to determine if multiple answers could be considered correct
       - Consider differential diagnosis scenarios and whether the question provides sufficient distinguishing information
       - If 2+ options could plausibly be correct based on the question stem, flag as `multiple_answer_risk=true`
       - Issue type: `multiple_answer_possible` (severity: "major" or "blocking" if severe)
     - Do NOT require options to appear in Front; options belong to the structured field.
4. **List issues**:
   - Use `severity` to reflect impact (`blocking` reserved for clinical safety only).
   - Provide minimal suggested fixes (do not rewrite the entire card).
5. **Actionable metadata (optional but recommended)**:
   - Include `issue_code`, `recommended_fix_target`, and `prompt_patch_hint` when you can point to a systematic upstream fix.

### 2. Image Evaluation (NEW)
Evaluate the image for:

1. **Anatomical Accuracy** (`anatomical_accuracy`): 0.0 | 0.5 | 1.0
   - Is the anatomical structure medically accurate?
   - **CRITICAL: Landmark Verification**:
     - Check if all landmarks listed in `key_landmarks_to_include` (from `image_hint_v2.anatomy.key_landmarks_to_include`) are visible in the image
     - Use visual analysis to identify each required landmark
     - Missing critical landmarks should be flagged with `landmark_missing` issue type
     - If essential landmarks are missing, consider `anatomical_accuracy=0.5` or `0.0` depending on severity
   - Is laterality (L/R/Midline) correct and clear?
   - **Axial convention safety**: If the image includes any explicit laterality text/markers (e.g., \"Left/Right\", \"L/R\"), treat this as high-risk and verify it matches axial convention (viewer-left = patient-right). If wrong → `blocking_error=true`.
   - Issue types: `anatomical_error`, `landmark_missing`, `laterality_error`

2. **Prompt Compliance** (`prompt_compliance`): 0.0 | 0.5 | 1.0
   - Does the image match the S3 `prompt_en` requirements?
   - **CRITICAL: Modality Match Verification**:
     - Extract modality keywords from card `front`/`back` text (CT, MRI, XR, US, Angio, NM, PETCT, etc.)
     - Compare with S2 `image_hint.modality_preferred` (must match)
     - Analyze the actual image to determine its modality using visual analysis
     - If card text mentions "CT" but image shows "US" (or vice versa), this is a **BLOCKING ERROR** (`blocking_error=true`)
     - Issue types: `modality_mismatch_text_hint`, `modality_mismatch_image_actual`, `modality_mismatch_text_image`
   - Is the correct view/sequence shown?
   - Are key findings from `key_findings_keywords` visible?
   - Issue types: `view_mismatch`, `key_finding_missing`

3. **Text-Image Consistency** (`text_image_consistency`): 0.0 | 0.5 | 1.0
   - Does the image match the card `front`/`back` text?
   - Does the image support the diagnosis/finding described in the card?
   - Issue types: `diagnosis_mismatch`, `finding_contradiction`

4. **Image Quality** (`image_quality`): 1-5 Likert
   - Resolution: Is the image resolution sufficient for interpretation?
   - Readability: Can anatomical structures be clearly identified?
   - Artifacts: Are there artifacts that affect interpretation?
   - Contrast: Is contrast sufficient?
   - **CRITICAL: Text/OCR Detection and Quality Assessment**:
   - **Image Placement Context**: Q1 and Q2 images are placed on the BACK of cards (2-card policy). Since the image appears AFTER the answer is revealed, text/labels in the image do NOT spoil the question. **However, text policy depends on `exam_prompt_profile`.**
  - **Text policy by `exam_prompt_profile` (MUST FOLLOW)**:
     - **REALISTIC** (`exam_prompt_profile` in realistic/pacs variants): **TEXT = 0 (FORBIDDEN)**.
       - Any detected text/labels/captions/measurements/letters/numbers is a policy violation.
       - Flag as `excessive_text` (even if only 1 short label).
       - Set: `issue_code="S3_TEXT_POLICY_VIOLATION_REALISTIC"`, `recommended_fix_target="S3_PROMPT"`, `prompt_patch_hint="Enforce S3 constraint_block TEXT_POLICY_ZERO_TOLERANCE for REALISTIC; regenerate with zero text."`
     - **DIAGRAM** (default): **limited labels allowed (OCR quality focus)**.
       - Text/labels may appear in DIAGRAM images (educational diagrams), but MUST remain minimal and clean.
       - Default allowance: short TITLE + a few short labels is OK (keep total text elements small).
       - Upper bound: if text is excessive/cluttered (approx >= 8 text elements), flag as `excessive_text`.
       - For DIAGRAM, do NOT fail merely because text exists. Instead focus on OCR-based text quality:
         - Is OCR text readable and meaningful (not garbled)?
         - Does OCR text contain forbidden tokens (laterality labels "Left/Right/L/R")?
         - Does OCR text contain obvious mistakes / wrong terms relative to key_findings_keywords?
       - Only when the text is excessive or clearly wrong/garbled should you add issues.
   - **CRITICAL: Text Quality Issues to Flag (when any text is present)**:
         1. **Mixed Language Issues (한영 병용 문제)**:
            - Check if text mixes Korean and English in a meaningless or confusing way
            - Example: "Popcorn-like 석회화" (mixing English term with Korean in awkward way)
            - Example: "CT 영상에서 보이는 finding" (unnecessary language mixing)
            - Flag as `text_language_mixing` issue if the mixing is confusing or meaningless
         2. **Inaccurate Text from S1/S2 Reuse**:
            - Text may be directly copied from S1 table or S2 card text without proper adaptation
            - Check if text accurately describes what is shown in the image
            - Example: If image shows a specific finding but text says something generic or slightly different
            - Example: If S1/S2 text is used verbatim but doesn't match the visual representation
            - Flag as `text_accuracy_error` or `text_image_mismatch` if text doesn't accurately describe the image
         3. **Readability and Clarity**:
            - Is text readable? (font size, contrast, clarity)
            - Is text grammatically correct?
            - Does text make sense in context?
            - Flag as `unreadable_text` or `text_clarity_issue` if readability is poor
         4. **Excessive Text**:
            - Does text exceed S4 S5R1 DIAGRAM policy (max 1 label, short words)?
            - Is text cluttered or overwhelming?
            - Flag as `excessive_text` if too much text is present
     - **For CONCEPT images (if applicable)**: Text may be present (e.g., labels, annotations). Use OCR to read ALL visible text in the image and verify:
       - Text accuracy: Are medical terms spelled correctly?
       - Text completeness: Are all required labels present?
       - Text-image consistency: Does the text match what is shown visually?
       - Same quality checks as above (language mixing, accuracy, readability)
  - **OCR Instructions**: Explicitly extract and read ALL text visible in the image using OCR capabilities. Report any text found, including:
       - Labels, annotations, measurements, or any alphanumeric characters
      - For REALISTIC: Any text presence is a policy violation (flag as `excessive_text`)
      - For DIAGRAM: Text presence is acceptable if limited; flag only if excessive OR unreadable/garbled OR contains forbidden tokens OR clearly incorrect/mismatched terms
       - Compare extracted text with S1 table context and S2 card text to identify verbatim copying issues
       - If text is missing or unreadable in a CONCEPT image (where it should be), flag as `missing_text` or `unreadable_text` issue type
   - Issue types: `low_resolution`, `artifacts`, `poor_contrast`, `excessive_text`, `unreadable_text`, `text_error`, `text_accuracy_error`, `text_language_mixing`, `text_image_mismatch`, `text_clarity_issue`

5. **Safety** (`safety_flag`): boolean
   - Does the image contain inappropriate content?
   - Could the image contain patient-identifying information?
   - Issue types: `inappropriate_content`, `patient_identifier`

6. **Realistic Appearance** (`realistic_appearance`): 0.0 | 0.5 | 1.0 (REALISTIC images only)
   - **CRITICAL: Only evaluate this metric if the image was generated using REALISTIC prompt profile (S4_EXAM_PROMPT_PROFILE=realistic).**
   - For DIAGRAM images, skip this evaluation or set to 1.0 (not applicable).
   - Does the image look like a real PACS clinical image?
   - **Studio/CG Render Detection**:
     - Does the image avoid "studio" or "CG render" appearance?
     - Check for: perfect lighting, overly smooth gradients, hyper-sharpened edges, unrealistic uniformity
     - If image looks like a 3D render or illustration rather than a real clinical image → `realistic_appearance=0.0` or `0.5`
     - Issue types: `studio_render_appearance`, `cg_like_rendering`, `unrealistic_lighting`
   - **PACS-like Style Verification**:
     - Does the image have the authentic look of a real radiology PACS image?
     - Clinical framing: appropriate field-of-view (FOV), includes typical adjacent anatomy
     - Avoid unnaturally tight lesion-centric crops
     - Issue types: `unnatural_framing`, `tight_crop`, `missing_adjacent_anatomy`

7. **Modality-Appropriate Texture** (`modality_appropriate_texture`): 0.0 | 0.5 | 1.0 (REALISTIC images only)
   - **CRITICAL: Only evaluate this metric if the image was generated using REALISTIC prompt profile.**
   - For DIAGRAM images, skip this evaluation or set to 1.0 (not applicable).
   - Does the image have modality-specific realistic texture and noise?
   - **XR (X-ray)**:
     - Trabecular pattern visible in bone
     - Cortical edge sharpness
     - Mild quantum mottle (realistic noise)
     - Issue types: `missing_trabecular_pattern`, `no_quantum_mottle`, `unrealistic_xr_texture`
   - **CT**:
     - Realistic quantum noise (not perfectly smooth)
     - Mild partial-volume effect (finite slice thickness feel)
     - Avoid CT-like smoothness in non-CT images
     - Issue types: `missing_ct_noise`, `no_partial_volume_effect`, `unrealistic_ct_texture`
   - **MRI**:
     - Subtle background noise (not perfectly uniform signal)
     - Mild coil shading (realistic non-uniformity)
     - Avoid perfectly uniform signal
     - Issue types: `missing_mri_noise`, `no_coil_shading`, `unrealistic_mri_texture`
   - **US (Ultrasound)**:
     - Realistic B-mode speckle pattern
     - Depth-dependent attenuation/gain
     - Avoid CT-like smoothness (US should have characteristic speckle)
     - Issue types: `missing_us_speckle`, `no_depth_attenuation`, `unrealistic_us_texture`
   - **General**: If modality cannot be determined or is "Other", evaluate based on whether texture looks realistic for the stated modality.

8. **Conspicuity Control** (`conspicuity_control`): 0.0 | 0.5 | 1.0 (REALISTIC images only)
   - **CRITICAL: Only evaluate this metric if the image was generated using REALISTIC prompt profile.**
   - For DIAGRAM images, skip this evaluation or set to 1.0 (not applicable).
   - Does the image show findings with appropriate severity (mild-to-moderate)?
   - **Over-exaggeration Detection**:
     - Are findings overly obvious or cartoonish?
     - Check for: glowing rims, excessive contrast, unrealistic conspicuity
     - Findings should be visible but not exaggerated (realistic subtlety)
     - If findings are too obvious (like a cartoon) → `conspicuity_control=0.0` or `0.5`
     - Issue types: `over_exaggerated_finding`, `glowing_rims`, `unrealistic_conspicuity`, `cartoonish_appearance`
   - **Severity Assessment**:
     - Findings should be mild-to-moderate severity (realistic clinical presentation)
     - Not too subtle (would be missed) but not too obvious (unrealistic)
     - Issue types: `too_subtle`, `too_obvious`, `unrealistic_severity`

### 3. Combined Evaluation
- If image has blocking errors (anatomical_accuracy=0.0, safety_flag=true), this may affect the overall card `blocking_error`.
- If text-image consistency is low (<0.5), this should be flagged as an issue affecting educational quality.

**Note**: Difficulty evaluation is NOT part of image evaluation. Since Q1 and Q2 images are placed on the BACK of cards, the image does not affect difficulty. Difficulty is evaluated in card text evaluation (S5_USER_CARD__v2.md) based on whether the card front text gives away the answer.

---

## Output

Return a JSON object with the following structure:

```json
{{
  "blocking_error": false,
  "technical_accuracy": 1.0,
  "educational_quality": 4,
  "issues": [...],
  "rag_evidence": [...],
    "card_image_validation": {{
    "blocking_error": false,
    "anatomical_accuracy": 1.0,
    "prompt_compliance": 1.0,
    "text_image_consistency": 1.0,
    "image_quality": 5,
    "safety_flag": false,
    "realistic_appearance": 1.0,
    "modality_appropriate_texture": 1.0,
    "conspicuity_control": 1.0,
    "modality_match": true,
    "landmarks_present": true,
    "extracted_text": null,
    "text_detected": false,
    "issues": [
      {{
        "severity": "minor",
        "type": "key_finding_missing",
        "description": "Halo sign is not clearly visible in the image",
        "issue_code": "PROMPT_COMPLIANCE_MISSING_FINDING",
        "recommended_fix_target": "S3_PROMPT",
        "prompt_patch_hint": "Add explicit requirement for 'halo sign' visualization in prompt.",
        "confidence": 0.9
      }}
    ],
    "image_path": "/path/to/image.jpg"
  }},
  "answer_explanation_consistency": true,
  "multiple_answer_risk": false
}}
```

**Note**: The `difficulty` field is evaluated in card text evaluation (S5_USER_CARD__v2.md), not in image evaluation. Since Q1 and Q2 images are placed on the BACK of cards, the image does not affect difficulty assessment.

**Critical:** 
- If `blocking_error=true` (card-level), you MUST include at least one RAG evidence entry with `relevance="high"`.
- If `card_image_validation.blocking_error=true`, include image-specific issues with appropriate severity.
- For MCQ cards, always include `answer_explanation_consistency` (boolean) and `multiple_answer_risk` (boolean) fields at the root level.
- For image validation, include `modality_match` (boolean) and `landmarks_present` (boolean) in `card_image_validation` if applicable.
- **OCR/Text Extraction**: 
  - Always use OCR to detect and extract any text visible in the image
  - For REALISTIC images: Text is **FORBIDDEN**. Always extract text and include in `extracted_text` field. If any text is detected → flag `excessive_text` and recommend `S3_PROMPT` fix.
  - For DIAGRAM images: Text is **minimal-label** policy. Always extract text and include in `extracted_text` field. Text presence is not automatically an error; flag if it violates minimal-label policy or is unreadable/inaccurate.
  - For CONCEPT images: Always extract text and include in `extracted_text` field. Verify text accuracy and completeness.

---

**Version:** 1.1  
**Last Updated:** 2026-01-01  
**Changes in v1.1:**
- Added Realistic image evaluation metrics (realistic_appearance, modality_appropriate_texture, conspicuity_control)
- These metrics are only evaluated for REALISTIC images (S4_EXAM_PROMPT_PROFILE=realistic)
- Addresses human QA feedback: over-exaggeration and anatomical abnormalities

