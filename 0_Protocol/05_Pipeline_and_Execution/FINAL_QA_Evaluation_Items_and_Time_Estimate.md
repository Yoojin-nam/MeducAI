# FINAL QA 평가 항목 및 시간 예상

**Status:** Canonical  
**Version:** 1.1  
**Date:** 2025-12-29  
**Last Updated:** 2025-12-29  
**Purpose:** FINAL 단계에서 QA 참가자들이 카드당 평가해야 하는 항목 정리 및 예상 소요 시간 제시  
**Change Log**: 
- v1.1 - FINAL QA는 Q1(단답형 주관식)과 Q2(MCQ)만 평가하며, 둘 다 이미지가 BACK에 배치됨. Q3은 평가하지 않음.
- v1.2 - Q3은 S0(QA 실험)에서만 사용되었으며, FINAL 모드에서는 S2가 Q1과 Q2만 생성함을 명확히 함.  
**Related Documents:**
- `FINAL_QA_Form_Design.md` (2-pass workflow)
- `QA_Metric_Definitions.md` (평가 메트릭 정의)
- `S5_Image_Evaluation_3Stage_Rubric.md` (이미지 평가 기준)

---

## 1. 평가 항목 개요

FINAL QA는 **2-pass workflow**로 구성됩니다:
1. **Pre-S5 Pass**: S5 결과 보기 전 평가 (primary endpoint)
2. **Post-S5 Pass**: S5 결과 본 후 수정 가능 (secondary endpoint)

**FINAL QA 카드 구성**:
- **Q1**: 단답형 주관식 (텍스트 영상소견 보고 진단 위주), 이미지 BACK 배치
- **Q2**: MCQ (병태원리 질문), 이미지 BACK 배치
- **Q3**: 없음 (FINAL QA에서는 평가하지 않음)

**참고**: FINAL 모드에서는 S2가 Q1과 Q2만 생성합니다. Q3은 S0(QA 실험)에서만 사용되었으며, FINAL에서는 생성되지 않습니다.

각 카드에 대해 다음을 평가합니다:
- **카드 텍스트 평가** (필수)
- **이미지 평가** (Q1/Q2 모두 이미지가 BACK에 있음)
- **난이도 평가** (카드 텍스트 평가에 포함)

---

## 2. 카드 텍스트 평가 항목 (필수, 모든 카드)

### 2.1 Pre-S5 Pass 평가 항목

| 항목 | 필드명 | 타입 | 필수 여부 | 설명 |
|------|--------|------|----------|------|
| **B1. Blocking Error** | `blocking_error_pre` | Yes/No | 필수 | 임상 안전 위험 또는 콘텐츠를 해결 불가능하게 만드는 문제 |
| **B1.5. Technical Accuracy** | `technical_accuracy_pre` | 0.0 / 0.5 / 1.0 | 필수 | 사실적 정확성 및 임상 타당성 (3단계) |
| **B2. Overall Card Quality** | `overall_quality_pre` | 1-5 Likert | 필수 | 교육적 가치 (명확성, 시험 적합성, 교육적 효과성) |
| **B3. Evidence Comment** | `evidence_comment_pre` | Text (1줄, max 200자) | 조건부 | B1=Yes 또는 B2≤2일 때만 필수 |

**평가 기준**:
- **Technical Accuracy**: 
  - 1.0: 핵심 개념과 설명이 완전히 정확함
  - 0.5: 핵심 개념은 정확하지만 설명에 소소한 누락/부정확성 있음
  - 0.0: 핵심 개념이 잘못되었거나 오해를 유발할 수 있음
- **Overall Card Quality**: 
  - 5: 매우 가치 있음, 시험 핵심 개념 직접 타겟
  - 4: 가치 있음, 중요한 개념 다루지만 소소한 제한 있음
  - 3: 적절함, 정확하지만 한계적으로 유용하거나 과도하게 일반적
  - 2: 제한적 가치, 주변적이거나 시험 지향 학습에 비효율적
  - 1: 가치 낮음, 학습에 도움이 되지 않을 가능성

