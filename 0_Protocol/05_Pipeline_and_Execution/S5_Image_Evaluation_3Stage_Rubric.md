# S5 이미지 평가 3단계 기준 (Human Rater용)

**Status:** Canonical  
**Version:** 1.0  
**Date:** 2025-12-29  
**Purpose:** 실제 사람 평가자가 S5의 3단계 평가 기준(0.0/0.5/1.0)에 맞춰 이미지를 평가할 수 있도록 명확한 기준 제공  
**Related Documents:**
- `QA_Metric_Definitions.md` (Technical Accuracy 3단계 기준)
- `S5_Validation_Schema_Canonical.md` (이미지 평가 스키마)
- `S5_vs_FINAL_QA_Alignment_Analysis.md` (3단계 평가 정렬)

---

## 1. 개요

S5 이미지 평가는 **카드 텍스트 평가와 동일한 3단계 기준**을 사용합니다:
- **1.0**: 완전히 정확하고 적절함 (수정 불필요)
- **0.5**: 핵심은 정확하지만 소소한 문제 있음 (minor issues)
- **0.0**: 차단 오류 (blocking error) 또는 심각한 부정확성

이미지 평가는 **4개 메트릭**으로 구성되며, 각 메트릭은 3단계(0.0/0.5/1.0) 또는 5점 Likert(1-5)로 평가됩니다.

**참고**: 
- 난이도(Difficulty) 평가는 이미지 평가가 아닌 **카드 텍스트 평가**에 포함됩니다. Q1과 Q2 모두 이미지가 BACK에 배치되므로, 이미지 자체는 난이도 평가와 무관합니다.
- **FINAL QA**: Q1(단답형 주관식)과 Q2(MCQ)만 평가하며, 둘 다 이미지가 BACK에 배치됩니다. Q3은 S0(QA 실험)에서만 사용되었으며, FINAL 모드에서는 생성되지 않습니다.

---

## 2. 이미지 평가 메트릭 정의

**참고**: 이미지 평가는 **카드 텍스트와 함께** 평가되며, 특히 **난이도(difficulty)** 평가는 카드 앞면 텍스트가 이미지 없이도 문제를 풀 수 있게 하는지 확인하는 것이 중요합니다.

### 2.1 Anatomical Accuracy (해부학적 정확성)

**평가 기준**: 이미지가 해부학적으로 정확한가?

| 점수 | 정의 | 예시 |
|------|------|------|
| **1.0** | 해부학적으로 완전히 정확함. 구조, 위치, 관계가 모두 올바름. | 정확한 해부학적 구조, 올바른 위치, 일관된 관계 |
| **0.5** | 핵심 해부학은 정확하지만, 세부 구조나 위치에 소소한 부정확성 있음. 학습 목표에는 영향 없음. | 대부분 정확하지만 일부 랜드마크 누락, 약간의 위치 오차 |
| **0.0** | 해부학적으로 잘못됨. 구조, 위치, 관계가 명백히 틀림. 학습자 오해 유발 가능. | 잘못된 해부학적 구조, 위치 오류, 관계 불일치 |

**평가 시 고려사항**:
- 해부학적 구조의 정확성 (예: 뼈, 장기, 혈관)
- 해부학적 위치의 정확성 (예: 좌우, 상하, 전후)
- 해부학적 관계의 정확성 (예: 인접 구조, 연결 관계)
- `key_landmarks_to_include`에 명시된 랜드마크의 가시성

---

### 2.2 Prompt Compliance (프롬프트 준수도)

**평가 기준**: 이미지가 S3 프롬프트 요구사항을 충족하는가?

| 점수 | 정의 | 예시 |
|------|------|------|
| **1.0** | 프롬프트 요구사항을 완전히 충족함. 모달리티, 뷰, 소견이 모두 일치함. | 요청된 모달리티(CT), 뷰(axial), 소견(popcorn calcification) 모두 정확히 표현 |
| **0.5** | 핵심 요구사항은 충족하지만, 일부 세부사항이 불일치하거나 누락됨. 학습 목표에는 영향 없음. | 모달리티는 맞지만 뷰가 약간 다름, 또는 소견은 있지만 강조가 부족 |
| **0.0** | 프롬프트 요구사항을 심각하게 위반함. 모달리티, 뷰, 소견이 명백히 불일치함. | 요청된 모달리티와 다른 모달리티, 완전히 다른 뷰, 요청된 소견이 없음 |

