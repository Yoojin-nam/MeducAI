# S5R3 개선 계획 (Phase 3: Final Improvement)

- **목적**: S5R2 리포트 분석을 통해 S5R3에서 추가로 개선해야 할 포인트를 식별
- **근거 소스**: S5R2 리포트 (`DEV_armG_mm_S5R2_after_postFix_20251230_193112__rep1`)
- **분석 일자**: 2025-12-31
- **다음 단계**: S5R3 프롬프트 개선 및 재생성

---

## 1. Executive Summary: S5R2 주요 이슈

### 1.1 Primary Endpoint (S2_any_issue_rate_per_group)

**S5R2 결과**:
- S2 blocking cards: 3/340 (0.9%)
- S2 mean technical accuracy: 0.98
- S2 mean educational quality: 4.93

**Blocking errors**: 3건
1. `grp_92ab25064f`: anatomical_error + laterality_error
2. `grp_6ae1e80a49`: laterality_error
3. `grp_1c64967efa`: modality_mismatch_text_image

### 1.2 Top Issue Types (S2 + Card Images)

1. **excessive_text**: 49 (S2), 72 (card images) ⚠️ **가장 큰 문제**
2. **view_mismatch**: 11 (S2), 14 (card images)
3. **multi_panel_layout**: 6 (S2), 13 (card images)
4. **laterality_error**: 3 (S2), 5 (card images)
5. **anatomical_error**: 1 (S2), 1 (card images)

### 1.3 Top Issue Codes (S3_PROMPT target)

1. **IMAGE_TEXT_BUDGET_EXCEEDED**: 24건
2. **IMAGE_TEXT_COUNT_EXCEEDED**: 15건
3. **PROMPT_COMPLIANCE_TEXT_COUNT**: 13건
4. **IMAGE_TEXT_EXCESSIVE**: 11건
5. **PROMPT_COMPLIANCE_VIEW_MISMATCH**: 8건

**총 Text Budget 관련 이슈**: 63건 이상 (전체 이슈의 약 30%)

---

## 2. S5R3 개선 포인트 (Priority 기반)

### 2.1 P0 (Critical): Text Budget Enforcement 극대화

**문제**: S5R2에서도 여전히 text budget violations가 가장 큰 문제 (63건 이상).

**근거**:
- `IMAGE_TEXT_BUDGET_EXCEEDED`: 24건
- `IMAGE_TEXT_COUNT_EXCEEDED`: 15건
- `PROMPT_COMPLIANCE_TEXT_COUNT`: 13건
- `IMAGE_TEXT_EXCESSIVE`: 11건

**S5R3 요구사항**:
1. **S4_EXAM_SYSTEM에서 text budget을 "ZERO TOLERANCE"로 변경**:
   - 현재: "Default: NO text labels (labels=0). Exception: max 1 label if absolutely necessary."
   - 변경: "ABSOLUTELY FORBIDDEN: Any text labels, captions, annotations, or measurements. Use ONLY arrows and circles. If you cannot convey the finding without text, use a different visual approach (e.g., color coding, shape variation, landmark positioning)."
   - 추가: "PRE-GENERATION CHECK: Before generating, ask yourself: 'Can I show this finding using only arrows/circles/visual cues?' If the answer is 'no', reconsider the visual approach."
   - 추가: "POST-GENERATION CHECK: Count ALL text elements. If count > 0, regenerate with ZERO text."

2. **S4_EXAM_USER에서 text budget을 "ZERO"로 명시**:
   - 현재: "Default: output NO text labels (labels=0). Exception: at most 1 short label total."
   - 변경: "MANDATORY: labels=0. NO EXCEPTIONS. Use arrows/circles/visual cues only."
   - 추가: "If you find yourself wanting to add a label, use one of these alternatives instead:
     - Arrow pointing to the finding
     - Circle/outline around the finding
     - Color/shade variation
     - Landmark positioning (e.g., 'near the heart' = position near heart silhouette)"

3. **Negative examples 강화**:
   - "FORBIDDEN: 'A', 'B', 'Finding 1', 'Finding 2', 'Left', 'Right', 'L', 'R', 'Anterior', 'Posterior', 'Superior', 'Inferior', any anatomical labels, any measurements, any annotations."
   - "If the image contains ANY text element, it is a FAILURE and must be regenerated."

### 2.2 P0 (Critical): Laterality/Anatomical Error 방지 극대화

**문제**: Laterality errors와 anatomical errors가 지속적으로 발생 (S5R2: 3건 blocking errors 중 2건).

**근거**:
- `grp_92ab25064f`: anatomical_error (L5 vertebral body 위치 오류) + laterality_error
- `grp_6ae1e80a49`: laterality_error (우측 부속기 vs 좌측 부속기)

