# S5 LLM 검증 vs FINAL QA 설문 문항 일치성 분석

**작성 일자**: 2025-12-29  
**목적**: S5 LLM 검증 기준과 FINAL QA 설문 문항의 일치 여부 확인 및 정렬 방안 제시

---

## 1. 현재 상태 비교

### 1.1 S5 LLM 검증 기준 (S5_Validation_Contract_Canonical.md)

| 항목 | 스케일/형식 | 정의 |
|------|------------|------|
| **Technical Accuracy** | 0.0 / 0.5 / 1.0 | 사실적 정확성, 의학적 정확성, 임상 가이드라인 정렬 |
| **Educational Quality** | 1-5 Likert | 명확성, 시험 적합성, 교육적 효과성 |
| **Blocking Error** | Binary (true/false) | 임상 안전 위험 또는 콘텐츠를 해결 불가능하게 만드는 문제 |

**S5 검증 규칙**:
- `blocking_error=true` → `technical_accuracy=0.0` (자동)
- Technical Accuracy: 1.0 (오류 없음), 0.5 (소소한 부정확성), 0.0 (차단 오류)

### 1.2 FINAL QA 설문 문항 (FINAL_QA_Form_Design.md)

| 항목 | 스케일/형식 | 정의 |
|------|------------|------|
| **B1. Blocking Error** | Yes/No | "Does this card contain a blocking error?" |
| **B2. Overall Card Quality** | 1-5 Likert | 전체 카드 품질 (1=매우 나쁨, 5=매우 좋음) |
| **B3. Evidence Comment** | Text (조건부) | B1=Yes 또는 B2≤2일 때만 필수 |

**FINAL QA 평가 규칙**:
- B1=Yes 또는 B2≤2일 때 B3 (Evidence Comment) 필수
- Pre-S5 Pass: S5 결과 보기 전 평가 (primary endpoint)
- Post-S5 Pass: S5 결과 본 후 수정 가능 (secondary endpoint)

### 1.3 QA Metric Definitions (QA_Metric_Definitions.md)

| 항목 | 스케일/형식 | 정의 |
|------|------------|------|
| **Technical Accuracy** | 0.0 / 0.5 / 1.0 | 사실적 정확성 및 임상 타당성 |
| **Educational Quality** | 1-5 Likert | 교육적 가치 (사실적 정확성과 독립적) |

**QA Metric 규칙**:
- Technical Accuracy는 **primary QA outcome**
- Educational Quality는 **co-primary QA outcome**

---

## 2. 일치성 분석

### 2.1 일치하는 항목 ✅

1. **Educational Quality ↔ Overall Card Quality**
   - **S5**: 1-5 Likert (Educational Quality)
   - **FINAL QA**: 1-5 Likert (Overall Card Quality)
   - **일치**: ✅ 동일한 스케일과 개념

2. **Blocking Error**
   - **S5**: Binary (true/false)
   - **FINAL QA**: Binary (Yes/No)
   - **일치**: ✅ 동일한 개념 (임상 안전 위험)

### 2.2 불일치하는 항목 ❌

1. **Technical Accuracy (0/0.5/1) 누락**
   - **S5**: Technical Accuracy를 0/0.5/1로 평가
   - **FINAL QA**: Technical Accuracy를 직접 평가하지 않음
   - **QA Metric**: Technical Accuracy는 **primary QA outcome**
   - **문제**: FINAL QA에서 Technical Accuracy를 평가하지 않으면 S5와 비교 불가능

2. **평가 세분도 차이**
   - **S5**: Technical Accuracy를 3단계 (0/0.5/1)로 세분화 평가
   - **FINAL QA**: Blocking Error만 Yes/No로 평가 (Technical Accuracy의 0.0만 포착)
   - **문제**: S5의 0.5 (minor inaccuracies)는 FINAL QA에서 포착되지 않음

---

## 3. 문제점 요약

### 3.1 핵심 문제

**FINAL QA 설문에서 Technical Accuracy (0/0.5/1)를 평가하지 않음**

- S5는 Technical Accuracy를 0/0.5/1로 평가
- QA_Metric_Definitions.md에 따르면 Technical Accuracy는 **primary QA outcome**
- 하지만 FINAL QA Form에서는 Blocking Error (Yes/No)만 평가
- 이로 인해:
  - S5의 Technical Accuracy와 FINAL QA 결과를 직접 비교 불가능
  - S5의 0.5 (minor inaccuracies)는 FINAL QA에서 포착되지 않음
  - Non-inferiority 분석에 필요한 Technical Accuracy 데이터 수집 불가능

### 3.2 영향

1. **S5 vs Human Rater 비교 분석 불가능**
   - S5의 Technical Accuracy (0/0.5/1)와 Human Rater의 평가를 비교할 수 없음
   - S5의 정확도(accuracy)를 검증할 수 없음

2. **Non-inferiority 분석 제약**
   - QA_Framework.md에 따르면 S0의 primary endpoint는 Mean Accuracy Score (0/0.5/1)
   - 하지만 FINAL QA Form에서는 이를 수집하지 않음