**추가 평가 (암묵적)**:
- **Difficulty (난이도 적절성)**: 카드 앞면 텍스트가 힌트를 과도하게 주는지 확인
  - Q1 (단답형 주관식): 앞면 텍스트만으로 문제를 풀 수 있는지 확인 (영상소견 설명이 과도한 힌트를 주는지)
  - Q2 (MCQ, 병태원리): 텍스트 설명만으로 문제를 풀 수 있는지 확인, 전문의 시험 수준에 적합한지 확인
  - **참고**: Difficulty는 별도 필드로 기록하지 않지만, Overall Quality 평가에 반영

### 2.2 Post-S5 Pass 평가 항목

| 항목 | 필드명 | 타입 | 필수 여부 | 설명 |
|------|--------|------|----------|------|
| **B1. Blocking Error** | `blocking_error_post` | Yes/No | 필수 | Pre-S5 값으로 pre-fill, 수정 가능 |
| **B1.5. Technical Accuracy** | `technical_accuracy_post` | 0.0 / 0.5 / 1.0 | 필수 | Pre-S5 값으로 pre-fill, 수정 가능 |
| **B2. Overall Card Quality** | `overall_quality_post` | 1-5 Likert | 필수 | Pre-S5 값으로 pre-fill, 수정 가능 |
| **B3. Evidence Comment** | `evidence_comment_post` | Text (1줄, max 200자) | 조건부 | Pre-S5 값으로 pre-fill, 수정 가능 |
| **Change Log** | `change_reason_code`, `change_note` | Dropdown + Text | 조건부 | Post-S5 값이 Pre-S5와 다를 때만 필수 |

**Change Log 항목** (변경 시):
- **Change Reason Code**: 변경 이유 (dropdown)
  - `S5_BLOCKING_FLAG`: S5가 blocking error 플래그, 검토 후 확인
  - `S5_BLOCKING_FALSE_POS`: S5가 blocking error 플래그했으나 false positive로 판단
  - `S5_QUALITY_INSIGHT`: S5 품질 평가가 유용한 인사이트 제공
  - `S5_EVIDENCE_HELPED`: S5 증거/제안이 이슈 식별에 도움
  - `S5_NO_EFFECT`: S5 결과 검토했으나 변경 불필요
  - `RATER_REVISION`: S5 영향 없이 평가자 재고려 (드묾)
  - `OTHER`: 기타 (노트에 명시)
- **Change Note**: 변경 사유 간단 설명 (1줄, max 200자)

---

## 3. 이미지 평가 항목 (Q1/Q2 모두 이미지가 BACK에 배치됨)

### 3.1 평가 메트릭 (4개)

| 메트릭 | 스케일 | 평가 기준 | 예상 시간 |
|--------|--------|----------|----------|
| **Anatomical Accuracy** | 0.0 / 0.5 / 1.0 | 해부학적 정확성 (구조, 위치, 관계) | 10-15초 |
| **Prompt Compliance** | 0.0 / 0.5 / 1.0 | S3 프롬프트 준수도 (모달리티, 뷰, 소견 일치) | 10-15초 |
| **Text-Image Consistency** | 0.0 / 0.5 / 1.0 | 카드 텍스트와 이미지 일관성 | 10-15초 |
| **Image Quality** | 1-5 Likert | 기술적 품질 (해상도, 가독성, 아티팩트, 대비) | 10-15초 |

**평가 시 제공 정보**:
- 카드 텍스트 (front, back)
- S3 프롬프트 (`prompt_en`, `image_hint_v2`)
- S2 이미지 힌트 (`image_hint`)
- S1 테이블 컨텍스트 (entity_context)
- 이미지 파일

**특별 주의사항**:
- **모달리티 불일치**: blocking error (0.0)
- **텍스트 품질** (이미지 내 텍스트가 있는 경우):
  - 한영 병용 문제 확인
  - S1/S2 텍스트 재사용 부정확성 확인
  - 가독성 확인
- **Blocking Error 판단**: 이미지가 학습 목표 달성을 불가능하게 만드는 경우

### 3.2 이미지 평가 기록 형식

