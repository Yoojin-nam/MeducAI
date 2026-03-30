# S5R1 분석 및 S5R2 개선 계획 (Phase 2 Analysis)

- **목적**: S5R0 vs S5R1 비교 분석을 통해 S5R1에서의 개선 효과를 측정하고, S5R2에서 추가로 개선해야 할 포인트를 식별
- **근거 소스**:
  - S5R0 (baseline): `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1`, `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_203653__rep2`
  - S5R1 (after 1st improvement): `DEV_armG_mm_S5R1_after_postFix_20251230_113754__rep1`, `DEV_armG_mm_S5R1_after_postFix_20251230_140936__rep2`
- **분석 일자**: 2025-12-30
- **다음 단계**: S5R2 프롬프트 개선 및 재생성

---

## 1. Executive Summary: S5R0 vs S5R1 주요 변화

### 1.1 Primary Endpoint 변화 (S2_any_issue_rate_per_group)

**S5R0 (baseline)**:
- rep1: S2 blocking cards 1/330 (0.3%), S2 total 330
- rep2: S2 blocking cards 3/348 (0.9%), S2 total 348
- **평균 blocking rate**: ~0.6%

**S5R1 (after improvement)**:
- rep1: S2 blocking cards 4/350 (1.1%), S2 total 350
- rep2: S2 blocking cards 1/342 (0.3%), S2 total 342
- **평균 blocking rate**: ~0.7%

**결과**: **S5R1에서 blocking rate가 약간 증가** (0.6% → 0.7%). 이는 예상과 다른 결과로, S5R1 프롬프트 변경이 일부 regressive effect를 가져왔을 가능성.

### 1.2 Key Secondary Endpoints 변화

#### A. Image Prompt Compliance (중요 지표)

**S5R0**:
- rep1: mean prompt compliance 0.94
- rep2: mean prompt compliance 0.91
- **평균**: 0.925

**S5R1**:
- rep1: mean prompt compliance 0.88
- rep2: mean prompt compliance 0.89
- **평균**: 0.885

**결과**: **Prompt compliance가 감소** (0.925 → 0.885, 약 -4.3%). 이는 S5R1에서 이미지 생성이 프롬프트 제약을 덜 따르고 있음을 시사.

#### B. Image Text Budget Violations (excessive_text)

**S5R0**:
- rep1: excessive_text issues 40 (S2), 71 (card images)
- rep2: excessive_text issues 49 (S2), 79 (card images)

**S5R1**:
- rep1: excessive_text issues 57 (S2), 86 (card images)
- rep2: excessive_text issues 63 (S2), 82 (card images)

**결과**: **Text budget violations가 증가** (S2: ~45 → ~60, 이미지: ~75 → ~84). S5R1에서 "max 1 label" 정책이 더 강화되었지만, 실제 생성물에서는 오히려 더 많은 텍스트가 생성되고 있음.

#### C. Technical Accuracy

**S5R0**:
- rep1: S2 mean TA 0.99, Image anatomical accuracy 0.99
- rep2: S2 mean TA 0.98, Image anatomical accuracy 0.98

**S5R1**:
- rep1: S2 mean TA 0.98, Image anatomical accuracy 0.97
- rep2: S2 mean TA 0.99, Image anatomical accuracy 0.99

**결과**: **Technical accuracy는 대체로 유지** (0.98-0.99 수준). 큰 변화 없음.

#### D. Educational Quality

**S5R0**:
- rep1: S2 mean EQ 4.93, Image quality 4.93
- rep2: S2 mean EQ 4.92, Image quality 4.92

**S5R1**:
- rep1: S2 mean EQ 4.89, Image quality 4.87
- rep2: S2 mean EQ 4.96, Image quality 4.93

**결과**: **Educational quality는 약간 변동** (rep1에서 감소, rep2에서 증가). Replicate 간 변동성이 있음.

### 1.3 S1 Blocking Tables 변화

