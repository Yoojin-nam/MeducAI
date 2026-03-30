# MeducAI FINAL 배포 이후 전공의 대상 사용자 연구 프로토콜

## 1. 연구 배경 및 목적

LLM 기반 교육 콘텐츠는 기술적 정확성(technical accuracy)뿐 아니라, 실제 시험 대비 학습에서의 **교육적 질(educational quality)**과 **효율성(efficiency)**이 핵심 성과 지표이다. 본 연구는 MeducAI FINAL 버전을 전공의에게 배포한 후, 실제 사용 맥락에서 해당 시스템이 전공의 학습에 미치는 영향을 **정량적·반복 측정 기반 사용자 연구**로 평가하는 것을 목적으로 한다.

특히 다음 질문에 답하고자 한다.
1. MeducAI FINAL 산출물은 전문의 시험 대비에 실질적으로 도움이 되는가?
2. 기술적 정확성과 교육적 질은 어떤 수준인가?
3. 학습 시간·노력 측면에서 효율성을 제공하는가?
4. 개인별 baseline 차이를 고려했을 때, 사용 전후 변화는 어떠한가?

---

## 2. 연구 설계 개요

- **연구 유형**: 전향적 관찰 연구 (prospective observational user study)
- **대상**: 영상의학과 4년차 전공의 (전문의 시험 준비 단계)
- **개입**: MeducAI FINAL 버전 자유 사용
- **연구 기간**: FINAL 배포 후 약 4–6주
- **평가 방식**:
  - Baseline 설문 (배포 전)
  - 반복 설문 (주 1회 또는 2주 1회)
  - Endline 설문 (연구 종료 시)
  - 사용 로그 분석 (가능한 경우)

---

## 3. 평가 프레임워크

### 3.1 Primary Outcome

1. **Technical Accuracy**
   - MeducAI FINAL 산출물의 사실적·임상적 정확성
2. **Educational Quality / Exam Utility**
   - 전문의 시험 대비에 대한 실질적 도움 정도
3. **Efficiency**
   - 학습 자료 생성·정리·이해에 소요되는 시간 및 노력 절감

### 3.2 Secondary Outcome

- Trust 및 Reliance calibration
- Usability 및 재사용 의향
- Cognitive load (인지부하)
- 사용량 대비 효과(dose–response 관계)

---

## 4. 설문조사 구성

### 4.1 Baseline Survey (배포 직전)

**목적**: 개인별 baseline 특성 파악 및 추후 변화량 분석을 위한 기준값 설정

#### A. 인구학적·학습 배경
- 연차(PGY)
- 현재 로테이션
- 평일/주말 평균 공부 시간(분)
- 기존 학습 도구(교재, 강의, Anki 등) 사용 여부

#### B. LLM 관련 경험 (Baseline Covariates)
- LLM 사용 경험 여부 (Yes/No)
- 임상 또는 영상 판독 목적 LLM 사용 경험 (Yes/No)
- LLM 기술 이해 수준 (1–5 Likert)
- LLM 생성 임상 설명 전반적 신뢰도 (1–5 Likert)

#### C. Baseline Outcome
- 학습 자기효능감 (1–5 Likert)
- 인지부하(mental effort) (1–5 Likert)

---

### 4.2 반복 설문 (Weekly / Biweekly)

**목적**: 사용량, 효율성, 교육적 질의 시간에 따른 변화 추적

#### A. 사용량(Self-report)
- 지난 기간 사용 일수
- 총 사용 시간(분)
- 학습에 실제 사용한 카드 수

#### B. Efficiency (분 단위 측정)
- MeducAI 사용 시 학습 자료 생성·정리에 소요된 시간(분)
- 동일 작업을 MeducAI 없이 수행했을 경우 예상 시간(분)
- 오류 수정·검증에 소요된 시간(분)
- 체감 시간 절감 정도 (1–5 Likert)

#### C. Educational Quality
(각 항목 1–5 Likert)
- 전문의 시험 대비에 도움이 됨
- 토픽의 핵심(core)을 잘 다룸
- 설명 구조가 학습에 적절함
- 오개념을 유발할 위험이 낮음

#### D. Trust / Calibration
- 산출물을 신뢰할 수 있었음
- 검증 없이 그대로 암기한 경험 (역문항)
- 그럴듯하지만 헷갈린 경험 (역문항)

---

### 4.3 Endline Survey (연구 종료 시)

**목적**: 종합 평가 및 위험/개선 요소 파악

- Technical accuracy(체감) (1–5)
- Educational quality(종합) (1–5)
- Efficiency(종합) (1–5)
- 재사용 의향 (1–5)
- 동료 추천 의향 (0–10)
- MeducAI 사용 기간 동안의 평균 수면 시간 (행동 변수, 단일 문항)
- 명백한 factual error 경험 횟수
- 학습에 악영향을 준 오류 경험 여부 (Yes/No + 서술)
- 개선이 가장 필요한 영역 (단일 선택)
- 자유 서술 의견(선택)

---

## 5. Technical Accuracy 평가 정의

### 5.1 평가 단위

- **단위**: Anki 카드(문항) 단위
- **평가 척도**: 0 / 0.5 / 1
  - 1: 사실·임상적으로 정확, 핵심 누락 없음
  - 0.5: 경미한 오류 또는 표현 문제
  - 0: 핵심 오류 또는 오개념 유발 가능

### 5.2 하위 구성요소

- Factual correctness
- Clinical appropriateness (시험 맥락 적합성)
- Completeness
- Harm potential

---

## 6. Efficiency 지표 정의

- **Time_saved_min** = 예상 소요 시간 − 실제 소요 시간
- **Edit_time_min** = 수정·검증에 소요된 시간
- **Efficiency index (탐색적)** = Time_saved_min / 실제 소요 시간

가능한 경우, 사용 로그(세션 길이, 카드 열람 수 등)와 설문 응답을 교차 분석한다.

---

## 7. 통계 분석 계획

### 7.1 기본 원칙

- 개인별 편차가 크므로 **baseline 대비 변화량 중심 분석**을 수행한다.
- 반복 측정 구조를 고려한 혼합효과모형(LMM) 또는 GEE를 사용한다.

### 7.2 Primary Analysis

- 종속변수: Quality, Efficiency, Accuracy
- 독립변수: 시간(time), 사용량, baseline covariates
- Random effect: 개인별 intercept (필수)

### 7.3 Dose–Response 분석

- 사용량(시간, 카드 수)과 outcome 변화량 간 연관 분석
- 필요 시 비선형(spline) 또는 구간화 분석

### 7.4 Subgroup Analysis

- PGY, baseline LLM 지식 수준, baseline 신뢰도
- time × subgroup interaction으로 변화량 차이 평가
- 탐색적 분석으로 명시

---

## 8. 결측치 및 민감도 분석

- 혼합모형을 통한 MAR 가정 하 분석
- 보조적으로 complete-case 분석 수행

---

## 9. 윤리적 고려

- IRB 승인 후 연구 진행
- 모든 설문은 익명화하여 분석
- 연구 참여 여부 및 설문 응답은 평가·시험과 무관함을 명시

---

## 10. 기대 효과

본 연구는 LLM 기반 전문의 시험 대비 학습 도구의 **정확성–교육적 질–효율성**을 통합적으로 평가하는 체계적 사용자 연구로서, 향후 교육용 의료 AI 평가 프레임워크 수립에 근거 자료를 제공할 것으로 기대된다.

