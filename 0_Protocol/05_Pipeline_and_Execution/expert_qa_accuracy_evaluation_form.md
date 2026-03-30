# MeducAI Expert QA (Technical Accuracy) Evaluation Form

**⚠️ Status: Deprecated**

**This document is superseded by:** `06_QA_and_Study/QA_Operations/QA_Evaluation_Rubric.md`

**Please use the canonical QA Evaluation Rubric v2.0 for all QA evaluations.**

---

본 문서는 **MeducAI FINAL 배포 콘텐츠의 기술적 정확성(Technical Accuracy)**을 평가하기 위한
**전문가 검증(Expert QA) 전용 평가표**이다.

본 평가는 사용자 설문과 **독립적으로 수행되는 전문가 기반 정확성 검증**이며,
LLM 기반 교육 콘텐츠의 **사실 오류, 임상적 부적절성, 오개념 유발 위험**을 체계적으로 식별하는 것을 목적으로 한다.

---

## 1. 평가 목적 및 원칙

### 1.1 목적

- MeducAI FINAL 콘텐츠의 **사실적 정확성(Factual correctness)** 검증
- 전문의 시험 및 임상 맥락에서의 **임상적 적절성(Clinical appropriateness)** 평가
- 학습자에게 **오개념(misconception)을 유발할 가능성** 식별
- 사용자 설문에서 보고된 오류 경험과의 **교차 검증(reference standard)** 역할

### 1.2 기본 원칙

- 평가는 **카드(문항) 단위**로 수행한다.
- 각 카드는 **독립적으로 평가**한다.
- 평가는 **2인 이상의 전문가**가 수행하며, 불일치 시 합의 절차를 따른다.
- 본 평가는 **교육용 정확성 평가**이며, 임상 진단 책임 판단이 아니다.

---

## 2. 평가 대상 및 샘플링

### 2.1 평가 대상

- MeducAI FINAL에서 배포된 콘텐츠 중:
  - Anki 카드 (기본 단위)
  - 요약 표 / 슬라이드의 개별 항목 (카드로 환산 가능할 경우)

### 2.2 샘플링 원칙 (권장)

- 토픽별 최소 **n = 10 카드**
- 전체 카드의 **10–20% 무작위 표본** 또는
- 사용자 설문에서 오류 보고가 잦은 토픽의 **집중 샘플링**

샘플링 방법은 연구 기록으로 남긴다.

---

## 3. Technical Accuracy 평가 척도

### 3.1 총점 척도 (Primary Score)

| 점수 | 정의 |
|---|---|
| **1.0** | 사실·임상적으로 정확하며, 핵심 누락이나 오해 소지 없음 |
| **0.5** | 경미한 오류·표현 부정확성은 있으나 학습 목표 달성 가능 |
| **0.0** | 핵심 오류 존재 또는 오개념/임상적 위험 유발 가능 |

---

## 4. 세부 평가 항목 (Subdomain Assessment)

각 카드는 아래 **4개 하위 영역**을 기준으로 검토한다.
(하위 항목은 참고용이며, 최종 점수는 3.1 기준으로 부여한다.)

### A. Factual Correctness
- 핵심 사실이 교과서·가이드라인과 일치하는가?
- 수치, 기준, 정의에 오류는 없는가?

### B. Clinical / Exam Appropriateness
- 전문의 시험 맥락에서 적절한 설명인가?
- 임상적으로 오해를 유발할 표현은 없는가?

### C. Completeness
- 시험에 중요한 핵심 포인트가 누락되지 않았는가?
- 지나친 단순화로 왜곡되지 않았는가?

### D. Harm / Misconception Potential
- 학습자가 잘못 이해할 위험은 없는가?
- 그럴듯하지만 틀린 정보(hallucination) 가능성은 없는가?

---

## 5. 평가 기록 양식 (카드 단위)

아래 표를 카드 1개당 1행으로 작성한다.

| 카드 ID | 토픽 | Factual | Clinical | Complete | Harm | 최종 점수 (1 / 0.5 / 0) | 주요 이슈 요약 |
|---|---|---|---|---|---|---|---|
| | | ☐ | ☐ | ☐ | ☐ | | |

- Factual / Clinical / Complete / Harm: **문제 있음 시 체크**
- 주요 이슈 요약: 오류 내용 또는 수정 필요 포인트 간단 기재

---

## 6. 다수 평가자 및 합의 절차

### 6.1 평가자 수

- 최소 **2인 이상**의 영상의학과 전문의 또는 고년차 전공의

### 6.2 불일치 처리

- 최종 점수 불일치 시:
  1. 상호 토의 후 합의 점수 도출
  2. 합의 불가 시 **보수적 점수(낮은 점수)** 채택

### 6.3 신뢰도 분석 (권장)

- Fleiss’ kappa 또는 weighted kappa
- 보고 항목:
  - 점수 일치율
  - 0점(치명 오류) 비율

---

## 7. 분석 및 보고 지표

### 7.1 주요 보고 지표

- 평균 Technical Accuracy 점수 (± SD)
- 0점 카드 비율 (critical error rate)
- 토픽별 평균 점수 분포

### 7.2 사용자 설문과의 연계

- 사용자 오류 경험 보고 빈도와
  - Expert QA 점수 간 상관 분석

---

## 8. 윤리 및 책임 고지

- 본 평가는 **교육 콘텐츠 품질 관리 목적**이며,
  임상 진료 의사결정을 대체하지 않는다.
- 본 평가 결과는 연구 목적 외 사용하지 않는다.

---

**Document status**: Draft – Expert QA Instrument for FINAL Accuracy Evaluation