```json
{
  "card_image_validation": {
    "blocking_error": false,
    "anatomical_accuracy": 1.0,
    "prompt_compliance": 0.5,
    "text_image_consistency": 1.0,
    "image_quality": 4,
    "safety_flag": false,
    "issues": [
      {
        "severity": "minor",
        "type": "view_mismatch",
        "description": "Requested axial view but image shows sagittal view"
      }
    ]
  }
}
```

---

## 4. 시간 예상 (카드당)

### 4.1 Pre-S5 Pass 시간 예상

| 평가 단계 | 예상 시간 | 설명 |
|-----------|----------|------|
| **카드 텍스트 읽기 및 이해** | 15-30초 | Front/Back 텍스트 읽기, MCQ 옵션 확인 (Q2만) |
| **Technical Accuracy 평가** | 20-40초 | 사실적 정확성, 임상 타당성 판단 (3단계 선택) |
| **Overall Quality 평가** | 15-30초 | 교육적 가치, 시험 적합성 판단 (1-5 Likert) |
| **Blocking Error 판단** | 10-20초 | 임상 안전 위험 여부 판단 (Yes/No) |
| **Evidence Comment 작성** (조건부) | 20-40초 | B1=Yes 또는 B2≤2일 때만 (1줄, max 200자) |
| **이미지 평가** (Q1/Q2 모두) | 40-60초 | 4개 메트릭 평가 (각 10-15초) |
| **난이도 평가** (암묵적) | 10-20초 | 카드 앞면 텍스트 힌트 확인 (Overall Quality에 반영) |
| **총 예상 시간** | **130-240초** | **2.2-4분** |

**시간 변동 요인**:
- **카드 복잡도**: 간단한 카드는 130초, 복잡한 카드는 240초
- **카드 유형**: Q1 (단답형)은 130-180초, Q2 (MCQ)는 150-240초
- **Blocking Error 유무**: Blocking error가 있으면 Evidence Comment 작성으로 +20-40초
- **평가자 경험**: 경험 많은 평가자는 더 빠름

### 4.2 Post-S5 Pass 시간 예상

| 평가 단계 | 예상 시간 | 설명 |
|-----------|----------|------|
| **S5 결과 확인** | 10-20초 | S5 blocking error 플래그, 품질 평가, 이슈 목록 확인 |
| **Pre-S5 값 재검토** | 10-20초 | Pre-S5 평가와 S5 결과 비교 |
| **Post-S5 값 수정** (조건부) | 20-40초 | S5 결과에 따라 평가 수정 (대부분 변경 없음) |
| **Change Log 작성** (조건부) | 20-40초 | 변경 시에만 (reason code + note) |
| **총 예상 시간** | **40-100초** | **0.7-1.7분** |

**시간 변동 요인**:
- **변경 여부**: 변경 없으면 40초, 변경 있으면 100초
- **S5 결과 복잡도**: S5 이슈가 많으면 검토 시간 증가

### 4.3 전체 카드당 총 예상 시간

| 시나리오 | Pre-S5 | Post-S5 | 총 시간 |
|----------|--------|---------|---------|
| **Q1 (단답형, 이미지 BACK, Blocking Error 없음)** | 130-180초 | 40-80초 | **170-260초 (2.8-4.3분)** |
| **Q2 (MCQ, 이미지 BACK, Blocking Error 없음)** | 150-240초 | 40-100초 | **190-340초 (3.2-5.7분)** |
| **Blocking Error 있음** | +20-40초 | +20-40초 | **+40-80초** |
| **평균 (Q1/Q2, Blocking Error 없음)** | **~165초** | **~70초** | **~235초 (약 3.9분)** |

---

## 5. 평가 워크플로우

### 5.1 Pre-S5 Pass 순서

1. **카드 내용 확인** (15-30초)
   - Front/Back 텍스트 읽기
   - MCQ 옵션 확인 (Q2만)
   - 이미지 확인 (Q1/Q2 모두 BACK에 배치)

2. **Technical Accuracy 평가** (20-40초)
   - 사실적 정확성 확인
   - 임상 타당성 확인
   - 3단계 중 선택 (0.0 / 0.5 / 1.0)

