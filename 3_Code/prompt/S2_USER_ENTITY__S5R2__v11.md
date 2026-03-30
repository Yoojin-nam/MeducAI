TASK:
Generate exactly N text-only Anki cards for the specified entity_name, aligned to the master_table_md and entity_context.

AUTHORITATIVE READ-ONLY CONTEXT:

[Master Table — S1 Output]
{master_table_md}

EXECUTION TARGET:
- Entity Name: {entity_name}
- Exact Card Count: {cards_for_entity_exact}

ENTITY CONTEXT (READ-ONLY):
{entity_context}

You MUST:
1) Output exactly N cards:
   - "cards_for_entity_exact" is authoritative, produce exactly N = {cards_for_entity_exact} cards.
   - Generate Q1, then Q2, in that order.
2) Keep entity scope:
   - Use ONLY concepts that belong to the entity_name and the S1 master_table_md.
   - Do NOT introduce content outside the entity's learning objective scope.
3) Card quality:
   - Each card MUST have non-empty front and back.
   - Exam-relevant, concise, clinically correct.
4) Card types and roles:
   - Q1: BASIC card type
   - Q2: MCQ card type (exactly 5 options A–E)
   - Each card MUST have card_role field: Q1 or Q2.
   - For Q2 MCQ: MUST include "options" array (5 strings) and "correct_index" (0-4).
5) Image hint requirements (BACK-only infographics for both):
   - Q1: MUST include image_hint object (required).
   - Q2: MUST include image_hint object (required, independent from Q1).
   - image_hint is minimal structured metadata, NOT a full image prompt.
6) Prohibitions:
   - No full image prompts.
   - No deictic image references on the front/back ("이 영상에서 보이는", "shown here" 등 금지).
   - No extra keys beyond schema (EXCEPTION: image_hint_v2 is allowed).

7) image_hint_v2 requirement (rollout/experiment mode):
   - If validation requires it (S2_REQUIRE_IMAGE_HINT_V2=1), you MUST include image_hint_v2 for both Q1 and Q2.
   - Even when not strictly required, you SHOULD include it when possible.

7) Token usage (when budget allows):
   - Use extra tokens to strengthen anatomy constraints in image_hint_v2 (laterality, landmarks, adjacency, topology).
   - Prefer short, structured constraints over verbose prose.

────────────────────────
CARD BLUEPRINTS WITH COGNITIVE ALIGNMENT
────────────────────────

────────────────────────
[Q1: BASIC] - ENTITY TYPE ADAPTATIONS
────────────────────────

The entity_context will include an entity_type field. Adapt Q1 generation based on entity_type:

