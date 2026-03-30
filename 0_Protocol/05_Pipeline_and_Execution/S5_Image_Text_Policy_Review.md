# S4 이미지 텍스트 정책 점검 및 실험 계획

**작성일**: 2025-12-29  
**목적**: 이미지 내 텍스트 정책 재검토 및 실험을 통한 최적 정책 도출  
**배경**: S5 검증 결과, EXAM 이미지에서 텍스트 포함이 blocking error로 감지되었으나, 적절한 키워드와 시험포인트는 교육적으로 유용할 수 있음

---

## 1. 현재 "No Text" 정책 정의 위치

### 1.1 S4 프롬프트 파일

**EXAM Lane (Q1/Q2 카드 이미지)**:
- **파일**: `3_Code/prompt/S4_EXAM_USER__v8_REALISTIC_4x5_2K.md`
  - Line 59: `- No labels, no arrows, no circles, no text.`
- **파일**: `3_Code/prompt/S4_EXAM_SYSTEM__v8_REALISTIC_4x5_2K.md`
  - Line 10: `Do NOT add text overlays, labels, arrows, circles, captions, UI elements, scale bars, slice numbers, R/L markers, or watermarks.`
  - Line 33: `Do NOT include any visible text/letters/markers of any kind.`
  - Line 42: `Any visible text/letters/markers (including R/L).` (FAIL 조건)

**CONCEPT Lane (테이블 인포그래픽)**:
- **파일**: `0_Protocol/04_Step_Contracts/Step04_S4/Entity_Definition_S4_Canonical.md`
  - Line 191: `Labels and minimal text allowed` (CONCEPT lane)
  - Line 209: `No labels, arrows, or text overlays` (EXAM lane)

### 1.2 S4 DIAGRAM 프롬프트 (현재 기준)

**파일**: `3_Code/prompt/S4_EXAM_SYSTEM__v8_DIAGRAM_4x5_2K.md`
- Line 35-42: `ALLOWED DIDACTIC ANNOTATION (LIMITED)`:
  - `Labels are OPTIONAL and should be avoided unless you are confident they render cleanly`
  - `Max 1–2 labels total, each 1–2 words preferred (max 3), no sentences`
  - `If text is likely to distort, OMIT TEXT`
  - `Prefer arrows/circles over text`

**파일**: `3_Code/prompt/S4_EXAM_USER__v8_DIAGRAM_4x5_2K.md`
- Line 39-46: `ANNOTATION RULES (TEXT-AVOIDANT)`:
  - `Labels are OPTIONAL and should be avoided unless you are confident they render cleanly`
  - `Max 1–2 labels total, each 1–2 words preferred (max 3)`
  - `If text is likely to distort, OMIT TEXT`
  - `If you use labels, derive them from key_findings_keywords (do NOT introduce new findings)`

**정책 요약**: 텍스트는 완전히 금지되지 않으며, 제한적으로 허용됨 (최대 1-2개 라벨, 각 1-3단어, `key_findings_keywords`에서 유도)

### 1.3 S5 검증 프롬프트

**파일**: `3_Code/prompt/S5_USER_CARD_IMAGE__v1.md`
- Line 132: `For EXAM images (Q1/Q2 card images): The image should NOT contain any text, labels, arrows, or annotations. If text is present, this is a **BLOCKING ERROR**`
- Line 201: `If text is found, include it in extracted_text and flag as unexpected_text issue.`

**문제점**: S4 DIAGRAM 프롬프트는 제한적 텍스트 허용을 명시하지만, S5 검증은 완전 금지로 검증하고 있어 불일치 발생

### 1.4 프로토콜 문서

**파일**: `0_Protocol/04_Step_Contracts/Step04_S4/S4_Image_Prompt_Analysis.md`
- Line 178: `Constraints: No text, no labels, no arrows, no watermark. Single frame. Realistic clinical style. Board-exam style.`
- Line 47: `Minimal text (prefer English short labels if any)` (CONCEPT lane에 대한 언급)