**S5R0**: 0/11 blocking tables (both replicates)
**S5R1**: rep1 1/11, rep2 0/11

**결과**: rep1에서 1개 blocking table이 새로 발생 (`grp_1c64967efa`). S1 품질이 약간 악화되었을 가능성.

---

## 2. Issue Taxonomy 변화 분석

### 2.1 Top Issue Types 변화 (S2 + Card Images)

#### S5R0 Top Issues:
1. **excessive_text**: 40-49 (S2), 71-79 (images)
2. **view_mismatch**: 15-17 (S2), 21-24 (images)
3. **text_image_mismatch**: 6 (S2), 4-5 (images)
4. **multi_panel_layout**: 3-6 (S2), 5-9 (images)

#### S5R1 Top Issues:
1. **excessive_text**: 57-63 (S2), 82-86 (images) ⚠️ **증가**
2. **view_mismatch**: 14-19 (S2), 19-22 (images) → **약간 감소**
3. **finding_contradiction**: 1-5 (S2), 5 (images) → **새로 등장**
4. **text_image_mismatch**: 3-5 (S2), 3 (images) → **약간 감소**

**핵심 발견**: 
- **excessive_text가 오히려 증가**: S5R1에서 "max 1 label" 정책을 강화했지만, 실제 생성물에서는 더 많은 텍스트가 생성됨. 이는 프롬프트의 "negative constraint"가 충분히 강하지 않거나, 이미지 생성 모델이 제약을 무시하는 패턴이 있을 수 있음.
- **view_mismatch는 약간 개선**: S5R1의 view 정합 규칙이 일부 효과를 보임.

### 2.2 Top Issue Codes 변화 (S3_PROMPT target)

#### S5R0 Top Issue Codes (S3_PROMPT):
1. `IMAGE_TEXT_EXCESSIVE`: 15-19
2. `PROMPT_COMPLIANCE_VIEW_MISMATCH`: 5-17
3. `IMAGE_TEXT_COUNT_EXCEEDED`: 6-19
4. `IMAGE_TEXT_BUDGET_EXCEEDED`: 3-9

#### S5R1 Top Issue Codes (S3_PROMPT):
1. `IMAGE_TEXT_EXCESSIVE`: 14-16 ⚠️ **유지/증가**
2. `IMAGE_TEXT_BUDGET_EXCEEDED`: 8-25 ⚠️ **대폭 증가**
3. `IMAGE_EXCESSIVE_TEXT`: 14-16 ⚠️ **증가**
4. `PROMPT_COMPLIANCE_VIEW_MISMATCH`: 4-11 → **약간 감소**
5. `IMAGE_TEXT_POLICY_VIOLATION`: 2-10 ⚠️ **새로 등장**

**핵심 발견**:
- **Text budget 관련 issue codes가 모두 증가**: `IMAGE_TEXT_BUDGET_EXCEEDED`가 8-25로 대폭 증가. S5R1에서 정책을 강화했지만, 실제 생성물에서는 더 많은 위반이 발생.
- **Policy violation이 새로 등장**: `IMAGE_TEXT_POLICY_VIOLATION`이 rep1에서 10건, rep2에서 2건 발생. 이는 프롬프트 정책과 실제 생성물 간의 불일치가 있음을 시사.

---

## 3. Blocking Errors 분석 (S5R1에서 새로 발생한 것)

### 3.1 S5R1 rep1 Blocking Errors (4건)

1. **`grp_c63d9a24cf` / `DERIVED:19f112ea8966__Q1__0`**: 
   - **finding_contradiction**: 이미지가 "NOT ON IMAGE ANNOTATION"으로 라벨링했지만, KIAMI 규정상 kVp/mAs는 영상 내 annotation으로 필수 표시되어야 함.
   - **S5R2 개선 포인트**: S2에서 regulatory requirement를 더 명확히 전달하고, S3/S4에서 "required annotations"를 강제.

