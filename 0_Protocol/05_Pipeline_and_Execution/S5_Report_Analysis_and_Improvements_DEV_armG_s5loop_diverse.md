# S5 리포트 분석 및 개선점 정리

**Run Tag**: `DEV_armG_s5loop_diverse_20251229_065718`  
**Arm**: `G`  
**분석 일자**: 2025-12-29  
**S5 리포트**: `2_Data/metadata/generated/DEV_armG_s5loop_diverse_20251229_065718/reports/s5_report__armG.md`

---

## 1. 전체 요약

### 검증 현황
- **S1 검증 그룹**: 11개
- **S2 검증 카드**: 334개
- **Blocking Error**: 0개 (S1: 0/11, S2: 0/334)
- **평균 Technical Accuracy**: S1 0.95, S2 1.00
- **평균 Educational Quality**: S1 4.91, S2 4.98

### 이슈 현황
- **S1 총 이슈**: 17개 (11개 그룹 중)
- **S2 총 이슈**: 18개 (334개 카드 중, 30개 카드에 이슈)
- **이슈 발생률**: S1 1.5개/그룹, S2 5.4% (30/334 카드)

---

## 2. 주요 이슈 카테고리 분석

### 2.1 S1 Table 이슈

#### 이슈 타입 분포 (상위)
1. **terminology** (7건): 용어 정확성/일관성 문제
2. **clarity** (5건): 명확성/가독성 문제
3. **clarification** (3건): 설명 보완 필요
4. **guideline_update** (2건): 가이드라인 업데이트 반영 필요
5. **completeness** (2건): 내용 완전성 문제

#### 주요 이슈 코드
- `AMBIGUOUS_TERMINOLOGY` (4건): 모호한 용어 사용
- `CLINICAL_NUANCE` (4건): 임상적 뉘앙스 정확성
- `TERM_PRECISION` (2건): 용어 정밀도
- `TERM_UPDATE` (2건): 용어 현대화 필요

#### 핵심 개선 영역
- **용어 정확성**: 7건 (가장 많음)
- **임상 가이드라인 반영**: 4건
- **명확성/가독성**: 5건

### 2.2 S2 Cards 이슈

#### 이슈 타입 분포 (상위)
1. **terminology** (7건): 용어 정확성 문제
2. **clarity** (3건): 명확성 문제
3. **consistency** (3건): 일관성 문제
4. **terminology_error** (2건): 용어 오류
5. **formatting** (2건): 형식 문제

#### 주요 이슈 코드
- `TERMINOLOGY_PRECISION` (4건): 용어 정밀도
- `TERMINOLOGY_MISMATCH` (2건): 용어 불일치
- `REDUNDANT_PREFIX` (2건): MCQ 옵션 중복 접두사
- `RATIONALE_*` (4건): 오답 설명 구조/일치성 문제

#### 핵심 개선 영역
- **용어 정확성**: 7건 (가장 많음)
- **MCQ 구조/일관성**: 6건 (formatting + rationale)
- **명확성**: 3건

---

## 3. 구체적 개선점 (Patch Backlog 기반)

### 3.1 S1 Table 개선점

#### 우선순위 1: 용어 정확성 및 현대화
1. **용어 혼동 방지**
   - `TERM_CONFUSION`: "Double stripe sign"은 HPOA 전용, Shin Splints에 사용 금지
   - `TERM_PRUNING_VS_OLIGEMIA`: "Pruning"은 Pulmonary Hypertension/Eisenmenger 전용, 감소된 폐혈류는 "oligemia" 사용

2. **용어 현대화**
   - `OUTDATED_TERMINOLOGY`: 구식 용어 업데이트 필요
   - `TERM_WHO_ALIGNMENT`: WHO 분류에 맞춘 용어 사용 (예: Osteofibrous dysplasia)

3. **임상 가이드라인 반영**
   - `OUTDATED_GUIDELINE`: Porcelain GB 암 위험도 현대적 추정치 반영
   - `CLINICAL_NUANCE_UPDATE`: 임상적 뉘앙스 업데이트

#### 우선순위 2: 명확성 및 완전성
1. **모호한 표현 개선**
   - `AMBIGUOUS_TERMINOLOGY` (4건): 모호한 용어 명확화
   - `AMBIGUOUS_PHRASING`: 모호한 문구 개선

2. **내용 완전성**
   - `MISSING_SCAN_RANGE`: 스캔 범위 정보 추가
   - `MISSING_ENTITY`: 누락된 entity 추가

#### 우선순위 3: 물리학/규제 정확성
1. **물리학 용어**
   - `PHYSICS_MTF_VALUE`: MTF 값 정확성
   - `PHYSICS_NOISE_UNIT`: 노이즈 단위 정확성