**Disease/Diagnosis (entity_type="disease", default):**
Cognitive Level: APPLICATION (Bloom's Taxonomy Level 3)

Front MUST start with:
- An imaging summary (do NOT require printing the literal label "영상 요약:") that describes:
  (1) Modality and typical view/sequence
    - Example: "CT axial에서", "MRI T2-weighted sagittal에서"
  (2) 2–4 key findings in plain descriptive language
    - Technical, specific, but NOT deictic ("관찰되는", "보이는" 등 금지)
    - Example (descriptive, non-giveaway): "장골 피질 내 1.2cm 크기의 작은 원형 저음영 중심부와 중심부 석회화가 있고, 주변부 반응성 골경화가 현저하다."
  (3) Minimal clinical context only if essential
    - Example: "야간 통증이 있는 15세 남성."
- Difficulty control (to avoid overly obvious stems):
  - Do NOT rely on a single "giveaway" hallmark term, sign name, or eponym to make the diagnosis trivial.
  - Prefer descriptive phrasing (location/distribution/shape/signal/attenuation/enhancement pattern).
  - Include 2–3 supportive findings + 1 discriminator (or 1 key negative finding) that helps rule out the closest common trap.
  - Optionally add one mild confounder (red herring) that is plausible but not decisive.
  - Still keep ONE best diagnosis (avoid broad multi-step differential workups).
- End with: "가장 가능성이 높은 진단은?"

image_hint.exam_focus: MUST be "diagnosis"

**Sign/Pattern (entity_type="sign"):**
Cognitive Level: APPLICATION (Bloom's Taxonomy Level 3)

Front MUST start with:
- An imaging summary describing the pattern (do NOT require printing the literal label "영상 요약:"):
  (1) Modality and typical view/sequence
  (2) 2–4 key pattern features in plain descriptive language
    - Example: "CT에서 폐 실질 내 공기 기관지 조영제(air bronchogram)와 함께 경계가 불명확한 경화음영이 관찰된다."
  (3) Minimal clinical context if relevant
- End with: "이 소견이 시사하는 진단은?" OR "이 영상 소견의 이름은?" (choose based on what fits better)

image_hint.exam_focus: MUST be "pattern" or "sign" (NOT "diagnosis")

**Overview/General (entity_type="overview"):**
Cognitive Level: KNOWLEDGE or APPLICATION (Bloom's Taxonomy Level 1 or 3)

Front:
- Describe key features or characteristics, then ask:
  - "이 개념에 해당하는 것은?" OR
  - "이 분류 체계에서 ...는?" OR
  - "이 원칙에 따라 ...는?" (choose based on entity content)
- Example: "다음 중 TNM 분류 체계에서 T1N0M0에 해당하는 것은?"

image_hint.exam_focus: MUST be "concept" or "classification" (NOT "diagnosis")

**QC (entity_type="qc"):**
Cognitive Level: APPLICATION (Bloom's Taxonomy Level 3)

Front:
- Describe test procedure/measurement, then ask:
  - "이 측정값의 의미는?" OR
  - "이 검사 절차의 목적은?" OR
  - "이 QC 항목에서 정상 범위는?" (choose based on entity content)
- Example: "CT phantom에서 측정한 Water CT Number가 0 HU인 경우, 이 측정값의 의미는?"

image_hint.exam_focus: MUST be "procedure", "measurement", or "principle" (NOT "diagnosis")

**Equipment (entity_type="equipment"):**
Cognitive Level: APPLICATION (Bloom's Taxonomy Level 3)

Front:
- Describe equipment operation/principle, then ask:
  - "이 기구의 이름은?" OR
  - "이 검사 기법의 주요 적응증은?" OR
  - "이 장비의 작동 원리는?" (choose based on entity content)
- Example: "다음 중 고주파 발생 장치를 사용하여 조직을 절제하는 수술 기구는?"

image_hint.exam_focus: MUST be "procedure", "principle", or "operation" (NOT "diagnosis")

**Comparison/Differential (entity_type="comparison"):**
Cognitive Level: APPLICATION (Bloom's Taxonomy Level 3)

Front MUST start with:
- An imaging summary (do NOT require printing the literal label "영상 요약:") that describes:
  (1) Modality and typical view/sequence
    - Example: "CT axial에서", "MRI T2-weighted sagittal에서"
  (2) 2–4 key findings that help distinguish between the compared entities
    - Technical, specific, but NOT deictic ("관찰되는", "보이는" 등 금지)
    - Focus on findings that differentiate between the compared entities
    - Example: "CT에서 흉막강 내 공기-액체 수평면(air-fluid level)이 있고, 벽이 두껍고 불규칙하며, 주변 폐실질에 염증 소견이 있다."
  (3) Minimal clinical context only if essential
- End with: "이 영상 소견에서 가장 가능성이 높은 진단은?" OR "다음 중 이 영상 소견과 가장 일치하는 진단은?"

Options (for MCQ Q1, if applicable):
- MUST include both entities in the comparison (e.g., if entity is "Lung Abscess vs Empyema", include both as options)
- Example options: ["Lung Abscess", "Empyema", "Pneumonia", "Pleural effusion", "Lung cancer"]

Back format:
- "Answer: <answer>"
- "근거:" 2–4 bullets explaining why the correct answer is more likely
- "함정/감별:" 1–2 bullets explaining key distinguishing features from the compared entity
  - Example: "Empyema와의 감별: Empyema는 흉막강 내 위치, 얇은 벽, 주변 폐실질 정상. 공기-액체 수평면은 Abscess에서 더 흔함."

image_hint.exam_focus: MUST be "diagnosis" (but frame as differential diagnosis)

Cognitive Alignment Check (all entity types):
- ✅ Requires appropriate cognitive operation for entity_type (diagnostic application, pattern recognition, conceptual understanding, or technical application)
- ❌ NOT pure factual recall without context (unless entity_type="overview" where it may be acceptable)
- ❌ NOT complex multi-step analysis (too complex, Analysis level)

Back format (all entity types):
- "Answer: <answer>"
- "근거:" 2–4 bullets
- "함정/감별:" 1–2 bullets (if applicable)
- Keep it brief, board-style.

image_hint_v2 for Q1 (structured constraints, NOT a full prompt; REQUIRED when IMG_REQ=true):
- MUST include: laterality (L/R/Midline/NA), orientation.view_plane or orientation.projection, key_landmarks_to_include (≤3), forbidden_structures (≤5)
- Set safety.requires_human_review=true if: missing_view, uncertain_location, or uncertain_modality

VIEW/LATERALITY SAFETY (S5R1; reduces view_mismatch/laterality_error):
- Choose view_or_sequence that is easiest to depict as a **single, unambiguous image**.
  - Use \"axial\" ONLY when a true cross-sectional slice depiction is appropriate.
  - For didactic whole-organ schematics where axial is error-prone (e.g., many cardiac/vascular diagrams), prefer \"coronal\"/\"frontal\" schematic unless the entity truly requires an axial slice.
- For axial CT/MRI: treat it as feet-to-head viewing convention (viewer-left = patient-right). Do NOT request or rely on L/R text labels.
- Never include laterality text tokens in any generated text/labels (forbidden tokens: \"Left\", \"Right\", \"L\", \"R\", \"(Left)\", \"(Right)\").
- For NM/Bone scan keywords:
  - If key_findings_keywords include \"Photopenia\" / \"Cold spot\", ensure the intended depiction is **decreased uptake** (avoid phrasing that implies a hot focus).

────────────────────────
[Q2: MCQ, 1교시 스타일 개념 이해 기반]
Cognitive Level: APPLICATION or KNOWLEDGE (Bloom's Taxonomy Level 3 or 1)
────────────────────────

Front format:
- Ask a concept question tied to the same entity:
  - Pathophysiology, mechanism
  - Treatment principle, indication/contraindication
  - Complication, QC/physics principle
  - Classification rationale
  - Pattern mechanism (for sign entities)
- Must be solvable from text alone (NO image dependency).
- Do NOT ask for a diagnosis again (avoid redundancy with Q1).
- **Anki convention**: Do NOT list options A–E in `front`. Provide the question stem in `front`, and put the 5 options in the structured `options[]` field with `correct_index`.
- **Terminology Context**: Distinguish between clinical and administrative/QC terminology.
  - For QC/administrative questions: Use "판정", "결과", "평가 결과", or "지적 사항" instead of "진단".
  - For clinical questions: Use "진단" appropriately.
  - Example: "이 QC 항목에서 정상 범위는?" (not "이 QC 항목의 진단은?").
- **Terminology discipline**: Prefer current standard terminology used in clinical practice/board exams. If a legacy term is common, add it as "formerly …" but keep modern naming primary.
  - Use standard Korean medical terms: "polyposis" → "용종증" (not "유종"), "Metaphysis" → "골간단" (consistent spelling), "bronchus" → "기관지" (not "동맥").
- **Numeric cutoffs**: If you include numeric thresholds, ensure they are context-specific (territory/modality dependent) and avoid overconfident single-number claims when ambiguous.

Examples of appropriate Q2 questions:
- "다음 중 Osteoid Osteoma의 치료에서 radiofrequency ablation의 주요 적응증으로 가장 적절한 것은?"
- "이 질환의 병인론적 기전과 가장 관련이 깊은 것은?"
- "다음 중 이 검사 기법의 주요 적응증이 아닌 것은?"
- "이 물리 현상의 핵심 원리는?"
- "Double stripe sign의 병인론적 기전과 가장 관련이 깊은 것은?" (for sign entities)

Cognitive Alignment Check:
- ✅ Tests conceptual understanding (pathophysiology, mechanism, treatment, etc.)
- ✅ Solvable from text alone (no image dependency)
- ❌ NOT diagnostic pattern recognition (that's Q1)
- ❌ NOT complex multi-step analysis (too complex, Analysis level)

Back format:
- "정답: <A–E or option text>"
  - Example: "정답: D"
- "근거:" 2–4 bullets
  - Example: "* RFA는 수술적으로 접근하기 어려운 부위에 적합"
- "오답 포인트:" 1–2 bullets (why the closest distractor is wrong)
  - Example: "C는 오히려 RFA의 금기증일 수 있음 (척추는 신경 손상 위험)"
  - **IMPORTANT**: If the MCQ has 5 options (A–E), ensure the explanation addresses ALL distractors (A, B, C, D, E) in the "오답 포인트" section.
  - Each distractor explanation must directly correspond to the lettered option (A, B, C, D, E).
  - The explanation should directly refute the specific content of the corresponding option.
  - Educational completeness requires all options to be accounted for.

options:
- Exactly 5 strings, each a plausible exam option.
- Options must form a "homogeneous set" (all diagnoses, all treatments, all principles, etc.).
- Keep options concise, noun-phrase centered. No long explanations.
- **CRITICAL**: Do NOT prepend the option letter (A, B, C, D, E) to the option text. The options[] array should contain clean text without redundant prefixes (e.g., "CTDIw" not "A. CTDIw").
- "All of the above" / "None of the above" FORBIDDEN in principle.

correct_index:
- 0–4 index of the best answer.

image_hint for Q2 (independent infographic):
{
  "modality_preferred": "...",  // MUST be one of: CT, MRI, XR, US, PET, Fluoro, Mammo, NM, Echo, Angio. NEVER "Other". May differ from Q1.
  "anatomy_region": "...",  // may differ from Q1
  "key_findings_keywords": ["...", "...", "..."],  // 3–8 keywords
  "view_or_sequence": "...",  // may differ from Q1
  "exam_focus": "concept"  // MUST be "concept" (or "management"/"mechanism" if more specific)
}

image_hint_v2 for Q2 (structured constraints; REQUIRED when IMG_REQ=true):
- MUST include required fields: laterality, orientation (view_plane or projection), key_landmarks_to_include (≤3), forbidden_structures (≤5)
- Use for anatomy grounding (laterality/landmarks/adjacency/topology) and strict rendering policy.
- Prefer to include at least 1 topology_constraints rule for Q2 when possible (even a short "A connects_to B" / "A anterior_to B" style rule).
- Prefer to include at least 1 adjacency_rules rule for Q2 when possible (even a short "A adjacent_to B" / "A connects_to B" style rule).
- To make this easy and consistent, choose ONE of these relationship types and write 1 short rule:
  - connects_to, located_in, crosses_midline, anterior_to/posterior_to, superior_to/inferior_to
  - Examples (pick 1–2 max; keep short):
    - "STRUCTURE_A connects_to STRUCTURE_B"
    - "STRUCTURE_A located_in REGION_B"
    - "TUBE/DUCT crosses_midline to reach TARGET"
    - "STRUCTURE_A anterior_to STRUCTURE_B"
    - "STRUCTURE_A inferior_to STRUCTURE_B"
- Set safety.requires_human_review=true if: missing_view (view_plane and projection both unknown), uncertain_location, or uncertain_modality
- If unsure, set safety.requires_human_review=true and keep constraints minimal.

────────────────────────
COGNITIVE ALIGNMENT VERIFICATION (REQUIRED)
────────────────────────

Before finalizing, verify:

Q1 Verification:
1. Does this question match the entity_type requirements?
   - Disease: Requires applying imaging findings to diagnostic knowledge? (APPLICATION level)
   - Sign: Requires pattern recognition and pattern→diagnosis mapping? (APPLICATION level)
   - Overview: Tests conceptual understanding of classification/summary? (KNOWLEDGE or APPLICATION level)
   - QC/Equipment: Tests technical application (measurement/procedure/principle)? (APPLICATION level)
   - Comparison: Tests differential diagnosis reasoning by distinguishing between compared entities? (APPLICATION level)
2. Does the front begin with modality/view + key findings/features (an imaging/pattern/procedure summary), without needing a fixed label like "영상 요약:"?
3. Does it ask the appropriate question type for the entity_type?
4. Can it be answered by the appropriate cognitive operation for the entity_type?
5. Is it NOT too simple (pure recall) or too complex (multi-step differentiation)?
6. Is it too easy because the stem includes a single giveaway hallmark term?
   - If YES → Rewrite more descriptively and add a discriminator (or key negative finding) and/or a mild confounder while keeping one best answer.
7. Does image_hint.exam_focus match the entity_type requirements?

Q2 Verification:
1. Is it solvable from text alone (no image dependency)?
2. Does it test conceptual understanding (not diagnostic pattern recognition)?
3. Does it avoid redundancy with Q1 (not asking for diagnosis again)?
4. Is it appropriately scoped (not too simple pure definition, not too complex multi-step analysis)?

If verification fails, regenerate the card with correct cognitive alignment.

────────────────────────
REMINDER
────────────────────────
- Q1 adapts based on entity_type (diagnostic/pattern/concept/technical), Q2 is conceptual/management (1교시 느낌, APPLICATION or KNOWLEDGE level).
- Both images are BACK-only infographics, so the card must stand alone without seeing any image.
- Both Q1 and Q2 require independent image_hint objects.
- image_hint.exam_focus MUST match entity_type requirements for Q1.

CANONICAL OUTPUT SCHEMA:
{
  "entity_name": "{entity_name}",
  "anki_cards": [
    {
      "card_role": "Q1",
      "card_type": "BASIC",
      "front": "CT axial에서 ... [appropriate question for entity_type]",
      "back": "Answer: ...\n\n근거:\n* ...\n\n함정/감별:\n* ...",
      "tags": ["string", "string"],
      "image_hint": {
        "modality_preferred": "...",
        "anatomy_region": "...",
        "key_findings_keywords": ["...", "...", "..."],
        "view_or_sequence": "...",
        "exam_focus": "[diagnosis|pattern|sign|concept|classification|procedure|measurement|principle|operation]"
      },
      "image_hint_v2": {
        "anatomy": {
          "organ_system": "...",
          "organ": "...",
          "subregion": "...",
          "laterality": "L",
          "orientation": {"view_plane": "axial", "projection": "NA"},
          "key_landmarks_to_include": ["..."],
          "forbidden_structures": ["..."],
          "adjacency_rules": ["..."],
          "topology_constraints": ["..."]
        },
        "rendering_policy": {
          "style_target": "flat_grayscale_diagram",
          "text_budget": "minimal_labels_only",
          "forbidden_styles": ["photorealistic", "PACS_UI", "DICOM_overlay"]
        },
        "safety": {"requires_human_review": false, "fallback_mode": "generic_conservative_diagram"}
      }
    },
    {
      "card_role": "Q2",
      "card_type": "MCQ",
      "front": "질문 텍스트 (이미지 참조 없음)",
      "back": "정답: ...\n\n근거:\n* ...\n\n오답 포인트:\n* ...",
      "tags": ["string", "string"],
      "options": ["option A", "option B", "option C", "option D", "option E"],
      "correct_index": 0,
      "image_hint": {
        "modality_preferred": "...",
        "anatomy_region": "...",
        "key_findings_keywords": ["...", "...", "..."],
        "view_or_sequence": "...",
        "exam_focus": "concept"
      },
      "image_hint_v2": {
        "anatomy": {
          "organ_system": "...",
          "organ": "...",
          "subregion": "...",
          "laterality": "NA",
          "orientation": {"view_plane": "NA", "projection": "NA"},
          "key_landmarks_to_include": ["..."],
          "forbidden_structures": [],
          "adjacency_rules": [],
          "topology_constraints": []
        },
        "rendering_policy": {
          "style_target": "flat_grayscale_diagram",
          "text_budget": "minimal_labels_only",
          "forbidden_styles": ["photorealistic", "PACS_UI", "DICOM_overlay"]
        },
        "safety": {"requires_human_review": false, "fallback_mode": "generic_conservative_diagram"}
      }
    }
  ]
}

STOP AFTER OUTPUT.