3. **Overall Quality 평가** (15-30초)
   - 교육적 가치 확인
   - 시험 적합성 확인
   - 난이도 적절성 확인 (암묵적)
   - 1-5 Likert 중 선택

4. **Blocking Error 판단** (10-20초)
   - 임상 안전 위험 여부 확인
   - Yes/No 선택

5. **Evidence Comment 작성** (조건부, 20-40초)
   - B1=Yes 또는 B2≤2일 때만
   - 1줄 설명 작성

6. **이미지 평가** (Q1/Q2, 조건부, 40-60초)
   - Anatomical Accuracy (10-15초)
   - Prompt Compliance (10-15초)
   - Text-Image Consistency (10-15초)
   - Image Quality (10-15초)

7. **Pre-S5 제출** (5초)
   - 모든 필수 항목 확인
   - 제출 버튼 클릭

### 5.2 S5 Reveal

1. **S5 결과 확인** (10-20초)
   - S5 blocking error 플래그 확인
   - S5 Technical Accuracy 확인
   - S5 Quality 확인
   - S5 이슈 목록 확인
   - S5 증거/제안 확인

### 5.3 Post-S5 Pass 순서

1. **Pre-S5 값 재검토** (10-20초)
   - Pre-S5 평가와 S5 결과 비교
   - 불일치 여부 확인

2. **Post-S5 값 수정** (조건부, 20-40초)
   - S5 결과에 따라 평가 수정
   - 대부분 변경 없음 (pre-filled 값 유지)

3. **Change Log 작성** (조건부, 20-40초)
   - 변경 시에만
   - Reason code 선택
   - Change note 작성

4. **Final 제출** (5초)
   - 모든 필수 항목 확인
   - 제출 버튼 클릭

---

## 6. 평가 항목 요약표

### 6.1 카드 텍스트 평가 (모든 카드, 필수)

| 항목 | Pre-S5 | Post-S5 | 시간 (Pre-S5) | 시간 (Post-S5) |
|------|--------|---------|---------------|----------------|
| Blocking Error | Yes/No | Yes/No (수정 가능) | 10-20초 | 10-20초 |
| Technical Accuracy | 0.0/0.5/1.0 | 0.0/0.5/1.0 (수정 가능) | 20-40초 | 10-20초 |
| Overall Quality | 1-5 Likert | 1-5 Likert (수정 가능) | 15-30초 | 10-20초 |
| Evidence Comment | Text (조건부) | Text (조건부, 수정 가능) | 20-40초 | 10-20초 |
| Difficulty | 암묵적 (Overall Quality에 반영) | 암묵적 | 10-20초 | 5-10초 |
| **소계** | | | **75-150초** | **45-90초** |

### 6.2 이미지 평가 (Q1/Q2 모두, 필수)

**참고**: FINAL QA에서는 Q1과 Q2 모두 이미지가 BACK에 배치되므로, 모든 카드에 대해 이미지 평가가 필요합니다.

| 항목 | Pre-S5 | Post-S5 | 시간 (Pre-S5) | 시간 (Post-S5) |
|------|--------|---------|---------------|----------------|
| Anatomical Accuracy | 0.0/0.5/1.0 | 0.0/0.5/1.0 (수정 가능) | 10-15초 | 5-10초 |
| Prompt Compliance | 0.0/0.5/1.0 | 0.0/0.5/1.0 (수정 가능) | 10-15초 | 5-10초 |
| Text-Image Consistency | 0.0/0.5/1.0 | 0.0/0.5/1.0 (수정 가능) | 10-15초 | 5-10초 |
| Image Quality | 1-5 Likert | 1-5 Likert (수정 가능) | 10-15초 | 5-10초 |
| **소계** | | | **40-60초** | **20-40초** |

### 6.3 Change Log (Post-S5, 조건부)

| 항목 | 시간 |
|------|------|
| Change Reason Code 선택 | 10-15초 |
| Change Note 작성 | 10-25초 |
| **소계** | **20-40초** |

---

## 7. 시간 예상 시나리오별 요약

### 7.1 최소 시간 (간단한 카드, Blocking Error 없음, 변경 없음)