2. **규제 한계**
   - `REGULATORY_LIMIT_PRECISION`: 규제 한계값 정밀도

### 3.2 S2 Cards 개선점

#### 우선순위 1: 용어 정확성 (가장 중요)
1. **QC/행정 용어 vs 임상 용어 구분**
   - `TERMINOLOGY_PRECISION` (4건):
     - QC/행정 결과: "진단" 대신 "판정", "결과", "평가 결과", "지적 사항" 사용
     - 예: "평가 결과" 또는 "지적 사항" (administrative/QC compliance questions)
   
2. **의학 용어 정확성**
   - `TERM_UNCONVENTIONAL`: "polyposis" → "용종증" (not "유종")
   - `TERMINOLOGY_TYPO`: "기관지" (bronchus) vs "동맥" (artery) 혼동 방지
   - `TERMINOLOGY_PRECISION`: "골간단" (Metaphysis) 일관성

3. **용어 일치성**
   - `TERMINOLOGY_MISMATCH`: 해부학 용어가 논의하는 장기와 일치해야 함 (Brain vs Chest)
   - `TERM_MISMATCH`: 질문의 성격과 답변의 성격 일치 (test/procedure vs diagnosis)

#### 우선순위 2: MCQ 구조 및 일관성
1. **MCQ 옵션 형식**
   - `REDUNDANT_PREFIX` (2건): MCQ 옵션 생성 시 선택지 문자(A, B, C...) 중복 접두사 방지
   - `MCQ_OPTION_INCOMPLETE`: 정답 옵션이 질문의 모든 구성요소를 다뤄야 함

2. **오답 설명 (Rationale) 구조**
   - `MISSING_DISTRACTOR_EXPLANATION`: 모든 MCQ 오답 선택지(A-E)를 "오답 포인트" 섹션에서 다뤄야 함
   - `RATIONALE_LABEL_MISMATCH`: "오답 포인트" 섹션의 각 설명이 해당 문자 옵션과 직접 대응되어야 함
   - `RATIONALE_STRUCTURE`: 오답 설명 구조 일관성
   - `RATIONALE_MISMATCH`: Back 필드의 오답 설명이 제공된 옵션 텍스트와 정확히 일치해야 함

3. **설명 정렬**
   - `EXP_MISALIGN`: 오답 설명이 해당 옵션의 구체적 내용을 직접 반박해야 함
   - `DISTRACTOR_EXPLANATION_MISMATCH`: "오답 포인트"의 Option E 설명이 MCQ options 필드의 텍스트와 일치해야 함

#### 우선순위 3: 명확성 및 정확성
1. **진단 vs 소견 구분**
   - `CLARITY_DIAGNOSIS_VS_FINDING`: 'Answer' 필드가 특징적 소견을 기저 병리학적 진단과 명시적으로 연결해야 함

2. **해부학적 정밀도**
   - `ANATOMICAL_PRECISION`: PA view에서 우심장 확장의 방사선학적 소견 명확화

3. **내용 일치성**
   - `ENTITY_MISMATCH`: 카드가 'Answer' 필드와 가장 일치하는 S1 행에 매핑되어야 함
   - `CRITERIA_MISATTRIBUTION`: 골수강 연골성 병변(연골종)의 진단 기준이 다른 병변과 혼동되지 않아야 함

---

## 4. 프롬프트 개선 권장사항

### 4.1 S1 프롬프트 (S1_SYSTEM__v12.md)

#### 추가할 규칙
1. **용어 혼동 방지**
   ```markdown
   - **Terminology Specificity**: Reserve specific radiological signs and terms
     for their correct clinical entities.
     - Example: "Double stripe sign" is specific to **Hypertrophic Pulmonary
       Osteoarthropathy (HPOA)**. Do NOT use this term for other conditions
       like Shin Splints.
     - Example: "Pruning" is reserved for **Pulmonary Hypertension/Eisenmenger
       syndrome**. For decreased pulmonary blood flow in other contexts, use
       "oligemia" instead.
   ```

2. **용어 현대화**
   ```markdown
   - **Terminology Modernization**: Use current WHO classification and modern
     medical terminology.
     - Example: Use "Osteofibrous dysplasia" for tibial lesions (modern WHO
       classification).
     - Avoid outdated terms; if necessary, append "(formerly ...)" to current
       accepted term.
   ```

3. **임상 가이드라인 반영**
   ```markdown
   - **Clinical Guideline Updates**: Reflect current evidence-based guidelines
     for risk estimates, prevalence, etc.
     - Example: Porcelain GB cancer risk should reflect modern lower estimates
       while retaining exam relevance.
   ```

### 4.2 S2 프롬프트 (S2_SYSTEM__v9.md, S2_USER_ENTITY__v9.md)