**S5R3 요구사항**:
1. **S2_SYSTEM에서 laterality requirement를 더 명확히 전달**:
   - "For entities with laterality requirements, include explicit laterality_check in image_hint_v2:
     ```json
     "laterality_check": {
       "required_side": "left|right|bilateral",
       "viewer_perspective": "coronal|axial|sagittal",
       "convention": "For coronal: patient_left = viewer_right. For axial: patient_right = viewer_left."
     }
     ```"

2. **S4_EXAM_SYSTEM에서 laterality validation을 "MANDATORY PRE-CHECK"로 변경**:
   - 현재: "LATERALITY VALIDATION (CRITICAL): For images with laterality requirements..."
   - 변경: "LATERALITY PRE-CHECK (MANDATORY): Before generating, verify:
     - Does IMAGE_HINT specify a laterality requirement? (e.g., 'left SVC', 'right adnexa', 'situs inversus')
     - If yes, what is the required side relative to the viewer?
     - For coronal views: patient's left = viewer's right
     - For axial views: patient's right = viewer's left
     - If laterality is ambiguous or you are uncertain, DO NOT generate. Request clarification or use a non-laterality-dependent view."

3. **S4_EXAM_USER에서 laterality checklist 강화**:
   - "LATERALITY CHECKLIST (MANDATORY):
     - [ ] Does the entity require specific laterality? (Check IMAGE_HINT and card text)
     - [ ] If yes, verify: Is the structure on the correct side relative to viewer?
     - [ ] For coronal: patient's left = viewer's right
     - [ ] For axial: patient's right = viewer's left
     - [ ] If uncertain, use a non-laterality-dependent view or request clarification"

### 2.3 P0 (Critical): View Mismatch 방지 강화

**문제**: View mismatch가 여전히 발생 (S5R2: 11건 S2, 14건 card images).

**근거**:
- `PROMPT_COMPLIANCE_VIEW_MISMATCH`: 8건

**S5R3 요구사항**:
1. **S2_SYSTEM에서 view consistency를 "HARD CONSTRAINT"로 변경**:
   - "MANDATORY: image_hint.view_or_sequence and image_hint_v2.anatomy.orientation MUST be consistent.
     - If view_or_sequence = 'axial', then view_plane MUST be 'axial' (not 'coronal' or 'sagittal').
     - If view_or_sequence = 'coronal', then view_plane MUST be 'coronal' (not 'axial' or 'sagittal').
     - If inconsistency exists, align them before generating image_hint."

2. **S4_EXAM_SYSTEM에서 view alignment을 "PRE-GENERATION CHECK"로 변경**:
   - 현재: "POST-GENERATION COMPLIANCE VALIDATION: View/plane alignment"
   - 변경: "PRE-GENERATION VIEW CHECK (MANDATORY): Before generating, verify:
     - Does view_or_sequence match view_plane/projection?
     - If view_or_sequence = 'axial CT', then the image MUST be an axial cross-section.
     - If view_or_sequence = 'coronal MRI', then the image MUST be a coronal slice.
     - If mismatch exists, DO NOT generate. Align the specifications first."

3. **S4_EXAM_USER에서 view consistency checklist 추가**:
   - "VIEW CONSISTENCY CHECKLIST (MANDATORY):
     - [ ] Does view_or_sequence match view_plane/projection?
     - [ ] If view_or_sequence = 'axial', is the image an axial cross-section?
     - [ ] If view_or_sequence = 'coronal', is the image a coronal slice?
     - [ ] If mismatch exists, regenerate with aligned specifications"

### 2.4 P1 (High): Multi-panel Layout 금지 강화

**문제**: Multi-panel layout이 여전히 발생 (S5R2: 6건 S2, 13건 card images).

**S5R3 요구사항**:
1. **S4_EXAM_SYSTEM에서 multi-panel 금지를 "ABSOLUTE FORBIDDEN"으로 변경**:
   - 현재: "NO-COLLAGE / NO-UI: Do NOT create multi-panel layouts..."
   - 변경: "ABSOLUTELY FORBIDDEN: Multi-panel layouts, collages, split screens, multiple images, side-by-side comparisons, before/after pairs, or any arrangement with 2+ panels. Generate ONLY a single, unified image."

2. **S4_EXAM_USER에서 multi-panel checklist 추가**:
   - "PANEL COUNT CHECKLIST (MANDATORY):
     - [ ] Is the image a single, unified panel? (Not 2+ panels, not split screen, not collage)
     - [ ] If the image contains 2+ panels, it is a FAILURE and must be regenerated as a single panel"