**평가 시 고려사항**:
- **모달리티 일치**: `modality_preferred` (CT, MRI, XR, US 등)와 실제 이미지 모달리티 일치 여부
- **뷰/시퀀스 일치**: `view_or_sequence`와 실제 이미지 뷰/시퀀스 일치 여부
- **핵심 소견 일치**: `key_findings_keywords`에 명시된 소견이 이미지에 표현되어 있는지
- **스타일 일치**: DIAGRAM 스타일 (벡터 라인아트, 플랫 톤) 준수 여부

**특별 주의사항**:
- 모달리티 불일치는 **blocking error** (0.0)로 평가
- 뷰/시퀀스 불일치는 심각도에 따라 0.5 또는 0.0

---

### 2.3 Text-Image Consistency (텍스트-이미지 일관성)

**평가 기준**: 이미지가 카드 텍스트(front/back)와 일관성이 있는가?

| 점수 | 정의 | 예시 |
|------|------|------|
| **1.0** | 이미지와 카드 텍스트가 완전히 일관됨. 텍스트에서 설명하는 내용이 이미지에 정확히 표현됨. | 카드가 "popcorn calcification"을 묻고, 이미지에 popcorn calcification이 명확히 보임 |
| **0.5** | 핵심 내용은 일치하지만, 세부사항에서 약간의 불일치 있음. 학습 목표에는 영향 없음. | 카드가 "calcification"을 묻고, 이미지에 calcification이 있지만 타입이 약간 다름 |
| **0.0** | 이미지와 카드 텍스트가 명백히 불일치함. 텍스트에서 설명하는 내용이 이미지에 없거나 반대임. | 카드가 "benign calcification"을 묻고, 이미지에 "malignant calcification"이 보임 |

**평가 시 고려사항**:
- 카드 `front`에서 묻는 질문과 이미지 내용의 일치성
- 카드 `back`에서 설명하는 내용과 이미지 내용의 일치성
- MCQ의 경우, 정답 선택지와 이미지 내용의 일치성
- 설명 키워드와 이미지 소견의 일치성

---

### 2.4 Image Quality (이미지 품질)

**평가 기준**: 이미지의 기술적 품질이 학습에 적합한가?

**스케일**: 1-5 Likert (카드 텍스트의 Educational Quality와 동일)

| 점수 | 정의 | 예시 |
|------|------|------|
| **5** | 매우 높은 품질. 해석에 완벽히 적합함. | 고해상도, 명확한 대비, 가독성 우수, 아티팩트 없음 |
| **4** | 높은 품질. 해석에 적합함. | 해상도 충분, 대비 양호, 가독성 양호, 미미한 아티팩트 |
| **3** | 적절한 품질. 해석 가능하지만 제한적임. | 해상도 보통, 대비 보통, 가독성 보통, 일부 아티팩트 |
| **2** | 낮은 품질. 해석이 어려움. | 해상도 부족, 대비 낮음, 가독성 낮음, 아티팩트 많음 |
| **1** | 매우 낮은 품질. 해석 불가능함. | 해상도 매우 낮음, 대비 매우 낮음, 가독성 매우 낮음, 아티팩트 심각 |

**평가 시 고려사항**:
- **해상도**: 이미지 해상도가 해석에 충분한가? (2K 목표)
- **가독성**: 해부학적 구조를 명확히 식별할 수 있는가?
- **아티팩트**: 아티팩트가 해석에 영향을 미치는가?
- **대비**: 대비가 충분한가?
- **텍스트 품질** (이미지 내 텍스트가 있는 경우):
  - 텍스트가 읽기 쉬운가? (폰트 크기, 대비, 명확성)
  - 한영 병용이 자연스러운가? (의미 없는 혼용 없음)
  - 텍스트가 이미지 내용을 정확히 설명하는가? (S1/S2 텍스트 재사용 문제 없음)

