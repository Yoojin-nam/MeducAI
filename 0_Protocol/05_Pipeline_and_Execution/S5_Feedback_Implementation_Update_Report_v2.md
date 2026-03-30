# S5 피드백 반영 업데이트 보고서 (v2)

**Run Tag**: `DEV_armG_s5loop_diverse_20251229_065718`  
**Arm**: `G`  
**구현 일자**: 2025-12-29  
**기반 문서**: `S5_Feedback_Update_Report_DEV_armG_s5loop_diverse_v2.md`

---

## 1. 개요

최신 S5 리포트 분석 결과를 바탕으로 추가 프롬프트 개선사항을 반영했습니다.

### 업데이트된 프롬프트
- **S1_SYSTEM**: `v13` → `v14`
- **S2_SYSTEM**: `v10` → `v11`
- **S2_USER_ENTITY**: `v10` → `v11`

---

## 2. 반영된 개선사항

### 2.1 S1 프롬프트 (S1_SYSTEM__v14.md)

#### 추가된 규칙

1. **임상적 뉘앙스 명시**
   ```markdown
   - **Clinical Nuance Specification**: When describing diagnostic criteria or imaging signs:
     - Explicitly state age groups (pediatric vs adult) if criteria differ (e.g., "소아에서", "성인에서").
     - For differential diagnoses, acknowledge overlapping imaging signs while emphasizing clinical context that distinguishes them.
     - Example: "Feeding vessel" can appear in multiple conditions; emphasize the clinical context that helps differentiate.
   ```
   - **이슈 코드**: `CLINICAL_NUANCE_PEDIATRIC`, `ACCURACY_NUANCE_001`
   - **목적**: 소아/성인 구분, 감별 진단의 overlapping signs 처리 명확화

2. **수치 일관성**
   ```markdown
   - **Numerical Consistency**: Ensure numerical values (measurements, thresholds, percentages) are consistent across:
     - Different columns in the same row.
     - Related entities in the same group.
     - When citing the same clinical guideline or standard.
   ```
   - **이슈 코드**: `NUMERICAL_INCONSISTENCY`
   - **목적**: 다양한 컨텍스트에서 수치 일관성 유지

3. **진단 기준 업데이트**
   ```markdown
   - **Diagnostic Criteria Updates**: When stating diagnostic criteria, reflect current evidence-based guidelines:
     - If multiple guideline versions exist (e.g., classic Rotterdam vs modern), mention both if space permits.
     - Prefer the most current guideline while acknowledging historical context when educationally relevant.
     - Example: PCOS diagnostic criteria: mention both Rotterdam (>12) and modern guidelines (>20) if applicable.
   ```
   - **이슈 코드**: `GUIDELINE_UPDATE`, `CLARITY_DIAGNOSTIC_CRITERIA`
   - **목적**: 진단 기준의 현대적 가이드라인 반영

### 2.2 S2 프롬프트 (S2_SYSTEM__v11.md, S2_USER_ENTITY__v11.md)

#### 추가된 규칙

1. **Back 설명 완전성 강화** (최우선)
   ```markdown
   - **Back Explanation Completeness**: Ensure the Back explanation includes:
     - All key clinical keywords mentioned in the question or answer (e.g., "Don't touch lesion").
     - Important clinical pearls or rules of thumb (e.g., "3cm rule" regarding proximity to deep venous junctions).
     - Exam-relevant points from the S1 '시험포인트' column when applicable (e.g., if S1 '시험포인트' mentions "GB cancer risk", include this in the explanation).
     - Educational completeness requires comprehensive coverage of clinically relevant information.
   ```
   - **이슈 코드**: `KEYWORD_MISSING`, `MISSING_CLINICAL_PEARL`, `MISSING_EXAM_POINT`
   - **목적**: Back 설명에 핵심 키워드, 임상적 진주, 시험 포인트 포함 보장

2. **Distractor 설명 일치성 강화** (최우선)
   ```markdown
   - **Distractor Explanation Precision**: Each distractor explanation must directly correspond to the exact option text in the `options[]` array.
     - The explanation must address the specific pathology, term, or concept mentioned in that option.
     - Do NOT use generic explanations that could apply to multiple options.
     - Example: If option A says "Ventricular catheter proximal", the explanation must specifically address "proximal" vs "distal" terminology.
   ```
   - **이슈 코드**: `DISTRACTOR_MISMATCH`, `DISTRACTOR_EXPLANATION_MISMATCH`, `DISTRACTOR_RATIONALE_MISMATCH`
   - **목적**: Distractor 설명이 option text와 정확히 일치하도록 보장

3. **질문 명확성 강화** (최우선)
   ```markdown
   - **Question Clarity**: Avoid vague abstract terms like '개념' (concept) in questions.
     - Use specific terms like '진단 범주' (diagnostic category), '임상적 상태' (clinical condition), '병리학적 소견' (pathological finding) as appropriate.
     - Ensure the question clearly indicates what type of answer is expected.
   ```
   - **이슈 코드**: `VAGUE_QUESTION`
   - **목적**: 모호한 추상적 표현 피하기

4. **용어 선택 정밀도** (우선순위 중간)
   ```markdown
   - **Nomenclature Precision**: Use terminology that matches the specific characteristics described (size, location, age, imaging characteristics).
     - Example: For bone lesions, if size is 2.5cm, use "NOF" (Non-ossifying fibroma) terminology rather than generic terms.
     - Consider size, location, age, and imaging characteristics when selecting appropriate medical terminology.
   ```
   - **이슈 코드**: `NOMENCLATURE_PRECISION`
   - **목적**: 병변 특성에 따른 정확한 용어 선택