**참고**: 이 문서는 REALISTIC 버전 기준으로 작성되어 있으며, 현재 사용 중인 DIAGRAM 버전과는 다름

---

## 2. 정책 불일치 및 문제점

### 2.1 현재 상황

1. **EXAM Lane (DIAGRAM 버전)**: 제한적 텍스트 허용 정책
   - S4 DIAGRAM 프롬프트: "Labels are OPTIONAL", 최대 1-2개 라벨, 각 1-3단어, `key_findings_keywords`에서 유도
   - S5 검증: 텍스트 발견 시 blocking error (완전 금지로 검증)
   - **불일치**: S4는 제한적 허용, S5는 완전 금지로 검증
   - **결과**: 15/16 카드에서 blocking error (93.8%) - S4 프롬프트와 S5 검증 기준 불일치로 인한 과도한 에러

2. **CONCEPT Lane**: 텍스트 허용
   - "Labels and minimal text allowed"
   - 인포그래픽에는 텍스트가 필요

3. **사용자 요구사항**:
   - 적절한 키워드와 시험포인트 정도의 텍스트는 넣고 싶음
   - 교육적 가치를 고려한 유연한 정책 필요
   - S4 DIAGRAM 프롬프트의 제한적 허용 정책에 맞춰 S5 검증도 조정 필요

### 2.2 문제점

1. **S4-S5 정책 불일치**: 
   - S4 DIAGRAM 프롬프트는 제한적 텍스트 허용 (최대 1-2개 라벨, 각 1-3단어)
   - S5 검증은 완전 금지로 검증하여 불일치 발생
   - 결과적으로 S4 프롬프트에 따라 생성된 이미지가 S5에서 blocking error로 감지됨

2. **정책 정의가 분산됨**: S4 프롬프트, S5 검증, 프로토콜 문서에 각각 정의되어 일관성 부족

3. **S5 검증 기준 조정 필요**: S4 DIAGRAM 프롬프트의 제한적 허용 정책에 맞춰 S5 검증 기준을 업데이트해야 함

4. **실험 기반 정책 부재**: 어떤 텍스트가 허용되어야 하는지, 허용 범위가 적절한지에 대한 데이터 기반 검증 필요

---

## 3. 실험 계획: 텍스트 정책 최적화

### 3.1 실험 목표

**주요 질문**:
1. 어떤 종류의 텍스트가 교육적으로 유용한가?
2. 어떤 텍스트가 답을 스포일러하는가?
3. 텍스트 포함 시 시험 정합성에 미치는 영향은?

### 3.2 실험 설계

#### 실험 1: 텍스트 유형별 허용 범위

**가설**: 특정 유형의 텍스트(키워드, 시험포인트)는 교육적 가치를 제공하면서도 답을 스포일러하지 않음

**변수**:
- **Control**: 현재 정책 (no text)
- **Treatment A**: 키워드만 허용 (예: "Popcorn-like calcification")
- **Treatment B**: 키워드 + 시험포인트 허용 (예: "BI-RADS 2")
- **Treatment C**: 모달리티/뷰 정보 허용 (예: "CT Axial")

**측정 지표**:
- S5 `prompt_compliance` 점수
- S5 `text_image_consistency` 점수
- `blocking_error` 비율
- `unexpected_text` 이슈 빈도
- 교육적 가치 평가 (QA 평가단 피드백)

**실행 방법**:
1. S4 프롬프트에 텍스트 허용 정책 추가 (버전별)
2. 동일한 run_tag로 S4 재실행
3. S5 재검증
4. Before/After 비교

#### 실험 2: 텍스트 위치별 영향

**가설**: 텍스트 위치(이미지 내부 vs 외부, 상단 vs 하단)에 따라 스포일러 효과가 다름

**변수**:
- 텍스트 위치: 이미지 내부 (상단/하단/중앙) vs 이미지 외부 (카드 텍스트 영역)
- 텍스트 스타일: 라벨 vs 주석 vs 키워드 태그