2. **`grp_2c6fda981d` / `DERIVED:5f18f78cd7cb__Q1__0`**:
   - **anatomical_error**: Chondroblastoma가 epiphysis에 위치해야 하는데, 이미지에서는 metaphysis에 위치함.
   - **S5R2 개선 포인트**: S2에서 entity의 characteristic location을 더 명확히 전달하고, S3에서 location constraint를 강제.

3. **`grp_afe6e9c0b9` / `DERIVED:cd52fab65bcc__Q1__0`**:
   - **laterality_error**: Persistent Left SVC가 환자의 우측(뷰어의 좌측)에 위치함. 표준 coronal diagram에서는 좌측이 뷰어의 우측에 있어야 함.
   - **minor excessive_text**: 2개 라벨이 생성됨 (max 1 정책 위반).
   - **S5R2 개선 포인트**: Laterality self-check를 더 강화하고, 라벨 개수 제한을 더 엄격히 강제.

4. **`grp_afe6e9c0b9` / `DERIVED:64d70ae9529d__Q2__1`**:
   - **anatomical_error**: L-TGA에서 morphological RV가 환자의 좌측에 있어야 하는데, 이미지에서는 우측에 위치함.
   - **S5R2 개선 포인트**: 복잡한 해부학적 변형(ventricular inversion)에 대한 laterality 규칙을 더 명확히 전달.

### 3.2 S5R1 rep2 Blocking Errors (1건)

1. **`grp_afe6e9c0b9` / `DERIVED:0673f8e15b8d__Q1__0`**:
   - **anatomical_error**: Situs inversus가 요구되지만, 이미지는 normal anatomy (Situs solitus)를 보여줌.
   - **S5R2 개선 포인트**: S2에서 "inverted/mirrored" anatomy를 더 명확히 전달하고, S3에서 laterality inversion을 강제.

### 3.3 S5R0 vs S5R1 Blocking Error 비교

**S5R0 blocking errors**:
- rep1: 1건 (laterality_error in `grp_afe6e9c0b9`)
- rep2: 3건 (laterality_error, finding_contradiction, diagnosis_mismatch)

**S5R1 blocking errors**:
- rep1: 4건 (finding_contradiction, anatomical_error×2, laterality_error)
- rep2: 1건 (anatomical_error)

**결과**: rep1에서 blocking errors가 증가 (1 → 4), rep2에서는 감소 (3 → 1). Replicate 간 변동성이 크지만, 전반적으로 laterality/anatomical errors가 지속적으로 발생.

---

## 4. S5R2 개선 포인트 (Priority 기반)

### 4.1 P0 (Critical): Text Budget Enforcement 강화

**문제**: S5R1에서 "max 1 label" 정책을 강화했지만, 실제 생성물에서는 오히려 더 많은 텍스트가 생성됨.

**근거**:
- `IMAGE_TEXT_BUDGET_EXCEEDED`: 8-25 (S5R1) vs 3-9 (S5R0) → **대폭 증가**
- `IMAGE_TEXT_EXCESSIVE`: 14-16 (S5R1) vs 15-19 (S5R0) → **유지/증가**
- `IMAGE_TEXT_POLICY_VIOLATION`: 2-10 (S5R1) → **새로 등장**

**S5R2 요구사항**:
1. **S3_PROMPT에서 text budget을 "hard constraint + validation"으로 변경**:
   - 현재: "max 1 label" (권고 수준)
   - 변경: "ABSOLUTELY NO TEXT LABELS unless explicitly required. If a label is absolutely necessary, use exactly 1 label, maximum 3 words. Any image with 2+ labels will be REJECTED."
   - 추가: "Before generating, count the number of text labels. If count > 1, regenerate with zero labels."

2. **S4_EXAM_SYSTEM에서 negative examples 추가**:
   - "DO NOT generate images with multiple labels, captions, or annotations."
   - "If the image contains 2+ text elements, it violates the policy and must be regenerated."