5. **의학 용어 번역 정확성** (기존 규칙 강화)
   ```markdown
   - Ensure medical terms like 'intramedullary' are correctly translated to '수내' or '골수 내' instead of '수중'.
   ```
   - **이슈 코드**: `TYPO_TERMINOLOGY`
   - **목적**: 의학 용어 번역 오류 방지

6. **옵션 용어 정밀도** (추가)
   ```markdown
   - Ensure precise terminology in options (e.g., "Ventricular catheter proximal" vs "Peritoneal catheter distal").
   ```
   - **이슈 코드**: `TERMINOLOGY_PRECISION`
   - **목적**: MCQ 옵션에서 용어 정밀도 향상

---

## 3. 변경 사항 상세

### 3.1 S1_SYSTEM__v14.md

**변경 위치**: `MEDICAL SAFETY & STYLE (HARD)` 섹션

**추가 내용**:
- Clinical Nuance Specification 규칙
- Numerical Consistency 규칙
- Diagnostic Criteria Updates 규칙

**기존 규칙 유지**:
- Terminology Specificity (기존)
- Terminology Modernization (기존)
- Clinical Guideline Updates (기존)

### 3.2 S2_SYSTEM__v11.md

**변경 위치**: `RISK CONTROL (CRITICAL)` 섹션

**추가 내용**:
- Nomenclature Precision 규칙

**기존 규칙 유지**:
- Terminology Context (기존)
- MCQ Option Format (기존)
- Distractor Completeness (기존)
- Korean Medical Terminology (기존)
- Question-Answer Type Alignment (기존)
- Entity ID Mapping (기존)
- Anatomical Description Precision (기존)

### 3.3 S2_USER_ENTITY__v11.md

**변경 위치**:
1. `[Q2: MCQ, 1교시 스타일 개념 이해 기반]` 섹션 (Front format)
2. `Back format` 섹션
3. `options:` 설명 부분

**추가 내용**:
- Question Clarity 규칙 (Front format에 추가)
- Back Explanation Completeness 규칙 (Back format에 추가)
- Distractor Explanation Precision 규칙 (Back format에 추가)
- 의학 용어 번역 정확성 (Terminology discipline에 추가)
- 옵션 용어 정밀도 (options 설명에 추가)

---

## 4. 프롬프트 레지스트리 업데이트

**파일**: `3_Code/prompt/_registry.json`

**변경 사항**:
```json
{
  "S1_SYSTEM": "S1_SYSTEM__v14.md",  // v13 → v14
  "S2_SYSTEM": "S2_SYSTEM__v11.md",  // v10 → v11
  "S2_USER_ENTITY": "S2_USER_ENTITY__v11.md"  // v10 → v11
}
```

---

## 5. 예상 효과

### 즉시 개선 예상 항목
1. **Back 설명 완전성**: 키워드/임상 진주/시험 포인트 누락 → 0건 예상
2. **Distractor 설명 일치성**: Option text와 불일치 → 0건 예상
3. **질문 명확성**: 모호한 추상적 표현 → 0건 예상

### 단기 개선 예상 항목
1. **임상적 뉘앙스**: 소아/성인 구분, overlapping signs 처리 개선
2. **수치 일관성**: 다양한 컨텍스트에서 수치 일관성 개선
3. **진단 기준 업데이트**: 현대적 가이드라인 반영 개선
4. **용어 선택 정밀도**: 병변 특성에 따른 용어 선택 개선

---

## 6. 검증 계획

### 다음 단계
1. **재생성**: 업데이트된 프롬프트로 S1/S2 재생성
2. **재검증**: S5 validation 재실행
3. **비교 분석**: 이전 리포트와 비교하여 개선율 측정
4. **모니터링**: 특정 이슈 코드의 발생 빈도 추적

### 성공 지표
- `KEYWORD_MISSING`, `MISSING_CLINICAL_PEARL`, `MISSING_EXAM_POINT`: 4건 → 0건
- `DISTRACTOR_MISMATCH`, `DISTRACTOR_EXPLANATION_MISMATCH`: 3건 → 0건
- `VAGUE_QUESTION`: 1건 → 0건
- `NOMENCLATURE_PRECISION`: 1건 → 0건
- `CLINICAL_NUANCE_PEDIATRIC`, `NUMERICAL_INCONSISTENCY`: 개선 예상

---

## 7. 참고 문서

- **업데이트 보고서**: `S5_Feedback_Update_Report_DEV_armG_s5loop_diverse_v2.md`
- **이전 분석**: `S5_Report_Analysis_and_Improvements_DEV_armG_s5loop_diverse.md`
- **이전 반영**: `0_Protocol/05_Pipeline_and_Execution/archived/2025-12/S5_Feedback_Implementation_Report_DEV_armG_s5loop_diverse.md`
- **S5 리포트**: `2_Data/metadata/generated/DEV_armG_s5loop_diverse_20251229_065718/reports/s5_report__armG.md`
- **프롬프트 위치**:
  - S1: `3_Code/prompt/S1_SYSTEM__v14.md`
  - S2: `3_Code/prompt/S2_SYSTEM__v11.md`, `3_Code/prompt/S2_USER_ENTITY__v11.md`

---

## 8. 버전 히스토리

- **v14 (S1)**: S5 피드백 v2 반영 - 임상적 뉘앙스, 수치 일관성, 진단 기준 업데이트
- **v11 (S2)**: S5 피드백 v2 반영 - Back 설명 완전성, Distractor 일치성, 질문 명확성, 용어 선택 정밀도

---

**구현 완료**: 2025-12-29