**특별 주의사항**:
- 이미지 품질이 1점이면 **blocking error**로 간주 가능 (해석 불가능)
- 텍스트 품질 문제(한영 병용, 부정확성)는 `image_quality` 점수에 반영

---

**참고: 난이도(Difficulty) 평가는 이미지 평가가 아닌 카드 텍스트 평가에 포함됩니다.**

Q1과 Q2 모두 이미지가 BACK에 배치되므로, 이미지 자체는 난이도 평가와 무관합니다. 난이도 평가는 카드 앞면 텍스트가 힌트를 너무 많이 주는지 평가하는 것이며, 이는 카드 텍스트 평가(S5_USER_CARD__v2.md)에서 수행됩니다.

---

## 3. Blocking Error 판단 기준

**Blocking Error**: 이미지가 학습 목표를 달성할 수 없게 만드는 심각한 문제

다음 중 하나라도 해당하면 `blocking_error = true`:

1. **해부학적 정확성**: 해부학적으로 명백히 잘못되어 학습자 오해 유발
2. **모달리티 불일치**: 요청된 모달리티와 실제 이미지 모달리티가 불일치 (예: CT 요청했는데 US 생성)
3. **핵심 소견 누락**: `key_findings_keywords`에 명시된 핵심 소견이 이미지에 없음
4. **텍스트-이미지 심각한 불일치**: 카드 텍스트와 이미지가 완전히 다른 내용
5. **이미지 품질**: 이미지 품질이 1점 (해석 불가능)
6. **안전성 문제**: 부적절한 콘텐츠, 환자 식별 정보 포함

**Blocking Error 규칙**:
- `blocking_error = true` → `anatomical_accuracy = 0.0`, `prompt_compliance = 0.0`, `text_image_consistency = 0.0` (자동)
- `blocking_error = true` → `image_quality ≤ 2` (일반적으로)

---

## 4. 평가 워크플로우

### 4.1 평가 순서

1. **이미지 전체 확인**: 이미지를 먼저 전체적으로 확인
2. **카드 텍스트 확인**: 카드 front/back 텍스트 확인
3. **S3 프롬프트 확인**: S3 프롬프트 요구사항 확인 (제공된 경우)
4. **메트릭별 평가**: 4개 메트릭을 순서대로 평가
5. **Blocking Error 판단**: Blocking error 여부 최종 판단

### 4.2 평가 시 제공 정보

평가자에게 다음 정보가 제공됩니다:
- 카드 텍스트 (front, back)
- 카드 옵션 (MCQ인 경우)
- S3 프롬프트 (`prompt_en`, `image_hint_v2`)
- S2 이미지 힌트 (`image_hint`)
- S1 테이블 컨텍스트 (entity_context)
- 이미지 파일

### 4.3 평가 기록

각 메트릭에 대해:
- 점수 (0.0/0.5/1.0 또는 1-5)
- 이슈 설명 (있는 경우)
- 이슈 코드 (있는 경우)
- 증거/근거 (blocking error인 경우 필수)

---

## 5. 특수 케이스 가이드

### 5.1 텍스트가 있는 이미지 (Q1/Q2)

**정책**: Q1/Q2 이미지는 BACK에 배치되므로 텍스트가 있어도 스포일러가 아님.

**평가 기준**:
- 텍스트 존재 자체는 **오류 아님** (S4 DIAGRAM 정책: 최대 1-2개 라벨, 각 1-3단어 허용)
- 텍스트 품질을 평가:
  - **한영 병용 문제**: 의미 없는 혼용 (예: "Popcorn-like 석회화") → `text_language_mixing` 이슈
  - **부정확성**: S1/S2 텍스트를 그대로 복사하여 이미지와 불일치 → `text_accuracy_error` 이슈
  - **과도한 텍스트**: S4 정책 초과 (1-2개 라벨, 각 1-3단어) → `excessive_text` 이슈
  - **가독성 문제**: 텍스트가 읽기 어려움 → `unreadable_text` 이슈

**점수 영향**:
- 텍스트 품질 문제는 `image_quality` 점수에 반영
- 심각한 텍스트 문제(부정확성, 과도함)는 `prompt_compliance` 점수에도 영향