3. **S5 검증 효과 측정 불가능**
   - S5가 Technical Accuracy를 올바르게 평가하는지 검증할 수 없음

---

## 4. 정렬 방안

### 4.1 옵션 1: FINAL QA Form에 Technical Accuracy 추가 (권장)

**변경 사항**:
- FINAL QA Form에 **B1.5. Technical Accuracy** 필드 추가
- 스케일: 0.0 / 0.5 / 1.0 (3단계)
- 정의:
  - 1.0: Core concept and explanation are fully correct
  - 0.5: Core concept is correct, but explanation contains minor omissions
  - 0.0: Core concept is incorrect or misleading

**FINAL QA Form 수정안**:
```
B1. Blocking Error (Yes/No) - 기존 유지
B1.5. Technical Accuracy (0.0 / 0.5 / 1.0) - 신규 추가
B2. Overall Card Quality (1-5 Likert) - 기존 유지
B3. Evidence Comment (조건부) - 기존 유지
```

**장점**:
- S5와 Human Rater 평가를 직접 비교 가능
- QA_Metric_Definitions.md의 primary outcome 수집 가능
- S5 검증 효과 측정 가능

**단점**:
- 평가자 부담 증가 (추가 평가 항목)

### 4.2 옵션 2: Blocking Error를 Technical Accuracy 0.0으로 매핑

**변경 사항**:
- FINAL QA에서 Blocking Error (Yes/No)를 Technical Accuracy로 변환
- Blocking Error = Yes → Technical Accuracy = 0.0
- Blocking Error = No → Technical Accuracy = 1.0 (또는 0.5, 평가자 판단)

**문제점**:
- S5의 0.5 (minor inaccuracies)를 포착할 수 없음
- Technical Accuracy의 세분화된 평가 불가능

### 4.3 옵션 3: S5 검증 기준을 FINAL QA에 맞춤 (비권장)

**변경 사항**:
- S5의 Technical Accuracy를 제거하고 Blocking Error만 평가

**문제점**:
- S5의 세분화된 평가 능력 상실
- QA_Metric_Definitions.md와 불일치

---

## 5. 권장 사항

### 5.1 즉시 조치

**FINAL QA Form에 Technical Accuracy (0/0.5/1) 필드 추가**

1. **FINAL_QA_Form_Design.md 수정**:
   - B1.5. Technical Accuracy 필드 추가
   - 스케일: 0.0 / 0.5 / 1.0
   - 정의: QA_Metric_Definitions.md의 Technical Accuracy 정의 사용

2. **평가자 가이드 업데이트**:
   - Technical Accuracy 평가 기준 명확화
   - S5의 Technical Accuracy와 비교 가능하도록 동일한 정의 사용

### 5.2 장기 개선

1. **S5 vs Human Rater 일치도 분석**:
   - Technical Accuracy 일치도 (Cohen's kappa)
   - Educational Quality 일치도 (Intraclass Correlation Coefficient)

2. **S5 검증 효과 측정**:
   - S5가 Human Rater의 평가를 얼마나 잘 예측하는지 측정
   - S5의 false positive/negative rate 계산

---

## 6. 참고 문서

- **S5 검증 기준**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Contract_Canonical.md`
- **FINAL QA 설문**: `0_Protocol/06_QA_and_Study/FINAL_QA_Form_Design.md`
- **QA Metric 정의**: `0_Protocol/05_Pipeline_and_Execution/QA_Metric_Definitions.md`
- **QA Framework**: `0_Protocol/06_QA_and_Study/QA_Framework.md`

---

## 6.1 FINAL gate용 major_error 매핑 (추가, pre-specified)

FINAL gate에서 보고하는 error rate(%)는 반드시 binary `major_error`로 계산한다.

정의, deterministic, pre-specified:

- `major_error=TRUE` if any of:
  - B1 Blocking Error equals Yes.
  - B1.5 Technical Accuracy equals 0.0.
  - image_blocking_error equals Yes, 예, modality mismatch, anatomy grossly wrong, 또는 이미지가 학습 목표 달성을 불가능하게 함.
- `major_error=FALSE` otherwise.

이 매핑은 `QA_Metric_Definitions.md` 및 `Human_Rating_Schema_Canonical.md`와 동일하게 유지한다.

---

## 7. 결론

**현재 상태**: S5 LLM 검증과 FINAL QA 설문 문항이 **부분적으로 일치**하지만, **Technical Accuracy (0/0.5/1) 평가가 FINAL QA에서 누락**되어 있습니다.

**권장 조치**: FINAL QA Form에 Technical Accuracy (0/0.5/1) 필드를 추가하여 S5와 Human Rater 평가를 직접 비교할 수 있도록 정렬해야 합니다.

**우선순위**: 높음 (S5 검증 효과 측정 및 Non-inferiority 분석에 필수)

---

**작성자**: MeducAI Research Team  
**검토 필요**: QA Framework, FINAL QA Form Design 문서 업데이트