### 2.5 P1 (High): Modality Mismatch 방지

**문제**: S5R2에서 modality_mismatch_text_image가 blocking error로 발생 (1건).

**근거**:
- `grp_1c64967efa`: modality_mismatch_text_image (Nuclear Medicine Bone Scan 질문 vs MRI 이미지)

**S5R3 요구사항**:
1. **S2_SYSTEM에서 modality consistency를 "HARD CONSTRAINT"로 변경**:
   - "MANDATORY: image_hint.modality_preferred and card text modality MUST be consistent.
     - If card text specifies 'Nuclear Medicine Bone Scan', then image MUST be a Nuclear Medicine diagram (not MRI, not CT).
     - If card text specifies 'CT', then image MUST be a CT diagram (not MRI, not XR).
     - If inconsistency exists, align them before generating image_hint."

2. **S4_EXAM_SYSTEM에서 modality validation 추가**:
   - "MODALITY CONSISTENCY CHECK (MANDATORY): Before generating, verify:
     - Does IMAGE_HINT.modality_preferred match the card text modality?
     - If card text says 'Bone Scan' but IMAGE_HINT says 'MRI', DO NOT generate. Align the specifications first.
     - If card text says 'CT' but IMAGE_HINT says 'XR', DO NOT generate. Align the specifications first."

---

## 3. S5R3 구현 체크리스트

### 3.1 S4_EXAM_SYSTEM 변경사항

- [ ] Text budget을 "ZERO TOLERANCE"로 변경
  - "ABSOLUTELY FORBIDDEN: Any text labels..."
  - "PRE-GENERATION CHECK: Can I show this without text?"
  - "POST-GENERATION CHECK: If text_count > 0, regenerate"
- [ ] Laterality validation을 "MANDATORY PRE-CHECK"로 변경
  - "Before generating, verify laterality requirements..."
  - "If uncertain, DO NOT generate"
- [ ] View alignment을 "PRE-GENERATION CHECK"로 변경
  - "Before generating, verify view consistency..."
  - "If mismatch exists, DO NOT generate"
- [ ] Multi-panel 금지를 "ABSOLUTE FORBIDDEN"으로 변경
  - "Generate ONLY a single, unified image"
- [ ] Modality validation 추가
  - "Before generating, verify modality consistency..."

### 3.2 S4_EXAM_USER 변경사항

- [ ] Text budget을 "ZERO"로 명시
  - "MANDATORY: labels=0. NO EXCEPTIONS."
  - "Alternatives to text: arrows/circles/visual cues"
- [ ] Laterality checklist 강화
  - "LATERALITY CHECKLIST (MANDATORY): ..."
- [ ] View consistency checklist 추가
  - "VIEW CONSISTENCY CHECKLIST (MANDATORY): ..."
- [ ] Panel count checklist 추가
  - "PANEL COUNT CHECKLIST (MANDATORY): ..."

### 3.3 S2_SYSTEM 변경사항

- [ ] Laterality requirement를 더 명확히 전달
  - "Include laterality_check in image_hint_v2"
- [ ] View consistency를 "HARD CONSTRAINT"로 변경
  - "MANDATORY: view_or_sequence and view_plane MUST be consistent"
- [ ] Modality consistency를 "HARD CONSTRAINT"로 변경
  - "MANDATORY: modality_preferred and card text modality MUST be consistent"

---

## 4. 예상 효과 (S5R3 목표)

### 4.1 Primary Endpoint 목표

- **S2_any_issue_rate_per_group**: S5R2 0.9% → S5R3 **< 0.5%**
- **Blocking cards**: S5R2 3건 → S5R3 **< 1건**

### 4.2 Key Secondary Endpoints 목표

- **Text budget violations**: S5R2 63건 → S5R3 **< 20건**
- **View mismatch**: S5R2 11-14건 → S5R3 **< 5건**
- **Multi-panel layout**: S5R2 6-13건 → S5R3 **< 2건**
- **Laterality/anatomical errors**: S5R2 3건 → S5R3 **< 1건**
- **Modality mismatch**: S5R2 1건 → S5R3 **0건**

---

## 5. 다음 단계

1. **S5R3 프롬프트 수정**: 위 체크리스트에 따라 S4_EXAM_SYSTEM, S4_EXAM_USER, S2_SYSTEM 수정
2. **레지스트리 업데이트**: `_registry.json`에 S5R3 버전 추가
3. **S5R3 재생성**: S1/S2 → S3 → S4 → S5 실행 (rep1, rep2)
4. **비교 분석**: S5R0 vs S5R3 비교 (prereg endpoint 사용)

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-12-31  
**다음 검토**: S5R3 실행 후