#### 추가할 규칙
1. **QC/행정 용어 vs 임상 용어 구분**
   ```markdown
   - **Terminology Context**: Distinguish between clinical and administrative/QC
     terminology.
     - For QC/administrative outcomes: Use "판정", "결과", "평가 결과", or
       "지적 사항" instead of "진단".
     - For clinical questions: Use "진단" appropriately.
     - Example: QC compliance questions should ask for "평가 결과" or "지적
       사항", not "진단".
   ```

2. **MCQ 옵션 형식**
   ```markdown
   - **MCQ Option Format**: When generating MCQ options, do NOT prepend the
     option letter (A, B, C, D, E) if it is already part of the option string.
     - The options[] array should contain clean text without redundant prefixes.
     - Example: Option should be "CTDIw" not "A. CTDIw" (the letter is added
       by the display system).
   ```

3. **오답 설명 완전성**
   ```markdown
   - **Distractor Completeness**: For MCQ cards with 5 options (A-E), ensure
     ALL distractors are addressed in the "오답 포인트" section.
     - Each distractor explanation must directly correspond to the lettered
       option (A, B, C, D, E).
     - The explanation should directly refute the specific content of the
       corresponding option.
   ```

4. **의학 용어 정확성**
   ```markdown
   - **Korean Medical Terminology**: Use standard Korean medical terms.
     - Example: "polyposis" → "용종증" (not "유종")
     - Example: "Metaphysis" → "골간단" (consistent spelling)
     - Example: "bronchus" → "기관지" (not "동맥")
   ```

5. **질문-답변 정렬**
   ```markdown
   - **Question-Answer Type Alignment**: Ensure the question prompt matches
     the nature of the answer.
     - For test/procedure/equipment questions: Do not ask for a "diagnosis".
     - For diagnostic questions: Use "진단" appropriately.
   ```

---

## 5. 우선순위별 액션 아이템

### 즉시 적용 (High Priority)
1. ✅ **S2 프롬프트**: QC/행정 용어 vs 임상 용어 구분 규칙 추가
2. ✅ **S2 프롬프트**: MCQ 옵션 중복 접두사 방지 규칙 추가
3. ✅ **S2 프롬프트**: 오답 설명 완전성 규칙 강화
4. ✅ **S1 프롬프트**: 용어 혼동 방지 규칙 추가 (Double stripe sign, Pruning)

### 단기 개선 (Medium Priority)
1. **S1 프롬프트**: 용어 현대화 규칙 추가 (WHO 분류 반영)
2. **S1 프롬프트**: 임상 가이드라인 업데이트 반영 규칙
3. **S2 프롬프트**: 의학 용어 정확성 규칙 강화
4. **S2 프롬프트**: 질문-답변 정렬 규칙 추가

### 장기 개선 (Low Priority)
1. **S1 프롬프트**: 물리학/규제 용어 정확성 규칙
2. **S2 프롬프트**: 해부학적 정밀도 규칙 강화
3. **스키마 검증**: MCQ 구조 검증 강화 (S5 validator)

---

## 6. 통계 요약

### 이슈 발생률
- **S1**: 평균 1.5개 이슈/그룹 (17개 이슈 / 11개 그룹)
- **S2**: 5.4% 카드에 이슈 (30개 카드 / 334개 카드)

### 이슈 분류
- **용어 관련**: S1 7건, S2 7건 (총 14건, 40%)
- **명확성**: S1 5건, S2 3건 (총 8건, 23%)
- **구조/일관성**: S2 6건 (17%)
- **기타**: S1 5건, S2 2건 (총 7건, 20%)

### Blocking Error
- **S1**: 0건 (0%)
- **S2**: 0건 (0%)
- **전체**: 매우 양호한 상태

---

## 7. 다음 단계

1. **프롬프트 업데이트**: 위의 우선순위에 따라 프롬프트 규칙 추가
2. **재검증**: 업데이트된 프롬프트로 재생성 후 S5 재검증
3. **모니터링**: 개선된 항목의 이슈 감소율 추적
4. **반복**: S5 리포트 → 개선점 정리 → 프롬프트 업데이트 → 재검증 사이클 유지

---

## 8. 참고

- **S5 리포트 원본**: `2_Data/metadata/generated/DEV_armG_s5loop_diverse_20251229_065718/reports/s5_report__armG.md`
- **S5 Validation 데이터**: `2_Data/metadata/generated/DEV_armG_s5loop_diverse_20251229_065718/s5_validation__armG.jsonl`
- **프롬프트 위치**: `3_Code/prompt/`
  - S1: `S1_SYSTEM__v12.md`, `S1_USER_GROUP__v11.md`
  - S2: `S2_SYSTEM__v9.md`, `S2_USER_ENTITY__v9.md`