### 5.2 테이블 인포그래픽 (S1 Table Visual)

**평가 기준**:
- **Information Clarity** (1-5 Likert): 정보 전달의 명확성
- **Anatomical Accuracy** (0.0/0.5/1.0): 해부학적 정확성
- **Prompt Compliance** (0.0/0.5/1.0): S3 프롬프트 준수도
- **Table-Visual Consistency** (0.0/0.5/1.0): S1 테이블과 인포그래픽의 일관성

**특별 고려사항**:
- 인포그래픽에는 텍스트가 **필수** (CONCEPT lane)
- 텍스트가 S1 테이블 내용을 정확히 반영하는지 확인
- OCR을 사용하여 텍스트 추출 및 검증

### 5.3 모달리티 불일치

**가장 심각한 오류 중 하나**: 모달리티 불일치는 **항상 blocking error** (0.0)

**판단 기준**:
- 카드 텍스트에서 언급된 모달리티 (예: "CT shows...")
- S2 `image_hint.modality_preferred` (예: "CT")
- 실제 이미지 모달리티 (시각적 분석)

**일치 여부**:
- 모두 일치 → 정상
- 하나라도 불일치 → blocking error (0.0)

---

## 6. 평가자 간 일치도 향상을 위한 가이드

### 6.1 모호한 경우 처리

**경계 케이스 (0.5 vs 1.0 또는 0.5 vs 0.0)**:
- 학습 목표에 영향이 있는가? → 영향 없으면 0.5, 있으면 0.0
- 수정이 필요한가? → 수정 불필요하면 1.0, 필요하면 0.5 또는 0.0
- 학습자 오해 가능성이 있는가? → 오해 가능하면 0.0

### 6.2 일관성 유지

- 동일한 유형의 문제는 동일한 점수 부여
- 평가 기준을 정기적으로 검토 및 업데이트
- 평가자 간 논의를 통한 기준 정합

### 6.3 증거 기반 평가

- 모든 판단은 명확한 증거 기반
- Blocking error는 반드시 구체적 근거 제시
- 이슈 코드는 표준화된 분류 사용

---

## 7. 평가 결과 기록 형식

### 7.1 카드 이미지 평가 결과

```json
{
  "card_image_validation": {
    "blocking_error": false,
    "anatomical_accuracy": 1.0,
    "prompt_compliance": 0.5,
    "text_image_consistency": 1.0,
    "image_quality": 4,
    "issues": [
      {
        "issue_type": "excessive_text",
        "issue_severity": "minor",
        "issue_code": "IMAGE_QUALITY_EXCESSIVE_TEXT",
        "description": "Image contains 3 labels (exceeds S4 policy of max 1-2 labels)"
      }
    ],
    "extracted_text": "Osteochondroma, Arrow",
    "text_detected": true
  }
}
```

### 7.2 테이블 인포그래픽 평가 결과

```json
{
  "table_visual_validation": {
    "blocking_error": false,
    "information_clarity": 5,
    "anatomical_accuracy": 1.0,
    "prompt_compliance": 1.0,
    "table_visual_consistency": 0.5,
    "issues": [
      {
        "issue_type": "content_mismatch",
        "issue_severity": "minor",
        "issue_code": "TABLE_VISUAL_CONTENT_MISMATCH",
        "description": "One entity row data is missing in the infographic"
      }
    ],
    "extracted_text": "Entity names, Key findings...",
    "entities_found_in_text": ["Entity1", "Entity2"]
  }
}
```

---

## 8. 참고 문서

- **QA Metric Definitions**: `0_Protocol/05_Pipeline_and_Execution/QA_Metric_Definitions.md`
- **S5 Validation Schema**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`
- **S5 vs FINAL QA Alignment**: `0_Protocol/05_Pipeline_and_Execution/S5_vs_FINAL_QA_Alignment_Analysis.md`
- **S4 Image Text Policy**: `0_Protocol/05_Pipeline_and_Execution/S5_Image_Text_Policy_Review.md`

---

**작성자**: MeducAI Research Team  
**검토 필요**: QA 평가자 훈련, 평가자 간 일치도 검증