3. **S4_EXAM_USER에서 explicit validation step 추가**:
   - "After generation, verify: text_count <= 1. If violated, regenerate."

### 4.2 P0 (Critical): Laterality/Anatomical Error 방지 강화

**문제**: Laterality errors와 anatomical errors가 지속적으로 발생 (S5R0: 4건, S5R1: 5건).

**근거**:
- S5R1 blocking errors 중 4/5건이 laterality/anatomical error
- `grp_afe6e9c0b9`에서 반복적으로 laterality errors 발생

**S5R2 요구사항**:
1. **S2_SYSTEM에서 laterality requirement를 더 명확히 전달**:
   - "For entities with laterality requirements (e.g., Persistent Left SVC, Situs inversus, L-TGA), explicitly specify the required anatomical orientation in image_hint."
   - "Include laterality_check: {required_side: 'left/right', viewer_perspective: 'coronal/axial'} in image_hint_v2."

2. **S3_PROMPT에서 laterality self-check 강화**:
   - "Before generating, verify: Does the image show the correct laterality? For coronal views: patient's left = viewer's right. For axial views: patient's right = viewer's left."
   - "If laterality is ambiguous or incorrect, regenerate with explicit laterality markers."

3. **S4_EXAM_SYSTEM에서 laterality validation 추가**:
   - "For images with laterality requirements, verify that structures are on the correct side relative to the viewer's perspective."
   - "Common errors: Left SVC on wrong side, ventricular inversion not shown, situs inversus not mirrored."

### 4.3 P1 (High): View Mismatch 추가 개선

**문제**: View mismatch는 약간 개선되었지만 여전히 발생 (S5R0: 15-17, S5R1: 14-19).

**S5R2 요구사항**:
1. **S2_SYSTEM에서 view consistency check 강화**:
   - "Ensure image_hint.view_or_sequence and image_hint_v2.anatomy.orientation are consistent."
   - "If view_or_sequence = 'axial', then view_plane must be 'axial' (not 'coronal' or 'sagittal')."

2. **S3_PROMPT에서 view alignment validation 추가**:
   - "Before generating, check: Does view_or_sequence match view_plane? If not, align them."
   - "For didactic diagrams, prefer 'schematic' or 'four-chamber' over conflicting view specifications."

### 4.4 P1 (High): Finding Contradiction 방지

**문제**: S5R1에서 finding_contradiction이 새로 등장 (rep1: 5건, rep2: 1건).

**근거**:
- `grp_c63d9a24cf`: 이미지가 "NOT ON IMAGE"로 라벨링했지만, 실제로는 "ON IMAGE"가 필수.

**S5R2 요구사항**:
1. **S2_SYSTEM에서 regulatory/compliance requirements를 더 명확히 전달**:
   - "For entities with regulatory requirements (e.g., KIAMI phantom image requirements), explicitly state what must be visible in the image."
   - "Include compliance_check: {required_elements: [...]} in image_hint_v2."

2. **S3_PROMPT에서 contradiction check 추가**:
   - "Before generating, verify: Does the image show what the card text requires? If the text says 'X must be visible', the image must show X, not label it as 'NOT VISIBLE'."

### 4.5 P2 (Medium): Prompt Compliance 개선

**문제**: Prompt compliance가 감소 (0.925 → 0.885).

**S5R2 요구사항**:
1. **S4_EXAM_SYSTEM에서 compliance validation 강화**:
   - "After generation, verify compliance with all constraints: text_budget, view_plane, laterality, panel_count."
   - "If any constraint is violated, regenerate."

2. **S4_EXAM_USER에서 explicit compliance checklist 추가**:
   - "Checklist: [ ] text_count <= 1, [ ] view matches specification, [ ] laterality correct, [ ] single panel."

---

## 5. S5R2 구현 체크리스트

### 5.1 S3_PROMPT 변경사항

- [ ] Text budget을 "hard constraint + validation"으로 변경
  - "ABSOLUTELY NO TEXT LABELS unless explicitly required"
  - "Before generating, count text labels. If count > 1, regenerate with zero labels."