**측정 지표**:
- 답 스포일러 여부 (S5 검증)
- 교육적 가치 (QA 평가)

#### 실험 3: 카드 역할별 차별화

**가설(업데이트)**: **현행 2-card policy에서 Q1/Q2 모두 IMAGE_ON_BACK**이므로, 텍스트 허용 범위는 “front에서의 스포일러 위험/학습 목적” 관점으로 재정의되어야 함

**변수**:
- Q1/Q2 (공통): front는 text-only이므로 **정답 스포일러를 유발하는 텍스트**를 억제
- Q2 (MCQ): distractor 설명을 돕는 범위 내에서 back 쪽 교육적 텍스트를 강화

**측정 지표**:
- Q1/Q2별 `blocking_error` 비율
- 교육적 가치 평가

---

## 4. 정책 재정의 제안

### 4.1 계층적 텍스트 정책

**Level 1: 완전 금지 (현재)**
- 모든 텍스트, 라벨, 화살표 금지
- **적용(업데이트)**: Q1/Q2 모두 IMAGE_ON_BACK이므로, **front 텍스트의 스포일러/정답 직접 언급 방지**가 핵심 적용점

**Level 2: 최소 허용 (제안)**
- 키워드만 허용 (예: "Popcorn-like calcification")
- 모달리티/뷰 정보 허용 (예: "CT Axial")
- **적용**: Q1 (선택적), Q2 (IMAGE_ON_BACK)

**Level 3: 교육적 허용 (제안)**
- 키워드 + 시험포인트 (예: "BI-RADS 2")
- 해부학적 랜드마크 라벨 (예: "MCA territory")
- **적용**: Q2 (IMAGE_ON_BACK), CONCEPT lane

**Level 4: 완전 허용**
- 모든 텍스트 허용
- **적용**: CONCEPT lane (인포그래픽)

### 4.2 금지 항목 (모든 레벨 공통)

- 정답 직접 언급 (예: "Osteosarcoma")
- 선택지 관련 텍스트 (예: "Answer: C")
- 측정값/수치 (예: "2.2 cm") - 측정 방향 오류 가능성
- 환자 식별 정보
- PACS UI 요소

---

## 5. 실험 실행 계획

### 5.1 Phase 1: Baseline 측정

**목적**: 현재 "no text" 정책의 문제점 정량화

**실행**:
```bash
# 현재 상태 측정 (이미 완료)
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag TEST_PROGRESS_20251229_145011 \
  --arm A
```

**결과 요약**:
- `prompt_compliance`: 0.44 (낮음)
- `blocking_error`: 15/16 (93.8%)
- 주요 이슈: `unexpected_text` (15건)

### 5.2 Phase 2: 프롬프트 수정

**작업**:
1. `S4_EXAM_USER__v9.md` 생성 (텍스트 허용 정책 추가)
2. `S4_EXAM_SYSTEM__v9.md` 생성 (시스템 프롬프트 업데이트)
3. 텍스트 허용 범위 명시:
   - 허용: 키워드, 모달리티/뷰 정보
   - 금지: 정답, 측정값, UI 요소

**프롬프트 예시**:
```
TEXT POLICY (v9):
- ALLOWED: Short keywords (e.g., "Popcorn-like calcification"), modality/view info (e.g., "CT Axial")
- FORBIDDEN: Direct answers, measurements, UI elements, patient identifiers
- For Q1: Minimize text to avoid spoilers
- For Q2: Educational keywords and exam points allowed
```

### 5.3 Phase 3: S5 검증 프롬프트 업데이트

**작업**:
1. `S5_USER_CARD_IMAGE__v2.md` 생성
2. 텍스트 정책 재정의:
   - Level 1 (금지): 정답, 측정값, UI 요소
   - Level 2 (경고): 과도한 텍스트, 스포일러 가능성
   - Level 3 (허용): 키워드, 모달리티 정보