- **Q1 (단답형, 이미지 BACK)**: 
  - Pre-S5: 130초
  - Post-S5: 40초
  - **총: 170초 (약 2.8분)**

- **Q2 (MCQ, 이미지 BACK)**:
  - Pre-S5: 150초
  - Post-S5: 40초
  - **총: 190초 (약 3.2분)**

### 7.2 최대 시간 (복잡한 카드, Blocking Error 있음, 변경 있음)

- **Q1 (단답형, 이미지 BACK)**:
  - Pre-S5: 220초 (이미지 평가 + Blocking Error + Evidence Comment)
  - Post-S5: 100초 (변경 + Change Log)
  - **총: 320초 (약 5.3분)**

- **Q2 (MCQ, 이미지 BACK)**:
  - Pre-S5: 280초 (이미지 평가 + Blocking Error + Evidence Comment)
  - Post-S5: 100초 (변경 + Change Log)
  - **총: 380초 (약 6.3분)**

### 7.3 평균 시간 (일반적인 카드)

- **Q1 (단답형, 이미지 BACK)**: 
  - Pre-S5: 155초
  - Post-S5: 60초
  - **총: 215초 (약 3.6분)**

- **Q2 (MCQ, 이미지 BACK)**:
  - Pre-S5: 195초
  - Post-S5: 70초
  - **총: 265초 (약 4.4분)**

---

## 8. 평가 효율성 향상을 위한 권장사항

### 8.1 평가자 훈련

- **평가 기준 숙지**: Technical Accuracy, Overall Quality, 이미지 평가 메트릭 정의 명확히 이해
- **3단계 평가 연습**: 0.0/0.5/1.0 판단 기준 익히기
- **시간 관리**: 카드당 2-4분 목표, 과도한 시간 소요 방지

### 8.2 평가 도구 개선

- **One-screen layout**: 스크롤 최소화, 모든 정보 한 화면에 표시
- **Pre-fill 기능**: Post-S5 값은 Pre-S5 값으로 자동 채우기
- **조건부 필드**: Evidence Comment, Change Log는 필요할 때만 표시
- **S5 결과 하이라이트**: Blocking error, 주요 이슈 강조 표시

### 8.3 평가 워크플로우 최적화

- **일괄 평가**: 유사한 카드들을 묶어서 평가 (컨텍스트 유지)
- **우선순위**: Blocking Error 확인 → Technical Accuracy → Overall Quality 순서
- **이미지 평가**: 카드 텍스트 평가 후 이미지 평가 (컨텍스트 이해 후)

---

## 9. 참고 문서

- **FINAL QA Form Design**: `0_Protocol/06_QA_and_Study/FINAL_QA_Form_Design.md`
- **QA Metric Definitions**: `0_Protocol/05_Pipeline_and_Execution/QA_Metric_Definitions.md`
- **S5 Image Evaluation Rubric**: `0_Protocol/05_Pipeline_and_Execution/S5_Image_Evaluation_3Stage_Rubric.md`
- **S5 Validation Schema**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`
- **S2 Cardset Policy**: `0_Protocol/04_Step_Contracts/Step02_S2/S2_Cardset_Image_Placement_Policy_Canonical.md`

---

## 10. FINAL QA 카드 구성 명확화

**중요**: FINAL QA 평가 단계에서는 **Q1과 Q2만 평가**합니다.

- **Q1**: 단답형 주관식 (텍스트 영상소견 보고 진단 위주), 이미지 BACK 배치
- **Q2**: MCQ (병태원리 질문), 이미지 BACK 배치
- **Q3**: FINAL QA에서 평가하지 않음

**중요**: 
- **FINAL 모드**: S2가 Q1과 Q2만 생성합니다. Q3은 생성되지 않습니다.
- **S0 모드 (QA 실험)**: S2가 Q1, Q2, Q3을 생성합니다 (과거 QA에서 사용됨).
- **FINAL QA**: 생성된 Q1과 Q2만 평가합니다.

---

**작성자**: MeducAI Research Team  
**검토 필요**: 실제 평가 데이터 수집 후 시간 예상 검증 및 조정