- [ ] Laterality self-check 강화
  - "For coronal views: patient's left = viewer's right"
  - "For axial views: patient's right = viewer's left"
  - "If laterality is ambiguous, regenerate with explicit markers."
- [ ] View alignment validation 추가
  - "Check: Does view_or_sequence match view_plane? If not, align them."
- [ ] Contradiction check 추가
  - "Verify: Does the image show what the card text requires?"

### 5.2 S4_EXAM_SYSTEM 변경사항

- [ ] Negative examples 추가 (multiple labels 금지)
- [ ] Laterality validation 추가
- [ ] Compliance validation 강화 (post-generation check)

### 5.3 S4_EXAM_USER 변경사항

- [ ] Explicit validation step 추가 (text_count <= 1)
- [ ] Compliance checklist 추가

### 5.4 S2_SYSTEM 변경사항

- [ ] Laterality requirement를 더 명확히 전달
  - "Include laterality_check in image_hint_v2"
- [ ] Regulatory/compliance requirements 전달
  - "Include compliance_check in image_hint_v2"
- [ ] View consistency check 강화
  - "Ensure view_or_sequence and view_plane are consistent"

---

## 6. 예상 효과 (S5R2 목표)

### 6.1 Primary Endpoint 목표

- **S2_any_issue_rate_per_group**: S5R1 0.7% → S5R2 **< 0.5%**
- **Blocking cards**: S5R1 평균 2.5건 → S5R2 **< 1건**

### 6.2 Key Secondary Endpoints 목표

- **Image prompt compliance**: S5R1 0.885 → S5R2 **> 0.92**
- **Text budget violations**: S5R1 ~60 (S2), ~84 (images) → S5R2 **< 40 (S2), < 60 (images)**
- **View mismatch**: S5R1 14-19 → S5R2 **< 10**
- **Laterality/anatomical errors**: S5R1 5건 → S5R2 **< 2건**

---

## 7. 다음 단계

1. **S5R2 프롬프트 수정**: 위 체크리스트에 따라 S3_PROMPT, S4_EXAM_SYSTEM, S4_EXAM_USER, S2_SYSTEM 수정
2. **레지스트리 업데이트**: `_registry.json`에 S5R2 버전 추가
3. **S5R2 재생성**: S1/S2 → S3 → S4 → S5 실행 (rep1, rep2)
4. **비교 분석**: S5R0 vs S5R2 비교 (prereg endpoint 사용)

---

## 부록: 상세 Issue Code 비교표

### A. S3_PROMPT Target Issue Codes

| Issue Code | S5R0 (rep1) | S5R0 (rep2) | S5R1 (rep1) | S5R1 (rep2) | 변화 |
|------------|-------------|-------------|-------------|-------------|------|
| IMAGE_TEXT_EXCESSIVE | 15 | 19 | 14 | 16 | 약간 감소 |
| IMAGE_TEXT_BUDGET_EXCEEDED | 3 | 8 | 10 | 25 | **대폭 증가** |
| IMAGE_EXCESSIVE_TEXT | 3 | 3 | 16 | 14 | **대폭 증가** |
| IMAGE_TEXT_COUNT_EXCEEDED | 6 | 19 | 8 | 9 | 약간 감소 |
| PROMPT_COMPLIANCE_VIEW_MISMATCH | 5 | 17 | 11 | 9 | 약간 감소 |
| IMAGE_TEXT_POLICY_VIOLATION | - | - | 10 | 2 | **새로 등장** |

### B. Blocking Errors 비교

| Run | S5R0 Blocking | S5R1 Blocking | 변화 |
|-----|--------------|---------------|------|
| rep1 | 1 | 4 | **증가** |
| rep2 | 3 | 1 | 감소 |
| 평균 | 2 | 2.5 | 약간 증가 |

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-12-30  
**다음 검토**: S5R2 실행 후