**검증 로직**:
```python
if text_contains_answer_or_measurement:
    blocking_error = True
elif text_is_excessive_or_spoiler:
    issue_severity = "major"
elif text_is_keyword_or_modality_info:
    issue_severity = "minor" or None
```

### 5.4 Phase 4: 실험 실행

**실험 그룹**:
- **Group A**: 현재 정책 (no text) - Baseline
- **Group B**: 키워드만 허용
- **Group C**: 키워드 + 시험포인트 허용

**실행**:
```bash
# Group B 실험
# 1. S4 프롬프트 v9 적용
# 2. S4 재실행
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag TEST_TEXT_POLICY_B \
  --arm A

# 3. S5 재검증
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag TEST_TEXT_POLICY_B \
  --arm A
```

### 5.5 Phase 5: 결과 비교

**비교 메트릭**:
- `prompt_compliance` 평균 점수
- `blocking_error` 비율
- `unexpected_text` 이슈 빈도
- 교육적 가치 평가 (QA 평가단)

**결정 기준**:
- `prompt_compliance` > 0.8
- `blocking_error` < 20%
- 교육적 가치 향상 확인

---

## 6. 프로토콜 문서 업데이트 필요

### 6.1 업데이트 대상 문서

1. **`S2_Cardset_Image_Placement_Policy_Canonical.md`**
   - 이미지 텍스트 정책 섹션 추가
   - Q1/Q2별 차별화 정책 명시

2. **`S4_Image_Prompt_Analysis.md`**
   - 텍스트 허용 범위 업데이트
   - 실험 결과 반영

3. **`Entity_Definition_S4_Canonical.md`**
   - EXAM lane 텍스트 정책 명확화
   - CONCEPT lane과의 차이점 명시

4. **`S5_Validation_Schema_Canonical.md`**
   - 텍스트 검증 기준 업데이트
   - 레벨별 이슈 심각도 정의

### 6.2 새 문서 생성

**`S4_Image_Text_Policy_Canonical.md`** (신규)
- 텍스트 정책의 권위 있는 정의
- 레벨별 허용/금지 항목
- 실험 결과 기반 정책 업데이트 절차

---

## 7. 다음 단계

1. **즉시**: 현재 정책 정의 위치 문서화 완료 (이 문서)
2. **단기**: 실험 설계 및 프롬프트 수정
3. **중기**: 실험 실행 및 결과 분석
4. **장기**: 프로토콜 문서 업데이트 및 정책 확정

---

## 8. 참고 자료

### 8.1 관련 문서
- `0_Protocol/04_Step_Contracts/Step02_S2/S2_Cardset_Image_Placement_Policy_Canonical.md`
- `0_Protocol/04_Step_Contracts/Step04_S4/S4_Image_Prompt_Analysis.md`
- `0_Protocol/04_Step_Contracts/Step04_S4/Entity_Definition_S4_Canonical.md`
- `3_Code/prompt/S4_EXAM_USER__v8_DIAGRAM_4x5_2K.md` (현재 기준)
- `3_Code/prompt/S4_EXAM_SYSTEM__v8_DIAGRAM_4x5_2K.md` (현재 기준)
- `3_Code/prompt/S5_USER_CARD_IMAGE__v1.md`
- `3_Code/prompt/S4_EXAM_USER__v8_REALISTIC_4x5_2K.md` (archive, 참고용)
- `3_Code/prompt/S4_EXAM_SYSTEM__v8_REALISTIC_4x5_2K.md` (archive, 참고용)

### 8.2 실험 데이터
- Baseline: `TEST_PROGRESS_20251229_145011`
- S5 리포트: `2_Data/metadata/generated/TEST_PROGRESS_20251229_145011/reports/s5_report__armA.md`

---

**작성자**: MeducAI Development Team  
**최종 업데이트**: 2025-12-29  
**버전**: 1.0

